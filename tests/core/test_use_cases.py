import math
from typing import List

import numpy as np


def make_elem(kind: str, p1, p2, efl=None, T=None, R=None):
    from optiverse.core.models import OpticalElement

    return OpticalElement(
        kind=kind,
        p1=np.array(p1, dtype=float),
        p2=np.array(p2, dtype=float),
        efl_mm=(efl if efl is not None else 0.0),
        split_T=(T if T is not None else 50.0),
        split_R=(R if R is not None else 50.0),
    )


def make_source(x, y, ang_deg=90.0, ray_length=100.0):
    from optiverse.core.models import SourceParams

    return SourceParams(
        x_mm=float(x),
        y_mm=float(y),
        angle_deg=float(ang_deg),
        size_mm=0.0,
        n_rays=1,
        ray_length_mm=float(ray_length),
        spread_deg=0.0,
    )


def test_reflection_on_mirror():
    from optiverse.core.use_cases import trace_rays

    elements = [make_elem("mirror", (-5.0, 0.0), (5.0, 0.0))]
    sources = [make_source(0.0, -10.0, ang_deg=90.0, ray_length=30.0)]
    paths = trace_rays(elements, sources, max_events=2)
    assert len(paths) >= 1
    # Expect hit at y=0, then reflection downward
    pts = paths[0].points
    assert len(pts) >= 3
    assert abs(pts[1][1]) < 1e-6  # intersection ~ y=0
    assert pts[2][1] < 0.0        # reflected below


def test_lens_zero_offset_no_deflection():
    from optiverse.core.use_cases import trace_rays

    # Lens centered at origin along x-axis; ray goes through center => no deflection
    elements = [make_elem("lens", (-5.0, 0.0), (5.0, 0.0), efl=100.0)]
    sources = [make_source(0.0, -10.0, ang_deg=90.0, ray_length=30.0)]
    paths = trace_rays(elements, sources, max_events=2)
    assert len(paths) >= 1
    pts = paths[0].points
    assert len(pts) >= 3
    # After lens, x should remain ~0 if no deflection
    assert abs(pts[-1][0]) < 1e-2


def test_beamsplitter_splits_into_two():
    from optiverse.core.use_cases import trace_rays

    elements = [make_elem("bs", (-5.0, 0.0), (5.0, 0.0), T=60.0, R=40.0)]
    sources = [make_source(0.0, -10.0, ang_deg=90.0, ray_length=30.0)]
    paths = trace_rays(elements, sources, max_events=2)
    # We expect at least 2 branches
    assert len(paths) >= 2
    # Sum of intensities approximately 1.0
    total_I = sum(p.intensity for p in paths)
    assert 0.95 <= total_I <= 1.05




