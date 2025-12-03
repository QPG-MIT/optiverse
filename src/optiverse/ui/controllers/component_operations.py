"""
Component operations handler for copy, paste, delete, and drop operations.

Extracts component manipulation logic from MainWindow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PyQt6 import QtCore, QtWidgets

from ...core.log_categories import LogCategory

if TYPE_CHECKING:
    from ...core.layer_group import GroupManager
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
        group_manager: GroupManager | None = None,
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
            group_manager: Optional group manager for group membership cleanup on delete
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
        self._group_manager = group_manager

        # Clipboard for copy/paste
        self._clipboard: list = []

    def set_group_manager(self, group_manager: GroupManager) -> None:
        """Set the group manager for delete operations."""
        self._group_manager = group_manager

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

        # Add to scene with undo support
        cmd = AddItemCommand(self.scene, item)
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
                cmd = RemoveItemCommand(self.scene, items_to_delete[0], self._group_manager)
            else:
                cmd = RemoveMultipleItemsCommand(self.scene, items_to_delete, self._group_manager)
            self.undo_stack.push(cmd)

        self._schedule_retrace()

    def copy_selected(self):
        """Copy selected items to clipboard."""
        from ...objects import BaseObj, RectangleItem
        from ...objects.annotations import RulerItem, TextNoteItem

        selected = self.scene.selectedItems()
        self._clipboard = []

        for item in selected:
            # Only copy items that have a clone method
            if isinstance(item, (BaseObj, RulerItem, TextNoteItem, RectangleItem)):
                self._clipboard.append(item)

        # Enable paste action if we have items
        self._set_paste_enabled(len(self._clipboard) > 0)

        if len(self._clipboard) > 0:
            self.log_service.info(
                f"Copied {len(self._clipboard)} item(s) to clipboard", LogCategory.COPY_PASTE
            )

    def paste_items(self, target_pos: QtCore.QPointF | None = None):
        """Paste items from clipboard using clone() method.

        Args:
            target_pos: Optional target position in scene coordinates.
                       If provided, items will be pasted centered at this position.
                       If None, items are pasted with a fixed offset from original position.
        """
        from ...core.undo_commands import PasteItemsCommand

        if not self._clipboard:
            self.log_service.warning("Cannot paste - clipboard is empty", LogCategory.COPY_PASTE)
            return

        # Calculate offset based on target position or use fixed offset
        if target_pos is not None:
            # Calculate centroid of clipboard items
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

            # Calculate offset to move centroid to target position
            paste_offset = (target_pos.x() - centroid_x, target_pos.y() - centroid_y)
        else:
            # Default offset for pasted items so they're visible
            paste_offset = (20.0, 20.0)

        pasted_items = []

        for item in self._clipboard:
            try:
                # Use clone() to create a proper deep copy
                cloned_item = item.clone(paste_offset)

                # Connect signals
                self._connect_item_signals(cloned_item)

                pasted_items.append(cloned_item)

            except Exception as e:
                import traceback

                self.log_service.error(
                    f"Error pasting {type(item).__name__}: {e}\n{traceback.format_exc()}",
                    LogCategory.COPY_PASTE,
                )

        if pasted_items:
            self.log_service.info(
                f"Successfully pasted {len(pasted_items)} item(s)", LogCategory.COPY_PASTE
            )

            # Use undo command to add all pasted items at once
            cmd = PasteItemsCommand(self.scene, pasted_items)
            self.undo_stack.push(cmd)

            # Clear current selection and select pasted items
            self.scene.clearSelection()
            for item in pasted_items:
                item.setSelected(True)

            self._schedule_retrace()

    @property
    def has_clipboard_items(self) -> bool:
        """Check if clipboard has items for pasting."""
        return len(self._clipboard) > 0
