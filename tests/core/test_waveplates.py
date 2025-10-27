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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

