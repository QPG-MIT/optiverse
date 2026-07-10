"""
Lens element implementation.

Implements an ideal thin lens using the exact ray-slope (f·tanθ) deflection law.
"""

import numpy as np

from ...core.raytracing_math import normalize
from ..ray import RayState
from .base import IOpticalElement


class LensElement(IOpticalElement):
    """
    Ideal thin lens element.

    Uses the ray-slope deflection law:  tan(θ_out) = tan(θ_in) − y/f

    This is the exact transformation for an ideal (distortion-free) thin lens:
    a bundle of parallel rays incident at any angle θ_in converges to a single
    point in the focal plane at height f·tan(θ_in), for any ray height y. The
    earlier θ_out = θ_in − arctan(y/f) form only focuses on-axis bundles and
    smears off-axis ones; the plain-angle θ_out = θ_in − y/f form is the
    small-angle linearization that aberrates at large ray heights.

    Building the exit direction as (normal + slope·tangent) also keeps its
    forward component positive, so the lens is always transmissive — it never
    reflects, for either sign of f. This matches the web engine's thin-lens
    deflection (GeometricEngine.thinLens / optiverse_engine _thin_lens).
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
        Deflect ray using the ideal thin lens ray-slope law.

        Physics:
        - Exact law: tan(θ_out) = tan(θ_in) − y/f, i.e. the exit ray slope
          (measured from the lens normal) is reduced by y/f. A parallel bundle
          at any angle focuses to a single point in the focal plane (f·tanθ).
        - Constructing the exit direction as (normal + slope·tangent) keeps the
          forward component positive, so the lens never reflects: a converging
          lens focuses, a diverging (f < 0) lens diverges — never a mirror.
        - Polarization unchanged through ideal lens
        """
        # Ensure normal points in ray propagation direction
        if np.dot(ray.direction, normal) < 0:
            normal = -normal

        # Compute ray height on lens (distance from center along tangent)
        center = 0.5 * (self.p1 + self.p2)
        y = float(np.dot(hit_point - center, tangent))

        # Decompose ray direction into normal and tangent components
        a_n = float(np.dot(ray.direction, normal))  # cos(θ_in) ≥ 0 (normal flipped forward)
        a_t = float(np.dot(ray.direction, tangent))  # sin(θ_in); a_t / a_n = tan(θ_in)

        # Apply the ideal thin lens: tan(θ_out) = tan(θ_in) − y/f. The exit
        # direction (normal + slope·tangent) always points forward, so the lens
        # stays transmissive for either sign of f. Skip when the focal length is
        # infinite or the ray grazes the lens (tan θ_in undefined) → pass through.
        if abs(self.efl_mm) > 1e-12 and a_n >= 1e-9:
            slope = a_t / a_n - y / self.efl_mm
            direction_out = normalize(normal + slope * tangent)
        else:
            direction_out = normalize(ray.direction)

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
            # Same ray-slope deflection as interact(), so the Gaussian ABCD uses
            # the matching exit direction (mirrors web GeometricEngine.lensQ):
            # tan(θ_out) = tan(θ_in) − y/f, direction = normal + slope·tangent.
            slope = a_t / cos_theta_in - y / f
            direction_out = n + slope * tvec
            norm_out = float(np.linalg.norm(direction_out))
            if norm_out > 1e-12:
                direction_out = direction_out / norm_out
            cos_theta_out = max(abs(float(np.dot(direction_out, n))), 1e-12)
            f_local = f * (1.0 + (y / f) ** 2)
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
