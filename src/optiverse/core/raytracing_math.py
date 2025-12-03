from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

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
    logging.warning(
        "numba not available. Raytracing will be slower. Install with: pip install numba"
    )

if TYPE_CHECKING:
    from .models import Polarization


@jit(nopython=True, cache=True)
def deg2rad(a: float) -> float:
    """Convert degrees to radians. JIT-compiled for performance when numba is available."""
    return a * math.pi / 180.0


@jit(nopython=True, cache=True)
def normalize(v: np.ndarray) -> np.ndarray:
    """Normalize a vector. JIT-compiled for performance when numba is available."""
    n = math.sqrt(v[0] ** 2 + v[1] ** 2)
    if n == 0.0:
        zero_vec: np.ndarray = v.copy()
        return zero_vec
    else:
        normalized_vec: np.ndarray = v / n
        return normalized_vec


def user_angle_to_qt(user_deg: float) -> float:
    """
    Convert user angle (CW from right) to Qt angle (CCW from right).

    User convention (clockwise):
    - 0° = right (→)
    - 90° = down (↓)
    - 180° = left (←)
    - 270° = up (↑)

    Qt convention (counter-clockwise):
    - 0° = right (→)
    - 90° = up (↑)
    - 180° = left (←)
    - 270° = down (↓)
    """
    return -user_deg


def qt_angle_to_user(qt_deg: float) -> float:
    """
    Convert Qt angle (CCW from right) to user angle (CW from right).

    Returns angle normalized to 0-360 range.
    """
    angle = -qt_deg
    # Normalize to 0-360
    angle = angle % 360
    if angle < 0:
        angle += 360
    return angle


@jit(nopython=True, cache=True)
def reflect_vec(v: np.ndarray, n_hat: np.ndarray) -> np.ndarray:
    """
    Reflect vector v across normal n_hat.

    JIT-compiled for performance when numba is available.
    """
    dot_product = v[0] * n_hat[0] + v[1] * n_hat[1]
    return v - 2.0 * dot_product * n_hat  # type: ignore[no-any-return]


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


def transform_polarization_mirror(
    pol: Polarization, v_in: np.ndarray, n_hat: np.ndarray
) -> Polarization:
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


