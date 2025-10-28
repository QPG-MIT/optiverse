"""
Optical objects module.

This module contains all graphical components for the optics simulation:
- Base classes (BaseObj, ComponentSprite)
- Optical elements (lenses, mirrors, beamsplitters, dichroics, waveplates, sources)
- Miscellaneous (SLMs)
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
from .dichroics import DichroicItem
from .waveplates import WaveplateItem
from .sources import SourceItem

# Miscellaneous
from .misc import SLMItem

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
    "DichroicItem",
    "WaveplateItem",
    "SourceItem",
    # Miscellaneous
    "SLMItem",
    # Annotations
    "RulerItem",
    "TextNoteItem",
    # Views
    "GraphicsView",
    "ImageCanvas",
]

