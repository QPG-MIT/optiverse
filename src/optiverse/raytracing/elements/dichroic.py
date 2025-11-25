"""
Dichroic mirror element implementation.

Implements wavelength-dependent reflection and transmission.
"""


import numpy as np

from ...core.raytracing_math import (
    compute_dichroic_reflectance,
    normalize,
    reflect_vec,
    transform_polarization_mirror,
)
from ..ray import RayState
from .base import IOpticalElement


class DichroicElement(IOpticalElement):
    """
    Dichroic mirror with wavelength-dependent reflection/transmission.

    Reflects short wavelengths and transmits long wavelengths (longpass)
    or vice versa (shortpass).
    """

    def __init__(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        cutoff_wavelength_nm: float,
        transition_width_nm: float,
        pass_type: str = "longpass",
    ):
        """
        Initialize dichroic mirror element.

        Args:
            p1: Start point of dichroic line segment [x, y] in mm
            p2: End point of dichroic line segment [x, y] in mm
            cutoff_wavelength_nm: Cutoff wavelength in nanometers
            transition_width_nm: Width of transition region in nanometers
            pass_type: "longpass" or "shortpass"
        """
        self.p1 = np.array(p1, dtype=float)
        self.p2 = np.array(p2, dtype=float)
        self.cutoff_wavelength_nm = cutoff_wavelength_nm
        self.transition_width_nm = transition_width_nm
        self.pass_type = pass_type

    def get_geometry(self) -> tuple[np.ndarray, np.ndarray]:
        """Get dichroic line segment"""
        return self.p1, self.p2

    def interact(
        self, ray: RayState, hit_point: np.ndarray, normal: np.ndarray, tangent: np.ndarray
    ) -> list[RayState]:
        """
        Split ray based on wavelength.

        Physics:
        - Short wavelengths reflect (longpass) or transmit (shortpass)
        - Long wavelengths transmit (longpass) or reflect (shortpass)
        - Smooth transition over transition_width region
        """
        # Compute wavelength-dependent reflectance and transmittance
        if ray.wavelength_nm > 0:
            R, T = compute_dichroic_reflectance(
                ray.wavelength_nm,
                self.cutoff_wavelength_nm,
                self.transition_width_nm,
                self.pass_type,
            )
        else:
            # No wavelength specified: 50/50 split
            R, T = 0.5, 0.5

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
                polarization=ray.polarization,  # Polarization preserved
                wavelength_nm=ray.wavelength_nm,
                path=ray.path + [hit_point],
                events=ray.events + 1,
            )
            output_rays.append(transmitted_ray)

        # Reflected ray
        if R > MIN_INTENSITY / ray.intensity:
            direction_reflected = normalize(reflect_vec(ray.direction, normal))
            polarization_reflected = transform_polarization_mirror(
                ray.polarization, ray.direction, normal
            )

            reflected_ray = RayState(
                position=hit_point + direction_reflected * EPS_ADV,
                direction=direction_reflected,
                intensity=ray.intensity * R,
                polarization=polarization_reflected,
                wavelength_nm=ray.wavelength_nm,
                path=ray.path + [hit_point],
                events=ray.events + 1,
            )
            output_rays.append(reflected_ray)

        return output_rays

    def get_bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """Get axis-aligned bounding box"""
        min_corner = np.minimum(self.p1, self.p2)
        max_corner = np.maximum(self.p1, self.p2)
        return min_corner, max_corner
