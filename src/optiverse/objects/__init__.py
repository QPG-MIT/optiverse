"""
Optical objects module.

This module contains all graphical components for the optics simulation:
- Base classes (BaseObj, ComponentSprite)
- Optical elements (lenses, mirrors, beamsplitters, sources)
- Annotations (rulers, text notes)
- Views (graphics view, image canvas)
"""

# Base classes
from .base_obj import BaseObj
from .component_sprite import ComponentSprite

# Optical elements
from .lenses import LensItem
from .mirrors import MirrorItem
from .beamsplitters import BeamsplitterItem
from .sources import SourceItem

# Annotations
from .annotations import RulerItem, TextNoteItem

# Views
from .views import GraphicsView, ImageCanvas

__all__ = [
    # Base classes
    "BaseObj",
    "ComponentSprite",
    # Optical elements
    "LensItem",
    "MirrorItem",
    "BeamsplitterItem",
    "SourceItem",
    # Annotations
    "RulerItem",
    "TextNoteItem",
    # Views
    "GraphicsView",
    "ImageCanvas",
]

