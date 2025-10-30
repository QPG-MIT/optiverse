"""
Beamsplitter element implementation.

Implements partial reflection and transmission, with optional polarization dependence (PBS).
"""
from typing import List, Tuple
import numpy as np

from .base import IOpticalElement
from ..ray import RayState
from ...core.geometry import (
    normalize, reflect_vec,
    transform_polarization_beamsplitter
)


class BeamsplitterElement(IOpticalElement):
    """
    Beamsplitter element with configurable split ratio.
    
    Can be non-polarizing (splits by intensity) or polarizing (PBS).
    """
    
    def __init__(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        transmission: float,
        reflection: float,
        is_polarizing: bool = False,
        polarization_axis_deg: float = 0.0
    ):
        """
        Initialize beamsplitter element.
        
        Args:
            p1: Start point of beamsplitter line segment [x, y] in mm
            p2: End point of beamsplitter line segment [x, y] in mm
            transmission: Transmission coefficient (0.0 to 1.0)
            reflection: Reflection coefficient (0.0 to 1.0)
            is_polarizing: True for PBS (Polarizing Beam Splitter)
            polarization_axis_deg: Transmission axis angle for PBS (degrees, absolute)
        """
        self.p1 = np.array(p1, dtype=float)
        self.p2 = np.array(p2, dtype=float)
        self.transmission = transmission
        self.reflection = reflection
        self.is_polarizing = is_polarizing
        self.polarization_axis_deg = polarization_axis_deg
    
    def get_geometry(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get beamsplitter line segment"""
        return self.p1, self.p2
    
    def interact(
        self,
        ray: RayState,
        hit_point: np.ndarray,
        normal: np.ndarray,
        tangent: np.ndarray
    ) -> List[RayState]:
        """
        Split ray into transmitted and reflected components.
        
        Physics:
        - Non-polarizing BS: Split by intensity only
        - Polarizing BS (PBS): Split by polarization
            * s-polarization (perpendicular) reflects
            * p-polarization (parallel) transmits
        """
        # Transform polarization for both paths
        polarization_transmitted, intensity_factor_transmitted = transform_polarization_beamsplitter(
            ray.polarization,
            ray.direction,
            normal,
            tangent,
            self.is_polarizing,
            self.polarization_axis_deg,
            is_transmitted=True
        )
        
        polarization_reflected, intensity_factor_reflected = transform_polarization_beamsplitter(
            ray.polarization,
            ray.direction,
            normal,
            tangent,
            self.is_polarizing,
            self.polarization_axis_deg,
            is_transmitted=False
        )
        
        # Determine split ratios
        if self.is_polarizing:
            # PBS: split determined by polarization
            T = intensity_factor_transmitted
            R = intensity_factor_reflected
        else:
            # Non-polarizing: use configured ratios
            T = self.transmission
            R = self.reflection
        
        output_rays = []
        EPS_ADV = 1e-3
        MIN_INTENSITY = 0.02
        
        # Transmitted ray
        if T > MIN_INTENSITY / ray.intensity:
            direction_transmitted = normalize(ray.direction)
            
            transmitted_ray = RayState(
                position=hit_point + direction_transmitted * EPS_ADV,
                direction=direction_transmitted,
                intensity=ray.intensity * T,
                polarization=polarization_transmitted,
                wavelength_nm=ray.wavelength_nm,
                path=ray.path + [hit_point],
                events=ray.events + 1
            )
            output_rays.append(transmitted_ray)
        
        # Reflected ray
        if R > MIN_INTENSITY / ray.intensity:
            direction_reflected = normalize(reflect_vec(ray.direction, normal))
            
            reflected_ray = RayState(
                position=hit_point + direction_reflected * EPS_ADV,
                direction=direction_reflected,
                intensity=ray.intensity * R,
                polarization=polarization_reflected,
                wavelength_nm=ray.wavelength_nm,
                path=ray.path + [hit_point],
                events=ray.events + 1
            )
            output_rays.append(reflected_ray)
        
        return output_rays
    
    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get axis-aligned bounding box"""
        min_corner = np.minimum(self.p1, self.p2)
        max_corner = np.maximum(self.p1, self.p2)
        return min_corner, max_corner

