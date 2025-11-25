"""
Handler for item drag, move, and rotation tracking.

Extracts position/rotation tracking and undo command creation from MainWindow.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Any

from PyQt6 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
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
        undo_stack: "UndoStack",
        snap_to_grid_getter: callable,
        schedule_retrace: callable,
    ):
        """
        Initialize the drag handler.

        Args:
            scene: Graphics scene containing items
            view: Graphics view for snap guide clearing
            undo_stack: Undo stack for command creation
            snap_to_grid_getter: Callable returning whether snap to grid is enabled
            schedule_retrace: Callable to schedule ray retracing
        """
        self.scene = scene
        self.view = view
        self.undo_stack = undo_stack
        self._get_snap_to_grid = snap_to_grid_getter
        self._schedule_retrace = schedule_retrace

        # Position tracking state
        self._item_positions: Dict[QtWidgets.QGraphicsItem, QtCore.QPointF] = {}
        self._item_rotations: Dict[QtWidgets.QGraphicsItem, float] = {}
        self._item_group_states: Dict[str, Any] = {}

    def handle_mouse_press(self, event: QtGui.QMouseEvent):
        """
        Track item positions and rotations on mouse press.

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

        # Get already-selected items
        selected_items = [
            it for it in self.scene.selectedItems()
            if isinstance(it, (BaseObj, RulerItem, TextNoteItem, RectangleItem))
        ]

        # Also track the item under the mouse cursor (may not be selected yet)
        clicked_item = self.scene.itemAt(event.scenePos(), QtGui.QTransform())

        # Walk up parent hierarchy to find the actual draggable item
        while clicked_item is not None:
            if isinstance(clicked_item, (BaseObj, RulerItem, TextNoteItem, RectangleItem)):
                if clicked_item not in selected_items:
                    selected_items.append(clicked_item)
                break
            clicked_item = clicked_item.parentItem()

        # Store initial positions
        for it in selected_items:
            self._item_positions[it] = QtCore.QPointF(it.pos())

            # Track rotations if in rotation mode
            if is_rotation_mode and isinstance(it, (BaseObj, RectangleItem)):
                self._item_rotations[it] = it.rotation()

        # For group rotation, track initial positions for orbit calculation
        if is_rotation_mode and len(selected_items) > 1:
            self._item_group_states = {
                'items': selected_items,
                'initial_positions': {it: QtCore.QPointF(it.pos()) for it in selected_items},
                'initial_rotations': {
                    it: it.rotation()
                    for it in selected_items
                    if isinstance(it, (BaseObj, RectangleItem))
                }
            }

    def handle_mouse_release(self) -> bool:
        """
        Handle mouse release - snap to grid and create undo commands.

        Returns:
            True if any commands were created
        """
        from ...objects import BaseObj, RectangleItem
        from ...core.undo_commands import MoveItemCommand, RotateItemCommand, RotateItemsCommand

        # Clear snap guides
        self.view.clear_snap_guides()

        commands_created = False

        # Check if this was a group rotation
        was_group_rotation = bool(self._item_group_states and 'items' in self._item_group_states)

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
                    cmd = MoveItemCommand(it, old_pos, new_pos)
                    self.undo_stack.push(cmd)
                    commands_created = True

        # Handle rotation commands
        if self._item_rotations and not was_group_rotation:
            # Single item rotation(s)
            for it, old_rotation in self._item_rotations.items():
                new_rotation = it.rotation()
                if abs(new_rotation - old_rotation) > 0.01:
                    cmd = RotateItemCommand(it, old_rotation, new_rotation)
                    self.undo_stack.push(cmd)
                    commands_created = True

        elif was_group_rotation:
            # Group rotation
            items = self._item_group_states['items']
            old_positions = self._item_group_states['initial_positions']
            old_rotations = self._item_group_states['initial_rotations']
            new_positions = {it: it.pos() for it in items}
            new_rotations = {
                it: it.rotation()
                for it in items
                if isinstance(it, (BaseObj, RectangleItem))
            }

            # Check if anything actually changed
            position_changed = any(
                old_positions[it] != new_positions[it]
                for it in items if it in old_positions
            )
            rotation_changed = any(
                abs(old_rotations.get(it, 0) - new_rotations.get(it, 0)) > 0.01
                for it in items if isinstance(it, (BaseObj, RectangleItem))
            )

            if position_changed or rotation_changed:
                rotatable_items = [
                    it for it in items
                    if isinstance(it, (BaseObj, RectangleItem))
                ]
                if rotatable_items:
                    cmd = RotateItemsCommand(
                        rotatable_items,
                        old_positions,
                        new_positions,
                        old_rotations,
                        new_rotations
                    )
                    self.undo_stack.push(cmd)
                    commands_created = True

        # Clear tracking state
        self._item_positions.clear()
        self._item_rotations.clear()
        self._item_group_states.clear()

        # Schedule retrace
        self._schedule_retrace()

        return commands_created



