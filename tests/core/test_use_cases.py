"""
Test ray tracing use cases with the polymorphic raytracing engine.
"""

import numpy as np

from optiverse.core.models import SourceParams
from optiverse.data import (
    BeamsplitterProperties,
    LensProperties,
    LineSegment,
    MirrorProperties,
    OpticalInterface,
)
from optiverse.integration import create_polymorphic_element
from optiverse.raytracing import trace_rays_polymorphic


def make_elem(kind: str, p1, p2, efl=None, T=None, R=None):
    """Create a polymorphic optical element."""
    p1_arr = np.array(p1, dtype=float)
    p2_arr = np.array(p2, dtype=float)
    geom = LineSegment(p1_arr, p2_arr)

    if kind == "mirror":
        props = MirrorProperties(reflectivity=1.0)
    elif kind == "lens":
        props = LensProperties(efl_mm=(efl if efl is not None else 100.0))
    elif kind == "bs":
        props = BeamsplitterProperties(
            transmission=(T if T is not None else 50.0) / 100.0,
            reflection=(R if R is not None else 50.0) / 100.0,
            is_polarizing=False,
            polarization_axis_deg=0.0,
        )
    else:
        raise ValueError(f"Unknown element kind: {kind}")

    iface = OpticalInterface(geometry=geom, properties=props)
    return create_polymorphic_element(iface)


def make_source(x, y, ang_deg=90.0, ray_length=100.0):
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
    elements = [make_elem("mirror", (-5.0, 0.0), (5.0, 0.0))]
    sources = [make_source(0.0, -10.0, ang_deg=90.0, ray_length=30.0)]
    paths = trace_rays_polymorphic(elements, sources, max_events=2)
    assert len(paths) >= 1
    # Expect hit at y=0, then reflection downward
    pts = paths[0].points
    assert len(pts) >= 3
    assert abs(pts[1][1]) < 1e-6  # intersection ~ y=0
    assert pts[2][1] < 0.0  # reflected below


def test_lens_zero_offset_no_deflection():
    # Lens centered at origin along x-axis; ray goes through center => no deflection
    elements = [make_elem("lens", (-5.0, 0.0), (5.0, 0.0), efl=100.0)]
    sources = [make_source(0.0, -10.0, ang_deg=90.0, ray_length=30.0)]
    paths = trace_rays_polymorphic(elements, sources, max_events=2)
    assert len(paths) >= 1
    pts = paths[0].points
    assert len(pts) >= 3
    # After lens, x should remain ~0 if no deflection
    assert abs(pts[-1][0]) < 1e-2


def test_beamsplitter_splits_into_two():
    elements = [make_elem("bs", (-5.0, 0.0), (5.0, 0.0), T=60.0, R=40.0)]
    sources = [make_source(0.0, -10.0, ang_deg=90.0, ray_length=30.0)]
    paths = trace_rays_polymorphic(elements, sources, max_events=2)
    # We expect at least 2 branches
    assert len(paths) >= 2
    # Sum of intensities approximately 1.0 (from alpha channel)
    total_I = sum(p.rgba[3] / 255.0 for p in paths)
    assert 0.95 <= total_I <= 1.05
