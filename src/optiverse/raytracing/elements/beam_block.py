"""
Beam block element implementation.

Implements ray absorption - terminates ray propagation at the hit point.
"""

import numpy as np

from ..ray import RayState
from .base import IOpticalElement


class BeamBlockElement(IOpticalElement):
    """
    Beam block element that absorbs all incident rays.

    Used for beam dumps, stops, and baffles. Returns no output rays,
    effectively terminating ray propagation at the hit point.
    """

    def __init__(self, p1: np.ndarray, p2: np.ndarray):
        """
        Initialize beam block element.

        Args:
            p1: Start point of beam block line segment [x, y] in mm
            p2: End point of beam block line segment [x, y] in mm
        """
        self.p1 = np.array(p1, dtype=float)
        self.p2 = np.array(p2, dtype=float)

    def get_geometry(self) -> tuple[np.ndarray, np.ndarray]:
        """Get beam block line segment"""
        return self.p1, self.p2

    def interact(
        self, ray: RayState, hit_point: np.ndarray, normal: np.ndarray, tangent: np.ndarray
    ) -> list[RayState]:
        """
        Absorb ray - returns empty list to terminate ray propagation.

        The ray path ends at hit_point (which is already recorded in the ray's path
        by the tracing engine before calling interact).
        """
        # Return empty list - ray is absorbed, no output rays
        return []

    def get_bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """Get axis-aligned bounding box"""
        min_corner = np.minimum(self.p1, self.p2)
        max_corner = np.maximum(self.p1, self.p2)
        return min_corner, max_corner

