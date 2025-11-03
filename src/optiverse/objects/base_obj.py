from __future__ import annotations

import math
import uuid
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets


class BaseObj(QtWidgets.QGraphicsObject):
    """
    Base class for all optical elements (Source, Lens, Mirror, Beamsplitter).
    
    Provides common functionality:
    - Standard flags (movable, selectable, sends geometry changes)
    - Context menu (Edit, Delete)
    - Ctrl+Wheel rotation
    - Position/rotation sync with params
    - Sprite helper methods for clickable sprites
    - Serialization interface
    """

    edited = QtCore.pyqtSignal()
    
    # Metadata registry for serialization (extensible by subclasses)
    # Maps metadata key to getter function
    _metadata_registry = {
        'item_uuid': lambda self: self.item_uuid,
        'locked': lambda self: self._locked,
        'z_value': lambda self: float(self.zValue()),
    }

    def __init__(self, item_uuid: str | None = None):
        super().__init__()
        # Generate or use provided UUID for collaboration
        self.item_uuid = item_uuid if item_uuid else str(uuid.uuid4())
        
        # Lock state (prevents movement, rotation, and deletion)
        self._locked = False
        
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        self.setTransformOriginPoint(0.0, 0.0)
        self._ready = False  # Set to True after full initialization
        
        # Rotation mode state (Ctrl + drag to rotate)
        self._rotating = False
        self._rotation_start_angle = 0.0
        self._rotation_initial = 0.0
        
        # Group rotation state (for multiple selected items)
        self._group_rotating = False
        self._group_items = []
        self._group_initial_positions = {}
        self._group_initial_rotations = {}
        self._group_center = QtCore.QPointF(0, 0)
        
        # Wheel rotation tracking for undo (batch multiple scroll events)
        self._wheel_rotation_timer = None
        self._wheel_rotation_start_rotation = None
        self._wheel_rotation_start_positions = None
        self._wheel_rotation_items = None

    def itemChange(self, change, value):
        """Sync params when position or rotation changes, and apply magnetic snap."""
        
        # Block position changes if locked
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if self._locked:
                return self.pos()  # Return current position (no change)
        
        # Magnetic snap: intercept position changes during interactive moves
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if getattr(self, "_ready", False) and self.scene() is not None:
                # Get the main window to check if magnetic snap is enabled
                scene = self.scene()
                if scene:
                    views = scene.views()
                    if views:
                        main_window = views[0].window()
                        # Check if magnetic snap is enabled and this is an interactive move
                        if hasattr(main_window, 'magnetic_snap') and main_window.magnetic_snap:
                            if hasattr(main_window, '_snap_helper'):
                                # value is the new position being proposed
                                new_pos = value
                                
                                # Calculate snap
                                snap_result = main_window._snap_helper.calculate_snap(
                                    new_pos,
                                    self,
                                    scene,
                                    views[0]
                                )
                                
                                if snap_result.snapped:
                                    # Update guide lines
                                    views[0].set_snap_guides(snap_result.guide_lines)
                                    # Return snapped position instead of proposed position
                                    return snap_result.position
                                else:
                                    # Clear guides if not snapping
                                    views[0].clear_snap_guides()
        
        if change in (
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemRotationHasChanged,
        ):
            if getattr(self, "_ready", False) and self.scene() is not None:
                self._sync_params_from_item()
                self.edited.emit()
                
                # Broadcast position/rotation change to collaboration
                if self.scene():
                    views = self.scene().views()
                    if views:
                        main_window = views[0].window()
                        if hasattr(main_window, 'collaboration_manager'):
                            main_window.collaboration_manager.broadcast_move_item(self)

        # Phase 2.2: Ensure sprite re-renders when selection toggles (remove lingering tint)
        if change in (
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedChange,
            QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged,
        ):
            # Repaint this item and its sprite (if any)
            self.update()
            sp = getattr(self, "_sprite", None)
            if sp is not None:
                sp.update()
            
            # Force viewport repaint to clear any cached rendering
            if self.scene() is not None:
                views = self.scene().views()
                if views:
                    views[0].viewport().update()

        return super().itemChange(change, value)

    def _sync_params_from_item(self):
        """
        Sync internal params from item's position and rotation.
        Override in subclasses that have params.
        """
        pass
    
    def is_locked(self) -> bool:
        """Check if item is locked (prevents movement, rotation, deletion)."""
        return self._locked
    
    def set_locked(self, locked: bool):
        """Set lock state (prevents movement, rotation, deletion, and selection)."""
        self._locked = locked
        # Update cursor to indicate locked state
        if locked:
            self.setCursor(QtCore.Qt.CursorShape.ForbiddenCursor)
            # Remove selectable flag so locked objects can't be selected
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        else:
            self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            # Restore selectable flag when unlocked
            self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        # Update visual appearance
        self.update()
    
    def setRotation(self, angle: float):
        """Override setRotation to block when locked."""
        if not self._locked:
            super().setRotation(angle)
        # If locked, do nothing (rotation blocked)

    # ----- Sprite Helper Methods (Phase 1.2: Clickable Sprites) -----
    def _sprite_rect_in_item(self) -> QtCore.QRectF | None:
        """
        Get sprite bounds in item-local coordinates.
        
        Returns None if sprite doesn't exist or is invisible.
        This is used to make sprites part of the clickable area.
        """
        sp = getattr(self, "_sprite", None)
        if sp is None or not sp.isVisible():
            return None
        # parent == this item ⇒ returned rect is in *item-local* coords
        return sp.mapRectToParent(sp.boundingRect())

    def _shape_union_sprite(self, shape_path: QtGui.QPainterPath) -> QtGui.QPainterPath:
        """
        Union sprite bounds into shape for hit testing.
        
        This makes the sprite clickable, not just the geometry line.
        Call this at the end of shape() method.
        """
        r = self._sprite_rect_in_item()
        if r is not None:
            pad = 1.0
            rp = QtGui.QPainterPath()
            rp.addRect(r.adjusted(-pad, -pad, pad, pad))
            shape_path = shape_path.united(rp)
        return shape_path

    def _bounds_union_sprite(self, base_rect: QtCore.QRectF) -> QtCore.QRectF:
        """
        Union sprite bounds into bounding rect.
        
        Ensures the bounding box encompasses the entire sprite.
        Call this at the end of boundingRect() method.
        """
        r = self._sprite_rect_in_item()
        if r is not None:
            pad = 2.0
            r = r.adjusted(-pad, -pad, pad, pad)
            base_rect = base_rect.united(r)
        return base_rect

    def _parent_window(self):
        """Get the parent window for dialogs."""
        sc = self.scene()
        if sc:
            views = sc.views()
            if views:
                return views[0].window()
        return QtWidgets.QApplication.activeWindow()

    def _rotate_group(self, items: list, rotation_delta: float):
        """Rotate a group of items around their common center."""
        if not items:
            return
        
        # Calculate center of all items
        center_x = sum(item.pos().x() for item in items) / len(items)
        center_y = sum(item.pos().y() for item in items) / len(items)
        center = QtCore.QPointF(center_x, center_y)
        
        # Rotate each item around the common center
        for item in items:
            # Get current position relative to center
            rel_pos = item.pos() - center
            
            # Rotate the relative position
            angle_rad = math.radians(rotation_delta)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            new_x = rel_pos.x() * cos_a - rel_pos.y() * sin_a
            new_y = rel_pos.x() * sin_a + rel_pos.y() * cos_a
            
            # Set new position
            item.setPos(center.x() + new_x, center.y() + new_y)
            
            # Also rotate the item itself
            item.setRotation(item.rotation() + rotation_delta)
            item.edited.emit()
    
    def mousePressEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        """Handle mouse press for rotation mode (Ctrl+drag) or normal drag."""
        # If locked, ignore event so rubber band selection can work
        if self._locked:
            ev.ignore()
            return
        
        if self.isSelected() and (ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            # Enter rotation mode
            self._rotating = True
            self._rotation_initial = self.rotation()
            
            # Check if this is a group rotation
            if self.scene():
                selected_items = [item for item in self.scene().selectedItems() 
                                if isinstance(item, BaseObj)]
                self._group_rotating = len(selected_items) > 1
                
                if self._group_rotating:
                    # Store initial state for all items
                    self._group_items = selected_items
                    self._group_initial_positions = {item: item.pos() for item in selected_items}
                    self._group_initial_rotations = {item: item.rotation() for item in selected_items}
                    
                    # Calculate group center
                    center_x = sum(item.pos().x() for item in selected_items) / len(selected_items)
                    center_y = sum(item.pos().y() for item in selected_items) / len(selected_items)
                    self._group_center = QtCore.QPointF(center_x, center_y)
                    center = self._group_center
                else:
                    self._group_rotating = False
                    center = self.mapToScene(self.transformOriginPoint())
            else:
                self._group_rotating = False
                center = self.mapToScene(self.transformOriginPoint())
            
            # Calculate initial angle from rotation center to mouse position
            mouse_pos = ev.scenePos()
            dx = mouse_pos.x() - center.x()
            dy = mouse_pos.y() - center.y()
            self._rotation_start_angle = math.degrees(math.atan2(dy, dx))
            
            # Change cursor to indicate rotation mode
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            ev.accept()
        else:
            # Normal drag behavior
            super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        """Handle mouse move for rotation or normal drag."""
        if self._rotating:
            # Get rotation center (group center or item center)
            if getattr(self, '_group_rotating', False):
                center = self._group_center
            else:
                center = self.mapToScene(self.transformOriginPoint())
            
            # Calculate current angle from rotation center to mouse position
            mouse_pos = ev.scenePos()
            dx = mouse_pos.x() - center.x()
            dy = mouse_pos.y() - center.y()
            current_angle = math.degrees(math.atan2(dy, dx))
            
            # Calculate rotation delta
            angle_delta = current_angle - self._rotation_start_angle
            
            # Apply rotation
            if getattr(self, '_group_rotating', False):
                # Group rotation
                # Shift+Ctrl: snap angle_delta to 45-degree increments for group rotation
                # This ensures all items rotate by the same amount, maintaining relative orientation
                if ev.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
                    angle_delta = round(angle_delta / 45.0) * 45.0
                
                for item in self._group_items:
                    # Rotate position around group center
                    initial_pos = self._group_initial_positions[item]
                    rel_pos = initial_pos - center
                    angle_rad = math.radians(angle_delta)
                    cos_a = math.cos(angle_rad)
                    sin_a = math.sin(angle_rad)
                    new_x = rel_pos.x() * cos_a - rel_pos.y() * sin_a
                    new_y = rel_pos.x() * sin_a + rel_pos.y() * cos_a
                    item.setPos(center.x() + new_x, center.y() + new_y)
                    
                    # Rotate the item itself
                    initial_rotation = self._group_initial_rotations[item]
                    new_rotation = initial_rotation + angle_delta
                    
                    item.setRotation(new_rotation)
                    # Emit edited signal during drag for live editor updates
                    item.edited.emit()
            else:
                # Single item rotation
                new_rotation = self._rotation_initial + angle_delta
                
                # Shift+Ctrl: snap to absolute 45-degree increments (0, 45, 90, 135, 180, etc.)
                if ev.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
                    new_rotation = round(new_rotation / 45.0) * 45.0
                
                self.setRotation(new_rotation)
                # Emit edited signal during drag for live editor updates
                self.edited.emit()
            
            ev.accept()
        else:
            # Normal drag behavior
            super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        """Handle mouse release to exit rotation mode."""
        if self._rotating:
            self._rotating = False
            self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            
            # Emit edited signal for all affected items
            if getattr(self, '_group_rotating', False):
                for item in self._group_items:
                    item.edited.emit()
                # Clean up group rotation state
                self._group_rotating = False
                self._group_items = []
                self._group_initial_positions = {}
                self._group_initial_rotations = {}
            else:
                self.edited.emit()
            
            ev.accept()
        else:
            super().mouseReleaseEvent(ev)

    def wheelEvent(self, ev: QtWidgets.QGraphicsSceneWheelEvent):
        """Ctrl + wheel → rotate element(s)."""
        # Block rotation if locked
        if self._locked and (ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            ev.ignore()
            return
        
        if self.isSelected() and (ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            dy = ev.angleDelta().y()
            steps = dy / 120.0
            rotation_delta = 2.0 * steps
            
            # Check if multiple items are selected for group rotation
            if self.scene():
                selected_items = [item for item in self.scene().selectedItems() 
                                if isinstance(item, BaseObj)]
                
                # Track initial state for undo (first wheel event in sequence)
                if self._wheel_rotation_start_rotation is None:
                    self._wheel_rotation_start_rotation = {item: item.rotation() for item in selected_items}
                    self._wheel_rotation_start_positions = {item: QtCore.QPointF(item.pos()) for item in selected_items}
                    self._wheel_rotation_items = selected_items
                
                if len(selected_items) > 1:
                    # Group rotation around common center
                    self._rotate_group(selected_items, rotation_delta)
                else:
                    # Single item rotation
                    self.setRotation(self.rotation() + rotation_delta)
                    self.edited.emit()
            else:
                # Fallback to single rotation
                # Track initial state for undo
                if self._wheel_rotation_start_rotation is None:
                    self._wheel_rotation_start_rotation = {self: self.rotation()}
                    self._wheel_rotation_start_positions = {self: QtCore.QPointF(self.pos())}
                    self._wheel_rotation_items = [self]
                
                self.setRotation(self.rotation() + rotation_delta)
                self.edited.emit()
            
            # Reset timer - create undo command after 300ms of no wheel events
            if self._wheel_rotation_timer:
                self._wheel_rotation_timer.stop()
            self._wheel_rotation_timer = QtCore.QTimer()
            self._wheel_rotation_timer.setSingleShot(True)
            self._wheel_rotation_timer.timeout.connect(self._finalize_wheel_rotation)
            self._wheel_rotation_timer.start(300)  # 300ms delay
            
            ev.accept()
        else:
            ev.ignore()
    
    def _finalize_wheel_rotation(self):
        """Create undo command for completed wheel rotation sequence."""
        if self._wheel_rotation_start_rotation is None:
            return
        
        # Get main window and undo stack
        if not self.scene():
            self._wheel_rotation_start_rotation = None
            self._wheel_rotation_start_positions = None
            self._wheel_rotation_items = None
            return
        
        # Find the main window through the scene's views
        views = self.scene().views()
        if not views:
            self._wheel_rotation_start_rotation = None
            self._wheel_rotation_start_positions = None
            self._wheel_rotation_items = None
            return
        
        # Get the MainWindow (parent of GraphicsView)
        view = views[0]
        main_window = view.window()
        if not main_window or not hasattr(main_window, 'undo_stack'):
            self._wheel_rotation_start_rotation = None
            self._wheel_rotation_start_positions = None
            self._wheel_rotation_items = None
            return
        
        # Import commands here to avoid circular imports
        from ..core.undo_commands import RotateItemCommand, RotateItemsCommand
        
        items = self._wheel_rotation_items
        old_rotations = self._wheel_rotation_start_rotation
        old_positions = self._wheel_rotation_start_positions
        new_rotations = {item: item.rotation() for item in items}
        new_positions = {item: item.pos() for item in items}
        
        # Check if anything actually changed
        rotation_changed = any(
            abs(old_rotations.get(item, 0) - new_rotations.get(item, 0)) > 0.01
            for item in items
        )
        position_changed = any(
            old_positions.get(item) != new_positions.get(item)
            for item in items if item in old_positions
        )
        
        if rotation_changed or position_changed:
            if len(items) == 1 and not position_changed:
                # Single item rotation only
                cmd = RotateItemCommand(items[0], old_rotations[items[0]], new_rotations[items[0]])
                main_window.undo_stack.push(cmd)
            elif len(items) > 1 or position_changed:
                # Group rotation or single item with position change
                cmd = RotateItemsCommand(items, old_positions, new_positions, old_rotations, new_rotations)
                main_window.undo_stack.push(cmd)
        
        # Clear tracking state
        self._wheel_rotation_start_rotation = None
        self._wheel_rotation_start_positions = None
        self._wheel_rotation_items = None

    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent):
        """Right-click context menu with Edit, Delete, Lock, and Z-Order options."""
        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit…")
        act_delete = m.addAction("Delete")
        
        # Add Lock action (checkable)
        m.addSeparator()
        act_lock = m.addAction("Lock")
        act_lock.setCheckable(True)
        act_lock.setChecked(self._locked)
        
        # Disable delete if locked
        if self._locked:
            act_delete.setEnabled(False)
            act_delete.setToolTip("Item is locked")
        
        # Add z-order submenu
        m.addSeparator()
        act_bring_to_front = m.addAction("Bring to Front")
        act_bring_forward = m.addAction("Bring Forward")
        act_send_backward = m.addAction("Send Backward")
        act_send_to_back = m.addAction("Send to Back")
        
        a = m.exec(ev.screenPos())
        if a == act_edit:
            self.open_editor()
        elif a == act_lock:
            self.set_locked(act_lock.isChecked())
        elif a == act_delete and self.scene() and not self._locked:
            self.scene().removeItem(self)
        elif a in (act_bring_to_front, act_bring_forward, act_send_backward, act_send_to_back):
            # Handle z-order changes
            self._handle_z_order_action(a, act_bring_to_front, act_bring_forward, 
                                       act_send_backward, act_send_to_back)
    
    def _handle_z_order_action(self, selected_action, act_bring_to_front, act_bring_forward,
                               act_send_backward, act_send_to_back):
        """Handle z-order menu actions."""
        from ..core.zorder_utils import apply_z_order_change
        
        if not self.scene():
            return
        
        # Get items to operate on: if this item is selected, use all selected items
        # Otherwise, just use this item
        if self.isSelected():
            items = [item for item in self.scene().selectedItems() 
                    if hasattr(item, 'setZValue')]
        else:
            items = [self]
        
        if not items:
            return
        
        # Determine operation
        if selected_action == act_bring_to_front:
            operation = "bring_to_front"
        elif selected_action == act_bring_forward:
            operation = "bring_forward"
        elif selected_action == act_send_backward:
            operation = "send_backward"
        elif selected_action == act_send_to_back:
            operation = "send_to_back"
        else:
            return
        
        # Get undo stack from main window
        undo_stack = None
        if self.scene().views():
            main_window = self.scene().views()[0].window()
            if hasattr(main_window, 'undo_stack'):
                undo_stack = main_window.undo_stack
        
        # Apply z-order change
        apply_z_order_change(items, operation, self.scene(), undo_stack)

    # Abstract interface methods (subclasses should override)
    def open_editor(self):
        """Open editor dialog for this element."""
        pass

    def clone(self, offset_mm: tuple[float, float] = (20.0, 20.0)) -> 'BaseObj':
        """
        Create a deep copy of this item with optional position offset.
        
        This method creates a proper in-memory clone without using file serialization,
        making it robust for copy/paste operations. Sprites, interfaces, and all other
        properties are preserved.
        
        Args:
            offset_mm: (x_offset, y_offset) in millimeters to offset the cloned item
            
        Returns:
            A new instance of the same type with all properties copied
        """
        import copy
        
        # Deep copy the params to get all nested structures (interfaces, etc.)
        new_params = copy.deepcopy(self.params)
        
        # Apply position offset
        new_params.x_mm += offset_mm[0]
        new_params.y_mm += offset_mm[1]
        
        # Create new instance of same type with copied params
        # This will automatically handle sprite attachment, interface setup, etc.
        new_item = type(self)(new_params)
        
        # Copy item-level properties that aren't in params
        new_item._locked = self._locked
        new_item.setZValue(self.zValue())
        
        return new_item

    def to_dict(self) -> dict[str, Any]:
        """Serialize element to dictionary."""
        return {
            "item_uuid": self.item_uuid,
            "locked": self._locked,
            "z_value": float(self.zValue()),
        }

    def from_dict(self, d: dict[str, Any]):
        """Deserialize element from dictionary."""
        # Restore locked state if present
        if "locked" in d:
            self.set_locked(d["locked"])
        
        # Restore z-value if present
        if "z_value" in d:
            self.setZValue(float(d["z_value"]))

