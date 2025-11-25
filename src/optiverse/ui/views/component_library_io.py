"""
Component Library I/O - Handles saving, loading, importing, and exporting components.

Extracted from ComponentEditor to reduce file size and improve separation of concerns.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PyQt6 import QtWidgets

from ...core.models import ComponentRecord, serialize_component
from ...core.utils import slugify
from ...services.error_handler import ErrorContext

if TYPE_CHECKING:
    from ...services.storage_service import StorageService

_logger = logging.getLogger(__name__)


class ComponentLibraryIO:
    """
    Handles all library I/O operations for the component editor.

    This class manages:
    - Saving components to the library
    - Exporting components to folders
    - Importing components from folders
    - Loading library files
    """

    def __init__(
        self,
        storage: StorageService,
        parent_widget: QtWidgets.QWidget,
        build_record_callback: Callable[[], ComponentRecord | None],
        refresh_callback: Callable[[], None],
        saved_callback: Callable[[], None],
    ):
        """
        Initialize the library I/O handler.

        Args:
            storage: StorageService for component persistence
            parent_widget: Parent widget for dialogs
            build_record_callback: Callback to build ComponentRecord from UI
            refresh_callback: Callback to refresh the library list
            saved_callback: Callback to emit when save is successful
        """
        self.storage = storage
        self.parent = parent_widget
        self._build_record = build_record_callback
        self._refresh_library = refresh_callback
        self._on_saved = saved_callback

    def save_component(self) -> bool:
        """
        Save component to library in folder-based structure.

        Returns:
            True if save was successful, False otherwise
        """
        with ErrorContext("while saving component", suppress=True):
            rec = self._build_record()
            if not rec:
                return False

            try:
                # Save using the new folder-based storage
                self.storage.save_component(rec)

                # Copy JSON to clipboard for convenience
                serialized = serialize_component(rec, self.storage.settings_service)
                QtWidgets.QApplication.clipboard().setText(json.dumps(serialized, indent=2))

                # Show success message
                library_path = self.storage.get_library_root()
                QtWidgets.QMessageBox.information(
                    self.parent,
                    "Saved",
                    f"Saved component '{rec.name}'\n\n"
                    f"Interfaces: {len(rec.interfaces) if rec.interfaces else 0}\n"
                    f"Library location:\n{library_path}\n\n"
                    f"Component JSON copied to clipboard.",
                )

                self._refresh_library()
                self._on_saved()
                return True

            except (OSError, ValueError) as e:
                QtWidgets.QMessageBox.critical(
                    self.parent,
                    "Save Failed",
                    f"Failed to save component '{rec.name}':\n\n{str(e)}",
                )
                return False
        return False

    def export_component(self) -> bool:
        """
        Export current component to a folder.

        Returns:
            True if export was successful, False otherwise
        """
        with ErrorContext("while exporting component", suppress=True):
            rec = self._build_record()
            if not rec:
                QtWidgets.QMessageBox.warning(
                    self.parent, "No Component", "Please create or load a component first."
                )
                return False

            # Ask user for destination folder
            dest_dir = QtWidgets.QFileDialog.getExistingDirectory(
                self.parent,
                "Select Export Destination",
                "",
                QtWidgets.QFileDialog.Option.ShowDirsOnly,
            )

            if not dest_dir:
                return False  # User cancelled

            try:
                # First save to library to ensure it's up to date
                self.storage.save_component(rec)

                # Then export from library
                success = self.storage.export_component(rec.name, dest_dir)

                if success:
                    folder_name = slugify(rec.name)
                    export_path = Path(dest_dir) / folder_name

                    QtWidgets.QMessageBox.information(
                        self.parent,
                        "Export Successful",
                        f"Component '{rec.name}' exported to:\n{export_path}\n\n"
                        f"You can share this folder with others.",
                    )
                    return True
                else:
                    QtWidgets.QMessageBox.critical(
                        self.parent, "Export Failed", f"Failed to export component '{rec.name}'."
                    )
                    return False
            except OSError as e:
                QtWidgets.QMessageBox.critical(
                    self.parent, "Export Error", f"Error exporting component:\n\n{str(e)}"
                )
                return False
        return False

    def import_component(self) -> bool:
        """
        Import a component from a folder.

        Returns:
            True if import was successful, False otherwise
        """
        # Ask user to select component folder
        source_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self.parent,
            "Select Component Folder to Import",
            "",
            QtWidgets.QFileDialog.Option.ShowDirsOnly,
        )

        if not source_dir:
            return False  # User cancelled

        # Check if component.json exists
        source_path = Path(source_dir)
        json_path = source_path / "component.json"

        if not json_path.exists():
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Invalid Component",
                f"Selected folder does not contain a component.json file:\n{source_dir}",
            )
            return False

        try:
            # Load component name to check for conflicts
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            component_name = data.get("name", "")

            if not component_name:
                QtWidgets.QMessageBox.warning(
                    self.parent, "Invalid Component", "Component JSON does not have a valid name."
                )
                return False

            # Check if component already exists
            existing = self.storage.get_component(component_name)
            overwrite = False

            if existing:
                reply = QtWidgets.QMessageBox.question(
                    self.parent,
                    "Component Exists",
                    f"Component '{component_name}' already exists in the library.\n\n"
                    f"Do you want to overwrite it?",
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No,
                    QtWidgets.QMessageBox.StandardButton.No,
                )

                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    overwrite = True
                else:
                    return False

            # Import the component
            success = self.storage.import_component(source_dir, overwrite=overwrite)

            if success:
                QtWidgets.QMessageBox.information(
                    self.parent,
                    "Import Successful",
                    f"Component '{component_name}' imported successfully.",
                )
                self._refresh_library()
                self._on_saved()
                return True
            else:
                QtWidgets.QMessageBox.critical(
                    self.parent, "Import Failed", f"Failed to import component from:\n{source_dir}"
                )
                return False
        except OSError as e:
            QtWidgets.QMessageBox.critical(
                self.parent, "Import Error", f"Error importing component:\n\n{str(e)}"
            )
            return False

    def reload_library(self) -> None:
        """Reload library from disk and show info dialog."""
        self._refresh_library()
        rows = self.storage.load_library()
        library_root = self.storage.get_library_root()
        QtWidgets.QMessageBox.information(
            self.parent,
            "Library",
            f"Loaded {len(rows)} component(s).\n\nLibrary folder:\n{library_root}",
        )

    def load_library_from_path(self) -> bool:
        """
        Load component library from a custom JSON file path.

        Returns:
            True if any new components were loaded, False otherwise
        """
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.parent, "Load Library File", "", "JSON files (*.json);;All files (*.*)"
        )
        if not path:
            return False

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                QtWidgets.QMessageBox.warning(
                    self.parent,
                    "Invalid Library",
                    "The selected file does not contain a valid component library (expected JSON array).",
                )
                return False

            # Merge with existing library
            existing = self.storage.load_library()
            existing_names = {comp.get("name") for comp in existing}

            new_count = 0
            for comp in data:
                if isinstance(comp, dict) and comp.get("name"):
                    if comp.get("name") not in existing_names:
                        existing.append(comp)
                        existing_names.add(comp.get("name"))
                        new_count += 1

            if new_count > 0:
                self.storage.save_library(existing)
                self._refresh_library()
                QtWidgets.QMessageBox.information(
                    self.parent,
                    "Library Loaded",
                    f"Loaded {new_count} new component(s) from:\n{path}\n\n"
                    f"Total components: {len(existing)}",
                )
                return True
            else:
                QtWidgets.QMessageBox.information(
                    self.parent,
                    "Library Loaded",
                    "No new components found in the library file (all components already exist).",
                )
                return False

        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.warning(
                self.parent, "Invalid JSON", f"Could not parse JSON file:\n{e}"
            )
            return False
        except OSError as e:
            QtWidgets.QMessageBox.warning(
                self.parent, "Load Error", f"Could not load library file:\n{e}"
            )
            return False
