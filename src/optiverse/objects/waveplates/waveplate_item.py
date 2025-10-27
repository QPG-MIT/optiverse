from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import WaveplateParams
from ..base_obj import BaseObj
from ..component_sprite import ComponentSprite


class WaveplateItem(BaseObj):
    """
    Waveplate optical element with configurable phase shift and fast axis.
    
    Waveplates introduce a phase shift between orthogonal polarization components:
    - Quarter waveplate (QWP): 90° phase shift - converts linear ↔ circular
    - Half waveplate (HWP): 180° phase shift - rotates linear polarization
    """
    
    def __init__(self, params: WaveplateParams):
        super().__init__()
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
            import math
            import os
            from PyQt6.QtGui import QPixmap
            
            # Load image to get actual dimensions
            if os.path.exists(self.params.image_path):
                pix = QPixmap(self.params.image_path)
                actual_height = pix.height()
                
                # line_px is in normalized 1000px space - denormalize to actual image space
                scale = float(actual_height) / 1000.0 if actual_height > 0 else 1.0
                x1, y1, x2, y2 = self.params.line_px
                x1_actual = x1 * scale
                y1_actual = y1 * scale
                x2_actual = x2 * scale
                y2_actual = y2 * scale
                
                # Compute picked line length in actual image pixels
                picked_len_px = max(1.0, math.hypot(x2_actual - x1_actual, y2_actual - y1_actual))
                
                # Compute mm_per_pixel from object_height_mm
                # Scale image so that the picked line is exactly object_height_mm long
                mm_per_pixel = self.params.object_height_mm / picked_len_px if self.params.object_height_mm > 0 else 0.1
                
                # The picked line length in mm is equal to object_height_mm
                picked_len_mm = self.params.object_height_mm
                
                # Update element geometry to match picked line length
                # This makes the blue line match the actual optical element size
                self._actual_length_mm = picked_len_mm
                self._update_geom()
                
                self._sprite = ComponentSprite(
                    self.params.image_path,
                    self.params.line_px,
                    self.params.object_height_mm,
                    self,
                )
        
        self.setZValue(0)
    
    def boundingRect(self) -> QtCore.QRectF:
        pad = 8
        rect = QtCore.QRectF(-self._len / 2 - pad, -pad, self._len + 2 * pad, 2 * pad)
        # Include sprite in bounds
        return self._bounds_union_sprite(rect)
    
    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.moveTo(self._p1)
        path.lineTo(self._p2)
        s = QtGui.QPainterPathStroker()
        s.setWidth(8)
        shp = s.createStroke(path)
        # Include sprite in shape for hit testing
        return self._shape_union_sprite(shp)
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        # Use purple color for waveplates to distinguish from lenses
        p.setPen(QtGui.QPen(QtGui.QColor("mediumpurple"), 2))
        p.drawLine(self._p1, self._p2)
        p.setBrush(QtGui.QColor("mediumpurple"))
        p.drawEllipse(QtCore.QPointF(0, 0), 2, 2)
    
    def open_editor(self):
        """Open editor dialog for waveplate parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit Waveplate")
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
        ang.setToolTip("Element orientation (0° = horizontal →, 90° = vertical ↑)")
        
        phase = QtWidgets.QDoubleSpinBox()
        phase.setRange(0, 360)
        phase.setDecimals(1)
        phase.setSuffix(" °")
        phase.setValue(self.params.phase_shift_deg)
        phase.setToolTip("Phase shift between fast and slow axes (90° for QWP, 180° for HWP)")
        
        fast_axis = QtWidgets.QDoubleSpinBox()
        fast_axis.setRange(-180, 180)
        fast_axis.setDecimals(2)
        fast_axis.setSuffix(" °")
        fast_axis.setValue(self.params.fast_axis_deg)
        fast_axis.setToolTip("Fast axis angle in lab frame (0° = horizontal, 90° = vertical)")
        
        length = QtWidgets.QDoubleSpinBox()
        length.setRange(1, 1e7)
        length.setDecimals(2)
        length.setSuffix(" mm")
        length.setValue(self.params.object_height_mm)
        
        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Element Angle", ang)
        f.addRow("Phase Shift", phase)
        f.addRow("Fast Axis Angle", fast_axis)
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
            self.params.phase_shift_deg = phase.value()
            self.params.fast_axis_deg = fast_axis.value()
            self.params.object_height_mm = length.value()
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
        self.params = WaveplateParams(**d)
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_geom()
        self._maybe_attach_sprite()
        self.edited.emit()

