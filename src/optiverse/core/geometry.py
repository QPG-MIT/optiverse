from __future__ import annotations

import math
from typing import Optional, Tuple, TYPE_CHECKING

import numpy as np

# Try to import numba, but make it optional
try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    # Fallback: no-op decorator if numba isn't available
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    NUMBA_AVAILABLE = False
    print("Warning: numba not available. Raytracing will be slower. Install with: pip install numba")

if TYPE_CHECKING:
    from .models import Polarization


@jit(nopython=True, cache=True)
def deg2rad(a: float) -> float:
    """Convert degrees to radians. JIT-compiled for performance when numba is available."""
    return a * math.pi / 180.0


@jit(nopython=True, cache=True)
def normalize(v: np.ndarray) -> np.ndarray:
    """Normalize a vector. JIT-compiled for performance when numba is available."""
    n = math.sqrt(v[0]**2 + v[1]**2)
    if n == 0.0:
        return v.copy()
    else:
        return v / n


@jit(nopython=True, cache=True)
def reflect_vec(v: np.ndarray, n_hat: np.ndarray) -> np.ndarray:
    """Reflect vector v across normal n_hat. JIT-compiled for performance when numba is available."""
    dot_product = v[0] * n_hat[0] + v[1] * n_hat[1]
    return v - 2.0 * dot_product * n_hat


def jones_matrix_rotation(angle_deg: float) -> np.ndarray:
    """
    Create Jones matrix for coordinate rotation.
    
    Args:
        angle_deg: Rotation angle in degrees
    
    Returns:
        2x2 complex rotation matrix
    """
    theta = deg2rad(angle_deg)
    c = np.cos(theta)
    s = np.sin(theta)
    return np.array([[c, s], [-s, c]], dtype=complex)


def transform_polarization_mirror(pol: 'Polarization', v_in: np.ndarray, n_hat: np.ndarray) -> 'Polarization':
    """
    Transform polarization upon reflection from a mirror.
    
    For ideal metallic mirrors, s-polarization (perpendicular to plane of incidence)
    maintains phase, while p-polarization (parallel to plane) gets phase shift of π.
    
    Args:
        pol: Input polarization state
        v_in: Incident ray direction (normalized)
        n_hat: Surface normal (normalized)
    
    Returns:
        Transformed polarization state
    """
    from .models import Polarization
    
    # Compute plane of incidence
    v_norm = normalize(v_in)
    
    # s-polarization direction (perpendicular to plane of incidence)
    # This is the cross product of v_in and n_hat
    s_hat = np.cross(np.append(v_norm, 0), np.append(n_hat, 0))[:2]
    s_hat = normalize(s_hat) if np.linalg.norm(s_hat) > 1e-12 else np.array([0.0, 1.0])
    
    # p-polarization direction (in plane of incidence, perpendicular to v_in)
    p_hat = np.array([-s_hat[1], s_hat[0]])
    
    # Decompose input polarization into s and p components
    jones = pol.jones_vector
    s_component = np.dot(jones, s_hat)
    p_component = np.dot(jones, p_hat)
    
    # Apply reflection: s maintains phase, p gets π phase shift
    # Jones matrix for ideal mirror reflection: [[1, 0], [0, -1]] in s-p basis
    s_out = s_component
    p_out = -p_component  # π phase shift = multiplication by -1
    
    # Reconstruct in original coordinate system
    jones_out = s_out * s_hat + p_out * p_hat
    
    return Polarization(jones_out)


def transform_polarization_lens(pol: 'Polarization') -> 'Polarization':
    """
    Transform polarization through a lens.
    
    Ideal lenses preserve polarization state (no birefringence).
    
    Args:
        pol: Input polarization state
    
    Returns:
        Unchanged polarization state
    """
    # Ideal lens preserves polarization
    return pol


