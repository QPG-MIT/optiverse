"""
Interface Widget Components - Reusable widgets for the InterfaceTreePanel.

This module contains:
- InterfaceTreeWidget: Tree widget with delete key handling
- EditableLabel: Double-click-to-edit label widget
- ColoredCircleLabel: Color indicator label
- PropertyListWidget: Interface property editor
"""

from __future__ import annotations

from typing import Optional, Dict, Any

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
        
        # Create stacked widget to switch between label and line edit
        self._stack = QtWidgets.QStackedWidget()
        
        # Label for display mode
        self._label = QtWidgets.QLabel(initial_value)
        self._label.setStyleSheet("QLabel { padding: 2px; }")
        self._stack.addWidget(self._label)
        
        # Line edit for edit mode
        self._edit = QtWidgets.QLineEdit(initial_value)
        self._edit.returnPressed.connect(self._finish_editing)
        self._edit.editingFinished.connect(self._finish_editing)
        self._stack.addWidget(self._edit)
        
        layout.addWidget(self._stack)
        
        # Start in label mode
        self._stack.setCurrentWidget(self._label)
    
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        """Switch to edit mode on double-click."""
        super().mouseDoubleClickEvent(event)
        self._start_editing()
    
    def _start_editing(self):
        """Switch to edit mode."""
        if self._editing:
            return
        self._editing = True
        self._edit.setText(self._label.text())
        self._stack.setCurrentWidget(self._edit)
        self._edit.setFocus()
        self._edit.selectAll()
    
    def _finish_editing(self):
        """Finish editing and switch back to label mode."""
        if not self._editing:
            return
        self._editing = False
        
        new_value = self._edit.text()
        if new_value != self._value:
            self._value = new_value
            self._label.setText(new_value)
            self.valueChanged.emit(new_value)
        else:
            self._label.setText(self._value)
        
        self._stack.setCurrentWidget(self._label)
    
    def setText(self, text: str):
        """Set the displayed text value."""
        self._value = text
        self._label.setText(text)
        if self._editing:
            self._edit.setText(text)
    
    def text(self) -> str:
        """Get the current text value."""
        return self._value
    
    def setPlaceholderText(self, text: str):
        """Set placeholder text for the edit field."""
        self._edit.setPlaceholderText(text)


class ColoredCircleLabel(QtWidgets.QLabel):
    """A small colored circle indicator."""
    
    def __init__(self, color: str, size: int = 12, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
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
        self._form.setVerticalSpacing(3)
        self._form.setHorizontalSpacing(10)
        self._form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Populate form
        self._populate_form()
        
        layout.addLayout(self._form)
        layout.addStretch()
        
        # Set proper size policy for smooth scrolling
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding
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
        
        # Type-specific properties
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
                h_layout = QtWidgets.QHBoxLayout()
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(5)
                
                if prop_name == 'n1':
                    circle = ColoredCircleLabel('#FFD700', size=10)
                    circle.setToolTip("n₁ side (yellow)")
                else:
                    circle = ColoredCircleLabel('#9370DB', size=10)
                    circle.setToolTip("n₂ side (purple)")
                
                h_layout.addWidget(circle)
                h_layout.addWidget(widget, 1)
                
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
            elif prop_name == 'polarizer_subtype':
                widget = QtWidgets.QComboBox()
                widget.addItems(['waveplate', 'linear_polarizer', 'faraday_rotator'])
                idx = widget.findText(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                widget.currentTextChanged.connect(lambda v: self._on_property_changed(prop_name, v))
                self._property_widgets[prop_name] = widget
            else:
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
            self.interface.element_type = new_type
            self._rebuild_form()
            self.propertyChanged.emit()
    
    def _rebuild_form(self):
        """Rebuild the entire form (used when type changes)."""
        while self._form.count() > 0:
            item = self._form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._property_widgets.clear()
        self._populate_form()
        self.updateGeometry()
        
        if hasattr(self, 'geometryChanged'):
            QtCore.QTimer.singleShot(10, self.geometryChanged)
    
    def _on_numeric_property_changed(self, prop_name: str):
        """Handle numeric property text field changes."""
        if self._updating:
            return
        
        line_edit = self._property_widgets.get(prop_name)
        if not line_edit:
            return
        
        try:
            value = float(line_edit.text())
            
            min_val, max_val = interface_types.get_property_range(self.interface.element_type, prop_name)
            if value < min_val or value > max_val:
                current_value = getattr(self.interface, prop_name, 0.0)
                line_edit.setText(f"{current_value:.3f}")
                return
            
            setattr(self.interface, prop_name, value)
            line_edit.setText(f"{value:.3f}")
            self.propertyChanged.emit()
        
        except ValueError:
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
                    if isinstance(value, (int, float)):
                        widget.setText(f"{value:.3f}")
                    else:
                        widget.setText(str(value))
        
        finally:
            self._updating = False

