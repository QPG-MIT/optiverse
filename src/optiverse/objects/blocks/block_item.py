from __future__ import annotations
from typing import Dict, Any, Optional, Tuple, List

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import BlockParams
from ...core.geometry import user_angle_to_qt, qt_angle_to_user
from ...ui.smart_spinbox import SmartDoubleSpinBox
from ...ui.widgets.interface_properties_widget import InterfacePropertiesWidget
from ..base_obj import BaseObj
from ..component_sprite import create_component_sprite
from ..type_registry import register_type, serialize_item, deserialize_item


@register_type("block", BlockParams)
class BlockItem(BaseObj):
    """
    Beam Block element: absorbs rays. Visually a thick black line.
    """
    
    def __init__(self, params: BlockParams, item_uuid: str | None = None):
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
        self.params.x_mm = float(self.pos().x())
        self.params.y_mm = float(self.pos().y())
        self.params.angle_deg = qt_angle_to_user(self.rotation())
    
    def _update_geom(self):
        self.prepareGeometryChange()
        L = max(1.0, self._actual_length_mm if self._actual_length_mm is not None else self.params.object_height_mm)
        self._p1 = QtCore.QPointF(-L / 2, 0)
        self._p2 = QtCore.QPointF(+L / 2, 0)
        self._len = L
    
    def _maybe_attach_sprite(self):
        if getattr(self, "_sprite", None):
            try:
                if self.scene():
                    self.scene().removeItem(self._sprite)
            except Exception:
                pass
            self._sprite = None
        
        self._picked_line_offset_mm = (0.0, 0.0)
        interfaces = getattr(self.params, 'interfaces', None)
        if interfaces and len(interfaces) > 0:
            first_iface = interfaces[0]
            cx_mm = 0.5 * (first_iface.x1_mm + first_iface.x2_mm)
            cy_mm = 0.5 * (first_iface.y1_mm + first_iface.y2_mm)
            self._picked_line_offset_mm = (cx_mm, cy_mm)
            dx = first_iface.x2_mm - first_iface.x1_mm
            dy = first_iface.y2_mm - first_iface.y1_mm
            interface_length = float(np.hypot(dx, dy))
            self.prepareGeometryChange()
            self._p1 = QtCore.QPointF(-interface_length / 2, 0)
            self._p2 = QtCore.QPointF(interface_length / 2, 0)
            self._len = interface_length
            self._actual_length_mm = interface_length
        
        if self.params.image_path:
            if hasattr(self.params, '_reference_line_mm'):
                reference_line_mm = self.params._reference_line_mm
            else:
                half_width = self.params.object_height_mm / 2.0
                reference_line_mm = (-half_width, 0.0, half_width, 0.0)
            
            self._sprite = create_component_sprite(
                self.params.image_path,
                reference_line_mm,
                self.params.object_height_mm,
                self,
            )
            if not (interfaces and len(interfaces) > 0):
                self._actual_length_mm = self._sprite.picked_line_length_mm
                self._update_geom()
                cx_mm = 0.5 * (reference_line_mm[0] + reference_line_mm[2])
                cy_mm = 0.5 * (reference_line_mm[1] + reference_line_mm[3])
                self._picked_line_offset_mm = (cx_mm, cy_mm)
        
        self.setZValue(0)
    
    def boundingRect(self) -> QtCore.QRectF:
        pad = 8
        rect = QtCore.QRectF(-self._len / 2 - pad, -pad, self._len + 2 * pad, 2 * pad)
        return self._bounds_union_sprite(rect)
    
    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.moveTo(self._p1)
        path.lineTo(self._p2)
        s = QtGui.QPainterPathStroker()
        s.setWidth(12)
        shp = s.createStroke(path)
        return self._shape_union_sprite(shp)
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        color = QtGui.QColor(20, 20, 20)
        pen = QtGui.QPen(color, 6)
        pen.setCosmetic(True)
        p.setPen(pen)
        
        interfaces = getattr(self.params, 'interfaces', None)
        if not interfaces or len(interfaces) == 0:
            p.drawLine(self._p1, self._p2)
            return
        
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        for iface in interfaces:
            p1 = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2 = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            p.drawLine(p1, p2)
    
    def open_editor(self):
        """Open editor dialog for beam block parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit Beam Block")
        f = QtWidgets.QFormLayout(d)
        
        # Save initial state for rollback on cancel
        initial_x = self.pos().x()
        initial_y = self.pos().y()
        # Convert Qt angle to user angle (CW from up)
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
        ang.setRange(0, 360)
        ang.setDecimals(2)
        ang.setSuffix(" °")
        ang.setValue(initial_ang)
        ang.setToolTip("Block angle (0° = right →, 90° = down ↓, 180° = left ←)")
        
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
        
        # Update spinboxes when item is modified externally (e.g., Ctrl+drag rotation)
        def sync_from_item():
            # Block signals to prevent recursive updates
            x.blockSignals(True)
            y.blockSignals(True)
            ang.blockSignals(True)
            
            # Convert Qt angle to user angle
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
        
        # Connect to item's edited signal to sync spinboxes
        self.edited.connect(sync_from_item)
        
        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Angle", ang)
        f.addRow("Length", length)
        
        # Add interface properties section
        if self.params.interfaces:
            # Add separator before interfaces
            separator2 = QtWidgets.QFrame()
            separator2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            f.addRow(separator2)
            
            # Add interface properties widget
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
        
        # Execute dialog and rollback if cancelled
        result = d.exec()
        
        # Disconnect the sync signal to prevent memory leaks
        self.edited.disconnect(sync_from_item)
        
        if not result:
            # User clicked Cancel - restore initial values
            self.setPos(initial_x, initial_y)
            self.params.x_mm = initial_x
            self.params.y_mm = initial_y
            self.setRotation(user_angle_to_qt(initial_ang))
            self.params.angle_deg = initial_ang
            self.params.object_height_mm = initial_length
            
            # Restore initial interface states
            if initial_interfaces:
                self.params.interfaces = initial_interfaces
            
            self._update_geom()
            self._maybe_attach_sprite()
            self.edited.emit()
    
    def endpoints_scene(self) -> Tuple[np.ndarray, np.ndarray]:
        p1 = self.mapToScene(self._p1)
        p2 = self.mapToScene(self._p2)
        return np.array([p1.x(), p1.y()]), np.array([p2.x(), p2.y()])
    
    def get_interfaces_scene(self):
        from ...core.interface_definition import InterfaceDefinition
        interfaces = getattr(self.params, 'interfaces', None)
        if not interfaces or len(interfaces) == 0:
            p1, p2 = self.endpoints_scene()
            default_interface = InterfaceDefinition(
                x1_mm=0.0,
                y1_mm=0.0,
                x2_mm=0.0,
                y2_mm=0.0,
                element_type="beam_block",
            )
            return [(p1, p2, default_interface)]
        
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        result: List[Tuple[np.ndarray, np.ndarray, Any]] = []  # type: ignore[name-defined]
        for iface in interfaces:
            p1_local = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2_local = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            p1_scene = self.mapToScene(p1_local)
            p2_scene = self.mapToScene(p2_local)
            p1 = np.array([p1_scene.x(), p1_scene.y()])
            p2 = np.array([p2_scene.x(), p2_scene.y()])
            result.append((p1, p2, iface))
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return serialize_item(self)
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'BlockItem':
        """Static factory method: deserialize from dictionary and return new BlockItem."""
        return deserialize_item(d)


