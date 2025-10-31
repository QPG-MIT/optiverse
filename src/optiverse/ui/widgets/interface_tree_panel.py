"""Tree-based panel for managing interface properties with collapsible sections."""

from __future__ import annotations

from typing import List, Optional, Dict, Any, Callable
import math

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.interface_definition import InterfaceDefinition
from ...core import interface_types


class InterfaceTreeWidget(QtWidgets.QTreeWidget):
    """Custom QTreeWidget that handles Delete/Backspace keys for interface deletion."""
    
    deleteKeyPressed = QtCore.pyqtSignal()
    
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Override to handle Delete/Backspace keys."""
        # Check if Delete or Backspace key is pressed
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            # Only handle if we're not currently editing an item
            if self.state() != QtWidgets.QAbstractItemView.State.EditingState:
                # Emit signal so parent panel can handle deletion
                self.deleteKeyPressed.emit()
                event.accept()
                return
        
        # Pass to parent for all other keys or when editing
        super().keyPressEvent(event)


class EditableLabel(QtWidgets.QWidget):
    """
    A label that becomes editable when double-clicked.
    More compact than always-visible text fields.
    """
    valueChanged = QtCore.pyqtSignal(str)
    
    def __init__(self, initial_value: str = "", parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._value = initial_value
        self._editing = False
        
        # Create layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Label for display mode
        self._label = QtWidgets.QLabel(initial_value)
        self._label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self._label.setStyleSheet("QLabel { padding: 2px; }")
        layout.addWidget(self._label)
        
        # Line edit for editing mode (initially hidden)
        self._edit = QtWidgets.QLineEdit(initial_value)
        self._edit.hide()
        self._edit.editingFinished.connect(self._finish_editing)
        self._edit.returnPressed.connect(self._finish_editing)
        layout.addWidget(self._edit)
        
        # Set size policy
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed
        )
    
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        """Start editing on double-click."""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._start_editing()
    
    def _start_editing(self):
        """Switch to edit mode."""
        if self._editing:
            return
        
        self._editing = True
        self._label.hide()
        self._edit.setText(self._value)
        self._edit.show()
        self._edit.setFocus()
        self._edit.selectAll()
    
    def _finish_editing(self):
        """Finish editing and switch back to label mode."""
        if not self._editing:
            return
        
        self._editing = False
        new_value = self._edit.text()
        
        # Only update if value changed
        if new_value != self._value:
            self._value = new_value
            self._label.setText(new_value)
            self.valueChanged.emit(new_value)
        
        self._edit.hide()
        self._label.show()
    
    def setText(self, text: str):
        """Set the text value."""
        self._value = text
        self._label.setText(text)
        if self._editing:
            self._edit.setText(text)
    
    def text(self) -> str:
        """Get the current text value."""
        return self._value
    
    def setPlaceholderText(self, text: str):
        """Set placeholder text for edit mode."""
        self._edit.setPlaceholderText(text)


class ColoredCircleLabel(QtWidgets.QLabel):
    """A small colored circle indicator."""
    
    def __init__(self, color: str, size: int = 12, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border: 1px solid rgba(0, 0, 0, 0.3);
                border-radius: {size // 2}px;
            }}
        """)


