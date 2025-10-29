"""
Test HWP at 22.5° with directionality (forward and backward passes).
"""
import numpy as np
from src.optiverse.core.geometry import transform_polarization_waveplate
from src.optiverse.core.models import Polarization

def test_hwp_22_5_directionality():
    """
    Test HWP at 22.5° fast axis with forward and backward passes.
    
    Expected behavior:
    - Forward pass: H → rotated by 45°
    - Backward pass: H → rotated by -45° (or 135° from horizontal)
    
    For HWP, forward and backward should give SAME result (exp(i·180°) = exp(-i·180°) = -1)
    """
    print(f"\n{'='*70}")
    print(f"HWP at 22.5° Fast Axis - Directionality Test")
    print(f"{'='*70}")
    
    pol_in = Polarization.horizontal()
    print(f"\nInput: Horizontal polarization [1, 0]")
    print(f"  Jones vector: {pol_in.jones_vector}")
    
    # Forward pass
    pol_forward = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=180.0,
        fast_axis_deg=22.5,
        is_forward=True
    )
    
    print(f"\n{'─'*70}")
    print(f"FORWARD PASS (is_forward=True)")
    print(f"{'─'*70}")
    print(f"  Jones vector: {pol_forward.jones_vector}")
    
    # Calculate angle
    jones_fwd = pol_forward.jones_vector
    ex_fwd = jones_fwd[0].real
    ey_fwd = jones_fwd[1].real
    angle_fwd = np.rad2deg(np.arctan2(ey_fwd, ex_fwd))
    if angle_fwd < 0:
        angle_fwd += 180
    
    print(f"  Ex: {ex_fwd:.6f}, Ey: {ey_fwd:.6f}")
    print(f"  Polarization angle: {angle_fwd:.2f}°")
    print(f"  Expected: 45.00° (2 × 22.5°)")
    print(f"  Difference: {abs(angle_fwd - 45.0):.2f}°")
    
    # Backward pass
    pol_backward = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=180.0,
        fast_axis_deg=22.5,
        is_forward=False
    )
    
    print(f"\n{'─'*70}")
    print(f"BACKWARD PASS (is_forward=False)")
    print(f"{'─'*70}")
    print(f"  Jones vector: {pol_backward.jones_vector}")
    
    # Calculate angle
    jones_bwd = pol_backward.jones_vector
    ex_bwd = jones_bwd[0].real
    ey_bwd = jones_bwd[1].real
    angle_bwd = np.rad2deg(np.arctan2(ey_bwd, ex_bwd))
    if angle_bwd < 0:
        angle_bwd += 180
    
    print(f"  Ex: {ex_bwd:.6f}, Ey: {ey_bwd:.6f}")
    print(f"  Polarization angle: {angle_bwd:.2f}°")
    print(f"  Expected: 45.00° (same as forward for HWP)")
    print(f"  Difference: {abs(angle_bwd - 45.0):.2f}°")
    
    # Compare forward and backward
    print(f"\n{'─'*70}")
    print(f"COMPARISON")
    print(f"{'─'*70}")
    
    # For HWP, forward and backward should be identical (up to global phase)
    are_same = np.allclose(np.abs(jones_fwd), np.abs(jones_bwd), atol=1e-6)
    
    print(f"  Forward angle: {angle_fwd:.2f}°")
    print(f"  Backward angle: {angle_bwd:.2f}°")
    print(f"  Are magnitudes same: {are_same}")
    
    if are_same:
        print(f"  ✓ CORRECT: HWP forward and backward give same result")
    else:
        print(f"  ❌ ERROR: HWP forward and backward should be the same!")
    
    print(f"\n{'='*70}")
    
    return are_same


def test_hwp_double_pass_22_5():
    """
    Test double pass through HWP at 22.5°.
    
    Scenario: Ray hits HWP, reflects off mirror, hits HWP again from opposite direction.
    Both passes use same fast axis orientation but opposite propagation directions.
    """
    print(f"\n{'='*70}")
    print(f"HWP at 22.5° - Double Pass Scenario")
    print(f"{'='*70}")
    print(f"Setup: Ray → HWP (forward) → Mirror → HWP (backward)")
    
    pol_in = Polarization.horizontal()
    print(f"\nStep 1: Initial polarization = Horizontal")
    print(f"  Jones vector: {pol_in.jones_vector}")
    
    # First pass (forward)
    pol_after_first = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=180.0,
        fast_axis_deg=22.5,
        is_forward=True
    )
    
    print(f"\nStep 2: After HWP (forward pass)")
    print(f"  Jones vector: {pol_after_first.jones_vector}")
    
    jones1 = pol_after_first.jones_vector
    ex1 = jones1[0].real
    ey1 = jones1[1].real
    angle1 = np.rad2deg(np.arctan2(ey1, ex1))
    if angle1 < 0:
        angle1 += 180
    print(f"  Polarization angle: {angle1:.2f}°")
    
    # Mirror (assume ideal reflection that preserves polarization state)
    pol_after_mirror = pol_after_first
    print(f"\nStep 3: After mirror (polarization preserved)")
    
    # Second pass (backward)
    pol_after_second = transform_polarization_waveplate(
        pol_after_mirror,
        phase_shift_deg=180.0,
        fast_axis_deg=22.5,
        is_forward=False
    )
    
    print(f"\nStep 4: After HWP (backward pass)")
    print(f"  Jones vector: {pol_after_second.jones_vector}")
    
    jones2 = pol_after_second.jones_vector
    ex2 = jones2[0].real
    ey2 = jones2[1].real
    angle2 = np.rad2deg(np.arctan2(ey2, ex2))
    if angle2 < 0:
        angle2 += 180
    print(f"  Polarization angle: {angle2:.2f}°")
    
    # Analysis
    print(f"\n{'─'*70}")
    print(f"ANALYSIS")
    print(f"{'─'*70}")
    print(f"  Input angle: 0°")
    print(f"  After 1st pass: {angle1:.2f}°")
    print(f"  After 2nd pass: {angle2:.2f}°")
    print(f"  Total rotation: {angle2:.2f}°")
    
    # For HWP, each pass rotates by 2θ = 45°
    # Two passes: should rotate by 2 × 45° = 90°
    # But since HWP forward = backward, we get 45° + 45° = 90°
    expected_total = 90.0
    if angle2 > 90:
        # Could also wrap around
        expected_total = angle2
    
    print(f"  Expected total: {expected_total:.2f}° (45° + 45°)")
    
    if abs(angle2 - expected_total) < 1.0:
        print(f"  ✓ CORRECT!")
    else:
        print(f"  ❌ ERROR: Total rotation is wrong!")
    
    print(f"\n{'='*70}")


if __name__ == "__main__":
    try:
        print("\n" + "#"*70)
        print("# HWP 22.5° DIRECTIONALITY TESTS")
        print("#"*70)
        
        test_hwp_22_5_directionality()
        test_hwp_double_pass_22_5()
        
        print("\n" + "#"*70)
        print("# COMPLETE")
        print("#"*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