def transform_polarization_waveplate(
    pol: 'Polarization',
    phase_shift_deg: float,
    fast_axis_deg: float
) -> 'Polarization':
    """
    Transform polarization through a waveplate.
    
    Physics Implementation:
    ----------------------
    A waveplate introduces a phase shift between light polarized along its fast axis
    and slow axis. The fast axis has lower refractive index, so light travels faster.
    
    Common waveplates:
    - Quarter waveplate (QWP): 90° phase shift (π/2 radians)
      * Converts linear → circular (at 45° to axis)
      * Converts circular → linear
    - Half waveplate (HWP): 180° phase shift (π radians)
      * Rotates linear polarization
      * Switches handedness of circular polarization
    
    Jones Matrix Formalism:
    ----------------------
    The Jones matrix for a waveplate with fast axis at angle θ and phase shift δ:
    
    J = R(-θ) · [[1, 0], [0, exp(iδ)]] · R(θ)
    
    Where:
    - R(θ) is the rotation matrix
    - exp(iδ) represents the phase shift on the slow axis
    - Fast axis component has no phase shift (factor of 1)
    
    Args:
        pol: Input polarization state (Jones vector)
        phase_shift_deg: Phase shift in degrees (90° for QWP, 180° for HWP)
        fast_axis_deg: ABSOLUTE angle of fast axis in lab frame (degrees)
                       0° = horizontal, 90° = vertical
    
    Returns:
        Transformed polarization state
    
    Example:
        # Convert horizontal to right circular with QWP at 45°
        pol_in = Polarization.horizontal()  # [1, 0]
        pol_out = transform_polarization_waveplate(
            pol_in,
            phase_shift_deg=90.0,  # Quarter wave
            fast_axis_deg=45.0     # 45° fast axis
        )
        # Result: right circular [1/√2, i/√2]
    """
    from .models import Polarization
    
    # Convert angles to radians
    theta = deg2rad(fast_axis_deg)
    delta = deg2rad(phase_shift_deg)
    
    # Rotation matrix to fast/slow axis basis
    c = np.cos(theta)
    s = np.sin(theta)
    R = np.array([[c, s], [-s, c]], dtype=complex)
    R_inv = np.array([[c, -s], [s, c]], dtype=complex)
    
    # Waveplate Jones matrix in its own basis
    # Fast axis has phase 0, slow axis has phase delta
    J_waveplate = np.array([[1.0, 0.0], [0.0, np.exp(1j * delta)]], dtype=complex)
    
    # Full Jones matrix in lab frame: J = R^(-1) · J_waveplate · R
    J = R_inv @ J_waveplate @ R
    
    # Apply to input Jones vector
    jones_in = pol.jones_vector
    jones_out = J @ jones_in
    
    return Polarization(jones_out)


def transform_polarization_beamsplitter(
    pol: 'Polarization',
    v_in: np.ndarray,
    n_hat: np.ndarray,
    t_hat: np.ndarray,
    is_polarizing: bool,
    pbs_axis_deg: float,
    is_transmitted: bool
) -> Tuple['Polarization', float]:
    """
    Transform polarization through a beamsplitter.
    
    Physics Implementation:
    ----------------------
    This function correctly implements PBS behavior for arbitrary angles using
    Jones vector formalism. It follows Malus's Law: I = I₀ cos²(θ), where θ is
    the angle between input polarization and the transmission axis.
    
    For PBS (Polarizing Beam Splitter):
    - p-polarization (parallel to transmission axis) is transmitted
    - s-polarization (perpendicular) is reflected
    - For polarization at angle θ to transmission axis:
      * Transmitted intensity = cos²(θ)
      * Reflected intensity = sin²(θ)
    - Total intensity is conserved: T + R = 1.0
    
    For non-polarizing BS:
    - Both polarizations split according to T/R ratio
    - Polarization state is preserved (except phase shift on reflection)
    
    The implementation has been validated with comprehensive tests verifying:
    - Malus's Law for angles 0° to 90°
    - Intensity conservation for arbitrary angle combinations
    - Correct behavior at 0°, 45°, 90°, and custom angles
    
    Args:
        pol: Input polarization state (Jones vector)
        v_in: Incident ray direction (normalized, currently unused but kept for API)
        n_hat: Surface normal (normalized, currently unused but kept for API)
        t_hat: Tangent direction (currently unused but kept for API)
        is_polarizing: True for PBS mode, False for regular beamsplitter
        pbs_axis_deg: Transmission axis angle in lab frame (degrees)
                      This is the ABSOLUTE angle, not relative to element
        is_transmitted: True for transmitted ray, False for reflected ray
    
    Returns:
        Tuple of (transformed_polarization, intensity_factor)
        - transformed_polarization: Output Jones vector (normalized)
        - intensity_factor: Fraction of input intensity (0.0 to 1.0)
    
    Example:
        # Horizontal input (0°) through PBS with 45° transmission axis
        pol_in = Polarization.horizontal()  # [1, 0]
        pol_t, int_t = transform_polarization_beamsplitter(
            pol_in, v_in, n_hat, t_hat,
            is_polarizing=True,
            pbs_axis_deg=45.0,  # 45° transmission axis
            is_transmitted=True
        )
        # Result: int_t = cos²(45°) = 0.5 (50% transmitted)
        
        pol_r, int_r = transform_polarization_beamsplitter(
            pol_in, v_in, n_hat, t_hat,
            is_polarizing=True,
            pbs_axis_deg=45.0,
            is_transmitted=False
        )
        # Result: int_r = sin²(45°) = 0.5 (50% reflected)
        # Conservation: int_t + int_r = 1.0 ✓
    """
    from .models import Polarization
    
    if not is_polarizing:
        # Non-polarizing beamsplitter: preserve polarization
        if is_transmitted:
            return pol, 1.0
        else:
            # Apply mirror-like phase shift for reflection
            return transform_polarization_mirror(pol, v_in, n_hat), 1.0
    
    # PBS mode: separate polarizations based on transmission axis
    # ============================================================
    
    # Define transmission axis (p-axis) and perpendicular axis (s-axis) in lab frame
    # The p-axis is the direction that transmits, s-axis reflects
    axis_rad = deg2rad(pbs_axis_deg)
    p_axis = np.array([np.cos(axis_rad), np.sin(axis_rad)])      # Transmission direction
    s_axis = np.array([-np.sin(axis_rad), np.cos(axis_rad)])     # Reflection direction (perpendicular)
    
    # Decompose input Jones vector onto p and s axes
    # This is the key step that implements Malus's Law
    jones = pol.jones_vector
    p_component = np.dot(jones, p_axis)  # Component parallel to transmission axis
    s_component = np.dot(jones, s_axis)  # Component perpendicular (to be reflected)
    
    if is_transmitted:
        # Transmit only the p-polarization component
        # Intensity = |p_component|² (Malus's Law: cos²(θ))
        jones_out = p_component * p_axis
        intensity = float(np.abs(p_component) ** 2)
    else:
        # Reflect only the s-polarization component
        # Intensity = |s_component|² (Malus's Law: sin²(θ))
        # Note: Negative sign introduces π phase shift on reflection
        jones_out = -s_component * s_axis
        intensity = float(np.abs(s_component) ** 2)
    
    # Normalize the output Jones vector to unit length
    # (The intensity is returned separately as the intensity_factor)
    if intensity > 1e-12:
        jones_out = jones_out / np.sqrt(intensity)
    else:
        # No intensity in this component, return zero vector
        jones_out = np.zeros(2, dtype=complex)
    
    return Polarization(jones_out), intensity


