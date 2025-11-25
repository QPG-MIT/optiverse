"""
Scene file management for save, load, and autosave operations.

This module extracts file management logic from MainWindow to improve
code organization and reduce the MainWindow's size.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import tempfile
from typing import TYPE_CHECKING, Callable

from PyQt6 import QtWidgets

from ..core.exceptions import AssemblyLoadError, AssemblySaveError
from ..core.protocols import Serializable

if TYPE_CHECKING:
    from .log_service import LogService


class SceneFileManager:
    """
    Manages scene file operations including save, load, and autosave.

    This class encapsulates all file-related operations to keep MainWindow focused
    on UI coordination rather than file management details.
    """

    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        log_service: LogService,
        get_ray_data: Callable,
        on_modified: Callable[[bool], None],
        parent_widget: QtWidgets.QWidget,
        connect_item_signals: Callable | None = None,
    ):
        """
        Initialize the scene file manager.

        Args:
            scene: The graphics scene to save/load
            log_service: Logging service for errors and debug info
            get_ray_data: Callable to get current ray data (for path measures)
            on_modified: Callback when modified state changes
            parent_widget: Parent widget for dialogs
            connect_item_signals: Optional callback to connect signals for items
        """
        self.scene = scene
        self.log_service = log_service
        self._get_ray_data = get_ray_data
        self._on_modified = on_modified
        self.parent_widget = parent_widget
        self._connect_item_signals = connect_item_signals

        # File state
        self._saved_file_path: str | None = None
        self._autosave_path: str | None = None
        self._unsaved_id: str | None = None
        self._is_modified = False

    @property
    def saved_file_path(self) -> str | None:
        """Get the current saved file path."""
        return self._saved_file_path

    @saved_file_path.setter
    def saved_file_path(self, value: str | None):
        """Set the saved file path."""
        self._saved_file_path = value

    @property
    def is_modified(self) -> bool:
        """Check if the scene has unsaved modifications."""
        return self._is_modified

    def mark_modified(self):
        """Mark the scene as having unsaved changes."""
        if not self._is_modified:
            self._is_modified = True
            self._on_modified(True)

    def mark_clean(self):
        """Mark the scene as saved (no unsaved changes)."""
        if self._is_modified:
            self._is_modified = False
        self._on_modified(False)

    def get_autosave_path(self) -> str:
        """Get autosave path in AppData (safe from permission/sync issues)."""
        from ..platform.paths import _app_data_root

        autosave_dir = _app_data_root() / "autosave"
        autosave_dir.mkdir(parents=True, exist_ok=True)

        if self._saved_file_path:
            # Hash the absolute path to create unique filename
            path_hash = hashlib.md5(self._saved_file_path.encode()).hexdigest()[:12]
            base_name = os.path.splitext(os.path.basename(self._saved_file_path))[0]
            filename = f"{base_name}_{path_hash}.autosave.json"
        else:
            # For unsaved files: use timestamp + sequential ID
            if not self._unsaved_id:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                self._unsaved_id = f"untitled_{timestamp}"
            filename = f"{self._unsaved_id}.autosave.json"

        return str(autosave_dir / filename)

    def serialize_scene(self) -> dict:
        """Serialize scene to dictionary format."""
        from optiverse.objects.annotations.path_measure_item import PathMeasureItem

        from ..objects import BaseObj, RectangleItem
        from ..objects.annotations import RulerItem, TextNoteItem

        data = {
            "version": "2.0",
            "items": [],
            "rulers": [],
            "texts": [],
            "rectangles": [],
            "path_measures": [],
        }

        for it in self.scene.items():
            if isinstance(it, BaseObj) and isinstance(it, Serializable):
                data["items"].append(it.to_dict())
            elif isinstance(it, RulerItem):
                data["rulers"].append(it.to_dict())
            elif isinstance(it, TextNoteItem):
                data["texts"].append(it.to_dict())
            elif isinstance(it, RectangleItem):
                data["rectangles"].append(it.to_dict())
            elif isinstance(it, PathMeasureItem):
                data["path_measures"].append(it.to_dict())

        return data

    def do_autosave(self):
        """Perform autosave to temporary file."""
        if not self._is_modified:
            return

        try:
            autosave_path = self.get_autosave_path()

            # Serialize scene
            data = self.serialize_scene()

            # Add metadata for recovery UI
            data["_autosave_meta"] = {
                "timestamp": datetime.datetime.now().isoformat(),
                "original_path": self._saved_file_path,
                "version": "2.0",
            }

            # Atomic write: temp file + rename
            autosave_dir = os.path.dirname(autosave_path)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=autosave_dir, delete=False, suffix=".tmp"
            ) as tmp:
                json.dump(data, tmp, indent=2)
                tmp_path = tmp.name

            # Atomic rename (overwrites existing autosave)
            os.replace(tmp_path, autosave_path)
            self._autosave_path = autosave_path

            self.log_service.debug(f"Autosaved to {autosave_path}", "Autosave")

        except (OSError, TypeError) as e:
            # OSError for file operations, TypeError for JSON serialization issues
            self.log_service.error(f"Autosave failed: {e}", "Autosave")

    def clear_autosave(self):
        """Delete autosave file."""
        try:
            if self._autosave_path and os.path.exists(self._autosave_path):
                os.unlink(self._autosave_path)
                self._autosave_path = None
                self.log_service.debug("Cleared autosave file", "Autosave")
        except OSError as e:
            self.log_service.error(f"Failed to clear autosave: {e}", "Autosave")

    def load_from_data(self, data: dict):
        """Load scene from data dict."""
        from optiverse.objects.annotations.path_measure_item import PathMeasureItem

        from ..objects import BaseObj, RectangleItem
        from ..objects.annotations import RulerItem, TextNoteItem
        from ..objects.type_registry import deserialize_item

        # Clear scene
        for it in list(self.scene.items()):
            if isinstance(it, (BaseObj, RulerItem, TextNoteItem, RectangleItem)):
                self.scene.removeItem(it)

        # Load items
        for item_data in data.get("items", []):
            try:
                item = deserialize_item(item_data)
                self.scene.addItem(item)
            except (KeyError, ValueError, TypeError) as e:
                # KeyError: missing required fields, ValueError/TypeError: invalid data
                self.log_service.error(f"Error loading item: {e}", "Load")

        # Load annotations
        for ruler_data in data.get("rulers", []):
            ruler = RulerItem.from_dict(ruler_data)
            if self._connect_item_signals:
                self._connect_item_signals(ruler)
            self.scene.addItem(ruler)

        for text_data in data.get("texts", []):
            self.scene.addItem(TextNoteItem.from_dict(text_data))

        for rect_data in data.get("rectangles", []):
            self.scene.addItem(RectangleItem.from_dict(rect_data))

        # Load path measures
        ray_data = self._get_ray_data()
        for pm_data in data.get("path_measures", []):
            try:
                item = PathMeasureItem.from_dict(pm_data, ray_data)
                self.scene.addItem(item)
            except (KeyError, ValueError, TypeError) as e:
                # KeyError: missing required fields, ValueError/TypeError: invalid data
                self.log_service.error(f"Error loading path measure: {e}", "Load")

    def _format_time_ago(self, delta: datetime.timedelta) -> str:
        """Format timedelta as human-readable string."""
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        else:
            return f"{seconds // 86400}d ago"

    def check_autosave_recovery(self) -> bool:
        """
        Check for autosave on startup and offer recovery.

        Returns:
            True if recovery was performed, False otherwise
        """
        from ..platform.paths import _app_data_root

        autosave_dir = _app_data_root() / "autosave"
        if not autosave_dir.exists():
            return False

        autosave_files = sorted(
            autosave_dir.glob("*.autosave.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        if not autosave_files:
            return False

        most_recent = autosave_files[0]

        try:
            with open(most_recent, encoding="utf-8") as f:
                data = json.load(f)

            if data.get("version") != "2.0":
                raise ValueError("Incompatible autosave version")

            meta = data.get("_autosave_meta", {})
            timestamp_str = meta.get("timestamp", "")
            original_path = meta.get("original_path")

            try:
                timestamp = datetime.datetime.fromisoformat(timestamp_str)
                age = datetime.datetime.now() - timestamp
                time_str = self._format_time_ago(age)
            except (ValueError, OSError):
                time_str = "unknown time"

            if original_path:
                file_name = os.path.basename(original_path)
                msg = f"Found autosave of '{file_name}'\nSaved: {time_str}"
            else:
                msg = f"Found autosave of unsaved file\nSaved: {time_str}"

            reply = QtWidgets.QMessageBox.question(
                self.parent_widget,
                "Recover Autosave?",
                f"{msg}\n\nWould you like to recover it?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.Yes,
            )

            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.load_from_data(data)
                self._saved_file_path = original_path
                self._autosave_path = str(most_recent)
                self.mark_modified()

                QtWidgets.QMessageBox.information(
                    self.parent_widget,
                    "Recovery Successful",
                    "Autosave recovered. Please save your work.",
                )
                return True
            else:
                most_recent.unlink()

        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            # OSError: file access, JSONDecodeError: corrupt file
            # KeyError/ValueError: invalid data structure
            self.log_service.error(f"Failed to recover autosave: {e}", "Recovery")

        return False

    def save_to_file(self, path: str) -> bool:
        """
        Save scene to specified file path.

        Returns:
            True if save was successful

        Raises:
            AssemblySaveError: If the file cannot be saved
        """
        data = self.serialize_scene()

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self._saved_file_path = path
            self.mark_clean()
            self.clear_autosave()
            return True

        except (OSError, json.JSONDecodeError) as e:
            raise AssemblySaveError(path, str(e)) from e

    def open_file(self, path: str) -> bool:
        """
        Open and load a scene file.

        Returns:
            True if open was successful

        Raises:
            AssemblyLoadError: If the file cannot be opened or parsed
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise AssemblyLoadError(path, str(e)) from e

        self.load_from_data(data)
        self._saved_file_path = path
        self._unsaved_id = None
        self.mark_clean()
        return True

    def prompt_save_changes(self) -> QtWidgets.QMessageBox.StandardButton:
        """
        Prompt user to save unsaved changes.

        Returns:
            The user's choice (Save, Discard, or Cancel)
        """
        return QtWidgets.QMessageBox.question(
            self.parent_widget,
            "Unsaved Changes",
            "Do you want to save your changes before closing?",
            QtWidgets.QMessageBox.StandardButton.Save
            | QtWidgets.QMessageBox.StandardButton.Discard
            | QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Save,
        )
