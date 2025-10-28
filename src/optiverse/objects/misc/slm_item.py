from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import SLMParams
from ...ui.smart_spinbox import SmartDoubleSpinBox
from ..base_obj import BaseObj
from ..component_sprite import ComponentSprite


class SLMItem(BaseObj):
    """
    Spatial Light Modulator (SLM) element with optional component sprite.
    Acts as a mirror for ray tracing purposes.
    """
    
    def __init__(self, params: SLMParams, item_uuid: str | None = None):
        super().__init__(item_uuid)
        self.params = params
        self._sprite: Optional[ComponentSprite] = None
        self._actual_length_mm: Optional[float] = None  # Calculated from picked line
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
        # Use actual calculated length if available, otherwise use object_height_mm
        L = max(1.0, self._actual_length_mm if self._actual_length_mm is not None else self.params.object_height_mm)
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
            # ComponentSprite handles all denormalization internally
            # We just pass the normalized coordinates and let it handle the rest
            self._sprite = ComponentSprite(
                self.params.image_path,
                self.params.line_px,
                self.params.object_height_mm,
                self,
            )
            
            # Update element geometry to match the picked line length (not full image height)
            self._actual_length_mm = self._sprite.picked_line_length_mm
            self._update_geom()
        
        self.setZValue(0)
    
    def boundingRect(self) -> QtCore.QRectF:
        pad = 8
        rect = QtCore.QRectF(-self._len / 2 - pad, -pad, self._len + 2 * pad, 2 * pad)
        # Include sprite in bounds (Phase 1.2: Clickable Sprites)
        return self._bounds_union_sprite(rect)
    
    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.moveTo(self._p1)
        path.lineTo(self._p2)
        s = QtGui.QPainterPathStroker()
        s.setWidth(10)
        shp = s.createStroke(path)
        # Include sprite in shape for hit testing (Phase 1.2: Clickable Sprites)
        return self._shape_union_sprite(shp)
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        # Use a distinct color for SLM (blue-ish)
        p.setPen(QtGui.QPen(QtGui.QColor("steelblue"), 3))
        p.drawLine(self._p1, self._p2)
    
    def open_editor(self):
        """Open editor dialog for SLM parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit SLM")
        f = QtWidgets.QFormLayout(d)
        
        # Save initial state for rollback on cancel
        initial_x = self.pos().x()
        initial_y = self.pos().y()
        initial_ang = self.rotation()
        initial_length = self.params.object_height_mm
        
        x = SmartDoubleSpinBox()
        x.setRange(-1e6, 1e6)
        x.setDecimals(3)
        x.setSuffix(" mm")
        x.setValue(initial_x)
        
        y = SmartDoubleSpinBox()
        y.setRange(-1e6, 1e6)
        y.setDecimals(3)
        y.setSuffix(" mm")
        y.setValue(initial_y)
        
        ang = SmartDoubleSpinBox()
        ang.setRange(-180, 180)
        ang.setDecimals(2)
        ang.setSuffix(" °")
        ang.setValue(initial_ang)
        ang.setToolTip("Optical axis angle (0° = horizontal →, 90° = vertical ↑)")
        
        length = SmartDoubleSpinBox()
        length.setRange(1, 1e7)
        length.setDecimals(2)
        length.setSuffix(" mm")
        length.setValue(initial_length)
        
        # Live update connections
        def update_position():
            self.setPos(x.value(), y.value())
            self.params.x_mm = x.value()
            self.params.y_mm = y.value()
            self.edited.emit()
        
        def update_angle():
            self.setRotation(ang.value())
            self.params.angle_deg = ang.value()
            self.edited.emit()
        
        def update_length():
            self.params.object_height_mm = length.value()
            self._update_geom()
            self._maybe_attach_sprite()
            self.edited.emit()
        
        x.valueChanged.connect(update_position)
        y.valueChanged.connect(update_position)
        ang.valueChanged.connect(update_angle)
        length.valueChanged.connect(update_length)
        
        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Optical Axis Angle", ang)
        f.addRow("Length", length)
        
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        # Execute dialog and rollback if cancelled
        if not d.exec():
            # User clicked Cancel - restore initial values
            self.setPos(initial_x, initial_y)
            self.params.x_mm = initial_x
            self.params.y_mm = initial_y
            self.setRotation(initial_ang)
            self.params.angle_deg = initial_ang
            self.params.object_height_mm = initial_length
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
        d["item_uuid"] = self.item_uuid
        return d
    
    def from_dict(self, d: Dict[str, Any]):
        """Deserialize from dictionary."""
        if "item_uuid" in d:
            self.item_uuid = d["item_uuid"]
        self.params = SLMParams(**d)
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_geom()
        self._maybe_attach_sprite()
        self.edited.emit()

