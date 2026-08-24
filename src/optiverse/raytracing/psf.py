"""
Point-spread-function analysis for traced ray paths.

The Optiverse raytracer is 2D, so the geometric PSF is represented as a
one-dimensional intensity profile along an image-plane line.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np

from .ray import RayPath

_EPSILON = 1e-12


@dataclass
class ImagePlane:
    """A 2D image plane represented by a point and a normal vector."""

    point_mm: np.ndarray
    normal: np.ndarray

    @classmethod
    def from_xy_angle(
        cls, x_mm: float, y_mm: float, normal_angle_deg: float = 0.0
    ) -> ImagePlane:
        """Create an image plane from a point and a normal angle in degrees."""
        angle_rad = np.deg2rad(normal_angle_deg)
        normal = np.array([np.cos(angle_rad), np.sin(angle_rad)], dtype=float)
        return cls(point_mm=np.array([x_mm, y_mm], dtype=float), normal=normal)

    @property
    def normalized_normal(self) -> np.ndarray:
        """Return the plane normal as a unit vector."""
        return _normalized_vector(self.normal, "image-plane normal")

    @property
    def tangent(self) -> np.ndarray:
        """Return the positive coordinate direction along the image plane."""
        normal = self.normalized_normal
        return np.array([-normal[1], normal[0]], dtype=float)


@dataclass
class PointSpreadFunction:
    """Computed geometric PSF data and summary metrics."""

    plane: ImagePlane
    sample_positions_mm: np.ndarray
    sample_weights: np.ndarray
    bin_edges_mm: np.ndarray
    bin_centers_mm: np.ndarray
    intensity: np.ndarray
    centroid_mm: float | None
    rms_radius_mm: float | None
    fwhm_mm: float | None
    total_weight: float
    histogram_weight: float
    sample_count: int


def compute_geometric_psf(
    ray_paths: Sequence[RayPath],
    image_plane: ImagePlane,
    *,
    bin_count: int = 101,
    extent_mm: float | None = None,
    source_index: int | None = None,
    first_intersection_only: bool = True,
) -> PointSpreadFunction:
    """
    Compute a geometric PSF from ray crossings at an image plane.

    Args:
        ray_paths: Traced ray paths to sample.
        image_plane: Plane where the PSF is measured.
        bin_count: Number of histogram bins in the returned intensity profile.
        extent_mm: Optional half-width of the histogram about the plane origin.
        source_index: Optional source index filter.
        first_intersection_only: Count at most one crossing from each RayPath.

    Returns:
        PointSpreadFunction with sampled ray positions and normalized histogram.
    """
    if bin_count <= 0:
        raise ValueError("bin_count must be positive")
    if extent_mm is not None and extent_mm <= 0:
        raise ValueError("extent_mm must be positive")

    point = _as_point(image_plane.point_mm, "image-plane point")
    normal = image_plane.normalized_normal
    tangent = image_plane.tangent

    positions: list[float] = []
    weights: list[float] = []

    for path in ray_paths:
        if source_index is not None and path.source_index != source_index:
            continue

        for segment_index in range(max(0, len(path.points) - 1)):
            p0 = _as_point(path.points[segment_index], "ray path point")
            p1 = _as_point(path.points[segment_index + 1], "ray path point")
            crossing = _segment_plane_crossing(p0, p1, point, normal)
            if crossing is None:
                continue

            intersection, t = crossing
            positions.append(float(np.dot(intersection - point, tangent)))
            weights.append(_path_weight_at(path, segment_index, t))

            if first_intersection_only:
                break

    sample_positions = np.asarray(positions, dtype=float)
    sample_weights = np.asarray(weights, dtype=float)
    total_weight = float(np.sum(sample_weights)) if sample_weights.size else 0.0

    if sample_positions.size == 0 or total_weight <= 0:
        bin_edges = _empty_bin_edges(bin_count, extent_mm)
        bin_centers = _bin_centers(bin_edges)
        return PointSpreadFunction(
            plane=image_plane,
            sample_positions_mm=sample_positions,
            sample_weights=sample_weights,
            bin_edges_mm=bin_edges,
            bin_centers_mm=bin_centers,
            intensity=np.zeros(bin_count, dtype=float),
            centroid_mm=None,
            rms_radius_mm=None,
            fwhm_mm=None,
            total_weight=total_weight,
            histogram_weight=0.0,
            sample_count=int(sample_positions.size),
        )

    centroid = float(np.average(sample_positions, weights=sample_weights))
    variance = float(np.average((sample_positions - centroid) ** 2, weights=sample_weights))
    rms_radius = float(np.sqrt(max(variance, 0.0)))

    bin_edges = _histogram_edges(sample_positions, bin_count, extent_mm)
    histogram, _ = np.histogram(sample_positions, bins=bin_edges, weights=sample_weights)
    histogram_weight = float(np.sum(histogram))
    intensity = histogram / histogram_weight if histogram_weight > 0 else histogram
    bin_centers = _bin_centers(bin_edges)
    fwhm = _fwhm_from_histogram(bin_centers, bin_edges, intensity)

    return PointSpreadFunction(
        plane=image_plane,
        sample_positions_mm=sample_positions,
        sample_weights=sample_weights,
        bin_edges_mm=bin_edges,
        bin_centers_mm=bin_centers,
        intensity=intensity,
        centroid_mm=centroid,
        rms_radius_mm=rms_radius,
        fwhm_mm=fwhm,
        total_weight=total_weight,
        histogram_weight=histogram_weight,
        sample_count=int(sample_positions.size),
    )


def _as_point(value: np.ndarray | Sequence[float], label: str) -> np.ndarray:
    point = np.asarray(value, dtype=float)
    if point.ndim == 0 or point.shape[0] < 2:
        raise ValueError(f"{label} must have at least two coordinates")
    return point[:2]


def _normalized_vector(value: np.ndarray | Sequence[float], label: str) -> np.ndarray:
    vector = _as_point(value, label)
    norm = float(np.linalg.norm(vector))
    if norm <= _EPSILON:
        raise ValueError(f"{label} must be non-zero")
    return vector / norm


def _segment_plane_crossing(
    p0: np.ndarray, p1: np.ndarray, plane_point: np.ndarray, plane_normal: np.ndarray
) -> tuple[np.ndarray, float] | None:
    delta = p1 - p0
    denom = float(np.dot(delta, plane_normal))
    if abs(denom) <= _EPSILON:
        return None

    t = -float(np.dot(p0 - plane_point, plane_normal)) / denom
    if t < -_EPSILON or t > 1.0 + _EPSILON:
        return None

    t = min(1.0, max(0.0, t))
    return p0 + t * delta, t


def _path_weight_at(path: RayPath, segment_index: int, t: float) -> float:
    if len(path.intensities) >= len(path.points):
        i0 = float(path.intensities[segment_index])
        i1 = float(path.intensities[segment_index + 1])
        weight = i0 + t * (i1 - i0)
    elif len(path.intensities) > segment_index:
        weight = float(path.intensities[segment_index])
    else:
        weight = float(path.rgba[3]) / 255.0
    return max(weight, 0.0)


def _histogram_edges(
    sample_positions: np.ndarray, bin_count: int, extent_mm: float | None
) -> np.ndarray:
    if extent_mm is not None:
        return np.linspace(-extent_mm, extent_mm, bin_count + 1, dtype=float)

    lo = float(np.min(sample_positions))
    hi = float(np.max(sample_positions))
    if np.isclose(lo, hi):
        pad = max(0.5, abs(lo) * 0.05)
        lo -= pad
        hi += pad
    return np.linspace(lo, hi, bin_count + 1, dtype=float)


def _empty_bin_edges(bin_count: int, extent_mm: float | None) -> np.ndarray:
    extent = 1.0 if extent_mm is None else extent_mm
    return np.linspace(-extent, extent, bin_count + 1, dtype=float)


def _bin_centers(bin_edges: np.ndarray) -> np.ndarray:
    return cast(np.ndarray, (bin_edges[:-1] + bin_edges[1:]) / 2.0)


def _fwhm_from_histogram(
    bin_centers: np.ndarray, bin_edges: np.ndarray, intensity: np.ndarray
) -> float | None:
    if intensity.size == 0:
        return None

    peak = float(np.max(intensity))
    if peak <= 0:
        return None

    above = np.flatnonzero(intensity >= peak / 2.0)
    if above.size == 0:
        return None

    left = int(above[0])
    right = int(above[-1])
    if left == right:
        return float(bin_edges[left + 1] - bin_edges[left])
    return float(bin_centers[right] - bin_centers[left])
