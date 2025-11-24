"""
Adapter for converting between legacy interfaces and new polymorphic elements.

Architecture:
    Legacy System → OpticalInterface (Phase 1) → IOpticalElement (Phase 2)
    
This adapter bridges the old and new systems, enabling gradual migration.
"""
from __future__ import annotations
from typing import List, Union, TYPE_CHECKING
import numpy as np

# Phase 1: Unified interface model
from ..data import OpticalInterface, LineSegment, CurvedSegment, GeometrySegment
from ..data.optical_properties import (
    LensProperties,
    MirrorProperties,
    RefractiveProperties,
    BeamsplitterProperties,
    WaveplateProperties,
    DichroicProperties,
)

# Phase 2: Polymorphic elements
from ..raytracing.elements import (
    IOpticalElement,
    Mirror,
    Lens,
    RefractiveInterfaceElement,
    Beamsplitter,
    Waveplate,
    Dichroic,
)

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
    geometry = optical_iface.geometry
    
    # Extract p1 and p2 from geometry
    p1 = geometry.p1
    p2 = geometry.p2
    
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
    
    else:
        raise ValueError(f"Unknown element type: {element_type}")


def convert_legacy_interface_to_optical(
    legacy_iface: Union['InterfaceDefinition', 'RefractiveInterface']
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
    legacy_interfaces: List[Union['InterfaceDefinition', 'RefractiveInterface']]
) -> List[IOpticalElement]:
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


def convert_scene_to_polymorphic(scene_items) -> List[IOpticalElement]:
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
        if hasattr(item, 'get_interfaces_scene') and callable(item.get_interfaces_scene):
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
                    if hasattr(optical_iface.geometry, 'is_curved') and optical_iface.geometry.is_curved:
                        # For curved geometry, preserve radius and curvature
                        optical_iface.geometry.p1 = p1
                        optical_iface.geometry.p2 = p2
                    else:
                        # For flat geometry, just update endpoints
                        optical_iface.geometry.p1 = p1
                        optical_iface.geometry.p2 = p2
                    
                    # Convert OpticalInterface to polymorphic element
                    element = create_polymorphic_element(optical_iface)
                    
                    elements.append(element)
                    
            except Exception as e:
                # Log error but continue with other components
                print(f"Warning: Error converting {type(item).__name__}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    return elements


def create_legacy_optical_element_from_interface(
    p1: np.ndarray,
    p2: np.ndarray,
    iface: Union['InterfaceDefinition', 'RefractiveInterface']
) -> 'OpticalElement':
    """
    Create a legacy OpticalElement from an interface.
    
    This is the OLD conversion path (what currently exists in MainWindow._create_element_from_interface).
    We keep this for backward compatibility during the migration period.
    
    Args:
        p1: Start point in scene coordinates
        p2: End point in scene coordinates
        iface: InterfaceDefinition or RefractiveInterface
    
    Returns:
        A legacy OpticalElement object
    """
    from ..core.models import OpticalElement, RefractiveInterface
    
    # Handle legacy RefractiveInterface objects
    if isinstance(iface, RefractiveInterface):
        elem = OpticalElement(
            kind="refractive_interface",
            p1=p1,
            p2=p2
        )
        elem.n1 = iface.n1
        elem.n2 = iface.n2
        elem.is_beam_splitter = iface.is_beam_splitter
        if elem.is_beam_splitter:
            elem.split_T = iface.split_T
            elem.split_R = iface.split_R
            elem.is_polarizing = iface.is_polarizing
            elem.pbs_transmission_axis_deg = iface.pbs_transmission_axis_deg
        return elem
    
    # Handle InterfaceDefinition objects
    element_type = iface.element_type
    
    if element_type == "lens":
        return OpticalElement(
            kind="lens",
            p1=p1,
            p2=p2,
            efl_mm=iface.efl_mm
        )
    
    elif element_type == "mirror":
        return OpticalElement(
            kind="mirror",
            p1=p1,
            p2=p2
        )
    
    elif element_type in ["beam_splitter", "beamsplitter"]:
        return OpticalElement(
            kind="bs",
            p1=p1,
            p2=p2,
            split_T=iface.split_T,
            split_R=iface.split_R,
            is_polarizing=iface.is_polarizing,
            pbs_transmission_axis_deg=iface.pbs_transmission_axis_deg
        )
    
    elif element_type == "dichroic":
        return OpticalElement(
            kind="dichroic",
            p1=p1,
            p2=p2,
            cutoff_wavelength_nm=iface.cutoff_wavelength_nm,
            transition_width_nm=iface.transition_width_nm,
            pass_type=iface.pass_type
        )
    
    elif element_type == "polarizing_interface":
        # Handle polarizing interface (currently only waveplates are implemented)
        if iface.polarizer_subtype == "waveplate":
            # Get angle_deg from parent item if available
            angle_deg = 0.0
            if hasattr(iface, 'angle_deg'):
                angle_deg = iface.angle_deg
            
            return OpticalElement(
                kind="waveplate",
                p1=p1,
                p2=p2,
                phase_shift_deg=iface.phase_shift_deg,
                fast_axis_deg=iface.fast_axis_deg,
                angle_deg=angle_deg
            )
        else:
            # Future: handle other polarizer subtypes
            raise ValueError(f"Unsupported polarizer subtype: {iface.polarizer_subtype}")
    
    elif element_type == "waveplate":
        # Legacy support for old "waveplate" element type
        phase_shift_deg = getattr(iface, 'phase_shift_deg', 90.0)
        fast_axis_deg = getattr(iface, 'fast_axis_deg', 0.0)
        angle_deg = 0.0
        
        return OpticalElement(
            kind="waveplate",
            p1=p1,
            p2=p2,
            phase_shift_deg=phase_shift_deg,
            fast_axis_deg=fast_axis_deg,
            angle_deg=angle_deg
        )
    
    elif element_type == "refractive_interface":
        elem = OpticalElement(
            kind="refractive_interface",
            p1=p1,
            p2=p2
        )
        elem.n1 = iface.n1
        elem.n2 = iface.n2
        elem.is_curved = getattr(iface, 'is_curved', False)
        elem.radius_of_curvature_mm = getattr(iface, 'radius_of_curvature_mm', 0.0)
        return elem
    
    else:
        # Unknown type - return None or raise error
        return None

