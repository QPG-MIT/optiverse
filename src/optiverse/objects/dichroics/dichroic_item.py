from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import DichroicParams
from ...platform.paths import to_relative_path, to_absolute_path
from ...ui.smart_spinbox import SmartDoubleSpinBox
from ..base_obj import BaseObj
from ..component_sprite import create_component_sprite


class DichroicItem(BaseObj):
    """
    Dichroic mirror element with wavelength-dependent reflection/transmission.
    
    Dichroic mirrors selectively reflect short wavelengths and transmit long wavelengths
    (or vice versa) based on a cutoff wavelength. The transition is smooth with a
    characteristic width.
    """
    
    def __init__(self, params: DichroicParams, item_uuid: str | None = None):
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
        
        # Calculate picked line offset for coordinate transformation
        self._picked_line_offset_mm = (0.0, 0.0)  # Default: no offset
        
        if self.params.image_path:
            # Check if component has a reference line from interface definition
            # This allows proper sprite orientation for components from the registry
            if hasattr(self.params, '_reference_line_mm'):
                reference_line_mm = self.params._reference_line_mm
            else:
                # For simple items without explicit interfaces, use a horizontal line
                # across the center of the image as the reference line
                # This represents the optical axis
                half_width = self.params.object_height_mm / 2.0
                reference_line_mm = (-half_width, 0.0, half_width, 0.0)
            
            self._sprite = create_component_sprite(
                self.params.image_path,
                reference_line_mm,
                self.params.object_height_mm,
                self,
            )
            
            # Update element geometry to match the reference line length
            self._actual_length_mm = self._sprite.picked_line_length_mm
            self._update_geom()
            
            # Calculate offset from image center to reference line center
            # ComponentSprite centers the component on the reference line, but interfaces
            # are stored relative to image center. We need to account for this offset.
            # Reference line center in mm (centered coordinate system)
            cx_mm = 0.5 * (reference_line_mm[0] + reference_line_mm[2])
            cy_mm = 0.5 * (reference_line_mm[1] + reference_line_mm[3])
            
            # Store offset: interfaces are at image center, but item (0,0) is at reference line center
            self._picked_line_offset_mm = (cx_mm, cy_mm)
        
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
        s.setWidth(10)
        shp = s.createStroke(path)
        # Include sprite in shape for hit testing
        return self._shape_union_sprite(shp)
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        """Paint optical interfaces."""
        if not hasattr(self.params, 'interfaces') or not self.params.interfaces:
            return
        
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        
        # Get offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        for iface in self.params.interfaces:
            # Draw interface line
            color = QtGui.QColor(100, 100, 255)  # Blue
            pen = QtGui.QPen(color, 2)
            pen.setCosmetic(True)
            p.setPen(pen)
            
            # Transform coordinates
            p1 = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2 = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            
            p.drawLine(p1, p2)
    
    def open_editor(self):
        """Open editor dialog for dichroic mirror parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit Dichroic Mirror")
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
        ang.setRange(0, 360)
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
        
        # Update spinboxes when item is modified externally (e.g., Ctrl+drag rotation)
        def sync_from_item():
            # Block signals to prevent recursive updates
            x.blockSignals(True)
            y.blockSignals(True)
            ang.blockSignals(True)
            
            # Normalize angle to 0 to 360 range
            angle = self.rotation() % 360
            if angle < 0:
                angle += 360
            
            x.setValue(self.pos().x())
            y.setValue(self.pos().y())
            ang.setValue(angle)
            
            x.blockSignals(False)
            y.blockSignals(False)
            ang.blockSignals(False)
        
        x.valueChanged.connect(update_position)
        y.valueChanged.connect(update_position)
        ang.valueChanged.connect(update_angle)
        length.valueChanged.connect(update_length)
        
        # Connect to item's edited signal to sync spinboxes
        self.edited.connect(sync_from_item)
        
        cutoff = QtWidgets.QDoubleSpinBox()
        cutoff.setRange(200, 2000)
        cutoff.setDecimals(1)
        cutoff.setSuffix(" nm")
        cutoff.setValue(self.params.cutoff_wavelength_nm)
        
        transition = QtWidgets.QDoubleSpinBox()
        transition.setRange(1, 200)
        transition.setDecimals(1)
        transition.setSuffix(" nm")
        transition.setValue(self.params.transition_width_nm)
        transition.setToolTip("Width of transition region between reflection and transmission")
        
        pass_type = QtWidgets.QComboBox()
        pass_type.addItems(["longpass", "shortpass"])
        # Set current value
        current_pass_type = getattr(self.params, "pass_type", "longpass")
        idx = pass_type.findText(current_pass_type)
        if idx >= 0:
            pass_type.setCurrentIndex(idx)
        
        # Update cutoff tooltip based on pass type
        def update_cutoff_tooltip(text):
            if text == "longpass":
                cutoff.setToolTip("Wavelengths below this reflect, above this transmit")
            else:  # shortpass
                cutoff.setToolTip("Wavelengths above this reflect, below this transmit")
        
        # Set initial tooltip
        update_cutoff_tooltip(pass_type.currentText())
        pass_type.currentTextChanged.connect(update_cutoff_tooltip)
        
        # Lock checkbox
        lock_cb = QtWidgets.QCheckBox("Lock position/rotation/deletion")
        lock_cb.setChecked(self.is_locked())
        lock_cb.toggled.connect(self.set_locked)
        f.addRow("", lock_cb)
        
        # Add separator
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        f.addRow(separator)
        
        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Optical Axis Angle", ang)
        f.addRow("Length", length)
        f.addRow("Pass Type", pass_type)
        f.addRow("Cutoff Wavelength", cutoff)
        f.addRow("Transition Width", transition)
        
        # Add info label
        info = QtWidgets.QLabel(
            "Dichroic mirrors selectively reflect or transmit based on wavelength.\n"
            "Long pass: reflects short wavelengths, transmits long wavelengths.\n"
            "Short pass: reflects long wavelengths, transmits short wavelengths."
        )
        info.setWordWrap(True)
        # Adapt color to theme
        palette = d.palette()
        is_dark = palette.color(QtGui.QPalette.ColorRole.Window).lightness() < 128
        info.setStyleSheet(f"color: {'#888' if is_dark else '#666'}; font-size: 10px;")
        f.addRow("", info)
        
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        # Execute dialog and rollback if cancelled
        result = d.exec()
        
        # Disconnect the sync signal to prevent memory leaks
        self.edited.disconnect(sync_from_item)
        
        if result:
            # Save dichroic parameters (x, y, angle, length already applied live)
            self.params.cutoff_wavelength_nm = cutoff.value()
            self.params.transition_width_nm = transition.value()
            self.params.pass_type = pass_type.currentText()
            self.edited.emit()
        else:
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
    
    def get_interfaces_scene(self):
        """
        Get all optical interfaces in scene coordinates.
        
        Uses the exact same coordinate transformation as paint() to ensure
        perfect alignment between what you see and what interacts with rays.
        
        Returns:
            List of (p1, p2, interface) tuples where p1 and p2 are numpy arrays
            in scene coordinates, and interface is an InterfaceDefinition.
        """
        from ...core.interface_definition import InterfaceDefinition
        
        # Check if interfaces field exists and has content
        interfaces = getattr(self.params, 'interfaces', None)
        if not interfaces or len(interfaces) == 0:
            # Create default interface from current geometry
            p1, p2 = self.endpoints_scene()
            
            default_interface = InterfaceDefinition(
                x1_mm=0.0,  # Will be transformed by scene coordinates
                y1_mm=0.0,
                x2_mm=0.0,
                y2_mm=0.0,
                element_type="dichroic",
                cutoff_wavelength_nm=self.params.cutoff_wavelength_nm,
                transition_width_nm=self.params.transition_width_nm,
                pass_type=self.params.pass_type
            )
            return [(p1, p2, default_interface)]
        
        # Get offset for coordinate transformation (same as paint())
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        result = []
        for iface in interfaces:
            # Transform from image-center coords to item local coords (same as paint())
            p1_local = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2_local = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            
            # Transform to scene coordinates
            p1_scene = self.mapToScene(p1_local)
            p2_scene = self.mapToScene(p2_local)
            
            p1 = np.array([p1_scene.x(), p1_scene.y()])
            p2 = np.array([p2_scene.x(), p2_scene.y()])
            result.append((p1, p2, iface))
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        d = asdict(self.params)
        d["x_mm"] = float(self.pos().x())
        d["y_mm"] = float(self.pos().y())
        d["angle_deg"] = float(self.rotation())
        d["item_uuid"] = self.item_uuid
        d["locked"] = self._locked  # Save lock state
        d["z_value"] = float(self.zValue())  # Save z-order
        # Convert image path to relative if within package
        if "image_path" in d:
            d["image_path"] = to_relative_path(d["image_path"])
        return d
    
    def from_dict(self, d: Dict[str, Any]):
        """Deserialize from dictionary."""
        if "item_uuid" in d:
            self.item_uuid = d["item_uuid"]
        # Restore locked state (call parent's from_dict)
        super().from_dict(d)
        # Convert relative image path to absolute
        if "image_path" in d:
            d["image_path"] = to_absolute_path(d["image_path"])
        self.params = DichroicParams(**d)
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_geom()
        self._maybe_attach_sprite()
        self.edited.emit()

