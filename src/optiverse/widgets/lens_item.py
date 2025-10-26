from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ..core.models import LensParams
from .base_obj import BaseObj
from .component_sprite import ComponentSprite


class LensItem(BaseObj):
    """
    Thin lens element with focal length and optional component sprite.
    """
    
    def __init__(self, params: LensParams):
        super().__init__()
        self.params = params
        self._sprite: Optional[ComponentSprite] = None
        self._update_geom()
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._maybe_attach_sprite()
        self._ready = True
    
    def _sync_params_from_item(self):
        """Sync params from item position/rotation."""
        self.params.x_mm = float(self.pos().x())
        self.params.y_mm = float(self.pos().y())
        self.params.angle_deg = float(self.rotation())
    
    def _update_geom(self):
        """Update geometry based on length."""
        self.prepareGeometryChange()
        L = max(1.0, self.params.length_mm)
        self._p1 = QtCore.QPointF(-L / 2, 0)
        self._p2 = QtCore.QPointF(+L / 2, 0)
        self._len = L
    
    def _maybe_attach_sprite(self):
        """Attach or update component sprite if image available."""
        if getattr(self, "_sprite", None):
            try:
                if self.scene():
                    self.scene().removeItem(self._sprite)
            except Exception:
                pass
            self._sprite = None
        
        if self.params.image_path and self.params.line_px:
            import math
            x1, y1, x2, y2 = self.params.line_px
            picked_len_px = max(1.0, math.hypot(x2 - x1, y2 - y1))
            picked_len_mm = picked_len_px * (
                self.params.mm_per_pixel if self.params.mm_per_pixel > 0 else 1.0
            )
            
            # Sync length from picked line
            if abs(self.params.length_mm - picked_len_mm) > 1e-6:
                self.params.length_mm = picked_len_mm
                self._update_geom()
            
            self._sprite = ComponentSprite(
                self.params.image_path,
                self.params.mm_per_pixel,
                self.params.line_px,
                self.params.length_mm,
                self,
            )
        
        self.setZValue(0)
    
    def boundingRect(self) -> QtCore.QRectF:
        pad = 8
        return QtCore.QRectF(-self._len / 2 - pad, -pad, self._len + 2 * pad, 2 * pad)
    
    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.moveTo(self._p1)
        path.lineTo(self._p2)
        s = QtGui.QPainterPathStroker()
        s.setWidth(8)
        return s.createStroke(path)
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setPen(QtGui.QPen(QtGui.QColor("royalblue"), 2))
        p.drawLine(self._p1, self._p2)
        p.setBrush(QtGui.QColor("royalblue"))
        p.drawEllipse(QtCore.QPointF(0, 0), 2, 2)
    
    def open_editor(self):
        """Open editor dialog for lens parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit Lens")
        f = QtWidgets.QFormLayout(d)
        
        x = QtWidgets.QDoubleSpinBox()
        x.setRange(-1e6, 1e6)
        x.setDecimals(3)
        x.setSuffix(" mm")
        x.setValue(self.pos().x())
        
        y = QtWidgets.QDoubleSpinBox()
        y.setRange(-1e6, 1e6)
        y.setDecimals(3)
        y.setSuffix(" mm")
        y.setValue(self.pos().y())
        
        ang = QtWidgets.QDoubleSpinBox()
        ang.setRange(-180, 180)
        ang.setDecimals(2)
        ang.setSuffix(" °")
        ang.setValue(self.rotation())
        
        efl = QtWidgets.QDoubleSpinBox()
        efl.setRange(-1e7, 1e7)
        efl.setDecimals(3)
        efl.setSuffix(" mm")
        efl.setValue(self.params.efl_mm)
        
        length = QtWidgets.QDoubleSpinBox()
        length.setRange(1, 1e7)
        length.setDecimals(2)
        length.setSuffix(" mm")
        length.setValue(self.params.length_mm)
        
        f.addRow("X", x)
        f.addRow("Y", y)
        f.addRow("Angle", ang)
        f.addRow("EFL", efl)
        f.addRow("Clear length", length)
        
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        if d.exec():
            self.setPos(x.value(), y.value())
            self.params.x_mm = x.value()
            self.params.y_mm = y.value()
            self.setRotation(ang.value())
            self.params.angle_deg = ang.value()
            self.params.efl_mm = efl.value()
            self.params.length_mm = length.value()
            self._update_geom()
            self._maybe_attach_sprite()
            self.edited.emit()
    
    def endpoints_scene(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get segment endpoints in scene coordinates."""
        p1 = self.mapToScene(self._p1)
        p2 = self.mapToScene(self._p2)
        return np.array([p1.x(), p1.y()]), np.array([p2.x(), p2.y()])
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        d = asdict(self.params)
        d["x_mm"] = float(self.pos().x())
        d["y_mm"] = float(self.pos().y())
        d["angle_deg"] = float(self.rotation())
        return d
    
    def from_dict(self, d: Dict[str, Any]):
        """Deserialize from dictionary."""
        self.params = LensParams(**d)
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_geom()
        self._maybe_attach_sprite()
        self.edited.emit()
