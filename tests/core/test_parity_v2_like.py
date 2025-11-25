import math
import numpy as np


def test_thin_lens_deflection_matches_v2_formula():
    from optiverse.core.models import OpticalElement, SourceParams
    from optiverse.core.use_cases import trace_rays

    # Lens centered at origin along x-axis; ray passes at x=+10 mm above optical axis
    lens = OpticalElement(kind="lens", p1=np.array([-50.0, 0.0]), p2=np.array([50.0, 0.0]), efl_mm=100.0)

    # Source at (10, -100) shooting straight up (along +Y)
    src = SourceParams(x_mm=10.0, y_mm=-100.0, angle_deg=90.0, size_mm=0.0, n_rays=1, ray_length_mm=400.0, spread_deg=0.0)

    paths = trace_rays([lens], [src], max_events=1)
    assert len(paths) >= 1
    pts = paths[0].points
    # after hit we should have at least 3 points (start, hit, post-advance)
    assert len(pts) >= 3

    # direction vector after lens (approximate from last segment)
    v = np.array(pts[-1]) - np.array(pts[-2])
    v_norm = v / (np.linalg.norm(v) or 1.0)

    # Expected theta_out = -y/f where y=+10 mm, f=100 mm => -0.1 rad
    expected_theta = -0.1
    # In global coords, n_hat is +Y, t_hat is +X; V = cos(theta)*n + sin(theta)*t
    exp = np.array([math.sin(expected_theta), math.cos(expected_theta)])
    # Allow small tolerance
    assert np.allclose(v_norm, exp, atol=1e-2)


def test_mirror_reflection_angle_parity():
    from optiverse.core.models import OpticalElement, SourceParams
    from optiverse.core.use_cases import trace_rays

    # 45° mirror: segment rotated 45° CCW so normal faces roughly right-down
    # Build segment endpoints at 45° around origin
    L = 100.0
    p1 = np.array([-L / math.sqrt(8), -L / math.sqrt(8)])
    p2 = np.array([L / math.sqrt(8), L / math.sqrt(8)])
    mirror = OpticalElement(kind="mirror", p1=p1, p2=p2)

    # Ray coming from left to right
    src = SourceParams(x_mm=-100.0, y_mm=0.0, angle_deg=0.0, size_mm=0.0, n_rays=1, ray_length_mm=400.0, spread_deg=0.0)
    paths = trace_rays([mirror], [src], max_events=2)
    assert len(paths) >= 1
    pts = paths[0].points
    assert len(pts) >= 3
    # After reflection, direction should be rotated by ~+90° (upwards)
    v = np.array(pts[-1]) - np.array(pts[-2])
    v_norm = v / (np.linalg.norm(v) or 1.0)
    assert v_norm[1] > 0.7  # strong upward component




