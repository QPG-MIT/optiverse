"""
Simple Excel-like table for managing interfaces - minimal complexity.

Just a plain table where you can:
- Click and type coordinates
- Double-click to edit properties
- Drag to reorder rows
"""

from __future__ import annotations

from typing import List, Optional
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.interface_definition import InterfaceDefinition
from ...core import interface_types


class SimpleInterfaceTable(QtWidgets.QWidget):
    """
    Excel-like interface table with minimal UI complexity.
    
    Features:
    - Plain text cells (click and type)
    - Simple double-click for properties
    - Clean, compact layout
    - No spinboxes, no embedded widgets
    
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
        
        # Simple header with add button
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        label = QtWidgets.QLabel("Interfaces")
        label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        header_layout.addWidget(label)
        
        header_layout.addStretch()
        
        # Simple add button with menu
        self._add_btn = QtWidgets.QPushButton("+ Add")
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
        
        # Simple table - no embedded widgets
        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "#", "Type", "X₁", "Y₁", "X₂", "Y₂", "Info"
        ])
        
        # Table appearance
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        
        # Column widths
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(0, 30)   # #
        self._table.setColumnWidth(1, 120)  # Type
        self._table.setColumnWidth(2, 70)   # X1
        self._table.setColumnWidth(3, 70)   # Y1
        self._table.setColumnWidth(4, 70)   # X2
        self._table.setColumnWidth(5, 70)   # Y2
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeMode.Stretch)  # Info stretches
        
        # Connect signals
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.cellChanged.connect(self._on_cell_changed)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
        layout.addWidget(self._table, 1)
        
        # Simple button bar
        btn_layout = QtWidgets.QHBoxLayout()
        
        self._up_btn = QtWidgets.QPushButton("↑")
        self._up_btn.setFixedWidth(40)
        self._up_btn.setToolTip("Move Up")
        self._up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(self._up_btn)
        
        self._down_btn = QtWidgets.QPushButton("↓")
        self._down_btn.setFixedWidth(40)
        self._down_btn.setToolTip("Move Down")
        self._down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(self._down_btn)
        
        btn_layout.addStretch()
        
        self._delete_btn = QtWidgets.QPushButton("Delete")
        self._delete_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self._delete_btn)
        
        layout.addLayout(btn_layout)
    
    def _add_interface(self, element_type: str):
        """Add a new interface of specified type."""
        interface = InterfaceDefinition(element_type=element_type)
        
        # Default geometry
        half_length = 10.0
        interface.x1_mm = -half_length
        interface.y1_mm = 0.0
        interface.x2_mm = half_length
        interface.y2_mm = 0.0
        
        self.add_interface(interface)
    
    def _update_table(self):
        """Refresh the entire table from interfaces."""
        self._updating = True
        
        try:
            self._table.setRowCount(len(self._interfaces))
            
            for row, interface in enumerate(self._interfaces):
                self._populate_row(row, interface)
        
        finally:
            self._updating = False
    
    def _populate_row(self, row: int, interface: InterfaceDefinition):
        """Populate a table row - simple text cells only."""
        
        # Column 0: Index (read-only)
        item = QtWidgets.QTableWidgetItem(str(row + 1))
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 0, item)
        
        # Column 1: Type (editable text, double-click to change)
        display_name = interface_types.get_type_display_name(interface.element_type)
        emoji = interface_types.get_type_emoji(interface.element_type)
        item = QtWidgets.QTableWidgetItem(f"{emoji} {display_name}")
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, interface.element_type)
        self._table.setItem(row, 1, item)
        
        # Columns 2-5: Coordinates (editable text)
        coords = [interface.x1_mm, interface.y1_mm, interface.x2_mm, interface.y2_mm]
        for col, value in enumerate(coords, start=2):
            item = QtWidgets.QTableWidgetItem(f"{value:.3f}")
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, col, item)
        
        # Column 6: Info (read-only, color-coded)
        length = interface.length_mm()
        angle = interface.angle_deg()
        item = QtWidgets.QTableWidgetItem(f"L={length:.1f}mm, θ={angle:.0f}° (double-click for props)")
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        
        # Color-code by type
        r, g, b = interface.get_color()
        item.setBackground(QtGui.QColor(r, g, b, 40))
        self._table.setItem(row, 6, item)
    
    def _on_selection_changed(self):
        """Handle row selection."""
        if self._updating:
            return
        
        selected = self._table.selectedItems()
        if selected:
            row = selected[0].row()
            self.interfaceSelected.emit(row)
    
    def _on_cell_changed(self, row: int, col: int):
        """Handle cell edit (coordinates only)."""
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
                
                # Update coordinate
                if col == 2:
                    interface.x1_mm = value
                elif col == 3:
                    interface.y1_mm = value
                elif col == 4:
                    interface.x2_mm = value
                elif col == 5:
                    interface.y2_mm = value
                
                # Update info
                self._updating = True
                length = interface.length_mm()
                angle = interface.angle_deg()
                info_item = self._table.item(row, 6)
                if info_item:
                    info_item.setText(f"L={length:.1f}mm, θ={angle:.0f}° (double-click for props)")
                self._updating = False
                
                self.interfacesChanged.emit()
            
            except ValueError:
                # Invalid number - revert
                self._populate_row(row, self._interfaces[row])
    
    def _on_cell_double_clicked(self, row: int, col: int):
        """Handle double-click to edit type or properties."""
        if row >= len(self._interfaces):
            return
        
        # Double-click on Type column - change type
        if col == 1:
            self._change_type(row)
        
        # Double-click on Info column - edit properties
        elif col == 6:
            self._edit_properties(row)
    
    def _change_type(self, row: int):
        """Change interface type via simple menu."""
        if row >= len(self._interfaces):
            return
        
        interface = self._interfaces[row]
        
        # Show menu at cursor
        menu = QtWidgets.QMenu(self)
        for type_name in interface_types.get_all_type_names():
            display_name = interface_types.get_type_display_name(type_name)
            emoji = interface_types.get_type_emoji(type_name)
            action = menu.addAction(f"{emoji} {display_name}")
            action.setData(type_name)
            if type_name == interface.element_type:
                action.setCheckable(True)
                action.setChecked(True)
        
        action = menu.exec(QtGui.QCursor.pos())
        if action:
            new_type = action.data()
            if new_type and new_type != interface.element_type:
                interface.element_type = new_type
                self._populate_row(row, interface)
                self.interfacesChanged.emit()
    
    def _edit_properties(self, row: int):
        """Edit type-specific properties in simple dialog."""
        if row >= len(self._interfaces):
            return
        
        interface = self._interfaces[row]
        props = interface_types.get_type_properties(interface.element_type)
        
        if not props:
            QtWidgets.QMessageBox.information(
                self,
                "No Properties",
                f"{interface_types.get_type_display_name(interface.element_type)} has no additional properties."
            )
            return
        
        # Create simple property dialog
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"Properties - {interface.get_label()}")
        dialog.setModal(True)
        dialog.resize(350, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        form = QtWidgets.QFormLayout()
        
        widgets = {}
        
        for prop_name in props:
            value = getattr(interface, prop_name, None)
            if value is None:
                continue
            
            label = interface_types.get_property_label(interface.element_type, prop_name)
            
            if isinstance(value, bool):
                widget = QtWidgets.QCheckBox()
                widget.setChecked(value)
                widgets[prop_name] = widget
                form.addRow(label + ":", widget)
            
            elif isinstance(value, (int, float)):
                widget = QtWidgets.QDoubleSpinBox()
                min_val, max_val = interface_types.get_property_range(interface.element_type, prop_name)
                widget.setRange(min_val, max_val)
                widget.setDecimals(3)
                unit = interface_types.get_property_unit(interface.element_type, prop_name)
                if unit:
                    widget.setSuffix(f" {unit}")
                widget.setValue(value)
                widgets[prop_name] = widget
                form.addRow(label + ":", widget)
            
            elif isinstance(value, str):
                if prop_name == 'pass_type':
                    widget = QtWidgets.QComboBox()
                    widget.addItems(['longpass', 'shortpass'])
                    idx = widget.findText(value)
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                    widgets[prop_name] = widget
                else:
                    widget = QtWidgets.QLineEdit()
                    widget.setText(value)
                    widgets[prop_name] = widget
                form.addRow(label + ":", widget)
        
        layout.addLayout(form)
        
        # Buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            # Apply changes
            for prop_name, widget in widgets.items():
                if isinstance(widget, QtWidgets.QCheckBox):
                    setattr(interface, prop_name, widget.isChecked())
                elif isinstance(widget, QtWidgets.QDoubleSpinBox):
                    setattr(interface, prop_name, widget.value())
                elif isinstance(widget, QtWidgets.QComboBox):
                    setattr(interface, prop_name, widget.currentText())
                elif isinstance(widget, QtWidgets.QLineEdit):
                    setattr(interface, prop_name, widget.text())
            
            self._populate_row(row, interface)
            self.interfacesChanged.emit()
    
    def _move_up(self):
        """Move selected row up."""
        row = self._table.currentRow()
        if row > 0:
            self.move_interface(row, row - 1)
            self._table.selectRow(row - 1)
    
    def _move_down(self):
        """Move selected row down."""
        row = self._table.currentRow()
        if 0 <= row < len(self._interfaces) - 1:
            self.move_interface(row, row + 1)
            self._table.selectRow(row + 1)
    
    def _delete_selected(self):
        """Delete selected row."""
        row = self._table.currentRow()
        if row >= 0:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Delete",
                f"Delete interface {row + 1}?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.remove_interface(row)
    
    # Public API (same as other panels)
    
    def add_interface(self, interface: InterfaceDefinition):
        """Add an interface."""
        self._interfaces.append(interface)
        self._update_table()
        self.interfacesChanged.emit()
    
    def remove_interface(self, index: int):
        """Remove interface at index."""
        if 0 <= index < len(self._interfaces):
            self._interfaces.pop(index)
            self._update_table()
            self.interfacesChanged.emit()
    
    def get_interfaces(self) -> List[InterfaceDefinition]:
        """Get all interfaces."""
        return self._interfaces.copy()
    
    def set_interfaces(self, interfaces: List[InterfaceDefinition]):
        """Set all interfaces."""
        self._interfaces = interfaces.copy()
        self._update_table()
    
    def clear(self):
        """Clear all interfaces."""
        self._interfaces.clear()
        self._update_table()
        self.interfacesChanged.emit()
    
    def get_interface(self, index: int) -> Optional[InterfaceDefinition]:
        """Get interface at index."""
        if 0 <= index < len(self._interfaces):
            return self._interfaces[index]
        return None
    
    def update_interface(self, index: int, interface: InterfaceDefinition):
        """Update interface at index."""
        if 0 <= index < len(self._interfaces):
            self._interfaces[index] = interface
            self._populate_row(index, interface)
            self.interfacesChanged.emit()
    
    def select_interface(self, index: int):
        """Select interface by index."""
        if 0 <= index < len(self._interfaces):
            self._table.selectRow(index)
        else:
            self._table.clearSelection()
    
    def get_selected_index(self) -> int:
        """Get selected index."""
        row = self._table.currentRow()
        return row if row >= 0 else -1
    
    def count(self) -> int:
        """Get interface count."""
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

