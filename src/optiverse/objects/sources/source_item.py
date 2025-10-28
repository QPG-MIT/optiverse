from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import SourceParams
from ...core.color_utils import qcolor_from_hex, hex_from_qcolor, wavelength_to_hex, LASER_WAVELENGTHS
from ..base_obj import BaseObj


class SourceItem(BaseObj):
    """
    Optical source element with configurable parameters.
    
    - Aperture size, number of rays, angular spread
    - Custom color via hex picker
    - Full editor dialog
    - Serialization support
    """
    
    def __init__(self, params: SourceParams, item_uuid: str | None = None):
        super().__init__(item_uuid)
        self.params = params
        self._color = qcolor_from_hex(self.params.color_hex)
        self._update_shape()
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._ready = True  # Enable position sync
    
    def _sync_params_from_item(self):
        """Sync params from item position/rotation."""
        self.params.x_mm = float(self.pos().x())
        self.params.y_mm = float(self.pos().y())
        self.params.angle_deg = float(self.rotation())
    
    def _update_shape(self):
        """Update geometry based on aperture size."""
        self.prepareGeometryChange()
        self._half = max(1.0, self.params.size_mm / 2.0)
        
        # Vertical bar representing aperture
        self._bar = QtGui.QPainterPath()
        self._bar.moveTo(0, -self._half)
        self._bar.lineTo(0, self._half)
        
        # Horizontal arrow showing direction
        self._arrow = QtGui.QPainterPath()
        self._arrow.moveTo(0, 0)
        self._arrow.lineTo(18.0, 0.0)
    
    def boundingRect(self) -> QtCore.QRectF:
        r = 22
        return QtCore.QRectF(-r, -self._half - 2, r + 2, self._half + 2)
    
    def shape(self) -> QtGui.QPainterPath:
        s = QtGui.QPainterPathStroker()
        s.setWidth(10)
        return s.createStroke(self._bar).united(self._arrow)
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        pen1 = QtGui.QPen(self._color, 2)
        pen2 = QtGui.QPen(self._color, 1.5)
        p.setPen(pen1)
        p.drawPath(self._bar)
        p.setPen(pen2)
        p.drawPath(self._arrow)
    
    def open_editor(self):
        """Open editor dialog for source parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit Source")
        f = QtWidgets.QFormLayout(d)
        
        # Position and orientation
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
        ang.setToolTip("Optical axis angle - direction rays emit (0° = horizontal →, 90° = vertical ↑)")
        
        # Source parameters
        size = QtWidgets.QDoubleSpinBox()
        size.setRange(0, 1e6)
        size.setDecimals(3)
        size.setSuffix(" mm")
        size.setValue(self.params.size_mm)
        
        nr = QtWidgets.QSpinBox()
        nr.setRange(1, 2001)
        nr.setValue(self.params.n_rays)
        
        rlen = QtWidgets.QDoubleSpinBox()
        rlen.setRange(1, 1e7)
        rlen.setDecimals(1)
        rlen.setSuffix(" mm")
        rlen.setValue(self.params.ray_length_mm)
        
        spr = QtWidgets.QDoubleSpinBox()
        spr.setRange(0, 89.9)
        spr.setDecimals(2)
        spr.setSuffix(" °")
        spr.setValue(self.params.spread_deg)
        
        # Wavelength controls
        wl_mode = QtWidgets.QComboBox()
        wl_mode.addItems(["Custom Color", "Wavelength"])
        wl_mode.setCurrentIndex(1 if self.params.wavelength_nm > 0 else 0)
        
        # Wavelength preset dropdown
        wl_preset = QtWidgets.QComboBox()
        wl_preset.addItem("Custom...", 0.0)
        for name, wl in LASER_WAVELENGTHS.items():
            wl_preset.addItem(name, wl)
        
        # Find current wavelength in presets
        if self.params.wavelength_nm > 0:
            for i in range(wl_preset.count()):
                if abs(wl_preset.itemData(i) - self.params.wavelength_nm) < 0.1:
                    wl_preset.setCurrentIndex(i)
                    break
        
        # Wavelength spinbox
        wl_spin = QtWidgets.QDoubleSpinBox()
        wl_spin.setRange(200, 2000)
        wl_spin.setDecimals(1)
        wl_spin.setSuffix(" nm")
        wl_spin.setValue(self.params.wavelength_nm if self.params.wavelength_nm > 0 else 633.0)
        wl_spin.setEnabled(self.params.wavelength_nm > 0)
        
        # Color picker
        color_btn = QtWidgets.QToolButton()
        color_btn.setText("Pick…")
        color_disp = QtWidgets.QLabel(self.params.color_hex)
        color_btn.setEnabled(self.params.wavelength_nm == 0)
        color_disp.setEnabled(self.params.wavelength_nm == 0)
        
        def paint_chip(lbl: QtWidgets.QLabel, hexstr: str):
            pm = QtGui.QPixmap(40, 16)
            pm.fill(QtCore.Qt.GlobalColor.transparent)
            painter = QtGui.QPainter(pm)
            painter.fillRect(0, 0, 40, 16, qcolor_from_hex(hexstr))
            painter.end()
            lbl.setPixmap(pm)
        
        chip = QtWidgets.QLabel()
        if self.params.wavelength_nm > 0:
            paint_chip(chip, wavelength_to_hex(self.params.wavelength_nm))
        else:
            paint_chip(chip, self.params.color_hex)
        
        def pick_color():
            c = QtWidgets.QColorDialog.getColor(
                self._color,
                d,
                "Choose Ray Color",
                QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog,
            )
            if c.isValid():
                self._color = c
                color_disp.setText(c.name())
                paint_chip(chip, c.name())
        
        def update_from_wavelength():
            """Update color chip from wavelength."""
            wl = wl_spin.value()
            paint_chip(chip, wavelength_to_hex(wl))
        
        def on_mode_changed(mode: str):
            """Handle wavelength mode change."""
            use_wl = (mode == "Wavelength")
            wl_preset.setEnabled(use_wl)
            wl_spin.setEnabled(use_wl)
            color_btn.setEnabled(not use_wl)
            color_disp.setEnabled(not use_wl)
            if use_wl:
                update_from_wavelength()
            else:
                paint_chip(chip, color_disp.text())
        
        def on_preset_changed(idx: int):
            """Handle wavelength preset selection."""
            wl = wl_preset.itemData(idx)
            if wl > 0:
                wl_spin.setValue(wl)
                update_from_wavelength()
        
        wl_mode.currentTextChanged.connect(on_mode_changed)
        wl_preset.currentIndexChanged.connect(on_preset_changed)
        wl_spin.valueChanged.connect(lambda: update_from_wavelength())
        
        row_color = QtWidgets.QHBoxLayout()
        row_color.addWidget(color_btn)
        row_color.addWidget(color_disp)
        row_color.addWidget(chip)
        row_color.addStretch(1)
        color_btn.clicked.connect(pick_color)
        
        # Polarization controls
        pol_type = QtWidgets.QComboBox()
        pol_type.addItems([
            "horizontal",
            "vertical",
            "+45",
            "-45",
            "circular_right",
            "circular_left",
            "linear",
        ])
        # Set current value
        try:
            idx = pol_type.findText(self.params.polarization_type)
            if idx >= 0:
                pol_type.setCurrentIndex(idx)
        except:
            pass
        
        pol_angle = QtWidgets.QDoubleSpinBox()
        pol_angle.setRange(-180, 180)
        pol_angle.setDecimals(1)
        pol_angle.setSuffix(" °")
        pol_angle.setValue(self.params.polarization_angle_deg)
        pol_angle.setEnabled(self.params.polarization_type == "linear")
        
        # Enable angle control only when "linear" is selected
        def on_pol_type_changed(text):
            pol_angle.setEnabled(text == "linear")
        pol_type.currentTextChanged.connect(on_pol_type_changed)
        
        # Add all fields to form
        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Optical Axis Angle", ang)
        f.addRow("Aperture size", size)
        f.addRow("# Rays", nr)
        f.addRow("Ray length", rlen)
        f.addRow("Angular spread (±)", spr)
        f.addRow("Color Mode", wl_mode)
        f.addRow("Wavelength Preset", wl_preset)
        f.addRow("Wavelength", wl_spin)
        f.addRow("Custom Color", row_color)
        f.addRow("Polarization", pol_type)
        f.addRow("Polarization angle", pol_angle)
        
        # Buttons
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        # Apply changes if accepted
        if d.exec():
            self.setPos(x.value(), y.value())
            self.params.x_mm = x.value()
            self.params.y_mm = y.value()
            self.setRotation(ang.value())
            self.params.angle_deg = ang.value()
            self.params.size_mm = size.value()
            self.params.n_rays = nr.value()
            self.params.ray_length_mm = rlen.value()
            self.params.spread_deg = spr.value()
            
            # Save wavelength or custom color based on mode
            if wl_mode.currentText() == "Wavelength":
                self.params.wavelength_nm = wl_spin.value()
                self.params.color_hex = wavelength_to_hex(self.params.wavelength_nm)
                self._color = qcolor_from_hex(self.params.color_hex)
            else:
                self.params.wavelength_nm = 0.0
                self.params.color_hex = hex_from_qcolor(self._color)
            
            # Polarization parameters
            self.params.polarization_type = pol_type.currentText()
            self.params.polarization_angle_deg = pol_angle.value()
            self._update_shape()
            self.edited.emit()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        d = asdict(self.params)
        # Force live pose + color
        d["x_mm"] = float(self.pos().x())
        d["y_mm"] = float(self.pos().y())
        d["angle_deg"] = float(self.rotation())
        d["color_hex"] = hex_from_qcolor(self._color)
        d["item_uuid"] = self.item_uuid
        return d
    
    def from_dict(self, d: Dict[str, Any]):
        """Deserialize from dictionary."""
        # Restore UUID if present
        if "item_uuid" in d:
            self.item_uuid = d["item_uuid"]
        self.params = SourceParams(**d)
        self._color = qcolor_from_hex(self.params.color_hex)
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_shape()
        self.edited.emit()
