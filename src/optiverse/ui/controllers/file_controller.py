"""
File controller for handling save/load/autosave operations.

Extracts file management UI logic from MainWindow.
Supports importing assemblies as grouped layers.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.constants import AUTOSAVE_DEBOUNCE_MS
from ...services.error_handler import ErrorContext
from ...services.scene_file_manager import SceneFileManager

if TYPE_CHECKING:
    from ...core.layer_tree_state import LayerTreeState
    from ...core.undo_stack import UndoStack
    from ...services.library_service import LibraryService
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
        layer_state: LayerTreeState | None = None,
        settings_service: SettingsService | None = None,
        library_service: LibraryService | None = None,
    ):
        super().__init__(parent_widget)

        self._parent = parent_widget
        self._undo_stack = undo_stack
        self._is_modified = False
        self._layer_state = layer_state
        self._log_service = log_service
        self._scene = scene
        self._connect_item_signals = connect_item_signals
        self._settings_service = settings_service
        self._library_service = library_service

        # Create file manager
        self.file_manager = SceneFileManager(
            scene=scene,
            log_service=log_service,
            get_ray_data=get_ray_data,
            on_modified=self._on_modified_changed,
            parent_widget=parent_widget,
            connect_item_signals=connect_item_signals,
            get_library_roots=(
                library_service.get_all_roots if library_service else None
            ),
        )

        # Forward layer_state to file manager for saving/loading layer_state
        if layer_state:
            self.file_manager.set_layer_state(layer_state)

        # Autosave timer
        self._autosave_timer = QtCore.QTimer()
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DEBOUNCE_MS)
        self._autosave_timer.timeout.connect(self._do_autosave)

        self._linked_assembly_service = None

        # Connect undo stack to modification tracking
        self._undo_stack.commandPushed.connect(self._on_command_pushed)

    def set_autosave_interval(self, interval_ms: int) -> None:
        """Update the autosave debounce interval and ensure the timer is running."""
        self._autosave_timer.setInterval(max(100, interval_ms))

    def disable_autosave(self) -> None:
        """Stop the autosave timer entirely."""
        self._autosave_timer.stop()

    def set_layer_state(self, layer_state: LayerTreeState) -> None:
        """Set the layer state for save/load/import-as-layer functionality."""
        self._layer_state = layer_state
        self.file_manager.set_layer_state(layer_state)

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
        from ...core import preferences

        if not preferences.autosave_enabled:
            return
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
            default_dir = (
                str(Path(self.saved_file_path).parent)
                if self.saved_file_path
                else ""
            )
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self._parent,
                "Save Assembly As",
                default_dir,
                "Optics Assembly (*.json)",
            )
            if path:
                if not path.lower().endswith(".json"):
                    path += ".json"
                self.file_manager.save_to_file(path)
                self._add_recent_file(path)

    def export_selected_as_assembly(self) -> None:
        """Export the currently selected scene items as a new assembly file."""
        uuids = {
            str(it.item_uuid)
            for it in self._scene.selectedItems()
            if hasattr(it, "item_uuid")
        }
        if not uuids:
            QtWidgets.QMessageBox.information(
                self._parent,
                "Export Selected",
                "No items are selected. Select one or more items first.",
            )
            return

        with ErrorContext("while exporting selected items", suppress=True):
            default_dir = (
                str(Path(self.saved_file_path).parent)
                if self.saved_file_path
                else ""
            )
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self._parent,
                "Export Selected as Assembly",
                default_dir,
                "Optics Assembly (*.json)",
            )
            if path:
                if not path.lower().endswith(".json"):
                    path += ".json"
                data = self.file_manager.serialize_selected(uuids)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

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

            # Clear the scene and linked assembly state
            self._clear_scene()
            if self._linked_assembly_service:
                self._linked_assembly_service.reset()
            from ...platform.paths import set_current_assembly_dir
            set_current_assembly_dir(None)

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
        # Clear layer state first
        if self._layer_state:
            self._layer_state.clear()

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

    _MM_TO_POINTS = 72.0 / 25.4  # Conversion factor: mm to points (1 pt = 1/72 inch)

    @staticmethod
    def _export_margin_mm() -> int:
        from ...core import preferences
        return preferences.export_margin_mm

    @staticmethod
    def _default_png_scale() -> float:
        from ...core import preferences
        return preferences.default_png_scale

    @staticmethod
    def _default_pdf_dpi() -> int:
        from ...core import preferences
        return preferences.default_pdf_dpi

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
        margin = self._export_margin_mm()
        rect.adjust(-margin, -margin, margin, margin)
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
                value=self._default_png_scale(),
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
                value=self._default_pdf_dpi(),
                min=72,
                max=1200,
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

    def export_pyopticl(self) -> bool:
        """Export the scene to a PyOpticL v2 layout folder.

        Shows dialogs for missing STEP warnings and baseplate configuration,
        then writes a folder containing the script plus a ``models/`` tree
        with one ``.step`` and ``.json`` per referenced component, matching
        the layout PyOpticL's ``import_model`` expects.

        Returns:
            True if export was successful
        """
        from ...export.pyopticl_dialogs import BaseplateOptionsDialog, MissingStepWarningDialog
        from ...export.pyopticl_exporter import (
            BaseplateOptions,
            _sanitize_stem,
            analyse_scene,
            export_scene,
        )

        with ErrorContext("while exporting PyOpticL layout", suppress=True):
            from ...platform.paths import to_absolute_path

            scene_data = self.file_manager.serialize_scene()

            all_items = scene_data.get("items", [])
            step_before = [
                (d.get("name", "?"), d.get("step_file_path", ""))
                for d in all_items if d.get("step_file_path")
            ]
            self._log_service.info(
                f"PyOpticL export: {len(all_items)} items, "
                f"{len(step_before)} with step_file_path before resolution",
                "Export",
            )
            for name, sfp in step_before:
                self._log_service.info(
                    f"  STEP (raw): {name!r} -> {sfp!r}", "Export"
                )

            # Resolve portable step_file_path values (@component/...,
            # @library/..., relative) back to absolute paths so the
            # exporter can find the actual STEP files on disk.
            roots = (
                self._library_service.get_all_roots()
                if self._library_service
                else None
            )
            self._log_service.info(
                f"  Library roots for resolution: {roots}", "Export"
            )
            for item_data in all_items:
                sfp = item_data.get("step_file_path")
                if sfp:
                    resolved = to_absolute_path(sfp, roots) or ""
                    # If the resolved path does not exist on disk, try to
                    # find the file by scanning library component folders
                    # (handles bare relative paths like "step/KS05.step").
                    if resolved and not os.path.isfile(resolved) and roots:
                        basename = os.path.basename(sfp)
                        for lib_root in roots:
                            for candidate in lib_root.rglob(basename):
                                if candidate.is_file():
                                    resolved = str(candidate)
                                    break
                            if os.path.isfile(resolved):
                                break
                    self._log_service.info(
                        f"  STEP resolve: {sfp!r} -> {resolved!r} "
                        f"(exists={os.path.isfile(resolved)})",
                        "Export",
                    )
                    item_data["step_file_path"] = resolved

            items, warnings = analyse_scene(scene_data)

            if warnings:
                dlg = MissingStepWarningDialog(warnings, parent=self._parent)
                if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                    return False

            opts_dlg = BaseplateOptionsDialog(BaseplateOptions(), parent=self._parent)
            if opts_dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return False
            options = opts_dlg.get_options()

            default_name = _sanitize_stem(options.label) or "pyopticl_export"
            export_dir, _ = QtWidgets.QFileDialog.getSaveFileName(
                self._parent,
                "Save PyOpticL Layout Folder As",
                default_name,
                "PyOpticL Layout Folder (*)",
            )
            if not export_dir:
                return False
            if export_dir.endswith(".py"):
                export_dir = export_dir[:-3]

            success, skipped = export_scene(scene_data, export_dir, options)
            if success:
                self._show_export_success(export_dir, "PyOpticL Layout")
            return success

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

            if self._layer_state:
                # Add items to scene first
                for item in imported_items:
                    if item.scene() is None:
                        self._scene.addItem(item)

                # Connect signals for imported items
                if self._connect_item_signals:
                    for item in imported_items:
                        self._connect_item_signals(item)

                # Determine legacy ordering input from imported items' z
                items_with_z: list[tuple[float, str]] = []
                for item in imported_items:
                    if hasattr(item, "item_uuid"):
                        items_with_z.append((float(item.zValue()), str(item.item_uuid)))

                # Build imported layer state from file
                # (new layer_state preferred, else legacy groups)
                from ...core.layer_tree_state import LayerTreeState

                if "layer_state" in data:
                    imported_state = LayerTreeState.from_dict(data.get("layer_state", {}))
                else:
                    imported_state = LayerTreeState.from_legacy(file_groups, items_with_z)

                # Create parent group in current state
                parent_uuid = self._layer_state.create_group(
                    group_name, parent_group_uuid=None, index=0, emit=False
                )

                # Attach imported roots under parent group
                for root in imported_state.get_root_nodes():
                    if root.is_group():
                        # recreate group with same uuid under parent
                        # (preserve UUIDs from imported file)
                        self._layer_state.create_group(
                            root.name or "Group",
                            parent_group_uuid=parent_uuid,
                            index=10**9,
                            group_uuid=root.uuid,
                            emit=False,
                        )
                        self._layer_state.set_group_collapsed(root.uuid, root.collapsed, emit=False)
                        # attach children recursively by serializing subtree and merging
                        from ...core.layer_tree_state import LayerNode

                        def add_children(dst_parent_uuid: str, node: LayerNode) -> None:
                            if not self._layer_state:
                                return
                            for ch in node.children:
                                if ch.is_group():
                                    self._layer_state.create_group(
                                        ch.name or "Group",
                                        parent_group_uuid=dst_parent_uuid,
                                        index=10**9,
                                        group_uuid=ch.uuid,
                                        emit=False,
                                    )
                                    self._layer_state.set_group_collapsed(
                                        ch.uuid, ch.collapsed, emit=False
                                    )
                                    add_children(ch.uuid, ch)
                                else:
                                    self._layer_state.add_item(
                                        ch.uuid, dst_parent_uuid, index=10**9, emit=False
                                    )
                        add_children(root.uuid, root)
                    else:
                        self._layer_state.add_item(root.uuid, parent_uuid, index=10**9, emit=False)

                # Any imported items not referenced in groups: add under parent
                imported_uuids = {uuid for _, uuid in items_with_z}
                referenced = set(imported_state.get_all_items_in_order())
                for uuid in imported_uuids - referenced:
                    self._layer_state.add_item(uuid, parent_uuid, index=10**9, emit=False)

                self._layer_state.changed.emit()

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
        roots = self._library_service.get_all_roots() if self._library_service else None

        # Create optical items
        for item_data in data.get("items", []):
            try:
                item = deserialize_item(item_data, library_roots=roots)
                if item is None:
                    self._log_service.warning(
                        f"Skipped unknown item type: {item_data.get('_type')}", "Import",
                    )
                    continue
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
        roots = self._library_service.get_all_roots() if self._library_service else None

        # Import optical items
        for item_data in data.get("items", []):
            try:
                item = deserialize_item(item_data, library_roots=roots)
                if item is None:
                    self._log_service.warning(
                        f"Skipped unknown item type: {item_data.get('_type')}", "Import",
                    )
                    continue
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

        # Reconnect autolabel signals for any imported ComponentItems
        from ...objects.generic.component_item import ComponentItem

        for it in self._scene.items():
            if isinstance(it, ComponentItem) and it.item_uuid in imported_uuids:
                it.connect_autolabel()

        # Get groups from the file and track which items are grouped
        file_groups = data.get("groups", [])
        grouped_uuids: set[str] = set()
        for group_data in file_groups:
            grouped_uuids.update(group_data.get("item_uuids", []))

        return imported_uuids, file_groups, grouped_uuids

    # ------------------------------------------------------------------
    # Linked Assembly operations
    # ------------------------------------------------------------------

    def set_linked_assembly_service(self, service) -> None:
        """Set the linked assembly service for link operations."""
        self._linked_assembly_service = service
        self.file_manager.set_linked_assembly_service(service)

    def link_assembly(self) -> bool:
        """Link an external assembly file (reference, not copy).

        Returns True if a link was created successfully.
        """
        from ...core.layer_tree_state import LinkMetadata

        if not self._linked_assembly_service:
            self._log_service.error("Linked assembly service not available", "Link")
            return False

        with ErrorContext("while linking assembly", suppress=True):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self._parent, "Link Assembly…", "", "Optics Assembly (*.json)",
            )
            if not path:
                return False

            if self.saved_file_path and os.path.abspath(path) == os.path.abspath(
                self.saved_file_path
            ):
                QtWidgets.QMessageBox.warning(
                    self._parent,
                    "Cannot Link",
                    "Cannot link an assembly to itself.",
                )
                return False

            try:
                assembly_dir = (
                    Path(self.saved_file_path).parent
                    if self.saved_file_path
                    else None
                )

                link_uuid = self._linked_assembly_service.add_link(
                    source_path=path,
                    assembly_dir=assembly_dir,
                )

                group_name = os.path.splitext(os.path.basename(path))[0]

                meta = LinkMetadata(source_path=path)

                if self._layer_state:
                    self._layer_state.create_linked_group(
                        name=group_name,
                        link_metadata=meta,
                        parent_group_uuid=None,
                        index=0,
                        group_uuid=link_uuid,
                        emit=False,
                    )

                items = self._linked_assembly_service.load_link_items(
                    link_uuid, self._connect_item_signals,
                )

                self.mark_modified()
                self.traceRequested.emit()

                self._log_service.info(
                    f"Linked {len(items)} items from '{os.path.basename(path)}'",
                    "Link",
                )
                return True

            except Exception as e:
                self._log_service.error(f"Failed to link assembly: {e}", "Link")
                QtWidgets.QMessageBox.warning(
                    self._parent,
                    "Link Failed",
                    f"Could not link assembly:\n{e}",
                )
                return False

    def refresh_linked_assembly(self, link_uuid: str) -> None:
        """Reload a linked assembly from its source file."""
        if not self._linked_assembly_service:
            return
        self._linked_assembly_service.reload_link(link_uuid, self._connect_item_signals)
        self.mark_modified()
        self.traceRequested.emit()

    def edit_linked_in_context(self, link_uuid: str) -> None:
        """Enter edit-in-context mode for a linked assembly."""
        if not self._linked_assembly_service:
            return
        self._linked_assembly_service.begin_edit_in_context(link_uuid)
        if self._layer_state:
            self._layer_state.changed.emit()

    def finish_edit_in_context(self, link_uuid: str) -> None:
        """Finish editing a linked assembly and write back to source."""
        if not self._linked_assembly_service:
            return
        success = self._linked_assembly_service.end_edit_in_context(link_uuid, save=True)
        if success:
            abs_path = self._linked_assembly_service.get_source_path(link_uuid)
            if abs_path:
                self._linked_assembly_service.reload_all_for_source(
                    abs_path, self._connect_item_signals,
                )
            self.mark_modified()
        self.traceRequested.emit()
        if self._layer_state:
            self._layer_state.changed.emit()

    def unlink_embed(self, link_uuid: str) -> None:
        """Convert a linked assembly into a regular (embedded) group."""
        if not self._linked_assembly_service:
            return
        self._linked_assembly_service.unlink_embed(link_uuid)
        self.mark_modified()
        if self._layer_state:
            self._layer_state.changed.emit()
        self.traceRequested.emit()
