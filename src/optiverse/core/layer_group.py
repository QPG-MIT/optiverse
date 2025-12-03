"""
Layer group model for organizing scene items.

Groups are a logical concept stored separately from Qt item hierarchy.
When any item in a group is moved, all group members move together.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from PyQt6 import QtCore, QtWidgets

if TYPE_CHECKING:
    pass


@dataclass
class LayerGroup:
    """
    Data model for a group of scene items.

    Groups are identified by UUID and contain references to item UUIDs.
    The visual hierarchy is managed by the LayerPanel, not Qt's item groups.
    Supports nested groups via parent_group_uuid.
    """

    name: str
    item_uuids: list[str] = field(default_factory=list)
    group_uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    collapsed: bool = False  # UI state for layer panel
    z_base: float = 0.0  # Base z-value for the group
    parent_group_uuid: str | None = None  # UUID of parent group (for nested groups)

    def to_dict(self) -> dict[str, Any]:
        """Serialize group to dictionary."""
        data = {
            "name": self.name,
            "item_uuids": self.item_uuids.copy(),
            "group_uuid": self.group_uuid,
            "collapsed": self.collapsed,
            "z_base": self.z_base,
        }
        if self.parent_group_uuid is not None:
            data["parent_group_uuid"] = self.parent_group_uuid
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LayerGroup:
        """Deserialize group from dictionary."""
        return cls(
            name=data.get("name", "Group"),
            item_uuids=data.get("item_uuids", []),
            group_uuid=data.get("group_uuid", str(uuid.uuid4())),
            collapsed=data.get("collapsed", False),
            z_base=data.get("z_base", 0.0),
            parent_group_uuid=data.get("parent_group_uuid"),
        )


class GroupManager(QtCore.QObject):
    """
    Manages layer groups for a scene.

    Provides operations for creating, modifying, and querying groups.
    Emits signals when groups change for UI updates.
    """

    # Signals
    groupsChanged = QtCore.pyqtSignal()  # Emitted when any group changes
    groupCreated = QtCore.pyqtSignal(str)  # Emitted with group_uuid when created
    groupDeleted = QtCore.pyqtSignal(str)  # Emitted with group_uuid when deleted

    def __init__(self, scene: QtWidgets.QGraphicsScene | None = None):
        super().__init__()
        self._scene = scene
        self._groups: dict[str, LayerGroup] = {}  # group_uuid -> LayerGroup
        self._item_to_group: dict[str, str] = {}  # item_uuid -> group_uuid

    def set_scene(self, scene: QtWidgets.QGraphicsScene) -> None:
        """Set the scene this manager operates on."""
        self._scene = scene

    @property
    def scene(self) -> QtWidgets.QGraphicsScene | None:
        """Get the associated scene."""
        return self._scene

    def create_group(
        self,
        name: str,
        item_uuids: list[str] | None = None,
        parent_group_uuid: str | None = None,
    ) -> LayerGroup:
        """
        Create a new group with the given name and optional items.

        Args:
            name: Display name for the group
            item_uuids: Optional list of item UUIDs to add to the group
            parent_group_uuid: Optional UUID of a parent group (for nested groups)

        Returns:
            The created LayerGroup
        """
        group = LayerGroup(
            name=name,
            item_uuids=item_uuids or [],
            parent_group_uuid=parent_group_uuid,
        )

        # Calculate z_base from items
        if item_uuids and self._scene:
            z_values = []
            for item in self._scene.items():
                if hasattr(item, "item_uuid") and item.item_uuid in item_uuids:
                    z_values.append(item.zValue())
            if z_values:
                group.z_base = max(z_values)

        self._groups[group.group_uuid] = group

        # Update item-to-group mapping
        for item_uuid in group.item_uuids:
            self._item_to_group[item_uuid] = group.group_uuid

        self.groupCreated.emit(group.group_uuid)
        self.groupsChanged.emit()
        return group

    def delete_group(self, group_uuid: str, keep_items: bool = True) -> None:
        """
        Delete a group and all its child groups.

        Args:
            group_uuid: UUID of the group to delete
            keep_items: If True, items remain in scene (ungrouped).
                       If False, items are also deleted from scene.
        """
        if group_uuid not in self._groups:
            return

        # First, recursively delete all child groups
        child_groups = self.get_child_groups(group_uuid)
        for child_group in child_groups:
            self.delete_group(child_group.group_uuid, keep_items=keep_items)

        group = self._groups.get(group_uuid)
        if not group:
            return  # Already deleted

        # Remove items from scene if requested
        if not keep_items and self._scene:
            for item in list(self._scene.items()):
                if hasattr(item, "item_uuid") and item.item_uuid in group.item_uuids:
                    self._scene.removeItem(item)

        # Clear item-to-group mapping
        for item_uuid in group.item_uuids:
            if self._item_to_group.get(item_uuid) == group_uuid:
                del self._item_to_group[item_uuid]

        del self._groups[group_uuid]
        self.groupDeleted.emit(group_uuid)
        self.groupsChanged.emit()

    def add_item_to_group(self, item_uuid: str, group_uuid: str) -> bool:
        """
        Add an item to a group.

        Args:
            item_uuid: UUID of the item to add
            group_uuid: UUID of the group

        Returns:
            True if successful, False if group doesn't exist
        """
        if group_uuid not in self._groups:
            return False

        # Remove from current group if in one
        current_group = self._item_to_group.get(item_uuid)
        if current_group and current_group != group_uuid:
            self.remove_item_from_group(item_uuid)

        group = self._groups[group_uuid]
        if item_uuid not in group.item_uuids:
            group.item_uuids.append(item_uuid)
            self._item_to_group[item_uuid] = group_uuid
            self.groupsChanged.emit()

        return True

    def remove_item_from_group(self, item_uuid: str) -> bool:
        """
        Remove an item from its group.

        If the group becomes empty (no items and no child groups), it is
        automatically deleted.

        Args:
            item_uuid: UUID of the item to remove

        Returns:
            True if item was in a group, False otherwise
        """
        group_uuid = self._item_to_group.get(item_uuid)
        if not group_uuid:
            return False

        if group_uuid in self._groups:
            group = self._groups[group_uuid]
            if item_uuid in group.item_uuids:
                group.item_uuids.remove(item_uuid)

            # Auto-delete empty groups (no items and no child groups)
            if not group.item_uuids and not self.get_child_groups(group_uuid):
                # Delete the empty group (keep_items=True since there are none)
                del self._item_to_group[item_uuid]
                self.delete_group(group_uuid, keep_items=True)
                return True

        del self._item_to_group[item_uuid]
        self.groupsChanged.emit()
        return True

    def get_group(self, group_uuid: str) -> LayerGroup | None:
        """Get a group by UUID."""
        return self._groups.get(group_uuid)

    def get_item_group(self, item_uuid: str) -> LayerGroup | None:
        """Get the group containing an item, or None if not grouped."""
        group_uuid = self._item_to_group.get(item_uuid)
        if group_uuid:
            return self._groups.get(group_uuid)
        return None

    def get_group_items(self, group_uuid: str) -> list[QtWidgets.QGraphicsItem]:
        """
        Get all scene items in a group.

        Args:
            group_uuid: UUID of the group

        Returns:
            List of QGraphicsItem objects in the group
        """
        if group_uuid not in self._groups or not self._scene:
            return []

        group = self._groups[group_uuid]
        items = []
        for item in self._scene.items():
            if hasattr(item, "item_uuid") and item.item_uuid in group.item_uuids:
                items.append(item)
        return items

    def get_grouped_items(self, item: QtWidgets.QGraphicsItem) -> list[QtWidgets.QGraphicsItem]:
        """
        Get all items grouped with the given item (including itself).

        Args:
            item: A scene item that may be in a group

        Returns:
            List of all items in the same group, or [item] if not grouped
        """
        if not hasattr(item, "item_uuid"):
            return [item]

        group = self.get_item_group(item.item_uuid)
        if not group:
            return [item]

        return self.get_group_items(group.group_uuid)

    def is_item_grouped(self, item_uuid: str) -> bool:
        """Check if an item is in a group."""
        return item_uuid in self._item_to_group

    def get_all_groups(self) -> list[LayerGroup]:
        """Get all groups."""
        return list(self._groups.values())

    def get_root_groups(self) -> list[LayerGroup]:
        """Get all top-level groups (groups with no parent)."""
        return [g for g in self._groups.values() if g.parent_group_uuid is None]

    def get_child_groups(self, parent_uuid: str) -> list[LayerGroup]:
        """
        Get all groups that are children of the specified parent group.

        Args:
            parent_uuid: UUID of the parent group

        Returns:
            List of child groups
        """
        return [g for g in self._groups.values() if g.parent_group_uuid == parent_uuid]

    def rename_group(self, group_uuid: str, new_name: str) -> bool:
        """
        Rename a group.

        Args:
            group_uuid: UUID of the group to rename
            new_name: New name for the group

        Returns:
            True if successful, False if group doesn't exist
        """
        if group_uuid not in self._groups:
            return False

        self._groups[group_uuid].name = new_name
        self.groupsChanged.emit()
        return True

    def set_group_collapsed(self, group_uuid: str, collapsed: bool) -> None:
        """Set the collapsed state of a group (for UI)."""
        if group_uuid in self._groups:
            self._groups[group_uuid].collapsed = collapsed

    def clear(self) -> None:
        """Clear all groups."""
        self._groups.clear()
        self._item_to_group.clear()
        self.groupsChanged.emit()

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Serialize all groups to a list of dictionaries."""
        return [group.to_dict() for group in self._groups.values()]

    def from_dict_list(self, data: list[dict[str, Any]]) -> None:
        """Load groups from a list of dictionaries (clears existing groups)."""
        self.clear()
        for group_data in data:
            group = LayerGroup.from_dict(group_data)
            self._groups[group.group_uuid] = group
            for item_uuid in group.item_uuids:
                self._item_to_group[item_uuid] = group.group_uuid
        self.groupsChanged.emit()

    def import_groups_from_dict_list(
        self, data: list[dict[str, Any]]
    ) -> list[LayerGroup]:
        """
        Import groups from a list of dictionaries without clearing existing groups.

        Args:
            data: List of group dictionaries to import

        Returns:
            List of imported LayerGroup objects
        """
        imported_groups = []
        for group_data in data:
            group = LayerGroup.from_dict(group_data)
            self._groups[group.group_uuid] = group
            for item_uuid in group.item_uuids:
                self._item_to_group[item_uuid] = group.group_uuid
            imported_groups.append(group)
        self.groupsChanged.emit()
        return imported_groups

    def group_selected_items(self, name: str = "Group") -> LayerGroup | None:
        """
        Create a group from currently selected items in the scene.

        Args:
            name: Name for the new group

        Returns:
            The created group, or None if no items selected
        """
        if not self._scene:
            return None

        selected = self._scene.selectedItems()
        if not selected:
            return None

        # Get UUIDs of selected items
        item_uuids = []
        for item in selected:
            if hasattr(item, "item_uuid"):
                item_uuids.append(item.item_uuid)

        if not item_uuids:
            return None

        return self.create_group(name, item_uuids)

    def ungroup(self, group_uuid: str) -> None:
        """
        Ungroup items in a group (keep items, delete group).

        Args:
            group_uuid: UUID of the group to ungroup
        """
        self.delete_group(group_uuid, keep_items=True)

    def add_group(self, group: LayerGroup) -> None:
        """
        Add an existing LayerGroup to the manager.

        Useful for importing groups from files.

        Args:
            group: The LayerGroup to add
        """
        self._groups[group.group_uuid] = group

        # Update item-to-group mapping
        for item_uuid in group.item_uuids:
            self._item_to_group[item_uuid] = group.group_uuid

        self.groupCreated.emit(group.group_uuid)
        self.groupsChanged.emit()

    def set_group_parent(self, group_uuid: str, parent_uuid: str | None) -> bool:
        """
        Set the parent group for a group.

        Args:
            group_uuid: UUID of the group to modify
            parent_uuid: UUID of the new parent group, or None to make it a root group

        Returns:
            True if successful, False if group doesn't exist
        """
        if group_uuid not in self._groups:
            return False

        self._groups[group_uuid].parent_group_uuid = parent_uuid
        self.groupsChanged.emit()
        return True