def transform_polarization_lens(pol: Polarization) -> Polarization:
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
    pol: Polarization, phase_shift_deg: float, fast_axis_deg: float, is_forward: bool = True
) -> Polarization:
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

    Directionality:
    --------------
    The direction of light propagation through the waveplate matters!
    - Forward direction (with element normal): phase shift = +δ
    - Backward direction (against element normal): phase shift = -δ

    This is critical for quarter waveplates:
    - QWP forward (+90°): H → Right Circular
    - QWP backward (-90°): H → Left Circular

    For half waveplates, direction doesn't matter since exp(i·180°) = exp(-i·180°) = -1

    Jones Matrix Formalism:
    ----------------------
    The Jones matrix for a waveplate with fast axis at angle θ and phase shift δ:

    J = R(-θ) · [[1, 0], [0, exp(iδ)]] · R(θ)

    Where:
    - R(θ) is the rotation matrix
    - exp(iδ) represents the phase shift on the slow axis
    - Fast axis component has no phase shift (factor of 1)
    - δ is negated if light travels backward through the waveplate

    Args:
        pol: Input polarization state (Jones vector)
        phase_shift_deg: Phase shift in degrees (90° for QWP, 180° for HWP)
        fast_axis_deg: ABSOLUTE angle of fast axis in lab frame (degrees)
                       0° = horizontal, 90° = vertical
        is_forward: True if light travels in forward direction (with normal),
                   False if backward (against normal). Default: True

    Returns:
        Transformed polarization state

    Example:
        # Convert horizontal to right circular with QWP at 45° (forward)
        pol_in = Polarization.horizontal()  # [1, 0]
        pol_out = transform_polarization_waveplate(
            pol_in,
            phase_shift_deg=90.0,  # Quarter wave
            fast_axis_deg=45.0,    # 45° fast axis
            is_forward=True        # Forward direction
        )
        # Result: right circular [1/√2, i/√2]

        # Same waveplate, backward direction gives left circular
        pol_out_back = transform_polarization_waveplate(
            pol_in,
            phase_shift_deg=90.0,
            fast_axis_deg=45.0,
            is_forward=False       # Backward direction
        )
        # Result: left circular [1/√2, -i/√2]
    """
    from .models import Polarization

    # Convert angles to radians
    theta = deg2rad(fast_axis_deg)
    delta = deg2rad(phase_shift_deg)

    # Apply directionality: backward direction reverses phase shift
    if not is_forward:
        delta = -delta

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
    pol: Polarization,
    v_in: np.ndarray,
    n_hat: np.ndarray,
    t_hat: np.ndarray,
    is_polarizing: bool,
    pbs_axis_deg: float,
    is_transmitted: bool,
) -> tuple[Polarization, float]:
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
    p_axis = np.array([np.cos(axis_rad), np.sin(axis_rad)])  # Transmission direction
    s_axis = np.array([-np.sin(axis_rad), np.cos(axis_rad)])  # Reflection direction (perpendicular)

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
    pass_type: str = "longpass",
) -> tuple[float, float]:
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


def refract_vector_snell(
    v_in: np.ndarray, n_hat: np.ndarray, n1: float, n2: float
) -> tuple[np.ndarray | None, bool]:
    """
    Apply Snell's law to refract a ray at an interface.

    Args:
        v_in: Incident ray direction (normalized)
        n_hat: Surface normal pointing from medium 1 to medium 2 (normalized)
        n1: Refractive index of incident medium
        n2: Refractive index of transmitted medium

    Returns:
        Tuple of (refracted_direction, is_total_reflection)
        - refracted_direction: Refracted ray direction (normalized),
          or None if total internal reflection
        - is_total_reflection: True if total internal reflection occurs

    Physics:
    - Snell's law: n1 * sin(θ1) = n2 * sin(θ2)
    - Total internal reflection occurs when n1 > n2 and θ1 > critical angle
    - Critical angle: θc = arcsin(n2 / n1)
    """
    # Normalize inputs
    v_in = normalize(v_in)
    n_hat = normalize(n_hat)

    # Compute incident angle (cos θ1)
    cos_theta1 = -np.dot(v_in, n_hat)

    # Handle ray coming from the "wrong" side (flip normal)
    if cos_theta1 < 0:
        n_hat = -n_hat
        cos_theta1 = -cos_theta1

    # Compute refractive index ratio
    eta = n1 / n2

    # Check for total internal reflection
    # sin²(θ2) = (n1/n2)² * sin²(θ1) = eta² * (1 - cos²(θ1))
    sin2_theta2 = eta * eta * (1.0 - cos_theta1 * cos_theta1)

    if sin2_theta2 > 1.0:
        # Total internal reflection
        # Reflect the ray
        v_reflected = reflect_vec(v_in, n_hat)
        return v_reflected, True

    # Compute refracted direction using vector form of Snell's law
    cos_theta2 = np.sqrt(1.0 - sin2_theta2)
    v_refracted = eta * v_in + (eta * cos_theta1 - cos_theta2) * n_hat
    v_refracted = normalize(v_refracted)

    return v_refracted, False


def fresnel_coefficients(theta1_rad: float, n1: float, n2: float) -> tuple[float, float]:
    """
    Compute Fresnel reflection and transmission coefficients for unpolarized light.

    Args:
        theta1_rad: Incident angle in radians (angle between ray and normal)
        n1: Refractive index of incident medium
        n2: Refractive index of transmitted medium

    Returns:
        Tuple of (R, T) where:
        - R: Reflectance (fraction of intensity reflected, 0-1)
        - T: Transmittance (fraction of intensity transmitted, 0-1)

    Physics:
    - Fresnel equations for unpolarized light (average of s and p polarizations)
    - At normal incidence: R = ((n1-n2)/(n1+n2))²
    - At grazing angles: R → 1 (Brewster angle effects)
    - Energy conservation: R + T = 1
    """
    import math

    # Compute incident angle
    cos_theta1 = math.cos(theta1_rad)
    sin_theta1 = math.sin(theta1_rad)

    # Check for total internal reflection
    eta = n1 / n2
    sin2_theta2 = eta * eta * sin_theta1 * sin_theta1

    if sin2_theta2 > 1.0:
        # Total internal reflection
        return 1.0, 0.0

    cos_theta2 = math.sqrt(1.0 - sin2_theta2)

    # Fresnel equations for s and p polarizations
    # s-polarization (perpendicular to plane of incidence)
    rs_num = n1 * cos_theta1 - n2 * cos_theta2
    rs_den = n1 * cos_theta1 + n2 * cos_theta2
    rs = rs_num / rs_den if abs(rs_den) > 1e-12 else 0.0

    # p-polarization (parallel to plane of incidence)
    rp_num = n2 * cos_theta1 - n1 * cos_theta2
    rp_den = n2 * cos_theta1 + n1 * cos_theta2
    rp = rp_num / rp_den if abs(rp_den) > 1e-12 else 0.0

    # Average reflectance for unpolarized light
    R = 0.5 * (rs * rs + rp * rp)
    T = 1.0 - R

    # Clamp to [0, 1]
    R = max(0.0, min(1.0, R))
    T = max(0.0, min(1.0, T))

    return R, T


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
    # NOTE: Direction is B->A (reversed) to flip normal 180° for correct n1/n2 sides
    diff = A - B
    L = math.sqrt(diff[0] ** 2 + diff[1] ** 2)
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


def ray_hit_curved_element(
    P: np.ndarray,
    V: np.ndarray,
    center: np.ndarray,
    radius: float,
    p1: np.ndarray,
    p2: np.ndarray,
    tol: float = 1e-9,
):
    """
    Intersect ray (P + t V, t>0) with a curved segment (circular arc).

    Args:
        P: Ray start point [x, y]
        V: Ray direction [x, y] (should be normalized)
        center: Center of the circle [x, y]
        radius: Radius of the circle (absolute value)
        p1, p2: Endpoints of the arc
        tol: Tolerance for numerical comparisons

    Returns:
        Tuple of (t, X, t_hat, n_hat, C, L) or None if no hit
        - t: Parameter along ray
        - X: Intersection point
        - t_hat: Tangent at intersection
        - n_hat: Normal at intersection (pointing outward from center)
        - C: Center of arc (same as input center)
        - L: Arc length
    """
    # Ray-circle intersection
    # Ray: R(t) = P + t*V
    # Circle: |R - center|² = radius²

    # Substitute ray equation into circle equation:
    # |P + t*V - center|² = radius²
    # Let PC = P - center
    # |PC + t*V|² = radius²
    # PC·PC + 2t(PC·V) + t²(V·V) = radius²
    # (V·V)t² + 2(PC·V)t + (PC·PC - radius²) = 0

    PC = P - center
    a = np.dot(V, V)
    b = 2.0 * np.dot(V, PC)
    c = np.dot(PC, PC) - radius**2

    discriminant = b**2 - 4 * a * c

    if discriminant < 0:
        return None  # No intersection with circle

    sqrt_disc = math.sqrt(discriminant)
    t1 = (-b - sqrt_disc) / (2 * a)
    t2 = (-b + sqrt_disc) / (2 * a)

    # Try both intersection points (ray might hit circle twice)
    for t in [t1, t2]:
        if t <= tol:
            continue  # Behind ray start

        # Calculate intersection point
        X = P + t * V

        # Check if this point is within the arc bounds
        # The arc is defined by the angular range between p1 and p2
        if not _point_on_arc_bounds(X, center, p1, p2, tol):
            continue

        # Calculate normal at this point (radial direction, outward)
        radial = X - center
        n_hat = radial / radius

        # Calculate tangent (perpendicular to normal)
        # Rotate normal 90° counterclockwise: (x, y) -> (-y, x)
        t_hat = np.array([-n_hat[1], n_hat[0]])

        # Calculate arc length (approximate)
        v1 = p1 - center
        v2 = p2 - center
        cos_angle = np.dot(v1, v2) / (radius * radius)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        arc_angle = math.acos(cos_angle)
        L = radius * arc_angle

        return (t, X, t_hat, n_hat, center, L)

    return None  # No valid intersection within arc bounds


def _point_on_arc_bounds(
    point: np.ndarray,
    center: np.ndarray,
    p1: np.ndarray,
    p2: np.ndarray,
    tol: float = 1e-6,
) -> bool:
    """
    Check if a point on a circle lies within the arc defined by p1 and p2.

    Args:
        point: Point to check (assumed to be on the circle)
        center: Center of the circle
        p1, p2: Endpoints defining the arc
        tol: Angular tolerance in radians

    Returns:
        True if point is within the arc bounds
    """
    # Calculate angles from center
    v1 = p1 - center
    v2 = p2 - center
    v_point = point - center

    angle1 = math.atan2(v1[1], v1[0])
    angle2 = math.atan2(v2[1], v2[0])
    angle_point = math.atan2(v_point[1], v_point[0])

    # Normalize to [0, 2π]
    def normalize_angle(a):
        while a < 0:
            a += 2 * math.pi
        while a >= 2 * math.pi:
            a -= 2 * math.pi
        return a

    angle1 = normalize_angle(angle1)
    angle2 = normalize_angle(angle2)
    angle_point = normalize_angle(angle_point)

    # Calculate angular span
    # Handle wraparound case
    if angle2 >= angle1:
        span = angle2 - angle1
        in_bounds = angle1 - tol <= angle_point <= angle2 + tol
    else:
        # Arc wraps around 0
        span = (2 * math.pi - angle1) + angle2
        in_bounds = (angle_point >= angle1 - tol) or (angle_point <= angle2 + tol)

    # Also check that the arc isn't too large (> π means we should use the other arc)
    if span > math.pi:
        # Use the complement arc
        return not in_bounds  # type: ignore[no-any-return]

    return in_bounds  # type: ignore[no-any-return]


def calculate_path_length(points: list[np.ndarray]) -> float:
    """
    Calculate cumulative optical path length along a sequence of points.

    This computes the total distance traveled by summing Euclidean distances
    between consecutive points. Used for measuring ray paths including
    reflections, refractions, and beam splitter paths.

    Args:
        points: List of [x, y] position arrays in mm

    Returns:
        Total path length in mm

    Example:
        >>> points = [np.array([0, 0]), np.array([10, 0]), np.array([10, 10])]
        >>> calculate_path_length(points)
        20.0
    """
    if len(points) < 2:
        return 0.0

    total_length = 0.0
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        total_length += math.sqrt(dx * dx + dy * dy)

    return total_length
