"""
Tests for raytracing math utilities.

These tests verify the core mathematical functions used in ray tracing:
- Angle conversions
- Vector normalization
- Ray-element intersection
- Vector reflection
"""

from __future__ import annotations

import math

import numpy as np


def test_deg2rad():
    """Test degree to radian conversion."""
    from optiverse.core.raytracing_math import deg2rad

    assert math.isclose(deg2rad(180.0), math.pi)
    assert math.isclose(deg2rad(0.0), 0.0)
    assert math.isclose(deg2rad(90.0), math.pi / 2)
    assert math.isclose(deg2rad(360.0), 2 * math.pi)
    assert math.isclose(deg2rad(-90.0), -math.pi / 2)


def test_normalize():
    """Test vector normalization."""
    from optiverse.core.raytracing_math import normalize

    # Standard 3-4-5 right triangle
    v = np.array([3.0, 4.0])
    u = normalize(v)
    assert math.isclose(float(np.linalg.norm(u)), 1.0)
    assert math.isclose(u[0], 0.6)
    assert math.isclose(u[1], 0.8)

    # Zero vector should return zero vector
    z = normalize(np.array([0.0, 0.0]))
    assert np.allclose(z, np.array([0.0, 0.0]))

    # Already unit vector
    unit = np.array([1.0, 0.0])
    assert np.allclose(normalize(unit), unit)


def test_reflect_and_intersect():
    """Test ray-element intersection and reflection."""
    from optiverse.core.raytracing_math import ray_hit_element, reflect_vec

    # Segment AB along x-axis from (-1,0) to (1,0), ray from (0,-1) heading up
    a = np.array([-1.0, 0.0])
    b = np.array([1.0, 0.0])
    p = np.array([0.0, -1.0])
    v = np.array([0.0, 1.0])

    res = ray_hit_element(p, v, a, b)
    assert res is not None
    t, x, t_hat, n_hat, c, l_len = res
    assert math.isclose(float(x[0]), 0.0)
    assert math.isclose(float(x[1]), 0.0)

    # Reflect V across upward normal [0,1] should invert Y
    vr = reflect_vec(v, np.array([0.0, 1.0]))
    assert np.allclose(vr, np.array([0.0, -1.0]))


def test_reflect_vec_at_angle():
    """Test reflection at various angles."""
    from optiverse.core.raytracing_math import reflect_vec

    # Horizontal ray reflecting off 45° mirror
    v = np.array([1.0, 0.0])
    n = np.array([-1.0 / np.sqrt(2), 1.0 / np.sqrt(2)])  # 45° normal
    vr = reflect_vec(v, n)

    # Should reflect upward
    assert vr[0] < 0.1  # Nearly zero horizontal
    assert vr[1] > 0.9  # Nearly 1 vertical


def test_ray_miss():
    """Test ray that misses the segment."""
    from optiverse.core.raytracing_math import ray_hit_element

    # Segment along x-axis
    a = np.array([-1.0, 0.0])
    b = np.array([1.0, 0.0])

    # Ray pointing away
    p = np.array([0.0, -1.0])
    v = np.array([0.0, -1.0])  # Pointing down, away from segment

    result = ray_hit_element(p, v, a, b)
    # Should return None or indicate no hit
    assert result is None or (result[0] < 0)  # No valid hit or negative t


def test_ray_parallel_to_segment():
    """Test ray parallel to segment (no intersection)."""
    from optiverse.core.raytracing_math import ray_hit_element

    # Segment along x-axis
    a = np.array([-1.0, 0.0])
    b = np.array([1.0, 0.0])

    # Ray parallel to segment
    p = np.array([0.0, 1.0])  # Above segment
    v = np.array([1.0, 0.0])  # Pointing right, parallel

    result = ray_hit_element(p, v, a, b)
    # Should return None for parallel non-intersecting ray
    assert result is None
