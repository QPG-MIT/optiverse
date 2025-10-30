"""
Lens element implementation.

Implements thin lens approximation using paraxial optics.
"""
from typing import List, Tuple
import numpy as np
import math

from .base import IOpticalElement
from ..ray import RayState
from ...core.geometry import normalize


class LensElement(IOpticalElement):
    """
    Thin lens element using paraxial approximation.
    
    Uses the thin lens equation to deflect rays based on their height
    off the optical axis.
    """
    
    def __init__(self, p1: np.ndarray, p2: np.ndarray, efl_mm: float):
        """
        Initialize lens element.
        
        Args:
            p1: Start point of lens line segment [x, y] in mm
            p2: End point of lens line segment [x, y] in mm
            efl_mm: Effective focal length in mm
        """
        self.p1 = np.array(p1, dtype=float)
        self.p2 = np.array(p2, dtype=float)
        self.efl_mm = efl_mm
    
    def get_geometry(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get lens line segment"""
        return self.p1, self.p2
    
    def interact(
        self,
        ray: RayState,
        hit_point: np.ndarray,
        normal: np.ndarray,
        tangent: np.ndarray
    ) -> List[RayState]:
        """
        Deflect ray using thin lens equation.
        
        Physics:
        - Thin lens approximation: θ_out = θ_in - y/f
        - where y is height off optical axis, f is focal length
        - Polarization unchanged through ideal lens
        """
        # Compute ray height on lens (distance from center along tangent)
        center = 0.5 * (self.p1 + self.p2)
        y = float(np.dot(hit_point - center, tangent))
        
        # Decompose ray direction into normal and tangent components
        a_n = float(np.dot(ray.direction, normal))
        a_t = float(np.dot(ray.direction, tangent))
        
        # Compute incident angle
        theta_in = math.atan2(a_t, a_n)
        
        # Apply thin lens equation: θ_out = θ_in - y/f
        if abs(self.efl_mm) > 1e-12:
            theta_out = theta_in - (y / self.efl_mm)
        else:
            theta_out = theta_in  # Infinite focal length = no deflection
        
        # Reconstruct direction from angle
        direction_out = normalize(
            math.cos(theta_out) * normal + math.sin(theta_out) * tangent
        )
        
        # Polarization unchanged through ideal lens
        EPS_ADV = 1e-3
        refracted_ray = RayState(
            position=hit_point + direction_out * EPS_ADV,
            direction=direction_out,
            intensity=ray.intensity,  # No loss in ideal lens
            polarization=ray.polarization,  # Unchanged
            wavelength_nm=ray.wavelength_nm,
            path=ray.path + [hit_point],
            events=ray.events + 1
        )
        
        return [refracted_ray]
    
    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get axis-aligned bounding box"""
        min_corner = np.minimum(self.p1, self.p2)
        max_corner = np.maximum(self.p1, self.p2)
        return min_corner, max_corner

