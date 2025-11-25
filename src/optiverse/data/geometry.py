"""
Geometric primitives for optical elements.

Pure geometric data structures with no optical or UI dependencies.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import math


@dataclass
class LineSegment:
    """
    2D line segment defined by two endpoints.

    This represents the geometry of a flat optical interface in 2D space.
    All coordinates are in millimeters.
    """
    p1: 'np.ndarray'  # Start point [x, y] in mm
    p2: 'np.ndarray'  # End point [x, y] in mm
    is_curved: bool = False  # Always False for LineSegment
    radius_of_curvature_mm: float = 0.0  # Always 0 for flat segments

    def __post_init__(self):
        """Ensure points are numpy arrays"""
        if not isinstance(self.p1, np.ndarray):
            self.p1 = np.array(self.p1, dtype=float)
        if not isinstance(self.p2, np.ndarray):
            self.p2 = np.array(self.p2, dtype=float)

        # Ensure 2D
        if self.p1.shape != (2,):
            raise ValueError(f"p1 must be 2D point, got shape {self.p1.shape}")
        if self.p2.shape != (2,):
            raise ValueError(f"p2 must be 2D point, got shape {self.p2.shape}")

    def length(self) -> float:
        """Calculate line segment length in mm"""
        return float(np.linalg.norm(self.p2 - self.p1))

    def midpoint(self) -> np.ndarray:
        """Calculate midpoint coordinates"""
        return 0.5 * (self.p1 + self.p2)

    def direction(self) -> np.ndarray:
        """Get normalized direction vector from p1 to p2"""
        vec = self.p2 - self.p1
        length = np.linalg.norm(vec)
        if length < 1e-12:
            return np.array([1.0, 0.0])
        return vec / length

    def normal(self) -> np.ndarray:
        """
        Get normalized normal vector (perpendicular to line).

        Normal points 90° counterclockwise from p2→p1 direction (reversed).
        This makes n1 on the "right" side and n2 on the "left" side when looking p1→p2.
        For a horizontal line from left to right (p1→p2), normal points down.
        """
        # Use reversed direction (p2→p1) to flip normal 180° for correct n1/n2 interpretation
        vec = self.p1 - self.p2
        length = np.linalg.norm(vec)
        if length < 1e-12:
            return np.array([0.0, 1.0])
        direction_reversed = vec / length
        # Rotate 90° counterclockwise: (x, y) -> (-y, x)
        return np.array([-direction_reversed[1], direction_reversed[0]])

    def tangent(self) -> np.ndarray:
        """Get normalized tangent vector (same as direction)"""
        return self.direction()

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "p1": self.p1.tolist(),
            "p2": self.p2.tolist(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LineSegment':
        """Deserialize from dictionary"""
        return cls(
            p1=np.array(data["p1"], dtype=float),
            p2=np.array(data["p2"], dtype=float),
        )


@dataclass
class CurvedSegment:
    """
    2D curved segment (circular arc) defined by two endpoints and radius of curvature.

    This represents the geometry of a curved optical interface (like a lens surface).
    All coordinates are in millimeters.

    The arc is defined by:
    - p1, p2: Endpoints of the arc
    - radius_of_curvature_mm: Radius of the circle (positive = convex, negative = concave)

    The center of curvature is calculated from these parameters.
    """
    p1: 'np.ndarray'  # Start point [x, y] in mm
    p2: 'np.ndarray'  # End point [x, y] in mm
    radius_of_curvature_mm: float  # Radius of curvature (+ or -)
    is_curved: bool = True  # Always True for CurvedSegment

    def __post_init__(self):
        """Ensure points are numpy arrays and calculate center"""
        if not isinstance(self.p1, np.ndarray):
            self.p1 = np.array(self.p1, dtype=float)
        if not isinstance(self.p2, np.ndarray):
            self.p2 = np.array(self.p2, dtype=float)

        # Ensure 2D
        if self.p1.shape != (2,):
            raise ValueError(f"p1 must be 2D point, got shape {self.p1.shape}")
        if self.p2.shape != (2,):
            raise ValueError(f"p2 must be 2D point, got shape {self.p2.shape}")

        # Calculate center of curvature
        self._center = self._calculate_center()

    def _calculate_center(self) -> np.ndarray:
        """
        Calculate the center of the circle from endpoints and radius.

        Returns:
            Center point [x, y] in mm
        """
        # Midpoint between endpoints
        mid = 0.5 * (self.p1 + self.p2)

        # Direction from p1 to p2
        chord = self.p2 - self.p1
        chord_length = np.linalg.norm(chord)

        if chord_length < 1e-9:
            return mid

        # Perpendicular direction (normal to chord)
        # Rotate chord 90° counterclockwise: (x, y) -> (-y, x)
        perp = np.array([-chord[1], chord[0]]) / chord_length

        # Distance from midpoint to center
        # Using Pythagoras: r² = (chord/2)² + d²
        r = abs(self.radius_of_curvature_mm)
        half_chord = chord_length / 2.0

        if r < half_chord:
            # Radius too small for this chord length
            # Return midpoint (degenerate to line)
            return mid

        d = math.sqrt(r**2 - half_chord**2)

        # Direction depends on sign of radius
        # Positive radius: center on one side, negative: other side
        if self.radius_of_curvature_mm > 0:
            center = mid + d * perp
        else:
            center = mid - d * perp

        return center

    def length(self) -> float:
        """Calculate arc length in mm"""
        r = abs(self.radius_of_curvature_mm)
        # Arc angle
        theta = self._arc_angle()
        return r * theta

    def _arc_angle(self) -> float:
        """Calculate the angle subtended by the arc (in radians)"""
        # Vectors from center to endpoints
        v1 = self.p1 - self._center
        v2 = self.p2 - self._center

        # Angle between vectors
        cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cos_theta = np.clip(cos_theta, -1.0, 1.0)  # Numerical stability

        return math.acos(cos_theta)

    def midpoint(self) -> np.ndarray:
        """Calculate midpoint of the arc (point at half the arc angle)"""
        # For simplicity, return chord midpoint
        # (true arc midpoint would be on the circle at half the arc angle)
        return 0.5 * (self.p1 + self.p2)

    def direction(self) -> np.ndarray:
        """Get average direction (tangent at midpoint)"""
        # Tangent at midpoint
        mid = 0.5 * (self.p1 + self.p2)
        radial = mid - self._center

        # Tangent is perpendicular to radial
        # Rotate 90° based on curvature direction
        if self.radius_of_curvature_mm > 0:
            tangent = np.array([-radial[1], radial[0]])
        else:
            tangent = np.array([radial[1], -radial[0]])

        length = np.linalg.norm(tangent)
        if length < 1e-12:
            return np.array([1.0, 0.0])
        return tangent / length

    def normal(self) -> np.ndarray:
        """
        Get average normal vector (perpendicular to tangent).

        For curved surfaces, this is the radial direction at the midpoint.
        Direction is reversed to match the n1/n2 convention (n1 on "right", n2 on "left").
        """
        mid = 0.5 * (self.p1 + self.p2)
        radial = mid - self._center

        length = np.linalg.norm(radial)
        if length < 1e-12:
            return np.array([0.0, 1.0])

        # Normal direction reversed to match flat surface convention
        # Normal points inward toward center (for positive radius)
        if self.radius_of_curvature_mm > 0:
            return -radial / length
        else:
            return radial / length

    def normal_at_point(self, point: np.ndarray) -> np.ndarray:
        """
        Get normal vector at a specific point on the arc.

        Args:
            point: Point on the arc [x, y]

        Returns:
            Normalized normal vector at that point
        """
        radial = point - self._center
        length = np.linalg.norm(radial)

        if length < 1e-12:
            return np.array([0.0, 1.0])

        # Normal direction reversed to match flat surface convention
        # Normal points inward toward center (for positive radius)
        if self.radius_of_curvature_mm > 0:
            return -radial / length
        else:
            return radial / length

    def tangent(self) -> np.ndarray:
        """Get average tangent vector (same as direction)"""
        return self.direction()

    def tangent_at_point(self, point: np.ndarray) -> np.ndarray:
        """
        Get tangent vector at a specific point on the arc.

        Args:
            point: Point on the arc [x, y]

        Returns:
            Normalized tangent vector at that point
        """
        normal = self.normal_at_point(point)
        # Tangent is perpendicular to normal
        # Rotate 90° counterclockwise
        return np.array([-normal[1], normal[0]])

    def get_center(self) -> np.ndarray:
        """Get the center of curvature"""
        return self._center

    def get_radius(self) -> float:
        """Get the absolute radius of curvature"""
        return abs(self.radius_of_curvature_mm)

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "p1": self.p1.tolist(),
            "p2": self.p2.tolist(),
            "radius_of_curvature_mm": self.radius_of_curvature_mm,
            "is_curved": True,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CurvedSegment':
        """Deserialize from dictionary"""
        return cls(
            p1=np.array(data["p1"], dtype=float),
            p2=np.array(data["p2"], dtype=float),
            radius_of_curvature_mm=data["radius_of_curvature_mm"],
        )


# Type alias for any geometry segment
GeometrySegment = LineSegment | CurvedSegment



