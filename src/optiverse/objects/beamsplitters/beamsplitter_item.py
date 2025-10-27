from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import BeamsplitterParams
from ..base_obj import BaseObj
from ..component_sprite import ComponentSprite


class BeamsplitterItem(BaseObj):
    """
    Beamsplitter element with transmission/reflection ratios and optional component sprite.
    """
    
    def __init__(self, params: BeamsplitterParams):
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
        p.setPen(QtGui.QPen(QtGui.QColor(0, 150, 120), 3))
        p.drawLine(self._p1, self._p2)
    
    def open_editor(self):
        """Open editor dialog for beamsplitter parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit Beamsplitter")
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
        ang.setToolTip("Optical axis angle (0° = horizontal →, 90° = vertical ↑)")
        
        length = QtWidgets.QDoubleSpinBox()
        length.setRange(1, 1e7)
        length.setDecimals(2)
        length.setSuffix(" mm")
        length.setValue(self.params.object_height_mm)
        
        t = QtWidgets.QDoubleSpinBox()
        t.setRange(0, 100)
        t.setDecimals(1)
        t.setSuffix(" %")
        t.setValue(self.params.split_T)
        
        r = QtWidgets.QDoubleSpinBox()
        r.setRange(0, 100)
        r.setDecimals(1)
        r.setSuffix(" %")
        r.setValue(self.params.split_R)
        
        # Sync T and R values
        def sync_from_t(val):
            r.blockSignals(True)
            r.setValue(max(0.0, min(100.0, 100.0 - val)))
            r.blockSignals(False)
        
        def sync_from_r(val):
            t.blockSignals(True)
            t.setValue(max(0.0, min(100.0, 100.0 - val)))
            t.blockSignals(False)
        
        t.valueChanged.connect(sync_from_t)
        r.valueChanged.connect(sync_from_r)
        
        # Polarization controls
        is_pbs = QtWidgets.QCheckBox("Polarizing Beam Splitter (PBS)")
        is_pbs.setChecked(self.params.is_polarizing)
        
        pbs_axis = QtWidgets.QDoubleSpinBox()
        pbs_axis.setRange(-180, 180)
        pbs_axis.setDecimals(1)
        pbs_axis.setSuffix(" °")
        pbs_axis.setValue(self.params.pbs_transmission_axis_deg)
        pbs_axis.setEnabled(self.params.is_polarizing)
        pbs_axis.setToolTip("ABSOLUTE angle of transmission axis in lab frame\n"
                           "(0° = horizontal, 90° = vertical)\n"
                           "p-polarization (parallel) transmits, s-polarization (perpendicular) reflects")
        
        # Enable/disable T/R controls and PBS axis based on PBS mode
        def on_pbs_toggled(checked):
            t.setEnabled(not checked)
            r.setEnabled(not checked)
            pbs_axis.setEnabled(checked)
        is_pbs.toggled.connect(on_pbs_toggled)
        
        # Disable T/R controls if PBS mode is active
        if self.params.is_polarizing:
            t.setEnabled(False)
            r.setEnabled(False)
        
        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Optical Axis Angle", ang)
        f.addRow("Length", length)
        f.addRow("Split T", t)
        f.addRow("Split R", r)
        f.addRow("", is_pbs)
        f.addRow("PBS transmission axis", pbs_axis)
        
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
            self.params.object_height_mm = length.value()
            self.params.split_T = t.value()
            self.params.split_R = r.value()
            # Polarization parameters
            self.params.is_polarizing = is_pbs.isChecked()
            self.params.pbs_transmission_axis_deg = pbs_axis.value()
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
        self.params = BeamsplitterParams(**d)
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_geom()
        self._maybe_attach_sprite()
        self.edited.emit()
