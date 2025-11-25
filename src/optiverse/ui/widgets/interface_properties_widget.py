"""
Widget for displaying and editing interface properties in component edit dialogs.

This widget shows optical properties (focal length, refractive index, etc.) for
one or more interfaces, excluding the geometric coordinates (x1, y1, x2, y2).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6 import QtCore, QtWidgets

from ...core import interface_types
from ...core.interface_definition import InterfaceDefinition
from .smart_spinbox import SmartDoubleSpinBox


class InterfacePropertiesWidget(QtWidgets.QWidget):
    """
    Widget for editing interface properties (excluding coordinates).

    Displays all interfaces in a component with their editable properties.
    Interface type is shown as read-only label.
    """

    propertiesChanged = QtCore.pyqtSignal()

    def __init__(self, interfaces: List[InterfaceDefinition], parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.interfaces = interfaces
        self._property_widgets: Dict[int, Dict[str, QtWidgets.QWidget]] = {}  # interface_index -> {prop_name -> widget}
        self._updating = False

        self._setup_ui()

    def _setup_ui(self):
        """Create the UI layout."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        if not self.interfaces:
            no_interfaces_label = QtWidgets.QLabel("No interfaces defined")
            no_interfaces_label.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(no_interfaces_label)
            return

        # Add a section for each interface
        for idx, interface in enumerate(self.interfaces):
            interface_widget = self._create_interface_section(idx, interface)
            layout.addWidget(interface_widget)

        layout.addStretch()

    def _create_interface_section(self, idx: int, interface: InterfaceDefinition) -> QtWidgets.QWidget:
        """Create a section for one interface."""
        group = QtWidgets.QGroupBox()

        # Set title with interface number and type
        type_name = interface_types.get_type_display_name(interface.element_type)
        emoji = interface_types.get_type_emoji(interface.element_type)
        if len(self.interfaces) > 1:
            group.setTitle(f"{emoji} Interface {idx + 1}: {type_name}")
        else:
            group.setTitle(f"{emoji} {type_name} Properties")

        form = QtWidgets.QFormLayout(group)
        form.setContentsMargins(10, 10, 10, 10)
        form.setVerticalSpacing(8)
        form.setHorizontalSpacing(10)

        # Get properties for this interface type
        props = interface_types.get_type_properties(interface.element_type)

        if not props:
            no_props_label = QtWidgets.QLabel("No editable properties")
            no_props_label.setStyleSheet("color: gray; font-style: italic;")
            form.addRow(no_props_label)
            return group

        # Create widgets for each property
        self._property_widgets[idx] = {}

        for prop_name in props:
            value = getattr(interface, prop_name, None)
            if value is None:
                continue

            label = interface_types.get_property_label(interface.element_type, prop_name)
            unit = interface_types.get_property_unit(interface.element_type, prop_name)

            # Add unit to label if present
            label_text = f"{label}:"

            if isinstance(value, bool):
                widget = QtWidgets.QCheckBox()
                widget.setChecked(value)
                widget.toggled.connect(lambda checked, i=idx, p=prop_name: self._on_property_changed(i, p, checked))
                self._property_widgets[idx][prop_name] = widget
                form.addRow(label_text, widget)

            elif isinstance(value, (int, float)):
                widget = SmartDoubleSpinBox()
                min_val, max_val = interface_types.get_property_range(interface.element_type, prop_name)
                widget.setRange(min_val, max_val)
                widget.setDecimals(3)
                if unit:
                    widget.setSuffix(f" {unit}")
                widget.setValue(float(value))
                widget.valueChanged.connect(lambda val, i=idx, p=prop_name: self._on_property_changed(i, p, val))
                self._property_widgets[idx][prop_name] = widget
                form.addRow(label_text, widget)

            elif isinstance(value, str):
                if prop_name == 'pass_type':
                    widget = QtWidgets.QComboBox()
                    widget.addItems(['longpass', 'shortpass'])
                    idx_combo = widget.findText(value)
                    if idx_combo >= 0:
                        widget.setCurrentIndex(idx_combo)
                    widget.currentTextChanged.connect(lambda v, i=idx, p=prop_name: self._on_property_changed(i, p, v))
                    self._property_widgets[idx][prop_name] = widget
                elif prop_name == 'polarizer_subtype':
                    # Dropdown for polarizer subtype
                    widget = QtWidgets.QComboBox()
                    widget.addItems(['waveplate', 'linear_polarizer', 'faraday_rotator'])
                    idx_combo = widget.findText(value)
                    if idx_combo >= 0:
                        widget.setCurrentIndex(idx_combo)
                    widget.currentTextChanged.connect(lambda v, i=idx, p=prop_name: self._on_property_changed(i, p, v))
                    self._property_widgets[idx][prop_name] = widget
                else:
                    widget = QtWidgets.QLineEdit(value)
                    widget.textChanged.connect(lambda v, i=idx, p=prop_name: self._on_property_changed(i, p, v))
                    self._property_widgets[idx][prop_name] = widget
                form.addRow(label_text, widget)

        return group

    def _on_property_changed(self, interface_idx: int, prop_name: str, value: Any):
        """Handle property value change."""
        if self._updating:
            return

        if interface_idx < len(self.interfaces):
            # Update the interface
            setattr(self.interfaces[interface_idx], prop_name, value)
            self.propertiesChanged.emit()

    def get_interfaces(self) -> List[InterfaceDefinition]:
        """Get the current interfaces with updated values."""
        return self.interfaces

    def update_from_interfaces(self, interfaces: List[InterfaceDefinition]):
        """Update widget values from interfaces."""
        self._updating = True
        try:
            self.interfaces = interfaces

            # Update all property widgets
            for idx, interface in enumerate(interfaces):
                if idx not in self._property_widgets:
                    continue

                for prop_name, widget in self._property_widgets[idx].items():
                    value = getattr(interface, prop_name, None)
                    if value is None:
                        continue

                    if isinstance(widget, QtWidgets.QCheckBox):
                        widget.setChecked(value)
                    elif isinstance(widget, SmartDoubleSpinBox):
                        widget.setValue(float(value))
                    elif isinstance(widget, QtWidgets.QComboBox):
                        idx_combo = widget.findText(str(value))
                        if idx_combo >= 0:
                            widget.setCurrentIndex(idx_combo)
                    elif isinstance(widget, QtWidgets.QLineEdit):
                        widget.setText(str(value))

        finally:
            self._updating = False



