"""
Layer panel widget for managing scene items by z-order.

Provides a Photoshop-style layer panel with:
- Items sorted by z-value (highest at top)
- Visibility and lock toggles
- Drag-to-reorder z-position
- Grouping support
- Context menu for operations
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.layer_group import GroupManager, LayerGroup
from ...core.zorder_utils import apply_z_order_change

if TYPE_CHECKING:
    from ...objects.base_obj import BaseObj


class LayerTreeWidget(QtWidgets.QTreeWidget):
    """
    Tree widget for displaying scene layers.

    Supports:
    - Drag and drop to reorder z-position
    - Click to select items in scene
    - Context menu for layer operations
    """

    # Signals
    itemsReordered = QtCore.pyqtSignal()  # Emitted when z-order changes via drag
    deleteKeyPressed = QtCore.pyqtSignal()  # Emitted when Delete/Backspace pressed

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setRootIsDecorated(True)
        self.setAnimated(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

        # Enable drag and drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)

        # Styling
        self.setStyleSheet(
            """
            QTreeWidget::item {
                padding: 4px 2px;
            }
            QTreeWidget::item:selected {
                background-color: #3d5a80;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #4a6fa5;
            }
        """
        )

    def keyPressEvent(self, event: QtGui.QKeyEvent | None) -> None:
        """Handle key presses."""
        if event is None:
            return
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            self.deleteKeyPressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent | None) -> None:
        """Handle drop to reorder items."""
        if event is None:
            return
        super().dropEvent(event)
        self.itemsReordered.emit()


class LayerItemWidget(QtWidgets.QWidget):
    """
    Custom widget for a layer item row.

    Shows:
    - Visibility toggle (eye icon)
    - Lock toggle (lock icon)
    - Item name
    """

    visibilityChanged = QtCore.pyqtSignal(bool)
    lockChanged = QtCore.pyqtSignal(bool)

    def __init__(
        self,
        name: str,
        is_visible: bool = True,
        is_locked: bool = False,
        is_group: bool = False,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)

        self._is_group = is_group

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Visibility toggle
        self._visibility_btn = QtWidgets.QToolButton()
        self._visibility_btn.setCheckable(True)
        self._visibility_btn.setChecked(is_visible)
        self._visibility_btn.setToolTip("Toggle visibility")
        self._visibility_btn.setFixedSize(20, 20)
        self._update_visibility_icon()
        self._visibility_btn.toggled.connect(self._on_visibility_toggled)
        layout.addWidget(self._visibility_btn)

        # Lock toggle
        self._lock_btn = QtWidgets.QToolButton()
        self._lock_btn.setCheckable(True)
        self._lock_btn.setChecked(is_locked)
        self._lock_btn.setToolTip("Toggle lock")
        self._lock_btn.setFixedSize(20, 20)
        self._update_lock_icon()
        self._lock_btn.toggled.connect(self._on_lock_toggled)
        layout.addWidget(self._lock_btn)

        # Type indicator
        type_label = QtWidgets.QLabel("📁" if is_group else "◆")
        type_label.setFixedWidth(16)
        layout.addWidget(type_label)

        # Name label
        self._name_label = QtWidgets.QLabel(name)
        self._name_label.setMinimumWidth(80)
        layout.addWidget(self._name_label, 1)

    def _update_visibility_icon(self) -> None:
        """Update visibility button icon."""
        if self._visibility_btn.isChecked():
            self._visibility_btn.setText("👁")
        else:
            self._visibility_btn.setText("○")

    def _update_lock_icon(self) -> None:
        """Update lock button icon."""
        if self._lock_btn.isChecked():
            self._lock_btn.setText("🔒")
        else:
            self._lock_btn.setText("🔓")

    def _on_visibility_toggled(self, checked: bool) -> None:
        """Handle visibility toggle."""
        self._update_visibility_icon()
        self.visibilityChanged.emit(checked)

    def _on_lock_toggled(self, checked: bool) -> None:
        """Handle lock toggle."""
        self._update_lock_icon()
        self.lockChanged.emit(checked)

    def set_name(self, name: str) -> None:
        """Update the displayed name."""
        self._name_label.setText(name)

    def set_visible(self, visible: bool) -> None:
        """Set visibility state."""
        self._visibility_btn.blockSignals(True)
        self._visibility_btn.setChecked(visible)
        self._update_visibility_icon()
        self._visibility_btn.blockSignals(False)

    def set_locked(self, locked: bool) -> None:
        """Set lock state."""
        self._lock_btn.blockSignals(True)
        self._lock_btn.setChecked(locked)
        self._update_lock_icon()
        self._lock_btn.blockSignals(False)


class LayerPanel(QtWidgets.QWidget):
    """
    Main layer panel widget.

    Displays scene items organized by z-order with grouping support.
    """

    # Signals
    selectionChanged = QtCore.pyqtSignal(list)  # List of selected item UUIDs

    # Data role constants
    ITEM_UUID_ROLE = QtCore.Qt.ItemDataRole.UserRole
    GROUP_UUID_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
    IS_GROUP_ROLE = QtCore.Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self._scene: QtWidgets.QGraphicsScene | None = None
        self._group_manager: GroupManager | None = None
        self._updating = False  # Prevent recursive updates

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the UI layout."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header with title and buttons
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(8, 8, 8, 4)

        title = QtWidgets.QLabel("Layers")
        title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Group button
        self._group_btn = QtWidgets.QToolButton()
        self._group_btn.setText("📁+")
        self._group_btn.setToolTip("Group selected items")
        self._group_btn.clicked.connect(self._group_selected)
        header_layout.addWidget(self._group_btn)

        # Ungroup button
        self._ungroup_btn = QtWidgets.QToolButton()
        self._ungroup_btn.setText("📁-")
        self._ungroup_btn.setToolTip("Ungroup selected group")
        self._ungroup_btn.clicked.connect(self._ungroup_selected)
        header_layout.addWidget(self._ungroup_btn)

        layout.addWidget(header)

        # Tree widget
        self._tree = LayerTreeWidget()
        self._tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self._tree.itemsReordered.connect(self._on_items_reordered)
        self._tree.deleteKeyPressed.connect(self._delete_selected)
        self._tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._tree.itemExpanded.connect(self._on_group_expanded)
        self._tree.itemCollapsed.connect(self._on_group_collapsed)
        layout.addWidget(self._tree, 1)

        # Z-order buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setContentsMargins(8, 4, 8, 8)

        self._up_btn = QtWidgets.QPushButton("↑ Up")
        self._up_btn.setToolTip("Bring forward (increase z-order)")
        self._up_btn.clicked.connect(self._bring_forward)
        btn_layout.addWidget(self._up_btn)

        self._down_btn = QtWidgets.QPushButton("↓ Down")
        self._down_btn.setToolTip("Send backward (decrease z-order)")
        self._down_btn.clicked.connect(self._send_backward)
        btn_layout.addWidget(self._down_btn)

        layout.addLayout(btn_layout)

    def set_scene(self, scene: QtWidgets.QGraphicsScene) -> None:
        """Set the scene to display layers for."""
        self._scene = scene

    def set_group_manager(self, group_manager: GroupManager) -> None:
        """Set the group manager."""
        self._group_manager = group_manager
        self._group_manager.groupsChanged.connect(self.refresh)

    def refresh(self) -> None:
        """Refresh the layer panel from scene state."""
        if self._updating or not self._scene:
            return

        self._updating = True
        try:
            self._rebuild_tree()
        finally:
            self._updating = False

    def _rebuild_tree(self) -> None:
        """Rebuild the tree from scene items."""
        self._tree.clear()

        if not self._scene:
            return

        # Get all scene items with z-values
        items_with_z: list[tuple[float, QtWidgets.QGraphicsItem]] = []
        for item in self._scene.items():
            # Filter to only BaseObj items (skip rays, guides, etc.)
            if hasattr(item, "item_uuid") and hasattr(item, "type_name"):
                items_with_z.append((item.zValue(), item))

        # Sort by z-value (highest first - top of layer panel)
        items_with_z.sort(key=lambda x: x[0], reverse=True)

        # Track which items are in groups
        grouped_uuids: set[str] = set()
        if self._group_manager:
            for group in self._group_manager.get_all_groups():
                grouped_uuids.update(group.item_uuids)

        # Collect all tree items for deferred widget setup
        all_tree_items: list[QtWidgets.QTreeWidgetItem] = []

        # Add groups first
        group_tree_items: dict[str, QtWidgets.QTreeWidgetItem] = {}
        if self._group_manager:
            for group in self._group_manager.get_all_groups():
                group_item = self._create_group_tree_item(group)
                self._tree.addTopLevelItem(group_item)
                group_tree_items[group.group_uuid] = group_item
                all_tree_items.append(group_item)

                # Add group members as children
                for z, item in items_with_z:
                    if hasattr(item, "item_uuid") and item.item_uuid in group.item_uuids:
                        child_item = self._create_item_tree_item(item)
                        group_item.addChild(child_item)
                        all_tree_items.append(child_item)

                # Set expanded state
                group_item.setExpanded(not group.collapsed)

        # Add ungrouped items
        for z, item in items_with_z:
            if hasattr(item, "item_uuid"):
                if item.item_uuid not in grouped_uuids:
                    tree_item = self._create_item_tree_item(item)
                    self._tree.addTopLevelItem(tree_item)
                    all_tree_items.append(tree_item)

        # Now set up widgets for all items (they're now in the tree)
        for tree_item in all_tree_items:
            is_group = tree_item.data(0, self.IS_GROUP_ROLE)
            if is_group:
                self._setup_group_widget(tree_item)
            else:
                self._setup_item_widget(tree_item)

    def _create_group_tree_item(self, group: LayerGroup) -> QtWidgets.QTreeWidgetItem:
        """Create a tree item for a group."""
        tree_item = QtWidgets.QTreeWidgetItem()
        tree_item.setData(0, self.GROUP_UUID_ROLE, group.group_uuid)
        tree_item.setData(0, self.IS_GROUP_ROLE, True)
        tree_item.setFlags(
            tree_item.flags()
            | QtCore.Qt.ItemFlag.ItemIsEditable
            | QtCore.Qt.ItemFlag.ItemIsDropEnabled
        )

        return tree_item

    def _setup_group_widget(self, tree_item: QtWidgets.QTreeWidgetItem) -> None:
        """Set up the widget for a group tree item after it's added to the tree."""
        group_uuid = tree_item.data(0, self.GROUP_UUID_ROLE)
        if not group_uuid or not self._group_manager:
            return
        
        group = self._group_manager.get_group(group_uuid)
        if not group:
            return

        widget = LayerItemWidget(group.name, is_group=True)
        widget.visibilityChanged.connect(
            lambda visible, g=group_uuid: self._set_group_visibility(g, visible)
        )
        widget.lockChanged.connect(
            lambda locked, g=group_uuid: self._set_group_locked(g, locked)
        )
        self._tree.setItemWidget(tree_item, 0, widget)

    def _create_item_tree_item(
        self, item: QtWidgets.QGraphicsItem
    ) -> QtWidgets.QTreeWidgetItem:
        """Create a tree item for a scene item."""
        tree_item = QtWidgets.QTreeWidgetItem()

        item_uuid = getattr(item, "item_uuid", "")
        tree_item.setData(0, self.ITEM_UUID_ROLE, item_uuid)
        tree_item.setData(0, self.IS_GROUP_ROLE, False)
        tree_item.setFlags(
            tree_item.flags()
            | QtCore.Qt.ItemFlag.ItemIsEditable
            | QtCore.Qt.ItemFlag.ItemIsDragEnabled
        )

        return tree_item

    def _setup_item_widget(self, tree_item: QtWidgets.QTreeWidgetItem) -> None:
        """Set up the widget for an item tree item after it's added to the tree."""
        item_uuid = tree_item.data(0, self.ITEM_UUID_ROLE)
        if not item_uuid:
            return

        item = self._get_item_by_uuid(item_uuid)
        if not item:
            return

        # Get item properties
        name = self._get_item_name(item)
        is_visible = item.isVisible()
        is_locked = getattr(item, "_locked", False)

        # Create custom widget
        widget = LayerItemWidget(name, is_visible, is_locked, is_group=False)
        widget.visibilityChanged.connect(
            lambda visible, uuid=item_uuid: self._set_item_visibility(uuid, visible)
        )
        widget.lockChanged.connect(
            lambda locked, uuid=item_uuid: self._set_item_locked(uuid, locked)
        )
        self._tree.setItemWidget(tree_item, 0, widget)

    def _get_item_name(self, item: QtWidgets.QGraphicsItem) -> str:
        """Get display name for a scene item."""
        # Try to get name from params or type
        if hasattr(item, "params") and hasattr(item.params, "name") and item.params.name:
            return item.params.name
        if hasattr(item, "type_name"):
            return item.type_name.replace("_", " ").title()
        return "Item"

    def _get_item_by_uuid(self, item_uuid: str) -> QtWidgets.QGraphicsItem | None:
        """Find scene item by UUID."""
        if not self._scene:
            return None
        for item in self._scene.items():
            if hasattr(item, "item_uuid") and item.item_uuid == item_uuid:
                return item
        return None

    def _on_tree_selection_changed(self) -> None:
        """Handle tree selection change - sync to scene selection."""
        if self._updating or not self._scene:
            return

        self._updating = True
        try:
            # Get selected UUIDs
            selected_uuids = []
            for tree_item in self._tree.selectedItems():
                is_group = tree_item.data(0, self.IS_GROUP_ROLE)
                if is_group:
                    # Select all items in group
                    group_uuid = tree_item.data(0, self.GROUP_UUID_ROLE)
                    if self._group_manager:
                        group = self._group_manager.get_group(group_uuid)
                        if group:
                            selected_uuids.extend(group.item_uuids)
                else:
                    item_uuid = tree_item.data(0, self.ITEM_UUID_ROLE)
                    if item_uuid:
                        selected_uuids.append(item_uuid)

            # Update scene selection
            self._scene.clearSelection()
            for item in self._scene.items():
                if hasattr(item, "item_uuid") and item.item_uuid in selected_uuids:
                    item.setSelected(True)

            self.selectionChanged.emit(selected_uuids)
        finally:
            self._updating = False

    def sync_from_scene_selection(self) -> None:
        """Sync tree selection from scene selection."""
        if self._updating or not self._scene:
            return

        self._updating = True
        try:
            # Get selected item UUIDs from scene
            selected_uuids = set()
            for item in self._scene.selectedItems():
                if hasattr(item, "item_uuid"):
                    selected_uuids.add(item.item_uuid)

            # Update tree selection
            self._tree.clearSelection()
            self._select_tree_items_by_uuid(selected_uuids)
        finally:
            self._updating = False

    def _select_tree_items_by_uuid(self, uuids: set[str]) -> None:
        """Select tree items matching the given UUIDs."""
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item:
                self._select_tree_item_recursive(item, uuids)

    def _select_tree_item_recursive(
        self, tree_item: QtWidgets.QTreeWidgetItem, uuids: set[str]
    ) -> None:
        """Recursively select tree items matching UUIDs."""
        is_group = tree_item.data(0, self.IS_GROUP_ROLE)
        if not is_group:
            item_uuid = tree_item.data(0, self.ITEM_UUID_ROLE)
            if item_uuid in uuids:
                tree_item.setSelected(True)

        # Check children
        for i in range(tree_item.childCount()):
            child = tree_item.child(i)
            if child:
                self._select_tree_item_recursive(child, uuids)

    def _on_items_reordered(self) -> None:
        """Handle drag-drop reorder - update z-values."""
        if not self._scene:
            return

        # Rebuild z-order from tree order (top = highest z)
        z = 100.0  # Start high so we have room

        for i in range(self._tree.topLevelItemCount()):
            tree_item = self._tree.topLevelItem(i)
            if not tree_item:
                continue

            is_group = tree_item.data(0, self.IS_GROUP_ROLE)
            if is_group:
                # Update all items in group
                for j in range(tree_item.childCount()):
                    child = tree_item.child(j)
                    if child:
                        item_uuid = child.data(0, self.ITEM_UUID_ROLE)
                        item = self._get_item_by_uuid(item_uuid)
                        if item:
                            item.setZValue(z)
                            z -= 1.0
            else:
                item_uuid = tree_item.data(0, self.ITEM_UUID_ROLE)
                item = self._get_item_by_uuid(item_uuid)
                if item:
                    item.setZValue(z)
                    z -= 1.0

    def _on_item_double_clicked(
        self, item: QtWidgets.QTreeWidgetItem, column: int
    ) -> None:
        """Handle double-click to rename."""
        # Start editing
        self._tree.editItem(item, column)

    def _on_group_expanded(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Handle group expand."""
        if not self._group_manager:
            return
        group_uuid = item.data(0, self.GROUP_UUID_ROLE)
        if group_uuid:
            self._group_manager.set_group_collapsed(group_uuid, False)

    def _on_group_collapsed(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Handle group collapse."""
        if not self._group_manager:
            return
        group_uuid = item.data(0, self.GROUP_UUID_ROLE)
        if group_uuid:
            self._group_manager.set_group_collapsed(group_uuid, True)

    def _set_item_visibility(self, item_uuid: str, visible: bool) -> None:
        """Set visibility of a scene item."""
        item = self._get_item_by_uuid(item_uuid)
        if item:
            item.setVisible(visible)

    def _set_item_locked(self, item_uuid: str, locked: bool) -> None:
        """Set lock state of a scene item."""
        item = self._get_item_by_uuid(item_uuid)
        if item and hasattr(item, "set_locked"):
            item.set_locked(locked)

    def _set_group_visibility(self, group_uuid: str, visible: bool) -> None:
        """Set visibility of all items in a group."""
        if not self._group_manager:
            return
        items = self._group_manager.get_group_items(group_uuid)
        for item in items:
            item.setVisible(visible)

    def _set_group_locked(self, group_uuid: str, locked: bool) -> None:
        """Set lock state of all items in a group."""
        if not self._group_manager:
            return
        items = self._group_manager.get_group_items(group_uuid)
        for item in items:
            if hasattr(item, "set_locked"):
                item.set_locked(locked)

    def _group_selected(self) -> None:
        """Group currently selected items."""
        if not self._scene or not self._group_manager:
            return

        # Get selected items from scene
        selected = self._scene.selectedItems()
        if len(selected) < 2:
            QtWidgets.QMessageBox.information(
                self,
                "Group Items",
                "Please select at least 2 items to group.",
            )
            return

        # Prompt for group name
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Create Group", "Group name:", text="Group"
        )
        if not ok:
            return

        # Create group
        self._group_manager.group_selected_items(name or "Group")

    def _ungroup_selected(self) -> None:
        """Ungroup the selected group."""
        if not self._group_manager:
            return

        selected = self._tree.selectedItems()
        for tree_item in selected:
            is_group = tree_item.data(0, self.IS_GROUP_ROLE)
            if is_group:
                group_uuid = tree_item.data(0, self.GROUP_UUID_ROLE)
                self._group_manager.ungroup(group_uuid)
                return

        QtWidgets.QMessageBox.information(
            self, "Ungroup", "Please select a group to ungroup."
        )

    def _delete_selected(self) -> None:
        """Delete selected items or groups."""
        if not self._scene:
            return

        selected = self._tree.selectedItems()
        if not selected:
            return

        # Confirm deletion
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete",
            f"Delete {len(selected)} selected item(s)?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        for tree_item in selected:
            is_group = tree_item.data(0, self.IS_GROUP_ROLE)
            if is_group:
                group_uuid = tree_item.data(0, self.GROUP_UUID_ROLE)
                if self._group_manager:
                    self._group_manager.delete_group(group_uuid, keep_items=False)
            else:
                item_uuid = tree_item.data(0, self.ITEM_UUID_ROLE)
                item = self._get_item_by_uuid(item_uuid)
                if item:
                    self._scene.removeItem(item)

        self.refresh()

    def _bring_forward(self) -> None:
        """Bring selected items forward (higher z-order)."""
        self._apply_z_order("bring_forward")

    def _send_backward(self) -> None:
        """Send selected items backward (lower z-order)."""
        self._apply_z_order("send_backward")

    def _apply_z_order(self, operation: str) -> None:
        """Apply z-order operation to selected items."""
        if not self._scene:
            return

        items = list(self._scene.selectedItems())
        if not items:
            return

        # Get undo stack from main window if available
        undo_stack = None
        views = self._scene.views()
        if views:
            main_window = views[0].window()
            if hasattr(main_window, "undo_stack"):
                undo_stack = main_window.undo_stack

        apply_z_order_change(items, operation, self._scene, undo_stack)
        self.refresh()

    def _show_context_menu(self, position: QtCore.QPoint) -> None:
        """Show context menu for layer item."""
        item = self._tree.itemAt(position)
        if not item:
            return

        menu = QtWidgets.QMenu(self)

        is_group = item.data(0, self.IS_GROUP_ROLE)

        if is_group:
            # Group context menu
            act_rename = menu.addAction("Rename Group")
            act_ungroup = menu.addAction("Ungroup")
            menu.addSeparator()
            act_delete = menu.addAction("Delete Group")

            action = menu.exec(self._tree.viewport().mapToGlobal(position))

            if action == act_rename:
                self._tree.editItem(item, 0)
            elif action == act_ungroup:
                group_uuid = item.data(0, self.GROUP_UUID_ROLE)
                if self._group_manager:
                    self._group_manager.ungroup(group_uuid)
            elif action == act_delete:
                group_uuid = item.data(0, self.GROUP_UUID_ROLE)
                if self._group_manager:
                    self._group_manager.delete_group(group_uuid, keep_items=False)
                self.refresh()
        else:
            # Item context menu
            act_rename = menu.addAction("Rename")
            menu.addSeparator()

            # Z-order submenu
            z_menu = menu.addMenu("Arrange")
            act_front = z_menu.addAction("Bring to Front")
            act_forward = z_menu.addAction("Bring Forward")
            act_backward = z_menu.addAction("Send Backward")
            act_back = z_menu.addAction("Send to Back")

            menu.addSeparator()
            act_delete = menu.addAction("Delete")

            action = menu.exec(self._tree.viewport().mapToGlobal(position))

            if action == act_rename:
                self._tree.editItem(item, 0)
            elif action == act_front:
                self._apply_z_order("bring_to_front")
            elif action == act_forward:
                self._apply_z_order("bring_forward")
            elif action == act_backward:
                self._apply_z_order("send_backward")
            elif action == act_back:
                self._apply_z_order("send_to_back")
            elif action == act_delete:
                item_uuid = item.data(0, self.ITEM_UUID_ROLE)
                scene_item = self._get_item_by_uuid(item_uuid)
                if scene_item and self._scene:
                    self._scene.removeItem(scene_item)
                self.refresh()

