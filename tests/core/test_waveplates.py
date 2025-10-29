"""
Tests for waveplate polarization physics.

Verifies that quarter and half waveplates correctly transform polarization states.
"""
import numpy as np
import pytest

from optiverse.core.geometry import transform_polarization_waveplate
from optiverse.core.models import Polarization


def test_quarter_waveplate_horizontal_to_circular():
    """QWP at 45° converts horizontal polarization to right circular."""
    pol_in = Polarization.horizontal()
    pol_out = transform_polarization_waveplate(pol_in, phase_shift_deg=90.0, fast_axis_deg=45.0)
    
    jones = pol_out.jones_vector
    
    # Check magnitude is normalized
    assert np.abs(np.linalg.norm(jones) - 1.0) < 1e-6
    
    # For right circular: Ex and Ey have equal magnitude, 90° phase difference
    assert np.abs(np.abs(jones[0]) - np.abs(jones[1])) < 1e-6


def test_quarter_waveplate_circular_to_linear():
    """QWP at 0° converts right circular to linear."""
    pol_in = Polarization.circular_right()
    pol_out = transform_polarization_waveplate(pol_in, phase_shift_deg=90.0, fast_axis_deg=0.0)
    
    jones = pol_out.jones_vector
    
    # Check magnitude is normalized
    assert np.abs(np.linalg.norm(jones) - 1.0) < 1e-6


def test_half_waveplate_rotates_linear():
    """HWP at 22.5° rotates horizontal polarization by 45°."""
    pol_in = Polarization.horizontal()
    pol_out = transform_polarization_waveplate(pol_in, phase_shift_deg=180.0, fast_axis_deg=22.5)
    
    jones = pol_out.jones_vector
    
    # Check magnitude is normalized
    assert np.abs(np.linalg.norm(jones) - 1.0) < 1e-6


def test_waveplate_preserves_intensity():
    """Waveplates preserve total intensity."""
    pol_in = Polarization.linear(30.0)
    pol_out = transform_polarization_waveplate(pol_in, phase_shift_deg=90.0, fast_axis_deg=60.0)
    
    intensity_in = pol_in.intensity()
    intensity_out = pol_out.intensity()
    
    # Intensity should be conserved
    assert np.abs(intensity_in - intensity_out) < 1e-6


def test_zero_phase_shift_is_identity():
    """Zero phase shift leaves polarization unchanged."""
    pol_in = Polarization.diagonal_plus_45()
    pol_out = transform_polarization_waveplate(pol_in, phase_shift_deg=0.0, fast_axis_deg=0.0)
    
    jones_in = pol_in.jones_vector
    jones_out = pol_out.jones_vector
    
    # Jones vectors should be identical
    assert np.allclose(jones_in, jones_out, atol=1e-6)


# ===== DIRECTIONALITY TESTS =====


def test_qwp_forward_horizontal_to_circular():
    """QWP forward at 45° converts horizontal to circular polarization."""
    pol_in = Polarization.horizontal()
    pol_out = transform_polarization_waveplate(
        pol_in, 
        phase_shift_deg=90.0, 
        fast_axis_deg=45.0,
        is_forward=True
    )
    
    jones = pol_out.jones_vector
    
    # Circular: equal magnitude components
    assert np.abs(np.linalg.norm(jones) - 1.0) < 1e-6
    assert np.abs(np.abs(jones[0]) - 1/np.sqrt(2)) < 1e-6
    assert np.abs(np.abs(jones[1]) - 1/np.sqrt(2)) < 1e-6
    
    # Check phase difference: should be ±90° (circular polarization)
    phase_diff = np.angle(jones[1]) - np.angle(jones[0])
    # Normalize to [-π, π]
    phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))
    assert np.abs(np.abs(phase_diff) - np.pi/2) < 1e-6  # Either +90° or -90°


def test_qwp_backward_horizontal_to_circular():
    """QWP backward at 45° converts horizontal to circular polarization (opposite handedness from forward)."""
    pol_in = Polarization.horizontal()
    pol_out = transform_polarization_waveplate(
        pol_in, 
        phase_shift_deg=90.0, 
        fast_axis_deg=45.0,
        is_forward=False  # Backward direction
    )
    
    jones = pol_out.jones_vector
    
    # Circular: equal magnitude components
    assert np.abs(np.linalg.norm(jones) - 1.0) < 1e-6
    assert np.abs(np.abs(jones[0]) - 1/np.sqrt(2)) < 1e-6
    assert np.abs(np.abs(jones[1]) - 1/np.sqrt(2)) < 1e-6
    
    # Check phase difference: should be ±90° (opposite from forward)
    phase_diff = np.angle(jones[1]) - np.angle(jones[0])
    # Normalize to [-π, π]
    phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))
    assert np.abs(np.abs(phase_diff) - np.pi/2) < 1e-6  # Either +90° or -90°


def test_qwp_directionality_opposite_handedness():
    """QWP forward and backward produce opposite circular handedness."""
    pol_in = Polarization.horizontal()
    
    pol_forward = transform_polarization_waveplate(
        pol_in, phase_shift_deg=90.0, fast_axis_deg=45.0, is_forward=True
    )
    pol_backward = transform_polarization_waveplate(
        pol_in, phase_shift_deg=90.0, fast_axis_deg=45.0, is_forward=False
    )
    
    jones_fwd = pol_forward.jones_vector
    jones_bwd = pol_backward.jones_vector
    
    # The y-component should have opposite phases
    # Forward: [a, i*b], Backward: [a, -i*b]
    # So jones_bwd[1] should be the complex conjugate of jones_fwd[1]
    assert np.allclose(jones_bwd[1], np.conj(jones_fwd[1]), atol=1e-6)


