from __future__ import annotations

import math
from typing import Optional, Dict, Any

from PyQt6 import QtCore, QtGui, QtWidgets


class RulerItem(QtWidgets.QGraphicsObject):
    """
    Draggable two-point ruler that shows the distance in mm.
    - Drag endpoint bars to measure; drag elsewhere to move as a whole.
    - Right-click → Delete.
    """
    
    def __init__(self, p1=QtCore.QPointF(-50, 0), p2=QtCore.QPointF(50, 0)):
        super().__init__()
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)  # avoid paint caching artifacts
        self.setZValue(10_000)  # keep ruler + label on top

        self._p1 = QtCore.QPointF(p1)
        self._p2 = QtCore.QPointF(p2)
        self._grab: Optional[str] = None  # 'p1' | 'p2' | None
        
        # Appearance
        self._line_w = 2.0
        self._bar_w = 2.0      # bar thickness along the line
        self._bar_h = 10.0     # bar height perpendicular to the line
        self._hit_radius = 10.0
        self._pad = 90.0       # padding to fully cover label area when moving

    def boundingRect(self) -> QtCore.QRectF:
        rect = QtCore.QRectF(self._p1, self._p2).normalized()
        pad = max(self._pad, self._bar_h * 1.5)
        return rect.adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.moveTo(self._p1)
        path.lineTo(self._p2)
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(max(12.0, self._bar_h))
        shp = stroker.createStroke(path)
        return shp

    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        
        # baseline (flat caps)
        base_pen = QtGui.QPen(QtGui.QColor(30, 30, 30), self._line_w)
        base_pen.setCosmetic(True)
        base_pen.setCapStyle(QtCore.Qt.PenCapStyle.FlatCap)
        base_pen.setJoinStyle(QtCore.Qt.PenJoinStyle.MiterJoin)
        p.setPen(base_pen)
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.drawLine(self._p1, self._p2)

        # vectors
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        L = math.hypot(dx, dy) or 1.0
        dirx, diry = dx / L, dy / L
        perpx, perpy = -diry, dirx

        # helper to draw a bar rectangle perpendicular to the line (BLACK)
        def draw_bar(center: QtCore.QPointF):
            cx, cy = center.x(), center.y()
            hw = self._bar_w / 2.0  # along dir
            hh = self._bar_h / 2.0  # along perp
            pts = [
                QtCore.QPointF(cx + (-hw * dirx + -hh * perpx), cy + (-hw * diry + -hh * perpy)),
                QtCore.QPointF(cx + (hw * dirx + -hh * perpx), cy + (hw * diry + -hh * perpy)),
                QtCore.QPointF(cx + (hw * dirx + hh * perpx), cy + (hw * diry + hh * perpy)),
                QtCore.QPointF(cx + (-hw * dirx + hh * perpx), cy + (-hw * diry + hh * perpy)),
            ]
            poly = QtGui.QPolygonF(pts)
            p.save()
            p.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black, 1))
            p.setBrush(QtCore.Qt.GlobalColor.black)
            p.drawPolygon(poly)
            p.restore()

        draw_bar(self._p1)
        draw_bar(self._p2)

        # label (same anti-smear method; uses QRectF overload)
        mid = (self._p1 + self._p2) * 0.5
        txt = f"{L:.1f} mm"
        angle = math.degrees(math.atan2(dy, dx))
        
        p.save()
        p.translate(mid)
        p.rotate(angle)
        fm = QtGui.QFontMetrics(p.font())
        w = fm.horizontalAdvance(txt) + 12
        h = fm.height() + 6
        y_off = -(self._bar_h / 2.0 + 10.0 + h)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(255, 255, 255, 240))
        p.drawRoundedRect(QtCore.QRectF(-w / 2.0, y_off, float(w), float(h)), 4.0, 4.0)
        p.setPen(QtGui.QPen(QtGui.QColor(20, 20, 20)))
        p.drawText(QtCore.QRectF(-w / 2.0, y_off, float(w), float(h)), QtCore.Qt.AlignmentFlag.AlignCenter, txt)
        p.restore()
    
    def _nearest_endpoint(self, pos: QtCore.QPointF) -> Optional[str]:
        """Check if pos is near p1 or p2."""
        if QtCore.QLineF(pos, self._p1).length() <= self._hit_radius:
            return "p1"
        if QtCore.QLineF(pos, self._p2).length() <= self._hit_radius:
            return "p2"
        return None
    
    def mousePressEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            # context menu on right-click
            m = QtWidgets.QMenu()
            act_del = m.addAction("Delete")
            if m.exec(ev.screenPos()) == act_del and self.scene():
                self.scene().removeItem(self)
            ev.accept()
            return
        
        which = self._nearest_endpoint(ev.pos())
        if ev.button() == QtCore.Qt.MouseButton.LeftButton and which:
            self._grab = which
            ev.accept()
            return
        
        self._grab = None
        super().mousePressEvent(ev)
    
    def mouseMoveEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        if self._grab == "p1":
            self.prepareGeometryChange()
            self._p1 = ev.pos()
            self.update()
            ev.accept()
            return
        if self._grab == "p2":
            self.prepareGeometryChange()
            self._p2 = ev.pos()
            self.update()
            ev.accept()
            return
        super().mouseMoveEvent(ev)
    
    def mouseReleaseEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        self._grab = None
        super().mouseReleaseEvent(ev)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize ruler to dictionary."""
        # Save absolute endpoints in scene space so reopening is exact
        p1_scene = self.mapToScene(self._p1)
        p2_scene = self.mapToScene(self._p2)
        return {
            "type": "ruler",
            "p1": [float(p1_scene.x()), float(p1_scene.y())],
            "p2": [float(p2_scene.x()), float(p2_scene.y())],
        }
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RulerItem":
        """Deserialize ruler from dictionary."""
        p1 = QtCore.QPointF(float(d["p1"][0]), float(d["p1"][1]))
        p2 = QtCore.QPointF(float(d["p2"][0]), float(d["p2"][1]))
        # store points in item coords and keep item at origin
        return RulerItem(p1, p2)


