from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import MirrorParams
from ...platform.paths import to_relative_path, to_absolute_path
from ...ui.smart_spinbox import SmartDoubleSpinBox
from ..base_obj import BaseObj
from ..component_sprite import ComponentSprite


class MirrorItem(BaseObj):
    """
    Mirror element with optional component sprite.
    """
    
    def __init__(self, params: MirrorParams, item_uuid: str | None = None):
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
        
        # Check if mirror has interfaces - if so, calculate geometry from first interface
        interfaces = getattr(self.params, 'interfaces', None)
        if interfaces and len(interfaces) > 0:
            # Use first interface to calculate length and offset
            first_iface = interfaces[0]
            
            # Calculate offset from image center to interface center
            cx_mm = 0.5 * (first_iface.x1_mm + first_iface.x2_mm)
            cy_mm = 0.5 * (first_iface.y1_mm + first_iface.y2_mm)
            self._picked_line_offset_mm = (cx_mm, cy_mm)
            
            # Calculate interface length
            dx = first_iface.x2_mm - first_iface.x1_mm
            dy = first_iface.y2_mm - first_iface.y1_mm
            interface_length = np.sqrt(dx*dx + dy*dy)
            
            # Set _p1/_p2 as HORIZONTAL in item-local space with the correct length
            # The item's rotation (setRotation) will orient it correctly
            # This ensures _p1/_p2 match the interface length but in item-local coordinates
            self.prepareGeometryChange()
            self._p1 = QtCore.QPointF(-interface_length / 2, 0)
            self._p2 = QtCore.QPointF(interface_length / 2, 0)
            self._len = interface_length
            self._actual_length_mm = interface_length
        
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
            
            # If we didn't set geometry from interfaces, update it from sprite
            if not (interfaces and len(interfaces) > 0):
                self._actual_length_mm = self._sprite.picked_line_length_mm
                self._update_geom()
                
                # Calculate offset from image center to reference line center
                cx_mm = 0.5 * (reference_line_mm[0] + reference_line_mm[2])
                cy_mm = 0.5 * (reference_line_mm[1] + reference_line_mm[3])
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
            color = QtGui.QColor(150, 150, 150)  # Grey
            pen = QtGui.QPen(color, 4)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.drawLine(self._p1, self._p2)
            return
        
        # Get offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        for iface in self.params.interfaces:
            # Draw interface line
            color = QtGui.QColor(150, 150, 150)  # Grey
            pen = QtGui.QPen(color, 4)
            pen.setCosmetic(True)
            p.setPen(pen)
            
            # Transform coordinates
            p1 = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2 = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            
            # Check if curved
            if iface.is_curved and abs(iface.radius_of_curvature_mm) > 0.1:
                self._draw_curved_surface(p, p1, p2, iface.radius_of_curvature_mm)
            else:
                p.drawLine(p1, p2)
    
    def _draw_curved_surface(self, p: QtGui.QPainter, p1: QtCore.QPointF, p2: QtCore.QPointF, radius_mm: float):
        """
        Draw a curved mirror surface as an arc.
        
        Args:
            p: QPainter
            p1, p2: Endpoints in local item coordinates
            radius_mm: Radius of curvature (positive or negative)
        """
        import math
        
        # Calculate the center of the arc
        # Midpoint
        mid_x = (p1.x() + p2.x()) / 2.0
        mid_y = (p1.y() + p2.y()) / 2.0
        
        # Chord vector
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        chord_length = math.sqrt(dx*dx + dy*dy)
        
        if chord_length < 0.01:
            p.drawLine(p1, p2)
            return
        
        # Perpendicular to chord
        perp_x = -dy / chord_length
        perp_y = dx / chord_length
        
        # Distance from midpoint to center
        r = abs(radius_mm)
        half_chord = chord_length / 2.0
        
        if r < half_chord:
            # Radius too small, draw straight line
            p.drawLine(p1, p2)
            return
        
        d = math.sqrt(r*r - half_chord*half_chord)
        
        # Center position (direction depends on sign of radius)
        if radius_mm > 0:
            center_x = mid_x + d * perp_x
            center_y = mid_y + d * perp_y
        else:
            center_x = mid_x - d * perp_x
            center_y = mid_y - d * perp_y
        
        # Calculate angles
        angle1 = math.atan2(p1.y() - center_y, p1.x() - center_x) * 180.0 / math.pi
        angle2 = math.atan2(p2.y() - center_y, p2.x() - center_x) * 180.0 / math.pi
        
        # Span angle (always draw shorter arc)
        span = angle2 - angle1
        if span > 180:
            span -= 360
        elif span < -180:
            span += 360
        
        # Draw arc
        rect = QtCore.QRectF(center_x - r, center_y - r, 2*r, 2*r)
        p.drawArc(rect, int(angle1 * 16), int(span * 16))  # Qt uses 1/16th degree units
    
    def open_editor(self):
        """Open editor dialog for mirror parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit Mirror")
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
        
        if not result:
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
                element_type="mirror",
                reflectivity=99.0
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
        self.params = MirrorParams(**d)
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_geom()
        self._maybe_attach_sprite()
        self.edited.emit()
