from __future__ import annotations

import math
import uuid
from typing import Dict, Any

from PyQt6 import QtCore, QtGui, QtWidgets


class RectangleItem(QtWidgets.QGraphicsObject):
    """
    Simple annotation rectangle (no optical effect).
    Single-click placement with default size; movable and selectable.
    Supports Ctrl+drag and Ctrl+wheel for rotation.
    """
    
    def __init__(self, width_mm: float = 60.0, height_mm: float = 40.0, item_uuid: str | None = None):
        super().__init__()
        self.item_uuid = item_uuid if item_uuid else str(uuid.uuid4())
        self._w = float(width_mm)
        self._h = float(height_mm)
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.setZValue(100.0)
        self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        self.setTransformOriginPoint(0.0, 0.0)
        
        # Rotation mode state (Ctrl + drag to rotate)
        self._rotating = False
        self._rotation_start_angle = 0.0
        self._rotation_initial = 0.0
    
    def boundingRect(self) -> QtCore.QRectF:
        w = max(1.0, self._w)
        h = max(1.0, self._h)
        return QtCore.QRectF(-w / 2.0, -h / 2.0, w, h)
    
    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = self.boundingRect()
        # Fill 20% gray
        p.setBrush(QtGui.QBrush(QtGui.QColor(200, 200, 200, 120)))
        # Black stroke
        pen = QtGui.QPen(QtGui.QColor(10, 10, 10), 2.0)
        pen.setCosmetic(True)
        p.setPen(pen)
        p.drawRect(rect)
    
    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent):
        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit")
        act_del = m.addAction("Delete")
        
        # Add z-order options
        m.addSeparator()
        act_bring_to_front = m.addAction("Bring to Front")
        act_bring_forward = m.addAction("Bring Forward")
        act_send_backward = m.addAction("Send Backward")
        act_send_to_back = m.addAction("Send to Back")
        
        a = m.exec(ev.screenPos())
        if a == act_edit:
            self.open_editor()
        elif a == act_del and self.scene():
            self.scene().removeItem(self)
        elif a in (act_bring_to_front, act_bring_forward, act_send_backward, act_send_to_back):
            self._handle_z_order_action(a, act_bring_to_front, act_bring_forward,
                                       act_send_backward, act_send_to_back)
    
    def _handle_z_order_action(self, selected_action, act_bring_to_front, act_bring_forward,
                               act_send_backward, act_send_to_back):
        """Handle z-order menu actions."""
        from optiverse.core.zorder_utils import apply_z_order_change
        
        if not self.scene():
            return
        
        # Get items to operate on: if this item is selected, use all selected items
        # Otherwise, just use this item
        if self.isSelected():
            items = [item for item in self.scene().selectedItems() 
                    if hasattr(item, 'setZValue')]
        else:
            items = [self]
        
        if not items:
            return
        
        # Determine operation
        if selected_action == act_bring_to_front:
            operation = "bring_to_front"
        elif selected_action == act_bring_forward:
            operation = "bring_forward"
        elif selected_action == act_send_backward:
            operation = "send_backward"
        elif selected_action == act_send_to_back:
            operation = "send_to_back"
        else:
            return
        
        # Get undo stack from main window
        undo_stack = None
        if self.scene().views():
            main_window = self.scene().views()[0].window()
            if hasattr(main_window, 'undo_stack'):
                undo_stack = main_window.undo_stack
        
        # Apply z-order change
        apply_z_order_change(items, operation, self.scene(), undo_stack)
    
    def mousePressEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        """Handle mouse press for rotation mode (Ctrl+drag) or normal drag."""
        if self.isSelected() and (ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            # Enter rotation mode
            self._rotating = True
            self._rotation_initial = self.rotation()
            
            # Calculate rotation center (item center in scene coordinates)
            center = self.mapToScene(self.transformOriginPoint())
            
            # Calculate initial angle from rotation center to mouse position
            mouse_pos = ev.scenePos()
            dx = mouse_pos.x() - center.x()
            dy = mouse_pos.y() - center.y()
            self._rotation_start_angle = math.degrees(math.atan2(dy, dx))
            
            # Change cursor to indicate rotation mode
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            ev.accept()
        else:
            # Normal drag behavior
            super().mousePressEvent(ev)
    
    def mouseMoveEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        """Handle mouse move for rotation or normal drag."""
        if self._rotating:
            # Get rotation center (item center in scene coordinates)
            center = self.mapToScene(self.transformOriginPoint())
            
            # Calculate current angle from rotation center to mouse position
            mouse_pos = ev.scenePos()
            dx = mouse_pos.x() - center.x()
            dy = mouse_pos.y() - center.y()
            current_angle = math.degrees(math.atan2(dy, dx))
            
            # Calculate rotation delta
            angle_delta = current_angle - self._rotation_start_angle
            
            # Apply rotation
            new_rotation = self._rotation_initial + angle_delta
            
            # Shift+Ctrl: snap to absolute 45-degree increments (0, 45, 90, 135, 180, etc.)
            if ev.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
                new_rotation = round(new_rotation / 45.0) * 45.0
            
            self.setRotation(new_rotation)
            
            ev.accept()
        else:
            # Normal drag behavior
            super().mouseMoveEvent(ev)
    
    def mouseReleaseEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        """Handle mouse release to exit rotation mode."""
        if self._rotating:
            self._rotating = False
            self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            ev.accept()
        else:
            super().mouseReleaseEvent(ev)
    
    def wheelEvent(self, ev: QtWidgets.QGraphicsSceneWheelEvent):
        """Ctrl + wheel → rotate element."""
        if self.isSelected() and (ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            dy = ev.angleDelta().y()
            steps = dy / 120.0
            rotation_delta = 2.0 * steps
            
            self.setRotation(self.rotation() + rotation_delta)
            
            ev.accept()
        else:
            super().wheelEvent(ev)
    
    def to_dict(self) -> Dict[str, Any]:
        r = self.boundingRect()
        return {
            "type": "rectangle",
            "x": float(self.scenePos().x()),
            "y": float(self.scenePos().y()),
            "width_mm": float(r.width()),
            "height_mm": float(r.height()),
            "angle_deg": float(self.rotation()),
            "item_uuid": self.item_uuid,
            "z_value": float(self.zValue()),
        }
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RectangleItem":
        item_uuid = d.get("item_uuid")
        width_mm = float(d.get("width_mm", 60.0))
        height_mm = float(d.get("height_mm", 40.0))
        item = RectangleItem(width_mm, height_mm, item_uuid)
        item.setPos(float(d.get("x", 0.0)), float(d.get("y", 0.0)))
        ang = float(d.get("angle_deg", 0.0))
        item.setRotation(ang)
        
        # Restore z-value if present
        if "z_value" in d:
            item.setZValue(float(d["z_value"]))
        
        return item

    def open_editor(self):
        d = QtWidgets.QDialog(self.scene().views()[0].window() if self.scene() and self.scene().views() else None)
        d.setWindowTitle("Edit Rectangle")
        f = QtWidgets.QFormLayout(d)
        
        # Save initial state for rollback on cancel
        initial_x = self.pos().x()
        initial_y = self.pos().y()
        initial_ang = self.rotation()
        initial_w = self._w
        initial_h = self._h
        
        x = QtWidgets.QDoubleSpinBox()
        x.setRange(-1e6, 1e6)
        x.setDecimals(3)
        x.setSuffix(" mm")
        x.setValue(initial_x)
        
        y = QtWidgets.QDoubleSpinBox()
        y.setRange(-1e6, 1e6)
        y.setDecimals(3)
        y.setSuffix(" mm")
        y.setValue(initial_y)
        
        ang = QtWidgets.QDoubleSpinBox()
        ang.setRange(-360, 360)
        ang.setDecimals(2)
        ang.setSuffix(" °")
        ang.setValue(initial_ang)
        
        w = QtWidgets.QDoubleSpinBox()
        w.setRange(1.0, 1e7)
        w.setDecimals(2)
        w.setSuffix(" mm")
        w.setValue(initial_w)
        
        h = QtWidgets.QDoubleSpinBox()
        h.setRange(1.0, 1e7)
        h.setDecimals(2)
        h.setSuffix(" mm")
        h.setValue(initial_h)
        
        def update_position():
            self.setPos(x.value(), y.value())
        
        def update_angle():
            self.setRotation(ang.value())
        
        def update_size():
            self.prepareGeometryChange()
            self._w = w.value()
            self._h = h.value()
            self.update()
        
        x.valueChanged.connect(update_position)
        y.valueChanged.connect(update_position)
        ang.valueChanged.connect(update_angle)
        w.valueChanged.connect(update_size)
        h.valueChanged.connect(update_size)
        
        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Rotation", ang)
        f.addRow("Width", w)
        f.addRow("Height", h)
        
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        result = d.exec()
        if not result:
            # rollback
            self.setPos(initial_x, initial_y)
            self.setRotation(initial_ang)
            self.prepareGeometryChange()
            self._w = initial_w
            self._h = initial_h
            self.update()


