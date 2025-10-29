"""
Test QWP at different angles to understand the rotation behavior.
User reports: QWP at 22.5° doesn't give 45° rotation, but QWP at 45° gives 90°.
"""
import numpy as np
from src.optiverse.core.geometry import transform_polarization_waveplate
from src.optiverse.core.models import Polarization

def analyze_linear_angle(jones):
    """Calculate the angle of linear polarization, or report if not linear."""
    # Check if it's linear
    phase_diff = np.angle(jones[1]) - np.angle(jones[0])
    # Normalize to [-π, π]
    phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))
    
    is_linear = np.abs(phase_diff) < 0.1 or np.abs(np.abs(phase_diff) - np.pi) < 0.1
    
    if is_linear:
        # Use atan2 of the real magnitudes
        angle_rad = np.arctan2(np.abs(jones[1]), np.abs(jones[0]))
        angle_deg = np.rad2deg(angle_rad)
        return f"Linear at {angle_deg:.2f}°"
    else:
        # Not linear - circular or elliptical
        return f"Elliptical/Circular (phase diff: {np.rad2deg(phase_diff):.2f}°)"


def test_qwp_single_pass(fast_axis_deg):
    """Test a single pass through QWP at given fast axis angle."""
    print(f"\n{'='*70}")
    print(f"QWP at {fast_axis_deg}° fast axis - SINGLE PASS")
    print(f"{'='*70}")
    
    pol_in = Polarization.horizontal()
    print(f"Input: Horizontal (0°)")
    
    pol_out = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=90.0,
        fast_axis_deg=fast_axis_deg,
        is_forward=True
    )
    
    print(f"Output: {analyze_linear_angle(pol_out.jones_vector)}")
    print(f"Jones vector: {pol_out.jones_vector}")
    

def test_qwp_double_pass_same_direction(fast_axis_deg):
    """
    Test double pass through QWP in the SAME direction.
    This would be like passing through two identical QWPs in series.
    """
    print(f"\n{'='*70}")
    print(f"QWP at {fast_axis_deg}° fast axis - DOUBLE PASS (SAME DIRECTION)")
    print(f"{'='*70}")
    print("Setup: Light → QWP₁ (forward) → QWP₂ (forward, same orientation)")
    
    pol_in = Polarization.horizontal()
    print(f"\nInput: Horizontal (0°)")
    
    # First pass
    pol_mid = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=90.0,
        fast_axis_deg=fast_axis_deg,
        is_forward=True
    )
    print(f"After 1st QWP: {analyze_linear_angle(pol_mid.jones_vector)}")
    
    # Second pass (same direction)
    pol_out = transform_polarization_waveplate(
        pol_mid,
        phase_shift_deg=90.0,
        fast_axis_deg=fast_axis_deg,
        is_forward=True  # Same direction!
    )
    print(f"After 2nd QWP: {analyze_linear_angle(pol_out.jones_vector)}")
    print(f"Jones vector: {pol_out.jones_vector}")
    
    # Check if it's linear
    jones = pol_out.jones_vector
    phase_diff = np.angle(jones[1]) - np.angle(jones[0])
    phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))
    is_linear = np.abs(phase_diff) < 0.1 or np.abs(np.abs(phase_diff) - np.pi) < 0.1
    
    if is_linear:
        angle_rad = np.arctan2(np.abs(jones[1]), np.abs(jones[0]))
        angle_deg = np.rad2deg(angle_rad)
        print(f"\n✓ Linear polarization at {angle_deg:.2f}°")
        return angle_deg
    else:
        print(f"\n⚠ Not linear polarization!")
        return None


def test_qwp_double_pass_opposite_directions(fast_axis_deg):
    """
    Test double pass through QWP with mirror (opposite directions).
    This is the physical setup you described.
    """
    print(f"\n{'='*70}")
    print(f"QWP at {fast_axis_deg}° fast axis - DOUBLE PASS (OPPOSITE DIRECTIONS)")
    print(f"{'='*70}")
    print("Setup: Light → QWP (forward) → Mirror → QWP (backward)")
    
    pol_in = Polarization.horizontal()
    print(f"\nInput: Horizontal (0°)")
    
    # First pass
    pol_mid = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=90.0,
        fast_axis_deg=fast_axis_deg,
        is_forward=True
    )
    print(f"After QWP forward: {analyze_linear_angle(pol_mid.jones_vector)}")
    
    # Second pass (opposite direction)
    pol_out = transform_polarization_waveplate(
        pol_mid,
        phase_shift_deg=90.0,
        fast_axis_deg=fast_axis_deg,
        is_forward=False  # Opposite direction!
    )
    print(f"After QWP backward: {analyze_linear_angle(pol_out.jones_vector)}")
    print(f"Jones vector: {pol_out.jones_vector}")
    
    # Check if it returned to original
    jones_out_norm = pol_out.jones_vector / np.linalg.norm(pol_out.jones_vector)
    jones_in_norm = pol_in.jones_vector / np.linalg.norm(pol_in.jones_vector)
    
    is_same = np.allclose(np.abs(jones_out_norm), np.abs(jones_in_norm), atol=1e-3)
    
    if is_same:
        print(f"\n✓ Returned to original state (identity operation)")
    else:
        print(f"\n⚠ Did NOT return to original state")


if __name__ == "__main__":
    print("\n" + "#"*70)
    print("# QWP ROTATION ANGLE TESTS")
    print("#"*70)
    
    # Test QWP at 22.5°
    test_qwp_single_pass(22.5)
    angle_22_5 = test_qwp_double_pass_same_direction(22.5)
    test_qwp_double_pass_opposite_directions(22.5)
    
    print("\n" + "-"*70)
    
    # Test QWP at 45°
    test_qwp_single_pass(45.0)
    angle_45 = test_qwp_double_pass_same_direction(45.0)
    test_qwp_double_pass_opposite_directions(45.0)
    
    print("\n" + "#"*70)
    print("# SUMMARY")
    print("#"*70)
    
    if angle_22_5 is not None:
        print(f"\nQWP at 22.5°, double pass (same direction): {angle_22_5:.2f}°")
        if abs(angle_22_5 - 45.0) < 5.0:
            print("  ✓ Close to 45° as might be expected")
        else:
            print(f"  ⚠ Not 45° (off by {abs(angle_22_5 - 45.0):.2f}°)")
    
    if angle_45 is not None:
        print(f"\nQWP at 45°, double pass (same direction): {angle_45:.2f}°")
        if abs(angle_45 - 90.0) < 5.0:
            print("  ✓ Close to 90° as might be expected")
        else:
            print(f"  ⚠ Not 90° (off by {abs(angle_45 - 90.0):.2f}°)")
    
    print("\n" + "#"*70 + "\n")

