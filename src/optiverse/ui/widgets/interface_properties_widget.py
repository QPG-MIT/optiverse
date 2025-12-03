"""
Unified widget for displaying and editing interface properties.

This module provides InterfacePropertiesWidget which can handle:
- Single interface with coordinates (for InterfaceTreePanel)
- Multiple interfaces without coordinates (for component edit dialogs)
"""

from __future__ import annotations

from typing import Any

from PyQt6 import QtCore, QtWidgets

from ...core import interface_types
from ...core.interface_definition import InterfaceDefinition
from .constants import (
    COLORED_CIRCLE_SIZE,
    PASS_TYPE_OPTIONS,
    POLARIZER_SUBTYPE_OPTIONS,
    PROPERTY_FORM_HORIZONTAL_SPACING,
    PROPERTY_FORM_LEFT_MARGIN,
    PROPERTY_FORM_VERTICAL_SPACING,
    Icons,
)
from .smart_spinbox import SmartDoubleSpinBox


class InterfacePropertiesWidget(QtWidgets.QWidget):
    """
    Unified widget for editing interface properties.

    Supports two modes:
    - Single interface with coordinates (show_coordinates=True)
    - Multiple interfaces without coordinates (show_coordinates=False)

    Args:
        interfaces: Single InterfaceDefinition or list of InterfaceDefinition
        show_coordinates: Whether to show x1, y1, x2, y2 fields
        parent: Parent widget
    """

    propertiesChanged = QtCore.pyqtSignal()
    # Alias for backward compatibility
    propertyChanged = propertiesChanged

    def __init__(
        self,
        interfaces: InterfaceDefinition | list[InterfaceDefinition],
        show_coordinates: bool = False,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)

        # Normalize to list internally
        if isinstance(interfaces, InterfaceDefinition):
            self._interfaces = [interfaces]
            self._single_mode = True
        else:
            self._interfaces = list(interfaces)
            self._single_mode = False

        self._show_coordinates = show_coordinates
        self._signals_blocked = False

        # Property widgets: interface_index -> {prop_name -> widget}
        self._property_widgets: dict[int, dict[str, QtWidgets.QWidget]] = {}
        # Form layouts for rebuilding on type change
        self._forms: dict[int, QtWidgets.QFormLayout] = {}

        self._setup_ui()

    # -------------------------------------------------------------------------
    # Properties for backward compatibility
    # -------------------------------------------------------------------------

    @property
    def interface(self) -> InterfaceDefinition:
        """Get the first interface (for single-interface mode)."""
        return self._interfaces[0] if self._interfaces else None  # type: ignore

    @interface.setter
    def interface(self, value: InterfaceDefinition) -> None:
        """Set the first interface (for single-interface mode)."""
        if self._interfaces:
            self._interfaces[0] = value
        else:
            self._interfaces = [value]

    @property
    def interfaces(self) -> list[InterfaceDefinition]:
        """Get all interfaces."""
        return self._interfaces

    # -------------------------------------------------------------------------
    # UI Setup
    # -------------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Create the UI layout."""
        layout = QtWidgets.QVBoxLayout(self)

        if self._single_mode and self._show_coordinates:
            # Compact mode for tree panel
            layout.setContentsMargins(PROPERTY_FORM_LEFT_MARGIN, 3, 5, 3)
            layout.setSpacing(2)
        else:
            # Standard mode for dialogs
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)

        if not self._interfaces:
            no_interfaces_label = QtWidgets.QLabel("No interfaces defined")
            no_interfaces_label.setObjectName("placeholderLabel")
            layout.addWidget(no_interfaces_label)
            return

        # Create sections for each interface
        for idx, interface in enumerate(self._interfaces):
            section = self._create_interface_section(idx, interface)
            layout.addWidget(section)

        layout.addStretch()

        # Size policy for smooth scrolling
        if self._single_mode:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            )

    def _create_interface_section(
        self, idx: int, interface: InterfaceDefinition
    ) -> QtWidgets.QWidget:
        """Create a section for one interface."""
        self._property_widgets[idx] = {}

        if self._single_mode and self._show_coordinates:
            # No group box for single interface in tree panel
            container = QtWidgets.QWidget()
            form = self._create_form_layout()
            container.setLayout(form)
            self._forms[idx] = form
            self._populate_form(idx, interface, form)
            return container

        # Group box for multi-interface or dialog mode
        group = QtWidgets.QGroupBox()
        type_name = interface_types.get_type_display_name(interface.element_type)
        emoji = interface_types.get_type_emoji(interface.element_type)

        if len(self._interfaces) > 1:
            group.setTitle(f"{emoji} Interface {idx + 1}: {type_name}")
        else:
            group.setTitle(f"{emoji} {type_name} Properties")

        form = self._create_form_layout()
        form.setContentsMargins(10, 10, 10, 10)
        form.setVerticalSpacing(8)
        group.setLayout(form)
        self._forms[idx] = form

        self._populate_form(idx, interface, form)
        return group

    def _populate_form(
        self, idx: int, interface: InterfaceDefinition, form: QtWidgets.QFormLayout
    ) -> None:
        """Populate form with properties."""
        # Type selector (for tree panel mode)
        if self._single_mode and self._show_coordinates:
            type_combo = QtWidgets.QComboBox()
            for type_name in interface_types.get_all_type_names():
                display_name = interface_types.get_type_display_name(type_name)
                emoji = interface_types.get_type_emoji(type_name)
                type_combo.addItem(f"{emoji} {display_name}", type_name)

            combo_idx = type_combo.findData(interface.element_type)
            if combo_idx >= 0:
                type_combo.setCurrentIndex(combo_idx)

            type_combo.currentIndexChanged.connect(
                lambda _, i=idx: self._on_type_changed(i)
            )
            self._property_widgets[idx]["type"] = type_combo
            form.addRow("Type:", type_combo)

        # Coordinate fields
        if self._show_coordinates:
            self._add_coordinate_fields(idx, interface, form)

        # Type-specific properties
        self._add_type_properties(idx, interface, form)

    def _add_coordinate_fields(
        self, idx: int, interface: InterfaceDefinition, form: QtWidgets.QFormLayout
    ) -> None:
        """Add coordinate edit fields."""
        from .interface_widgets import EditableLabel

        for coord_name, value in [
            ("X₁", interface.x1_mm),
            ("Y₁", interface.y1_mm),
            ("X₂", interface.x2_mm),
            ("Y₂", interface.y2_mm),
        ]:
            editable = EditableLabel(f"{value:.3f}")
            editable.setPlaceholderText("0.000")
            editable.valueChanged.connect(
                lambda val, i=idx, c=coord_name: self._on_coordinate_changed(i, c, val)
            )
            self._property_widgets[idx][coord_name] = editable
            form.addRow(f"{coord_name} (mm):", editable)

    def _add_type_properties(
        self, idx: int, interface: InterfaceDefinition, form: QtWidgets.QFormLayout
    ) -> None:
        """Add type-specific properties."""
        props = interface_types.get_type_properties(interface.element_type)

        if not props:
            if not self._show_coordinates:
                no_props = QtWidgets.QLabel("No editable properties")
                no_props.setObjectName("placeholderLabel")
                form.addRow(no_props)
            return

        for prop_name in props:
            value = getattr(interface, prop_name, None)
            if value is None:
                continue

            widget, label_text = self._create_property_widget(
                idx, prop_name, value, interface.element_type
            )

            # Refractive index gets colored indicator
            if prop_name in ("n1", "n2"):
                container = self._create_refractive_index_row(prop_name, widget)
                form.addRow(f"{label_text}:", container)
            else:
                form.addRow(f"{label_text}:", widget)

    def _create_refractive_index_row(
        self, prop_name: str, value_widget: QtWidgets.QWidget
    ) -> QtWidgets.QWidget:
        """Create row with colored circle for refractive index."""
        from .interface_widgets import ColoredCircleLabel

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        color = Icons.N1_COLOR if prop_name == "n1" else Icons.N2_COLOR
        tooltip = "n₁ side (yellow)" if prop_name == "n1" else "n₂ side (purple)"

        circle = ColoredCircleLabel(color, size=COLORED_CIRCLE_SIZE)
        circle.setToolTip(tooltip)
        layout.addWidget(circle)
        layout.addWidget(value_widget, 1)

        container = QtWidgets.QWidget()
        container.setLayout(layout)
        return container

    # -------------------------------------------------------------------------
    # Widget Creation
    # -------------------------------------------------------------------------

    def _create_property_widget(
        self, idx: int, prop_name: str, value: Any, element_type: str
    ) -> tuple[QtWidgets.QWidget, str]:
        """Create appropriate widget for a property."""
        label = interface_types.get_property_label(element_type, prop_name)
        unit = interface_types.get_property_unit(element_type, prop_name)
        label_text = f"{label} ({unit})" if unit else label

        widget: QtWidgets.QWidget

        if isinstance(value, bool):
            widget = QtWidgets.QCheckBox()
            widget.setChecked(value)
            widget.toggled.connect(
                lambda v, i=idx, p=prop_name: self._on_property_changed(i, p, v)
            )

        elif isinstance(value, (int, float)):
            spinbox = SmartDoubleSpinBox()
            min_val, max_val = interface_types.get_property_range(element_type, prop_name)
            spinbox.setRange(min_val, max_val)
            spinbox.setDecimals(3)
            if unit:
                spinbox.setSuffix(f" {unit}")
            spinbox.setValue(float(value))
            spinbox.valueChanged.connect(
                lambda v, i=idx, p=prop_name: self._on_property_changed(i, p, v)
            )
            widget = spinbox

        elif isinstance(value, str):
            if prop_name == "pass_type":
                combo = QtWidgets.QComboBox()
                combo.addItems(PASS_TYPE_OPTIONS)
                combo_idx = combo.findText(value)
                if combo_idx >= 0:
                    combo.setCurrentIndex(combo_idx)
                combo.currentTextChanged.connect(
                    lambda v, i=idx, p=prop_name: self._on_property_changed(i, p, v)
                )
                widget = combo

            elif prop_name == "polarizer_subtype":
                combo = QtWidgets.QComboBox()
                combo.addItems(POLARIZER_SUBTYPE_OPTIONS)
                combo_idx = combo.findText(value)
                if combo_idx >= 0:
                    combo.setCurrentIndex(combo_idx)
                combo.currentTextChanged.connect(
                    lambda v, i=idx, p=prop_name: self._on_property_changed(i, p, v)
                )
                widget = combo

            else:
                line_edit = QtWidgets.QLineEdit(value)
                line_edit.textChanged.connect(
                    lambda v, i=idx, p=prop_name: self._on_property_changed(i, p, v)
                )
                widget = line_edit
        else:
            widget = QtWidgets.QLabel(str(value))

        self._property_widgets[idx][prop_name] = widget
        return widget, label_text

    @staticmethod
    def _create_form_layout() -> QtWidgets.QFormLayout:
        """Create consistently styled form layout."""
        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(PROPERTY_FORM_VERTICAL_SPACING)
        form.setHorizontalSpacing(PROPERTY_FORM_HORIZONTAL_SPACING)
        form.setLabelAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        form.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        return form

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_property_changed(self, idx: int, prop_name: str, value: Any) -> None:
        """Handle property value change."""
        if self._signals_blocked:
            return
        if 0 <= idx < len(self._interfaces):
            setattr(self._interfaces[idx], prop_name, value)
            self.propertiesChanged.emit()

    def _on_coordinate_changed(self, idx: int, coord_name: str, value_str: str) -> None:
        """Handle coordinate value change."""
        if self._signals_blocked or idx >= len(self._interfaces):
            return

        from .interface_widgets import EditableLabel

        widget = self._property_widgets.get(idx, {}).get(coord_name)
        if not widget:
            return

        try:
            value = float(value_str)
            interface = self._interfaces[idx]

            if coord_name == "X₁":
                interface.x1_mm = value
            elif coord_name == "X₂":
                interface.x2_mm = value
            elif coord_name == "Y₁":
                interface.y1_mm = value
            elif coord_name == "Y₂":
                interface.y2_mm = value

            if isinstance(widget, EditableLabel):
                widget.setText(f"{value:.3f}")
            self.propertiesChanged.emit()

        except ValueError:
            # Revert on invalid input
            self._revert_coordinate(idx, coord_name, widget)

    def _revert_coordinate(
        self, idx: int, coord_name: str, widget: QtWidgets.QWidget
    ) -> None:
        """Revert coordinate widget to current value."""
        from .interface_widgets import EditableLabel

        if not isinstance(widget, EditableLabel) or idx >= len(self._interfaces):
            return

        interface = self._interfaces[idx]
        if coord_name == "X₁":
            widget.setText(f"{interface.x1_mm:.3f}")
        elif coord_name == "X₂":
            widget.setText(f"{interface.x2_mm:.3f}")
        elif coord_name == "Y₁":
            widget.setText(f"{interface.y1_mm:.3f}")
        elif coord_name == "Y₂":
            widget.setText(f"{interface.y2_mm:.3f}")

    def _on_type_changed(self, idx: int) -> None:
        """Handle type change - rebuild properties."""
        if self._signals_blocked or idx >= len(self._interfaces):
            return

        type_combo = self._property_widgets.get(idx, {}).get("type")
        if not isinstance(type_combo, QtWidgets.QComboBox):
            return

        new_type = type_combo.currentData()
        if new_type and new_type != self._interfaces[idx].element_type:
            self._interfaces[idx].element_type = new_type
            self._rebuild_form(idx)
            self.propertiesChanged.emit()

    def _rebuild_form(self, idx: int) -> None:
        """Rebuild form for interface at index."""
        form = self._forms.get(idx)
        if not form or idx >= len(self._interfaces):
            return

        # Clear form
        while form.count() > 0:
            item = form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._property_widgets[idx].clear()
        self._populate_form(idx, self._interfaces[idx], form)
        self.updateGeometry()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_interfaces(self) -> list[InterfaceDefinition]:
        """Get current interfaces."""
        return self._interfaces

    def update_from_interface(self, interface: InterfaceDefinition) -> None:
        """Update from single interface (single-mode compatibility)."""
        self.update_from_interfaces([interface])

    def update_from_interfaces(self, interfaces: list[InterfaceDefinition]) -> None:
        """Update widget values from interfaces."""
        from .interface_widgets import EditableLabel

        self._signals_blocked = True
        try:
            self._interfaces = interfaces

            for idx, interface in enumerate(interfaces):
                if idx not in self._property_widgets:
                    continue

                for prop_name, widget in self._property_widgets[idx].items():
                    widget.blockSignals(True)
                    try:
                        # Handle coordinates
                        if prop_name in ("X₁", "Y₁", "X₂", "Y₂"):
                            if isinstance(widget, EditableLabel):
                                attr = {"X₁": "x1_mm", "Y₁": "y1_mm", "X₂": "x2_mm", "Y₂": "y2_mm"}[prop_name]
                                widget.setText(f"{getattr(interface, attr):.3f}")
                            continue

                        # Handle type combo
                        if prop_name == "type":
                            if isinstance(widget, QtWidgets.QComboBox):
                                combo_idx = widget.findData(interface.element_type)
                                if combo_idx >= 0:
                                    widget.setCurrentIndex(combo_idx)
                            continue

                        # Handle other properties
                        value = getattr(interface, prop_name, None)
                        if value is None:
                            continue

                        if isinstance(widget, QtWidgets.QCheckBox):
                            widget.setChecked(bool(value))
                        elif isinstance(widget, SmartDoubleSpinBox):
                            widget.setValue(float(value))
                        elif isinstance(widget, QtWidgets.QComboBox):
                            combo_idx = widget.findText(str(value))
                            if combo_idx >= 0:
                                widget.setCurrentIndex(combo_idx)
                        elif isinstance(widget, QtWidgets.QLineEdit):
                            widget.setText(str(value))

                    finally:
                        widget.blockSignals(False)

        finally:
            self._signals_blocked = False
