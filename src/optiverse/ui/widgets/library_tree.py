"""Drag-enabled library tree widget for component templates."""

from __future__ import annotations

import json

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.constants import MIME_OPTICS_COMPONENT


class HasComponentEditor:
    """Protocol marker for windows that can open component editor."""

    def open_component_editor(self, component: dict | None = None) -> None:
        """Open the component editor."""
        ...


class LibraryTree(QtWidgets.QTreeWidget):
    """Drag-enabled library tree for component templates organized by category."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIconSize(QtCore.QSize(64, 64))
        self.setDragEnabled(True)
        self.setSelectionMode(QtWidgets.QTreeWidget.SelectionMode.SingleSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(QtCore.Qt.DropAction.CopyAction)
        self.setIndentation(20)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Expand all categories by default
        self.expandAll()

    def _show_context_menu(self, position):
        """Show context menu for component items."""
        item = self.itemAt(position)
        if not item:
            return

        # Only show context menu for leaf items (components), not category headers
        if item.childCount() > 0:
            return

        payload = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not payload:
            return

        # Create context menu
        menu = QtWidgets.QMenu(self)
        edit_action = menu.addAction("Edit Component")
        edit_action.triggered.connect(lambda: self._edit_component(payload))

        # Show menu at cursor position
        menu.exec(self.viewport().mapToGlobal(position))

    def _edit_component(self, component_data: dict):
        """Open component editor with the selected component loaded."""
        # Get the main window parent
        main_window = self.window()
        if isinstance(main_window, HasComponentEditor):
            main_window.open_component_editor(component_data)

    def startDrag(self, actions):
        it = self.currentItem()
        if not it:
            return

        # Only allow dragging leaf items (components), not category headers
        if it.childCount() > 0:
            return

        payload = it.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not payload:
            return

        md = QtCore.QMimeData()
        md.setData(MIME_OPTICS_COMPONENT, json.dumps(payload).encode("utf-8"))
        drag = QtGui.QDrag(self)
        drag.setMimeData(md)

        # Set an empty 1x1 transparent pixmap to prevent Qt from creating a default drag cursor
        # The ghost preview in GraphicsView provides the visual feedback
        empty_pixmap = QtGui.QPixmap(1, 1)
        empty_pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        drag.setPixmap(empty_pixmap)
        drag.setHotSpot(QtCore.QPoint(0, 0))

        # Execute drag and clear selection afterwards
        result = drag.exec(QtCore.Qt.DropAction.CopyAction)
        if result == QtCore.Qt.DropAction.CopyAction:
            self.clearSelection()
