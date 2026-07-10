"""
Component operations handler for copy, paste, delete, and drop operations.

Extracts component manipulation logic from MainWindow.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets

from ...core.log_categories import LogCategory

if TYPE_CHECKING:
    from ...core.layer_tree_state import LayerTreeState
    from ...core.undo_stack import UndoStack
    from ...services.collaboration_manager import CollaborationManager
    from ...services.log_service import LogService


class ComponentOperationsHandler:
    """
    Handles component operations: copy, paste, delete, and drop from library.

    Extracts component manipulation logic from MainWindow for better separation of concerns.
    """

    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        undo_stack: UndoStack,
        collaboration_manager: CollaborationManager,
        log_service: LogService,
        snap_to_grid_getter: Callable[[], bool],
        connect_item_signals: Callable,
        schedule_retrace: Callable,
        set_paste_enabled: Callable[[bool], None],
        parent_widget: QtWidgets.QWidget,
        layer_state: LayerTreeState | None = None,
    ):
        """
        Initialize the component operations handler.

        Args:
            scene: Graphics scene containing items
            undo_stack: Undo stack for command creation
            collaboration_manager: Manager for broadcasting changes
            log_service: Logging service
            snap_to_grid_getter: Callable returning whether snap to grid is enabled
            connect_item_signals: Callable to connect signals on new items
            schedule_retrace: Callable to schedule ray retracing
            set_paste_enabled: Callable to enable/disable paste action
            parent_widget: Parent widget for dialogs
            layer_state: Optional layer state for group membership cleanup on delete
        """
        self.scene = scene
        self.undo_stack = undo_stack
        self.collaboration_manager = collaboration_manager
        self.log_service = log_service
        self._get_snap_to_grid = snap_to_grid_getter
        self._connect_item_signals = connect_item_signals
        self._schedule_retrace = schedule_retrace
        self._set_paste_enabled = set_paste_enabled
        self.parent_widget = parent_widget
        self._layer_state = layer_state

        # Clipboard for copy/paste
        self._clipboard: list = []

    def set_layer_state(self, layer_state: LayerTreeState) -> None:
        """Set the layer state for delete operations."""
        self._layer_state = layer_state

    def on_drop_component(self, rec: dict, scene_pos: QtCore.QPointF):
        """
        Handle component drop from library.

        Uses ComponentFactory to ensure dropped item matches ghost preview.

        Args:
            rec: Component record dictionary from library
            scene_pos: Position in scene coordinates where component was dropped
        """
        from ...core.undo_commands import AddItemCommand
        from ...objects.component_factory import ComponentFactory

        # Apply snap to grid if enabled
        if self._get_snap_to_grid():
            scene_pos = QtCore.QPointF(round(scene_pos.x()), round(scene_pos.y()))

        # Use ComponentFactory to create the item
        item = ComponentFactory.create_item_from_dict(rec, scene_pos.x(), scene_pos.y())

        if not item:
            name = rec.get("name", "Unknown")
            QtWidgets.QMessageBox.warning(
                self.parent_widget,
                "Invalid Component",
                f"Cannot create component '{name}': Unknown error during creation.",
            )
            return

        # Connect signals
        self._connect_item_signals(item)

        # Auto-index duplicate names (e.g. second "Lens" becomes "Lens 2")
        from ...objects.naming import assign_unique_name

        assign_unique_name(self.scene, item)

        # Add to scene with undo support
        cmd = AddItemCommand(self.scene, item, self._layer_state)
        self.undo_stack.push(cmd)

        # Clear previous selection and select only the newly dropped item
        self.scene.clearSelection()
        item.setSelected(True)

        # Broadcast addition to collaboration
        self.collaboration_manager.broadcast_add_item(item)

        # Trigger ray tracing
        self._schedule_retrace()

    def delete_selected(self):
        """Delete selected items using undo stack."""
        from ...core.undo_commands import RemoveItemCommand, RemoveMultipleItemsCommand
        from ...objects import BaseObj, RectangleItem
        from ...objects.annotations import AngleMeasureItem, RulerItem, TextNoteItem
        from ...objects.annotations.path_measure_item import PathMeasureItem

        selected = self.scene.selectedItems()
        items_to_delete = []
        locked_items = []

        for item in selected:
            # Only delete optical components and annotations (not grid lines or rays)
            if isinstance(
                item,
                (
                    BaseObj,
                    RulerItem,
                    TextNoteItem,
                    RectangleItem,
                    PathMeasureItem,
                    AngleMeasureItem,
                ),
            ):
                # Check if item is locked
                if isinstance(item, BaseObj) and item.is_locked():
                    locked_items.append(item)
                else:
                    items_to_delete.append(item)
                    # Broadcast deletion to collaboration
                    self.collaboration_manager.broadcast_remove_item(item)

        # Warn user if trying to delete locked items
        if locked_items:
            locked_count = len(locked_items)
            QtWidgets.QMessageBox.warning(
                self.parent_widget,
                "Locked Items",
                f"Cannot delete {locked_count} locked item(s).\n"
                f"Unlock them first in the edit dialog.",
            )

        # Use a single command for all deletions
        if items_to_delete:
            if len(items_to_delete) == 1:
                cmd = RemoveItemCommand(self.scene, items_to_delete[0], self._layer_state)
            else:
                cmd = RemoveMultipleItemsCommand(self.scene, items_to_delete, self._layer_state)
            self.undo_stack.push(cmd)

        self._schedule_retrace()

    _MIME_TYPE = "application/x-optiverse-items"

    def copy_selected(self):
        """Copy selected items to clipboard.

        When a ComponentItem with an autolabel is copied, the label is
        automatically included so paste can re-link it.  Items are also
        serialized to the system clipboard for cross-instance paste.
        """
        from ...objects import BaseObj, RectangleItem
        from ...objects.annotations import RulerItem, TextNoteItem
        from ...objects.generic.component_item import ComponentItem

        selected = self.scene.selectedItems()
        self._clipboard = []
        copied_uuids: set[str] = set()

        for item in selected:
            if isinstance(item, (BaseObj, RulerItem, TextNoteItem, RectangleItem)):
                self._clipboard.append(item)
                uid = getattr(item, "item_uuid", None)
                if uid:
                    copied_uuids.add(uid)

        # Also include autolabels owned by any copied ComponentItem
        for item in list(self._clipboard):
            if isinstance(item, ComponentItem):
                label = item._find_autolabel()
                if label is not None and label.item_uuid not in copied_uuids:
                    self._clipboard.append(label)
                    copied_uuids.add(label.item_uuid)

        self._set_paste_enabled(len(self._clipboard) > 0)

        if len(self._clipboard) > 0:
            self._copy_to_system_clipboard()
            self.log_service.info(
                f"Copied {len(self._clipboard)} item(s) to clipboard", LogCategory.COPY_PASTE
            )

    def _copy_to_system_clipboard(self) -> None:
        """Serialize clipboard items to the system clipboard for cross-instance paste."""
        import json

        from PyQt6.QtGui import QGuiApplication

        from ...objects import BaseObj, RectangleItem
        from ...objects.annotations import RulerItem, TextNoteItem
        from ...objects.type_registry import serialize_item

        items_data: list[dict] = []
        for item in self._clipboard:
            try:
                if isinstance(item, (RulerItem, TextNoteItem, RectangleItem)):
                    items_data.append(item.to_dict())
                elif isinstance(item, BaseObj):
                    items_data.append(serialize_item(item))
            except Exception:
                pass

        if not items_data:
            return

        payload = json.dumps({"optiverse_clipboard": items_data})
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            mime = QtCore.QMimeData()
            mime.setData(self._MIME_TYPE, payload.encode("utf-8"))
            clipboard.setMimeData(mime)

    def paste_items(self, target_pos: QtCore.QPointF | None = None):
        """Paste items from clipboard using clone() method.

        If the in-memory clipboard is empty, attempts to read serialized
        items from the system clipboard (cross-instance paste).

        Args:
            target_pos: Optional target position in scene coordinates.
                       If provided, items will be pasted centered at this position.
                       If None, items are pasted with a fixed offset from original position.
        """
        from ...core.undo_commands import PasteItemsCommand
        from ...objects.annotations import TextNoteItem
        from ...objects.generic.component_item import ComponentItem

        # Try cross-instance paste when local clipboard is empty
        if not self._clipboard:
            cross_items = self._items_from_system_clipboard()
            if cross_items:
                self._paste_deserialized_items(cross_items, target_pos)
                return
            self.log_service.warning("Cannot paste - clipboard is empty", LogCategory.COPY_PASTE)
            return

        # Same-instance paste via clone()
        if target_pos is not None:
            centroid_x = 0.0
            centroid_y = 0.0
            count = 0

            for item in self._clipboard:
                pos = item.scenePos()
                centroid_x += pos.x()
                centroid_y += pos.y()
                count += 1

            if count > 0:
                centroid_x /= count
                centroid_y /= count

            paste_offset = (target_pos.x() - centroid_x, target_pos.y() - centroid_y)
        else:
            from ...core import preferences

            paste_offset = (preferences.clone_offset_x_mm, preferences.clone_offset_y_mm)

        pasted_items = []
        owner_map: dict[str, ComponentItem] = {}

        for item in self._clipboard:
            try:
                cloned_item = item.clone(paste_offset)
                self._connect_item_signals(cloned_item)
                pasted_items.append(cloned_item)

                if isinstance(item, ComponentItem):
                    owner_map[item.item_uuid] = cloned_item

            except Exception as e:
                import traceback

                self.log_service.error(
                    f"Error pasting {type(item).__name__}: {e}\n{traceback.format_exc()}",
                    LogCategory.COPY_PASTE,
                )

        for cloned in pasted_items:
            if not isinstance(cloned, TextNoteItem):
                continue
            orig = next(
                (it for it in self._clipboard
                 if isinstance(it, TextNoteItem) and it.owner_uuid is not None
                 and cloned.toPlainText() == it.toPlainText()),
                None,
            )
            if orig is None or orig.owner_uuid is None:
                continue
            new_owner = owner_map.get(orig.owner_uuid)
            if new_owner is not None:
                cloned.owner_uuid = new_owner.item_uuid
                cloned._owner_offset = QtCore.QPointF(orig._owner_offset)
                new_owner.edited.connect(cloned.follow_owner)

        if pasted_items:
            self.log_service.info(
                f"Successfully pasted {len(pasted_items)} item(s)", LogCategory.COPY_PASTE
            )

            # Auto-index duplicate names across the scene and within this batch
            # (a pasted/duplicated "Lens" becomes "Lens 2", two at once "Lens 2"/"Lens 3")
            from ...objects.naming import assign_unique_names

            assign_unique_names(self.scene, pasted_items)

            cmd = PasteItemsCommand(self.scene, pasted_items, self._layer_state)
            self.undo_stack.push(cmd)

            self.scene.clearSelection()
            for item in pasted_items:
                item.setSelected(True)

            self._schedule_retrace()

    # ---- Cross-instance helpers ----

    def _items_from_system_clipboard(self) -> list:
        """Deserialize optiverse items from the system clipboard, if present."""
        import json

        from PyQt6.QtGui import QGuiApplication

        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return []
        mime = clipboard.mimeData()
        if mime is None or not mime.hasFormat(self._MIME_TYPE):
            return []

        try:
            raw = mime.data(self._MIME_TYPE).data().decode("utf-8")
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return []

        item_dicts = payload.get("optiverse_clipboard", [])
        if not isinstance(item_dicts, list):
            return []

        return self._deserialize_item_dicts(item_dicts)

    def _deserialize_item_dicts(self, item_dicts: list[dict]) -> list:
        """Reconstruct scene items from a list of serialized dicts."""
        import uuid as _uuid

        from ...objects import RectangleItem
        from ...objects.annotations import RulerItem, TextNoteItem
        from ...objects.type_registry import deserialize_item

        items = []
        for d in item_dicts:
            try:
                item_type = d.get("type", d.get("_type", ""))
                new_item: object | None = None
                if item_type == "ruler":
                    new_item = RulerItem.from_dict(d)
                elif item_type in ("text_note", "text"):
                    new_item = TextNoteItem.from_dict(d)
                elif item_type == "rectangle":
                    new_item = RectangleItem.from_dict(d)
                else:
                    new_item = deserialize_item(d)

                if new_item is not None:
                    if hasattr(new_item, "item_uuid"):
                        new_item.item_uuid = str(_uuid.uuid4())  # type: ignore[union-attr]
                    items.append(new_item)
            except Exception:
                pass
        return items

    def _paste_deserialized_items(
        self,
        items: list,
        target_pos: QtCore.QPointF | None = None,
    ) -> None:
        """Add deserialized items to the scene with an optional target offset."""
        from ...core import preferences
        from ...core.undo_commands import PasteItemsCommand

        if target_pos is not None:
            centroid_x = 0.0
            centroid_y = 0.0
            for it in items:
                p = it.pos()
                centroid_x += p.x()
                centroid_y += p.y()
            if items:
                centroid_x /= len(items)
                centroid_y /= len(items)
            dx = target_pos.x() - centroid_x
            dy = target_pos.y() - centroid_y
        else:
            dx = preferences.clone_offset_x_mm
            dy = preferences.clone_offset_y_mm

        for it in items:
            it.setPos(it.pos().x() + dx, it.pos().y() + dy)
            self._connect_item_signals(it)

        # Auto-index duplicate names against the scene and within this batch
        from ...objects.naming import assign_unique_names

        assign_unique_names(self.scene, items)

        cmd = PasteItemsCommand(self.scene, items, self._layer_state)
        self.undo_stack.push(cmd)

        self.scene.clearSelection()
        for it in items:
            it.setSelected(True)

        self._schedule_retrace()
        self.log_service.info(
            f"Pasted {len(items)} item(s) from another instance", LogCategory.COPY_PASTE
        )

    @property
    def has_clipboard_items(self) -> bool:
        """Check if clipboard has items for pasting (local or system)."""
        if self._clipboard:
            return True
        from PyQt6.QtGui import QGuiApplication

        cb = QGuiApplication.clipboard()
        if cb is not None:
            mime = cb.mimeData()
            if mime is not None and mime.hasFormat(self._MIME_TYPE):
                return True
        return False
