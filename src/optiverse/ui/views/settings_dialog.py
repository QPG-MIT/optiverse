"""
Settings dialog for application-wide preferences.

Provides a general-purpose settings interface organized by categories,
allowing easy addition of new settings in the future.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from ...platform.paths import get_user_library_root
from ...services.settings_service import SettingsService


class SettingsDialog(QtWidgets.QDialog):
    """
    General-purpose settings dialog with category-based organization.

    Architecture:
    - Left panel: Category list (Library, Appearance, Performance, etc.)
    - Right panel: Stacked widget with settings pages
    - Easy to extend with new categories and settings

    Signals:
        settings_changed: Emitted when settings are applied
    """

    settings_changed = QtCore.pyqtSignal()

    def __init__(
        self, settings_service: SettingsService, parent: QtWidgets.QWidget | None = None
    ):
        super().__init__(parent)
        self.settings_service = settings_service

        self.setWindowTitle("Preferences")
        self.resize(800, 500)

        # Main layout: horizontal split
        main_layout = QtWidgets.QHBoxLayout(self)

        # Left panel: Category list
        self.category_list = QtWidgets.QListWidget()
        self.category_list.setMaximumWidth(180)
        self.category_list.setIconSize(QtCore.QSize(24, 24))
        self.category_list.currentRowChanged.connect(self._on_category_changed)
        main_layout.addWidget(self.category_list)

        # Right panel: Settings pages
        right_layout = QtWidgets.QVBoxLayout()

        # Title label
        self.page_title = QtWidgets.QLabel()
        self.page_title.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px;")
        right_layout.addWidget(self.page_title)

        # Stacked widget for different settings pages
        self.pages_stack = QtWidgets.QStackedWidget()
        right_layout.addWidget(self.pages_stack)

        # Button box
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
            | QtWidgets.QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._apply_settings
        )
        right_layout.addWidget(button_box)

        main_layout.addLayout(right_layout, 1)

        # Build settings pages
        self._build_pages()

        # Load current settings
        self._load_settings()

        # Select first category
        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

    def _build_pages(self):
        """Build all settings pages and add to category list."""
        # Library Settings
        self._build_library_page()
        self._add_category(
            "Library", "Component library locations and organization", self.library_page
        )

        # Future categories can be added here:
        # self._build_appearance_page()
        # self._add_category("Appearance", "Theme, colors, and UI preferences", self.appearance_page)

        # self._build_performance_page()
        # self._add_category("Performance", "Raytracing and rendering options", self.performance_page)

    def _add_category(self, name: str, description: str, page: QtWidgets.QWidget):
        """Add a category to the list."""
        item = QtWidgets.QListWidgetItem(name)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, description)
        self.category_list.addItem(item)
        self.pages_stack.addWidget(page)

    def _on_category_changed(self, index: int):
        """Handle category selection change."""
        if index >= 0:
            self.pages_stack.setCurrentIndex(index)
            item = self.category_list.item(index)
            item.data(QtCore.Qt.ItemDataRole.UserRole)
            self.page_title.setText(f"{item.text()}")

    def _build_library_page(self):
        """Build the Library settings page."""
        self.library_page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.library_page)
        layout.setContentsMargins(10, 10, 10, 10)

        # Description
        desc = QtWidgets.QLabel(
            "Configure component library locations. Optiverse will search all configured "
            "directories for components. When saving assemblies, component image paths will "
            "be stored relative to these library locations, making your assemblies portable "
            "across different computers."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: palette(dark); padding: 5px;")
        layout.addWidget(desc)

        # Library paths list
        list_label = QtWidgets.QLabel("Library Directories:")
        list_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(list_label)

        # List widget with buttons
        list_layout = QtWidgets.QHBoxLayout()

        self.library_list = QtWidgets.QListWidget()
        self.library_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        list_layout.addWidget(self.library_list)

        # Buttons
        button_layout = QtWidgets.QVBoxLayout()

        self.add_library_btn = QtWidgets.QPushButton("Add...")
        self.add_library_btn.clicked.connect(self._add_library_path)
        button_layout.addWidget(self.add_library_btn)

        self.remove_library_btn = QtWidgets.QPushButton("Remove")
        self.remove_library_btn.clicked.connect(self._remove_library_path)
        button_layout.addWidget(self.remove_library_btn)

        button_layout.addStretch()

        self.open_library_btn = QtWidgets.QPushButton("Open in Finder")
        self.open_library_btn.clicked.connect(self._open_selected_library)
        button_layout.addWidget(self.open_library_btn)

        list_layout.addLayout(button_layout)
        layout.addLayout(list_layout)

        # Info label
        info = QtWidgets.QLabel(
            "💡 Tip: The default user library is always included. "
            "Add additional directories to organize components by project, vendor, or category."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: palette(dark); padding: 5px; margin-top: 5px;")
        layout.addWidget(info)

        layout.addStretch()

    def _load_settings(self):
        """Load current settings from SettingsService."""
        # Load library paths
        library_paths = self.settings_service.get_value("library_paths", [], list)

        # Always show default user library first (read-only)
        default_path = str(get_user_library_root())
        default_item = QtWidgets.QListWidgetItem(f"📁 {default_path}")
        default_item.setData(QtCore.Qt.ItemDataRole.UserRole, default_path)
        default_item.setForeground(QtGui.QBrush(QtGui.QColor(100, 100, 100)))
        default_item.setFlags(default_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
        default_item.setToolTip("Default user library (always included)")
        self.library_list.addItem(default_item)

        # Add custom library paths
        for path in library_paths:
            if path and path != default_path:  # Don't duplicate default
                self._add_library_item(path)

    def _add_library_item(self, path: str):
        """Add a library path to the list."""
        # Check if path exists
        path_obj = Path(path)
        if path_obj.exists():
            # Count components in this library
            component_count = self._count_components(path_obj)
            display_text = f"📚 {path}"
            if component_count > 0:
                display_text += f"  ({component_count} components)"
        else:
            display_text = f"❌ {path} (not found)"

        item = QtWidgets.QListWidgetItem(display_text)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self.library_list.addItem(item)

    def _count_components(self, library_path: Path) -> int:
        """Count components in a library directory."""
        if not library_path.exists() or not library_path.is_dir():
            return 0

        count = 0
        try:
            for item in library_path.iterdir():
                if item.is_dir() and (item / "component.json").exists():
                    count += 1
        except OSError:
            pass  # Library path may not exist or be inaccessible

        return count

    def _add_library_path(self):
        """Add a new library path."""
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Component Library Directory",
            "",
            QtWidgets.QFileDialog.Option.ShowDirsOnly,
        )

        if not path:
            return

        # Check if already in list
        for i in range(self.library_list.count()):
            item = self.library_list.item(i)
            existing_path = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if existing_path == path:
                QtWidgets.QMessageBox.information(
                    self, "Already Added", f"This library path is already in the list:\n{path}"
                )
                return

        # Add to list
        self._add_library_item(path)

    def _remove_library_path(self):
        """Remove selected library path."""
        current_item = self.library_list.currentItem()
        if not current_item:
            return

        # Don't allow removing the default library (first item)
        if self.library_list.row(current_item) == 0:
            QtWidgets.QMessageBox.information(
                self, "Cannot Remove", "The default user library cannot be removed."
            )
            return

        # Confirm removal
        path = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
        reply = QtWidgets.QMessageBox.question(
            self,
            "Remove Library Path",
            f"Remove this library path from the list?\n\n{path}\n\n"
            "Note: This only removes it from the list. The files will not be deleted.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.library_list.takeItem(self.library_list.row(current_item))

    def _open_selected_library(self):
        """Open selected library in file manager."""
        current_item = self.library_list.currentItem()
        if not current_item:
            return

        path = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if path:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))

    def _apply_settings(self):
        """Apply settings without closing dialog."""
        self._save_settings()
        self.settings_changed.emit()

        QtWidgets.QMessageBox.information(
            self,
            "Settings Applied",
            "Settings have been applied successfully.\n\n"
            "Note: You may need to restart the application for all changes to take effect.",
        )

    def _save_settings(self):
        """Save settings to SettingsService."""
        # Collect library paths (skip first item which is default)
        library_paths = []
        for i in range(1, self.library_list.count()):  # Start at 1 to skip default
            item = self.library_list.item(i)
            path = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if path:
                library_paths.append(path)

        # Save to settings
        self.settings_service.set_value("library_paths", library_paths)

    def accept(self):
        """Override accept to save settings."""
        self._save_settings()
        self.settings_changed.emit()
        super().accept()
