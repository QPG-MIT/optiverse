"""
Waveplate element implementation.

Implements phase shift between orthogonal polarization components.
"""
from typing import List, Tuple
import numpy as np
import math

from .base import IOpticalElement
from ..ray import RayState
from ...core.raytracing_math import normalize, deg2rad, transform_polarization_waveplate


class WaveplateElement(IOpticalElement):
    """
    Waveplate element with configurable phase shift and fast axis.
    
    Introduces phase shift between polarization components:
    - Quarter waveplate (QWP): 90° phase shift
    - Half waveplate (HWP): 180° phase shift
    """
    
    def __init__(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        phase_shift_deg: float,
        fast_axis_deg: float,
        waveplate_angle_deg: float = 90.0
    ):
        """
        Initialize waveplate element.
        
        Args:
            p1: Start point of waveplate line segment [x, y] in mm
            p2: End point of waveplate line segment [x, y] in mm
            phase_shift_deg: Phase shift in degrees (90° for QWP, 180° for HWP)
            fast_axis_deg: Fast axis angle in lab frame (degrees, absolute)
            waveplate_angle_deg: Orientation angle of waveplate for directionality (degrees)
        """
        self.p1 = np.array(p1, dtype=float)
        self.p2 = np.array(p2, dtype=float)
        self.phase_shift_deg = phase_shift_deg
        self.fast_axis_deg = fast_axis_deg
        self.waveplate_angle_deg = waveplate_angle_deg
    
    def get_geometry(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get waveplate line segment"""
        return self.p1, self.p2
    
    def interact(
        self,
        ray: RayState,
        hit_point: np.ndarray,
        normal: np.ndarray,
        tangent: np.ndarray
    ) -> List[RayState]:
        """
        Apply waveplate transformation to polarization.
        
        Physics:
        - Introduces phase shift between fast and slow axis components
        - Direction matters: forward (+δ) vs backward (-δ)
        - Ray direction unchanged (waveplate doesn't deflect ray)
        """
        # Determine forward/backward direction
        # Waveplate's intrinsic orientation angle defines its forward normal
        waveplate_angle_rad = deg2rad(self.waveplate_angle_deg)
        
        # Compute forward normal (perpendicular to waveplate)
        # For vertical waveplate (90°): normal points LEFT (-1, 0)
        # For horizontal waveplate (0°): normal points UP (0, 1)
        forward_normal = np.array([
            -math.sin(waveplate_angle_rad),
            math.cos(waveplate_angle_rad)
        ])
        
        # Ray hits from forward side if traveling against the normal
        dot_v_n = float(np.dot(ray.direction, forward_normal))
        is_forward = dot_v_n < 0  # Traveling against normal = forward
        
        # Apply waveplate transformation
        polarization_out = transform_polarization_waveplate(
            ray.polarization,
            self.phase_shift_deg,
            self.fast_axis_deg,
            is_forward
        )
        
        # Ray continues in same direction with transformed polarization
        EPS_ADV = 1e-3
        direction_out = normalize(ray.direction)
        
        output_ray = RayState(
            position=hit_point + direction_out * EPS_ADV,
            direction=direction_out,
            intensity=ray.intensity,  # No loss in ideal waveplate
            polarization=polarization_out,
            wavelength_nm=ray.wavelength_nm,
            path=ray.path + [hit_point],
            events=ray.events + 1
        )
        
        return [output_ray]
    
    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get axis-aligned bounding box"""
        min_corner = np.minimum(self.p1, self.p2)
        max_corner = np.maximum(self.p1, self.p2)
        return min_corner, max_corner

