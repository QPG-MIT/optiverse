"""
Unified optical interface model.

This module provides the single, unified interface model that replaces both
InterfaceDefinition and RefractiveInterface from the old architecture.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any

from .geometry import LineSegment, CurvedSegment, GeometrySegment
from .optical_properties import (
    OpticalProperties,
    RefractiveProperties,
    LensProperties,
    MirrorProperties,
    BeamsplitterProperties,
    WaveplateProperties,
    DichroicProperties,
)


@dataclass
class OpticalInterface:
    """
    Unified optical interface model.
    
    This single class replaces both InterfaceDefinition and RefractiveInterface
    from the old architecture, providing a type-safe, consistent representation
    of all optical interfaces.
    
    Design:
    - Geometry (LineSegment or CurvedSegment) defines where the interface is
    - Properties (Union type) defines what the interface does
    - Type safety via Union types catches misuse at development time
    """
    geometry: GeometrySegment  # Can be LineSegment or CurvedSegment
    properties: OpticalProperties
    name: str = ""
    
    def get_element_type(self) -> str:
        """
        Get element type string for backward compatibility.
        
        Returns:
            String identifier: "lens", "mirror", "refractive", etc.
        """
        if isinstance(self.properties, LensProperties):
            return "lens"
        elif isinstance(self.properties, MirrorProperties):
            return "mirror"
        elif isinstance(self.properties, RefractiveProperties):
            return "refractive"
        elif isinstance(self.properties, BeamsplitterProperties):
            return "beamsplitter"
        elif isinstance(self.properties, WaveplateProperties):
            return "waveplate"
        elif isinstance(self.properties, DichroicProperties):
            return "dichroic"
        else:
            return "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for JSON storage.
        
        Returns:
            Dictionary with geometry, properties, and metadata
        """
        # Determine property type for deserialization
        property_type = self.get_element_type()
        
        # Serialize properties (convert to dict)
        properties_dict = asdict(self.properties)
        
        return {
            "geometry": self.geometry.to_dict(),
            "properties": properties_dict,
            "property_type": property_type,
            "name": self.name,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OpticalInterface':
        """
        Deserialize from dictionary.
        
        Args:
            data: Dictionary with geometry, properties, property_type, and name
            
        Returns:
            OpticalInterface instance
        """
        # Deserialize geometry
        geometry = LineSegment.from_dict(data["geometry"])
        
        # Deserialize properties based on type
        property_type = data["property_type"]
        properties_data = data["properties"]
        
        if property_type == "lens":
            properties = LensProperties(**properties_data)
        elif property_type == "mirror":
            properties = MirrorProperties(**properties_data)
        elif property_type == "refractive":
            properties = RefractiveProperties(**properties_data)
        elif property_type == "beamsplitter":
            properties = BeamsplitterProperties(**properties_data)
        elif property_type == "waveplate":
            properties = WaveplateProperties(**properties_data)
        elif property_type == "dichroic":
            properties = DichroicProperties(**properties_data)
        else:
            raise ValueError(f"Unknown property type: {property_type}")
        
        return cls(
            geometry=geometry,
            properties=properties,
            name=data.get("name", ""),
        )
    
    @classmethod
    def from_legacy_interface_definition(cls, old_interface) -> 'OpticalInterface':
        """
        Convert from old InterfaceDefinition format to new OpticalInterface.
        
        Args:
            old_interface: Old InterfaceDefinition object
            
        Returns:
            New OpticalInterface object
        """
        import numpy as np
        
        # Create geometry (curved if specified)
        p1 = np.array([old_interface.x1_mm, old_interface.y1_mm])
        p2 = np.array([old_interface.x2_mm, old_interface.y2_mm])
        
        # Check if surface is curved
        is_curved = getattr(old_interface, 'is_curved', False)
        radius = getattr(old_interface, 'radius_of_curvature_mm', 0.0)
        
        if is_curved and abs(radius) > 1e-6:
            # Create curved segment for curved surfaces
            geometry = CurvedSegment(p1, p2, radius)
        else:
            # Create straight line segment for flat surfaces
            geometry = LineSegment(p1, p2)
        
        # Convert properties based on element_type
        element_type = old_interface.element_type
        
        if element_type == "lens":
            properties = LensProperties(efl_mm=old_interface.efl_mm)
        elif element_type == "mirror":
            properties = MirrorProperties(reflectivity=old_interface.reflectivity / 100.0)
        elif element_type in ["beam_splitter", "beamsplitter"]:
            properties = BeamsplitterProperties(
                transmission=old_interface.split_T / 100.0,
                reflection=old_interface.split_R / 100.0,
                is_polarizing=old_interface.is_polarizing,
                polarization_axis_deg=old_interface.pbs_transmission_axis_deg
            )
        elif element_type == "dichroic":
            properties = DichroicProperties(
                cutoff_wavelength_nm=old_interface.cutoff_wavelength_nm,
                transition_width_nm=old_interface.transition_width_nm,
                pass_type=old_interface.pass_type
            )
        elif element_type == "waveplate":
            # Note: waveplate properties might be stored as attributes
            phase_shift = getattr(old_interface, 'phase_shift_deg', 90.0)
            fast_axis = getattr(old_interface, 'fast_axis_deg', 0.0)
            properties = WaveplateProperties(
                phase_shift_deg=phase_shift,
                fast_axis_deg=fast_axis
            )
        elif element_type == "refractive_interface":
            curvature = old_interface.radius_of_curvature_mm if old_interface.is_curved else None
            properties = RefractiveProperties(
                n1=old_interface.n1,
                n2=old_interface.n2,
                curvature_radius_mm=curvature
            )
        else:
            # Default to refractive
            properties = RefractiveProperties(
                n1=getattr(old_interface, 'n1', 1.0),
                n2=getattr(old_interface, 'n2', 1.0)
            )
        
        return cls(
            geometry=geometry,
            properties=properties,
            name=old_interface.name
        )
    
    @classmethod
    def from_legacy_refractive_interface(cls, old_interface) -> 'OpticalInterface':
        """
        Convert from old RefractiveInterface format to new OpticalInterface.
        
        Args:
            old_interface: Old RefractiveInterface object
            
        Returns:
            New OpticalInterface object
        """
        import numpy as np
        
        # Create geometry (curved if specified)
        p1 = np.array([old_interface.x1_mm, old_interface.y1_mm])
        p2 = np.array([old_interface.x2_mm, old_interface.y2_mm])
        
        # Check if surface is curved
        is_curved = getattr(old_interface, 'is_curved', False)
        radius = getattr(old_interface, 'radius_of_curvature_mm', 0.0)
        
        if is_curved and abs(radius) > 1e-6:
            # Create curved segment for curved surfaces
            geometry = CurvedSegment(p1, p2, radius)
        else:
            # Create straight line segment for flat surfaces
            geometry = LineSegment(p1, p2)
        
        # Check if it's a beam splitter or regular refractive interface
        if old_interface.is_beam_splitter:
            properties = BeamsplitterProperties(
                transmission=old_interface.split_T / 100.0,
                reflection=old_interface.split_R / 100.0,
                is_polarizing=old_interface.is_polarizing,
                polarization_axis_deg=old_interface.pbs_transmission_axis_deg
            )
        else:
            properties = RefractiveProperties(
                n1=old_interface.n1,
                n2=old_interface.n2
            )
        
        return cls(
            geometry=geometry,
            properties=properties,
            name=""
        )

