from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np

from .geometry import (
    deg2rad, normalize, reflect_vec, ray_hit_element,
    transform_polarization_mirror, transform_polarization_lens,
    transform_polarization_beamsplitter, transform_polarization_waveplate,
    compute_dichroic_reflectance
)
from .models import OpticalElement, SourceParams, RayPath, Polarization
from .color_utils import qcolor_from_hex, wavelength_to_rgb


def _endpoints(elements: List[OpticalElement]):
    return [(e, e.p1, e.p2) for e in elements]


def trace_rays(
    elements: List[OpticalElement],
    sources: List[SourceParams],
    max_events: int = 80,
) -> List[RayPath]:
    paths: List[RayPath] = []
    mirrors = [(e, e.p1, e.p2) for e in elements if e.kind == "mirror"]
    lenses = [(e, e.p1, e.p2) for e in elements if e.kind == "lens"]
    bss = [(e, e.p1, e.p2) for e in elements if e.kind == "bs"]
    waveplates = [(e, e.p1, e.p2) for e in elements if e.kind == "waveplate"]
    dichroics = [(e, e.p1, e.p2) for e in elements if e.kind == "dichroic"]

    EPS_ADV = 1e-3
    MIN_I = 0.02

    for S in sources:
        base = deg2rad(S.angle_deg)
        spread = deg2rad(S.spread_deg)
        
        # Determine wavelength and color
        # Wavelength is used for physics calculations (dichroics, etc.)
        # Color is always used for visualization (independent of wavelength)
        source_wavelength = S.wavelength_nm if S.wavelength_nm > 0 else 0.0
        
        # Always use color_hex for visualization
        src_col = qcolor_from_hex(S.color_hex)
        base_rgb = (src_col.red(), src_col.green(), src_col.blue())

        ys = [0.0] if (S.n_rays <= 1 or S.size_mm == 0) else list(np.linspace(-S.size_mm/2, S.size_mm/2, S.n_rays))
        if spread == 0 or S.n_rays <= 1:
            angles = [base] * len(ys)
        else:
            fan = np.linspace(-spread, +spread, len(ys))
            angles = [base + a for a in fan]

        # Get initial polarization for this source
        initial_pol = S.get_polarization()
        
        for i, y0 in enumerate(ys):
            P = np.array([S.x_mm, S.y_mm + y0], float)
            th = angles[i]
            V = np.array([math.cos(th), math.sin(th)], float)

            # Stack now includes polarization and wavelength: (points, position, velocity, remaining, last_obj, events, intensity, polarization, wavelength)
            stack: List[Tuple[List[np.ndarray], np.ndarray, np.ndarray, float, object, int, float, Polarization, float]] = []
            stack.append(([P.copy()], P.copy(), V.copy(), S.ray_length_mm, None, 0, 1.0, initial_pol, source_wavelength))

            while stack:
                pts, P, V, remaining, last_obj, events, I, pol, wl = stack.pop()
                if remaining <= 0 or events >= max_events or I < MIN_I:
                    if len(pts) >= 2:
                        a = int(255 * max(0.0, min(1.0, I)))
                        paths.append(RayPath(pts, (base_rgb[0], base_rgb[1], base_rgb[2], a), pol, wl))
                    continue

                nearest = (None, None, None, None, None, None, None, None)  # t,X,kind,obj,t_hat,n_hat,C,L
                vnorm = float(np.linalg.norm(V))

                for obj, A, B in mirrors:
                    if last_obj is obj:
                        continue
                    res = ray_hit_element(P, V, A, B)
                    if res is None:
                        continue
                    t, X, t_hat, n_hat, C, L = res
                    if t * vnorm > remaining:
                        continue
                    if nearest[0] is None or t < nearest[0]:
                        nearest = (t, X, "mirror", obj, t_hat, n_hat, C, L)

                for obj, A, B in lenses:
                    if last_obj is obj:
                        continue
                    res = ray_hit_element(P, V, A, B)
                    if res is None:
                        continue
                    t, X, t_hat, n_hat, C, L = res
                    if t * vnorm > remaining:
                        continue
                    if nearest[0] is None or t < nearest[0]:
                        nearest = (t, X, "lens", obj, t_hat, n_hat, C, L)

                for obj, A, B in bss:
                    if last_obj is obj:
                        continue
                    res = ray_hit_element(P, V, A, B)
                    if res is None:
                        continue
                    t, X, t_hat, n_hat, C, L = res
                    if t * vnorm > remaining:
                        continue
                    if nearest[0] is None or t < nearest[0]:
                        nearest = (t, X, "bs", obj, t_hat, n_hat, C, L)

                for obj, A, B in waveplates:
                    if last_obj is obj:
                        continue
                    res = ray_hit_element(P, V, A, B)
                    if res is None:
                        continue
                    t, X, t_hat, n_hat, C, L = res
                    if t * vnorm > remaining:
                        continue
                    if nearest[0] is None or t < nearest[0]:
                        nearest = (t, X, "waveplate", obj, t_hat, n_hat, C, L)

                for obj, A, B in dichroics:
                    if last_obj is obj:
                        continue
                    res = ray_hit_element(P, V, A, B)
                    if res is None:
                        continue
                    t, X, t_hat, n_hat, C, L = res
                    if t * vnorm > remaining:
                        continue
                    if nearest[0] is None or t < nearest[0]:
                        nearest = (t, X, "dichroic", obj, t_hat, n_hat, C, L)

                t, X, kind, obj, t_hat, n_hat, C, L = nearest
                if X is None:
                    P2 = P + V * (remaining / max(1e-12, vnorm))
                    pts2 = pts + [P2.copy()]
                    a = int(255 * max(0.0, min(1.0, I)))
                    paths.append(RayPath(pts2, (base_rgb[0], base_rgb[1], base_rgb[2], a), pol, wl))
                    continue

                step = float(t) * vnorm
                P = X
                pts = pts + [P.copy()]
                remaining -= step

                if float(np.dot(V, n_hat)) < 0:
                    n_hat = -n_hat
                    t_hat = -t_hat

                if kind == "mirror":
                    V2 = normalize(reflect_vec(V, n_hat))
                    P2 = P + V2 * EPS_ADV
                    # Transform polarization upon reflection
                    pol2 = transform_polarization_mirror(pol, V, n_hat)
                    stack.append((pts + [P2.copy()], P2.copy(), V2, remaining - EPS_ADV, obj, events + 1, I, pol2, wl))
                    continue

                if kind == "lens":
                    y = float(np.dot(P - C, t_hat))
                    a_n = float(np.dot(V, n_hat))
                    a_t = float(np.dot(V, t_hat))
                    theta_in = math.atan2(a_t, a_n)
                    f = float(obj.efl_mm)
                    theta_out = theta_in - (y / f) if abs(f) > 1e-12 else theta_in
                    Vloc = np.array([math.cos(theta_out), math.sin(theta_out)])
                    V2 = normalize(Vloc[0] * n_hat + Vloc[1] * t_hat)
                    P2 = P + V2 * EPS_ADV
                    # Transform polarization through lens (preserved for ideal lens)
                    pol2 = transform_polarization_lens(pol)
                    stack.append((pts + [P2.copy()], P2.copy(), V2, remaining - EPS_ADV, obj, events + 1, I, pol2, wl))
                    continue

                if kind == "bs":
                    # Get polarization properties
                    is_polarizing = getattr(obj, 'is_polarizing', False)
                    pbs_axis_deg = getattr(obj, 'pbs_transmission_axis_deg', 0.0)
                    
                    # Transform polarization for transmitted ray
                    pol_t, intensity_factor_t = transform_polarization_beamsplitter(
                        pol, V, n_hat, t_hat, is_polarizing, pbs_axis_deg, is_transmitted=True
                    )
                    
                    # Transform polarization for reflected ray
                    pol_r, intensity_factor_r = transform_polarization_beamsplitter(
                        pol, V, n_hat, t_hat, is_polarizing, pbs_axis_deg, is_transmitted=False
                    )
                    
                    if is_polarizing:
                        # PBS mode: intensity modulated by polarization
                        T = intensity_factor_t
                        R = intensity_factor_r
                    else:
                        # Non-polarizing mode: use split ratios
                        T = max(0.0, min(1.0, float(obj.split_T) / 100.0))
                        R = max(0.0, min(1.0, float(obj.split_R) / 100.0))

                    Vt = normalize(V)
                    Pt = P + Vt * EPS_ADV
                    It = I * T
                    if It >= MIN_I:
                        stack.append((pts + [Pt.copy()], Pt.copy(), Vt, remaining - EPS_ADV, obj, events + 1, It, pol_t, wl))

                    Vr = normalize(reflect_vec(V, n_hat))
                    Pr = P + Vr * EPS_ADV
                    Ir = I * R
                    if Ir >= MIN_I:
                        stack.append((pts + [Pr.copy()], Pr.copy(), Vr, remaining - EPS_ADV, obj, events + 1, Ir, pol_r, wl))
                    continue

                if kind == "waveplate":
                    # Get waveplate properties
                    phase_shift_deg = getattr(obj, 'phase_shift_deg', 90.0)
                    fast_axis_deg = getattr(obj, 'fast_axis_deg', 0.0)
                    
                    # Transform polarization through waveplate
                    pol2 = transform_polarization_waveplate(pol, phase_shift_deg, fast_axis_deg)
                    
                    # Ray continues straight through (no refraction or reflection)
                    V2 = normalize(V)
                    P2 = P + V2 * EPS_ADV
                    stack.append((pts + [P2.copy()], P2.copy(), V2, remaining - EPS_ADV, obj, events + 1, I, pol2, wl))
                    continue
                
                if kind == "dichroic":
                    # Get dichroic properties
                    cutoff_wl = getattr(obj, 'cutoff_wavelength_nm', 550.0)
                    transition_width = getattr(obj, 'transition_width_nm', 50.0)
                    pass_type = getattr(obj, 'pass_type', 'longpass')
                    
                    # Compute wavelength-dependent reflectance and transmittance
                    # If wavelength not specified (wl == 0), assume 50/50 split
                    if wl > 0:
                        R, T = compute_dichroic_reflectance(wl, cutoff_wl, transition_width, pass_type)
                    else:
                        # No wavelength specified, treat as 50/50 beamsplitter
                        R, T = 0.5, 0.5
                    
                    # Transmitted ray (straight through)
                    Vt = normalize(V)
                    Pt = P + Vt * EPS_ADV
                    It = I * T
                    if It >= MIN_I:
                        # Polarization preserved for ideal dichroic (no birefringence)
                        stack.append((pts + [Pt.copy()], Pt.copy(), Vt, remaining - EPS_ADV, obj, events + 1, It, pol, wl))
                    
                    # Reflected ray
                    Vr = normalize(reflect_vec(V, n_hat))
                    Pr = P + Vr * EPS_ADV
                    Ir = I * R
                    if Ir >= MIN_I:
                        # Transform polarization upon reflection (like a mirror)
                        pol_r = transform_polarization_mirror(pol, V, n_hat)
                        stack.append((pts + [Pr.copy()], Pr.copy(), Vr, remaining - EPS_ADV, obj, events + 1, Ir, pol_r, wl))
                    continue

    return paths


