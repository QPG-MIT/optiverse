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
from .lenses import LensItem
from .mirrors import MirrorItem
from .beamsplitters import BeamsplitterItem
from .dichroics import DichroicItem
from .waveplates import WaveplateItem
from .sources import SourceItem
from .refractive import RefractiveObjectItem
from .blocks.block_item import BlockItem

# Miscellaneous
from .misc import SLMItem

# Background/decorative items
from .background import BackgroundItem

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
    # Optical elements
    "LensItem",
    "MirrorItem",
    "BeamsplitterItem",
    "DichroicItem",
    "WaveplateItem",
    "SourceItem",
    "RefractiveObjectItem",
    "BlockItem",
    # Miscellaneous
    "SLMItem",
    # Background/decorative items
    "BackgroundItem",
    # Annotations
    "RulerItem",
    "TextNoteItem",
    "RectangleItem",
    # Views
    "GraphicsView",
    "ImageCanvas",
]