def compute_dichroic_reflectance(
    wavelength_nm: float,
    cutoff_wavelength_nm: float,
    transition_width_nm: float,
    pass_type: str = "longpass"
) -> Tuple[float, float]:
    """
    Compute reflection and transmission coefficients for a dichroic mirror.
    
    Dichroic mirrors selectively reflect or transmit based on wavelength.
    The transition is modeled with a smooth sigmoid function.
    
    Physical model:
    - Long pass: R(λ) = 1 / (1 + exp((λ - λ_cutoff) / Δλ)), T(λ) = 1 - R(λ)
      (reflects short wavelengths, transmits long wavelengths)
    - Short pass: R(λ) = 1 / (1 + exp((λ_cutoff - λ) / Δλ)), T(λ) = 1 - R(λ)
      (reflects long wavelengths, transmits short wavelengths)
    
    Args:
        wavelength_nm: Incident light wavelength in nanometers
        cutoff_wavelength_nm: Cutoff wavelength (50% point)
        transition_width_nm: Characteristic width of transition region
        pass_type: "longpass" or "shortpass"
        
    Returns:
        Tuple of (reflectance, transmittance) both in range [0, 1]
        
    Notes:
        - Long pass: Short wavelengths (< cutoff) have high reflectance
        - Short pass: Long wavelengths (> cutoff) have high reflectance
        - Smooth transition preserves energy (R + T ≈ 1)
    """
    # Normalized deviation from cutoff
    delta = (wavelength_nm - cutoff_wavelength_nm) / max(1.0, transition_width_nm)
    
    # Sigmoid function for smooth transition
    if pass_type == "shortpass":
        # Invert the behavior: reflect long wavelengths, transmit short wavelengths
        # R increases from 0 to 1 as wavelength increases
        reflectance = 1.0 / (1.0 + np.exp(-delta))
    else:  # longpass (default)
        # R decreases from 1 to 0 as wavelength increases
        reflectance = 1.0 / (1.0 + np.exp(delta))
    
    transmittance = 1.0 - reflectance
    
    # Clamp to physical range
    reflectance = float(np.clip(reflectance, 0.0, 1.0))
    transmittance = float(np.clip(transmittance, 0.0, 1.0))
    
    return reflectance, transmittance


@jit(nopython=True, cache=True)
def ray_hit_element(
    P: np.ndarray,
    V: np.ndarray,
    A: np.ndarray,
    B: np.ndarray,
    tol: float = 1e-9,
):
    """
    Intersect ray (P + t V, t>0) with finite segment AB.
    JIT-compiled for maximum performance.

    Returns (t, X, t_hat, n_hat, C, L) or None if no hit.
    """
    # Compute segment direction and length
    diff = B - A
    L = math.sqrt(diff[0]**2 + diff[1]**2)
    if L < tol:
        return None
    
    t_hat = diff / L
    n_hat = np.array([-t_hat[1], t_hat[0]])
    C = 0.5 * (A + B)
    
    # Check if ray is parallel to segment
    denom = V[0] * n_hat[0] + V[1] * n_hat[1]
    if abs(denom) < tol:
        return None
    
    # Compute intersection parameter
    diff_CP = C - P
    t = (diff_CP[0] * n_hat[0] + diff_CP[1] * n_hat[1]) / denom
    if t <= tol:
        return None
    
    # Compute intersection point
    X = P + t * V
    
    # Check if intersection is within segment bounds
    diff_XC = X - C
    s = diff_XC[0] * t_hat[0] + diff_XC[1] * t_hat[1]
    if abs(s) > 0.5 * L + 1e-7:
        return None
    
    return (t, X, t_hat, n_hat, C, L)


