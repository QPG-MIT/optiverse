"""Collapsible widget for editing a single optical interface."""

from __future__ import annotations

from typing import Optional, Dict, Any

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.interface_definition import InterfaceDefinition
from ...core import interface_types


class CollapsibleInterfaceWidget(QtWidgets.QWidget):
    """
    Collapsible widget for editing a single optical interface.
    
    Features:
    - Expandable/collapsible header
    - Element type selector
    - Coordinate editing (x1, y1, x2, y2 in mm)
    - Dynamic property fields based on element type
    - Color indicator matching canvas visualization
    - Delete button
    
    Signals:
        interfaceChanged: Emitted when any property changes
        deleteRequested: Emitted when delete button clicked
        expandedChanged: Emitted when expand/collapse state changes
    """
    
    interfaceChanged = QtCore.pyqtSignal(object)  # InterfaceDefinition
    deleteRequested = QtCore.pyqtSignal()
    expandedChanged = QtCore.pyqtSignal(bool)
    
    def __init__(self, interface: InterfaceDefinition, index: int = 0, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        
        self._interface = interface
        self._index = index
        self._expanded = False
        self._updating = False  # Flag to prevent recursion during updates
        
        self._setup_ui()
        self._connect_signals()
        self._update_from_interface()
    
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header (always visible)
        self._header = self._create_header()
        layout.addWidget(self._header)
        
        # Content (collapsible)
        self._content = QtWidgets.QWidget()
        self._content.setVisible(False)  # Start collapsed
        self._content_layout = QtWidgets.QFormLayout(self._content)
        self._content_layout.setContentsMargins(20, 10, 10, 10)
        
        # Element type selector
        self._type_combo = QtWidgets.QComboBox()
        for type_name in interface_types.get_all_type_names():
            display_name = interface_types.get_type_display_name(type_name)
            self._type_combo.addItem(display_name, type_name)
        self._content_layout.addRow("Element Type:", self._type_combo)
        
        # Geometry group
        geom_group = QtWidgets.QGroupBox("Geometry")
        geom_layout = QtWidgets.QFormLayout(geom_group)
        
        # Point 1
        p1_layout = QtWidgets.QHBoxLayout()
        self._x1_spin = QtWidgets.QDoubleSpinBox()
        self._x1_spin.setRange(-10000, 10000)
        self._x1_spin.setDecimals(3)
        self._x1_spin.setSuffix(" mm")
        self._y1_spin = QtWidgets.QDoubleSpinBox()
        self._y1_spin.setRange(-10000, 10000)
        self._y1_spin.setDecimals(3)
        self._y1_spin.setSuffix(" mm")
        p1_layout.addWidget(QtWidgets.QLabel("x₁:"))
        p1_layout.addWidget(self._x1_spin)
        p1_layout.addWidget(QtWidgets.QLabel("y₁:"))
        p1_layout.addWidget(self._y1_spin)
        geom_layout.addRow("Point 1:", p1_layout)
        
        # Point 2
        p2_layout = QtWidgets.QHBoxLayout()
        self._x2_spin = QtWidgets.QDoubleSpinBox()
        self._x2_spin.setRange(-10000, 10000)
        self._x2_spin.setDecimals(3)
        self._x2_spin.setSuffix(" mm")
        self._y2_spin = QtWidgets.QDoubleSpinBox()
        self._y2_spin.setRange(-10000, 10000)
        self._y2_spin.setDecimals(3)
        self._y2_spin.setSuffix(" mm")
        p2_layout.addWidget(QtWidgets.QLabel("x₂:"))
        p2_layout.addWidget(self._x2_spin)
        p2_layout.addWidget(QtWidgets.QLabel("y₂:"))
        p2_layout.addWidget(self._y2_spin)
        geom_layout.addRow("Point 2:", p2_layout)
        
        # Info labels (length, angle)
        self._info_label = QtWidgets.QLabel()
        self._info_label.setStyleSheet("color: #666; font-size: 9pt;")
        geom_layout.addRow("Info:", self._info_label)
        
        self._content_layout.addRow(geom_group)
        
        # Properties container (dynamically populated)
        self._properties_group = QtWidgets.QGroupBox("Properties")
        self._properties_layout = QtWidgets.QFormLayout(self._properties_group)
        self._content_layout.addRow(self._properties_group)
        
        # Storage for property widgets
        self._property_widgets: Dict[str, QtWidgets.QWidget] = {}
        
        layout.addWidget(self._content)
    
    def _create_header(self) -> QtWidgets.QWidget:
        """Create the header widget with expand/collapse button."""
        header = QtWidgets.QWidget()
        header.setAutoFillBackground(True)
        header.setStyleSheet("""
            QWidget {
                background-color: palette(window);
                border: 1px solid palette(mid);
                border-radius: 3px;
            }
            QWidget:hover {
                background-color: palette(light);
            }
        """)
        
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        # Expand/collapse button
        self._expand_btn = QtWidgets.QToolButton()
        self._expand_btn.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self._expand_btn.setStyleSheet("QToolButton { border: none; }")
        self._expand_btn.clicked.connect(self._toggle_expanded)
        header_layout.addWidget(self._expand_btn)
        
        # Color indicator
        self._color_indicator = QtWidgets.QLabel("●")
        self._color_indicator.setStyleSheet(f"font-size: 16pt;")
        header_layout.addWidget(self._color_indicator)
        
        # Label
        self._header_label = QtWidgets.QLabel()
        self._header_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self._header_label, 1)
        
        # Delete button
        self._delete_btn = QtWidgets.QPushButton("×")
        self._delete_btn.setFixedSize(24, 24)
        self._delete_btn.setToolTip("Delete this interface")
        self._delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        self._delete_btn.clicked.connect(self.deleteRequested.emit)
        header_layout.addWidget(self._delete_btn)
        
        # Make header clickable
        header.mousePressEvent = lambda e: self._toggle_expanded()
        
        return header
    
    def _connect_signals(self):
        """Connect widget signals to handlers."""
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        self._x1_spin.valueChanged.connect(self._on_geometry_changed)
        self._y1_spin.valueChanged.connect(self._on_geometry_changed)
        self._x2_spin.valueChanged.connect(self._on_geometry_changed)
        self._y2_spin.valueChanged.connect(self._on_geometry_changed)
    
    def _toggle_expanded(self):
        """Toggle expand/collapse state."""
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._expand_btn.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if self._expanded else QtCore.Qt.ArrowType.RightArrow
        )
        self.expandedChanged.emit(self._expanded)
    
    def _update_from_interface(self):
        """Update UI from interface definition."""
        if self._updating:
            return
        
        self._updating = True
        
        try:
            # Update header
            label_text = f"Interface {self._index + 1}: {self._interface.get_label()}"
            self._header_label.setText(label_text)
            
            # Update color indicator
            r, g, b = self._interface.get_color()
            self._color_indicator.setStyleSheet(f"font-size: 16pt; color: rgb({r}, {g}, {b});")
            
            # Update type combo
            idx = self._type_combo.findData(self._interface.element_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
            
            # Update geometry
            self._x1_spin.setValue(self._interface.x1_mm)
            self._y1_spin.setValue(self._interface.y1_mm)
            self._x2_spin.setValue(self._interface.x2_mm)
            self._y2_spin.setValue(self._interface.y2_mm)
            
            # Update info label
            length = self._interface.length_mm()
            angle = self._interface.angle_deg()
            self._info_label.setText(f"Length: {length:.2f} mm, Angle: {angle:.1f}°")
            
            # Update properties
            self._update_property_widgets()
        
        finally:
            self._updating = False
    
    def _update_property_widgets(self):
        """Create/update property widgets based on element type."""
        # Clear existing widgets
        for widget in self._property_widgets.values():
            widget.deleteLater()
        self._property_widgets.clear()
        
        # Clear layout
        while self._properties_layout.count():
            item = self._properties_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get properties for this element type
        props = interface_types.get_type_properties(self._interface.element_type)
        
        for prop_name in props:
            widget = self._create_property_widget(prop_name)
            if widget:
                label = interface_types.get_property_label(self._interface.element_type, prop_name)
                self._properties_layout.addRow(label + ":", widget)
                self._property_widgets[prop_name] = widget
    
    def _create_property_widget(self, prop_name: str) -> Optional[QtWidgets.QWidget]:
        """Create a widget for a specific property."""
        value = getattr(self._interface, prop_name, None)
        if value is None:
            return None
        
        # Handle different property types
        if isinstance(value, bool):
            # Checkbox
            widget = QtWidgets.QCheckBox()
            widget.setChecked(value)
            widget.toggled.connect(lambda checked: self._on_property_changed(prop_name, checked))
            return widget
        
        elif isinstance(value, (int, float)):
            # SpinBox
            widget = QtWidgets.QDoubleSpinBox()
            min_val, max_val = interface_types.get_property_range(self._interface.element_type, prop_name)
            widget.setRange(min_val, max_val)
            widget.setDecimals(3)
            unit = interface_types.get_property_unit(self._interface.element_type, prop_name)
            if unit:
                widget.setSuffix(f" {unit}")
            widget.setValue(value)
            widget.valueChanged.connect(lambda v: self._on_property_changed(prop_name, v))
            return widget
        
        elif isinstance(value, str):
            # ComboBox for pass_type, or LineEdit for others
            if prop_name == 'pass_type':
                widget = QtWidgets.QComboBox()
                widget.addItems(['longpass', 'shortpass'])
                idx = widget.findText(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                widget.currentTextChanged.connect(lambda v: self._on_property_changed(prop_name, v))
                return widget
            else:
                widget = QtWidgets.QLineEdit()
                widget.setText(value)
                widget.textChanged.connect(lambda v: self._on_property_changed(prop_name, v))
                return widget
        
        return None
    
    def _on_type_changed(self):
        """Handle element type change."""
        if self._updating:
            return
        
        new_type = self._type_combo.currentData()
        if new_type and new_type != self._interface.element_type:
            self._interface.element_type = new_type
            self._update_from_interface()
            self.interfaceChanged.emit(self._interface)
    
    def _on_geometry_changed(self):
        """Handle geometry coordinate changes."""
        if self._updating:
            return
        
        self._interface.x1_mm = self._x1_spin.value()
        self._interface.y1_mm = self._y1_spin.value()
        self._interface.x2_mm = self._x2_spin.value()
        self._interface.y2_mm = self._y2_spin.value()
        
        # Update info label
        length = self._interface.length_mm()
        angle = self._interface.angle_deg()
        self._info_label.setText(f"Length: {length:.2f} mm, Angle: {angle:.1f}°")
        
        # Update header color (in case it depends on properties)
        r, g, b = self._interface.get_color()
        self._color_indicator.setStyleSheet(f"font-size: 16pt; color: rgb({r}, {g}, {b});")
        
        self.interfaceChanged.emit(self._interface)
    
    def _on_property_changed(self, prop_name: str, value: Any):
        """Handle property value change."""
        if self._updating:
            return
        
        setattr(self._interface, prop_name, value)
        
        # Update header (label and color may have changed)
        self._header_label.setText(f"Interface {self._index + 1}: {self._interface.get_label()}")
        r, g, b = self._interface.get_color()
        self._color_indicator.setStyleSheet(f"font-size: 16pt; color: rgb({r}, {g}, {b});")
        
        self.interfaceChanged.emit(self._interface)
    
    # Public API
    
    def get_interface(self) -> InterfaceDefinition:
        """Get the interface definition."""
        return self._interface
    
    def set_interface(self, interface: InterfaceDefinition):
        """Set a new interface definition."""
        self._interface = interface
        self._update_from_interface()
    
    def set_index(self, index: int):
        """Update the interface index (for display)."""
        self._index = index
        self._header_label.setText(f"Interface {self._index + 1}: {self._interface.get_label()}")
    
    def is_expanded(self) -> bool:
        """Check if widget is expanded."""
        return self._expanded
    
    def set_expanded(self, expanded: bool):
        """Set expand/collapse state."""
        if expanded != self._expanded:
            self._toggle_expanded()

