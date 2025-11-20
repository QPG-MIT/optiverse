from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional, Tuple, List

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import ComponentParams
from ...core.geometry import user_angle_to_qt, qt_angle_to_user
from ...core.interface_definition import InterfaceDefinition
from ...platform.paths import to_relative_path, to_absolute_path
from ...ui.smart_spinbox import SmartDoubleSpinBox
from ...ui.widgets.interface_properties_widget import InterfacePropertiesWidget
from ..base_obj import BaseObj
from ..component_sprite import create_component_sprite
from ..type_registry import register_type, serialize_item, deserialize_item


@register_type("component", ComponentParams)
class ComponentItem(BaseObj):
    """
    Generic optical component that holds any collection of interfaces.
    
    Each interface behaves independently based on its element_type.
    The component is just a container/grouping mechanism.
    
    Supports any combination of:
    - Lenses (thin lens approximation with focal length)
    - Mirrors (pure reflection)
    - Beamsplitters (partial reflection/transmission)
    - Dichroics (wavelength-dependent)
    - Waveplates (polarization rotation)
    - Refractive interfaces (Snell's law refraction)
    - Beam blocks (ray absorption)
    - Background/decorative items (empty interfaces list)
    
    COORDINATE SYSTEM:
    - Interfaces are stored in InterfaceDefinition objects (Y-up, mm, image-center origin)
    - When displayed, coordinates are transformed from image-center to picked-line-center
    - The picked line offset accounts for centering the sprite on the reference line
    - ComponentSprite handles Y-up to Y-down conversion for Qt display
    """
    
    def __init__(self, params: ComponentParams, item_uuid: str | None = None):
        super().__init__(item_uuid)
        self.params = params
        self._sprite: Optional[ComponentSprite] = None
        self._actual_length_mm: Optional[float] = None
        self._update_geom()
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(user_angle_to_qt(self.params.angle_deg))
        self._maybe_attach_sprite()
        self._ready = True
    
    def _sync_params_from_item(self):
        """Sync params from item position/rotation."""
        self.params.x_mm = float(self.pos().x())
        self.params.y_mm = float(self.pos().y())
        self.params.angle_deg = qt_angle_to_user(self.rotation())
    
    def _update_geom(self):
        """Update geometry based on interfaces."""
        self.prepareGeometryChange()
        
        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        # Compute bounding box from all interfaces
        if self.params.interfaces:
            all_x = []
            all_y = []
            for iface in self.params.interfaces:
                # Apply picked line offset transformation
                # Interfaces are stored relative to image center, but item (0,0) is at picked line center
                all_x.extend([iface.x1_mm - offset_x, iface.x2_mm - offset_x])
                all_y.extend([iface.y1_mm - offset_y, iface.y2_mm - offset_y])
            
            if all_x and all_y:
                min_x = min(all_x)
                max_x = max(all_x)
                min_y = min(all_y)
                max_y = max(all_y)
                
                # Store bounds for rendering
                self._bounds = QtCore.QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
            else:
                # Default bounds
                L = self.params.object_height_mm
                self._bounds = QtCore.QRectF(-L/2, -L/2, L, L)
        else:
            # Default bounds if no interfaces
            L = self.params.object_height_mm
            self._bounds = QtCore.QRectF(-L/2, -L/2, L, L)
    
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
        
        # Use first interface to compute reference line for sprite positioning
        if self.params.image_path and self.params.interfaces and len(self.params.interfaces) > 0:
            first_interface = self.params.interfaces[0]
            
            # Get interface center and length
            cx = 0.5 * (first_interface.x1_mm + first_interface.x2_mm)
            cy = 0.5 * (first_interface.y1_mm + first_interface.y2_mm)
            
            dx = first_interface.x2_mm - first_interface.x1_mm
            dy = first_interface.y2_mm - first_interface.y1_mm
            interface_length = (dx**2 + dy**2)**0.5
            
            # Use the interface itself as the reference line for most element types
            # For refractive objects, we might want perpendicular, but for lens/mirror/BS
            # the interface line IS the optical element
            reference_line_mm = (
                first_interface.x1_mm,
                first_interface.y1_mm,
                first_interface.x2_mm,
                first_interface.y2_mm,
            )
            
            self._sprite = create_component_sprite(
                self.params.image_path,
                reference_line_mm,
                self.params.object_height_mm,
                self,
            )
            self._actual_length_mm = self._sprite.picked_line_length_mm
            
            # Store offset: interfaces are at image center, but item (0,0) is at reference line center
            self._picked_line_offset_mm = (cx, cy)
            
            self._update_geom()
            self.setZValue(0)
        
        elif self.params.image_path and (not self.params.interfaces or len(self.params.interfaces) == 0):
            # Background objects (no interfaces) - use default horizontal reference line
            # This allows tables, breadboards, etc. to display their sprites
            reference_line_mm = (-50.0, 0.0, 50.0, 0.0)  # Horizontal line at center
            
            self._sprite = create_component_sprite(
                self.params.image_path,
                reference_line_mm,
                self.params.object_height_mm,
                self,
            )
            self._actual_length_mm = self._sprite.picked_line_length_mm
            
            # No interface offset for background objects
            self._picked_line_offset_mm = (0.0, 0.0)
            
            self._update_geom()
            self.setZValue(-10)  # Render backgrounds behind optical elements
    
    def boundingRect(self) -> QtCore.QRectF:
        """Return bounding rectangle."""
        rect = self._bounds.adjusted(-8, -8, 8, 8)
        return self._bounds_union_sprite(rect)
    
    def shape(self) -> QtGui.QPainterPath:
        """Return shape for hit testing."""
        path = QtGui.QPainterPath()
        
        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        # Add all interfaces to shape
        for iface in self.params.interfaces:
            # Transform from image-center coords to picked-line-center coords
            p1 = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2 = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            line_path = QtGui.QPainterPath()
            line_path.moveTo(p1)
            line_path.lineTo(p2)
            
            s = QtGui.QPainterPathStroker()
            s.setWidth(10)
            path.addPath(s.createStroke(line_path))
        
        return self._shape_union_sprite(path)
    
    def _get_interface_color(self, element_type: str) -> QtGui.QColor:
        """Get color for interface based on element type."""
        color_map = {
            "lens": QtGui.QColor(50, 120, 220),      # Blue
            "mirror": QtGui.QColor(150, 150, 150),   # Grey
            "beam_splitter": QtGui.QColor(15, 160, 80),  # Green
            "beamsplitter": QtGui.QColor(15, 160, 80),   # Green
            "dichroic": QtGui.QColor(200, 50, 200),  # Magenta
            "waveplate": QtGui.QColor(100, 200, 100),  # Light green
            "polarizing_interface": QtGui.QColor(100, 200, 100),  # Light green
            "refractive_interface": QtGui.QColor(100, 100, 255),  # Light blue
            "beam_block": QtGui.QColor(50, 50, 50),  # Dark grey
        }
        return color_map.get(element_type, QtGui.QColor(150, 100, 255))  # Purple default
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        """Paint all interfaces with appropriate colors."""
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        
        # If no interfaces and no sprite, draw placeholder (for background items)
        if not self.params.interfaces and self._sprite is None:
            pen = QtGui.QPen(QtGui.QColor(150, 150, 150), 2)
            pen.setStyle(QtCore.Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.drawRect(self.boundingRect())
            
            # Draw text
            p.setPen(QtGui.QColor(100, 100, 100))
            font = p.font()
            font.setPointSize(10)
            p.setFont(font)
            p.drawText(self.boundingRect(), QtCore.Qt.AlignmentFlag.AlignCenter, self.params.name or "Background")
            return
        
        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        for iface in self.params.interfaces:
            # Get color based on element type
            color = self._get_interface_color(iface.element_type)
            width = 3
            
            pen = QtGui.QPen(color, width)
            pen.setCosmetic(True)
            p.setPen(pen)
            
            # Transform from image-center coords to picked-line-center coords (item local coords)
            p1 = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2 = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            
            # Check if curved (for lenses with curvature)
            if hasattr(iface, 'is_curved') and iface.is_curved and abs(getattr(iface, 'radius_of_curvature_mm', 0.0)) > 0.1:
                self._draw_curved_surface(p, p1, p2, iface.radius_of_curvature_mm)
            else:
                p.drawLine(p1, p2)
    
    def _draw_curved_surface(self, p: QtGui.QPainter, p1: QtCore.QPointF, p2: QtCore.QPointF, radius_mm: float):
        """Draw a curved surface as an arc."""
        import math
        
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
    
    def get_interfaces_scene(self):
        """
        Get all optical interfaces in scene coordinates.
        
        Each interface retains its element_type and behaves independently.
        
        Returns:
            List of (p1, p2, interface) tuples where p1 and p2 are numpy arrays
            in scene coordinates, and interface is an InterfaceDefinition.
        """
        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        result = []
        for iface in self.params.interfaces:
            # Transform from image-center coords to item local coords
            p1_local = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2_local = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            
            # Transform to scene coordinates
            p1_scene = self.mapToScene(p1_local)
            p2_scene = self.mapToScene(p2_local)
            
            p1 = np.array([p1_scene.x(), p1_scene.y()])
            p2 = np.array([p2_scene.x(), p2_scene.y()])
            result.append((p1, p2, iface))
        
        return result
    
    def open_editor(self):
        """Open editor dialog for component parameters."""
        # Capture initial state for undo
        initial_state = self.capture_state()
        
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle(f"Edit {self.params.name or 'Component'}")
        f = QtWidgets.QFormLayout(d)
        
        # Save initial state for rollback on cancel
        initial_x = self.pos().x()
        initial_y = self.pos().y()
        initial_ang = qt_angle_to_user(self.rotation())
        initial_length = self.params.object_height_mm
        
        # Save initial interface states (deep copy)
        from copy import deepcopy
        initial_interfaces = [deepcopy(iface) for iface in self.params.interfaces] if self.params.interfaces else []
        
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
        ang.setRange(-1e6, 1e6)
        ang.setDecimals(2)
        ang.setSuffix(" °")
        ang.setValue(initial_ang)
        ang.setToolTip("Component angle (0° = right →, 90° = down ↓, 180° = left ←)")
        
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
            user_angle = ang.value()
            self.setRotation(user_angle_to_qt(user_angle))
            self.params.angle_deg = user_angle
            self.edited.emit()
        
        def update_length():
            self.params.object_height_mm = length.value()
            self._update_geom()
            self._maybe_attach_sprite()
            self.edited.emit()
        
        # Update spinboxes when item is modified externally
        def sync_from_item():
            x.blockSignals(True)
            y.blockSignals(True)
            ang.blockSignals(True)
            
            user_angle = qt_angle_to_user(self.rotation())
            
            x.setValue(self.pos().x())
            y.setValue(self.pos().y())
            ang.setValue(user_angle)
            
            x.blockSignals(False)
            y.blockSignals(False)
            ang.blockSignals(False)
        
        x.valueChanged.connect(update_position)
        y.valueChanged.connect(update_position)
        ang.valueChanged.connect(update_angle)
        length.valueChanged.connect(update_length)
        
        self.edited.connect(sync_from_item)
        
        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Angle", ang)
        f.addRow("Size", length)
        
        # Add interface properties section
        if self.params.interfaces:
            separator = QtWidgets.QFrame()
            separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            f.addRow(separator)
            
            interface_widget = InterfacePropertiesWidget(self.params.interfaces)
            interface_widget.propertiesChanged.connect(self.edited.emit)
            f.addRow(interface_widget)
        
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        result = d.exec()
        
        self.edited.disconnect(sync_from_item)
        
        if result:
            # User clicked OK - create undo command for property change
            final_state = self.capture_state()
            if initial_state != final_state:
                from ...core.undo_commands import PropertyChangeCommand
                cmd = PropertyChangeCommand(self, initial_state, final_state)
                self.commandCreated.emit(cmd)
        else:
            # User clicked Cancel - restore initial state
            self.apply_state(initial_state)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return serialize_item(self)
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'ComponentItem':
        """Static factory method: deserialize from dictionary and return new ComponentItem."""
        return deserialize_item(d)

