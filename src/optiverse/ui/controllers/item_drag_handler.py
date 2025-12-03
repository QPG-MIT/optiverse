"""
Handler for item drag, move, and rotation tracking.

Extracts position/rotation tracking and undo command creation from MainWindow.
Supports group movement where all items in a group move together.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PyQt6 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from ...core.layer_group import GroupManager
    from ...core.undo_stack import UndoStack


class ItemDragHandler:
    """
    Handles item dragging, position tracking, and rotation for undo/redo support.

    This class tracks item positions on mouse press and creates appropriate
    undo commands on mouse release.
    """

    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        view: QtWidgets.QGraphicsView,
        undo_stack: UndoStack,
        snap_to_grid_getter: Callable[[], bool],
        schedule_retrace: Callable[[], None],
        group_manager: GroupManager | None = None,
    ):
        """
        Initialize the drag handler.

        Args:
            scene: Graphics scene containing items
            view: Graphics view for snap guide clearing
            undo_stack: Undo stack for command creation
            snap_to_grid_getter: Callable returning whether snap to grid is enabled
            schedule_retrace: Callable to schedule ray retracing
            group_manager: Optional group manager for group movement
        """
        self.scene = scene
        self.view = view
        self.undo_stack = undo_stack
        self._get_snap_to_grid = snap_to_grid_getter
        self._schedule_retrace = schedule_retrace
        self._group_manager = group_manager

        # Position tracking state
        self._item_positions: dict[QtWidgets.QGraphicsItem, QtCore.QPointF] = {}
        self._item_rotations: dict[QtWidgets.QGraphicsItem, float] = {}
        self._item_group_states: dict[str, Any] = {}
        
        # Group movement tracking
        self._dragging_group = False
        self._group_items: list[QtWidgets.QGraphicsItem] = []
        self._group_offsets: dict[QtWidgets.QGraphicsItem, QtCore.QPointF] = {}
        self._primary_drag_item: QtWidgets.QGraphicsItem | None = None

    def set_group_manager(self, group_manager: GroupManager) -> None:
        """Set the group manager for group movement support."""
        self._group_manager = group_manager

    def handle_mouse_press(self, event: QtGui.QMouseEvent):
        """
        Track item positions and rotations on mouse press.

        Also handles group movement - when one grouped item is pressed,
        all group members are tracked for coordinated movement.

        Args:
            event: Mouse event from the scene
        """
        from ...objects import BaseObj, RectangleItem
        from ...objects.annotations import RulerItem, TextNoteItem

        # Check if this is a rotation operation (Ctrl modifier)
        is_rotation_mode = event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier

        # Clear previous tracking state
        self._item_positions.clear()
        self._item_rotations.clear()
        self._item_group_states.clear()
        self._dragging_group = False
        self._group_items.clear()
        self._group_offsets.clear()
        self._primary_drag_item = None

        # Get already-selected items
        selected_items = [
            it
            for it in self.scene.selectedItems()
            if isinstance(it, (BaseObj, RulerItem, TextNoteItem, RectangleItem))
        ]

        # Also track the item under the mouse cursor (may not be selected yet)
        # QMouseEvent doesn't have scenePos, use pos() mapped to scene
        if hasattr(self.view, "mapToScene"):
            scene_pos: QtCore.QPointF = self.view.mapToScene(event.pos())
        else:
            scene_pos = QtCore.QPointF(event.pos())
        clicked_item = self.scene.itemAt(scene_pos, QtGui.QTransform())

        # Walk up parent hierarchy to find the actual draggable item
        while clicked_item is not None:
            if isinstance(clicked_item, (BaseObj, RulerItem, TextNoteItem, RectangleItem)):
                if clicked_item not in selected_items:
                    selected_items.append(clicked_item)
                self._primary_drag_item = clicked_item
                break
            clicked_item = clicked_item.parentItem()

        # Check for group membership and expand selection
        if self._group_manager and self._primary_drag_item:
            grouped_items = self._group_manager.get_grouped_items(self._primary_drag_item)
            if len(grouped_items) > 1:
                self._dragging_group = True
                self._group_items = grouped_items
                # Store offsets relative to primary item
                primary_pos = self._primary_drag_item.pos()
                for item in grouped_items:
                    if item != self._primary_drag_item:
                        offset = item.pos() - primary_pos
                        self._group_offsets[item] = offset
                        # Add to selected items for position tracking
                        if item not in selected_items:
                            selected_items.append(item)

        # Store initial positions
        for it in selected_items:
            self._item_positions[it] = QtCore.QPointF(it.pos())

            # Track rotations if in rotation mode
            if is_rotation_mode and isinstance(it, (BaseObj, RectangleItem)):
                self._item_rotations[it] = it.rotation()

        # For group rotation, track initial positions for orbit calculation
        if is_rotation_mode and len(selected_items) > 1:
            self._item_group_states = {
                "items": selected_items,
                "initial_positions": {it: QtCore.QPointF(it.pos()) for it in selected_items},
                "initial_rotations": {
                    it: it.rotation()
                    for it in selected_items
                    if isinstance(it, (BaseObj, RectangleItem))
                },
            }

    def update_group_positions(self) -> None:
        """
        Update positions of all group members during drag.

        Should be called during mouse move when dragging grouped items.
        Moves all group members relative to the primary drag item.
        """
        if not self._dragging_group or not self._primary_drag_item:
            return

        primary_pos = self._primary_drag_item.pos()

        for item, offset in self._group_offsets.items():
            # Temporarily disable signals to prevent cascading updates
            if hasattr(item, "blockSignals"):
                item.blockSignals(True)
            
            new_pos = primary_pos + offset
            item.setPos(new_pos)
            
            if hasattr(item, "blockSignals"):
                item.blockSignals(False)

    def is_dragging_group(self) -> bool:
        """Check if currently dragging a group."""
        return self._dragging_group

    def handle_mouse_release(self) -> bool:
        """
        Handle mouse release - snap to grid and create undo commands.

        Returns:
            True if any commands were created
        """
        from ...core.undo_commands import MoveItemCommand, RotateItemCommand, RotateItemsCommand
        from ...objects import BaseObj, RectangleItem

        # Clear snap guides
        if hasattr(self.view, "clear_snap_guides"):
            self.view.clear_snap_guides()  # type: ignore[attr-defined]

        commands_created = False

        # Check if this was a group rotation
        was_group_rotation = bool(self._item_group_states and "items" in self._item_group_states)

        # Apply snap to grid and create move commands
        for it in list(self._item_positions.keys()):
            if isinstance(it, BaseObj) and self._get_snap_to_grid():
                p = it.pos()
                it.setPos(round(p.x()), round(p.y()))

            # Create move command if item was moved (and not rotated)
            if it not in self._item_rotations:
                old_pos = self._item_positions[it]
                new_pos = it.pos()
                if old_pos != new_pos:
                    move_cmd = MoveItemCommand(it, old_pos, new_pos)
                    self.undo_stack.push(move_cmd)
                    commands_created = True

        # Handle rotation commands
        if self._item_rotations and not was_group_rotation:
            # Single item rotation(s)
            for it, old_rotation in self._item_rotations.items():
                new_rotation = it.rotation()
                if abs(new_rotation - old_rotation) > 0.01:
                    rot_cmd: RotateItemCommand = RotateItemCommand(it, old_rotation, new_rotation)
                    self.undo_stack.push(rot_cmd)
                    commands_created = True

        elif was_group_rotation:
            # Group rotation
            items = self._item_group_states["items"]
            old_positions = self._item_group_states["initial_positions"]
            old_rotations = self._item_group_states["initial_rotations"]
            new_positions = {it: it.pos() for it in items}
            new_rotations = {
                it: it.rotation() for it in items if isinstance(it, (BaseObj, RectangleItem))
            }

            # Check if anything actually changed
            position_changed = any(
                old_positions[it] != new_positions[it] for it in items if it in old_positions
            )
            rotation_changed = any(
                abs(old_rotations.get(it, 0) - new_rotations.get(it, 0)) > 0.01
                for it in items
                if isinstance(it, (BaseObj, RectangleItem))
            )

            if position_changed or rotation_changed:
                rotatable_items = [it for it in items if isinstance(it, (BaseObj, RectangleItem))]
                if rotatable_items:
                    # Convert to QGraphicsItem types for RotateItemsCommand
                    from PyQt6.QtWidgets import QGraphicsItem

                    rotatable_items_typed: list[QGraphicsItem] = [
                        it for it in rotatable_items
                    ]  # type: ignore[list-item]
                    old_positions_typed: dict[QGraphicsItem, QtCore.QPointF] = {
                        it: old_positions[it] for it in rotatable_items if it in old_positions
                    }  # type: ignore[dict-item]
                    new_positions_typed: dict[QGraphicsItem, QtCore.QPointF] = {
                        it: new_positions[it] for it in rotatable_items if it in new_positions
                    }  # type: ignore[dict-item]
                    old_rotations_typed: dict[QGraphicsItem, float] = {
                        it: old_rotations[it] for it in rotatable_items if it in old_rotations
                    }  # type: ignore[dict-item]
                    new_rotations_typed: dict[QGraphicsItem, float] = {
                        it: new_rotations[it] for it in rotatable_items if it in new_rotations
                    }  # type: ignore[dict-item]
                    rot_items_cmd: RotateItemsCommand = RotateItemsCommand(
                        rotatable_items_typed,
                        old_positions_typed,
                        new_positions_typed,
                        old_rotations_typed,
                        new_rotations_typed,
                    )
                    self.undo_stack.push(rot_items_cmd)
                    commands_created = True

        # Clear tracking state
        self._item_positions.clear()
        self._item_rotations.clear()
        self._item_group_states.clear()
        self._dragging_group = False
        self._group_items.clear()
        self._group_offsets.clear()
        self._primary_drag_item = None

        # Schedule retrace
        self._schedule_retrace()

        return commands_created
