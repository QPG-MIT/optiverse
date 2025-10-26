from __future__ import annotations

import math
from typing import Optional, Tuple

import numpy as np


def deg2rad(a: float) -> float:
    return a * math.pi / 180.0


def normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v if n == 0.0 else (v / n)


def reflect_vec(v: np.ndarray, n_hat: np.ndarray) -> np.ndarray:
    return v - 2.0 * float(np.dot(v, n_hat)) * n_hat


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


