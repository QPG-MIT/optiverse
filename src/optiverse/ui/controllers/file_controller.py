"""
File controller for handling save/load/autosave operations.

Extracts file management UI logic from MainWindow.
Supports importing assemblies as grouped layers.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.constants import AUTOSAVE_DEBOUNCE_MS
from ...services.error_handler import ErrorContext
from ...services.scene_file_manager import SceneFileManager

if TYPE_CHECKING:
    from ...core.layer_group import GroupManager
    from ...core.undo_stack import UndoStack
    from ...services.log_service import LogService
    from ...services.settings_service import SettingsService


class FileController(QtCore.QObject):
    """
    Controller for file operations (save, open, autosave).

    Wraps SceneFileManager and provides UI interactions.
    """

    # Signal emitted when file operations complete and trace should be updated
    traceRequested = QtCore.pyqtSignal()
    # Signal emitted when window title should be updated
    windowTitleChanged = QtCore.pyqtSignal(str)
    # Signal emitted when recent files list changes
    recentFilesChanged = QtCore.pyqtSignal()

    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        undo_stack: UndoStack,
        log_service: LogService,
        get_ray_data: Callable,
        parent_widget: QtWidgets.QWidget,
        connect_item_signals: Callable | None = None,
        group_manager: GroupManager | None = None,
        settings_service: SettingsService | None = None,
    ):
        super().__init__(parent_widget)

        self._parent = parent_widget
        self._undo_stack = undo_stack
        self._is_modified = False
        self._group_manager = group_manager
        self._log_service = log_service
        self._scene = scene
        self._connect_item_signals = connect_item_signals
        self._settings_service = settings_service

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
                self._add_recent_file(self.saved_file_path)
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
                self._add_recent_file(path)

    def new_assembly(self) -> bool:
        """
        Create a new empty assembly.

        Prompts to save if there are unsaved changes.

        Returns:
            True if new assembly was created, False if cancelled
        """
        with ErrorContext("while creating new assembly", suppress=True):
            if self._is_modified:
                reply = self.prompt_save_changes()
                if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return False

            # Clear the scene
            self._clear_scene()

            # Reset file path
            self.file_manager.saved_file_path = None

            # Clear undo stack
            self._undo_stack.clear()

            # Mark as clean (new file)
            self.mark_clean()

            # Update title
            self._update_window_title()

            # Request retrace (clears rays)
            self.traceRequested.emit()

            return True
        return False

    def close_assembly(self) -> bool:
        """
        Close the current assembly.

        Prompts to save if there are unsaved changes.
        Resets to an untitled state.

        Returns:
            True if assembly was closed, False if cancelled
        """
        return self.new_assembly()

    def _clear_scene(self) -> None:
        """Clear all items from the scene."""
        # Clear groups first
        if self._group_manager:
            self._group_manager.clear()

        # Remove all items from scene
        for item in list(self._scene.items()):
            self._scene.removeItem(item)

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

            # Add to recent files
            self._add_recent_file(path)

        # Clear undo history after loading
        self._undo_stack.clear()
        self.traceRequested.emit()
        return True

    def open_recent_file(self, path: str) -> bool:
        """
        Open a file from the recent files list.

        Args:
            path: File path to open

        Returns:
            True if file was opened successfully
        """
        with ErrorContext("while opening recent file", suppress=True):
            if not Path(path).exists():
                QtWidgets.QMessageBox.warning(
                    self._parent,
                    "File Not Found",
                    f"The file no longer exists:\n{path}",
                )
                # Remove from recent files
                if self._settings_service:
                    files = self._settings_service.get_recent_files()
                    files = [f for f in files if f != path]
                    self._settings_service.set_value("recent_files", files)
                    self.recentFilesChanged.emit()
                return False

            if self._is_modified:
                reply = self.prompt_save_changes()
                if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return False

            if not self.file_manager.open_file(path):
                return False

            # Add to recent files (moves to front)
            self._add_recent_file(path)

        # Clear undo history after loading
        self._undo_stack.clear()
        self.traceRequested.emit()
        return True

    def _add_recent_file(self, path: str) -> None:
        """Add a file to the recent files list."""
        if self._settings_service:
            self._settings_service.add_recent_file(path)
            self.recentFilesChanged.emit()

    def get_recent_files(self) -> list[str]:
        """Get list of recent files."""
        if self._settings_service:
            return self._settings_service.get_recent_files()
        return []

    # --- Export Methods ---

    # Export constants
    _EXPORT_MARGIN_MM = 20  # Margin around exported content in mm
    _DEFAULT_PNG_SCALE = 4.0  # Default scale factor for PNG (4x = 288 DPI)
    _DEFAULT_PDF_DPI = 300  # Default DPI for PDF export
    _MM_TO_POINTS = 72.0 / 25.4  # Conversion factor: mm to points (1 pt = 1/72 inch)

    def _get_export_rect(self) -> QtCore.QRectF | None:
        """
        Get the scene bounding rect for export with margin.

        Returns:
            QRectF with margin added, or None if scene is empty
        """
        rect = self._scene.itemsBoundingRect()
        if rect.isEmpty():
            QtWidgets.QMessageBox.information(
                self._parent,
                "Export",
                "Nothing to export - the scene is empty.",
            )
            return None
        rect.adjust(
            -self._EXPORT_MARGIN_MM,
            -self._EXPORT_MARGIN_MM,
            self._EXPORT_MARGIN_MM,
            self._EXPORT_MARGIN_MM,
        )
        return rect

    def _show_export_success(self, path: str, format_name: str) -> None:
        """Show export success message and log."""
        self._log_service.info(f"Exported {format_name} to: {path}", "Export")
        QtWidgets.QMessageBox.information(
            self._parent,
            "Export Successful",
            f"{format_name} exported to:\n{path}",
        )

    def _show_export_failure(self, path: str) -> None:
        """Show export failure message."""
        QtWidgets.QMessageBox.critical(
            self._parent,
            "Export Failed",
            f"Failed to save file to:\n{path}",
        )

    def export_image(self) -> bool:
        """
        Export the scene to an image file (PNG or SVG).

        Shows a dialog for format selection and save location.

        Returns:
            True if export was successful
        """
        with ErrorContext("while exporting image", suppress=True):
            # Get save path with filter for supported formats
            path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
                self._parent,
                "Export Image",
                "",
                "PNG Image (*.png);;SVG Image (*.svg)",
            )
            if not path:
                return False

            # Ensure correct extension and delegate to appropriate method
            if "svg" in selected_filter.lower():
                if not path.lower().endswith(".svg"):
                    path += ".svg"
                return self._export_svg(path)
            else:
                if not path.lower().endswith(".png"):
                    path += ".png"
                return self._export_png(path)

        return False

    def _export_png(self, path: str) -> bool:
        """Export scene to PNG file."""
        with ErrorContext("while exporting PNG", suppress=True):
            # Get export rect (checks for empty scene)
            rect = self._get_export_rect()
            if rect is None:
                return False

            # Ask user for scale factor
            scale, ok = QtWidgets.QInputDialog.getDouble(
                self._parent,
                "Export Resolution",
                "Scale factor (1x = 72 DPI, 4x = 288 DPI):",
                value=self._DEFAULT_PNG_SCALE,
                min=1.0,
                max=10.0,
                decimals=1,
            )
            if not ok:
                return False

            # Create image at selected resolution
            width = int(rect.width() * scale)
            height = int(rect.height() * scale)

            image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
            image.fill(QtCore.Qt.GlobalColor.white)

            # Render scene to image
            painter = QtGui.QPainter(image)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            target_rect = QtCore.QRectF(0, 0, width, height)
            self._scene.render(painter, target_rect, rect)
            painter.end()

            # Flip image vertically to correct for Y-up scene coordinates
            image = image.mirrored(False, True)

            # Save image
            if image.save(path):
                self._show_export_success(path, "Image")
                return True
            else:
                self._show_export_failure(path)
                return False

        return False

    def _export_svg(self, path: str) -> bool:
        """Export scene to SVG file."""
        from PyQt6 import QtSvg

        with ErrorContext("while exporting SVG", suppress=True):
            # Get export rect (checks for empty scene)
            rect = self._get_export_rect()
            if rect is None:
                return False

            width = int(rect.width())
            height = int(rect.height())

            # Create SVG generator
            generator = QtSvg.QSvgGenerator()
            generator.setFileName(path)
            generator.setSize(QtCore.QSize(width, height))
            generator.setViewBox(QtCore.QRect(0, 0, width, height))
            generator.setTitle("Optiverse Export")

            # Render scene to SVG with Y-flip transform for correct orientation
            painter = QtGui.QPainter(generator)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            # Apply Y-flip: translate to bottom, then flip
            painter.translate(0, height)
            painter.scale(1, -1)
            target_rect = QtCore.QRectF(0, 0, width, height)
            self._scene.render(painter, target_rect, rect)
            painter.end()

            # Verify file was created
            if Path(path).exists():
                self._show_export_success(path, "SVG")
                return True
            else:
                self._show_export_failure(path)
                return False

        return False

    def export_pdf(self) -> bool:
        """
        Export the scene to a PDF file.

        Shows a dialog for save location.

        Returns:
            True if export was successful
        """
        with ErrorContext("while exporting PDF", suppress=True):
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self._parent,
                "Export PDF",
                "",
                "PDF Document (*.pdf)",
            )
            if not path:
                return False

            # Ensure correct extension
            if not path.lower().endswith(".pdf"):
                path += ".pdf"

            # Get export rect (checks for empty scene)
            rect = self._get_export_rect()
            if rect is None:
                return False

            # Ask user for DPI
            dpi, ok = QtWidgets.QInputDialog.getInt(
                self._parent,
                "Export Resolution",
                "PDF resolution (DPI):",
                value=self._DEFAULT_PDF_DPI,
                min=72,
                max=600,
                step=50,
            )
            if not ok:
                return False

            # Create PDF writer
            from PyQt6.QtGui import QPageSize, QPdfWriter

            writer = QPdfWriter(path)
            writer.setResolution(dpi)

            # Set page size (convert mm to points)
            width_pt = rect.width() * self._MM_TO_POINTS
            height_pt = rect.height() * self._MM_TO_POINTS

            page_size = QPageSize(
                QtCore.QSizeF(width_pt, height_pt),
                QPageSize.Unit.Point,
            )
            writer.setPageSize(page_size)
            writer.setPageMargins(QtCore.QMarginsF(0, 0, 0, 0))

            # Calculate target size in device pixels
            width_px = int(rect.width() * dpi / 25.4)
            height_px = int(rect.height() * dpi / 25.4)

            # Render scene to PDF with Y-flip transform
            painter = QtGui.QPainter(writer)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.translate(0, height_px)
            painter.scale(1, -1)
            target_rect = QtCore.QRectF(0, 0, width_px, height_px)
            self._scene.render(painter, target_rect, rect)
            painter.end()

            # Verify file was created
            if Path(path).exists():
                self._show_export_success(path, "PDF")
                return True
            else:
                self._show_export_failure(path)
                return False

        return False

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

            # Import items without clearing scene (but don't add to scene yet)
            imported_items, file_groups, grouped_uuids = self._import_items_for_layer(
                data
            )

            if not imported_items:
                QtWidgets.QMessageBox.information(
                    self._parent,
                    "Import Complete",
                    "No items were imported from the file.",
                )
                return False

            # Use filename (without extension) as parent group name
            group_name = os.path.splitext(os.path.basename(path))[0]

            if self._group_manager:
                from ...core.layer_group import LayerGroup
                from ...core.undo_commands import ImportAsLayerCommand

                # Get UUIDs of imported items
                imported_uuids = [
                    item.item_uuid for item in imported_items
                    if hasattr(item, "item_uuid")
                ]

                # Find ungrouped items (items not in any group from the file)
                ungrouped_uuids = [
                    uuid for uuid in imported_uuids if uuid not in grouped_uuids
                ]

                # Create parent group data (but don't add yet)
                parent_group = LayerGroup(name=group_name, item_uuids=ungrouped_uuids)
                parent_group_data = parent_group.to_dict()

                # Prepare imported groups data with parent relationships
                imported_groups_data = []
                for group_data in file_groups:
                    # Set parent for root groups
                    if group_data.get("parent_group_uuid") is None:
                        group_data["parent_group_uuid"] = parent_group.group_uuid
                    imported_groups_data.append(group_data)

                # Create and execute the command (adds items and groups)
                cmd = ImportAsLayerCommand(
                    self._scene,
                    self._group_manager,
                    imported_items,
                    parent_group_data,
                    imported_groups_data,
                )
                self._undo_stack.push(cmd)

                # Connect signals for imported items
                if self._connect_item_signals:
                    for item in imported_items:
                        self._connect_item_signals(item)

            # Mark as modified and retrace
            self.mark_modified()
            self.traceRequested.emit()

            self._log_service.info(
                f"Imported {len(imported_items)} items as layer '{group_name}'",
                "Import",
            )

            return True

        return False

    def _import_items_for_layer(
        self, data: dict
    ) -> tuple[list[QtWidgets.QGraphicsItem], list[dict], set[str]]:
        """
        Create items from data dict without adding to scene.

        Args:
            data: Dictionary containing assembly data

        Returns:
            Tuple of:
            - List of created items (not yet in scene)
            - List of group dicts from the file (for hierarchy preservation)
            - Set of item UUIDs that were in groups in the file
        """
        from ...objects import RectangleItem
        from ...objects.annotations import RulerItem, TextNoteItem
        from ...objects.type_registry import deserialize_item

        imported_items: list[QtWidgets.QGraphicsItem] = []

        # Create optical items
        for item_data in data.get("items", []):
            try:
                item = deserialize_item(item_data)
                imported_items.append(item)
            except (KeyError, ValueError, TypeError) as e:
                self._log_service.error(f"Error importing item: {e}", "Import")

        # Create rulers
        for ruler_data in data.get("rulers", []):
            try:
                ruler = RulerItem.from_dict(ruler_data)
                imported_items.append(ruler)
            except (KeyError, ValueError, TypeError) as e:
                self._log_service.error(f"Error importing ruler: {e}", "Import")

        # Create text notes
        for note_data in data.get("text_notes", []):
            try:
                note = TextNoteItem.from_dict(note_data)
                imported_items.append(note)
            except (KeyError, ValueError, TypeError) as e:
                self._log_service.error(f"Error importing text note: {e}", "Import")

        # Create rectangles
        for rect_data in data.get("rectangles", []):
            try:
                rect = RectangleItem.from_dict(rect_data)
                imported_items.append(rect)
            except (KeyError, ValueError, TypeError) as e:
                self._log_service.error(f"Error importing rectangle: {e}", "Import")

        # Get group info
        file_groups = data.get("groups", [])
        grouped_uuids: set[str] = set()
        for group_data in file_groups:
            grouped_uuids.update(group_data.get("item_uuids", []))

        return imported_items, file_groups, grouped_uuids

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
