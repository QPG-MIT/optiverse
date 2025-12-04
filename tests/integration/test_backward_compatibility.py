"""
Tests for polymorphic raytracing engine behavior.

These tests verify that the polymorphic engine handles various scenarios correctly.
"""

import numpy as np
import pytest

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


class TestPolymorphicEngineBasics:
    """Test basic polymorphic engine functionality."""

    def test_empty_scene(self):
        """Test that engine handles empty scenes correctly."""
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=3,
            size_mm=10.0,
            ray_length_mm=100.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([], [source], max_events=10)

        # Should produce 3 paths (3 rays)
        assert len(paths) == 3

        # All paths should escape (2 points: start and end)
        for path in paths:
            assert len(path.points) == 2

    def test_single_mirror(self):
        """Test that engine handles a single mirror correctly."""
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=1.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror = create_polymorphic_element(iface)

        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=1,
            size_mm=0.0,
            ray_length_mm=200.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([mirror], [source], max_events=10)

        # Should produce 1 path
        assert len(paths) == 1

        # Path should have at least 3 points (start, hit, reflected)
        path = paths[0]
        assert len(path.points) >= 3

        # First point should be source position
        assert np.allclose(path.points[0], [0.0, 0.0], atol=1e-6)

    def test_single_lens(self):
        """Test that engine handles a single lens correctly."""
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = LensProperties(efl_mm=100.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        lens = create_polymorphic_element(iface)

        # Create source (off-axis)
        source = SourceParams(
            x_mm=0.0,
            y_mm=10.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=1,
            size_mm=0.0,
            ray_length_mm=200.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([lens], [source], max_events=10)

        # Should produce 1 path
        assert len(paths) == 1

        # Path should have points
        path = paths[0]
        assert len(path.points) >= 2

    def test_beamsplitter_splits(self):
        """Test that beamsplitter creates two output rays."""
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = BeamsplitterProperties(
            transmission=0.7, reflection=0.3, is_polarizing=False, polarization_axis_deg=0.0
        )
        iface = OpticalInterface(geometry=geom, properties=props)
        bs = create_polymorphic_element(iface)

        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=1,
            size_mm=0.0,
            ray_length_mm=200.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([bs], [source], max_events=10)

        # Should produce 2 paths (transmitted + reflected)
        assert len(paths) == 2

    def test_multiple_rays(self):
        """Test that engine handles multiple rays correctly."""
        geom = LineSegment(np.array([50.0, -30.0]), np.array([50.0, 30.0]))
        props = MirrorProperties(reflectivity=1.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror = create_polymorphic_element(iface)

        # Create source with 5 rays
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=5,
            size_mm=20.0,
            ray_length_mm=200.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([mirror], [source], max_events=10)

        # Should produce 5 paths
        assert len(paths) == 5

    def test_complex_scene(self):
        """Test engine with multiple elements."""
        # Create lens
        lens_geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        lens_props = LensProperties(efl_mm=100.0)
        lens_iface = OpticalInterface(geometry=lens_geom, properties=lens_props)
        lens = create_polymorphic_element(lens_iface)

        # Create mirror
        mirror_geom = LineSegment(np.array([150.0, -20.0]), np.array([150.0, 20.0]))
        mirror_props = MirrorProperties(reflectivity=1.0)
        mirror_iface = OpticalInterface(geometry=mirror_geom, properties=mirror_props)
        mirror = create_polymorphic_element(mirror_iface)

        # Create source
        source = SourceParams(
            x_mm=0.0,
            y_mm=5.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=3,
            size_mm=10.0,
            ray_length_mm=300.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([lens, mirror], [source], max_events=20)

        # Should produce 3 paths
        assert len(paths) == 3

    def test_output_format(self):
        """Test that output RayPath has correct attributes."""
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=1.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror = create_polymorphic_element(iface)

        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=1,
            size_mm=0.0,
            ray_length_mm=200.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([mirror], [source], max_events=10)

        path = paths[0]

        # Verify RayPath structure
        assert hasattr(path, "points")
        assert hasattr(path, "rgba")
        assert hasattr(path, "polarization")
        assert hasattr(path, "wavelength_nm")

        # RGBA format should be correct
        assert len(path.rgba) == 4

        # Wavelength should match
        assert path.wavelength_nm == 633.0


class TestRegressionPrevention:
    """Tests that prevent regression by verifying specific known behaviors."""

    def test_ray_escaping_behavior(self):
        """Test that rays escape properly when no elements are hit."""
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=1,
            size_mm=0.0,
            ray_length_mm=100.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([], [source], max_events=10)

        # Should produce 1 path with 2 points (start and end)
        assert len(paths) == 1
        assert len(paths[0].points) == 2

        # End point should be ray_length_mm away
        start = paths[0].points[0]
        end = paths[0].points[1]
        distance = np.linalg.norm(end - start)
        assert distance == pytest.approx(100.0, rel=1e-6)

    def test_intensity_preservation(self):
        """Test that ray intensity is properly tracked."""
        # Create low-reflectivity mirror
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=0.5)  # 50% reflectivity
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror = create_polymorphic_element(iface)

        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=1,
            size_mm=0.0,
            ray_length_mm=200.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([mirror], [source], max_events=10)

        # Should get at least 1 path
        assert len(paths) >= 1

        # Alpha should reflect intensity
        for path in paths:
            r, g, b, a = path.rgba
            assert 0 <= a <= 255

    def test_max_events_termination(self):
        """Test that rays terminate after max_events interactions."""
        # Create two mirrors facing each other
        mirror1_geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        mirror1_props = MirrorProperties(reflectivity=1.0)
        mirror1_iface = OpticalInterface(geometry=mirror1_geom, properties=mirror1_props)
        mirror1 = create_polymorphic_element(mirror1_iface)

        mirror2_geom = LineSegment(np.array([100.0, -20.0]), np.array([100.0, 20.0]))
        mirror2_props = MirrorProperties(reflectivity=1.0)
        mirror2_iface = OpticalInterface(geometry=mirror2_geom, properties=mirror2_props)
        mirror2 = create_polymorphic_element(mirror2_iface)

        # Create source between mirrors
        source = SourceParams(
            x_mm=75.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=1,
            size_mm=0.0,
            ray_length_mm=1000.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        # Trace with low max_events
        paths = trace_rays_polymorphic([mirror1, mirror2], [source], max_events=5)

        # Should terminate after 5 events
        assert len(paths) >= 1


class TestParallelProcessing:
    """Test parallel processing functionality."""

    def test_parallel_produces_same_results(self):
        """Test that parallel processing produces same results as sequential."""
        geom = LineSegment(np.array([50.0, -30.0]), np.array([50.0, 30.0]))
        props = MirrorProperties(reflectivity=1.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror = create_polymorphic_element(iface)

        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=50,
            size_mm=20.0,
            ray_length_mm=200.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        # Sequential
        paths_seq = trace_rays_polymorphic(
            [mirror], [source], max_events=10, parallel=False
        )

        # Parallel (if available)
        paths_par = trace_rays_polymorphic(
            [mirror], [source], max_events=10, parallel=True, parallel_threshold=10
        )

        # Should produce same number of paths
        assert len(paths_seq) == len(paths_par)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
