"""
Command pattern implementation for undo/redo functionality.
Each command encapsulates an action that can be executed and undone.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from PyQt6 import QtCore

from .protocols import Editable, HasParams, Undoable

if TYPE_CHECKING:
    from PyQt6 import QtWidgets

    from .layer_group import GroupManager


class Command(ABC):
    """Abstract base class for undoable commands."""

    @abstractmethod
    def execute(self) -> None:
        """Execute the command."""
        pass

    @abstractmethod
    def undo(self) -> None:
        """Undo the command."""
        pass

    def id(self) -> int:
        """Return command ID for merging. Return -1 to disable merging."""
        return -1

    def merge_with(self, other: Command) -> bool:
        """Attempt to merge with another command. Return True if successful."""
        return False


class AddItemCommand(Command):
    """Command to add an item to the scene."""

    def __init__(self, scene: QtWidgets.QGraphicsScene, item: QtWidgets.QGraphicsItem):
        """
        Initialize AddItemCommand.

        Args:
            scene: The graphics scene to add the item to
            item: The graphics item to add
        """
        self.scene = scene
        self.item = item
        self._executed = False

    def execute(self) -> None:
        """Add the item to the scene."""
        if not self._executed:
            self.scene.addItem(self.item)
            self._executed = True

    def undo(self) -> None:
        """Remove the item from the scene."""
        if self._executed:
            self.scene.removeItem(self.item)
            self._executed = False


class RemoveItemCommand(Command):
    """Command to remove an item from the scene."""

    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        item: QtWidgets.QGraphicsItem,
        group_manager: GroupManager | None = None,
    ):
        """
        Initialize RemoveItemCommand.

        Args:
            scene: The graphics scene to remove the item from
            item: The graphics item to remove
            group_manager: Optional group manager for group membership cleanup
        """
        self.scene = scene
        self.item = item
        self._group_manager = group_manager
        self._executed = False

        # Store group membership and full group data for undo support
        self._group_uuid: str | None = None
        self._group_data: dict[str, Any] | None = None
        if group_manager and hasattr(item, "item_uuid"):
            group = group_manager.get_item_group(item.item_uuid)
            if group:
                self._group_uuid = group.group_uuid
                # Store full group data in case it gets auto-deleted
                self._group_data = group.to_dict()

    def execute(self) -> None:
        """Remove the item from the scene and its group."""
        if not self._executed:
            # Remove from group first (triggers auto-delete if empty)
            if self._group_manager and hasattr(self.item, "item_uuid"):
                self._group_manager.remove_item_from_group(self.item.item_uuid)
            self.scene.removeItem(self.item)
            self._executed = True

    def undo(self) -> None:
        """Add the item back to the scene and restore group membership."""
        if self._executed:
            self.scene.addItem(self.item)
            # Restore group membership (recreate group if it was auto-deleted)
            if self._group_manager and self._group_uuid and hasattr(self.item, "item_uuid"):
                # Recreate group if it was auto-deleted
                if not self._group_manager.get_group(self._group_uuid) and self._group_data:
                    from .layer_group import LayerGroup

                    group = LayerGroup.from_dict(self._group_data)
                    self._group_manager.add_group(group)

                # Add item back to group
                self._group_manager.add_item_to_group(self.item.item_uuid, self._group_uuid)
            self._executed = False


class MoveItemCommand(Command):
    """Command to move an item to a new position."""

    def __init__(
        self,
        item: QtWidgets.QGraphicsItem,
        old_pos: QtCore.QPointF,
        new_pos: QtCore.QPointF,
    ):
        """
        Initialize MoveItemCommand.

        Args:
            item: The graphics item to move
            old_pos: The original position
            new_pos: The new position
        """
        self.item = item
        self.old_pos = QtCore.QPointF(old_pos)  # Make a copy
        self.new_pos = QtCore.QPointF(new_pos)  # Make a copy

    def execute(self) -> None:
        """Move the item to the new position."""
        self.item.setPos(self.new_pos)
        # Force Qt to update cached transforms (fixes BeamsplitterItem position tracking)
        self.item.setTransform(self.item.transform())

    def undo(self) -> None:
        """Move the item back to the old position."""
        self.item.setPos(self.old_pos)
        # Force Qt to update cached transforms (fixes BeamsplitterItem position tracking)
        self.item.setTransform(self.item.transform())

    def id(self) -> int:
        """Return unique ID for this item to enable command merging."""
        return id(self.item)

    def merge_with(self, other: Command) -> bool:
        """Merge with another MoveItemCommand for the same item."""
        if not isinstance(other, MoveItemCommand):
            return False
        if other.item is not self.item:
            return False
        # Update new position to include the other command's movement
        self.new_pos = QtCore.QPointF(other.new_pos)
        return True


class AddMultipleItemsCommand(Command):
    """Command to add multiple items to the scene in a single operation."""

    def __init__(self, scene: QtWidgets.QGraphicsScene, items: list[QtWidgets.QGraphicsItem]):
        """
        Initialize AddMultipleItemsCommand.

        Args:
            scene: The graphics scene to add items to
            items: The list of graphics items to add
        """
        self.scene = scene
        self.items = items
        self._executed = False

    def execute(self) -> None:
        """Add all items to the scene."""
        if not self._executed:
            for item in self.items:
                self.scene.addItem(item)
            self._executed = True

    def undo(self) -> None:
        """Remove all items from the scene."""
        if self._executed:
            for item in self.items:
                self.scene.removeItem(item)
            self._executed = False


class RemoveMultipleItemsCommand(Command):
    """Command to remove multiple items from the scene in a single operation."""

    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        items: list[QtWidgets.QGraphicsItem],
        group_manager: GroupManager | None = None,
    ):
        """
        Initialize RemoveMultipleItemsCommand.

        Args:
            scene: The graphics scene to remove items from
            items: The list of graphics items to remove
            group_manager: Optional group manager for group membership cleanup
        """
        self.scene = scene
        self.items = items
        self._group_manager = group_manager
        self._executed = False

        # Store group memberships and full group data for undo support
        self._item_groups: dict[str, str] = {}  # item_uuid -> group_uuid
        self._group_data: dict[str, dict[str, Any]] = {}  # group_uuid -> group data
        if group_manager:
            for item in items:
                if hasattr(item, "item_uuid"):
                    group = group_manager.get_item_group(item.item_uuid)
                    if group:
                        self._item_groups[item.item_uuid] = group.group_uuid
                        # Store full group data (avoid duplicates)
                        if group.group_uuid not in self._group_data:
                            self._group_data[group.group_uuid] = group.to_dict()

    def execute(self) -> None:
        """Remove all items from the scene and their groups."""
        if not self._executed:
            # Remove from groups first (triggers auto-delete if empty)
            if self._group_manager:
                for item in self.items:
                    if hasattr(item, "item_uuid"):
                        self._group_manager.remove_item_from_group(item.item_uuid)
            for item in self.items:
                self.scene.removeItem(item)
            self._executed = True

    def undo(self) -> None:
        """Add all items back to the scene and restore group memberships."""
        if self._executed:
            for item in self.items:
                self.scene.addItem(item)
            # Restore group memberships (recreate groups if they were auto-deleted)
            if self._group_manager:
                # First, recreate any auto-deleted groups
                for group_uuid, group_data in self._group_data.items():
                    if not self._group_manager.get_group(group_uuid):
                        from .layer_group import LayerGroup

                        group = LayerGroup.from_dict(group_data)
                        self._group_manager.add_group(group)

                # Then restore item memberships
                for item in self.items:
                    if hasattr(item, "item_uuid"):
                        group_uuid = self._item_groups.get(item.item_uuid)
                        if group_uuid:
                            self._group_manager.add_item_to_group(item.item_uuid, group_uuid)
            self._executed = False


class PasteItemsCommand(Command):
    """Command to paste multiple items to the scene."""

    def __init__(self, scene: QtWidgets.QGraphicsScene, items: list[QtWidgets.QGraphicsItem]):
        """
        Initialize PasteItemsCommand.

        Args:
            scene: The graphics scene to add items to
            items: The list of graphics items to add
        """
        self.scene = scene
        self.items = items
        self._executed = False

    def execute(self) -> None:
        """Add all items to the scene."""
        if not self._executed:
            for item in self.items:
                self.scene.addItem(item)
            self._executed = True

    def undo(self) -> None:
        """Remove all items from the scene."""
        if self._executed:
            for item in self.items:
                self.scene.removeItem(item)
            self._executed = False


class PropertyChangeCommand(Command):
    """Command to change properties of an item using memento pattern."""

    def __init__(
        self,
        item: Undoable,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
    ):
        """
        Initialize PropertyChangeCommand.

        Args:
            item: The item whose properties changed (must implement Undoable protocol)
            before_state: Dictionary of property values before the change
            after_state: Dictionary of property values after the change
        """
        self.item = item
        self.before_state = before_state
        self.after_state = after_state

    def execute(self) -> None:
        """Apply the after state to the item."""
        self._apply_state(self.after_state)

    def undo(self) -> None:
        """Restore the before state to the item."""
        self._apply_state(self.before_state)

    def _apply_state(self, state: dict[str, Any]) -> None:
        """Apply a state dictionary to the item."""
        # Try custom apply_state method first (Undoable protocol)
        if isinstance(self.item, Undoable):
            self.item.apply_state(state)
            return

        # Fallback: apply each key-value pair
        for key, value in state.items():
            if key == "pos":
                self.item.setPos(QtCore.QPointF(value["x"], value["y"]))
            elif key == "rotation":
                self.item.setRotation(value)
            elif isinstance(self.item, HasParams):
                # For items with params dataclass
                if hasattr(self.item.params, key):
                    setattr(self.item.params, key, value)

        # Trigger updates
        if isinstance(self.item, HasParams):
            self.item._sync_params_from_item()
        if isinstance(self.item, Editable):
            self.item.edited.emit()
        # All QGraphicsItems have update() - no hasattr check needed
        self.item.update()


class RotateItemCommand(Command):
    """Command to rotate an item to a new angle."""

    def __init__(
        self,
        item: QtWidgets.QGraphicsItem,
        old_rotation: float,
        new_rotation: float,
    ):
        """
        Initialize RotateItemCommand.

        Args:
            item: The graphics item to rotate
            old_rotation: The original rotation in degrees
            new_rotation: The new rotation in degrees
        """
        self.item = item
        self.old_rotation = old_rotation
        self.new_rotation = new_rotation

    def execute(self) -> None:
        """Rotate the item to the new angle."""
        self.item.setRotation(self.new_rotation)

    def undo(self) -> None:
        """Rotate the item back to the old angle."""
        self.item.setRotation(self.old_rotation)


class RotateItemsCommand(Command):
    """Command to rotate multiple items together (group rotation)."""

    def __init__(
        self,
        items: list[QtWidgets.QGraphicsItem],
        old_positions: dict[QtWidgets.QGraphicsItem, QtCore.QPointF],
        new_positions: dict[QtWidgets.QGraphicsItem, QtCore.QPointF],
        old_rotations: dict[QtWidgets.QGraphicsItem, float],
        new_rotations: dict[QtWidgets.QGraphicsItem, float],
    ):
        """
        Initialize RotateItemsCommand for group rotation.

        Args:
            items: The list of graphics items to rotate
            old_positions: Dict mapping items to their original positions
            new_positions: Dict mapping items to their new positions
            old_rotations: Dict mapping items to their original rotations
            new_rotations: Dict mapping items to their new rotations
        """
        self.items = items
        self.old_positions = {item: QtCore.QPointF(pos) for item, pos in old_positions.items()}
        self.new_positions = {item: QtCore.QPointF(pos) for item, pos in new_positions.items()}
        self.old_rotations = dict(old_rotations)
        self.new_rotations = dict(new_rotations)

    def execute(self) -> None:
        """Apply new positions and rotations to all items."""
        for item in self.items:
            item.setPos(self.new_positions[item])
            item.setRotation(self.new_rotations[item])

    def undo(self) -> None:
        """Restore old positions and rotations for all items."""
        for item in self.items:
            item.setPos(self.old_positions[item])
            item.setRotation(self.old_rotations[item])


class ZOrderCommand(Command):
    """Command to change z-order (stacking order) of items."""

    def __init__(
        self,
        items: list[QtWidgets.QGraphicsItem],
        old_z_values: dict[QtWidgets.QGraphicsItem, float],
        new_z_values: dict[QtWidgets.QGraphicsItem, float],
    ):
        """
        Initialize ZOrderCommand.

        Args:
            items: The list of graphics items to change z-order for
            old_z_values: Dict mapping items to their original z-values
            new_z_values: Dict mapping items to their new z-values
        """
        self.items = items
        self.old_z_values = dict(old_z_values)
        self.new_z_values = dict(new_z_values)

    def execute(self) -> None:
        """Apply new z-values to all items."""
        for item in self.items:
            item.setZValue(self.new_z_values[item])

    def undo(self) -> None:
        """Restore old z-values for all items."""
        for item in self.items:
            item.setZValue(self.old_z_values[item])


# =============================================================================
# Group Commands
# =============================================================================


class CreateGroupCommand(Command):
    """Command to create a new group."""

    def __init__(
        self,
        group_manager: GroupManager,
        name: str,
        item_uuids: list[str],
        parent_group_uuid: str | None = None,
    ):
        """
        Initialize CreateGroupCommand.

        Args:
            group_manager: The group manager to use
            name: Name of the group
            item_uuids: List of item UUIDs to add to the group
            parent_group_uuid: Optional parent group UUID for nested groups
        """
        from .layer_group import LayerGroup

        self._group_manager = group_manager
        self._name = name
        self._item_uuids = list(item_uuids)
        self._parent_group_uuid = parent_group_uuid
        self._group: LayerGroup | None = None
        self._executed = False

    def execute(self) -> None:
        """Create the group."""
        if not self._executed:
            if self._group:
                # Re-add an existing group (redo case)
                # First remove items from parent group if this is a subgroup
                if self._parent_group_uuid:
                    parent = self._group_manager.get_group(self._parent_group_uuid)
                    if parent:
                        for item_uuid in self._item_uuids:
                            if item_uuid in parent.item_uuids:
                                parent.item_uuids.remove(item_uuid)
                self._group_manager.add_group(self._group)
            else:
                # First time creation
                self._group = self._group_manager.create_group(
                    self._name, self._item_uuids, self._parent_group_uuid
                )
            self._executed = True

    def undo(self) -> None:
        """Delete the group and restore items to parent if this was a subgroup."""
        if self._executed and self._group:
            # Delete the group (keep items)
            self._group_manager.delete_group(self._group.group_uuid, keep_items=True)

            # If this was a subgroup, restore items to parent group
            if self._parent_group_uuid:
                parent = self._group_manager.get_group(self._parent_group_uuid)
                if parent:
                    for item_uuid in self._item_uuids:
                        if item_uuid not in parent.item_uuids:
                            parent.item_uuids.append(item_uuid)
                        self._group_manager._item_to_group[item_uuid] = self._parent_group_uuid
                    self._group_manager.groupsChanged.emit()

            self._executed = False


class DeleteGroupCommand(Command):
    """Command to delete a group."""

    def __init__(
        self,
        group_manager: GroupManager,
        group_uuid: str,
        keep_items: bool = True,
    ):
        """
        Initialize DeleteGroupCommand.

        Args:
            group_manager: The group manager to use
            group_uuid: UUID of the group to delete
            keep_items: If True, items remain in scene (ungrouped)
        """
        self._group_manager = group_manager
        self._group_uuid = group_uuid
        self._keep_items = keep_items
        self._executed = False

        # Store full group data for restoration
        group = group_manager.get_group(group_uuid)
        if group:
            self._group_data: dict[str, Any] | None = group.to_dict()
        else:
            self._group_data = None

        # If not keeping items, store the actual items for restoration
        self._items: list[QtWidgets.QGraphicsItem] = []
        if not keep_items and group:
            self._items = group_manager.get_group_items(group_uuid)

    def execute(self) -> None:
        """Delete the group."""
        if not self._executed and self._group_data:
            self._group_manager.delete_group(self._group_uuid, keep_items=self._keep_items)
            self._executed = True

    def undo(self) -> None:
        """Restore the group."""
        if self._executed and self._group_data:
            from .layer_group import LayerGroup

            # Re-add items to scene if they were deleted
            if not self._keep_items and self._items and self._group_manager.scene:
                for item in self._items:
                    self._group_manager.scene.addItem(item)

            # Recreate the group
            group = LayerGroup.from_dict(self._group_data)
            self._group_manager.add_group(group)
            self._executed = False


class AddItemToGroupCommand(Command):
    """Command to add an item to a group."""

    def __init__(
        self,
        group_manager: GroupManager,
        item_uuid: str,
        group_uuid: str,
    ):
        """
        Initialize AddItemToGroupCommand.

        Args:
            group_manager: The group manager to use
            item_uuid: UUID of the item to add
            group_uuid: UUID of the group to add to
        """
        self._group_manager = group_manager
        self._item_uuid = item_uuid
        self._target_group_uuid = group_uuid
        self._executed = False

        # Store previous group membership (if any)
        prev_group = group_manager.get_item_group(item_uuid)
        self._previous_group_uuid: str | None = prev_group.group_uuid if prev_group else None

    def execute(self) -> None:
        """Add item to the group."""
        if not self._executed:
            self._group_manager.add_item_to_group(self._item_uuid, self._target_group_uuid)
            self._executed = True

    def undo(self) -> None:
        """Remove item from group (restore previous membership if any)."""
        if self._executed:
            self._group_manager.remove_item_from_group(self._item_uuid)
            if self._previous_group_uuid:
                self._group_manager.add_item_to_group(self._item_uuid, self._previous_group_uuid)
            self._executed = False


class RemoveItemFromGroupCommand(Command):
    """Command to remove an item from its group."""

    def __init__(
        self,
        group_manager: GroupManager,
        item_uuid: str,
    ):
        """
        Initialize RemoveItemFromGroupCommand.

        Args:
            group_manager: The group manager to use
            item_uuid: UUID of the item to remove from its group
        """
        self._group_manager = group_manager
        self._item_uuid = item_uuid
        self._executed = False

        # Store group membership for restoration
        group = group_manager.get_item_group(item_uuid)
        self._group_uuid: str | None = group.group_uuid if group else None

        # Store full group data in case it gets auto-deleted
        if group:
            self._group_data: dict[str, Any] | None = group.to_dict()
        else:
            self._group_data = None

    def execute(self) -> None:
        """Remove item from its group."""
        if not self._executed and self._group_uuid:
            self._group_manager.remove_item_from_group(self._item_uuid)
            self._executed = True

    def undo(self) -> None:
        """Restore item to its group (recreate group if auto-deleted)."""
        if self._executed and self._group_uuid:
            # Check if group still exists
            if not self._group_manager.get_group(self._group_uuid) and self._group_data:
                # Recreate the auto-deleted group
                from .layer_group import LayerGroup

                group = LayerGroup.from_dict(self._group_data)
                self._group_manager.add_group(group)

            # Add item back to group
            self._group_manager.add_item_to_group(self._item_uuid, self._group_uuid)
            self._executed = False
