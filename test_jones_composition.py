"""
Test Jones matrix composition for HWP.
When you pass through the same HWP twice, what should happen?
"""
import numpy as np
from src.optiverse.core.geometry import deg2rad

def compute_hwp_jones_matrix(fast_axis_deg):
    """Compute the Jones matrix for a HWP at given fast axis angle."""
    theta = deg2rad(fast_axis_deg)
    delta = deg2rad(180.0)  # HWP
    
    # Rotation matrices
    c = np.cos(theta)
    s = np.sin(theta)
    R = np.array([[c, s], [-s, c]], dtype=complex)
    R_inv = np.array([[c, -s], [s, c]], dtype=complex)
    
    # Waveplate matrix in its own basis
    J_waveplate = np.array([[1.0, 0.0], [0.0, np.exp(1j * delta)]], dtype=complex)
    
    # Full Jones matrix: J = R^(-1) · J_waveplate · R
    J = R_inv @ J_waveplate @ R
    
    return J

def test_jones_composition():
    """Test what happens when you apply the same HWP Jones matrix twice."""
    print("\n" + "="*70)
    print("JONES MATRIX COMPOSITION TEST - HWP at 22.5°")
    print("="*70)
    
    fast_axis_deg = 22.5
    
    # Compute Jones matrix
    J = compute_hwp_jones_matrix(fast_axis_deg)
    
    print(f"\nJones matrix J for HWP at {fast_axis_deg}°:")
    print(J)
    print(f"\nReal part:")
    print(J.real)
    
    # Apply twice: J · J
    J2 = J @ J
    
    print(f"\nJ² = J · J (applying HWP twice):")
    print(J2)
    print(f"\nReal part:")
    print(J2.real)
    
    # For HWP, J² should rotate by 4θ = 4 × 22.5° = 90°
    # The Jones matrix for 90° rotation is:
    # [[0, 1], [1, 0]] (swaps H and V)
    
    expected_J2 = np.array([[0, 1], [1, 0]], dtype=complex)
    print(f"\nExpected J² (90° rotation):")
    print(expected_J2)
    
    # Check if they match
    if np.allclose(J2.real, expected_J2.real, atol=1e-6):
        print(f"\n✓ J² matches expected!")
    else:
        print(f"\n❌ J² does NOT match expected!")
        print(f"   Difference:")
        print(J2.real - expected_J2.real)
    
    # Test on horizontal polarization
    print(f"\n" + "-"*70)
    print(f"Testing on horizontal polarization [1, 0]")
    print(f"-"*70)
    
    pol_in = np.array([1.0, 0.0], dtype=complex)
    print(f"\nInput: {pol_in}")
    
    # Apply J once
    pol_after_1 = J @ pol_in
    print(f"\nAfter 1st pass (J · pol_in):")
    print(f"  {pol_after_1}")
    angle_1 = np.rad2deg(np.arctan2(pol_after_1[1].real, pol_after_1[0].real))
    if angle_1 < 0:
        angle_1 += 180
    print(f"  Angle: {angle_1:.2f}°")
    
    # Apply J twice
    pol_after_2 = J @ pol_after_1
    print(f"\nAfter 2nd pass (J · (J · pol_in)):")
    print(f"  {pol_after_2}")
    angle_2 = np.rad2deg(np.arctan2(pol_after_2[1].real, pol_after_2[0].real))
    if angle_2 < 0:
        angle_2 += 180
    print(f"  Angle: {angle_2:.2f}°")
    
    # Or equivalently: J² · pol_in
    pol_after_2_alt = J2 @ pol_in
    print(f"\nOr equivalently (J² · pol_in):")
    print(f"  {pol_after_2_alt}")
    
    # Expected: 90° (vertical polarization)
    print(f"\n" + "-"*70)
    print(f"ANALYSIS")
    print(f"-"*70)
    print(f"  Input angle: 0°")
    print(f"  After 1st pass: {angle_1:.2f}° (expected 45°)")
    print(f"  After 2nd pass: {angle_2:.2f}° (expected 90°)")
    
    if abs(angle_2 - 90.0) < 1.0:
        print(f"  ✓ CORRECT!")
    else:
        print(f"  ❌ WRONG!")
    
    print(f"\n" + "="*70)


def analyze_hwp_matrix_properties():
    """Analyze mathematical properties of HWP Jones matrix."""
    print("\n" + "="*70)
    print("HWP JONES MATRIX PROPERTIES")
    print("="*70)
    
    fast_axis_deg = 22.5
    J = compute_hwp_jones_matrix(fast_axis_deg)
    
    print(f"\nFor HWP at {fast_axis_deg}°:")
    print(f"J =")
    print(J.real)
    
    # Compute J²
    J2 = J @ J
    print(f"\nJ² =")
    print(J2.real)
    
    # Compute J⁴ (should be identity for HWP since 4 × 45° = 180° ≡ 0° mod 180°)
    J4 = J2 @ J2
    print(f"\nJ⁴ =")
    print(J4.real)
    
    # Check if J⁴ = I (identity)
    I = np.eye(2)
    if np.allclose(J4.real, I, atol=1e-6) or np.allclose(J4.real, -I, atol=1e-6):
        print(f"  ✓ J⁴ = ±I (identity, up to sign)")
    else:
        print(f"  ❌ J⁴ ≠ ±I")
    
    # Determinant
    det_J = np.linalg.det(J)
    print(f"\ndet(J) = {det_J}")
    print(f"  Expected: ±1 (unitary)")
    
    # Eigenvalues
    eigenvalues = np.linalg.eigvals(J)
    print(f"\nEigenvalues of J:")
    print(f"  {eigenvalues}")
    print(f"  Expected: exp(±i·θ) for some angle θ")
    
    print(f"\n" + "="*70)


if __name__ == "__main__":
    try:
        test_jones_composition()
        analyze_hwp_matrix_properties()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

