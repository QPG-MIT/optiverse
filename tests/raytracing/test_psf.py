import numpy as np
import pytest

from optiverse.core.models import Polarization
from optiverse.raytracing import ImagePlane, RayPath, compute_geometric_psf


def _path(
    p0: tuple[float, float],
    p1: tuple[float, float],
    *,
    source_index: int = 0,
    intensities: list[float] | None = None,
) -> RayPath:
    return RayPath(
        points=[np.array(p0, dtype=float), np.array(p1, dtype=float)],
        rgba=(255, 0, 0, 255),
        polarization=Polarization.horizontal(),
        wavelength_nm=633.0,
        source_index=source_index,
        intensities=intensities or [1.0, 1.0],
    )


def test_geometric_psf_samples_image_plane_crossings():
    paths = [
        _path((0.0, -1.0), (10.0, -1.0)),
        _path((0.0, 0.0), (10.0, 0.0)),
        _path((0.0, 1.0), (10.0, 1.0)),
    ]

    psf = compute_geometric_psf(
        paths,
        ImagePlane.from_xy_angle(5.0, 0.0, 0.0),
        bin_count=3,
        extent_mm=1.5,
    )

    assert psf.sample_count == 3
    assert np.allclose(np.sort(psf.sample_positions_mm), [-1.0, 0.0, 1.0])
    assert psf.centroid_mm == pytest.approx(0.0)
    assert psf.rms_radius_mm == pytest.approx(np.sqrt(2.0 / 3.0))
    assert psf.total_weight == pytest.approx(3.0)
    assert np.sum(psf.intensity) == pytest.approx(1.0)


def test_geometric_psf_ignores_parallel_and_missing_segments():
    paths = [
        _path((0.0, 1.0), (10.0, 1.0)),
        _path((6.0, -1.0), (10.0, 1.0)),
        _path((0.0, -2.0), (4.0, -2.0)),
    ]

    psf = compute_geometric_psf(paths, ImagePlane.from_xy_angle(5.0, 0.0), bin_count=5)

    assert psf.sample_count == 1
    assert psf.sample_positions_mm[0] == pytest.approx(1.0)


def test_geometric_psf_uses_interpolated_intensity_weights():
    paths = [
        _path((0.0, -1.0), (10.0, -1.0), intensities=[1.0, 0.0]),
        _path((0.0, 1.0), (10.0, 1.0), intensities=[1.0, 1.0]),
    ]

    psf = compute_geometric_psf(
        paths,
        ImagePlane.from_xy_angle(5.0, 0.0),
        bin_count=2,
        extent_mm=1.5,
    )

    assert np.sort(psf.sample_weights).tolist() == pytest.approx([0.5, 1.0])
    assert psf.centroid_mm == pytest.approx(1.0 / 3.0)
    assert psf.total_weight == pytest.approx(1.5)


def test_geometric_psf_filters_by_source_index():
    paths = [
        _path((0.0, -3.0), (10.0, -3.0), source_index=0),
        _path((0.0, 2.0), (10.0, 2.0), source_index=1),
    ]

    psf = compute_geometric_psf(
        paths,
        ImagePlane.from_xy_angle(5.0, 0.0),
        source_index=1,
    )

    assert psf.sample_count == 1
    assert psf.sample_positions_mm[0] == pytest.approx(2.0)


def test_geometric_psf_reports_histogram_fwhm():
    paths = [
        _path((0.0, -1.0), (10.0, -1.0), intensities=[0.2, 0.2]),
        _path((0.0, 0.0), (10.0, 0.0), intensities=[1.0, 1.0]),
        _path((0.0, 1.0), (10.0, 1.0), intensities=[0.2, 0.2]),
    ]

    psf = compute_geometric_psf(
        paths,
        ImagePlane.from_xy_angle(5.0, 0.0),
        bin_count=3,
        extent_mm=1.5,
    )

    assert psf.fwhm_mm == pytest.approx(1.0)


def test_geometric_psf_returns_empty_result_without_crossings():
    psf = compute_geometric_psf(
        [_path((0.0, 0.0), (1.0, 0.0))],
        ImagePlane.from_xy_angle(5.0, 0.0),
        bin_count=7,
    )

    assert psf.sample_count == 0
    assert psf.centroid_mm is None
    assert psf.rms_radius_mm is None
    assert psf.fwhm_mm is None
    assert len(psf.intensity) == 7
    assert np.sum(psf.intensity) == 0.0


def test_geometric_psf_counts_zero_weight_crossings_without_metrics():
    psf = compute_geometric_psf(
        [_path((0.0, 0.0), (10.0, 0.0), intensities=[0.0, 0.0])],
        ImagePlane.from_xy_angle(5.0, 0.0),
    )

    assert psf.sample_count == 1
    assert psf.total_weight == 0.0
    assert psf.centroid_mm is None
    assert np.sum(psf.intensity) == 0.0


def test_geometric_psf_validates_inputs():
    plane = ImagePlane.from_xy_angle(5.0, 0.0)

    with pytest.raises(ValueError, match="bin_count"):
        compute_geometric_psf([], plane, bin_count=0)

    with pytest.raises(ValueError, match="normal"):
        compute_geometric_psf([], ImagePlane(np.array([0.0, 0.0]), np.array([0.0, 0.0])))
