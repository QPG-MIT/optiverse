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
) -> "ComponentItem":
    """
    Create a ComponentItem with lens interface.

    Args:
        x_mm: X position in mm
        y_mm: Y position in mm
        angle_deg: Orientation angle in degrees (90 = vertical)
        object_height_mm: Height of the lens in mm
        efl_mm: Effective focal length in mm

    Returns:
        Configured ComponentItem with lens interface
    """
    from optiverse.core.models import ComponentParams
    from optiverse.core.interface_definition import InterfaceDefinition
    from optiverse.objects import ComponentItem

    # Create lens interface
    half_height = object_height_mm / 2.0
    interface = InterfaceDefinition(
        x1_mm=0.0,
        y1_mm=-half_height,
        x2_mm=0.0,
        y2_mm=half_height,
        element_type="lens",
        efl_mm=efl_mm,
    )

    params = ComponentParams(
        x_mm=x_mm,
        y_mm=y_mm,
        angle_deg=angle_deg,
        object_height_mm=object_height_mm,
        interfaces=[interface],
    )
    return ComponentItem(params)


def create_mirror_item(
    x_mm: float = 200.0,
    y_mm: float = 0.0,
    angle_deg: float = 45.0,
    object_height_mm: float = 80.0,
) -> "ComponentItem":
    """
    Create a ComponentItem with mirror interface.

    Args:
        x_mm: X position in mm
        y_mm: Y position in mm
        angle_deg: Orientation angle in degrees
        object_height_mm: Height of the mirror in mm

    Returns:
        Configured ComponentItem with mirror interface
    """
    from optiverse.core.models import ComponentParams
    from optiverse.core.interface_definition import InterfaceDefinition
    from optiverse.objects import ComponentItem

    # Create mirror interface
    half_height = object_height_mm / 2.0
    interface = InterfaceDefinition(
        x1_mm=0.0,
        y1_mm=-half_height,
        x2_mm=0.0,
        y2_mm=half_height,
        element_type="mirror",
        reflectivity=100.0,
    )

    params = ComponentParams(
        x_mm=x_mm,
        y_mm=y_mm,
        angle_deg=angle_deg,
        object_height_mm=object_height_mm,
        interfaces=[interface],
    )
    return ComponentItem(params)


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


def create_component_from_params(params) -> "ComponentItem":
    """
    Create a ComponentItem from legacy params (LensParams, MirrorParams, etc.).

    This is a compatibility helper for tests that use legacy params classes.

    Args:
        params: LensParams, MirrorParams, BeamsplitterParams, etc.

    Returns:
        ComponentItem with appropriate interfaces
    """
    from optiverse.core.models import ComponentParams
    from optiverse.core.interface_definition import InterfaceDefinition
    from optiverse.objects import ComponentItem

    # Determine component type and create appropriate interface
    half_height = params.object_height_mm / 2.0

    if hasattr(params, 'efl_mm'):
        # LensParams
        interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-half_height,
            x2_mm=0.0,
            y2_mm=half_height,
            element_type="lens",
            efl_mm=params.efl_mm,
        )
    elif hasattr(params, 'split_T'):
        # BeamsplitterParams
        interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-half_height,
            x2_mm=0.0,
            y2_mm=half_height,
            element_type="beam_splitter",
            split_T=params.split_T,
            split_R=params.split_R,
            is_polarizing=getattr(params, 'is_polarizing', False),
            pbs_transmission_axis_deg=getattr(params, 'pbs_transmission_axis_deg', 0.0),
        )
    elif hasattr(params, 'reflectivity'):
        # MirrorParams
        interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-half_height,
            x2_mm=0.0,
            y2_mm=half_height,
            element_type="mirror",
            reflectivity=getattr(params, 'reflectivity', 100.0),
        )
    elif hasattr(params, 'cutoff_wavelength_nm'):
        # DichroicParams
        interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-half_height,
            x2_mm=0.0,
            y2_mm=half_height,
            element_type="dichroic",
            cutoff_wavelength_nm=params.cutoff_wavelength_nm,
            transition_width_nm=getattr(params, 'transition_width_nm', 50.0),
            pass_type=getattr(params, 'pass_type', 'longpass'),
        )
    elif hasattr(params, 'phase_shift_deg'):
        # WaveplateParams
        interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-half_height,
            x2_mm=0.0,
            y2_mm=half_height,
            element_type="waveplate",
            phase_shift_deg=params.phase_shift_deg,
            fast_axis_deg=getattr(params, 'fast_axis_deg', 0.0),
        )
    else:
        # Unknown - create empty component
        interface = None

    component_params = ComponentParams(
        x_mm=params.x_mm,
        y_mm=params.y_mm,
        angle_deg=params.angle_deg,
        object_height_mm=params.object_height_mm,
        name=getattr(params, 'name', None),
        image_path=getattr(params, 'image_path', None),
        mm_per_pixel=getattr(params, 'mm_per_pixel', 0.1),
        interfaces=[interface] if interface else [],
    )
    return ComponentItem(component_params)


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



