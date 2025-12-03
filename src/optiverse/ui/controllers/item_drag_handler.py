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

    # Class-level tracking for multi-selection drag (used by BaseObj to block movement)
    _current_secondary_items: set[QtWidgets.QGraphicsItem] = set()
    # Class-level storage for secondary item offsets (used by BaseObj to get correct position)
    _secondary_item_offsets: dict[QtWidgets.QGraphicsItem, QtCore.QPointF] = {}
    # Class-level reference to primary drag item (used by BaseObj to calculate position)
    _current_primary_item: QtWidgets.QGraphicsItem | None = None
    # Class-level storage for primary item's target position (updated during itemChange)
    _primary_target_position: QtCore.QPointF | None = None

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
        
        # Group movement tracking (for LayerGroup items)
        self._dragging_group = False
        self._group_items: list[QtWidgets.QGraphicsItem] = []
        self._group_offsets: dict[QtWidgets.QGraphicsItem, QtCore.QPointF] = {}
        self._primary_drag_item: QtWidgets.QGraphicsItem | None = None
        self._last_primary_pos: QtCore.QPointF | None = None  # For delta calculation
        
        # Multi-selection tracking (for any multi-selected items, not just groups)
        self._dragging_multi_selection = False
        self._multi_selection_offsets: dict[QtWidgets.QGraphicsItem, QtCore.QPointF] = {}

    @classmethod
    def is_secondary_drag_item(cls, item: QtWidgets.QGraphicsItem) -> bool:
        """Check if an item is a secondary item in a multi-selection drag.
        
        Secondary items should block Qt's automatic movement and instead
        follow the primary item to preserve relative positions.
        """
        return item in cls._current_secondary_items

    @classmethod
    def get_secondary_item_target_pos(cls, item: QtWidgets.QGraphicsItem) -> QtCore.QPointF | None:
        """Get the correct target position for a secondary item.
        
        Returns the position based on primary item's TARGET position (after snap) + stored offset,
        or None if this item is not a secondary drag item.
        
        Uses _primary_target_position if available (set during primary's itemChange),
        otherwise falls back to primary.pos().
        """
        if item not in cls._current_secondary_items:
            return None
        if cls._current_primary_item is None:
            return None
        offset = cls._secondary_item_offsets.get(item)
        if offset is None:
            return None
        # Use target position if available (set during primary's itemChange), otherwise use current
        primary_pos = cls._primary_target_position if cls._primary_target_position is not None else cls._current_primary_item.pos()
        return primary_pos + offset
    
    @classmethod
    def set_primary_target_position(cls, target_pos: QtCore.QPointF) -> None:
        """Set the primary item's target position (called from primary's itemChange after snap)."""
        cls._primary_target_position = target_pos

    def set_group_manager(self, group_manager: GroupManager) -> None:
        """Set the group manager for group movement support."""
        self._group_manager = group_manager

    def handle_mouse_press(self, event: QtGui.QMouseEvent):
        """
        Track item positions and rotations on mouse press.
        
        Legacy method - prefer handle_mouse_press_at_scene_pos for correct coordinates.
        """
        # Map view coordinates to scene coordinates
        if hasattr(self.view, "mapToScene"):
            scene_pos = self.view.mapToScene(event.pos())
        else:
            scene_pos = QtCore.QPointF(event.pos())
        self.handle_mouse_press_at_scene_pos(scene_pos, event.modifiers())

    def handle_mouse_press_at_scene_pos(
        self, scene_pos: QtCore.QPointF, modifiers: QtCore.Qt.KeyboardModifier
    ):
        """
        Track item positions and rotations on mouse press.

        Also handles group movement - when one grouped item is pressed,
        all group members are tracked for coordinated movement.

        Args:
            scene_pos: Mouse position in scene coordinates
            modifiers: Keyboard modifiers active during press
        """
        from ...objects import BaseObj, RectangleItem
        from ...objects.annotations import RulerItem, TextNoteItem

        # Check if this is a rotation operation (Ctrl modifier)
        is_rotation_mode = modifiers & QtCore.Qt.KeyboardModifier.ControlModifier

        # Clear previous tracking state
        self._item_positions.clear()
        self._item_rotations.clear()
        self._item_group_states.clear()
        self._dragging_group = False
        self._group_items.clear()
        self._group_offsets.clear()
        self._primary_drag_item = None
        self._last_primary_pos = None
        self._dragging_multi_selection = False
        self._multi_selection_offsets.clear()
        # Clear class-level state
        ItemDragHandler._current_secondary_items.clear()
        ItemDragHandler._secondary_item_offsets.clear()
        ItemDragHandler._current_primary_item = None
        ItemDragHandler._primary_target_position = None

        # Get already-selected items
        selected_items = [
            it
            for it in self.scene.selectedItems()
            if isinstance(it, (BaseObj, RulerItem, TextNoteItem, RectangleItem))
        ]

        # Find the item under the mouse cursor (the one being directly dragged)
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
                # Store initial primary position for delta calculation
                self._last_primary_pos = QtCore.QPointF(self._primary_drag_item.pos())
                # Store offsets relative to primary item (for reference)
                primary_pos = self._primary_drag_item.pos()
                for item in grouped_items:
                    if item != self._primary_drag_item:
                        offset = item.pos() - primary_pos
                        self._group_offsets[item] = offset
                        # Add to selected items for position tracking
                        if item not in selected_items:
                            selected_items.append(item)

        # Track secondary items for multi-selection drag
        # This applies to both grouped items AND multiple selected items
        if self._primary_drag_item and len(selected_items) > 1:
            self._dragging_multi_selection = True
            primary_pos = self._primary_drag_item.pos()
            # Set class-level primary reference for BaseObj.itemChange()
            ItemDragHandler._current_primary_item = self._primary_drag_item
            
            for item in selected_items:
                if item != self._primary_drag_item:
                    # Store offset relative to primary
                    offset = item.pos() - primary_pos
                    self._multi_selection_offsets[item] = offset
                    # Set class-level tracking for BaseObj.itemChange()
                    ItemDragHandler._current_secondary_items.add(item)
                    ItemDragHandler._secondary_item_offsets[item] = offset
            
            # Initialize last primary position for update_group_positions
            if self._last_primary_pos is None:
                self._last_primary_pos = QtCore.QPointF(primary_pos)

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
        Update positions of all secondary items during drag.

        Uses offset-based positioning: each secondary item is placed at
        primary.pos() + stored_offset. This correctly handles magnetic snap
        by preserving relative positions regardless of where the primary snaps.
        
        Handles both LayerGroup items and arbitrary multi-selection.
        """
        if not self._primary_drag_item:
            return
        
        # Must be dragging either a group or multi-selection
        if not self._dragging_group and not self._dragging_multi_selection:
            return

        primary_pos = self._primary_drag_item.pos()

        # For grouped items, use offset-based positioning
        for item, offset in self._group_offsets.items():
            item.setPos(primary_pos + offset)
        
        # For multi-selected items (may overlap with group), use offset-based positioning
        for item, offset in self._multi_selection_offsets.items():
            # Don't double-move items that are already in _group_offsets
            if item not in self._group_offsets:
                item.setPos(primary_pos + offset)

        # Update last position (still needed for undo tracking)
        self._last_primary_pos = QtCore.QPointF(primary_pos)

    def is_dragging_group(self) -> bool:
        """Check if currently dragging a group or multi-selection."""
        return self._dragging_group or self._dragging_multi_selection

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
        self._last_primary_pos = None
        self._dragging_multi_selection = False
        self._multi_selection_offsets.clear()
        # Clear class-level state
        ItemDragHandler._current_secondary_items.clear()
        ItemDragHandler._secondary_item_offsets.clear()
        ItemDragHandler._current_primary_item = None
        ItemDragHandler._primary_target_position = None

        # Schedule retrace
        self._schedule_retrace()

        return commands_created
