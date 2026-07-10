"""Layer panel widget for managing scene items by z-order.

Uses Qt's Model/View architecture:
- LayerItemModel: tree structure + drag/drop
- LayerItemDelegate: paints icons + text, handles click toggles
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.layer_tree_state import LayerTreeState
from ...core.undo_commands import CreateGroupCommand, DeleteGroupCommand
from ..delegates import LayerItemDelegate
from ..delegates.layer_icons import make_folder_add_icon, make_folder_remove_icon
from ..models import LayerItemModel
from ..views.keyboard_layer_tree_view import KeyboardLayerTreeView

if TYPE_CHECKING:
    from ...core.undo_stack import UndoStack

from ..models.layer_item_model import GROUP_UUID_ROLE, IS_GROUP_ROLE, IS_LINKED_ROLE, ITEM_UUID_ROLE


class LayerPanel(QtWidgets.QWidget):
    """Layer panel for managing scene items by z-order."""

    selectionChanged = QtCore.pyqtSignal(list)
    zOrderChanged = QtCore.pyqtSignal()
    visibilityChanged = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._scene: QtWidgets.QGraphicsScene | None = None
        self._layer_state: LayerTreeState | None = None

        self._model = LayerItemModel(self)
        self._model.orderChanged.connect(self._on_model_order_changed)
        self._model.visibilityChanged.connect(self._on_visibility_changed)

        # Debounce timers
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._do_refresh)

        self._sync_timer = QtCore.QTimer(self)
        self._sync_timer.setSingleShot(True)
        self._sync_timer.timeout.connect(self._do_sync_from_scene_selection)

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

        palette = self.palette()
        text_role = QtGui.QPalette.ColorRole.WindowText
        icon_size = 20
        for icon, tooltip, callback in [
            (
                make_folder_add_icon(icon_size, palette, text_role),
                "Group selected items",
                self._group_selected,
            ),
            (
                make_folder_remove_icon(icon_size, palette, text_role),
                "Ungroup selected group",
                self._ungroup_selected,
            ),
        ]:
            btn = QtWidgets.QToolButton()
            btn.setIcon(icon)
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            h_layout.addWidget(btn)

        layout.addWidget(header)

        # Tree view
        self._tree = KeyboardLayerTreeView()
        self._tree.setModel(self._model)
        self._tree.setItemDelegate(LayerItemDelegate(self._tree))
        self._tree.setHeaderHidden(True)
        self._tree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self._tree.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self._tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setIndentation(16)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)

        if sm := self._tree.selectionModel():
            sm.selectionChanged.connect(self._on_selection_changed)

        self._tree.deleteKeyPressed.connect(self._delete_selected)
        self._tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.expanded.connect(lambda idx: self._set_node_collapsed(idx, False))
        self._tree.collapsed.connect(lambda idx: self._set_node_collapsed(idx, True))
        layout.addWidget(self._tree, 1)

        # Z-order buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setContentsMargins(8, 4, 8, 8)
        for text, tooltip, op in [
            ("↑ Up", "Bring forward", "bring_forward"),
            ("↓ Down", "Send backward", "send_backward"),
        ]:
            z_btn = QtWidgets.QPushButton(text)
            z_btn.setToolTip(tooltip)
            z_btn.clicked.connect(lambda _, o=op: self._apply_z_order(o))
            btn_layout.addWidget(z_btn)
        layout.addLayout(btn_layout)

    def set_scene(self, scene: QtWidgets.QGraphicsScene) -> None:
        self._scene = scene
        self._model.set_context(
            scene=scene, layer_state=self._layer_state, undo_stack=self._get_undo_stack()
        )

    @property
    def model(self) -> LayerItemModel:
        return self._model

    def set_layer_state(self, layer_state: LayerTreeState) -> None:
        self._layer_state = layer_state
        layer_state.changed.connect(self.refresh)
        self._model.set_context(
            scene=self._scene, layer_state=layer_state, undo_stack=self._get_undo_stack()
        )

    def _get_undo_stack(self) -> UndoStack | None:
        if not self._scene or not (views := self._scene.views()):
            return None
        window = views[0].window()
        return cast("UndoStack | None", getattr(window, "undo_stack", None))

    def has_tree_focus(self) -> bool:
        """True when the layer tree view currently has keyboard focus."""
        return self._tree.hasFocus()

    def cleanup(self) -> None:
        """Clean up before shutdown to prevent accessing deleted objects."""
        self._refresh_timer.stop()
        self._sync_timer.stop()
        self._model.cleanup()

    # --- Refresh ---

    def refresh(self) -> None:
        """Debounced refresh."""
        self._refresh_timer.stop()
        self._sync_timer.stop()
        self._refresh_timer.start(100)

    def _do_refresh(self) -> None:
        if not self._scene:
            return
        # Never reset the model while the user is renaming a layer: a
        # beginResetModel/endResetModel tears down the open inline editor and the
        # typed name is lost. Defer until the edit finishes.
        if self._tree.state() == QtWidgets.QAbstractItemView.State.EditingState:
            self._refresh_timer.start(100)
            return
        self._model.set_context(
            scene=self._scene,
            layer_state=self._layer_state,
            undo_stack=self._get_undo_stack(),
        )
        self._apply_group_collapsed_state()
        self._do_sync_from_scene_selection()

    def _apply_group_collapsed_state(self) -> None:
        """Expand/collapse groups based on LayerTreeState."""
        if not self._layer_state:
            return
        self._tree.blockSignals(True)
        try:
            self._walk_and_apply_collapsed(QtCore.QModelIndex())
        finally:
            self._tree.blockSignals(False)

    def _walk_and_apply_collapsed(self, parent: QtCore.QModelIndex) -> None:
        for r in range(self._model.rowCount(parent)):
            idx = self._model.index(r, 0, parent)
            if not idx.isValid():
                continue
            row_count = self._model.rowCount(idx)
            if row_count > 0:
                is_group = bool(idx.data(IS_GROUP_ROLE))
                if is_group:
                    uuid = cast(str, idx.data(GROUP_UUID_ROLE))
                else:
                    uuid = cast(str, idx.data(ITEM_UUID_ROLE))
                if is_group:
                    node = (
                        self._layer_state.get_node(uuid)
                        if uuid and self._layer_state
                        else None
                    )
                    collapsed = bool(getattr(node, "collapsed", False)) if node else False
                    self._tree.setExpanded(idx, not collapsed)
                else:
                    self._tree.setExpanded(idx, True)
                self._walk_and_apply_collapsed(idx)

    def _set_node_collapsed(self, idx: QtCore.QModelIndex, collapsed: bool) -> None:
        if not self._layer_state or not idx.isValid():
            return
        is_group = bool(idx.data(IS_GROUP_ROLE))
        if not is_group and collapsed:
            self._tree.blockSignals(True)
            self._tree.setExpanded(idx, True)
            self._tree.blockSignals(False)
            return
        node_uuid = idx.data(GROUP_UUID_ROLE) if is_group else idx.data(ITEM_UUID_ROLE)
        if node_uuid:
            self._layer_state.set_node_collapsed(str(node_uuid), collapsed, emit=True)

    # --- Z-Order ---

    def _apply_z_order(self, operation: str) -> None:
        if not self._scene or not self._layer_state:
            return
        uuids = [
            item.item_uuid for item in self._scene.selectedItems() if hasattr(item, "item_uuid")
        ]
        if not uuids:
            return
        from ...core.undo_commands import ZOrderCommand

        undo_stack = self._get_undo_stack()
        cmd = ZOrderCommand(self._layer_state, uuids, operation)
        if undo_stack:
            undo_stack.push(cmd)
        else:
            cmd.execute()

    def _on_model_order_changed(self) -> None:
        self.zOrderChanged.emit()

    def _on_visibility_changed(self) -> None:
        self.visibilityChanged.emit()

    # --- Selection ---

    def _on_selection_changed(
        self,
        _sel: QtCore.QItemSelection | None = None,
        _desel: QtCore.QItemSelection | None = None,
    ) -> None:
        if not self._scene:
            return
        selected: list[str] = []
        if sm := self._tree.selectionModel():
            for idx in sm.selectedRows(0):
                selected.extend(self._model.item_uuids_under(idx))
        self._scene.clearSelection()
        for item in self._scene.items():
            if hasattr(item, "item_uuid") and item.item_uuid in selected:
                item.setSelected(True)
        self.selectionChanged.emit(selected)

    def sync_from_scene_selection(self) -> None:
        """Sync layer panel selection from scene (debounced)."""
        if self._refresh_timer.isActive():
            return
        self._sync_timer.stop()
        self._sync_timer.start(50)

    def _do_sync_from_scene_selection(self) -> None:
        if not self._scene:
            return
        # Selecting a layer for rename triggers this sync; clearing/reselecting
        # the tree's selection mid-edit closes the inline editor before the name
        # is committed. Skip while editing — a later selection change re-syncs.
        if self._tree.state() == QtWidgets.QAbstractItemView.State.EditingState:
            return
        uuids = {
            item.item_uuid for item in self._scene.selectedItems() if hasattr(item, "item_uuid")
        }
        sm = self._tree.selectionModel()
        if not sm:
            return
        sm.blockSignals(True)
        try:
            sm.clearSelection()
            if uuids:
                self._select_by_uuid(uuids, QtCore.QModelIndex())
        finally:
            sm.blockSignals(False)
        if viewport := self._tree.viewport():
            viewport.update()

    def _select_by_uuid(self, uuids: set[str], parent: QtCore.QModelIndex) -> None:
        sm = self._tree.selectionModel()
        if not sm:
            return
        for r in range(self._model.rowCount(parent)):
            idx = self._model.index(r, 0, parent)
            if not idx.isValid():
                continue
            if not bool(idx.data(IS_GROUP_ROLE)):
                if idx.data(ITEM_UUID_ROLE) in uuids:
                    sm.select(
                        idx,
                        QtCore.QItemSelectionModel.SelectionFlag.Select
                        | QtCore.QItemSelectionModel.SelectionFlag.Rows,
                    )
            self._select_by_uuid(uuids, idx)

    # --- Actions ---

    def _group_selected(self) -> None:
        if not self._scene or not self._layer_state:
            return
        selected = self._scene.selectedItems()
        if len(selected) < 2:
            QtWidgets.QMessageBox.information(
                self, "Group Items", "Select at least 2 items to group."
            )
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "Create Group", "Group name:", text="Group")
        if not ok:
            return
        uuids = [item.item_uuid for item in selected if hasattr(item, "item_uuid")]
        if not uuids:
            return
        cmd = CreateGroupCommand(self._layer_state, name or "Group", uuids, None)
        if undo := self._get_undo_stack():
            undo.push(cmd)
        else:
            cmd.execute()

    def _ungroup_selected(self) -> None:
        if not self._layer_state:
            return
        group_uuid: str | None = None

        # Check if a group is selected in tree
        if sm := self._tree.selectionModel():
            for idx in sm.selectedRows(0):
                if bool(idx.data(IS_GROUP_ROLE)):
                    group_uuid = cast(str, idx.data(GROUP_UUID_ROLE))
                    break

        # Check if selected items share a common group
        if not group_uuid and self._scene:
            groups: set[str] = set()
            for item in self._scene.selectedItems():
                if hasattr(item, "item_uuid"):
                    node = self._layer_state.get_node(item.item_uuid)
                    if node and node.parent and node.parent.is_group():
                        groups.add(node.parent.uuid)
            if len(groups) == 1:
                group_uuid = groups.pop()

        if not group_uuid:
            QtWidgets.QMessageBox.information(self, "Ungroup", "Select a group to ungroup.")
            return

        cmd = DeleteGroupCommand(self._layer_state, group_uuid, keep_items=True)
        if undo := self._get_undo_stack():
            undo.push(cmd)
        else:
            cmd.execute()

    def _delete_selected(self) -> None:
        if not self._scene:
            return
        sm = self._tree.selectionModel()
        if not sm:
            return
        rows = sm.selectedRows(0)
        if not rows:
            return

        from ...core.undo_commands import RemoveItemCommand

        undo = self._get_undo_stack()
        group_uuids: set[str] = set()
        item_uuids: set[str] = set()

        for idx in rows:
            if bool(idx.data(IS_GROUP_ROLE)):
                if gu := idx.data(GROUP_UUID_ROLE):
                    group_uuids.add(str(gu))
            elif iu := idx.data(ITEM_UUID_ROLE):
                item_uuids.add(str(iu))

        linked_groups: list[tuple[str, str]] = []  # (gid, display_name)
        for gid in list(group_uuids):
            if self._layer_state:
                node = self._layer_state.get_node(gid)
                if node and node.is_linked():
                    linked_groups.append((gid, node.name or gid))
                    group_uuids.discard(gid)
                    continue
                cmd = DeleteGroupCommand(self._layer_state, gid, keep_items=False)
                if undo:
                    undo.push(cmd)
                else:
                    cmd.execute()

        if linked_groups:
            self._prompt_linked_delete(linked_groups)

        # Skip items that belong to a linked group
        if self._layer_state:
            for uid in list(item_uuids):
                node = self._layer_state.get_node(uid)
                if not node:
                    continue
                if node.parent and node.parent.is_linked():
                    item_uuids.discard(uid)

        for uid in item_uuids:
            item = next(
                (
                    i
                    for i in self._scene.items()
                    if hasattr(i, "item_uuid") and i.item_uuid == uid
                ),
                None,
            )
            if item:
                if undo:
                    undo.push(RemoveItemCommand(self._scene, item, self._layer_state))
                else:
                    if self._layer_state:
                        self._layer_state.remove_item(uid, emit=True)
                    self._scene.removeItem(item)
            elif self._layer_state:
                # Orphan node: exists in layer state but not in scene — clean it up
                self._layer_state.remove_item(uid, emit=True)

        self.refresh()

    def _find_scene_item(self, item_uuid: str) -> QtWidgets.QGraphicsItem | None:
        """Find a scene item by its UUID."""
        if not self._scene:
            return None
        for item in self._scene.items():
            if hasattr(item, "item_uuid") and item.item_uuid == item_uuid:
                return item
        return None

    def _edit_item_by_uuid(self, item_uuid: str) -> None:
        """Open the property editor for the scene item with the given UUID."""
        item = self._find_scene_item(item_uuid)
        if item is not None:
            open_editor = getattr(item, "open_editor", None)
            if callable(open_editor):
                open_editor()

    def _edit_in_component_editor_by_uuid(self, item_uuid: str) -> None:
        """Open the Component Editor for the scene item with the given UUID."""
        from ...objects.generic.component_item import ComponentItem

        item = self._find_scene_item(item_uuid)
        if isinstance(item, ComponentItem):
            main_window = item._parent_window()
            if main_window is not None and hasattr(main_window, "open_component_editor_for_item"):
                main_window.open_component_editor_for_item(item)

    def _export_selected_as_assembly(self) -> None:
        """Delegate to FileController via the main window."""
        mw = self.window()
        if mw is not None and hasattr(mw, "file_controller"):
            mw.file_controller.export_selected_as_assembly()

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        idx = self._tree.indexAt(pos)
        menu = QtWidgets.QMenu(self)

        if idx.isValid():
            from ..models.layer_item_model import LOCKED_ROLE, VISIBLE_ROLE

            if not bool(idx.data(IS_GROUP_ROLE)):
                if iu := idx.data(ITEM_UUID_ROLE):
                    uid = str(iu)
                    if edit_act := menu.addAction("Edit…"):
                        edit_act.triggered.connect(
                            lambda _checked=False, u=uid: self._edit_item_by_uuid(u)
                        )
                    from ...objects.generic.component_item import ComponentItem

                    if isinstance(self._find_scene_item(uid), ComponentItem):
                        if ce_act := menu.addAction("Edit in Component Editor…"):
                            ce_act.triggered.connect(
                                lambda _checked=False, u=uid:
                                    self._edit_in_component_editor_by_uuid(u)
                            )
                    menu.addSeparator()

            vis_act = menu.addAction("Toggle Visibility")
            if vis_act:
                vis_act.triggered.connect(lambda: self._toggle_role(idx, VISIBLE_ROLE))
            lock_act = menu.addAction("Toggle Lock")
            if lock_act:
                lock_act.triggered.connect(lambda: self._toggle_role(idx, LOCKED_ROLE))
            menu.addSeparator()

            if bool(idx.data(IS_GROUP_ROLE)):
                is_linked = bool(idx.data(IS_LINKED_ROLE))
                if is_linked:
                    group_uuid = str(idx.data(GROUP_UUID_ROLE) or "")
                    node = self._layer_state.get_node(group_uuid) if self._layer_state else None
                    is_editing = (
                        node.link_metadata.editing
                        if node and node.link_metadata
                        else False
                    )

                    if is_editing:
                        if act := menu.addAction("Finish Editing"):
                            act.triggered.connect(
                                lambda _=False, u=group_uuid: self._finish_edit_linked(u)
                            )
                    else:
                        if act := menu.addAction("\U0001f517 Edit in Context"):
                            act.triggered.connect(
                                lambda _=False, u=group_uuid: self._edit_linked_in_context(u)
                            )

                    if act := menu.addAction("Refresh from Source"):
                        act.triggered.connect(
                            lambda _=False, u=group_uuid: self._refresh_linked(u)
                        )
                    if act := menu.addAction("Unlink (Embed)"):
                        act.triggered.connect(
                            lambda _=False, u=group_uuid: self._unlink_embed(u)
                        )
                    menu.addSeparator()
                else:
                    if act := menu.addAction("Ungroup"):
                        act.triggered.connect(self._ungroup_selected)
            else:
                if act := menu.addAction("Group with Selected"):
                    act.triggered.connect(self._group_selected)
            menu.addSeparator()
            if act := menu.addAction("Delete"):
                act.triggered.connect(self._delete_selected)

        menu.addSeparator()
        if z_menu := menu.addMenu("Z-Order"):
            for label, op in [
                ("Bring to Front", "bring_to_front"),
                ("Bring Forward", "bring_forward"),
                ("Send Backward", "send_backward"),
                ("Send to Back", "send_to_back"),
            ]:
                if act := z_menu.addAction(label):
                    act.triggered.connect(lambda _, o=op: self._apply_z_order(o))

        menu.addSeparator()
        has_selection = bool(
            self._scene and any(
                hasattr(it, "item_uuid") for it in self._scene.selectedItems()
            )
        )
        if export_act := menu.addAction("Export Selected as Assembly\u2026"):
            export_act.setEnabled(has_selection)
            export_act.triggered.connect(self._export_selected_as_assembly)

        if vp := self._tree.viewport():
            menu.exec(vp.mapToGlobal(pos))

    # --- Linked Assembly Actions ---

    def _edit_linked_in_context(self, group_uuid: str) -> None:
        mw = self.window()
        if mw is not None and hasattr(mw, "file_controller"):
            mw.file_controller.edit_linked_in_context(group_uuid)

    def _finish_edit_linked(self, group_uuid: str) -> None:
        mw = self.window()
        if mw is not None and hasattr(mw, "file_controller"):
            mw.file_controller.finish_edit_in_context(group_uuid)

    def _refresh_linked(self, group_uuid: str) -> None:
        mw = self.window()
        if mw is not None and hasattr(mw, "file_controller"):
            mw.file_controller.refresh_linked_assembly(group_uuid)

    def _unlink_embed(self, group_uuid: str) -> None:
        mw = self.window()
        if mw is not None and hasattr(mw, "file_controller"):
            mw.file_controller.unlink_embed(group_uuid)

    def _prompt_linked_delete(self, linked_groups: list[tuple[str, str]]) -> None:
        """Show a dialog for linked assemblies with Unlink / Delete / Cancel."""
        names = "\n".join(f"  - {name}" for _, name in linked_groups)
        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msg.setWindowTitle("Linked Assembly")
        msg.setText(
            f"The following are linked assemblies:\n{names}\n\n"
            "What would you like to do?"
        )
        btn_unlink = msg.addButton("Unlink", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        btn_delete = msg.addButton("Delete", QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked is btn_unlink:
            for gid, _ in linked_groups:
                self._unlink_embed(gid)
        elif clicked is btn_delete:
            for gid, _ in linked_groups:
                self._delete_linked_group(gid)

    def _delete_linked_group(self, group_uuid: str) -> None:
        """Fully delete a linked assembly: clean up service state and layer tree."""
        mw = self.window()
        if mw is not None and hasattr(mw, "linked_assembly_service"):
            mw.linked_assembly_service.remove_link(group_uuid)
        if self._layer_state:
            self._layer_state.delete_group(group_uuid, emit=True)
        if mw is not None and hasattr(mw, "file_controller"):
            mw.file_controller.mark_modified()
            mw.file_controller.traceRequested.emit()

    def _toggle_role(self, idx: QtCore.QModelIndex, role: int) -> None:
        from ..models.layer_item_model import LOCKED_ROLE

        new_value = not bool(idx.data(role))
        sm = self._tree.selectionModel()
        selected = sm.selectedRows(0) if sm else []

        if role == int(LOCKED_ROLE) and len(selected) > 1 and idx in selected:
            self._model.toggle_locked_for_indexes(selected, new_value)
        else:
            self._model.setData(idx, new_value, role)
        self.refresh()