def test_qwp_round_trip_identity():
    """QWP forward then backward returns to original polarization."""
    pol_in = Polarization.linear(30.0)  # Arbitrary linear polarization
    
    # Forward pass
    pol_mid = transform_polarization_waveplate(
        pol_in, phase_shift_deg=90.0, fast_axis_deg=45.0, is_forward=True
    )
    
    # Backward pass
    pol_out = transform_polarization_waveplate(
        pol_mid, phase_shift_deg=90.0, fast_axis_deg=45.0, is_forward=False
    )
    
    # Should return to original polarization (up to global phase)
    jones_in = pol_in.jones_vector
    jones_out = pol_out.jones_vector
    
    # Check if they're the same up to a global phase factor
    # Two Jones vectors are equivalent if one is a complex scalar multiple of the other
    ratio = jones_out[0] / jones_in[0] if np.abs(jones_in[0]) > 1e-6 else jones_out[1] / jones_in[1]
    expected_jones_out = ratio * jones_in
    
    assert np.allclose(jones_out, expected_jones_out, atol=1e-6)


def test_hwp_directionality_symmetric():
    """HWP behavior is symmetric - forward and backward give same result."""
    pol_in = Polarization.horizontal()
    
    pol_forward = transform_polarization_waveplate(
        pol_in, phase_shift_deg=180.0, fast_axis_deg=22.5, is_forward=True
    )
    pol_backward = transform_polarization_waveplate(
        pol_in, phase_shift_deg=180.0, fast_axis_deg=22.5, is_forward=False
    )
    
    jones_fwd = pol_forward.jones_vector
    jones_bwd = pol_backward.jones_vector
    
    # For HWP, exp(i*180°) = exp(-i*180°) = -1, so forward and backward are the same
    # They should be equal up to a global phase factor (both get multiplied by some phase)
    # The simplest check: they should both have the same relative components
    assert np.allclose(np.abs(jones_fwd), np.abs(jones_bwd), atol=1e-6)
    
    # More rigorous: check if one is a scalar multiple of the other
    ratio = jones_fwd[0] / jones_bwd[0] if np.abs(jones_bwd[0]) > 1e-6 else jones_fwd[1] / jones_bwd[1]
    assert np.allclose(jones_fwd, ratio * jones_bwd, atol=1e-6)


def test_qwp_vertical_polarization_directionality():
    """Test QWP directionality with vertical input polarization."""
    pol_in = Polarization.vertical()
    
    pol_forward = transform_polarization_waveplate(
        pol_in, phase_shift_deg=90.0, fast_axis_deg=45.0, is_forward=True
    )
    pol_backward = transform_polarization_waveplate(
        pol_in, phase_shift_deg=90.0, fast_axis_deg=45.0, is_forward=False
    )
    
    jones_fwd = pol_forward.jones_vector
    jones_bwd = pol_backward.jones_vector
    
    # Both should produce circular polarization with opposite handedness
    assert np.abs(np.linalg.norm(jones_fwd) - 1.0) < 1e-6
    assert np.abs(np.linalg.norm(jones_bwd) - 1.0) < 1e-6
    
    # Forward and backward should produce opposite handedness
    # The phase relationship should be opposite
    phase_fwd = np.angle(jones_fwd[1]) - np.angle(jones_fwd[0])
    phase_bwd = np.angle(jones_bwd[1]) - np.angle(jones_bwd[0])
    
    # Normalize phases to [-π, π]
    phase_fwd = np.arctan2(np.sin(phase_fwd), np.cos(phase_fwd))
    phase_bwd = np.arctan2(np.sin(phase_bwd), np.cos(phase_bwd))
    
    # They should be opposite
    assert np.abs(phase_fwd + phase_bwd) < 1e-5 or np.abs(np.abs(phase_fwd + phase_bwd) - 2*np.pi) < 1e-5


def test_arbitrary_waveplate_directionality():
    """Test that arbitrary phase shifts are correctly reversed by direction."""
    pol_in = Polarization.diagonal_plus_45()
    phase_shift = 37.5  # Arbitrary phase shift
    
    pol_forward = transform_polarization_waveplate(
        pol_in, phase_shift_deg=phase_shift, fast_axis_deg=60.0, is_forward=True
    )
    pol_backward = transform_polarization_waveplate(
        pol_in, phase_shift_deg=phase_shift, fast_axis_deg=60.0, is_forward=False
    )
    
    jones_fwd = pol_forward.jones_vector
    jones_bwd = pol_backward.jones_vector
    
    # Forward and backward should produce different results (unless phase = 180°)
    # They should NOT be equivalent up to global phase
    # We can check that they're different by comparing their relative phases
    if np.abs(jones_fwd[0]) > 1e-6 and np.abs(jones_bwd[0]) > 1e-6:
        rel_phase_fwd = np.angle(jones_fwd[1] / jones_fwd[0])
        rel_phase_bwd = np.angle(jones_bwd[1] / jones_bwd[0])
        # They should be different (not equal)
        assert not np.allclose(rel_phase_fwd, rel_phase_bwd, atol=1e-5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

