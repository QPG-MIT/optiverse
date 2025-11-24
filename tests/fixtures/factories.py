"""
Factory fixtures for creating test objects.

These factories create properly configured optical items for testing,
avoiding the need to manually construct items with all their parameters.
"""
from __future__ import annotations

from typing import List, Optional

from PyQt6 import QtWidgets


def create_source_item(
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    angle_deg: float = 0.0,
    num_rays: int = 5,
    divergence_deg: float = 10.0,
    wavelength_nm: float = 550.0,
) -> "SourceItem":
    """
    Create a SourceItem with specified parameters.
    
    Args:
        x_mm: X position in mm
        y_mm: Y position in mm
        angle_deg: Emission angle in degrees (0 = right)
        num_rays: Number of rays to emit
        divergence_deg: Angular spread of rays
        wavelength_nm: Wavelength in nanometers
        
    Returns:
        Configured SourceItem
    """
    from optiverse.core.models import SourceParams
    from optiverse.objects import SourceItem
    
    params = SourceParams(
        x_mm=x_mm,
        y_mm=y_mm,
        angle_deg=angle_deg,
        num_rays=num_rays,
        divergence_deg=divergence_deg,
        wavelength_nm=wavelength_nm,
    )
    return SourceItem(params)


def create_lens_item(
    x_mm: float = 100.0,
    y_mm: float = 0.0,
    angle_deg: float = 90.0,
    object_height_mm: float = 60.0,
    efl_mm: float = 50.0,
) -> "LensItem":
    """
    Create a LensItem with specified parameters.
    
    Args:
        x_mm: X position in mm
        y_mm: Y position in mm
        angle_deg: Orientation angle in degrees (90 = vertical)
        object_height_mm: Height of the lens in mm
        efl_mm: Effective focal length in mm
        
    Returns:
        Configured LensItem
    """
    from optiverse.core.models import LensParams
    from optiverse.objects import LensItem
    
    params = LensParams(
        x_mm=x_mm,
        y_mm=y_mm,
        angle_deg=angle_deg,
        object_height_mm=object_height_mm,
        efl_mm=efl_mm,
    )
    return LensItem(params)


def create_mirror_item(
    x_mm: float = 200.0,
    y_mm: float = 0.0,
    angle_deg: float = 45.0,
    object_height_mm: float = 80.0,
) -> "MirrorItem":
    """
    Create a MirrorItem with specified parameters.
    
    Args:
        x_mm: X position in mm
        y_mm: Y position in mm
        angle_deg: Orientation angle in degrees
        object_height_mm: Height of the mirror in mm
        
    Returns:
        Configured MirrorItem
    """
    from optiverse.core.models import MirrorParams
    from optiverse.objects import MirrorItem
    
    params = MirrorParams(
        x_mm=x_mm,
        y_mm=y_mm,
        angle_deg=angle_deg,
        object_height_mm=object_height_mm,
    )
    return MirrorItem(params)


def create_component_item(
    name: str = "Test Component",
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    angle_deg: float = 0.0,
    object_height_mm: float = 60.0,
    interfaces: Optional[List] = None,
) -> "ComponentItem":
    """
    Create a generic ComponentItem with specified parameters.
    
    Args:
        name: Component name
        x_mm: X position in mm
        y_mm: Y position in mm
        angle_deg: Orientation angle in degrees
        object_height_mm: Height of the component in mm
        interfaces: Optional list of InterfaceDefinition objects
        
    Returns:
        Configured ComponentItem
    """
    from optiverse.core.models import ComponentParams
    from optiverse.objects.generic import ComponentItem
    
    params = ComponentParams(
        name=name,
        x_mm=x_mm,
        y_mm=y_mm,
        angle_deg=angle_deg,
        object_height_mm=object_height_mm,
        interfaces=interfaces or [],
    )
    return ComponentItem(params)


def create_scene_with_items(
    items: Optional[List] = None,
) -> QtWidgets.QGraphicsScene:
    """
    Create a QGraphicsScene with optional pre-added items.
    
    Args:
        items: Optional list of items to add to the scene
        
    Returns:
        QGraphicsScene with items added
    """
    from optiverse.core.constants import SCENE_SIZE_MM, SCENE_MIN_COORD
    
    scene = QtWidgets.QGraphicsScene()
    scene.setSceneRect(
        SCENE_MIN_COORD,
        SCENE_MIN_COORD,
        SCENE_SIZE_MM,
        SCENE_SIZE_MM,
    )
    
    if items:
        for item in items:
            scene.addItem(item)
    
    return scene


def create_basic_optical_setup() -> tuple:
    """
    Create a basic optical setup: source -> lens -> mirror.
    
    Returns:
        Tuple of (scene, source, lens, mirror)
    """
    source = create_source_item(x_mm=-100, y_mm=0, angle_deg=0)
    lens = create_lens_item(x_mm=0, y_mm=0, angle_deg=90, efl_mm=50)
    mirror = create_mirror_item(x_mm=100, y_mm=0, angle_deg=45)
    
    scene = create_scene_with_items([source, lens, mirror])
    return scene, source, lens, mirror

