"""Qt item model for the Layer panel tree with drag/drop support.

Integrates with:
- Scene items (QGraphicsItem) for visibility/lock state
- LayerTreeState for hierarchy + order (single source of truth)
- UndoStack for undo/redo support
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets, sip

from ...core.layer_tree_state import LayerNode, LayerTreeState
from ...core.undo_commands import (
    BatchCommand,
    Command,
    MoveNodeCommand,
    RenameNodeCommand,
    ToggleLockCommand,
    ToggleVisibilityCommand,
)

if TYPE_CHECKING:
    from ...core.undo_stack import UndoStack


# Data roles
ITEM_UUID_ROLE = QtCore.Qt.ItemDataRole.UserRole
GROUP_UUID_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
IS_GROUP_ROLE = QtCore.Qt.ItemDataRole.UserRole + 2
IS_LINKED_ROLE = QtCore.Qt.ItemDataRole.UserRole + 3
IS_AUTOLABEL_ROLE = QtCore.Qt.ItemDataRole.UserRole + 4
VISIBLE_ROLE = QtCore.Qt.ItemDataRole.UserRole + 10
LOCKED_ROLE = QtCore.Qt.ItemDataRole.UserRole + 11

MIME_TYPE_LAYER_ITEMS = "application/x-optiverse-layer-item-uuids"


class LayerItemModel(QtCore.QAbstractItemModel):
    """Tree model for layers with drag-drop support."""

    orderChanged = QtCore.pyqtSignal()
    visibilityChanged = QtCore.pyqtSignal()

    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self._scene: QtWidgets.QGraphicsScene | None = None
        self._layer_state: LayerTreeState | None = None
        self._undo_stack: UndoStack | None = None
        self._uuid_to_item: dict[str, QtWidgets.QGraphicsItem] = {}
        self._order: list[str] = []
        # Persistent storage for internal pointer data (prevents GC issues with Qt indexes)
        self._index_data: dict[str, tuple[str, int]] = {}
        # Shutdown flag to prevent data access during Qt cleanup
        self._shutdown: bool = False

    def _is_alive(self, item: QtWidgets.QGraphicsItem) -> bool:
        """Return True if the underlying C++ QGraphicsItem still exists."""
        try:
            return not sip.isdeleted(item)
        except Exception:
            return False

    def _get_live_item(self, uuid: str) -> QtWidgets.QGraphicsItem | None:
        """Look up a cached item by UUID, evicting stale (C++-deleted) entries."""
        item = self._uuid_to_item.get(uuid)
        if item is None:
            return None
        if not self._is_alive(item):
            self._uuid_to_item.pop(uuid, None)
            return None
        return item

    def set_context(
        self,
        *,
        scene: QtWidgets.QGraphicsScene | None,
        layer_state: LayerTreeState | None,
        undo_stack: UndoStack | None,
    ) -> None:
        self._scene = scene
        self._layer_state = layer_state
        self._undo_stack = undo_stack
        self.refresh()

    def refresh(self) -> None:
        self.beginResetModel()
        try:
            self._index_data.clear()
            self._rebuild_caches()
            self._prune_orphan_items()
            self._order = self._layer_state.get_all_items_in_order() if self._layer_state else []
            self._apply_all_effective_states()
        finally:
            self.endResetModel()

    def cleanup(self) -> None:
        """Clear all cached references before shutdown."""
        self._shutdown = True
        self.beginResetModel()
        self._uuid_to_item.clear()
        self._scene = None
        self._layer_state = None
        self.endResetModel()

    def get_order(self) -> list[str]:
        return list(self._order)

    def item_uuids_under(self, index: QtCore.QModelIndex) -> list[str]:
        """Get item UUIDs under index (groups/items expand to all descendants)."""
        node = self._node_from_index(index)
        if not node:
            return []
        if node.is_item():
            uuids = [node.uuid]
            for child in node.children:
                if child.is_item():
                    uuids.append(child.uuid)
            return uuids
        if self._layer_state:
            return self._layer_state.get_group_items_recursive(node.uuid)
        return []

    # --- Qt Model Overrides ---

    def columnCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return 1

    def rowCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        if parent is None:
            parent = QtCore.QModelIndex()
        if not self._layer_state:
            return 0
        if not parent.isValid():
            return len(self._layer_state.get_root_nodes())
        node = self._node_from_index(parent)
        return len(node.children) if node and (node.is_group() or node.children) else 0

    def index(
        self, row: int, column: int, parent: QtCore.QModelIndex | None = None
    ) -> QtCore.QModelIndex:
        if parent is None:
            parent = QtCore.QModelIndex()
        if column != 0 or row < 0 or not self._layer_state:
            return QtCore.QModelIndex()

        if not parent.isValid():
            roots = self._layer_state.get_root_nodes()
            if row >= len(roots):
                return QtCore.QModelIndex()
            return self._create_index(row, column, roots[row].uuid)

        parent_node = self._node_from_index(parent)
        if not parent_node or row >= len(parent_node.children):
            return QtCore.QModelIndex()
        return self._create_index(row, column, parent_node.children[row].uuid)

    def _create_index(self, row: int, column: int, uuid: str) -> QtCore.QModelIndex:
        """Create index with persistent pointer data."""
        if uuid not in self._index_data:
            self._index_data[uuid] = (
                uuid,
                self._layer_state.generation if self._layer_state else 0,
            )
        return self.createIndex(row, column, self._index_data[uuid])

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:  # type: ignore[override]
        if not self._layer_state:
            return QtCore.QModelIndex()
        node = self._node_from_index(index)
        if not node or not node.parent:
            return QtCore.QModelIndex()
        parent_node = node.parent
        siblings = (
            parent_node.parent.children
            if parent_node.parent
            else self._layer_state.get_root_nodes()
        )
        try:
            row = siblings.index(parent_node)
        except ValueError:
            return QtCore.QModelIndex()
        return self._create_index(row, 0, parent_node.uuid)

    def data(
        self, index: QtCore.QModelIndex, role: int = int(QtCore.Qt.ItemDataRole.DisplayRole)
    ) -> object:
        if self._shutdown:
            return None
        node = self._node_from_index(index)
        if not node:
            return None

        if role in (int(QtCore.Qt.ItemDataRole.DisplayRole), int(QtCore.Qt.ItemDataRole.EditRole)):
            return node.name or "Group" if node.is_group() else self._get_item_name(node.uuid)
        if role == int(IS_GROUP_ROLE):
            return node.is_group()
        if role == int(IS_LINKED_ROLE):
            return node.is_linked()
        if role == int(IS_AUTOLABEL_ROLE):
            return node.is_item() and node.parent is not None and node.parent.is_item()
        if role == int(GROUP_UUID_ROLE) and node.is_group():
            return node.uuid
        if role == int(ITEM_UUID_ROLE) and node.is_item():
            return node.uuid
        if role == int(VISIBLE_ROLE):
            return node.visible
        if role == int(LOCKED_ROLE):
            return node.locked
        return None

    def setData(
        self,
        index: QtCore.QModelIndex,
        value: object,
        role: int = int(QtCore.Qt.ItemDataRole.EditRole),
    ) -> bool:
        node = self._node_from_index(index)
        if not node:
            return False

        if role == int(QtCore.Qt.ItemDataRole.EditRole):
            new_name = str(value).strip() or None
            if node.is_group() and self._layer_state:
                old_name = node.name
                cmd = RenameNodeCommand(
                    self._layer_state, node.uuid, old_name, new_name, is_group=True
                )
                if self._undo_stack:
                    self._undo_stack.push(cmd)
                else:
                    cmd.execute()
                self.dataChanged.emit(index, index, [int(QtCore.Qt.ItemDataRole.DisplayRole)])
                return True
            elif node.is_item():
                item = self._get_live_item(node.uuid)
                if item:
                    if hasattr(item, "display_name"):
                        old_name = item.display_name
                    elif hasattr(item, "params") and hasattr(item.params, "name"):
                        old_name = item.params.name
                    else:
                        old_name = None
                    cmd = RenameNodeCommand(
                        self._layer_state or LayerTreeState(),
                        node.uuid,
                        old_name,
                        new_name,
                        is_group=False,
                        item=item,
                    )
                    if self._undo_stack:
                        self._undo_stack.push(cmd)
                    else:
                        cmd.execute()
                    self.dataChanged.emit(
                        index, index, [int(QtCore.Qt.ItemDataRole.DisplayRole)]
                    )
                    return True

        if role == int(VISIBLE_ROLE) and self._scene and self._layer_state:
            old_visible = node.visible
            new_visible = bool(value)
            if old_visible != new_visible:
                vis_cmd = ToggleVisibilityCommand(
                    node, old_visible, new_visible, self._apply_effective_visibility
                )
                if self._undo_stack:
                    self._undo_stack.push(vis_cmd)
                else:
                    vis_cmd.execute()
            self.dataChanged.emit(index, index, [int(VISIBLE_ROLE)])
            self.visibilityChanged.emit()
            return True

        if role == int(LOCKED_ROLE) and self._scene and self._layer_state:
            old_locked = node.locked
            new_locked = bool(value)
            if old_locked != new_locked:
                lock_cmd = ToggleLockCommand(
                    node, old_locked, new_locked, self._apply_effective_locked
                )
                if self._undo_stack:
                    self._undo_stack.push(lock_cmd)
                else:
                    lock_cmd.execute()
            self.dataChanged.emit(index, index, [int(LOCKED_ROLE)])
            return True

        return False

    def toggle_locked_for_indexes(
        self, indexes: list[QtCore.QModelIndex], new_locked: bool
    ) -> None:
        """Toggle lock on multiple layer nodes as a single undoable batch."""
        if not self._scene or not self._layer_state:
            return
        cmds: list[Command] = []
        affected: list[QtCore.QModelIndex] = []
        for idx in indexes:
            node = self._node_from_index(idx)
            if not node or node.locked == new_locked:
                continue
            cmds.append(
                ToggleLockCommand(node, node.locked, new_locked, self._apply_effective_locked)
            )
            affected.append(idx)
        if not cmds:
            return
        batch = BatchCommand(cmds) if len(cmds) > 1 else cmds[0]
        if self._undo_stack:
            self._undo_stack.push(batch)
        else:
            batch.execute()
        for idx in affected:
            self.dataChanged.emit(idx, idx, [int(LOCKED_ROLE)])

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        if not index.isValid():
            return QtCore.Qt.ItemFlag.ItemIsDropEnabled
        node = self._node_from_index(index)
        if not node:
            return QtCore.Qt.ItemFlag.NoItemFlags
        # Autolabel children: selectable only (not draggable, not editable)
        if node.is_item() and node.parent and node.parent.is_item():
            return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        flags = (
            QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
            | QtCore.Qt.ItemFlag.ItemIsDragEnabled
        )
        if node.is_group():
            flags |= QtCore.Qt.ItemFlag.ItemIsDropEnabled | QtCore.Qt.ItemFlag.ItemIsEditable
        else:
            flags |= QtCore.Qt.ItemFlag.ItemIsEditable
        return flags

    def supportedDropActions(self) -> QtCore.Qt.DropAction:
        return QtCore.Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        return [MIME_TYPE_LAYER_ITEMS]

    def mimeData(self, indexes: list[QtCore.QModelIndex]) -> QtCore.QMimeData:  # type: ignore[override]
        mime = QtCore.QMimeData()
        uuids = self._uuids_from_indexes(indexes)
        mime.setData(MIME_TYPE_LAYER_ITEMS, ",".join(uuids).encode("utf-8"))
        return mime

    def dropMimeData(  # type: ignore[override]
        self,
        data: QtCore.QMimeData,
        action: QtCore.Qt.DropAction,
        row: int,
        column: int,
        parent: QtCore.QModelIndex,
    ) -> bool:
        if action != QtCore.Qt.DropAction.MoveAction or not self._scene or not self._layer_state:
            return False
        if not data.hasFormat(MIME_TYPE_LAYER_ITEMS):
            return False

        raw = data.data(MIME_TYPE_LAYER_ITEMS).data().decode("utf-8").strip()
        moved_uuids = [u for u in raw.split(",") if u]
        if not moved_uuids:
            return False

        target_node = self._node_from_index(parent) if parent.isValid() else None
        if target_node and target_node.is_item():
            return False

        # Block drops into a linked group
        if target_node and target_node.is_linked():
            return False

        # Block dragging items out of a linked group
        for uid in moved_uuids:
            node = self._layer_state.get_node(uid)
            if node and node.parent and node.parent.is_linked():
                return False

        dest_list = target_node.children if target_node else self._layer_state.get_root_nodes()
        insert_row = row if row >= 0 else len(dest_list)
        insert_row = max(0, min(insert_row, len(dest_list)))

        moved_uuids = self._sort_by_order(moved_uuids)
        target_uuid = target_node.uuid if target_node and target_node.is_group() else None

        # Adjust for removals above insertion point
        adjusted = insert_row
        for uuid in moved_uuids:
            pos = self._layer_state.get_parent_and_index(uuid)
            if pos and pos[0] == target_uuid and pos[1] < insert_row:
                adjusted -= 1
        adjusted = max(0, adjusted)

        cmds: list[Command] = [
            MoveNodeCommand(self._layer_state, uuid, target_uuid, adjusted + i)
            for i, uuid in enumerate(moved_uuids)
        ]
        batch = BatchCommand(cmds)
        if self._undo_stack:
            self._undo_stack.push(batch)
        else:
            batch.execute()

        self.refresh()
        self.orderChanged.emit()
        return True

    # --- Helpers ---

    def _node_from_index(self, index: QtCore.QModelIndex) -> LayerNode | None:
        if not index.isValid() or not self._layer_state:
            return None
        ptr = index.internalPointer()
        if isinstance(ptr, tuple) and len(ptr) == 2:
            uuid, gen = ptr
            if isinstance(uuid, str) and gen == self._layer_state.generation:
                return self._layer_state.get_node(uuid)
        return None

    def _rebuild_caches(self) -> None:
        self._uuid_to_item.clear()
        if not self._scene:
            return
        for item in self._scene.items():
            if self._is_alive(item) and hasattr(item, "item_uuid") and hasattr(item, "type_name"):
                self._uuid_to_item[item.item_uuid] = item

    def _prune_orphan_items(self) -> None:
        """Remove item nodes from LayerTreeState that have no matching scene item."""
        if not self._layer_state or not self._scene:
            return
        all_item_uuids = self._layer_state.get_all_items_in_order()
        orphans = [uid for uid in all_item_uuids if uid not in self._uuid_to_item]
        for uid in orphans:
            self._layer_state.remove_item(uid, emit=False)

    def _get_item_name(self, uuid: str) -> str:
        from ...objects.naming import item_label

        item = self._get_live_item(uuid)
        if not item:
            return "Item"
        return item_label(item)

    def _uuids_from_indexes(self, indexes: list[QtCore.QModelIndex]) -> list[str]:
        uuids: list[str] = []
        seen: set[str] = set()
        for idx in indexes:
            if idx.column() != 0:
                continue
            node = self._node_from_index(idx)
            if node and node.is_item() and node.uuid not in seen:
                seen.add(node.uuid)
                uuids.append(node.uuid)
        return self._sort_by_order(uuids)

    def _sort_by_order(self, uuids: list[str]) -> list[str]:
        current = self._layer_state.get_all_items_in_order() if self._layer_state else []
        rank = {u: i for i, u in enumerate(current)}
        return sorted(uuids, key=lambda u: rank.get(u, 10**9))

    def _apply_all_effective_states(self) -> None:
        """Apply effective visibility and lock to all items based on LayerNode hierarchy."""
        if not self._layer_state:
            return
        for root in self._layer_state.get_root_nodes():
            self._apply_effective_visibility(root)
            self._apply_effective_locked(root)

    def _apply_effective_visibility(self, node: LayerNode) -> None:
        """Apply effective visibility to node and all descendants."""
        layer_state = self._layer_state
        if not layer_state:
            return

        def apply_to_node(n: LayerNode) -> None:
            if n.is_item():
                if item := self._get_live_item(n.uuid):
                    effective = layer_state.is_effectively_visible(n.uuid)
                    item.setVisible(effective)
            for child in n.children:
                apply_to_node(child)

        apply_to_node(node)

    def _apply_effective_locked(self, node: LayerNode) -> None:
        """Apply effective locked state to node and all descendants.

        Linked groups that are not in editing mode are skipped entirely --
        their children's interaction state is managed by LinkedAssemblyService,
        not the user-facing lock mechanism.
        """
        layer_state = self._layer_state
        if not layer_state:
            return

        def apply_to_node(n: LayerNode) -> None:
            if n.is_item():
                if item := self._get_live_item(n.uuid):
                    if hasattr(item, "set_locked"):
                        effective = layer_state.is_effectively_locked(n.uuid)
                        item.set_locked(effective)
                for child in n.children:
                    apply_to_node(child)
            else:
                if n.is_linked() and n.link_metadata and not n.link_metadata.editing:
                    return
                for child in n.children:
                    apply_to_node(child)

        apply_to_node(node)
