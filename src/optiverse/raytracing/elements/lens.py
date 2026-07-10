"""
Lens element implementation.

Implements an ideal thin lens using the exact (non-paraxial) deflection formula.
"""

import math

import numpy as np

from ...core.raytracing_math import normalize
from ..ray import RayState
from .base import IOpticalElement


class LensElement(IOpticalElement):
    """
    Ideal thin lens element (non-paraxial).

    Uses the exact deflection formula: θ_out = θ_in - arctan(y/f)
    which produces perfect focusing at all ray heights, not just near
    the optical axis. The paraxial approximation θ_out = θ_in - y/f
    is the small-angle linearization that introduces spurious aberration
    at large impact parameters.
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

    def get_geometry(self) -> tuple[np.ndarray, np.ndarray]:
        """Get lens line segment"""
        return self.p1, self.p2

    def interact(
        self, ray: RayState, hit_point: np.ndarray, normal: np.ndarray, tangent: np.ndarray
    ) -> list[RayState]:
        """
        Deflect ray using ideal (non-paraxial) thin lens equation.

        Physics:
        - Exact formula: θ_out = θ_in - arctan(y/f)
        - This ensures a collimated beam at any height y converges
          exactly to the focal point, without spherical-like aberration.
        - Polarization unchanged through ideal lens
        """
        # Ensure normal points in ray propagation direction
        if np.dot(ray.direction, normal) < 0:
            normal = -normal

        # Compute ray height on lens (distance from center along tangent)
        center = 0.5 * (self.p1 + self.p2)
        y = float(np.dot(hit_point - center, tangent))

        # Decompose ray direction into normal and tangent components
        a_n = float(np.dot(ray.direction, normal))
        a_t = float(np.dot(ray.direction, tangent))

        # Compute incident angle
        theta_in = math.atan2(a_t, a_n)

        # Apply ideal thin lens equation: θ_out = θ_in - arctan(y/f)
        # The arctan form is the exact angle subtended by height y at
        # distance f, giving perfect focusing at all ray heights.
        # Use single-argument atan(y/f), NOT atan2(y, f): for f < 0 the
        # two-argument form returns an angle in the rear hemisphere, which
        # sends the ray backward (the lens acts as a mirror). atan(y/f)
        # keeps the deflection in (-π/2, π/2) so a negative-focal-length
        # lens stays transmissive and diverges the beam.
        if abs(self.efl_mm) > 1e-12:
            theta_out = theta_in - math.atan(y / self.efl_mm)
        else:
            theta_out = theta_in  # Infinite focal length = no deflection

        # Reconstruct direction from angle
        direction_out = normalize(math.cos(theta_out) * normal + math.sin(theta_out) * tangent)

        # Polarization unchanged through ideal lens
        EPS_ADV = 1e-3
        refracted_ray = RayState(
            position=hit_point + direction_out * EPS_ADV,
            direction=direction_out,
            intensity=ray.intensity,  # No loss in ideal lens
            polarization=ray.polarization,  # Unchanged
            wavelength_nm=ray.wavelength_nm,
            path=ray.path + [hit_point],
            events=ray.events + 1,
        )

        return [refracted_ray]

    def transform_q(
        self,
        q: complex,
        ray: RayState,
        normal: np.ndarray,
        *,
        hit_point: np.ndarray | None = None,
        tangent: np.ndarray | None = None,
    ) -> complex:
        """Tangential-plane ABCD thin lens; oblique incidence and height y on lens."""
        from ...core.gaussian_beam import apply_abcd

        n = np.asarray(normal, dtype=float)
        v = ray.direction
        if float(np.dot(v, n)) < 0:
            n = -n
        a_n = float(np.dot(v, n))
        cos_theta_in = max(a_n, 1e-12)
        f = self.efl_mm
        if abs(f) < 1e-12:
            return apply_abcd(q, 1.0, 0.0, 0.0, 1.0)

        if hit_point is not None and tangent is not None:
            tvec = np.asarray(tangent, dtype=float)
            center = 0.5 * (self.p1 + self.p2)
            y = float(np.dot(hit_point - center, tvec))
            a_t = float(np.dot(v, tvec))
            theta_in = math.atan2(a_t, a_n)
            # atan(y/f), not atan2(y, f): keeps a negative-f lens transmissive
            # instead of reflecting (see interact()).
            theta_out = theta_in - math.atan(y / f)
            f_local = f * (1.0 + (y / f) ** 2)
            direction_out = math.cos(theta_out) * n + math.sin(theta_out) * tvec
            norm_out = float(np.linalg.norm(direction_out))
            if norm_out > 1e-12:
                direction_out = direction_out / norm_out
            cos_theta_out = max(abs(float(np.dot(direction_out, n))), 1e-12)
            A = cos_theta_out / cos_theta_in
            C = -1.0 / (f_local * cos_theta_in)
            return apply_abcd(q, A, 0.0, C, 1.0)

        C = -1.0 / (f * cos_theta_in)
        return apply_abcd(q, 1.0, 0.0, C, 1.0)

    def get_bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """Get axis-aligned bounding box"""
        min_corner = np.minimum(self.p1, self.p2)
        max_corner = np.maximum(self.p1, self.p2)
        return min_corner, max_corner
