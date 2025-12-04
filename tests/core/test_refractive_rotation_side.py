"""
Test refractive interface consistency regardless of endpoint orientation.
"""

from __future__ import annotations

import math

import numpy as np

from optiverse.core.models import SourceParams
from optiverse.data import LineSegment, OpticalInterface, RefractiveProperties
from optiverse.integration import create_polymorphic_element
from optiverse.raytracing import trace_rays_polymorphic


def _unit(vec: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(vec))
    return vec / n if n > 0 else vec


def _path_last_direction(points: list[np.ndarray]) -> np.ndarray:
    if len(points) < 2:
        return np.array([0.0, 0.0], dtype=float)
    return _unit(points[-1] - points[-2])


def _directions_after_first_event(elements: list, source: SourceParams) -> list[np.ndarray]:
    # Limit to one interaction so the last segment reflects/transmits
    # immediately after the interface
    paths = trace_rays_polymorphic(elements, [source], max_events=1)
    dirs: list[np.ndarray] = []
    for p in paths:
        if len(p.points) >= 2:
            # Points are stored as tuples; convert to ndarray
            pts = [np.array(pt, dtype=float) for pt in p.points]
            dirs.append(_path_last_direction(pts))
    return dirs


def _angles_sorted(dirs: list[np.ndarray]) -> list[float]:
    # Convert to angles for order-independent comparison
    angs = [math.atan2(float(v[1]), float(v[0])) for v in dirs]
    # Normalize to [-pi, pi]
    angs = [math.atan2(math.sin(a), math.cos(a)) for a in angs]
    return sorted(angs)


def _create_refractive_element(p1: np.ndarray, p2: np.ndarray, n1: float = 1.0, n2: float = 1.5):
    """Create a refractive interface element."""
    geom = LineSegment(p1, p2)
    props = RefractiveProperties(n1=n1, n2=n2)
    iface = OpticalInterface(geometry=geom, properties=props)
    return create_polymorphic_element(iface)


def test_refractive_interface_rotation_side_consistency():
    # Diagonal interface (45°) to ensure non-normal incidence for a horizontal ray
    p1 = np.array([-10.0, -10.0], dtype=float)
    p2 = np.array([+10.0, +10.0], dtype=float)

    # Same physical interface, two orientations (swap endpoints simulates 180° rotation of tangent)
    e1 = _create_refractive_element(p1, p2, n1=1.0, n2=1.5)
    e2 = _create_refractive_element(p2, p1, n1=1.0, n2=1.5)

    # Source from the left going right, slightly off-axis to avoid degenerate cases
    src = SourceParams(
        x_mm=-50.0,
        y_mm=0.0,
        angle_deg=0.0,
        n_rays=1,
        ray_length_mm=200.0,
    )

    dirs1 = _directions_after_first_event([e1], src)
    dirs2 = _directions_after_first_event([e2], src)

    # Expect same set of outgoing directions (transmitted + reflected) regardless of orientation
    # Compare by sorted angles with tolerance
    a1 = _angles_sorted(dirs1)
    a2 = _angles_sorted(dirs2)

    assert len(a1) == len(a2) and len(a1) >= 1

    for ang1, ang2 in zip(a1, a2):
        assert abs(ang1 - ang2) < 1e-6