class PropertyListWidget(QtWidgets.QWidget):
    """Simple vertical property list for an interface."""
    
    propertyChanged = QtCore.pyqtSignal()
    
    def __init__(self, interface: InterfaceDefinition, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.interface = interface
        self._updating = False
        self._property_widgets: Dict[str, QtWidgets.QWidget] = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the simple vertical property layout."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 3, 5, 3)
        layout.setSpacing(2)
        
        # Create form layout for properties
        self._form = QtWidgets.QFormLayout()
        self._form.setContentsMargins(0, 0, 0, 0)
        self._form.setVerticalSpacing(3)  # Reduced from 5 to 3
        self._form.setHorizontalSpacing(10)  # Reduced from 15 to 10
        self._form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)  # Left-aligned
        self._form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Populate form
        self._populate_form()
        
        layout.addLayout(self._form)
        layout.addStretch()  # Push content to top
        
        # Set proper size policy for smooth scrolling
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Minimum
        )
    
    def _populate_form(self):
        """Populate the form with properties stacked vertically."""
        # Type row (dropdown/combobox)
        type_combo = QtWidgets.QComboBox()
        for type_name in interface_types.get_all_type_names():
            display_name = interface_types.get_type_display_name(type_name)
            emoji = interface_types.get_type_emoji(type_name)
            type_combo.addItem(f"{emoji} {display_name}", type_name)
        
        # Set current type
        idx = type_combo.findData(self.interface.element_type)
        if idx >= 0:
            type_combo.setCurrentIndex(idx)
        
        type_combo.currentIndexChanged.connect(self._on_type_changed)
        self._property_widgets["type"] = type_combo
        self._form.addRow("Type:", type_combo)
        
        # Coordinate fields with double-click-to-edit labels
        for coord_name, value in [("X₁", self.interface.x1_mm), ("Y₁", self.interface.y1_mm), 
                                    ("X₂", self.interface.x2_mm), ("Y₂", self.interface.y2_mm)]:
            editable_label = EditableLabel(f"{value:.3f}")
            editable_label.setPlaceholderText("0.000")
            editable_label.valueChanged.connect(lambda val, c=coord_name: self._on_coordinate_text_changed(c))
            self._property_widgets[coord_name] = editable_label
            self._form.addRow(f"{coord_name} (mm):", editable_label)
        
        # Type-specific properties (no separator)
        props = interface_types.get_type_properties(self.interface.element_type)
        if props:
            for prop_name in props:
                self._add_property_field(prop_name)
    
    def _add_property_field(self, prop_name: str):
        """Add a type-specific property field."""
        value = getattr(self.interface, prop_name, None)
        if value is None:
            return
        
        label = interface_types.get_property_label(self.interface.element_type, prop_name)
        unit = interface_types.get_property_unit(self.interface.element_type, prop_name)
        
        # Add unit to label if present
        label_text = f"{label} ({unit})" if unit else f"{label}"
        
        if isinstance(value, bool):
            widget = QtWidgets.QCheckBox()
            widget.setChecked(value)
            widget.toggled.connect(lambda checked: self._on_property_changed(prop_name, checked))
            self._property_widgets[prop_name] = widget
            self._form.addRow(f"{label_text}:", widget)
        
        elif isinstance(value, (int, float)):
            # Use double-click-to-edit label
            widget = EditableLabel(f"{value:.3f}")
            widget.setPlaceholderText("0.000")
            widget.valueChanged.connect(lambda val, p=prop_name: self._on_numeric_property_changed(p))
            self._property_widgets[prop_name] = widget
            
            # Add colored circle indicator for n1 and n2 (refractive index properties)
            if prop_name in ('n1', 'n2'):
                # Create horizontal layout with color indicator and value
                h_layout = QtWidgets.QHBoxLayout()
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(5)
                
                # Add colored circle (yellow for n1, purple for n2)
                if prop_name == 'n1':
                    circle = ColoredCircleLabel('#FFD700', size=10)  # Yellow for n₁
                    circle.setToolTip("n₁ side (yellow)")
                else:  # n2
                    circle = ColoredCircleLabel('#9370DB', size=10)  # Purple for n₂
                    circle.setToolTip("n₂ side (purple)")
                
                h_layout.addWidget(circle)
                h_layout.addWidget(widget, 1)  # Stretch factor 1
                
                # Create container widget
                container = QtWidgets.QWidget()
                container.setLayout(h_layout)
                
                self._form.addRow(f"{label_text}:", container)
            else:
                self._form.addRow(f"{label_text}:", widget)
        
        elif isinstance(value, str):
            if prop_name == 'pass_type':
                widget = QtWidgets.QComboBox()
                widget.addItems(['longpass', 'shortpass'])
                idx = widget.findText(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                widget.currentTextChanged.connect(lambda v: self._on_property_changed(prop_name, v))
                self._property_widgets[prop_name] = widget
            else:
                # Use double-click-to-edit label for string properties
                widget = EditableLabel(value)
                widget.valueChanged.connect(lambda v, p=prop_name: self._on_property_changed(p, v))
                self._property_widgets[prop_name] = widget
            self._form.addRow(f"{label_text}:", widget)
    
    def _on_coordinate_text_changed(self, coord_name: str):
        """Handle coordinate text field changes."""
        if self._updating:
            return
        
        line_edit = self._property_widgets.get(coord_name)
        if not line_edit:
            return
        
        try:
            value = float(line_edit.text())
            
            if coord_name == "X₁":
                self.interface.x1_mm = value
            elif coord_name == "X₂":
                self.interface.x2_mm = value
            elif coord_name == "Y₁":
                self.interface.y1_mm = value
            elif coord_name == "Y₂":
                self.interface.y2_mm = value
            
            # Format the text nicely
            line_edit.setText(f"{value:.3f}")
            self.propertyChanged.emit()
        
        except ValueError:
            # Invalid number - revert to current interface value
            if coord_name == "X₁":
                line_edit.setText(f"{self.interface.x1_mm:.3f}")
            elif coord_name == "X₂":
                line_edit.setText(f"{self.interface.x2_mm:.3f}")
            elif coord_name == "Y₁":
                line_edit.setText(f"{self.interface.y1_mm:.3f}")
            elif coord_name == "Y₂":
                line_edit.setText(f"{self.interface.y2_mm:.3f}")
    
    def _on_type_changed(self):
        """Handle type changes from dropdown - rebuild to show new properties."""
        if self._updating:
            return
        
        type_combo = self._property_widgets.get("type")
        if not type_combo:
            return
        
        new_type = type_combo.currentData()
        if new_type and new_type != self.interface.element_type:
            old_type = self.interface.element_type
            self.interface.element_type = new_type
            
            # Rebuild the form to show type-specific properties
            self._rebuild_form()
            
            self.propertyChanged.emit()
    
    def _rebuild_form(self):
        """Rebuild the entire form (used when type changes)."""
        # Clear existing form
        while self._form.count() > 0:
            item = self._form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._property_widgets.clear()
        
        # Repopulate with new properties
        self._populate_form()
    
    def _on_numeric_property_changed(self, prop_name: str):
        """Handle numeric property text field changes."""
        if self._updating:
            return
        
        line_edit = self._property_widgets.get(prop_name)
        if not line_edit:
            return
        
        try:
            value = float(line_edit.text())
            
            # Validate range
            min_val, max_val = interface_types.get_property_range(self.interface.element_type, prop_name)
            if value < min_val or value > max_val:
                # Out of range - revert
                current_value = getattr(self.interface, prop_name, 0.0)
                line_edit.setText(f"{current_value:.3f}")
                return
            
            setattr(self.interface, prop_name, value)
            
            # Format the text nicely
            line_edit.setText(f"{value:.3f}")
            self.propertyChanged.emit()
        
        except ValueError:
            # Invalid number - revert to current interface value
            current_value = getattr(self.interface, prop_name, 0.0)
            line_edit.setText(f"{current_value:.3f}")
    
    def _on_property_changed(self, prop_name: str, value: Any):
        """Handle property value changes (for non-numeric properties)."""
        if self._updating:
            return
        
        setattr(self.interface, prop_name, value)
        self.propertyChanged.emit()
    
    def update_from_interface(self, interface: InterfaceDefinition):
        """Update all widgets from interface data."""
        self._updating = True
        
        try:
            self.interface = interface
            
            # Update type combobox
            if "type" in self._property_widgets:
                type_combo = self._property_widgets["type"]
                if isinstance(type_combo, QtWidgets.QComboBox):
                    idx = type_combo.findData(interface.element_type)
                    if idx >= 0:
                        type_combo.setCurrentIndex(idx)
            
            # Update coordinate text fields
            if "X₁" in self._property_widgets:
                self._property_widgets["X₁"].setText(f"{interface.x1_mm:.3f}")
            if "X₂" in self._property_widgets:
                self._property_widgets["X₂"].setText(f"{interface.x2_mm:.3f}")
            if "Y₁" in self._property_widgets:
                self._property_widgets["Y₁"].setText(f"{interface.y1_mm:.3f}")
            if "Y₂" in self._property_widgets:
                self._property_widgets["Y₂"].setText(f"{interface.y2_mm:.3f}")
            
            # Update other properties
            for prop_name, widget in self._property_widgets.items():
                if prop_name in ["X₁", "X₂", "Y₁", "Y₂", "type"]:
                    continue
                
                value = getattr(interface, prop_name, None)
                if value is None:
                    continue
                
                if isinstance(widget, QtWidgets.QCheckBox):
                    widget.setChecked(value)
                elif isinstance(widget, QtWidgets.QComboBox):
                    idx = widget.findData(str(value)) if hasattr(widget, 'findData') else widget.findText(str(value))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                elif isinstance(widget, (QtWidgets.QLineEdit, EditableLabel)):
                    # Format numeric values, keep strings as-is
                    if isinstance(value, (int, float)):
                        widget.setText(f"{value:.3f}")
                    else:
                        widget.setText(str(value))
        
        finally:
            self._updating = False


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
    
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        
        self._interfaces: List[InterfaceDefinition] = []
        self._tree_items: List[QtWidgets.QTreeWidgetItem] = []
        self._property_widgets: List[PropertyListWidget] = []
        
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
        self._tree.setStyleSheet("""
            QTreeWidget::item:selected {
                background-color: #d0d0d0;
                color: black;
            }
        """)
        
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
    
    def _create_tree_item(self, interface: InterfaceDefinition, index: int) -> QtWidgets.QTreeWidgetItem:
        """Create a tree item for an interface."""
        item = QtWidgets.QTreeWidgetItem()
        
        # Use custom name if set, otherwise default to "Interface N"
        display_name = interface.name if interface.name else f"Interface {index + 1}"
        item.setText(0, display_name)
        
        # Make item editable (for renaming with double-click)
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEditable)
        
        # Store interface index in item data for later retrieval
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, index)
        
        # Create property list widget
        prop_widget = PropertyListWidget(interface)
        prop_widget.propertyChanged.connect(self.interfacesChanged.emit)
        
        self._tree.addTopLevelItem(item)
        
        # Add child item to hold the widget
        child_item = QtWidgets.QTreeWidgetItem(item)
        self._tree.setItemWidget(child_item, 0, prop_widget)
        
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
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
        else:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Delete Interfaces",
                f"Delete {len(indices)} interfaces?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
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
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
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
    
    def get_interfaces(self) -> List[InterfaceDefinition]:
        """Get list of all interface definitions."""
        return self._interfaces.copy()
    
    def set_interfaces(self, interfaces: List[InterfaceDefinition]):
        """Set the complete list of interfaces."""
        self._interfaces = interfaces.copy()
        self._rebuild_tree()
    
    def clear(self):
        """Remove all interfaces."""
        self._interfaces.clear()
        self._rebuild_tree()
        self.interfacesChanged.emit()
    
    def get_interface(self, index: int) -> Optional[InterfaceDefinition]:
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
    
    def select_interfaces(self, indices: List[int]):
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
    
    def get_selected_indices(self) -> List[int]:
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
        if (0 <= from_index < len(self._interfaces) and 
            0 <= to_index < len(self._interfaces) and 
            from_index != to_index):
            
            interface = self._interfaces.pop(from_index)
            self._interfaces.insert(to_index, interface)
            self._rebuild_tree()
            self.interfacesChanged.emit()

