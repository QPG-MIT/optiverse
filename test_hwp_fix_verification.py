"""
Verify the HWP fix handles complex Jones vectors correctly.
"""
import numpy as np
from src.optiverse.core.geometry import transform_polarization_waveplate
from src.optiverse.core.models import Polarization

def analyze_polarization_state(jones):
    """Analyze a Jones vector to determine polarization state."""
    # Normalize
    jones_norm = jones / np.linalg.norm(jones)
    
    ex, ey = jones_norm[0], jones_norm[1]
    
    # Check if linear (phase difference is 0 or π)
    phase_diff = np.angle(ey) - np.angle(ex)
    # Normalize to [-π, π]
    while phase_diff > np.pi:
        phase_diff -= 2*np.pi
    while phase_diff < -np.pi:
        phase_diff += 2*np.pi
    
    is_linear = np.abs(phase_diff) < 0.1 or np.abs(np.abs(phase_diff) - np.pi) < 0.1
    
    if is_linear:
        # For linear polarization, angle is atan2(|Ey|, |Ex|)
        angle_rad = np.arctan2(np.abs(ey), np.abs(ex))
        angle_deg = np.rad2deg(angle_rad)
        return "linear", angle_deg, phase_diff
    else:
        # Circular or elliptical
        return "elliptical", None, phase_diff

def test_hwp_with_new_formula():
    """Test HWP behavior with the new Jones matrix formula."""
    print("\n" + "="*70)
    print("HWP at 22.5° - Testing New Jones Matrix Formula")
    print("="*70)
    
    pol_in = Polarization.horizontal()
    print(f"\nInput: Horizontal [1, 0]")
    print(f"  Jones: {pol_in.jones_vector}")
    
    # Single pass
    pol_out = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=180.0,
        fast_axis_deg=22.5,
        is_forward=True
    )
    
    print(f"\nAfter HWP (22.5° fast axis):")
    print(f"  Jones: {pol_out.jones_vector}")
    
    # Analyze the state
    state_type, angle, phase_diff = analyze_polarization_state(pol_out.jones_vector)
    
    print(f"  State: {state_type}")
    if state_type == "linear":
        print(f"  Angle: {angle:.2f}°")
        print(f"  Expected: 45.00°")
        if abs(angle - 45.0) < 1.0:
            print(f"  ✓ CORRECT!")
        else:
            print(f"  ❌ WRONG!")
    else:
        print(f"  Phase difference: {np.rad2deg(phase_diff):.2f}°")
        print(f"  ❌ Should be linear, not elliptical!")
    
    # Double pass
    print(f"\n{'─'*70}")
    print(f"Double Pass Test")
    print(f"{'─'*70}")
    
    pol_mid = pol_out
    pol_final = transform_polarization_waveplate(
        pol_mid,
        phase_shift_deg=180.0,
        fast_axis_deg=22.5,
        is_forward=True  # Same direction for now
    )
    
    print(f"\nAfter 2nd pass:")
    print(f"  Jones: {pol_final.jones_vector}")
    
    state_type2, angle2, phase_diff2 = analyze_polarization_state(pol_final.jones_vector)
    
    print(f"  State: {state_type2}")
    if state_type2 == "linear":
        print(f"  Angle: {angle2:.2f}°")
        print(f"  Expected: 90.00°")
        if abs(angle2 - 90.0) < 1.0:
            print(f"  ✓ CORRECT!")
            return True
        else:
            print(f"  ❌ WRONG!")
            return False
    else:
        print(f"  Phase difference: {np.rad2deg(phase_diff2):.2f}°")
        print(f"  ❌ Should be linear!")
        return False

def test_hwp_45_should_swap():
    """HWP at 45° should swap H ↔ V."""
    print("\n" + "="*70)
    print("HWP at 45° - Should Swap H ↔ V")
    print("="*70)
    
    pol_in = Polarization.horizontal()
    print(f"\nInput: Horizontal [1, 0]")
    
    pol_out = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=180.0,
        fast_axis_deg=45.0,
        is_forward=True
    )
    
    print(f"\nAfter HWP (45° fast axis):")
    print(f"  Jones: {pol_out.jones_vector}")
    
    # Should be vertical [0, 1] (up to global phase)
    jones = pol_out.jones_vector
    jones_norm = jones / np.linalg.norm(jones)
    
    # Check if it's mostly vertical
    ratio = np.abs(jones_norm[1]) / (np.abs(jones_norm[0]) + 1e-10)
    
    print(f"  |Ey|/|Ex| ratio: {ratio:.2f}")
    
    if ratio > 10:  # Mostly vertical
        print(f"  ✓ CORRECT - Horizontal swapped to Vertical!")
        return True
    else:
        print(f"  ❌ WRONG - Should be vertical!")
        return False

if __name__ == "__main__":
    try:
        success1 = test_hwp_with_new_formula()
        success2 = test_hwp_45_should_swap()
        
        print(f"\n" + "="*70)
        if success1 and success2:
            print("✓ All tests PASSED!")
        else:
            print("❌ Some tests FAILED!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

