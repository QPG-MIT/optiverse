"""Tree-based panel for managing interface properties with collapsible sections."""

from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from ...core import interface_types
from ...core.interface_definition import InterfaceDefinition
from .interface_widgets import (
    InterfaceTreeWidget,
    PropertyListWidget,
)


class InterfaceTreePanel(QtWidgets.QWidget):
    """
    Tree-based panel for managing optical interfaces with collapsible sections.

    Features:
    - Collapsible tree structure
    - Simple two-column property list
    - Type indicator with icon
    - Compact display
    - Easy reordering

    Signals:
        interfacesChanged: Emitted when interfaces list changes
        interfaceSelected: Emitted when an interface is selected (index) - for single selection
        interfacesSelected: Emitted when multiple interfaces are selected (list of indices)
    """

    interfacesChanged = QtCore.pyqtSignal()
    interfaceSelected = QtCore.pyqtSignal(int)  # Single selection (backward compatibility)
    interfacesSelected = QtCore.pyqtSignal(list)  # Multi-selection

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self._interfaces: list[InterfaceDefinition] = []
        self._tree_items: list[QtWidgets.QTreeWidgetItem] = []
        self._property_widgets: list[PropertyListWidget] = []
        self._child_items: list[QtWidgets.QTreeWidgetItem] = (
            []
        )  # Store child items for size updates

        self._setup_ui()

    def _setup_ui(self):
        """Create the UI layout."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Header with label and add button
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(5, 5, 5, 5)

        label = QtWidgets.QLabel("Interfaces")
        label.setStyleSheet("font-weight: normal; font-size: 10pt;")
        header_layout.addWidget(label)

        header_layout.addStretch()

        # Add interface dropdown button
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

        layout.addWidget(header)

        # Tree widget (custom subclass for keyboard handling)
        self._tree = InterfaceTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(10)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)

        # Enable multi-selection
        self._tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)

        # Fix scrolling behavior
        self._tree.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._tree.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._tree.setUniformRowHeights(False)  # Allow variable height items

        # Custom styling to keep text readable when selected
        self._tree.setStyleSheet(
            """
            QTreeWidget::item:selected {
                background-color: #d0d0d0;
                color: black;
            }
        """
        )

        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.itemExpanded.connect(self._on_item_expanded)
        self._tree.itemCollapsed.connect(self._on_item_collapsed)
        self._tree.itemChanged.connect(self._on_item_renamed)

        # Connect Delete/Backspace key handler
        self._tree.deleteKeyPressed.connect(self._handle_delete_key)

        # Allow clicking on white space to deselect
        self._tree.viewport().installEventFilter(self)

        layout.addWidget(self._tree, 1)

        # Bottom buttons
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

        layout.addLayout(btn_layout)

    def _add_interface(self, element_type: str):
        """Add a new interface of specified type."""
        interface = InterfaceDefinition(element_type=element_type)

        # Set default geometry (centered in image, horizontal line)
        # Coordinate system: (0, 0) at IMAGE CENTER, Y-up (mathematical convention)
        # Default interface: horizontal line at center, 10mm long
        y_center = 0.0  # mm - at vertical center
        x_center = 0.0  # mm - at horizontal center
        half_length = 5.0  # mm - half the line length (10mm total)

        interface.x1_mm = x_center - half_length
        interface.y1_mm = y_center
        interface.x2_mm = x_center + half_length
        interface.y2_mm = y_center

        self.add_interface(interface)

    def _create_tree_item(
        self, interface: InterfaceDefinition, index: int
    ) -> QtWidgets.QTreeWidgetItem:
        """Create a tree item for an interface."""
        item = QtWidgets.QTreeWidgetItem()

        # Use custom name if set, otherwise default to "Interface N"
        display_name = interface.name if interface.name else f"Interface {index + 1}"
        item.setText(0, display_name)

        # Make item editable (for renaming with double-click)
        item.setFlags(
            item.flags() | QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEditable
        )

        # Store interface index in item data for later retrieval
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, index)

        # Create property list widget
        prop_widget = PropertyListWidget(interface)
        prop_widget.propertyChanged.connect(self.interfacesChanged.emit)
        # Connect to geometry changed signal to update tree item size
        prop_widget.geometryChanged = lambda: self._update_child_item_size(index)

        self._tree.addTopLevelItem(item)

        # Add child item to hold the widget
        child_item = QtWidgets.QTreeWidgetItem(item)
        self._tree.setItemWidget(child_item, 0, prop_widget)

        # Store child item for later size updates
        if index >= len(self._child_items):
            self._child_items.extend([None] * (index + 1 - len(self._child_items)))
        self._child_items[index] = child_item

        # Adjust child item size to fit widget
        child_item.setSizeHint(0, prop_widget.sizeHint())

        # Expand by default
        item.setExpanded(True)

        return item

    def _on_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int):
        """Handle tree item clicks."""
        # Get all selected top-level items
        selected_items = self._tree.selectedItems()
        selected_indices = []

        for sel_item in selected_items:
            # Find the top-level item
            while sel_item.parent() is not None:
                sel_item = sel_item.parent()

            # Get index
            index = self._tree.indexOfTopLevelItem(sel_item)
            if index >= 0 and index not in selected_indices:
                selected_indices.append(index)

        selected_indices.sort()

        # Emit signals
        if len(selected_indices) == 1:
            self.interfaceSelected.emit(selected_indices[0])

        self.interfacesSelected.emit(selected_indices)

    def _update_child_item_size(self, index: int):
        """Update the size hint for a child item after widget size changes."""
        if 0 <= index < len(self._child_items) and 0 <= index < len(self._property_widgets):
            child_item = self._child_items[index]
            prop_widget = self._property_widgets[index]
            if child_item and prop_widget:
                # Update size hint to match widget's new size
                child_item.setSizeHint(0, prop_widget.sizeHint())
                # Force tree to update geometries
                QtCore.QTimer.singleShot(0, self._tree.updateGeometries)

    def _on_item_expanded(self, item: QtWidgets.QTreeWidgetItem):
        """Handle item expansion - update scroll."""
        # Schedule geometry update for smooth scrolling
        QtCore.QTimer.singleShot(0, self._tree.updateGeometries)

    def _on_item_collapsed(self, item: QtWidgets.QTreeWidgetItem):
        """Handle item collapse - update scroll."""
        # Schedule geometry update for smooth scrolling
        QtCore.QTimer.singleShot(0, self._tree.updateGeometries)

    def _on_item_renamed(self, item: QtWidgets.QTreeWidgetItem, column: int):
        """Handle item name changes (user edited the text)."""
        # Only handle top-level items (interface headers, not property widgets)
        if item.parent() is not None:
            return

        # Get the index from stored data
        index = self._tree.indexOfTopLevelItem(item)
        if 0 <= index < len(self._interfaces):
            # Update the interface name
            new_name = item.text(0).strip()
            self._interfaces[index].name = new_name

            # Emit change signal
            self.interfacesChanged.emit()

    def _handle_delete_key(self):
        """Handle Delete/Backspace key press - delete selected interface(s)."""
        # Get selected items
        selected_items = self._tree.selectedItems()
        if not selected_items:
            return

        # Get all top-level selected indices
        indices = []
        for sel_item in selected_items:
            # Find the top-level item
            while sel_item.parent() is not None:
                sel_item = sel_item.parent()

            index = self._tree.indexOfTopLevelItem(sel_item)
            if index >= 0 and index not in indices:
                indices.append(index)

        if not indices:
            return

        # Sort indices in descending order so we can delete from end to start
        indices.sort(reverse=True)

        # Confirm deletion
        if len(indices) == 1:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Delete Interface",
                f"Delete interface {indices[0] + 1}?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            )
        else:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Delete Interfaces",
                f"Delete {len(indices)} interfaces?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # Delete from highest index to lowest to avoid index shifting issues
            for index in indices:
                self.remove_interface(index)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Filter events to allow deselection by clicking on white space."""
        # Handle mouse clicks on viewport
        if obj == self._tree.viewport() and event.type() == QtCore.QEvent.Type.MouseButtonPress:
            mouse_event = event
            # Check if click is on empty space (no item at position)
            item = self._tree.itemAt(mouse_event.pos())
            if item is None:
                # Clicked on white space - deselect all
                self._tree.clearSelection()
                self.interfaceSelected.emit(-1)
                return False  # Let event continue

        return super().eventFilter(obj, event)

    def _rebuild_tree(self):
        """Rebuild the entire tree from the interface list."""
        self._tree.clear()
        self._tree_items.clear()
        self._property_widgets.clear()

        for i, interface in enumerate(self._interfaces):
            item = self._create_tree_item(interface, i)
            self._tree_items.append(item)

            # Get the property widget from the child item
            if item.childCount() > 0:
                child = item.child(0)
                widget = self._tree.itemWidget(child, 0)
                if isinstance(widget, PropertyListWidget):
                    self._property_widgets.append(widget)

    def _move_up(self):
        """Move selected interface up one position."""
        item = self._tree.currentItem()
        if item is None:
            return

        # Get top-level item
        while item.parent() is not None:
            item = item.parent()

        index = self._tree.indexOfTopLevelItem(item)
        if index > 0:
            self.move_interface(index, index - 1)
            # Select the moved item
            self._tree.setCurrentItem(self._tree_items[index - 1])

    def _move_down(self):
        """Move selected interface down one position."""
        item = self._tree.currentItem()
        if item is None:
            return

        # Get top-level item
        while item.parent() is not None:
            item = item.parent()

        index = self._tree.indexOfTopLevelItem(item)
        if 0 <= index < len(self._interfaces) - 1:
            self.move_interface(index, index + 1)
            # Select the moved item
            self._tree.setCurrentItem(self._tree_items[index + 1])

    def _delete_selected(self):
        """Delete the selected interface."""
        item = self._tree.currentItem()
        if item is None:
            return

        # Get top-level item
        while item.parent() is not None:
            item = item.parent()

        index = self._tree.indexOfTopLevelItem(item)
        if index >= 0:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Delete Interface",
                f"Delete interface {index + 1}?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            )

            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.remove_interface(index)

    # Public API

    def add_interface(self, interface: InterfaceDefinition):
        """Add an interface to the panel."""
        self._interfaces.append(interface)
        self._rebuild_tree()
        self.interfacesChanged.emit()

    def remove_interface(self, index: int):
        """Remove interface at specified index."""
        if 0 <= index < len(self._interfaces):
            self._interfaces.pop(index)
            self._rebuild_tree()
            self.interfacesChanged.emit()

    def get_interfaces(self) -> list[InterfaceDefinition]:
        """Get list of all interface definitions."""
        return self._interfaces.copy()

    def set_interfaces(self, interfaces: list[InterfaceDefinition]):
        """Set the complete list of interfaces."""
        self._interfaces = interfaces.copy()
        self._rebuild_tree()

    def clear(self):
        """Remove all interfaces."""
        self._interfaces.clear()
        self._rebuild_tree()
        self.interfacesChanged.emit()

    def get_interface(self, index: int) -> InterfaceDefinition | None:
        """Get interface at specified index."""
        if 0 <= index < len(self._interfaces):
            return self._interfaces[index]
        return None

    def update_interface(self, index: int, interface: InterfaceDefinition):
        """Update interface at specified index."""
        if 0 <= index < len(self._property_widgets):
            self._interfaces[index] = interface
            self._property_widgets[index].update_from_interface(interface)
            self.interfacesChanged.emit()

    def select_interface(self, index: int):
        """Select an interface by index (single selection)."""
        if 0 <= index < len(self._tree_items):
            self._tree.setCurrentItem(self._tree_items[index])
        else:
            self._tree.setCurrentItem(None)

    def select_interfaces(self, indices: list[int]):
        """Select multiple interfaces by indices."""
        # Block signals during programmatic selection
        self._tree.blockSignals(True)

        # Clear selection first
        self._tree.clearSelection()

        # Select all specified items
        for index in indices:
            if 0 <= index < len(self._tree_items):
                self._tree_items[index].setSelected(True)

        # Unblock signals
        self._tree.blockSignals(False)

    def get_selected_index(self) -> int:
        """Get currently selected interface index (backward compatibility)."""
        item = self._tree.currentItem()
        if item is None:
            return -1

        # Get top-level item
        while item.parent() is not None:
            item = item.parent()

        return self._tree.indexOfTopLevelItem(item)

    def get_selected_indices(self) -> list[int]:
        """Get all selected interface indices."""
        selected_items = self._tree.selectedItems()
        indices = []

        for sel_item in selected_items:
            # Find the top-level item
            while sel_item.parent() is not None:
                sel_item = sel_item.parent()

            index = self._tree.indexOfTopLevelItem(sel_item)
            if index >= 0 and index not in indices:
                indices.append(index)

        return sorted(indices)

    def count(self) -> int:
        """Get number of interfaces."""
        return len(self._interfaces)

    def move_interface(self, from_index: int, to_index: int):
        """Move interface from one position to another."""
        if (
            0 <= from_index < len(self._interfaces)
            and 0 <= to_index < len(self._interfaces)
            and from_index != to_index
        ):
            interface = self._interfaces.pop(from_index)
            self._interfaces.insert(to_index, interface)
            self._rebuild_tree()
            self.interfacesChanged.emit()
