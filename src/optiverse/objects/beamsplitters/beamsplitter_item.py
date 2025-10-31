from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import BeamsplitterParams
from ...platform.paths import to_relative_path, to_absolute_path
from ...ui.smart_spinbox import SmartDoubleSpinBox
from ..base_obj import BaseObj
from ..component_sprite import ComponentSprite


class BeamsplitterItem(BaseObj):
    """
    Beamsplitter element with transmission/reflection ratios and optional component sprite.
    """
    
    def __init__(self, params: BeamsplitterParams, item_uuid: str | None = None):
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
            
            self._sprite = ComponentSprite(
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
        """Paint optical interfaces."""
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        
        if not hasattr(self.params, 'interfaces') or not self.params.interfaces:
            # Draw default line when no interfaces defined (backward compatibility)
            color = QtGui.QColor(15, 160, 80)  # Green (darker)
            pen = QtGui.QPen(color, 4)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.drawLine(self._p1, self._p2)
            return
        
        # Get offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        for iface in self.params.interfaces:
            # Draw interface line
            color = QtGui.QColor(15, 160, 80)  # Green (darker)
            pen = QtGui.QPen(color, 4)
            pen.setCosmetic(True)
            p.setPen(pen)
            
            # Transform coordinates
            p1 = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2 = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            
            p.drawLine(p1, p2)
    
    def open_editor(self):
        """Open editor dialog for beamsplitter parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit Beamsplitter")
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
        
        # Live update connections for x, y, ang, length
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
        
        # Execute dialog and rollback if cancelled
        result = d.exec()
        
        # Disconnect the sync signal to prevent memory leaks
        self.edited.disconnect(sync_from_item)
        
        if result:
            # Save T/R and PBS settings (x, y, angle, length already applied live)
            self.params.split_T = t.value()
            self.params.split_R = r.value()
            self.params.is_polarizing = is_pbs.isChecked()
            self.params.pbs_transmission_axis_deg = pbs_axis.value()
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
                element_type="beam_splitter",
                split_T=self.params.split_T,
                split_R=self.params.split_R,
                is_polarizing=self.params.is_polarizing,
                pbs_transmission_axis_deg=self.params.pbs_transmission_axis_deg
            )
            return [(p1, p2, default_interface)]
        
        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        result = []
        for iface in interfaces:
            # Transform from image-center coords to picked-line-center coords (item local coords)
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
        self.params = BeamsplitterParams(**d)
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_geom()
        self._maybe_attach_sprite()
        self.edited.emit()
