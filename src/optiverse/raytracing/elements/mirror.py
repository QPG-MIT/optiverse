"""
Mirror element implementation.

Implements perfect reflection according to the law of reflection.
"""

import numpy as np

from ...core.models import Polarization
from ...core.raytracing_math import normalize, reflect_vec
from ..ray import RayState
from .base import IOpticalElement


def transform_polarization_mirror(
    pol: Polarization, v_in: np.ndarray, n_hat: np.ndarray
) -> Polarization:
    """Transform polarization upon mirror reflection (reuse from core)"""
    from ...core.raytracing_math import transform_polarization_mirror as core_transform

    return core_transform(pol, v_in, n_hat)


class MirrorElement(IOpticalElement):
    """
    Mirror element with configurable reflectivity.

    Implements the law of reflection: angle of incidence = angle of reflection
    """

    def __init__(self, p1: np.ndarray, p2: np.ndarray, reflectivity: float = 1.0):
        """
        Initialize mirror element.

        Args:
            p1: Start point of mirror line segment [x, y] in mm
            p2: End point of mirror line segment [x, y] in mm
            reflectivity: Fraction of light reflected (0.0 to 1.0)
        """
        self.p1 = np.array(p1, dtype=float)
        self.p2 = np.array(p2, dtype=float)
        self.reflectivity = reflectivity

    def get_geometry(self) -> tuple[np.ndarray, np.ndarray]:
        """Get mirror line segment"""
        return self.p1, self.p2

    def interact(
        self, ray: RayState, hit_point: np.ndarray, normal: np.ndarray, tangent: np.ndarray
    ) -> list[RayState]:
        """
        Reflect ray according to law of reflection.

        Physics:
        - Angle of incidence = angle of reflection
        - Intensity reduced by reflectivity
        - Polarization transformed (s-pol maintained, p-pol gets π phase shift)
        """
        # Compute reflected direction
        direction_reflected = normalize(reflect_vec(ray.direction, normal))

        # Transform polarization
        polarization_reflected = transform_polarization_mirror(
            ray.polarization, ray.direction, normal
        )

        # Create reflected ray
        EPS_ADV = 1e-3  # Small advancement to avoid self-intersection
        reflected_ray = RayState(
            position=hit_point + direction_reflected * EPS_ADV,
            direction=direction_reflected,
            intensity=ray.intensity * self.reflectivity,
            polarization=polarization_reflected,
            wavelength_nm=ray.wavelength_nm,
            path=ray.path + [hit_point],
            events=ray.events + 1,
        )

        return [reflected_ray]

    def get_bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """Get axis-aligned bounding box"""
        min_corner = np.minimum(self.p1, self.p2)
        max_corner = np.maximum(self.p1, self.p2)
        return min_corner, max_corner
