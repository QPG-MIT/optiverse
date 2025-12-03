"""Layer panel widget for managing scene items by z-order."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.layer_group import GroupManager, LayerGroup
from ...core.zorder_utils import apply_z_order_change
from .constants import (
    LAYER_ITEM_MARGIN,
    LAYER_ITEM_SPACING,
    TOGGLE_BUTTON_SIZE,
    Z_ORDER_INITIAL_VALUE,
    Z_ORDER_STEP,
    Icons,
)

if TYPE_CHECKING:
    pass

# Shared data role constants
ITEM_UUID_ROLE = QtCore.Qt.ItemDataRole.UserRole
GROUP_UUID_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
IS_GROUP_ROLE = QtCore.Qt.ItemDataRole.UserRole + 2


class ClickableLabel(QtWidgets.QLabel):
    """A QLabel that emits clicked signal on left mouse press."""

    clicked = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._checked = False
        alignment = (
            QtCore.Qt.AlignmentFlag.AlignHCenter
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.setAlignment(alignment)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        self._checked = checked

    def mousePressEvent(self, event: QtGui.QMouseEvent | None) -> None:
        if event and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class LayerItemWidget(QtWidgets.QWidget):
    """Widget for a layer item row with visibility/lock toggles."""

    visibilityChanged = QtCore.pyqtSignal(bool)
    lockChanged = QtCore.pyqtSignal(bool)

    def __init__(self, name: str, is_visible: bool = True, is_locked: bool = False,
                 is_group: bool = False, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(
            LAYER_ITEM_MARGIN,
            LAYER_ITEM_MARGIN,
            LAYER_ITEM_MARGIN,
            LAYER_ITEM_MARGIN,
        )
        layout.setSpacing(LAYER_ITEM_SPACING)

        # Visibility toggle
        self._vis_btn = self._create_toggle(is_visible, "Toggle visibility", self._on_vis_clicked)
        self._update_vis_icon()
        layout.addWidget(self._vis_btn)

        # Lock toggle
        self._lock_btn = self._create_toggle(is_locked, "Toggle lock", self._on_lock_clicked)
        self._update_lock_icon()
        layout.addWidget(self._lock_btn)

        if is_group:
            layout.addWidget(QtWidgets.QLabel(Icons.FOLDER))

        name_label = QtWidgets.QLabel(name)
        name_label.setContentsMargins(4, 0, 0, 0)
        layout.addWidget(name_label, 1)

    def _create_toggle(
        self, checked: bool, tooltip: str, callback: Callable[[], None]
    ) -> ClickableLabel:
        btn = ClickableLabel()
        btn.setChecked(checked)
        btn.setToolTip(tooltip)
        btn.setFixedSize(TOGGLE_BUTTON_SIZE, TOGGLE_BUTTON_SIZE)
        btn.clicked.connect(callback)
        return btn

    def _update_vis_icon(self) -> None:
        self._vis_btn.setText(Icons.VISIBLE if self._vis_btn.isChecked() else Icons.HIDDEN)

    def _update_lock_icon(self) -> None:
        self._lock_btn.setText(Icons.LOCKED if self._lock_btn.isChecked() else Icons.UNLOCKED)

    def _on_vis_clicked(self) -> None:
        new_state = not self._vis_btn.isChecked()
        self._vis_btn.setChecked(new_state)
        self._update_vis_icon()
        self.visibilityChanged.emit(new_state)

    def _on_lock_clicked(self) -> None:
        new_state = not self._lock_btn.isChecked()
        self._lock_btn.setChecked(new_state)
        self._update_lock_icon()
        self.lockChanged.emit(new_state)


class LayerTreeWidget(QtWidgets.QTreeWidget):
    """Tree widget with drag-drop and delete key handling."""

    itemsReordered = QtCore.pyqtSignal()
    itemDroppedInGroup = QtCore.pyqtSignal(str, str)
    itemRemovedFromGroup = QtCore.pyqtSignal(str)
    deleteKeyPressed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setIndentation(16)
        self.setRootIsDecorated(True)
        self.setAnimated(True)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)

    def keyPressEvent(self, event: QtGui.QKeyEvent | None) -> None:
        if event and event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            if self.state() != QtWidgets.QAbstractItemView.State.EditingState:
                self.deleteKeyPressed.emit()
                event.accept()
                return
        super().keyPressEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent | None) -> None:
        if not event:
            return

        target_item = self.itemAt(event.position().toPoint())
        drop_indicator = self.dropIndicatorPosition()

        moved_uuids = [item.data(0, ITEM_UUID_ROLE) for item in self.selectedItems()
                       if not item.data(0, IS_GROUP_ROLE) and item.data(0, ITEM_UUID_ROLE)]

        super().dropEvent(event)

        if target_item and target_item.data(0, IS_GROUP_ROLE):
            if drop_indicator == QtWidgets.QAbstractItemView.DropIndicatorPosition.OnItem:
                group_uuid = target_item.data(0, GROUP_UUID_ROLE)
                for uuid in moved_uuids:
                    self.itemDroppedInGroup.emit(uuid, group_uuid)
            else:
                for uuid in moved_uuids:
                    self.itemRemovedFromGroup.emit(uuid)
        else:
            for uuid in moved_uuids:
                if any(
                    (top_item := self.topLevelItem(i))
                    and top_item.data(0, ITEM_UUID_ROLE) == uuid
                    for i in range(self.topLevelItemCount())
                ):
                    self.itemRemovedFromGroup.emit(uuid)

        self.itemsReordered.emit()


class LayerPanel(QtWidgets.QWidget):
    """Main layer panel widget."""

    selectionChanged = QtCore.pyqtSignal(list)

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._scene: QtWidgets.QGraphicsScene | None = None
        self._group_manager: GroupManager | None = None
        self._uuid_cache: dict[str, QtWidgets.QGraphicsItem] = {}
        self._z_counter = Z_ORDER_INITIAL_VALUE
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(header)
        h_layout.setContentsMargins(8, 8, 8, 4)

        title = QtWidgets.QLabel("Layers")
        title.setObjectName("layerPanelTitle")
        h_layout.addWidget(title)
        h_layout.addStretch()

        for icon, tooltip, callback in [
            (Icons.FOLDER_ADD, "Group selected items", self._group_selected),
            (Icons.FOLDER_REMOVE, "Ungroup selected group", self._ungroup_selected),
        ]:
            btn = QtWidgets.QToolButton()
            btn.setText(icon)
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            h_layout.addWidget(btn)

        layout.addWidget(header)

        # Tree
        self._tree = LayerTreeWidget()
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._tree.itemsReordered.connect(self._on_reordered)
        def add_to_group(uuid: str, group_uuid: str) -> None:
            if self._group_manager:
                self._group_manager.add_item_to_group(uuid, group_uuid)

        def remove_from_group(uuid: str) -> None:
            if self._group_manager:
                self._group_manager.remove_item_from_group(uuid)

        self._tree.itemDroppedInGroup.connect(add_to_group)
        self._tree.itemRemovedFromGroup.connect(remove_from_group)
        self._tree.deleteKeyPressed.connect(self._delete_selected)
        self._tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemDoubleClicked.connect(lambda item, col: self._tree.editItem(item, col))
        self._tree.itemExpanded.connect(lambda item: self._set_group_collapsed(item, False))
        self._tree.itemCollapsed.connect(lambda item: self._set_group_collapsed(item, True))
        layout.addWidget(self._tree, 1)

        # Z-order buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setContentsMargins(8, 4, 8, 8)
        buttons = [
            ("↑ Up", "Bring forward", "bring_forward"),
            ("↓ Down", "Send backward", "send_backward"),
        ]
        for text, tooltip, op in buttons:
            push_btn = QtWidgets.QPushButton(text)
            push_btn.setToolTip(tooltip)
            push_btn.clicked.connect(lambda _, o=op: self._apply_z_order(o))
            btn_layout.addWidget(push_btn)
        layout.addLayout(btn_layout)

    def _set_group_collapsed(self, item: QtWidgets.QTreeWidgetItem, collapsed: bool) -> None:
        if self._group_manager and (uuid := item.data(0, GROUP_UUID_ROLE)):
            self._group_manager.set_group_collapsed(uuid, collapsed)

    def set_scene(self, scene: QtWidgets.QGraphicsScene) -> None:
        self._scene = scene

    def set_group_manager(self, group_manager: GroupManager) -> None:
        self._group_manager = group_manager
        group_manager.groupsChanged.connect(self.refresh)

    def refresh(self) -> None:
        if not self._scene:
            return
        self._tree.blockSignals(True)
        try:
            self._rebuild_tree()
        finally:
            self._tree.blockSignals(False)

    def _rebuild_tree(self) -> None:
        self._tree.clear()
        self._uuid_cache.clear()

        if not self._scene:
            return

        # Build cache and get sorted items
        items_with_z = []
        for item in self._scene.items():
            if hasattr(item, "item_uuid") and hasattr(item, "type_name"):
                items_with_z.append((item.zValue(), item))
                self._uuid_cache[item.item_uuid] = item
        items_with_z.sort(key=lambda x: x[0], reverse=True)

        # Get grouped UUIDs
        grouped = set()
        if self._group_manager:
            for g in self._group_manager.get_all_groups():
                grouped.update(g.item_uuids)

        group_items: dict[str, QtWidgets.QTreeWidgetItem] = {}

        # Add groups
        if self._group_manager:
            for group in self._group_manager.get_root_groups():
                self._tree.addTopLevelItem(self._build_group_item(group, items_with_z, group_items))

        # Add ungrouped items
        ungrouped: list[QtWidgets.QTreeWidgetItem] = []
        for _z, item in items_with_z:
            if hasattr(item, "item_uuid") and item.item_uuid not in grouped:
                tree_item = self._create_item(item)
                self._tree.addTopLevelItem(tree_item)
                ungrouped.append(tree_item)

        # Setup widgets
        for uuid, tree_item in group_items.items():
            if self._group_manager:
                layer_group: LayerGroup | None = self._group_manager.get_group(uuid)
                if layer_group is not None:
                    widget = LayerItemWidget(layer_group.name, is_group=True)
                    def set_group_visible(visible: bool, group_uuid: str = uuid) -> None:
                        self._apply_to_group(group_uuid, lambda item: item.setVisible(visible))

                    def set_group_locked(locked: bool, group_uuid: str = uuid) -> None:
                        self._apply_to_group(
                            group_uuid,
                            lambda item: hasattr(item, "set_locked")
                            and item.set_locked(locked),
                        )

                    widget.visibilityChanged.connect(set_group_visible)
                    widget.lockChanged.connect(set_group_locked)
                    self._tree.setItemWidget(tree_item, 0, widget)
                    tree_item.setExpanded(not layer_group.collapsed)

            for i in range(tree_item.childCount()):
                if (child := tree_item.child(i)) and not child.data(0, IS_GROUP_ROLE):
                    self._setup_item_widget(child)

        for tree_item in ungrouped:
            self._setup_item_widget(tree_item)

    def _build_group_item(
        self,
        group: LayerGroup,
        items_with_z: list,
        group_items: dict,
    ) -> QtWidgets.QTreeWidgetItem:
        tree_item = QtWidgets.QTreeWidgetItem()
        # Don't setText - we use setItemWidget which renders its own text
        tree_item.setData(0, GROUP_UUID_ROLE, group.group_uuid)
        tree_item.setData(0, IS_GROUP_ROLE, True)
        flags = (
            tree_item.flags()
            | QtCore.Qt.ItemFlag.ItemIsSelectable
            | QtCore.Qt.ItemFlag.ItemIsEditable
        )
        tree_item.setFlags(flags)
        group_items[group.group_uuid] = tree_item

        if self._group_manager:
            for child in self._group_manager.get_child_groups(group.group_uuid):
                tree_item.addChild(self._build_group_item(child, items_with_z, group_items))

        filtered_items = [
            (z, i)
            for z, i in items_with_z
            if hasattr(i, "item_uuid") and i.item_uuid in group.item_uuids
        ]
        for _z, item in sorted(filtered_items, key=lambda x: x[0], reverse=True):
            tree_item.addChild(self._create_item(item))

        return tree_item

    def _create_item(self, item: QtWidgets.QGraphicsItem) -> QtWidgets.QTreeWidgetItem:
        tree_item = QtWidgets.QTreeWidgetItem()
        # Don't setText - we use setItemWidget which renders its own text
        if hasattr(item, "item_uuid"):
            tree_item.setData(0, ITEM_UUID_ROLE, item.item_uuid)
        tree_item.setData(0, IS_GROUP_ROLE, False)
        flags = (
            tree_item.flags()
            | QtCore.Qt.ItemFlag.ItemIsSelectable
            | QtCore.Qt.ItemFlag.ItemIsEditable
        )
        tree_item.setFlags(flags)
        return tree_item

    def _setup_item_widget(self, tree_item: QtWidgets.QTreeWidgetItem) -> None:
        uuid = tree_item.data(0, ITEM_UUID_ROLE)
        if not uuid:
            return
        item = self._uuid_cache.get(uuid)
        if not item:
            return
        widget = LayerItemWidget(
            self._get_name(item),
            item.isVisible(),
            getattr(item, "_locked", False),
        )
        widget.visibilityChanged.connect(lambda v: item.setVisible(v))

        def set_locked(locked: bool) -> None:
            if hasattr(item, "set_locked"):
                item.set_locked(locked)

        widget.lockChanged.connect(set_locked)
        self._tree.setItemWidget(tree_item, 0, widget)

    def _get_name(self, item: QtWidgets.QGraphicsItem) -> str:
        if hasattr(item, "params") and hasattr(item.params, "name") and item.params.name:
            name: str = item.params.name
            return name
        return item.type_name.replace("_", " ").title() if hasattr(item, "type_name") else "Item"

    # --- Group Operations ---

    def _apply_to_group(self, group_uuid: str, action: Callable) -> None:
        """Apply action recursively to all items in a group."""
        if not self._group_manager:
            return
        for item in self._group_manager.get_group_items(group_uuid):
            action(item)
        for child in self._group_manager.get_child_groups(group_uuid):
            self._apply_to_group(child.group_uuid, action)

    def _collect_group_uuids(self, group_uuid: str) -> list[str]:
        """Collect all item UUIDs from a group recursively."""
        if not self._group_manager or not (group := self._group_manager.get_group(group_uuid)):
            return []
        result = list(group.item_uuids)
        for child in self._group_manager.get_child_groups(group_uuid):
            result.extend(self._collect_group_uuids(child.group_uuid))
        return result

    # --- Z-Order ---

    def _apply_z_order(self, operation: str) -> None:
        if not self._scene or not (items := list(self._scene.selectedItems())):
            return
        undo_stack = None
        if views := self._scene.views():
            window = views[0].window()
            if window is not None and hasattr(window, "undo_stack"):
                undo_stack = window.undo_stack
        apply_z_order_change(items, operation, self._scene, undo_stack)

    def _update_z_from_tree(self) -> None:
        self._z_counter = Z_ORDER_INITIAL_VALUE
        for i in range(self._tree.topLevelItemCount()):
            if item := self._tree.topLevelItem(i):
                self._update_z_recursive(item)

    def _update_z_recursive(self, tree_item: QtWidgets.QTreeWidgetItem) -> None:
        if tree_item.data(0, IS_GROUP_ROLE):
            for i in range(tree_item.childCount()):
                if child := tree_item.child(i):
                    self._update_z_recursive(child)
        elif (uuid := tree_item.data(0, ITEM_UUID_ROLE)) and (item := self._uuid_cache.get(uuid)):
            item.setZValue(self._z_counter)
            self._z_counter -= Z_ORDER_STEP

    # --- Selection Sync ---

    def _on_selection_changed(self) -> None:
        if not self._scene:
            return
        selected = []
        for item in self._tree.selectedItems():
            if item.data(0, IS_GROUP_ROLE):
                selected.extend(self._collect_group_uuids(item.data(0, GROUP_UUID_ROLE)))
            elif uuid := item.data(0, ITEM_UUID_ROLE):
                selected.append(uuid)

        self._scene.clearSelection()
        for graphics_item in self._scene.items():
            if hasattr(graphics_item, "item_uuid") and graphics_item.item_uuid in selected:
                graphics_item.setSelected(True)
        self.selectionChanged.emit(selected)

    def sync_from_scene_selection(self) -> None:
        if not self._scene:
            return
        self._tree.blockSignals(True)
        try:
            uuids = {
                item.item_uuid
                for item in self._scene.selectedItems()
                if hasattr(item, "item_uuid")
            }
            self._tree.clearSelection()
            self._select_in_tree(uuids)
        finally:
            self._tree.blockSignals(False)

    def _select_in_tree(
        self, uuids: set[str], parent: QtWidgets.QTreeWidgetItem | None = None
    ) -> None:
        count = parent.childCount() if parent else self._tree.topLevelItemCount()
        for i in range(count):
            item = parent.child(i) if parent else self._tree.topLevelItem(i)
            if not item:
                continue
            if not item.data(0, IS_GROUP_ROLE) and item.data(0, ITEM_UUID_ROLE) in uuids:
                item.setSelected(True)
            self._select_in_tree(uuids, item)

    def _on_reordered(self) -> None:
        if self._scene:
            self._update_z_from_tree()
            self.refresh()

    # --- Actions ---

    def _group_selected(self) -> None:
        if not self._scene or not self._group_manager:
            return
        if len(self._scene.selectedItems()) < 2:
            QtWidgets.QMessageBox.information(
                self, "Group Items", "Please select at least 2 items to group."
            )
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "Create Group", "Group name:", text="Group")
        if ok:
            self._group_manager.group_selected_items(name or "Group")

    def _ungroup_selected(self) -> None:
        if not self._group_manager:
            return
        for item in self._tree.selectedItems():
            if item.data(0, IS_GROUP_ROLE):
                self._group_manager.ungroup(item.data(0, GROUP_UUID_ROLE))
                return
        QtWidgets.QMessageBox.information(self, "Ungroup", "Please select a group to ungroup.")

    def _delete_selected(self) -> None:
        if not self._scene:
            return
        selected = self._tree.selectedItems()
        if not selected:
            return

        for item in selected:
            if item.data(0, IS_GROUP_ROLE):
                if self._group_manager:
                    self._group_manager.delete_group(item.data(0, GROUP_UUID_ROLE))
            else:
                uuid = item.data(0, ITEM_UUID_ROLE)
                if uuid:
                    scene_item = self._uuid_cache.get(uuid)
                    if scene_item:
                        # Remove from group first (this triggers empty group cleanup)
                        if self._group_manager:
                            self._group_manager.remove_item_from_group(uuid)
                        self._scene.removeItem(scene_item)
        self.refresh()

    def _toggle_property(
        self,
        item: QtWidgets.QTreeWidgetItem,
        get_val: Callable,
        set_val: Callable,
    ) -> None:
        """Toggle a property (visibility/lock) for item or group."""
        if item.data(0, IS_GROUP_ROLE):
            uuid = item.data(0, GROUP_UUID_ROLE)
            items = self._group_manager.get_group_items(uuid) if self._group_manager else []
            current = get_val(items[0]) if items else True
            self._apply_to_group(uuid, lambda i: set_val(i, not current))
        else:
            uuid = item.data(0, ITEM_UUID_ROLE)
            if uuid:
                scene_item = self._uuid_cache.get(uuid)
                if scene_item:
                    set_val(scene_item, not get_val(scene_item))
        self.refresh()

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        item = self._tree.itemAt(pos)
        menu = QtWidgets.QMenu(self)

        if item:
            def toggle_visibility() -> None:
                self._toggle_property(
                    item,
                    lambda i: i.isVisible(),
                    lambda i, v: i.setVisible(v),
                )

            def toggle_lock() -> None:
                self._toggle_property(
                    item,
                    lambda i: getattr(i, "_locked", False),
                    lambda i, v: hasattr(i, "set_locked") and i.set_locked(v),
                )

            visibility_action = menu.addAction("Toggle Visibility")
            if visibility_action is not None:
                visibility_action.triggered.connect(toggle_visibility)
            lock_action = menu.addAction("Toggle Lock")
            if lock_action is not None:
                lock_action.triggered.connect(toggle_lock)
            menu.addSeparator()

            if item.data(0, IS_GROUP_ROLE):
                ungroup_action = menu.addAction("Ungroup")
                if ungroup_action is not None:
                    ungroup_action.triggered.connect(self._ungroup_selected)
            else:
                group_action = menu.addAction("Group with Selected")
                if group_action is not None:
                    group_action.triggered.connect(self._group_selected)
            menu.addSeparator()
            delete_action = menu.addAction("Delete")
            if delete_action is not None:
                delete_action.triggered.connect(self._delete_selected)

        menu.addSeparator()
        z_menu = menu.addMenu("Z-Order")
        if z_menu is not None:
            for label, op in [
                ("Bring to Front", "bring_to_front"),
                ("Bring Forward", "bring_forward"),
                ("Send Backward", "send_backward"),
                ("Send to Back", "send_to_back"),
            ]:
                z_action = z_menu.addAction(label)
                if z_action is not None:
                    z_action.triggered.connect(lambda _, o=op: self._apply_z_order(o))

        viewport = self._tree.viewport()
        if viewport is not None:
            menu.exec(viewport.mapToGlobal(pos))
