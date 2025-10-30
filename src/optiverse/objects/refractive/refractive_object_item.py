from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, Optional, Tuple, List

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import RefractiveObjectParams, RefractiveInterface
from ...platform.paths import to_relative_path, to_absolute_path
from ...ui.smart_spinbox import SmartDoubleSpinBox
from ..base_obj import BaseObj
from ..component_sprite import ComponentSprite


class RefractiveObjectItem(BaseObj):
    """
    Refractive object with multiple optical interfaces.
    
    This represents complex optical components like beam splitter cubes, prisms,
    or any component with multiple refracting surfaces. Each interface handles
    refraction according to Snell's law and partial reflection via Fresnel equations.
    """
    
    def __init__(self, params: RefractiveObjectParams, item_uuid: str | None = None):
        super().__init__(item_uuid)
        self.params = params
        self._sprite: Optional[ComponentSprite] = None
        self._actual_length_mm: Optional[float] = None
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
        
        if self.params.image_path and self.params.line_px:
            self._sprite = ComponentSprite(
                self.params.image_path,
                self.params.line_px,
                self.params.object_height_mm,
                self,
            )
            self._actual_length_mm = self._sprite.picked_line_length_mm
            
            # Calculate offset from image center to picked line center
            # ComponentSprite centers the component on the picked line, but interfaces
            # are stored relative to image center. We need to account for this offset.
            import os
            from PyQt6 import QtGui
            if os.path.exists(self.params.image_path):
                pix = QtGui.QPixmap(self.params.image_path)
                actual_height = pix.height()
                actual_width = pix.width()
                
                if actual_height > 0:
                    # Denormalize line_px from 1000px space to actual image space
                    scale = float(actual_height) / 1000.0
                    x1_actual = self.params.line_px[0] * scale
                    y1_actual = self.params.line_px[1] * scale
                    x2_actual = self.params.line_px[2] * scale
                    y2_actual = self.params.line_px[3] * scale
                    
                    # Picked line center in image pixel coords (top-left origin)
                    cx_px = 0.5 * (x1_actual + x2_actual)
                    cy_px = 0.5 * (y1_actual + y2_actual)
                    
                    # Convert to centered coordinate system (image center origin)
                    mm_per_px = self.params.object_height_mm / actual_height
                    x_picked_mm = (cx_px - actual_width / 2) * mm_per_px
                    y_picked_mm = (cy_px - actual_height / 2) * mm_per_px
                    
                    # Store offset: interfaces are at image center, but item (0,0) is at picked line center
                    self._picked_line_offset_mm = (x_picked_mm, y_picked_mm)
            
            self._update_geom()
        
        self.setZValue(0)
    
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
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        """Paint all interfaces."""
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        
        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        for iface in self.params.interfaces:
            # Color coding by interface type
            if iface.is_beam_splitter:
                color = QtGui.QColor(0, 150, 120)  # Teal for beam splitter
                width = 3
            elif iface.n1 != iface.n2:
                color = QtGui.QColor(100, 100, 255)  # Blue for refractive interface
                width = 2
            else:
                color = QtGui.QColor(150, 150, 150)  # Gray for same index
                width = 1
            
            p.setPen(QtGui.QPen(color, width))
            
            # Transform from image-center coords to picked-line-center coords
            # Interfaces are stored relative to image center, but item (0,0) is at picked line center
            p1 = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
            p2 = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
            p.drawLine(p1, p2)
            
            # Draw small normal indicator
            mid = (p1 + p2) / 2
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            length = np.sqrt(dx*dx + dy*dy)
            if length > 1e-6:
                # Normal direction
                nx = -dy / length
                ny = dx / length
                normal_len = 5.0
                p.setPen(QtGui.QPen(color, 1, QtCore.Qt.PenStyle.DashLine))
                p.drawLine(mid, mid + QtCore.QPointF(nx * normal_len, ny * normal_len))
    
    def open_editor(self):
        """Open editor dialog for refractive object parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("Edit Refractive Object")
        d.setMinimumWidth(600)
        layout = QtWidgets.QVBoxLayout(d)
        
        # Position and rotation
        form = QtWidgets.QFormLayout()
        
        initial_x = self.pos().x()
        initial_y = self.pos().y()
        initial_ang = self.rotation()
        
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
        
        def update_position():
            self.setPos(x.value(), y.value())
            self.params.x_mm = x.value()
            self.params.y_mm = y.value()
            self.edited.emit()
        
        def update_angle():
            self.setRotation(ang.value())
            self.params.angle_deg = ang.value()
            self.edited.emit()
        
        def sync_from_item():
            x.blockSignals(True)
            y.blockSignals(True)
            ang.blockSignals(True)
            
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
        self.edited.connect(sync_from_item)
        
        form.addRow("X Position", x)
        form.addRow("Y Position", y)
        form.addRow("Rotation Angle", ang)
        
        layout.addLayout(form)
        
        # Interfaces list
        layout.addWidget(QtWidgets.QLabel("<b>Optical Interfaces:</b>"))
        
        interfaces_list = QtWidgets.QListWidget()
        interfaces_list.setMaximumHeight(200)
        
        def update_interface_list():
            interfaces_list.clear()
            for i, iface in enumerate(self.params.interfaces):
                desc = f"Interface {i+1}: "
                if iface.is_beam_splitter:
                    desc += "Beam Splitter "
                desc += f"n={iface.n1:.3f}→{iface.n2:.3f}"
                interfaces_list.addItem(desc)
        
        update_interface_list()
        layout.addWidget(interfaces_list)
        
        # Interface editing buttons
        btn_layout = QtWidgets.QHBoxLayout()
        
        btn_add = QtWidgets.QPushButton("Add Interface")
        btn_edit = QtWidgets.QPushButton("Edit Selected")
        btn_delete = QtWidgets.QPushButton("Delete Selected")
        
        def add_interface():
            # Add a default interface
            iface = RefractiveInterface(
                x1_mm=-20.0, y1_mm=-20.0,
                x2_mm=20.0, y2_mm=-20.0,
                n1=1.0, n2=1.5
            )
            self.params.interfaces.append(iface)
            update_interface_list()
            self._update_geom()
            self.update()
            self.edited.emit()
        
        def edit_interface():
            row = interfaces_list.currentRow()
            if row >= 0 and row < len(self.params.interfaces):
                self._open_interface_editor(row)
                update_interface_list()
                self._update_geom()
                self.update()
                self.edited.emit()
        
        def delete_interface():
            row = interfaces_list.currentRow()
            if row >= 0 and row < len(self.params.interfaces):
                del self.params.interfaces[row]
                update_interface_list()
                self._update_geom()
                self.update()
                self.edited.emit()
        
        btn_add.clicked.connect(add_interface)
        btn_edit.clicked.connect(edit_interface)
        btn_delete.clicked.connect(delete_interface)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        layout.addLayout(btn_layout)
        
        # Dialog buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(d.accept)
        btn_box.rejected.connect(d.reject)
        layout.addWidget(btn_box)
        
        result = d.exec()
        self.edited.disconnect(sync_from_item)
        
        if not result:
            # Rollback
            self.setPos(initial_x, initial_y)
            self.params.x_mm = initial_x
            self.params.y_mm = initial_y
            self.setRotation(initial_ang)
            self.params.angle_deg = initial_ang
            self.edited.emit()
    
    def _open_interface_editor(self, index: int):
        """Open editor for a specific interface."""
        if index < 0 or index >= len(self.params.interfaces):
            return
        
        iface = self.params.interfaces[index]
        
        d = QtWidgets.QDialog(self._parent_window())
        d.setWindowTitle(f"Edit Interface {index + 1}")
        f = QtWidgets.QFormLayout(d)
        
        # Geometry
        x1 = SmartDoubleSpinBox()
        x1.setRange(-1000, 1000)
        x1.setDecimals(2)
        x1.setSuffix(" mm")
        x1.setValue(iface.x1_mm)
        
        y1 = SmartDoubleSpinBox()
        y1.setRange(-1000, 1000)
        y1.setDecimals(2)
        y1.setSuffix(" mm")
        y1.setValue(iface.y1_mm)
        
        x2 = SmartDoubleSpinBox()
        x2.setRange(-1000, 1000)
        x2.setDecimals(2)
        x2.setSuffix(" mm")
        x2.setValue(iface.x2_mm)
        
        y2 = SmartDoubleSpinBox()
        y2.setRange(-1000, 1000)
        y2.setDecimals(2)
        y2.setSuffix(" mm")
        y2.setValue(iface.y2_mm)
        
        # Refractive indices
        n1 = SmartDoubleSpinBox()
        n1.setRange(1.0, 3.0)
        n1.setDecimals(4)
        n1.setValue(iface.n1)
        
        n2 = SmartDoubleSpinBox()
        n2.setRange(1.0, 3.0)
        n2.setDecimals(4)
        n2.setValue(iface.n2)
        
        # Beam splitter properties
        is_bs = QtWidgets.QCheckBox("Beam Splitter Interface")
        is_bs.setChecked(iface.is_beam_splitter)
        
        split_t = QtWidgets.QDoubleSpinBox()
        split_t.setRange(0, 100)
        split_t.setDecimals(1)
        split_t.setSuffix(" %")
        split_t.setValue(iface.split_T)
        split_t.setEnabled(iface.is_beam_splitter)
        
        split_r = QtWidgets.QDoubleSpinBox()
        split_r.setRange(0, 100)
        split_r.setDecimals(1)
        split_r.setSuffix(" %")
        split_r.setValue(iface.split_R)
        split_r.setEnabled(iface.is_beam_splitter)
        
        is_pbs = QtWidgets.QCheckBox("Polarizing (PBS)")
        is_pbs.setChecked(iface.is_polarizing)
        is_pbs.setEnabled(iface.is_beam_splitter)
        
        pbs_axis = QtWidgets.QDoubleSpinBox()
        pbs_axis.setRange(-180, 180)
        pbs_axis.setDecimals(1)
        pbs_axis.setSuffix(" °")
        pbs_axis.setValue(iface.pbs_transmission_axis_deg)
        pbs_axis.setEnabled(iface.is_beam_splitter and iface.is_polarizing)
        
        def on_bs_toggled(checked):
            split_t.setEnabled(checked)
            split_r.setEnabled(checked)
            is_pbs.setEnabled(checked)
            pbs_axis.setEnabled(checked and is_pbs.isChecked())
        
        def on_pbs_toggled(checked):
            pbs_axis.setEnabled(is_bs.isChecked() and checked)
        
        is_bs.toggled.connect(on_bs_toggled)
        is_pbs.toggled.connect(on_pbs_toggled)
        
        # Layout
        f.addRow("Start X", x1)
        f.addRow("Start Y", y1)
        f.addRow("End X", x2)
        f.addRow("End Y", y2)
        f.addRow("Refractive Index (n1)", n1)
        f.addRow("Refractive Index (n2)", n2)
        f.addRow("", is_bs)
        f.addRow("Transmission %", split_t)
        f.addRow("Reflection %", split_r)
        f.addRow("", is_pbs)
        f.addRow("PBS Axis", pbs_axis)
        
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        if d.exec():
            # Save changes
            iface.x1_mm = x1.value()
            iface.y1_mm = y1.value()
            iface.x2_mm = x2.value()
            iface.y2_mm = y2.value()
            iface.n1 = n1.value()
            iface.n2 = n2.value()
            iface.is_beam_splitter = is_bs.isChecked()
            iface.split_T = split_t.value()
            iface.split_R = split_r.value()
            iface.is_polarizing = is_pbs.isChecked()
            iface.pbs_transmission_axis_deg = pbs_axis.value()
    
    def get_interfaces_scene(self) -> List[Tuple[np.ndarray, np.ndarray, RefractiveInterface]]:
        """Get all interfaces in scene coordinates.
        
        Returns:
            List of (p1, p2, interface) tuples where p1 and p2 are scene coordinates
        """
        # Get picked line offset for coordinate transformation
        offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
        
        result = []
        for iface in self.params.interfaces:
            # Transform from image-center coords to picked-line-center coords (item local coords)
            # Then transform to scene coordinates
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
        d = {
            "x_mm": float(self.pos().x()),
            "y_mm": float(self.pos().y()),
            "angle_deg": float(self.rotation()),
            "object_height_mm": self.params.object_height_mm,
            "image_path": to_relative_path(self.params.image_path),
            "mm_per_pixel": self.params.mm_per_pixel,
            "line_px": self.params.line_px,
            "name": self.params.name,
            "item_uuid": self.item_uuid,
            "interfaces": [asdict(iface) for iface in self.params.interfaces]
        }
        return d
    
    def from_dict(self, d: Dict[str, Any]):
        """Deserialize from dictionary."""
        if "item_uuid" in d:
            self.item_uuid = d["item_uuid"]
        
        # Restore interfaces
        interfaces = []
        for iface_dict in d.get("interfaces", []):
            interfaces.append(RefractiveInterface(**iface_dict))
        
        # Convert relative image path to absolute
        image_path = d.get("image_path")
        if image_path:
            image_path = to_absolute_path(image_path)
        
        self.params = RefractiveObjectParams(
            x_mm=d.get("x_mm", 0.0),
            y_mm=d.get("y_mm", 0.0),
            angle_deg=d.get("angle_deg", 45.0),
            object_height_mm=d.get("object_height_mm", 80.0),
            interfaces=interfaces,
            image_path=image_path,
            mm_per_pixel=d.get("mm_per_pixel", 0.1),
            line_px=d.get("line_px"),
            name=d.get("name")
        )
        
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_geom()
        self._maybe_attach_sprite()
        self.edited.emit()

