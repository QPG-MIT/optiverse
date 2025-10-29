"""
Test half-wave plate rotation angles.
A HWP with fast axis at angle θ should rotate linear polarization by 2θ.
"""
import numpy as np
import math
from src.optiverse.core.geometry import transform_polarization_waveplate, deg2rad
from src.optiverse.core.models import Polarization

def analyze_jones_matrix(fast_axis_deg, phase_shift_deg=180.0):
    """Compute and display the Jones matrix for a waveplate."""
    print(f"\n{'='*70}")
    print(f"Analyzing HWP with fast axis at {fast_axis_deg}°")
    print(f"{'='*70}")
    
    theta = deg2rad(fast_axis_deg)
    delta = deg2rad(phase_shift_deg)
    
    # Rotation matrices
    c = np.cos(theta)
    s = np.sin(theta)
    R = np.array([[c, s], [-s, c]], dtype=complex)
    R_inv = np.array([[c, -s], [s, c]], dtype=complex)
    
    print(f"\nRotation angle θ = {fast_axis_deg}°")
    print(f"cos(θ) = {c:.6f}, sin(θ) = {s:.6f}")
    
    print(f"\nR(θ) = ")
    print(R)
    print(f"\nR(-θ) = ")
    print(R_inv)
    
    # Waveplate matrix in its own basis
    J_waveplate = np.array([[1.0, 0.0], [0.0, np.exp(1j * delta)]], dtype=complex)
    
    print(f"\nJ_waveplate (in fast/slow basis) = ")
    print(J_waveplate)
    print(f"exp(i·{phase_shift_deg}°) = {np.exp(1j * delta):.6f}")
    
    # Full Jones matrix
    J = R_inv @ J_waveplate @ R
    
    print(f"\nJ (full Jones matrix in lab frame) = R(-θ) · J_waveplate · R(θ)")
    print(J)
    
    # For a HWP (δ=180°), exp(iδ) = -1, so the matrix simplifies
    if abs(phase_shift_deg - 180.0) < 0.1:
        print(f"\nFor HWP (δ=180°), exp(iδ) = -1")
        print(f"Expected matrix elements:")
        c2 = np.cos(2*theta)
        s2 = np.sin(2*theta)
        print(f"  J11 = cos(2θ) = {c2:.6f}")
        print(f"  J12 = sin(2θ) = {s2:.6f}")
        print(f"  J21 = sin(2θ) = {s2:.6f}")
        print(f"  J22 = -cos(2θ) = {-c2:.6f}")
        
        print(f"\nActual matrix elements:")
        print(f"  J11 = {J[0,0].real:.6f}")
        print(f"  J12 = {J[0,1].real:.6f}")
        print(f"  J21 = {J[1,0].real:.6f}")
        print(f"  J22 = {J[1,1].real:.6f}")
        
        # Check if they match
        if np.allclose(J.real, [[c2, s2], [s2, -c2]], atol=1e-6):
            print(f"  ✓ Matrix elements match expected HWP form!")
        else:
            print(f"  ❌ Matrix elements DO NOT match expected form!")
    
    return J


def test_hwp_rotation(fast_axis_deg):
    """Test that HWP rotates polarization by 2θ."""
    print(f"\n{'='*70}")
    print(f"Testing HWP rotation with fast axis at {fast_axis_deg}°")
    print(f"Expected rotation: 2 × {fast_axis_deg}° = {2*fast_axis_deg}°")
    print(f"{'='*70}")
    
    # Start with horizontal polarization
    pol_in = Polarization.horizontal()
    print(f"\nInput: Horizontal polarization")
    print(f"  Jones vector: {pol_in.jones_vector}")
    
    # Apply HWP
    pol_out = transform_polarization_waveplate(
        pol_in,
        phase_shift_deg=180.0,
        fast_axis_deg=fast_axis_deg,
        is_forward=True
    )
    
    print(f"\nOutput after HWP:")
    print(f"  Jones vector: {pol_out.jones_vector}")
    
    # Calculate the actual rotation angle from the Jones vector
    # For linear polarization, angle = atan2(Ey, Ex)
    jones = pol_out.jones_vector
    
    # Take only real parts for linear polarization
    ex = jones[0].real
    ey = jones[1].real
    
    actual_angle_rad = np.arctan2(ey, ex)
    actual_angle_deg = np.rad2deg(actual_angle_rad)
    
    # Normalize to [0, 180] for linear polarization
    if actual_angle_deg < 0:
        actual_angle_deg += 180
    
    expected_angle_deg = 2 * fast_axis_deg
    if expected_angle_deg >= 180:
        expected_angle_deg -= 180
    
    print(f"\nPolarization angle:")
    print(f"  Expected: {expected_angle_deg:.2f}°")
    print(f"  Actual: {actual_angle_deg:.2f}°")
    print(f"  Difference: {abs(actual_angle_deg - expected_angle_deg):.2f}°")
    
    if abs(actual_angle_deg - expected_angle_deg) < 1.0:
        print(f"  ✓ Rotation is CORRECT!")
        return True
    else:
        print(f"  ❌ Rotation is WRONG!")
        return False


def test_multiple_angles():
    """Test HWP rotation for multiple fast axis angles."""
    print(f"\n{'#'*70}")
    print(f"# TESTING HWP ROTATION FOR MULTIPLE FAST AXIS ANGLES")
    print(f"{'#'*70}")
    
    test_angles = [0, 22.5, 45, 67.5, 90]
    results = {}
    
    for angle in test_angles:
        # First analyze the Jones matrix
        analyze_jones_matrix(angle, 180.0)
        
        # Then test the rotation
        success = test_hwp_rotation(angle)
        results[angle] = success
        
        print()
    
    print(f"\n{'#'*70}")
    print(f"# SUMMARY")
    print(f"{'#'*70}")
    for angle, success in results.items():
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"  Fast axis {angle:5.1f}° → Expected rotation {2*angle:5.1f}° : {status}")
    
    all_pass = all(results.values())
    if all_pass:
        print(f"\n🎉 All tests PASSED!")
    else:
        print(f"\n❌ Some tests FAILED!")
    
    return all_pass


if __name__ == "__main__":
    try:
        all_pass = test_multiple_angles()
        exit(0 if all_pass else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

