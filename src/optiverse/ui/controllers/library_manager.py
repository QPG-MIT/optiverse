"""
Library management for component library operations.

This module extracts library loading and import logic from MainWindow.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from ...services.log_service import LogService
    from ...services.storage_service import StorageService


# Category display order
CATEGORY_ORDER = [
    "Lenses", "Objectives", "Mirrors", "Beamsplitters",
    "Dichroics", "Waveplates", "Sources", "Background", "Misc", "Other"
]

# Map from lowercase category keys to display names
CATEGORY_MAP = {
    "lenses": "Lenses",
    "objectives": "Objectives",
    "mirrors": "Mirrors",
    "beamsplitters": "Beamsplitters",
    "dichroics": "Dichroics",
    "waveplates": "Waveplates",
    "sources": "Sources",
    "background": "Background",
    "misc": "Misc",
}


class LibraryManager:
    """
    Manages component library loading, display, and import operations.

    Extracts library-related logic from MainWindow to improve separation of concerns.
    """

    def __init__(
        self,
        library_tree: QtWidgets.QTreeWidget,
        storage_service: "StorageService",
        log_service: "LogService",
        get_dark_mode: Callable[[], bool],
        get_style: Callable[[], QtWidgets.QStyle],
        parent_widget: QtWidgets.QWidget,
    ):
        """
        Initialize library manager.

        Args:
            library_tree: Tree widget to populate with components
            storage_service: Service for component storage operations
            log_service: Logging service
            get_dark_mode: Callable returning current dark mode state
            get_style: Callable returning current widget style
            parent_widget: Parent widget for dialogs
        """
        self.library_tree = library_tree
        self.storage_service = storage_service
        self.log_service = log_service
        self._get_dark_mode = get_dark_mode
        self._get_style = get_style
        self.parent_widget = parent_widget

        # Component templates for toolbar placement
        self.component_templates: Dict[str, dict] = {}

    def populate(self) -> Dict[str, dict]:
        """
        Load and populate component library organized by category.

        Returns:
            Dictionary mapping toolbar type strings to component data
        """
        from ...objects.component_registry import ComponentRegistry
        from ...objects.definitions_loader import load_component_dicts_from_multiple
        from ...platform.paths import get_all_custom_library_roots

        self.library_tree.clear()

        # Load built-in (standard) components
        builtin_records = ComponentRegistry.get_standard_components()
        for rec in builtin_records:
            rec["_source"] = "builtin"

        # Load custom library components
        custom_library_paths = get_all_custom_library_roots()
        user_records = load_component_dicts_from_multiple(custom_library_paths)
        for rec in user_records:
            rec["_source"] = "user"

        all_records = builtin_records + user_records

        # Cache standard component templates for toolbar
        self.component_templates = self._extract_toolbar_templates(all_records)

        # Organize and display by category
        categories = self._categorize_records(all_records)
        self._populate_tree(categories)

        self.library_tree.expandAll()
        return self.component_templates

    def _extract_toolbar_templates(self, records: List[dict]) -> Dict[str, dict]:
        """Extract standard component templates for toolbar placement."""
        templates = {}
        for rec in records:
            name = rec.get("name", "")
            if "Standard Lens" in name and "lens" not in templates:
                templates["lens"] = rec
            elif "Standard Mirror" in name and "mirror" not in templates:
                templates["mirror"] = rec
            elif "Standard Beamsplitter" in name and "beamsplitter" not in templates:
                templates["beamsplitter"] = rec
        return templates

    def _categorize_records(self, records: List[dict]) -> Dict[str, List[dict]]:
        """Organize records by category."""
        from ...objects.component_registry import ComponentRegistry

        categories = {cat: [] for cat in CATEGORY_ORDER}

        for rec in records:
            name = rec.get("name", "")

            # Check explicit category first
            if "category" in rec:
                category_key = rec["category"].lower()
                category = CATEGORY_MAP.get(category_key, "Other")
            else:
                # Fallback: determine from interface element_type
                interfaces = rec.get("interfaces", [])
                if interfaces:
                    element_type = interfaces[0].get("element_type", "lens")
                    category = ComponentRegistry.get_category_for_element_type(element_type, name)
                else:
                    category = "Other"

            categories[category].append(rec)

        return categories

    def _populate_tree(self, categories: Dict[str, List[dict]]):
        """Populate tree widget with categorized components."""
        is_dark = self._get_dark_mode()
        style = self._get_style()

        for category_name in CATEGORY_ORDER:
            comps = categories.get(category_name, [])
            if not comps:
                continue

            # Create category header
            category_item = QtWidgets.QTreeWidgetItem([category_name])
            category_item.setFlags(category_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsDragEnabled)

            # Style category header
            font = category_item.font(0)
            font.setBold(True)
            font.setPointSize(10)
            category_item.setFont(0, font)

            # Color adapts to dark/light mode
            if is_dark:
                category_item.setForeground(0, QtGui.QColor(140, 150, 200))
            else:
                category_item.setForeground(0, QtGui.QColor(60, 60, 100))

            self.library_tree.addTopLevelItem(category_item)

            # Add components under category
            for rec in comps:
                name = rec.get("name", "(unnamed)")
                img = rec.get("image_path")

                if img and os.path.exists(img):
                    icon = QtGui.QIcon(img)
                else:
                    icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)

                comp_item = QtWidgets.QTreeWidgetItem([name])
                comp_item.setIcon(0, icon)
                comp_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, rec)
                category_item.addChild(comp_item)

    def import_library(self) -> bool:
        """
        Import components from another library folder.

        Returns:
            True if any components were imported
        """
        # Ask user to select a library folder
        source_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self.parent_widget,
            "Select Component Library Folder to Import",
            "",
            QtWidgets.QFileDialog.Option.ShowDirsOnly
        )

        if not source_dir:
            return False

        source_path = Path(source_dir)

        # Find component folders
        component_folders = [
            p for p in source_path.iterdir()
            if p.is_dir() and (p / "component.json").exists()
        ]

        if not component_folders:
            QtWidgets.QMessageBox.warning(
                self.parent_widget,
                "Invalid Library",
                f"Selected folder does not contain any valid components.\n\n"
                f"A component library should contain folders with component.json files."
            )
            return False

        # Ask for confirmation
        reply = QtWidgets.QMessageBox.question(
            self.parent_widget,
            "Import Library",
            f"Found {len(component_folders)} component(s) in:\n{source_dir}\n\n"
            f"Import all components into your user library?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes
        )

        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return False

        # Import each component
        imported_count = 0
        skipped_count = 0

        for comp_folder in component_folders:
            try:
                success = self.storage_service.import_component(str(comp_folder), overwrite=False)
                if success:
                    imported_count += 1
                else:
                    skipped_count += 1
            except OSError as e:
                self.log_service.warning(f"Failed to import {comp_folder.name}: {e}", "Import")
                skipped_count += 1

        # Show results
        message = f"Import complete!\n\nImported: {imported_count} component(s)\n"
        if skipped_count > 0:
            message += f"Skipped: {skipped_count} component(s) (already exist or invalid)"

        QtWidgets.QMessageBox.information(
            self.parent_widget,
            "Import Complete",
            message
        )

        return imported_count > 0



