"""
Adapter for converting between legacy interfaces and new polymorphic elements.

Architecture:
    Legacy System → OpticalInterface (Phase 1) → IOpticalElement (Phase 2)

This adapter bridges the old and new systems, enabling gradual migration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# Phase 1: Unified interface model
from ..data import OpticalInterface
from ..data.optical_properties import (
    BeamBlockProperties,
    BeamsplitterProperties,
    DichroicProperties,
    LensProperties,
    MirrorProperties,
    RefractiveProperties,
    WaveplateProperties,
)

# Phase 2: Polymorphic elements
from ..raytracing.elements import (
    BeamBlock,
    Beamsplitter,
    Dichroic,
    IOpticalElement,
    Lens,
    Mirror,
    RefractiveInterfaceElement,
    Waveplate,
)

_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..core.interface_definition import InterfaceDefinition
    from ..core.models import RefractiveInterface


def create_polymorphic_element(optical_iface: OpticalInterface) -> IOpticalElement:
    """
    Convert an OpticalInterface (Phase 1) to a polymorphic IOpticalElement (Phase 2).

    This is the key adapter function that bridges the data model to the raytracing engine.

    Args:
        optical_iface: An OpticalInterface object (from Phase 1)

    Returns:
        A concrete IOpticalElement subclass instance (Mirror, Lens, etc.)

    Raises:
        ValueError: If the interface type is unknown
    """
    element_type = optical_iface.get_element_type()
    properties = optical_iface.properties

    # Extract p1 and p2 from geometry

    if element_type == "mirror":
        assert isinstance(properties, MirrorProperties)
        return Mirror(optical_iface)

    elif element_type == "lens":
        assert isinstance(properties, LensProperties)
        return Lens(optical_iface)

    elif element_type == "refractive" or element_type == "refractive_interface":
        assert isinstance(properties, RefractiveProperties)
        return RefractiveInterfaceElement(optical_iface)

    elif element_type == "beamsplitter":
        assert isinstance(properties, BeamsplitterProperties)
        return Beamsplitter(optical_iface)

    elif element_type == "waveplate":
        assert isinstance(properties, WaveplateProperties)
        return Waveplate(optical_iface)

    elif element_type == "dichroic":
        assert isinstance(properties, DichroicProperties)
        return Dichroic(optical_iface)

    elif element_type == "beam_block":
        assert isinstance(properties, BeamBlockProperties)
        return BeamBlock(optical_iface)

    else:
        raise ValueError(f"Unknown element type: {element_type}")


def convert_legacy_interface_to_optical(
    legacy_iface: InterfaceDefinition | RefractiveInterface,
) -> OpticalInterface:
    """
    Convert a legacy interface (InterfaceDefinition or RefractiveInterface) to OpticalInterface.

    This uses the converters built into OpticalInterface in Phase 1.

    Args:
        legacy_iface: A legacy InterfaceDefinition or RefractiveInterface

    Returns:
        An OpticalInterface object
    """
    from ..core.interface_definition import InterfaceDefinition
    from ..core.models import RefractiveInterface

    if isinstance(legacy_iface, InterfaceDefinition):
        return OpticalInterface.from_legacy_interface_definition(legacy_iface)
    elif isinstance(legacy_iface, RefractiveInterface):
        return OpticalInterface.from_legacy_refractive_interface(legacy_iface)
    else:
        raise TypeError(f"Unknown legacy interface type: {type(legacy_iface)}")


def convert_legacy_interfaces(
    legacy_interfaces: list[InterfaceDefinition | RefractiveInterface],
) -> list[IOpticalElement]:
    """
    Convert a list of legacy interfaces to polymorphic elements.

    This is the main adapter function for batch conversion.

    Args:
        legacy_interfaces: List of InterfaceDefinition or RefractiveInterface objects

    Returns:
        List of IOpticalElement objects ready for raytracing
    """
    elements = []

    for legacy_iface in legacy_interfaces:
        # Step 1: Legacy → OpticalInterface
        optical_iface = convert_legacy_interface_to_optical(legacy_iface)

        # Step 2: OpticalInterface → IOpticalElement
        element = create_polymorphic_element(optical_iface)

        elements.append(element)

    return elements


def convert_scene_to_polymorphic(scene_items) -> list[IOpticalElement]:
    """
    Convert all optical elements from a QGraphicsScene to polymorphic elements.

    This mimics the logic in MainWindow.retrace() but outputs polymorphic elements.

    Args:
        scene_items: Items from a QGraphicsScene (typically scene.items())

    Returns:
        List of IOpticalElement objects ready for raytracing
    """
    elements = []

    for item in scene_items:
        # Check if item has get_interfaces_scene() method
        if hasattr(item, "get_interfaces_scene") and callable(item.get_interfaces_scene):
            try:
                interfaces_scene = item.get_interfaces_scene()

                # Each interface is a tuple: (p1, p2, iface)
                # CRITICAL: p1 and p2 are CURRENT scene coordinates (updated when item moves)
                # The iface object has STALE coordinates, so we must use the current p1, p2!
                for p1, p2, iface in interfaces_scene:
                    # Convert legacy interface to OpticalInterface
                    optical_iface = convert_legacy_interface_to_optical(iface)

                    # UPDATE geometry with CURRENT scene coordinates
                    # This is essential for dynamic updates when items move!
                    # We must CREATE NEW geometry objects to ensure derived values
                    # (like center of curvature) are recalculated correctly.
                    from ..data.geometry import CurvedSegment, LineSegment

                    if (
                        hasattr(optical_iface.geometry, "is_curved")
                        and optical_iface.geometry.is_curved
                    ):
                        # For curved geometry, create new CurvedSegment with updated endpoints
                        # This ensures the center of curvature is recalculated
                        optical_iface.geometry = CurvedSegment(
                            p1=p1,
                            p2=p2,
                            radius_of_curvature_mm=optical_iface.geometry.radius_of_curvature_mm,
                        )
                    else:
                        # For flat geometry, create new LineSegment
                        optical_iface.geometry = LineSegment(p1=p1, p2=p2)

                    # Convert OpticalInterface to polymorphic element
                    element = create_polymorphic_element(optical_iface)

                    elements.append(element)

            except Exception as e:
                # Log error but continue with other components
                _logger.warning("Error converting %s: %s", type(item).__name__, e, exc_info=True)
                continue

    return elements
