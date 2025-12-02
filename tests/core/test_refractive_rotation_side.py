from __future__ import annotations

import math

import numpy as np

from optiverse.core.models import OpticalElement, SourceParams
from optiverse.core.use_cases import trace_rays


def _unit(vec: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(vec))
    return vec / n if n > 0 else vec


def _path_last_direction(points: list[np.ndarray]) -> np.ndarray:
    if len(points) < 2:
        return np.array([0.0, 0.0], dtype=float)
    return _unit(points[-1] - points[-2])


def _directions_after_first_event(
    elements: list[OpticalElement], source: SourceParams
) -> list[np.ndarray]:
    # Limit to one interaction so the last segment reflects/transmits
    # immediately after the interface
    paths = trace_rays(elements, [source], max_events=1)
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


def test_refractive_interface_rotation_side_consistency():
    # Diagonal interface (45°) to ensure non-normal incidence for a horizontal ray
    p1 = np.array([-10.0, -10.0], dtype=float)
    p2 = np.array([+10.0, +10.0], dtype=float)

    # Same physical interface, two orientations (swap endpoints simulates 180° rotation of tangent)
    e1 = OpticalElement(kind="refractive_interface", p1=p1, p2=p2)
    e1.n1 = 1.0
    e1.n2 = 1.5
    e1.is_beam_splitter = False

    e2 = OpticalElement(kind="refractive_interface", p1=p2, p2=p1)
    e2.n1 = 1.0
    e2.n2 = 1.5
    e2.is_beam_splitter = False

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
