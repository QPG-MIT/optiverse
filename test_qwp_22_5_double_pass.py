"""
Test QWP at 22.5° - double pass scenario
"""
import numpy as np
from src.optiverse.core.geometry import transform_polarization_waveplate
from src.optiverse.core.models import Polarization

def test_qwp_22_5_double_pass():
    """Test double pass through QWP at 22.5°."""
    print(f"\n{'='*70}")
    print(f"QWP at 22.5° - Double Pass Scenario")
    print(f"{'='*70}")
    print(f"Setup: Ray → QWP (forward) → Mirror → QWP (backward)")
    
    pol_in = Polarization.horizontal()
    print(f"\nStep 1: Initial polarization = Horizontal")
    print(f"  Jones vector: {pol_in.jones_vector}")
    
    # First pass (forward)
    pol_after_first = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=90.0,  # Quarter wave
        fast_axis_deg=22.5,
        is_forward=True
    )
    
    print(f"\nStep 2: After QWP (forward pass)")
    print(f"  Jones vector: {pol_after_first.jones_vector}")
    
    jones1 = pol_after_first.jones_vector
    ex1 = np.abs(jones1[0])
    ey1 = np.abs(jones1[1])
    phase_diff1 = np.angle(jones1[1]) - np.angle(jones1[0])
    print(f"  |Ex|={ex1:.6f}, |Ey|={ey1:.6f}")
    print(f"  Phase difference: {np.rad2deg(phase_diff1):.2f}°")
    
    # Mirror (assume ideal reflection that preserves polarization state)
    pol_after_mirror = pol_after_first
    print(f"\nStep 3: After mirror (polarization preserved)")
    
    # Second pass (backward)
    pol_after_second = transform_polarization_waveplate(
        pol_after_mirror,
        phase_shift_deg=90.0,
        fast_axis_deg=22.5,
        is_forward=False
    )
    
    print(f"\nStep 4: After QWP (backward pass)")
    print(f"  Jones vector: {pol_after_second.jones_vector}")
    
    jones2 = pol_after_second.jones_vector
    ex2 = np.abs(jones2[0])
    ey2 = np.abs(jones2[1])
    phase_diff2 = np.angle(jones2[1]) - np.angle(jones2[0])
    print(f"  |Ex|={ex2:.6f}, |Ey|={ey2:.6f}")
    print(f"  Phase difference: {np.rad2deg(phase_diff2):.2f}°")
    
    # Check if it's linear
    is_linear = np.abs(np.abs(phase_diff2)) < 0.1 or np.abs(np.abs(phase_diff2) - np.pi) < 0.1
    
    if is_linear:
        angle2 = np.rad2deg(np.arctan2(ey2, ex2))
        if angle2 < 0:
            angle2 += 180
        print(f"  Polarization angle: {angle2:.2f}°")
    else:
        print(f"  State: Elliptical/Circular")
    
    # Analysis
    print(f"\n{'─'*70}")
    print(f"ANALYSIS")
    print(f"{'─'*70}")
    print(f"Expected behavior for double pass QWP at 22.5°:")
    print(f"  1st pass: H → elliptical/circular")
    print(f"  2nd pass (backward): should be OPPOSITE of forward")
    print(f"  Result: Should return to H (identity)")
    
    # Check if we got back to horizontal
    jones_final = pol_after_second.jones_vector
    jones_in = pol_in.jones_vector
    
    # Normalize both
    jones_final_norm = jones_final / np.linalg.norm(jones_final)
    jones_in_norm = jones_in / np.linalg.norm(jones_in)
    
    # Check if they're the same up to global phase
    ratio = jones_final_norm[0] / jones_in_norm[0] if np.abs(jones_in_norm[0]) > 1e-6 else jones_final_norm[1] / jones_in_norm[1]
    expected = ratio * jones_in_norm
    
    is_identity = np.allclose(jones_final_norm, expected, atol=1e-3)
    
    print(f"\n  Did we return to original state? {is_identity}")
    if is_identity:
        print(f"  ✓ CORRECT! QWP forward + backward = identity")
    else:
        print(f"  ❌ ERROR! Should return to horizontal")
    
    print(f"\n{'='*70}")
    return is_identity


def test_qwp_45_double_pass():
    """Test double pass through QWP at 45°."""
    print(f"\n{'='*70}")
    print(f"QWP at 45° - Double Pass Scenario")
    print(f"{'='*70}")
    print(f"Setup: Ray → QWP (forward) → Mirror → QWP (backward)")
    
    pol_in = Polarization.horizontal()
    print(f"\nStep 1: Initial polarization = Horizontal")
    print(f"  Jones vector: {pol_in.jones_vector}")
    
    # First pass (forward)
    pol_after_first = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=90.0,  # Quarter wave
        fast_axis_deg=45.0,
        is_forward=True
    )
    
    print(f"\nStep 2: After QWP (forward pass)")
    print(f"  Jones vector: {pol_after_first.jones_vector}")
    
    jones1 = pol_after_first.jones_vector
    phase_diff1 = np.angle(jones1[1]) - np.angle(jones1[0])
    print(f"  Phase difference: {np.rad2deg(phase_diff1):.2f}°")
    print(f"  Should be circular: |Ex|={np.abs(jones1[0]):.6f}, |Ey|={np.abs(jones1[1]):.6f}")
    
    # Mirror
    pol_after_mirror = pol_after_first
    
    # Second pass (backward)
    pol_after_second = transform_polarization_waveplate(
        pol_after_mirror,
        phase_shift_deg=90.0,
        fast_axis_deg=45.0,
        is_forward=False
    )
    
    print(f"\nStep 4: After QWP (backward pass)")
    print(f"  Jones vector: {pol_after_second.jones_vector}")
    
    # Check if we got back to horizontal
    jones_final = pol_after_second.jones_vector
    jones_in = pol_in.jones_vector
    
    # Normalize both
    jones_final_norm = jones_final / np.linalg.norm(jones_final)
    jones_in_norm = jones_in / np.linalg.norm(jones_in)
    
    # Check if they're the same up to global phase
    ratio = jones_final_norm[0] / jones_in_norm[0] if np.abs(jones_in_norm[0]) > 1e-6 else jones_final_norm[1] / jones_in_norm[1]
    expected = ratio * jones_in_norm
    
    is_identity = np.allclose(jones_final_norm, expected, atol=1e-3)
    
    print(f"\n  Did we return to original state? {is_identity}")
    if is_identity:
        print(f"  ✓ CORRECT! QWP forward + backward = identity")
    else:
        print(f"  ❌ ERROR! Should return to horizontal")
    
    print(f"\n{'='*70}")
    return is_identity


if __name__ == "__main__":
    result1 = test_qwp_22_5_double_pass()
    result2 = test_qwp_45_double_pass()
    
    print(f"\n{'='*70}")
    if result1 and result2:
        print("✓ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print(f"{'='*70}\n")

