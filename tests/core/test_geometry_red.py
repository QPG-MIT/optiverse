import math

import numpy as np


def test_deg2rad():
    from optiverse.core.raytracing_math import deg2rad

    assert math.isclose(deg2rad(180.0), math.pi)
    assert math.isclose(deg2rad(0.0), 0.0)


def test_normalize():
    from optiverse.core.raytracing_math import normalize

    v = np.array([3.0, 4.0])
    u = normalize(v)
    assert math.isclose(float(np.linalg.norm(u)), 1.0)
    z = normalize(np.array([0.0, 0.0]))
    assert np.allclose(z, np.array([0.0, 0.0]))


def test_reflect_and_intersect():
    from optiverse.core.raytracing_math import ray_hit_element, reflect_vec

    # Segment AB along x-axis from (-1,0) to (1,0), ray from (0,-1) heading up
    A = np.array([-1.0, 0.0])
    B = np.array([1.0, 0.0])
    P = np.array([0.0, -1.0])
    V = np.array([0.0, 1.0])

    res = ray_hit_element(P, V, A, B)
    assert res is not None
    t, X, t_hat, n_hat, C, L = res
    assert math.isclose(float(X[0]), 0.0)
    assert math.isclose(float(X[1]), 0.0)

    # Reflect V across upward normal [0,1] should invert Y
    Vr = reflect_vec(V, np.array([0.0, 1.0]))
    assert np.allclose(Vr, np.array([0.0, -1.0]))
