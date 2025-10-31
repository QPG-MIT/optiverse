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
    
    COORDINATE SYSTEM (STORAGE FORMAT):
    - Origin (0,0) is at the IMAGE CENTER
    - X-axis: positive right, negative left
    - Y-axis: positive UP, negative DOWN (Y-up, math/engineering convention)
    - Units: millimeters
    
    The optical effect is determined by the spatial position (x, y) of the interface,
    not by the order in the list.
    """
    
    # Geometry (in millimeters, centered coordinate system, Y-up)
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
    
    # Curved surface properties (for Zemax import)
    is_curved: bool = False  # True if this is a curved surface
    radius_of_curvature_mm: float = 0.0  # Radius of curvature (0 or inf = flat)
    # Center of curvature is calculated from radius and surface position
    # Positive radius: center is to the right (convex from left)
    # Negative radius: center is to the left (concave from left)
    
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
            'is_curved': self.is_curved,
            'radius_of_curvature_mm': self.radius_of_curvature_mm,
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
            is_curved=data.get('is_curved', False),
            radius_of_curvature_mm=data.get('radius_of_curvature_mm', 0.0),
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
    
    def center_of_curvature_mm(self) -> Tuple[float, float]:
        """
        Calculate center of curvature for curved surfaces.
        
        For Zemax convention:
        - Positive radius: center is to the right (convex from left)
        - Negative radius: center is to the left (concave from left)
        
        Returns:
            (x, y) coordinates of center of curvature in mm
        """
        if not self.is_curved or abs(self.radius_of_curvature_mm) < 1e-6:
            # Flat surface: return point at infinity
            return (float('inf'), 0.0)
        
        # Get midpoint of the interface
        mid_x = (self.x1_mm + self.x2_mm) / 2
        mid_y = (self.y1_mm + self.y2_mm) / 2
        
        # Center is along x-axis at distance = radius from midpoint
        center_x = mid_x + self.radius_of_curvature_mm
        center_y = mid_y
        
        return (center_x, center_y)
    
    def is_flat(self) -> bool:
        """Check if surface is flat (not curved)."""
        return not self.is_curved or abs(self.radius_of_curvature_mm) < 1e-6 or math.isinf(self.radius_of_curvature_mm)
    
    def surface_sag_at_y(self, y_mm: float) -> float:
        """
        Calculate surface sag (deviation from flat) at given y-coordinate.
        
        For a spherical surface, the sag is:
            sag = R - sqrt(R² - y²)
        
        where R is radius of curvature and y is distance from optical axis.
        
        Args:
            y_mm: Distance from optical axis in mm
            
        Returns:
            Sag (x-displacement) in mm
        """
        if self.is_flat():
            return 0.0
        
        R = abs(self.radius_of_curvature_mm)
        y_sq = y_mm ** 2
        
        if y_sq > R ** 2:
            # Beyond the surface radius
            return 0.0
        
        sag = R - math.sqrt(R**2 - y_sq)
        
        # Apply sign based on curvature direction
        if self.radius_of_curvature_mm > 0:
            return sag  # Convex from left
        else:
            return -sag  # Concave from left

