"""Tree-based panel for managing interface properties with collapsible sections."""

from __future__ import annotations

from typing import Callable, cast

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core import interface_types
from ...core.interface_definition import InterfaceDefinition
from .constants import INTERFACE_DEFAULT_HALF_LENGTH_MM, INTERFACE_TREE_INDENTATION
from .interface_properties_widget import InterfacePropertiesWidget
from .interface_widgets import InterfaceTreeWidget


class InterfaceTreePanel(QtWidgets.QWidget):
    """
    Tree-based panel for managing optical interfaces with collapsible sections.

    Features:
    - Collapsible tree structure
    - Simple two-column property list
    - Type indicator with icon
    - Compact display
    - Easy reordering
    """

    interfacesChanged = QtCore.pyqtSignal()
    interfaceSelected = QtCore.pyqtSignal(int)  # Single selection
    interfacesSelected = QtCore.pyqtSignal(list)  # Multi-selection

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._tree: InterfaceTreeWidget | None = None
        self._interfaces: list[InterfaceDefinition] = []
        self._tree_items: list[QtWidgets.QTreeWidgetItem] = []
        self._property_widgets: list[InterfacePropertiesWidget] = []
        self._child_items: list[QtWidgets.QTreeWidgetItem | None] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        header = self._create_header()
        layout.addWidget(header)

        # Create tree
        self._tree = InterfaceTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(INTERFACE_TREE_INDENTATION)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._tree.setUniformRowHeights(False)

        # Connect signals
        self._tree.deleteKeyPressed.connect(self._on_delete_key)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.itemExpanded.connect(self._on_item_expanded)
        self._tree.itemCollapsed.connect(self._on_item_collapsed)
        self._tree.itemChanged.connect(self._on_item_renamed)

        # Whitespace click handling
        self._tree.viewport().installEventFilter(self)

        layout.addWidget(self._tree, 1)

        btn_layout = self._create_button_layout()
        layout.addLayout(btn_layout)

    def _create_header(self) -> QtWidgets.QWidget:
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(5, 5, 5, 5)

        label = QtWidgets.QLabel("Interfaces")
        header_layout.addWidget(label)
        header_layout.addStretch()

        self._add_btn = QtWidgets.QPushButton("Add Interface")
        self._add_menu = QtWidgets.QMenu(self)

        for type_name in interface_types.get_all_type_names():
            display_name = interface_types.get_type_display_name(type_name)
            emoji = interface_types.get_type_emoji(type_name)
            action = self._add_menu.addAction(f"{emoji} {display_name}")
            action.setData(type_name)
            action.triggered.connect(lambda checked=False, t=type_name: self._add_interface(t))

        self._add_btn.setMenu(self._add_menu)
        header_layout.addWidget(self._add_btn)

        return header

    def _create_button_layout(self) -> QtWidgets.QHBoxLayout:
        btn_layout = QtWidgets.QHBoxLayout()

        self._move_up_btn = QtWidgets.QPushButton("↑ Move Up")
        self._move_up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(self._move_up_btn)

        self._move_down_btn = QtWidgets.QPushButton("↓ Move Down")
        self._move_down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(self._move_down_btn)

        btn_layout.addStretch()

        self._delete_btn = QtWidgets.QPushButton("Delete")
        self._delete_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self._delete_btn)

        return btn_layout

    def eventFilter(self, obj: QtCore.QObject | None, event: QtCore.QEvent | None) -> bool:
        """Handle whitespace clicks to deselect."""
        if obj is None or event is None or self._tree is None:
            return super().eventFilter(obj, event)

        if obj == self._tree.viewport() and event.type() == QtCore.QEvent.Type.MouseButtonPress:
            mouse_event = cast(QtGui.QMouseEvent, event)
            if self._tree.itemAt(mouse_event.pos()) is None:
                self._tree.clearSelection()
                self.interfaceSelected.emit(-1)
                return False

        return super().eventFilter(obj, event)

    # --- Tree Navigation Helpers ---

    @staticmethod
    def get_top_level_item(item: QtWidgets.QTreeWidgetItem) -> QtWidgets.QTreeWidgetItem:
        """Get the top-level parent of a tree item."""
        while item.parent() is not None:
            item = item.parent()
        return item

    def _get_selected_top_level_indices(self) -> list[int]:
        """Get indices of all selected top-level items."""
        if self._tree is None:
            return []

        indices: list[int] = []
        for selected_item in self._tree.selectedItems():
            top_item = self.get_top_level_item(selected_item)
            index = self._tree.indexOfTopLevelItem(top_item)
            if index >= 0 and index not in indices:
                indices.append(index)

        return sorted(indices)

    def _with_signals_blocked(self, func: Callable[[], None]) -> None:
        """Execute a function with tree signals blocked."""
        if self._tree is None:
            func()
            return

        self._tree.blockSignals(True)
        try:
            func()
        finally:
            self._tree.blockSignals(False)

    # --- Interface CRUD ---

    def _add_interface(self, element_type: str) -> None:
        interface = InterfaceDefinition(element_type=element_type)
        interface.x1_mm = -INTERFACE_DEFAULT_HALF_LENGTH_MM
        interface.y1_mm = 0.0
        interface.x2_mm = INTERFACE_DEFAULT_HALF_LENGTH_MM
        interface.y2_mm = 0.0
        self.add_interface(interface)

    def _create_tree_item(self, interface: InterfaceDefinition, index: int) -> QtWidgets.QTreeWidgetItem:
        if self._tree is None:
            raise RuntimeError("Tree not initialized")

        item = QtWidgets.QTreeWidgetItem()
        display_name = interface.name if interface.name else f"Interface {index + 1}"
        item.setText(0, display_name)
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEditable)
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, index)

        prop_widget = InterfacePropertiesWidget(interface, show_coordinates=True)
        prop_widget.propertiesChanged.connect(self.interfacesChanged.emit)

        self._tree.addTopLevelItem(item)

        child_item = QtWidgets.QTreeWidgetItem(item)
        self._tree.setItemWidget(child_item, 0, prop_widget)

        if index >= len(self._child_items):
            self._child_items.extend([None] * (index + 1 - len(self._child_items)))
        self._child_items[index] = child_item

        child_item.setSizeHint(0, prop_widget.sizeHint())
        item.setExpanded(True)

        return item

    def _rebuild_tree(self) -> None:
        if self._tree is None:
            return

        self._tree.clear()
        self._tree_items.clear()
        self._property_widgets.clear()
        self._child_items.clear()

        for i, interface in enumerate(self._interfaces):
            item = self._create_tree_item(interface, i)
            self._tree_items.append(item)

            if item.childCount() > 0:
                child = item.child(0)
                if child:
                    widget = self._tree.itemWidget(child, 0)
                    if isinstance(widget, InterfacePropertiesWidget):
                        self._property_widgets.append(widget)

    # --- Event Handlers ---

    def _on_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        selected_indices = self._get_selected_top_level_indices()
        if len(selected_indices) == 1:
            self.interfaceSelected.emit(selected_indices[0])
        self.interfacesSelected.emit(selected_indices)

    def _on_item_expanded(self, item: QtWidgets.QTreeWidgetItem) -> None:
        if self._tree:
            QtCore.QTimer.singleShot(0, self._tree.updateGeometries)

    def _on_item_collapsed(self, item: QtWidgets.QTreeWidgetItem) -> None:
        if self._tree:
            QtCore.QTimer.singleShot(0, self._tree.updateGeometries)

    def _on_item_renamed(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        if item.parent() is not None or self._tree is None:
            return
        index = self._tree.indexOfTopLevelItem(item)
        if 0 <= index < len(self._interfaces):
            self._interfaces[index].name = item.text(0).strip()
            self.interfacesChanged.emit()

    def _on_delete_key(self) -> None:
        indices = self._get_selected_top_level_indices()
        if not indices:
            return

        msg = f"Delete interface {indices[0] + 1}?" if len(indices) == 1 else f"Delete {len(indices)} interfaces?"
        reply = QtWidgets.QMessageBox.question(
            self, "Delete Interface" if len(indices) == 1 else "Delete Interfaces", msg,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            for index in sorted(indices, reverse=True):
                self.remove_interface(index)

    def _move_up(self) -> None:
        if self._tree is None:
            return
        item = self._tree.currentItem()
        if item is None:
            return

        top_item = self.get_top_level_item(item)
        index = self._tree.indexOfTopLevelItem(top_item)

        if index > 0:
            self.move_interface(index, index - 1)
            self._tree.setCurrentItem(self._tree_items[index - 1])

    def _move_down(self) -> None:
        if self._tree is None:
            return
        item = self._tree.currentItem()
        if item is None:
            return

        top_item = self.get_top_level_item(item)
        index = self._tree.indexOfTopLevelItem(top_item)

        if 0 <= index < len(self._interfaces) - 1:
            self.move_interface(index, index + 1)
            self._tree.setCurrentItem(self._tree_items[index + 1])

    def _delete_selected(self) -> None:
        if self._tree is None:
            return
        item = self._tree.currentItem()
        if item is None:
            return

        top_item = self.get_top_level_item(item)
        index = self._tree.indexOfTopLevelItem(top_item)

        if index >= 0:
            reply = QtWidgets.QMessageBox.question(
                self, "Delete Interface", f"Delete interface {index + 1}?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.remove_interface(index)

    # --- Public API ---

    def add_interface(self, interface: InterfaceDefinition) -> None:
        self._interfaces.append(interface)
        self._rebuild_tree()
        self.interfacesChanged.emit()

    def remove_interface(self, index: int) -> None:
        if 0 <= index < len(self._interfaces):
            self._interfaces.pop(index)
            self._rebuild_tree()
            self.interfacesChanged.emit()

    def get_interfaces(self) -> list[InterfaceDefinition]:
        return self._interfaces.copy()

    def set_interfaces(self, interfaces: list[InterfaceDefinition]) -> None:
        self._interfaces = interfaces.copy()
        self._rebuild_tree()

    def clear(self) -> None:
        self._interfaces.clear()
        self._rebuild_tree()
        self.interfacesChanged.emit()

    def get_interface(self, index: int) -> InterfaceDefinition | None:
        if 0 <= index < len(self._interfaces):
            return self._interfaces[index]
        return None

    def update_interface(self, index: int, interface: InterfaceDefinition) -> None:
        if 0 <= index < len(self._property_widgets):
            self._interfaces[index] = interface
            self._property_widgets[index].update_from_interface(interface)
            self.interfacesChanged.emit()

    def select_interface(self, index: int) -> None:
        if self._tree is None:
            return
        if 0 <= index < len(self._tree_items):
            self._tree.setCurrentItem(self._tree_items[index])
        else:
            self._tree.setCurrentItem(None)

    def select_interfaces(self, indices: list[int]) -> None:
        if self._tree is None:
            return

        def do_select() -> None:
            if self._tree is None:
                return
            self._tree.clearSelection()
            for index in indices:
                if 0 <= index < len(self._tree_items):
                    self._tree_items[index].setSelected(True)

        self._with_signals_blocked(do_select)

    def get_selected_index(self) -> int:
        if self._tree is None:
            return -1
        item = self._tree.currentItem()
        if item is None:
            return -1
        top_item = self.get_top_level_item(item)
        result = self._tree.indexOfTopLevelItem(top_item)
        return result if result >= 0 else -1

    def get_selected_indices(self) -> list[int]:
        return self._get_selected_top_level_indices()

    def count(self) -> int:
        return len(self._interfaces)

    def move_interface(self, from_index: int, to_index: int) -> None:
        if 0 <= from_index < len(self._interfaces) and 0 <= to_index < len(self._interfaces) and from_index != to_index:
            interface = self._interfaces.pop(from_index)
            self._interfaces.insert(to_index, interface)
            self._rebuild_tree()
            self.interfacesChanged.emit()
