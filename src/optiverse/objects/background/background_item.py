from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any

from PyQt6 import QtCore, QtGui, QtWidgets

from ...ui.smart_spinbox import SmartDoubleSpinBox
from ..base_obj import BaseObj
from ..component_sprite import create_component_sprite


@dataclass
class BackgroundParams:
    """Parameters for background/decorative items."""
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 0.0
    object_height_mm: float = 100.0
    name: str = "Background"
    image_path: str = ""


class BackgroundItem(BaseObj):
    """
    Background/decorative item with no optical interfaces.
    
    Used for visual elements like laser tables, optical benches, etc.
    that don't participate in raytracing but provide visual context.
    """
    
    def __init__(self, params: BackgroundParams, item_uuid: str | None = None):
        super().__init__(item_uuid)
        self.params = params
        
        # Create sprite if image path exists
        self._sprite = None
        if self.params.image_path:
            try:
                # Reference line spans the full object height (centered)
                half_height = self.params.object_height_mm / 2.0
                reference_line = (0.0, -half_height, 0.0, half_height)
                
                self._sprite = create_component_sprite(
                    image_path=self.params.image_path,
                    reference_line_mm=reference_line,
                    object_height_mm=self.params.object_height_mm,
                    parent_item=self,
                )
                self._sprite.setVisible(True)
            except Exception as e:
                print(f"[BackgroundItem] Failed to load sprite: {e}")
                self._sprite = None
        
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._ready = True  # Enable position sync
    
    def _sync_params_from_item(self):
        """Sync params from item position/rotation."""
        self.params.x_mm = float(self.pos().x())
        self.params.y_mm = float(self.pos().y())
        self.params.angle_deg = float(self.rotation())
    
    def boundingRect(self) -> QtCore.QRectF:
        """Return bounding rectangle."""
        # Simple fallback rect if no sprite
        base_rect = QtCore.QRectF(-50, -50, 100, 100)
        
        # Union with sprite if it exists
        if self._sprite is not None:
            return self._bounds_union_sprite(base_rect)
        
        return base_rect
    
    def shape(self) -> QtGui.QPainterPath:
        """Return shape for hit testing."""
        # Create a basic path
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        
        # Union with sprite for clickability
        return self._shape_union_sprite(path)
    
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        """Paint the background item (sprite handles itself)."""
        # If no sprite, draw a simple placeholder
        if self._sprite is None:
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
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
            p.drawText(self.boundingRect(), QtCore.Qt.AlignmentFlag.AlignCenter, self.params.name)
    
    def open_editor(self):
        """Open editor dialog for background item parameters."""
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle(f"Edit {self.params.name}")
        f = QtWidgets.QFormLayout(d)
        
        # Save initial state for rollback on cancel
        initial_x = self.pos().x()
        initial_y = self.pos().y()
        initial_ang = self.rotation()
        
        # Position and orientation
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
        
        # Update spinboxes when item is modified externally
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
        
        # Add fields to form
        f.addRow("X Position", x)
        f.addRow("Y Position", y)
        f.addRow("Rotation", ang)
        
        # Buttons
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        result = d.exec()
        
        # Disconnect the sync signal to prevent memory leaks
        self.edited.disconnect(sync_from_item)
        
        if result:
            # Position and angle already applied live - nothing more to do
            pass
        else:
            # User clicked Cancel - restore initial position and angle
            self.setPos(initial_x, initial_y)
            self.params.x_mm = initial_x
            self.params.y_mm = initial_y
            self.setRotation(initial_ang)
            self.params.angle_deg = initial_ang
            self.edited.emit()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        d = asdict(self.params)
        # Force live pose
        d["x_mm"] = float(self.pos().x())
        d["y_mm"] = float(self.pos().y())
        d["angle_deg"] = float(self.rotation())
        d["item_uuid"] = self.item_uuid
        d["locked"] = self._locked  # Save lock state
        d["z_value"] = float(self.zValue())  # Save z-order
        return d
    
    def from_dict(self, d: Dict[str, Any]):
        """Deserialize from dictionary."""
        # Restore UUID if present
        if "item_uuid" in d:
            self.item_uuid = d["item_uuid"]
        # Restore locked state (call parent's from_dict)
        super().from_dict(d)
        
        # Update params
        self.params.x_mm = d.get("x_mm", 0.0)
        self.params.y_mm = d.get("y_mm", 0.0)
        self.params.angle_deg = d.get("angle_deg", 0.0)
        self.params.object_height_mm = d.get("object_height_mm", 100.0)
        self.params.name = d.get("name", "Background")
        self.params.image_path = d.get("image_path", "")
        
        # Update position and rotation
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self.edited.emit()

