"""Table-based panel for managing interface properties."""

from __future__ import annotations

from typing import List, Optional, Dict, Any
import math

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.interface_definition import InterfaceDefinition
from ...core import interface_types


class PropertyEditorDialog(QtWidgets.QDialog):
    """Dialog for editing type-specific properties of an interface."""
    
    def __init__(self, interface: InterfaceDefinition, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.interface = interface
        self._property_widgets: Dict[str, QtWidgets.QWidget] = {}
        
        self.setWindowTitle(f"Properties - {interface.get_label()}")
        self.setModal(True)
        self.resize(400, 500)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Scroll area for properties
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QtWidgets.QWidget()
        form_layout = QtWidgets.QFormLayout(content)
        
        # Get properties for this element type
        props = interface_types.get_type_properties(self.interface.element_type)
        
        for prop_name in props:
            widget = self._create_property_widget(prop_name)
            if widget:
                label = interface_types.get_property_label(self.interface.element_type, prop_name)
                form_layout.addRow(label + ":", widget)
                self._property_widgets[prop_name] = widget
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
    
    def _create_property_widget(self, prop_name: str) -> Optional[QtWidgets.QWidget]:
        """Create a widget for a specific property."""
        value = getattr(self.interface, prop_name, None)
        if value is None:
            return None
        
        # Handle different property types
        if isinstance(value, bool):
            widget = QtWidgets.QCheckBox()
            widget.setChecked(value)
            return widget
        
        elif isinstance(value, (int, float)):
            widget = QtWidgets.QDoubleSpinBox()
            min_val, max_val = interface_types.get_property_range(self.interface.element_type, prop_name)
            widget.setRange(min_val, max_val)
            widget.setDecimals(3)
            unit = interface_types.get_property_unit(self.interface.element_type, prop_name)
            if unit:
                widget.setSuffix(f" {unit}")
            widget.setValue(value)
            return widget
        
        elif isinstance(value, str):
            if prop_name == 'pass_type':
                widget = QtWidgets.QComboBox()
                widget.addItems(['longpass', 'shortpass'])
                idx = widget.findText(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                return widget
            else:
                widget = QtWidgets.QLineEdit()
                widget.setText(value)
                return widget
        
        return None
    
    def get_updated_interface(self) -> InterfaceDefinition:
        """Get the interface with updated property values."""
        for prop_name, widget in self._property_widgets.items():
            if isinstance(widget, QtWidgets.QCheckBox):
                setattr(self.interface, prop_name, widget.isChecked())
            elif isinstance(widget, QtWidgets.QDoubleSpinBox):
                setattr(self.interface, prop_name, widget.value())
            elif isinstance(widget, QtWidgets.QComboBox):
                setattr(self.interface, prop_name, widget.currentText())
            elif isinstance(widget, QtWidgets.QLineEdit):
                setattr(self.interface, prop_name, widget.text())
        
        return self.interface


class InterfaceTablePanel(QtWidgets.QWidget):
    """
    Table-based panel for managing optical interfaces.
    
    Features:
    - Compact table view with all interfaces visible
    - Direct inline editing of coordinates
    - Quick type selection via dropdown
    - Properties button for type-specific settings
    - Row selection and reordering
    - Color-coded interface types
    
    Signals:
        interfacesChanged: Emitted when interfaces list changes
        interfaceSelected: Emitted when an interface is selected (index)
    """
    
    interfacesChanged = QtCore.pyqtSignal()
    interfaceSelected = QtCore.pyqtSignal(int)
    
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        
        self._interfaces: List[InterfaceDefinition] = []
        self._updating = False
        
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
        
        # Table
        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "#", "Type", "x₁ (mm)", "y₁ (mm)", "x₂ (mm)", "y₂ (mm)", "Info", "Props"
        ])
        
        # Configure table
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        
        # Set column widths
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)  # #
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)  # Type
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Fixed)  # x1
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Fixed)  # y1
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Fixed)  # x2
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.Fixed)  # y2
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeMode.Stretch)  # Info
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeMode.Fixed)  # Props
        
        self._table.setColumnWidth(0, 35)  # #
        self._table.setColumnWidth(1, 150)  # Type
        self._table.setColumnWidth(2, 80)  # x1
        self._table.setColumnWidth(3, 80)  # y1
        self._table.setColumnWidth(4, 80)  # x2
        self._table.setColumnWidth(5, 80)  # y2
        self._table.setColumnWidth(7, 60)  # Props
        
        # Connect signals
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.cellChanged.connect(self._on_cell_changed)
        
        layout.addWidget(self._table, 1)
        
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
        
        # Set default geometry (centered, horizontal line)
        half_length = 10.0  # mm
        interface.x1_mm = -half_length
        interface.y1_mm = 0.0
        interface.x2_mm = half_length
        interface.y2_mm = 0.0
        
        self.add_interface(interface)
    
    def _update_table(self):
        """Refresh the entire table from the interface list."""
        self._updating = True
        
        try:
            self._table.setRowCount(len(self._interfaces))
            
            for row, interface in enumerate(self._interfaces):
                self._populate_row(row, interface)
        
        finally:
            self._updating = False
    
    def _populate_row(self, row: int, interface: InterfaceDefinition):
        """Populate a table row with interface data."""
        # Column 0: Index
        index_item = QtWidgets.QTableWidgetItem(str(row + 1))
        index_item.setFlags(index_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        index_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 0, index_item)
        
        # Column 1: Type (ComboBox)
        type_combo = QtWidgets.QComboBox()
        for type_name in interface_types.get_all_type_names():
            display_name = interface_types.get_type_display_name(type_name)
            type_combo.addItem(display_name, type_name)
        
        idx = type_combo.findData(interface.element_type)
        if idx >= 0:
            type_combo.setCurrentIndex(idx)
        
        type_combo.currentIndexChanged.connect(lambda: self._on_type_changed(row))
        self._table.setCellWidget(row, 1, type_combo)
        
        # Columns 2-5: Coordinates
        coords = [interface.x1_mm, interface.y1_mm, interface.x2_mm, interface.y2_mm]
        for col, value in enumerate(coords, start=2):
            item = QtWidgets.QTableWidgetItem(f"{value:.3f}")
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, col, item)
        
        # Column 6: Info (length, angle)
        length = interface.length_mm()
        angle = interface.angle_deg()
        info_item = QtWidgets.QTableWidgetItem(f"L={length:.1f}mm, θ={angle:.0f}°")
        info_item.setFlags(info_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        info_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        
        # Set background color based on interface type
        r, g, b = interface.get_color()
        info_item.setBackground(QtGui.QColor(r, g, b, 50))  # Semi-transparent
        self._table.setItem(row, 6, info_item)
        
        # Column 7: Properties button
        props_btn = QtWidgets.QPushButton("...")
        props_btn.setToolTip("Edit type-specific properties")
        props_btn.clicked.connect(lambda: self._edit_properties(row))
        self._table.setCellWidget(row, 7, props_btn)
    
    def _on_selection_changed(self):
        """Handle table selection changes."""
        if self._updating:
            return
        
        selected = self._table.selectedItems()
        if selected:
            row = selected[0].row()
            self.interfaceSelected.emit(row)
        else:
            self.interfaceSelected.emit(-1)
    
    def _on_cell_changed(self, row: int, col: int):
        """Handle cell value changes (coordinates)."""
        if self._updating or row >= len(self._interfaces):
            return
        
        # Only handle coordinate columns (2-5)
        if 2 <= col <= 5:
            try:
                item = self._table.item(row, col)
                if item is None:
                    return
                
                value = float(item.text())
                interface = self._interfaces[row]
                
                if col == 2:
                    interface.x1_mm = value
                elif col == 3:
                    interface.y1_mm = value
                elif col == 4:
                    interface.x2_mm = value
                elif col == 5:
                    interface.y2_mm = value
                
                # Update info column
                self._updating = True
                length = interface.length_mm()
                angle = interface.angle_deg()
                info_item = self._table.item(row, 6)
                if info_item:
                    info_item.setText(f"L={length:.1f}mm, θ={angle:.0f}°")
                self._updating = False
                
                self.interfacesChanged.emit()
            
            except ValueError:
                # Invalid number, revert
                self._populate_row(row, self._interfaces[row])
    
    def _on_type_changed(self, row: int):
        """Handle element type change."""
        if self._updating or row >= len(self._interfaces):
            return
        
        type_combo = self._table.cellWidget(row, 1)
        if isinstance(type_combo, QtWidgets.QComboBox):
            new_type = type_combo.currentData()
            if new_type:
                self._interfaces[row].element_type = new_type
                
                # Update info column color
                self._updating = True
                r, g, b = self._interfaces[row].get_color()
                info_item = self._table.item(row, 6)
                if info_item:
                    info_item.setBackground(QtGui.QColor(r, g, b, 50))
                self._updating = False
                
                self.interfacesChanged.emit()
    
    def _edit_properties(self, row: int):
        """Open property editor dialog for an interface."""
        if row >= len(self._interfaces):
            return
        
        interface = self._interfaces[row]
        dialog = PropertyEditorDialog(interface, self)
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._interfaces[row] = dialog.get_updated_interface()
            
            # Update info column (properties might affect display)
            self._updating = True
            info_item = self._table.item(row, 6)
            if info_item:
                length = interface.length_mm()
                angle = interface.angle_deg()
                info_item.setText(f"L={length:.1f}mm, θ={angle:.0f}°")
                r, g, b = interface.get_color()
                info_item.setBackground(QtGui.QColor(r, g, b, 50))
            self._updating = False
            
            self.interfacesChanged.emit()
    
    def _move_up(self):
        """Move selected interface up one position."""
        row = self._table.currentRow()
        if row > 0:
            self.move_interface(row, row - 1)
            self._table.selectRow(row - 1)
    
    def _move_down(self):
        """Move selected interface down one position."""
        row = self._table.currentRow()
        if 0 <= row < len(self._interfaces) - 1:
            self.move_interface(row, row + 1)
            self._table.selectRow(row + 1)
    
    def _delete_selected(self):
        """Delete the selected interface."""
        row = self._table.currentRow()
        if row >= 0:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Delete Interface",
                f"Delete interface {row + 1}?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.remove_interface(row)
    
    # Public API
    
    def add_interface(self, interface: InterfaceDefinition):
        """Add an interface to the panel."""
        self._interfaces.append(interface)
        self._update_table()
        self.interfacesChanged.emit()
    
    def remove_interface(self, index: int):
        """Remove interface at specified index."""
        if 0 <= index < len(self._interfaces):
            self._interfaces.pop(index)
            self._update_table()
            self.interfacesChanged.emit()
    
    def get_interfaces(self) -> List[InterfaceDefinition]:
        """Get list of all interface definitions."""
        return self._interfaces.copy()
    
    def set_interfaces(self, interfaces: List[InterfaceDefinition]):
        """Set the complete list of interfaces."""
        self._interfaces = interfaces.copy()
        self._update_table()
    
    def clear(self):
        """Remove all interfaces."""
        self._interfaces.clear()
        self._update_table()
        self.interfacesChanged.emit()
    
    def get_interface(self, index: int) -> Optional[InterfaceDefinition]:
        """Get interface at specified index."""
        if 0 <= index < len(self._interfaces):
            return self._interfaces[index]
        return None
    
    def update_interface(self, index: int, interface: InterfaceDefinition):
        """Update interface at specified index."""
        if 0 <= index < len(self._interfaces):
            self._interfaces[index] = interface
            self._populate_row(index, interface)
            self.interfacesChanged.emit()
    
    def select_interface(self, index: int):
        """Select an interface by index."""
        if 0 <= index < len(self._interfaces):
            self._table.selectRow(index)
        else:
            self._table.clearSelection()
    
    def get_selected_index(self) -> int:
        """Get currently selected interface index."""
        row = self._table.currentRow()
        return row if row >= 0 else -1
    
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
            self._update_table()
            self.interfacesChanged.emit()

