"""
Optical objects module.

This module contains all graphical components for the optics simulation:
- Base classes (BaseObj, ComponentSprite)
- Optical elements (lenses, mirrors, beamsplitters, dichroics, waveplates, sources)
- Component factory (unified component creation)
- Miscellaneous (SLMs)
- Annotations (rulers, text notes)
- Views (graphics view, image canvas)
"""

# Base classes
# Annotations
from .annotations import RectangleItem, RulerItem, TextNoteItem
from .base_obj import BaseObj

# Component factory
from .component_factory import ComponentFactory
from .component_sprite import ComponentSprite

# Optical elements
from .generic import ComponentItem
from .sources import SourceItem

# Views
from .views import GraphicsView, ImageCanvas

__all__ = [
    # Base classes
    "BaseObj",
    "ComponentSprite",
    # Component factory
    "ComponentFactory",
    # Optical elements (includes background/decorative items with no interfaces)
    "ComponentItem",
    "SourceItem",
    # Annotations
    "RulerItem",
    "TextNoteItem",
    "RectangleItem",
    # Views
    "GraphicsView",
    "ImageCanvas",
]
