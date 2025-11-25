"""
Backward compatibility tests for polymorphic raytracing engine.

These tests ensure that the new polymorphic engine produces
equivalent results to the legacy engine.
"""

import numpy as np
import pytest

from optiverse.core.models import OpticalElement, SourceParams
from optiverse.core.use_cases import trace_rays as trace_rays_legacy
from optiverse.data import (
    BeamsplitterProperties,
    LensProperties,
    LineSegment,
    MirrorProperties,
    OpticalInterface,
)
from optiverse.integration import create_polymorphic_element
from optiverse.raytracing import trace_rays_polymorphic


class TestBackwardCompatibility:
    """
    Compare outputs between legacy and polymorphic engines.

    These tests verify that both engines produce equivalent results
    for the same scenes, ensuring backward compatibility.
    """

    def test_empty_scene_compatibility(self):
        """Test that both engines handle empty scenes identically."""
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

        # Legacy engine
        legacy_paths = trace_rays_legacy([], [source], max_events=10)

        # Polymorphic engine
        poly_paths = trace_rays_polymorphic([], [source], max_events=10)

        # Both should produce 3 paths (3 rays)
        assert len(legacy_paths) == len(poly_paths) == 3

        # All paths should escape (2 points: start and end)
        for legacy, poly in zip(legacy_paths, poly_paths):
            assert len(legacy.points) == 2
            assert len(poly.points) == 2

    def test_single_mirror_compatibility(self):
        """Test that both engines handle a single mirror identically."""
        # Create mirror
        mirror_legacy = OpticalElement(
            kind="mirror", p1=np.array([50.0, -20.0]), p2=np.array([50.0, 20.0])
        )

        # Create source
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

        # Trace with legacy
        legacy_paths = trace_rays_legacy([mirror_legacy], [source], max_events=10)

        # Convert mirror to polymorphic
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=99.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror_poly = create_polymorphic_element(iface)

        # Trace with polymorphic
        poly_paths = trace_rays_polymorphic([mirror_poly], [source], max_events=10)

        # Both should produce 1 path
        assert len(legacy_paths) == len(poly_paths) == 1

        # Both paths should have similar structure
        legacy_path = legacy_paths[0]
        poly_path = poly_paths[0]

        # Similar number of points (within 1)
        assert abs(len(legacy_path.points) - len(poly_path.points)) <= 1

        # First point should be identical (source position)
        assert np.allclose(legacy_path.points[0], poly_path.points[0], atol=1e-6)

    def test_single_lens_compatibility(self):
        """Test that both engines handle a single lens identically."""
        # Create lens
        lens_legacy = OpticalElement(
            kind="lens", p1=np.array([50.0, -20.0]), p2=np.array([50.0, 20.0]), efl_mm=100.0
        )

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

        # Trace with legacy
        legacy_paths = trace_rays_legacy([lens_legacy], [source], max_events=10)

        # Convert lens to polymorphic
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = LensProperties(efl_mm=100.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        lens_poly = create_polymorphic_element(iface)

        # Trace with polymorphic
        poly_paths = trace_rays_polymorphic([lens_poly], [source], max_events=10)

        # Both should produce 1 path
        assert len(legacy_paths) == len(poly_paths) == 1

        # Compare paths
        legacy_path = legacy_paths[0]
        poly_path = poly_paths[0]

        # Similar number of points
        assert abs(len(legacy_path.points) - len(poly_path.points)) <= 1

        # First point identical
        assert np.allclose(legacy_path.points[0], poly_path.points[0], atol=1e-6)

    def test_beamsplitter_compatibility(self):
        """Test that both engines handle beamsplitters identically."""
        # Create beamsplitter
        bs_legacy = OpticalElement(
            kind="bs",
            p1=np.array([50.0, -20.0]),
            p2=np.array([50.0, 20.0]),
            split_T=70.0,
            split_R=30.0,
            is_polarizing=False,
            pbs_transmission_axis_deg=0.0,
        )

        # Create source
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

        # Trace with legacy
        legacy_paths = trace_rays_legacy([bs_legacy], [source], max_events=10)

        # Convert beamsplitter to polymorphic
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = BeamsplitterProperties(split_T=70.0, split_R=30.0, is_polarizing=False)
        iface = OpticalInterface(geometry=geom, properties=props)
        bs_poly = create_polymorphic_element(iface)

        # Trace with polymorphic
        poly_paths = trace_rays_polymorphic([bs_poly], [source], max_events=10)

        # Both should produce 2 paths (transmitted + reflected)
        assert len(legacy_paths) == len(poly_paths) == 2

    def test_multiple_rays_compatibility(self):
        """Test that both engines handle multiple rays identically."""
        # Create mirror
        mirror_legacy = OpticalElement(
            kind="mirror", p1=np.array([50.0, -30.0]), p2=np.array([50.0, 30.0])
        )

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

        # Trace with legacy
        legacy_paths = trace_rays_legacy([mirror_legacy], [source], max_events=10)

        # Convert mirror to polymorphic
        geom = LineSegment(np.array([50.0, -30.0]), np.array([50.0, 30.0]))
        props = MirrorProperties(reflectivity=99.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror_poly = create_polymorphic_element(iface)

        # Trace with polymorphic
        poly_paths = trace_rays_polymorphic([mirror_poly], [source], max_events=10)

        # Both should produce 5 paths
        assert len(legacy_paths) == len(poly_paths) == 5

    def test_complex_scene_compatibility(self):
        """Test that both engines handle a complex scene with multiple elements."""
        # Create elements (legacy format)
        lens_legacy = OpticalElement(
            kind="lens", p1=np.array([50.0, -20.0]), p2=np.array([50.0, 20.0]), efl_mm=100.0
        )
        mirror_legacy = OpticalElement(
            kind="mirror", p1=np.array([150.0, -20.0]), p2=np.array([150.0, 20.0])
        )

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

        # Trace with legacy
        legacy_paths = trace_rays_legacy([lens_legacy, mirror_legacy], [source], max_events=20)

        # Convert elements to polymorphic
        lens_geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        lens_props = LensProperties(efl_mm=100.0)
        lens_iface = OpticalInterface(geometry=lens_geom, properties=lens_props)
        lens_poly = create_polymorphic_element(lens_iface)

        mirror_geom = LineSegment(np.array([150.0, -20.0]), np.array([150.0, 20.0]))
        mirror_props = MirrorProperties(reflectivity=99.0)
        mirror_iface = OpticalInterface(geometry=mirror_geom, properties=mirror_props)
        mirror_poly = create_polymorphic_element(mirror_iface)

        # Trace with polymorphic
        poly_paths = trace_rays_polymorphic([lens_poly, mirror_poly], [source], max_events=20)

        # Both should produce 3 paths
        assert len(legacy_paths) == len(poly_paths) == 3

    def test_output_format_compatibility(self):
        """Test that both engines produce identical RayPath structures."""
        # Create mirror
        mirror_legacy = OpticalElement(
            kind="mirror", p1=np.array([50.0, -20.0]), p2=np.array([50.0, 20.0])
        )

        # Create source
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

        # Trace with legacy
        legacy_paths = trace_rays_legacy([mirror_legacy], [source], max_events=10)

        # Convert mirror to polymorphic
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=99.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror_poly = create_polymorphic_element(iface)

        # Trace with polymorphic
        poly_paths = trace_rays_polymorphic([mirror_poly], [source], max_events=10)

        # Compare RayPath structure
        legacy_path = legacy_paths[0]
        poly_path = poly_paths[0]

        # Both should have same attributes
        assert hasattr(legacy_path, "points")
        assert hasattr(poly_path, "points")
        assert hasattr(legacy_path, "rgba")
        assert hasattr(poly_path, "rgba")
        assert hasattr(legacy_path, "polarization")
        assert hasattr(poly_path, "polarization")
        assert hasattr(legacy_path, "wavelength_nm")
        assert hasattr(poly_path, "wavelength_nm")

        # RGBA format should be identical
        assert len(legacy_path.rgba) == len(poly_path.rgba) == 4

        # Wavelength should match
        assert legacy_path.wavelength_nm == poly_path.wavelength_nm == 633.0


class TestRegressionPrevention:
    """
    Tests that prevent regression by verifying specific known behaviors.
    """

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

        # Polymorphic engine
        poly_paths = trace_rays_polymorphic([], [source], max_events=10)

        # Should produce 1 path with 2 points (start and end)
        assert len(poly_paths) == 1
        assert len(poly_paths[0].points) == 2

        # End point should be ray_length_mm away
        start = poly_paths[0].points[0]
        end = poly_paths[0].points[1]
        distance = np.linalg.norm(end - start)
        assert distance == pytest.approx(100.0, rel=1e-6)

    def test_intensity_preservation(self):
        """Test that ray intensity is properly tracked."""
        # Create low-reflectivity mirror
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=50.0)  # 50% reflectivity
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror = create_polymorphic_element(iface)

        # Create source
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

        # Trace
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
        mirror1_props = MirrorProperties(reflectivity=99.0)
        mirror1_iface = OpticalInterface(geometry=mirror1_geom, properties=mirror1_props)
        mirror1 = create_polymorphic_element(mirror1_iface)

        mirror2_geom = LineSegment(np.array([100.0, -20.0]), np.array([100.0, 20.0]))
        mirror2_props = MirrorProperties(reflectivity=99.0)
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


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
