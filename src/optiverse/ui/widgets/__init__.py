"""Custom widgets for Optiverse UI."""

from .interface_properties_widget import InterfacePropertiesWidget
from .interface_tree_panel import InterfaceTreePanel
from .interface_widgets import (
    ColoredCircleLabel,
    EditableLabel,
    InterfaceTreeWidget,
)
from .layer_panel import (
    ClickableLabel,
    LayerItemWidget,
    LayerPanel,
    LayerTreeWidget,
)
from .library_tree import LibraryTree
from .ruler_widget import CanvasWithRulers, RulerWidget
from .smart_spinbox import SmartDoubleSpinBox, SmartSpinBox

__all__ = [
    # Main panels
    "InterfaceTreePanel",
    "LayerPanel",
    "LibraryTree",
    # Ruler widgets
    "RulerWidget",
    "CanvasWithRulers",
    # Smart spinboxes
    "SmartDoubleSpinBox",
    "SmartSpinBox",
    # Property widgets
    "InterfacePropertiesWidget",
    # Interface widgets
    "InterfaceTreeWidget",
    "EditableLabel",
    "ColoredCircleLabel",
    # Layer widgets
    "ClickableLabel",
    "LayerItemWidget",
    "LayerTreeWidget",
]
