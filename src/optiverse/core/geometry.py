from __future__ import annotations

import math
from typing import Optional, Tuple, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .models import Polarization


def deg2rad(a: float) -> float:
    return a * math.pi / 180.0


def normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v if n == 0.0 else (v / n)


def reflect_vec(v: np.ndarray, n_hat: np.ndarray) -> np.ndarray:
    return v - 2.0 * float(np.dot(v, n_hat)) * n_hat


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
    
    For PBS (Polarizing Beam Splitter):
    - p-polarization (parallel to transmission axis) is transmitted
    - s-polarization (perpendicular) is reflected
    
    For non-polarizing BS:
    - Both polarizations split according to T/R ratio
    
    Args:
        pol: Input polarization state
        v_in: Incident ray direction (normalized)
        n_hat: Surface normal (normalized)
        t_hat: Tangent direction along beamsplitter surface
        is_polarizing: True for PBS mode
        pbs_axis_deg: Transmission axis angle (for PBS)
        is_transmitted: True for transmitted ray, False for reflected
    
    Returns:
        Tuple of (transformed_polarization, intensity_factor)
    """
    from .models import Polarization
    
    if not is_polarizing:
        # Non-polarizing beamsplitter: preserve polarization
        if is_transmitted:
            return pol, 1.0
        else:
            # Apply mirror-like phase shift for reflection
            return transform_polarization_mirror(pol, v_in, n_hat), 1.0
    
    # PBS mode: separate polarizations
    # Define transmission axis in lab frame
    axis_rad = deg2rad(pbs_axis_deg)
    p_axis = np.array([np.cos(axis_rad), np.sin(axis_rad)])
    s_axis = np.array([-np.sin(axis_rad), np.cos(axis_rad)])
    
    # Decompose polarization
    jones = pol.jones_vector
    p_component = np.dot(jones, p_axis)
    s_component = np.dot(jones, s_axis)
    
    if is_transmitted:
        # Transmit p-polarization only
        jones_out = p_component * p_axis
        intensity = float(np.abs(p_component) ** 2)
    else:
        # Reflect s-polarization only (with phase shift)
        jones_out = -s_component * s_axis  # π phase shift
        intensity = float(np.abs(s_component) ** 2)
    
    # Normalize if non-zero
    if intensity > 1e-12:
        jones_out = jones_out / np.sqrt(intensity)
    else:
        jones_out = np.zeros(2, dtype=complex)
    
    return Polarization(jones_out), intensity


def ray_hit_element(
    P: np.ndarray,
    V: np.ndarray,
    A: np.ndarray,
    B: np.ndarray,
    tol: float = 1e-9,
):
    """Intersect ray (P + t V, t>0) with finite segment AB.

    Returns (t, X, t_hat, n_hat, C, L) or None if no hit.
    """
    t_hat = normalize(B - A)
    L = float(np.linalg.norm(B - A))
    if L < tol:
        return None
    n_hat = np.array([-t_hat[1], t_hat[0]])
    C = 0.5 * (A + B)
    denom = float(np.dot(V, n_hat))
    if abs(denom) < tol:
        return None
    t = float(np.dot(C - P, n_hat)) / denom
    if t <= tol:
        return None
    X = P + t * V
    s = float(np.dot(X - C, t_hat))
    if abs(s) > 0.5 * L + 1e-7:
        return None
    return t, X, t_hat, n_hat, C, L


