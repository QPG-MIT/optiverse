"""Panel for managing multiple interface widgets."""

from __future__ import annotations

from typing import List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.interface_definition import InterfaceDefinition
from ...core import interface_types
from .collapsible_interface_widget import CollapsibleInterfaceWidget


class InterfacePropertiesPanel(QtWidgets.QWidget):
    """
    Panel containing a list of CollapsibleInterfaceWidget instances.
    
    Features:
    - Scrollable list of interface widgets
    - Add/remove interfaces
    - Reorder interfaces (drag and drop)
    - Selection synchronization with canvas
    - Bulk operations
    
    Signals:
        interfacesChanged: Emitted when interfaces list changes
        interfaceSelected: Emitted when an interface is selected (index)
    """
    
    interfacesChanged = QtCore.pyqtSignal()
    interfaceSelected = QtCore.pyqtSignal(int)
    
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        
        self._interface_widgets: List[CollapsibleInterfaceWidget] = []
        self._selected_index = -1
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with label and add button
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        label = QtWidgets.QLabel("Interfaces")
        label.setStyleSheet("font-weight: normal; font-size: 10pt;")  # Not bold per requirements
        header_layout.addWidget(label)
        
        header_layout.addStretch()
        
        # Add interface dropdown button
        self._add_btn = QtWidgets.QPushButton("Add Interface")
        self._add_menu = QtWidgets.QMenu(self)
        
        # Add menu items for each interface type
        for type_name in interface_types.get_all_type_names():
            display_name = interface_types.get_type_display_name(type_name)
            emoji = interface_types.get_type_emoji(type_name)
            action = self._add_menu.addAction(f"{emoji} {display_name}")
            action.setData(type_name)
            action.triggered.connect(lambda checked=False, t=type_name: self._add_interface(t))
        
        self._add_btn.setMenu(self._add_menu)
        header_layout.addWidget(self._add_btn)
        
        layout.addWidget(header)
        
        # Scroll area for interface widgets
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self._container = QtWidgets.QWidget()
        self._container_layout = QtWidgets.QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(2)
        self._container_layout.addStretch()
        
        scroll.setWidget(self._container)
        layout.addWidget(scroll, 1)
        
        # Bottom buttons (edit, delete)
        btn_layout = QtWidgets.QHBoxLayout()
        
        self._edit_btn = QtWidgets.QPushButton("Edit")
        self._edit_btn.setToolTip("Expand selected interface for editing")
        self._edit_btn.clicked.connect(self._edit_selected)
        btn_layout.addWidget(self._edit_btn)
        
        self._delete_btn = QtWidgets.QPushButton("Delete")
        self._delete_btn.setToolTip("Delete selected interface")
        self._delete_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self._delete_btn)
        
        layout.addLayout(btn_layout)
    
    def _add_interface(self, element_type: str):
        """Add a new interface of specified type."""
        # Create new interface with default properties
        interface = InterfaceDefinition(element_type=element_type)
        
        # Set default geometry (centered, horizontal line)
        half_length = 10.0  # mm
        interface.x1_mm = -half_length
        interface.y1_mm = 0.0
        interface.x2_mm = half_length
        interface.y2_mm = 0.0
        
        # Add to list
        self.add_interface(interface)
    
    def _edit_selected(self):
        """Expand the selected interface for editing."""
        if 0 <= self._selected_index < len(self._interface_widgets):
            widget = self._interface_widgets[self._selected_index]
            widget.set_expanded(True)
    
    def _delete_selected(self):
        """Delete the selected interface."""
        if 0 <= self._selected_index < len(self._interface_widgets):
            reply = QtWidgets.QMessageBox.question(
                self,
                "Delete Interface",
                f"Delete interface {self._selected_index + 1}?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.remove_interface(self._selected_index)
    
    def _on_interface_changed(self, interface: InterfaceDefinition):
        """Handle interface property changes."""
        self.interfacesChanged.emit()
    
    def _on_delete_requested(self):
        """Handle delete request from interface widget."""
        # Find which widget sent the signal
        sender = self.sender()
        if sender in self._interface_widgets:
            index = self._interface_widgets.index(sender)
            self.remove_interface(index)
    
    def _update_indices(self):
        """Update interface indices for display."""
        for i, widget in enumerate(self._interface_widgets):
            widget.set_index(i)
    
    # Public API
    
    def add_interface(self, interface: InterfaceDefinition) -> CollapsibleInterfaceWidget:
        """
        Add an interface to the panel.
        
        Args:
            interface: InterfaceDefinition to add
        
        Returns:
            The created CollapsibleInterfaceWidget
        """
        widget = CollapsibleInterfaceWidget(interface, len(self._interface_widgets), self)
        widget.interfaceChanged.connect(self._on_interface_changed)
        widget.deleteRequested.connect(self._on_delete_requested)
        
        # Insert before stretch
        self._container_layout.insertWidget(len(self._interface_widgets), widget)
        self._interface_widgets.append(widget)
        
        self._update_indices()
        self.interfacesChanged.emit()
        
        return widget
    
    def remove_interface(self, index: int):
        """Remove interface at specified index."""
        if 0 <= index < len(self._interface_widgets):
            widget = self._interface_widgets.pop(index)
            widget.deleteLater()
            
            # Update selection
            if self._selected_index == index:
                self._selected_index = -1
            elif self._selected_index > index:
                self._selected_index -= 1
            
            self._update_indices()
            self.interfacesChanged.emit()
    
    def get_interfaces(self) -> List[InterfaceDefinition]:
        """Get list of all interface definitions."""
        return [widget.get_interface() for widget in self._interface_widgets]
    
    def set_interfaces(self, interfaces: List[InterfaceDefinition]):
        """Set the complete list of interfaces."""
        # Clear existing
        self.clear()
        
        # Add new
        for interface in interfaces:
            self.add_interface(interface)
    
    def clear(self):
        """Remove all interfaces."""
        while self._interface_widgets:
            widget = self._interface_widgets.pop()
            widget.deleteLater()
        
        self._selected_index = -1
        self.interfacesChanged.emit()
    
    def get_interface(self, index: int) -> Optional[InterfaceDefinition]:
        """Get interface at specified index."""
        if 0 <= index < len(self._interface_widgets):
            return self._interface_widgets[index].get_interface()
        return None
    
    def update_interface(self, index: int, interface: InterfaceDefinition):
        """Update interface at specified index."""
        if 0 <= index < len(self._interface_widgets):
            self._interface_widgets[index].set_interface(interface)
            self.interfacesChanged.emit()
    
    def select_interface(self, index: int):
        """
        Select an interface by index.
        
        Args:
            index: Index to select, or -1 to deselect all
        """
        self._selected_index = index
        
        # Visual feedback (highlight selected widget)
        for i, widget in enumerate(self._interface_widgets):
            is_selected = (i == index)
            widget.setStyleSheet(
                "background-color: palette(highlight); border-radius: 3px;" if is_selected else ""
            )
        
        self.interfaceSelected.emit(index)
    
    def get_selected_index(self) -> int:
        """Get currently selected interface index."""
        return self._selected_index
    
    def count(self) -> int:
        """Get number of interfaces."""
        return len(self._interface_widgets)
    
    def expand_all(self):
        """Expand all interface widgets."""
        for widget in self._interface_widgets:
            widget.set_expanded(True)
    
    def collapse_all(self):
        """Collapse all interface widgets."""
        for widget in self._interface_widgets:
            widget.set_expanded(False)
    
    def move_interface(self, from_index: int, to_index: int):
        """
        Move interface from one position to another.
        
        Args:
            from_index: Source index
            to_index: Destination index
        """
        if (0 <= from_index < len(self._interface_widgets) and 
            0 <= to_index < len(self._interface_widgets) and 
            from_index != to_index):
            
            # Move in list
            widget = self._interface_widgets.pop(from_index)
            self._interface_widgets.insert(to_index, widget)
            
            # Update layout
            self._container_layout.removeWidget(widget)
            self._container_layout.insertWidget(to_index, widget)
            
            # Update indices
            self._update_indices()
            
            # Update selection
            if self._selected_index == from_index:
                self._selected_index = to_index
            elif from_index < self._selected_index <= to_index:
                self._selected_index -= 1
            elif to_index <= self._selected_index < from_index:
                self._selected_index += 1
            
            self.interfacesChanged.emit()

