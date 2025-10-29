"""Interface definition data model for generalized component editor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple
import math


@dataclass
class InterfaceDefinition:
    """
    Definition of a single optical interface in a component.
    
    Each interface represents an optical element (lens, mirror, beam splitter, etc.)
    with specific geometry and optical properties.
    
    Coordinates are stored in millimeters in a local coordinate system.
    The optical effect is determined by the spatial position (x, y) of the interface,
    not by the order in the list.
    """
    
    # Geometry (in millimeters, local coordinate system)
    x1_mm: float = 0.0
    y1_mm: float = 0.0
    x2_mm: float = 10.0
    y2_mm: float = 0.0
    
    # Element type
    element_type: str = "refractive_interface"  # lens, mirror, beam_splitter, dichroic, refractive_interface
    
    # Common properties
    name: str = ""  # Optional user-defined name
    
    # Lens properties
    efl_mm: float = 100.0  # Effective focal length
    
    # Mirror properties
    reflectivity: float = 99.0  # Percentage
    
    # Beam splitter properties
    split_T: float = 50.0  # Transmission percentage
    split_R: float = 50.0  # Reflection percentage
    is_polarizing: bool = False
    pbs_transmission_axis_deg: float = 0.0
    
    # Dichroic properties
    cutoff_wavelength_nm: float = 550.0
    transition_width_nm: float = 50.0
    pass_type: str = "longpass"  # "longpass" | "shortpass"
    
    # Refractive interface properties
    n1: float = 1.0  # Incident refractive index
    n2: float = 1.5  # Transmitted refractive index
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'x1_mm': self.x1_mm,
            'y1_mm': self.y1_mm,
            'x2_mm': self.x2_mm,
            'y2_mm': self.y2_mm,
            'element_type': self.element_type,
            'name': self.name,
            'efl_mm': self.efl_mm,
            'reflectivity': self.reflectivity,
            'split_T': self.split_T,
            'split_R': self.split_R,
            'is_polarizing': self.is_polarizing,
            'pbs_transmission_axis_deg': self.pbs_transmission_axis_deg,
            'cutoff_wavelength_nm': self.cutoff_wavelength_nm,
            'transition_width_nm': self.transition_width_nm,
            'pass_type': self.pass_type,
            'n1': self.n1,
            'n2': self.n2,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterfaceDefinition':
        """Deserialize from dictionary."""
        return cls(
            x1_mm=data.get('x1_mm', 0.0),
            y1_mm=data.get('y1_mm', 0.0),
            x2_mm=data.get('x2_mm', 10.0),
            y2_mm=data.get('y2_mm', 0.0),
            element_type=data.get('element_type', 'refractive_interface'),
            name=data.get('name', ''),
            efl_mm=data.get('efl_mm', 100.0),
            reflectivity=data.get('reflectivity', 99.0),
            split_T=data.get('split_T', 50.0),
            split_R=data.get('split_R', 50.0),
            is_polarizing=data.get('is_polarizing', False),
            pbs_transmission_axis_deg=data.get('pbs_transmission_axis_deg', 0.0),
            cutoff_wavelength_nm=data.get('cutoff_wavelength_nm', 550.0),
            transition_width_nm=data.get('transition_width_nm', 50.0),
            pass_type=data.get('pass_type', 'longpass'),
            n1=data.get('n1', 1.0),
            n2=data.get('n2', 1.5),
        )
    
    def get_color(self) -> Tuple[int, int, int]:
        """
        Get display color based on element type.
        
        Returns RGB tuple (0-255 range).
        """
        if self.element_type == 'lens':
            return (0, 180, 180)  # Cyan
        elif self.element_type == 'mirror':
            return (255, 140, 0)  # Orange
        elif self.element_type == 'beam_splitter':
            if self.is_polarizing:
                return (150, 0, 150)  # Purple (PBS)
            else:
                return (0, 150, 120)  # Green (BS)
        elif self.element_type == 'dichroic':
            return (255, 0, 255)  # Magenta
        elif self.element_type == 'refractive_interface':
            # Blue for refractive, gray if same index
            if abs(self.n1 - self.n2) > 0.01:
                return (100, 100, 255)  # Blue
            else:
                return (150, 150, 150)  # Gray
        else:
            return (150, 150, 150)  # Default gray
    
    def get_label(self) -> str:
        """
        Get display label for this interface.
        
        Returns user-defined name if available, otherwise generates
        a descriptive label based on element type and properties.
        """
        if self.name:
            return self.name
        
        if self.element_type == 'lens':
            return f'Lens ({self.efl_mm:.1f}mm)'
        elif self.element_type == 'mirror':
            return 'Mirror'
        elif self.element_type == 'beam_splitter':
            if self.is_polarizing:
                return f'PBS ({self.split_T:.0f}/{self.split_R:.0f})'
            else:
                return f'BS ({self.split_T:.0f}/{self.split_R:.0f})'
        elif self.element_type == 'dichroic':
            return f'Dichroic ({self.cutoff_wavelength_nm:.0f}nm)'
        elif self.element_type == 'refractive_interface':
            return f'n={self.n1:.3f}→{self.n2:.3f}'
        else:
            return 'Interface'
    
    def length_mm(self) -> float:
        """Calculate interface length in millimeters."""
        dx = self.x2_mm - self.x1_mm
        dy = self.y2_mm - self.y1_mm
        return math.sqrt(dx**2 + dy**2)
    
    def angle_deg(self) -> float:
        """
        Calculate interface angle in degrees.
        
        Returns angle from horizontal (0° = horizontal, 90° = vertical).
        """
        dx = self.x2_mm - self.x1_mm
        dy = self.y2_mm - self.y1_mm
        return math.degrees(math.atan2(dy, dx))
    
    def midpoint_mm(self) -> Tuple[float, float]:
        """Calculate midpoint coordinates in millimeters."""
        return (
            (self.x1_mm + self.x2_mm) / 2,
            (self.y1_mm + self.y2_mm) / 2
        )
    
    def copy(self) -> 'InterfaceDefinition':
        """Create a copy of this interface definition."""
        return InterfaceDefinition.from_dict(self.to_dict())

