"""Scene serialization and file I/O service."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from PyQt6 import QtWidgets

if TYPE_CHECKING:
    from ..services.log_service import LogService


class SceneSerializer:
    """
    Service for scene serialization, autosave, and file I/O.
    
    This class handles:
    - Serializing scene items to JSON
    - Loading scene data from JSON
    - Autosave functionality
    - File save/load operations
    """
    
    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        log_service: "LogService",
        get_ray_data: Callable[[], list] = None,
    ):
        """
        Initialize the scene serializer.
        
        Args:
            scene: The graphics scene to serialize/deserialize
            log_service: Logging service for debug/error messages
            get_ray_data: Callable to get current ray data (for PathMeasureItem)
        """
        self.scene = scene
        self.log_service = log_service
        self._get_ray_data = get_ray_data or (lambda: [])
        
        # State tracking
        self._saved_file_path: Optional[str] = None
        self._autosave_path: Optional[str] = None
        self._unsaved_id: Optional[str] = None
        self._is_modified: bool = False
    
    @property
    def saved_file_path(self) -> Optional[str]:
        """Get the current saved file path."""
        return self._saved_file_path
    
    @saved_file_path.setter
    def saved_file_path(self, value: Optional[str]):
        """Set the saved file path."""
        self._saved_file_path = value
    
    @property
    def is_modified(self) -> bool:
        """Check if scene has unsaved changes."""
        return self._is_modified
    
    @is_modified.setter
    def is_modified(self, value: bool):
        """Set the modified state."""
        self._is_modified = value
    
    @property
    def unsaved_id(self) -> Optional[str]:
        """Get the unsaved document ID."""
        return self._unsaved_id
    
    @unsaved_id.setter
    def unsaved_id(self, value: Optional[str]):
        """Set the unsaved document ID."""
        self._unsaved_id = value
    
    def serialize_scene(self) -> dict:
        """
        Serialize the scene to a dictionary.
        
        Returns:
            Dictionary containing all scene data in JSON-serializable format
        """
        from ..objects import RectangleItem, BaseObj, RulerItem, TextNoteItem
        from optiverse.objects.annotations.path_measure_item import PathMeasureItem
        
        data = {
            "version": "2.0",
            "items": [],
            "rulers": [],
            "texts": [],
            "rectangles": [],
            "path_measures": [],
        }
        
        for it in self.scene.items():
            if isinstance(it, BaseObj) and hasattr(it, 'type_name'):
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
    
    def load_from_data(self, data: dict) -> None:
        """
        Load scene from data dictionary.
        
        Args:
            data: Dictionary containing scene data (from JSON file or autosave)
        """
        from ..objects import RectangleItem, BaseObj, RulerItem, TextNoteItem
        from ..objects.type_registry import deserialize_item
        from optiverse.objects.annotations.path_measure_item import PathMeasureItem
        
        # Clear scene (only our item types, not grid lines etc.)
        for it in list(self.scene.items()):
            if isinstance(it, (BaseObj, RulerItem, TextNoteItem, RectangleItem)):
                self.scene.removeItem(it)
        
        # Load optical components
        for item_data in data.get("items", []):
            try:
                item = deserialize_item(item_data)
                self.scene.addItem(item)
            except Exception as e:
                self.log_service.error(f"Error loading item: {e}", "Load")
        
        # Load annotations
        for ruler_data in data.get("rulers", []):
            self.scene.addItem(RulerItem.from_dict(ruler_data))
        
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
            except Exception as e:
                self.log_service.error(f"Error loading path measure: {e}", "Load")
    
    def get_autosave_path(self) -> str:
        """
        Get autosave path in AppData (safe from permission/sync issues).
        
        Returns:
            Full path to the autosave file
        """
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
    
    def do_autosave(self) -> None:
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
                "version": "2.0"
            }
            
            # Atomic write: temp file + rename
            autosave_dir = os.path.dirname(autosave_path)
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=autosave_dir,
                delete=False,
                suffix='.tmp'
            ) as tmp:
                json.dump(data, tmp, indent=2)
                tmp_path = tmp.name
            
            # Atomic rename (overwrites existing autosave)
            os.replace(tmp_path, autosave_path)
            self._autosave_path = autosave_path
            
            self.log_service.debug(f"Autosaved to {autosave_path}", "Autosave")
            
        except Exception as e:
            self.log_service.error(f"Autosave failed: {e}", "Autosave")
            # Don't show error to user - autosave should be silent
    
    def clear_autosave(self) -> None:
        """Delete autosave file."""
        try:
            if self._autosave_path and os.path.exists(self._autosave_path):
                os.unlink(self._autosave_path)
                self._autosave_path = None
                self.log_service.debug("Cleared autosave file", "Autosave")
        except Exception as e:
            self.log_service.error(f"Failed to clear autosave: {e}", "Autosave")
    
    def save_to_file(self, path: str, parent_widget: QtWidgets.QWidget = None) -> bool:
        """
        Save scene to specified file path.
        
        Args:
            path: File path to save to
            parent_widget: Parent widget for error dialogs
            
        Returns:
            True if save was successful, False otherwise
        """
        data = self.serialize_scene()
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            self._saved_file_path = path
            self._is_modified = False
            
            # Clear autosave after successful save
            self.clear_autosave()
            
            return True
            
        except Exception as e:
            if parent_widget:
                QtWidgets.QMessageBox.critical(parent_widget, "Save error", str(e))
            return False
    
    def open_from_file(self, path: str, parent_widget: QtWidgets.QWidget = None) -> bool:
        """
        Load scene from specified file path.
        
        Args:
            path: File path to load from
            parent_widget: Parent widget for error dialogs
            
        Returns:
            True if load was successful, False otherwise
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            if parent_widget:
                QtWidgets.QMessageBox.critical(parent_widget, "Open error", str(e))
            return False
        
        self.load_from_data(data)
        self._saved_file_path = path
        self._unsaved_id = None  # Clear unsaved ID
        self._is_modified = False
        
        return True
    
    @staticmethod
    def format_time_ago(delta: datetime.timedelta) -> str:
        """
        Format timedelta as human-readable string.
        
        Args:
            delta: Time difference to format
            
        Returns:
            Human-readable string like "5m ago", "2h ago", etc.
        """
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        else:
            return f"{seconds // 86400}d ago"
    
    def check_autosave_recovery(self, parent_widget: QtWidgets.QWidget = None) -> Optional[dict]:
        """
        Check for autosave files on startup.
        
        Args:
            parent_widget: Parent widget for dialogs
            
        Returns:
            Recovery data dict if user chose to recover, None otherwise
        """
        from ..platform.paths import _app_data_root
        
        autosave_dir = _app_data_root() / "autosave"
        if not autosave_dir.exists():
            return None
        
        autosave_files = sorted(
            autosave_dir.glob("*.autosave.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # Most recent first
        )
        
        if not autosave_files:
            return None
        
        # Try most recent autosave
        most_recent = autosave_files[0]
        
        try:
            # Validate autosave file
            with open(most_recent, encoding='utf-8') as f:
                data = json.load(f)
            
            # Check version compatibility
            if data.get("version") != "2.0":
                raise ValueError("Incompatible autosave version")
            
            # Get metadata
            meta = data.get("_autosave_meta", {})
            timestamp_str = meta.get("timestamp", "")
            original_path = meta.get("original_path")
            
            # Format time
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp_str)
                age = datetime.datetime.now() - timestamp
                time_str = self.format_time_ago(age)
            except Exception:
                time_str = "unknown time"
            
            # Build message
            if original_path:
                file_name = os.path.basename(original_path)
                msg = f"Found autosave of '{file_name}'\nSaved: {time_str}"
            else:
                msg = f"Found autosave of unsaved file\nSaved: {time_str}"
            
            # Ask user
            reply = QtWidgets.QMessageBox.question(
                parent_widget,
                "Recover Autosave?",
                f"{msg}\n\nWould you like to recover it?",
                QtWidgets.QMessageBox.StandardButton.Yes |
                QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.Yes
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # Load the data
                self.load_from_data(data)
                self._saved_file_path = original_path  # Restore original path if any
                self._autosave_path = str(most_recent)  # Track this autosave
                self._is_modified = True  # Mark as modified - needs save
                
                QtWidgets.QMessageBox.information(
                    parent_widget,
                    "Recovery Successful",
                    "Autosave recovered. Please save your work."
                )
                return data
            else:
                # Delete if user declines
                most_recent.unlink()
                return None
                
        except Exception as e:
            self.log_service.error(f"Failed to recover autosave: {e}", "Recovery")
            # Silently skip corrupted autosaves
            return None
    
    @staticmethod
    def prompt_save_changes(
        parent_widget: QtWidgets.QWidget,
        save_callback: Callable[[], None],
        is_modified_callback: Callable[[], bool],
    ) -> QtWidgets.QMessageBox.StandardButton:
        """
        Prompt user to save unsaved changes.
        
        Args:
            parent_widget: Parent widget for the dialog
            save_callback: Function to call when user chooses Save
            is_modified_callback: Function to check if still modified after save
            
        Returns:
            The user's choice (Save, Discard, or Cancel)
        """
        reply = QtWidgets.QMessageBox.question(
            parent_widget,
            "Unsaved Changes",
            "Do you want to save your changes before closing?",
            QtWidgets.QMessageBox.StandardButton.Save |
            QtWidgets.QMessageBox.StandardButton.Discard |
            QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Save
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Save:
            # Save the file
            save_callback()
            # Check if save was successful (user didn't cancel the save dialog)
            if is_modified_callback():
                # User cancelled the save dialog, treat as cancel
                return QtWidgets.QMessageBox.StandardButton.Cancel
        
        return reply

