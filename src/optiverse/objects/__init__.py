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
from .base_obj import BaseObj
from .component_sprite import ComponentSprite

# Component factory
from .component_factory import ComponentFactory

# Optical elements
from .generic import ComponentItem
from .sources import SourceItem

# Annotations
from .annotations import RulerItem, TextNoteItem, RectangleItem

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



