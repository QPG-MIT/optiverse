"""
File controller for handling save/load/autosave operations.

Extracts file management UI logic from MainWindow.
Supports importing assemblies as grouped layers.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Callable

from PyQt6 import QtCore, QtWidgets

from ...core.constants import AUTOSAVE_DEBOUNCE_MS
from ...services.error_handler import ErrorContext
from ...services.scene_file_manager import SceneFileManager

if TYPE_CHECKING:
    from ...core.layer_group import GroupManager
    from ...core.undo_stack import UndoStack
    from ...services.log_service import LogService


class FileController(QtCore.QObject):
    """
    Controller for file operations (save, open, autosave).

    Wraps SceneFileManager and provides UI interactions.
    """

    # Signal emitted when file operations complete and trace should be updated
    traceRequested = QtCore.pyqtSignal()
    # Signal emitted when window title should be updated
    windowTitleChanged = QtCore.pyqtSignal(str)

    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        undo_stack: UndoStack,
        log_service: LogService,
        get_ray_data: Callable,
        parent_widget: QtWidgets.QWidget,
        connect_item_signals: Callable | None = None,
        group_manager: GroupManager | None = None,
    ):
        super().__init__(parent_widget)

        self._parent = parent_widget
        self._undo_stack = undo_stack
        self._is_modified = False
        self._group_manager = group_manager
        self._log_service = log_service
        self._scene = scene
        self._connect_item_signals = connect_item_signals

        # Create file manager
        self.file_manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=get_ray_data,
            on_modified=self._on_modified_changed,
            parent_widget=parent_widget,
            connect_item_signals=connect_item_signals,
        )

        # Forward group_manager to file manager for saving/loading groups
        if group_manager:
            self.file_manager.set_group_manager(group_manager)

    def set_group_manager(self, group_manager: GroupManager) -> None:
        """Set the group manager for import-as-layer functionality."""
        self._group_manager = group_manager
        self.file_manager.set_group_manager(group_manager)

        # Autosave timer
        self._autosave_timer = QtCore.QTimer()
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DEBOUNCE_MS)
        self._autosave_timer.timeout.connect(self._do_autosave)

        # Connect undo stack to modification tracking
        self._undo_stack.commandPushed.connect(self._on_command_pushed)

    @property
    def saved_file_path(self) -> str | None:
        """Get the current saved file path."""
        return self.file_manager.saved_file_path

    @saved_file_path.setter
    def saved_file_path(self, value: str | None):
        """Set the saved file path."""
        self.file_manager.saved_file_path = value

    @property
    def is_modified(self) -> bool:
        """Check if there are unsaved changes."""
        return self._is_modified

    def _on_command_pushed(self):
        """Handle command pushed - mark modified and schedule autosave."""
        self.mark_modified()
        self._schedule_autosave()

    def mark_modified(self):
        """Mark the scene as having unsaved changes."""
        self.file_manager.mark_modified()

    def mark_clean(self):
        """Mark the scene as saved (no unsaved changes)."""
        self.file_manager.mark_clean()

    def _on_modified_changed(self, is_modified: bool):
        """Callback when file manager's modified state changes."""
        self._is_modified = is_modified
        self._update_window_title()

    def _update_window_title(self):
        """Update window title to show file name and modified state."""
        if self.saved_file_path:
            filename = os.path.basename(self.saved_file_path)
            filename_no_ext = os.path.splitext(filename)[0]
            title = filename_no_ext
        else:
            title = "Untitled"

        if self._is_modified:
            title = f"{title} — Edited"

        self.windowTitleChanged.emit(title)

    def _schedule_autosave(self):
        """Schedule autosave with debouncing."""
        if self._autosave_timer:
            self._autosave_timer.stop()
            self._autosave_timer.start()

    def _do_autosave(self):
        """Perform autosave (delegated to file manager)."""
        self.file_manager.do_autosave()

    def check_autosave_recovery(self) -> bool:
        """Check for autosave on startup."""
        if self.file_manager.check_autosave_recovery():
            self.traceRequested.emit()
            return True
        return False

    def prompt_save_changes(self) -> QtWidgets.QMessageBox.StandardButton:
        """
        Prompt user to save unsaved changes.

        Returns:
            User's response (Save, Discard, Cancel)
        """
        reply = self.file_manager.prompt_save_changes()
        if reply == QtWidgets.QMessageBox.StandardButton.Save:
            self.save_assembly()
            if self._is_modified:
                return QtWidgets.QMessageBox.StandardButton.Cancel
        return reply

    def save_assembly(self):
        """Quick save: save to current file or prompt if new."""
        with ErrorContext("while saving assembly", suppress=True):
            if self.saved_file_path:
                self.file_manager.save_to_file(self.saved_file_path)
            else:
                self.save_assembly_as()

    def save_assembly_as(self):
        """Save As: always prompt for new file location."""
        with ErrorContext("while saving assembly", suppress=True):
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self._parent, "Save Assembly As", "", "Optics Assembly (*.json)"
            )
            if path:
                self.file_manager.save_to_file(path)

    def open_assembly(self) -> bool:
        """
        Load all elements from JSON file.

        Returns:
            True if file was opened successfully
        """
        with ErrorContext("while opening assembly", suppress=True):
            if self._is_modified:
                reply = self.prompt_save_changes()
                if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return False

            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self._parent, "Open Assembly", "", "Optics Assembly (*.json)"
            )
            if not path:
                return False

            if not self.file_manager.open_file(path):
                return False

        # Clear undo history after loading
        self._undo_stack.clear()
        self.traceRequested.emit()
        return True

    def import_as_layer(self) -> bool:
        """
        Import an assembly file as a new layer (group).

        Does not clear the current scene. Creates a parent group containing
        all imported items. Preserves any group hierarchy from the imported file
        as nested groups under the parent group.

        Returns:
            True if import was successful
        """
        with ErrorContext("while importing assembly as layer", suppress=True):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self._parent, "Import Assembly as Layer", "", "Optics Assembly (*.json)"
            )
            if not path:
                return False

            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                self._log_service.error(f"Failed to load file: {e}", "Import")
                QtWidgets.QMessageBox.warning(
                    self._parent,
                    "Import Failed",
                    f"Could not read file:\n{e}",
                )
                return False

            # Import items without clearing scene
            imported_uuids, file_groups, grouped_uuids = self._import_items_from_data(
                data
            )

            if not imported_uuids:
                QtWidgets.QMessageBox.information(
                    self._parent,
                    "Import Complete",
                    "No items were imported from the file.",
                )
                return False

            # Use filename (without extension) as parent group name
            group_name = os.path.splitext(os.path.basename(path))[0]

            if self._group_manager:
                # Find ungrouped items (items not in any group from the file)
                ungrouped_uuids = [
                    uuid for uuid in imported_uuids if uuid not in grouped_uuids
                ]

                # Create the parent group with only ungrouped items
                parent_group = self._group_manager.create_group(
                    group_name, ungrouped_uuids
                )

                # Import groups from the file and set them as children of parent
                if file_groups:
                    imported_groups = self._group_manager.import_groups_from_dict_list(
                        file_groups
                    )
                    # Set parent for all imported root groups (those without a parent)
                    for group in imported_groups:
                        if group.parent_group_uuid is None:
                            self._group_manager.set_group_parent(
                                group.group_uuid, parent_group.group_uuid
                            )

            # Mark as modified and retrace
            self.mark_modified()
            self.traceRequested.emit()

            self._log_service.info(
                f"Imported {len(imported_uuids)} items as layer '{group_name}'",
                "Import",
            )

            return True

        return False

    def _import_items_from_data(
        self, data: dict
    ) -> tuple[list[str], list[dict], set[str]]:
        """
        Import items from data dict without clearing scene.

        Args:
            data: Dictionary containing assembly data

        Returns:
            Tuple of:
            - List of all imported item UUIDs
            - List of group dicts from the file (for hierarchy preservation)
            - Set of item UUIDs that were in groups in the file
        """

        from ...objects import RectangleItem
        from ...objects.annotations import RulerItem, TextNoteItem
        from ...objects.type_registry import deserialize_item

        imported_uuids: list[str] = []

        # Import optical items
        for item_data in data.get("items", []):
            try:
                item = deserialize_item(item_data)
                self._scene.addItem(item)
                if self._connect_item_signals:
                    self._connect_item_signals(item)
                if hasattr(item, "item_uuid"):
                    imported_uuids.append(item.item_uuid)
            except (KeyError, ValueError, TypeError) as e:
                self._log_service.error(f"Error importing item: {e}", "Import")

        # Import rulers
        for ruler_data in data.get("rulers", []):
            try:
                ruler = RulerItem.from_dict(ruler_data)
                self._scene.addItem(ruler)
                if self._connect_item_signals:
                    self._connect_item_signals(ruler)
                if hasattr(ruler, "item_uuid"):
                    imported_uuids.append(ruler.item_uuid)
            except (KeyError, ValueError, TypeError) as e:
                self._log_service.error(f"Error importing ruler: {e}", "Import")

        # Import text notes
        for text_data in data.get("texts", []):
            try:
                text_item = TextNoteItem.from_dict(text_data)
                self._scene.addItem(text_item)
                if hasattr(text_item, "item_uuid"):
                    imported_uuids.append(text_item.item_uuid)
            except (KeyError, ValueError, TypeError) as e:
                self._log_service.error(f"Error importing text: {e}", "Import")

        # Import rectangles
        for rect_data in data.get("rectangles", []):
            try:
                rect_item = RectangleItem.from_dict(rect_data)
                self._scene.addItem(rect_item)
                if hasattr(rect_item, "item_uuid"):
                    imported_uuids.append(rect_item.item_uuid)
            except (KeyError, ValueError, TypeError) as e:
                self._log_service.error(f"Error importing rectangle: {e}", "Import")

        # Get groups from the file and track which items are grouped
        file_groups = data.get("groups", [])
        grouped_uuids: set[str] = set()
        for group_data in file_groups:
            grouped_uuids.update(group_data.get("item_uuids", []))

        return imported_uuids, file_groups, grouped_uuids
