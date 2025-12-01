from __future__ import annotations

import uuid
from typing import Any, cast

from PyQt6 import QtCore, QtGui, QtWidgets

from ..core.constants import WHEEL_ROTATION_DEGREES_PER_STEP
from ..core.protocols import HasCollaboration, HasParams, HasShape, HasSnapping, HasUndoStack
from ..core.ui_constants import (
    CLONE_OFFSET_X_MM,
    CLONE_OFFSET_Y_MM,
    QT_WHEEL_ANGLE_DELTA_PER_STEP,
    SPRITE_BOUNDS_PADDING_PX,
    SPRITE_SHAPE_PADDING_PX,
)
from ..core.undo_stack import UndoStack
from .rotation_handler import (
    GroupRotationHandler,
    SingleItemRotationHandler,
    WheelRotationTracker,
    rotate_group_instant,
)


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

    type_name: str = "base_obj"  # For Serializable protocol

    edited = QtCore.pyqtSignal()
    commandCreated = QtCore.pyqtSignal(object)  # Emits Command objects for undo/redo

    # Metadata registry for serialization (extensible by subclasses)
    # Maps metadata key to getter function
    _metadata_registry = {
        "item_uuid": lambda self: self.item_uuid,
        "locked": lambda self: self._locked,
        "z_value": lambda self: float(self.zValue()),
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

        # Rotation handlers (extracted for cleaner code)
        self._single_rotation: SingleItemRotationHandler | None = None
        self._group_rotation: GroupRotationHandler | None = None
        self._wheel_tracker = WheelRotationTracker(self._get_undo_stack)

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
                        if isinstance(main_window, HasSnapping) and main_window.magnetic_snap:
                            # value is the new position being proposed
                            new_pos = value

                            # Calculate snap
                            snap_result = main_window._snap_helper.calculate_snap(
                                new_pos, self, scene, views[0]
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
                        if isinstance(main_window, HasCollaboration):
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
        return cast(QtCore.QRectF, sp.mapRectToParent(sp.boundingRect()))

    def _shape_union_sprite(self, shape_path: QtGui.QPainterPath) -> QtGui.QPainterPath:
        """
        Union sprite bounds into shape for hit testing.

        This makes the sprite clickable, not just the geometry line.
        Call this at the end of shape() method.
        """
        r = self._sprite_rect_in_item()
        if r is not None:
            pad = SPRITE_SHAPE_PADDING_PX
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
            pad = SPRITE_BOUNDS_PADDING_PX
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

    def _get_undo_stack(self) -> UndoStack | None:
        """Get the undo stack from main window (for WheelRotationTracker)."""
        scene = self.scene()
        if scene is None:
            return None
        views = scene.views()
        if not views:
            return None
        main_window = views[0].window()
        if isinstance(main_window, HasUndoStack):
            return main_window.undo_stack
        return None

    def mousePressEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent | None):
        """Handle mouse press for rotation mode (Ctrl+drag) or normal drag."""
        if ev is None:
            return
        # If locked, ignore event so rubber band selection can work
        if self._locked:
            ev.ignore()
            return

        if self.isSelected() and (ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            # Enter rotation mode
            mouse_pos = ev.scenePos()

            # Check if this is a group rotation
            scene = self.scene()
            if scene is not None:
                selected_items = [
                    item for item in scene.selectedItems() if isinstance(item, BaseObj)
                ]

                if len(selected_items) > 1:
                    # Group rotation
                    self._group_rotation = GroupRotationHandler(selected_items)
                    self._group_rotation.start_rotation(mouse_pos)
                    self._single_rotation = None
                else:
                    # Single item rotation
                    self._single_rotation = SingleItemRotationHandler(self)
                    self._single_rotation.start_rotation(mouse_pos, self.rotation())
                    self._group_rotation = None
            else:
                # Fallback to single rotation
                self._single_rotation = SingleItemRotationHandler(self)
                self._single_rotation.start_rotation(mouse_pos, self.rotation())
                self._group_rotation = None

            # Change cursor to indicate rotation mode
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            ev.accept()
        else:
            # Normal drag behavior
            super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent | None):
        """Handle mouse move for rotation or normal drag."""
        if ev is None:
            return
        mouse_pos = ev.scenePos()
        snap_to_45 = bool(ev.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier)

        if self._group_rotation and self._group_rotation.is_rotating:
            # Group rotation
            self._group_rotation.update_rotation(mouse_pos, snap_to_45)
            ev.accept()
        elif self._single_rotation and self._single_rotation.is_rotating:
            # Single item rotation
            new_rotation = self._single_rotation.update_rotation(mouse_pos, snap_to_45)
            self.setRotation(new_rotation)
            self.edited.emit()
            ev.accept()
        else:
            # Normal drag behavior
            super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent | None):
        """Handle mouse release to exit rotation mode."""
        if ev is None:
            return
        if self._group_rotation and self._group_rotation.is_rotating:
            self._group_rotation.finish_rotation()
            self._group_rotation = None
            self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            ev.accept()
        elif self._single_rotation and self._single_rotation.is_rotating:
            self._single_rotation.finish_rotation()
            self._single_rotation = None
            self.edited.emit()
            self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            ev.accept()
        else:
            super().mouseReleaseEvent(ev)

    def wheelEvent(self, ev: QtWidgets.QGraphicsSceneWheelEvent | None):
        """Ctrl + wheel → rotate element(s)."""
        if ev is None:
            return
        # Block rotation if locked
        if self._locked and (ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            ev.ignore()
            return

        if self.isSelected() and (ev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            dy = ev.angleDelta().y()  # type: ignore[attr-defined]
            steps = dy / QT_WHEEL_ANGLE_DELTA_PER_STEP
            rotation_delta = WHEEL_ROTATION_DEGREES_PER_STEP * steps

            # Check if multiple items are selected for group rotation
            scene = self.scene()
            if scene is not None:
                selected_items = [
                    item for item in scene.selectedItems() if isinstance(item, BaseObj)
                ]

                # Track for undo
                self._wheel_tracker.track(selected_items)

                if len(selected_items) > 1:
                    # Group rotation around common center
                    rotate_group_instant(selected_items, rotation_delta)
                else:
                    # Single item rotation
                    self.setRotation(self.rotation() + rotation_delta)
                    self.edited.emit()
            else:
                # Fallback to single rotation
                self._wheel_tracker.track([self])
                self.setRotation(self.rotation() + rotation_delta)
                self.edited.emit()

            ev.accept()
        else:
            ev.ignore()

    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent | None):
        """Right-click context menu with Edit, Delete, Lock, and Z-Order options."""
        if ev is None:
            return
        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit…")
        act_delete = m.addAction("Delete")

        # Add Lock action (checkable)
        m.addSeparator()
        act_lock = m.addAction("Lock")
        if act_lock is not None:
            act_lock.setCheckable(True)
            act_lock.setChecked(self._locked)

        # Disable delete if locked
        if self._locked and act_delete is not None:
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
        elif a == act_lock and act_lock is not None:
            self.set_locked(act_lock.isChecked())
        elif a == act_delete and act_delete is not None:
            scene = self.scene()
            if scene is not None and not self._locked:
                scene.removeItem(self)
        elif a in (act_bring_to_front, act_bring_forward, act_send_backward, act_send_to_back):
            # Handle z-order changes
            self._handle_z_order_action(
                a, act_bring_to_front, act_bring_forward, act_send_backward, act_send_to_back
            )

    def _handle_z_order_action(
        self,
        selected_action,
        act_bring_to_front,
        act_bring_forward,
        act_send_backward,
        act_send_to_back,
    ):
        """Handle z-order menu actions."""
        from ..core.zorder_utils import apply_z_order_change

        if not self.scene():
            return

        # Get items to operate on: if this item is selected, use all selected items
        # Otherwise, just use this item
        if self.isSelected():
            items = [item for item in self.scene().selectedItems() if hasattr(item, "setZValue")]
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
            if isinstance(main_window, HasUndoStack):
                undo_stack = main_window.undo_stack

        # Apply z-order change
        apply_z_order_change(items, operation, self.scene(), undo_stack)

    # Abstract interface methods (subclasses should override)
    def open_editor(self):
        """Open editor dialog for this element."""
        pass

    def capture_state(self) -> dict[str, Any]:
        """Capture current state for undo/redo. Subclasses should extend."""
        import dataclasses

        state = {
            "pos": {"x": self.pos().x(), "y": self.pos().y()},
            "rotation": self.rotation(),
            "locked": self._locked,
            "z_value": float(self.zValue()),
        }
        # Capture params if available (using protocol for type safety)
        if isinstance(self, HasParams) and hasattr(self, "params") and self.params is not None:
            import dataclasses

            if dataclasses.is_dataclass(self.params):
                state["params"] = dataclasses.asdict(self.params)  # type: ignore[arg-type]
        return state

    def apply_state(self, state: dict[str, Any]) -> None:
        """Apply state from undo/redo. Subclasses should extend if needed."""
        import dataclasses

        if "pos" in state:
            self.setPos(QtCore.QPointF(state["pos"]["x"], state["pos"]["y"]))
        if "rotation" in state:
            self.setRotation(state["rotation"])
        if "locked" in state:
            self.set_locked(state["locked"])
        if "z_value" in state:
            self.setZValue(state["z_value"])

        # Apply params if available (using protocol for type safety)
        if "params" in state and isinstance(self, HasParams):
            if dataclasses.is_dataclass(self.params):
                for key, value in state["params"].items():
                    if hasattr(self.params, key):
                        setattr(self.params, key, value)

        # Sync visual state (using protocol for type safety)
        if isinstance(self, HasParams):
            self._sync_params_from_item()
        if isinstance(self, HasShape):
            self._update_shape()
            self._update_geom()
        self.edited.emit()
        self.update()

    def clone(
        self, offset_mm: tuple[float, float] = (CLONE_OFFSET_X_MM, CLONE_OFFSET_Y_MM)
    ) -> BaseObj:
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
        if not isinstance(self, HasParams):
            raise TypeError("clone() requires HasParams protocol")
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
