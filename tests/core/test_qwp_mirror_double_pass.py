import numpy as np

from optiverse.core.models import Polarization
from optiverse.core.raytracing_math import (
    deg2rad,
    transform_polarization_mirror,
    transform_polarization_waveplate,
)


def _equivalent_up_to_global_phase(a: np.ndarray, b: np.ndarray, atol: float = 1e-6) -> bool:
    """Return True if Jones vectors a and b are equal up to a global complex scale."""
    if np.linalg.norm(a) < 1e-12 and np.linalg.norm(b) < 1e-12:
        return True
    # Pick a nonzero component to compute the ratio
    if abs(b[0]) > 1e-12:
        ratio = a[0] / b[0]
    elif abs(b[1]) > 1e-12:
        ratio = a[1] / b[1]
    else:
        return False
    return np.allclose(a, ratio * b, atol=atol)


def _linear_jones(angle_deg: float) -> np.ndarray:
    """Ideal linear polarization Jones vector at angle_deg (from horizontal)."""
    th = deg2rad(angle_deg)
    return np.array([np.cos(th), np.sin(th)], dtype=complex)


def _apply_qwp_mirror_qwp(pol: Polarization, theta_deg: float) -> Polarization:
    """Apply forward QWP(θ), ideal mirror, then backward QWP(θ)."""
    # Forward pass through QWP with +90°
    pol1 = transform_polarization_waveplate(
        pol,
        phase_shift_deg=90.0,
        fast_axis_deg=theta_deg,
        is_forward=True,
    )

    # Ideal mirror at near-normal incidence (s/p fallback picks s=[0,1], p=[-1,0])
    # Convention is fine; only relative phase matters
    pol2 = transform_polarization_mirror(
        pol1, v_in=np.array([1.0, 0.0]), n_hat=np.array([1.0, 0.0])
    )

    # Backward pass through the same QWP (−90° effective)
    pol3 = transform_polarization_waveplate(
        pol2,
        phase_shift_deg=90.0,
        fast_axis_deg=theta_deg,
        is_forward=False,
    )
    return pol3


def test_qwp_mirror_qwp_22_5_degrees_is_not_simple_45_rotation():
    pol_in = Polarization.horizontal()
    pol_out = _apply_qwp_mirror_qwp(pol_in, theta_deg=22.5)

    # Check it's not linear at 45° (i.e., not a simple 2θ rotation)
    expected_45 = _linear_jones(45.0)
    assert not _equivalent_up_to_global_phase(pol_out.jones_vector, expected_45, atol=1e-6)
    # Also assert it's not purely linear (phase difference not 0 or π)
    ex, ey = pol_out.jones_vector
    phase_diff = np.angle(ey) - np.angle(ex)
    phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))
    assert not (abs(phase_diff) < 1e-3 or abs(abs(phase_diff) - np.pi) < 1e-3)


def test_qwp_mirror_qwp_45_degrees_rotates_by_90():
    pol_in = Polarization.horizontal()
    pol_out = _apply_qwp_mirror_qwp(pol_in, theta_deg=45.0)

    expected = _linear_jones(90.0)
    assert _equivalent_up_to_global_phase(pol_out.jones_vector, expected, atol=1e-6)
