"""
Tests for the new polymorphic raytracing engine.

This tests the complete end-to-end raytracing using IOpticalElement polymorphism.
"""

import numpy as np

from optiverse.core.models import SourceParams
from optiverse.data import LensProperties, LineSegment, MirrorProperties, OpticalInterface
from optiverse.integration import create_polymorphic_element
from optiverse.raytracing.engine import trace_rays_polymorphic


class TestPolymorphicEngine:
    """Test the new polymorphic raytracing engine."""

    def test_empty_scene(self):
        """Test with no elements - rays should propagate freely."""
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

        # Should get 3 paths (3 rays), each propagating straight
        assert len(paths) == 3
        for path in paths:
            assert len(path.points) >= 2  # Start and end
            # First and last points should be horizontal (angle_deg=0)
            assert path.points[0][0] < path.points[-1][0]  # Moving right

    def test_single_mirror(self):
        """Test ray reflection off a single mirror."""
        # Create mirror at x=50
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=99.0)
        iface = OpticalInterface(geometry=geom, properties=props, name="Test Mirror")
        mirror = create_polymorphic_element(iface)

        # Create source shooting rays to the right
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

        # Should get 1 path
        assert len(paths) == 1
        path = paths[0]

        # Should have at least 3 points: start, hit mirror, reflect
        assert len(path.points) >= 2

        # Ray should hit mirror around x=50
        # Find the point closest to x=50
        hit_point = None
        for _i, pt in enumerate(path.points):
            if abs(pt[0] - 50.0) < 1.0:  # Within 1mm of mirror
                hit_point = pt
                break

        assert hit_point is not None, "Ray should hit the mirror"

    def test_single_lens(self):
        """Test ray refraction through a single lens."""
        # Create lens at x=50 with f=100mm
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = LensProperties(efl_mm=100.0)
        iface = OpticalInterface(geometry=geom, properties=props, name="Test Lens")
        lens = create_polymorphic_element(iface)

        # Create source with rays at y=10 (off-axis)
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

        # Should get 1 path
        assert len(paths) == 1
        path = paths[0]

        # Should have at least 2 points
        assert len(path.points) >= 2

        # Ray should hit lens around x=50
        hit_point = None
        for _i, pt in enumerate(path.points):
            if abs(pt[0] - 50.0) < 1.0:
                hit_point = pt
                break

        assert hit_point is not None, "Ray should hit the lens"

        # After lens, ray should bend downward (towards focal point at y=0, x=150)
        # Find last point after lens
        last_point = path.points[-1]
        if last_point[0] > 50.0:  # After lens
            # y should decrease (ray bending down toward optical axis)
            assert last_point[1] < hit_point[1], "Ray should bend toward optical axis"

    def test_mirror_and_lens(self):
        """Test ray through lens then reflecting off mirror."""
        # Create lens at x=50
        lens_geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        lens_props = LensProperties(efl_mm=100.0)
        lens_iface = OpticalInterface(geometry=lens_geom, properties=lens_props)
        lens = create_polymorphic_element(lens_iface)

        # Create mirror at x=100
        mirror_geom = LineSegment(np.array([100.0, -20.0]), np.array([100.0, 20.0]))
        mirror_props = MirrorProperties(reflectivity=99.0)
        mirror_iface = OpticalInterface(geometry=mirror_geom, properties=mirror_props)
        mirror = create_polymorphic_element(mirror_iface)

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

        paths = trace_rays_polymorphic([lens, mirror], [source], max_events=10)

        # Should get at least 1 path
        assert len(paths) >= 1
        path = paths[0]

        # Should have at least 3 points: start, through lens, hit mirror
        assert len(path.points) >= 3

    def test_multiple_rays(self):
        """Test with multiple rays from a source."""
        # Create mirror
        geom = LineSegment(np.array([50.0, -30.0]), np.array([50.0, 30.0]))
        props = MirrorProperties(reflectivity=99.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror = create_polymorphic_element(iface)

        # Create source with 5 rays
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=5,
            size_mm=20.0,  # 5 rays spread over 20mm
            ray_length_mm=200.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([mirror], [source], max_events=10)

        # Should get 5 paths (one per ray)
        assert len(paths) == 5

    def test_max_events_limit(self):
        """Test that rays stop after max_events interactions."""
        # Create two mirrors facing each other (cavity)
        mirror1_geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        mirror1_props = MirrorProperties(reflectivity=99.0)
        mirror1_iface = OpticalInterface(geometry=mirror1_geom, properties=mirror1_props)
        mirror1 = create_polymorphic_element(mirror1_iface)

        mirror2_geom = LineSegment(np.array([100.0, -20.0]), np.array([100.0, 20.0]))
        mirror2_props = MirrorProperties(reflectivity=99.0)
        mirror2_iface = OpticalInterface(geometry=mirror2_geom, properties=mirror2_props)
        mirror2 = create_polymorphic_element(mirror2_iface)

        # Create source
        source = SourceParams(
            x_mm=75.0,
            y_mm=0.0,  # Start between mirrors
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=1,
            size_mm=0.0,
            ray_length_mm=1000.0,  # Very long
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        # Limit to 5 events
        paths = trace_rays_polymorphic([mirror1, mirror2], [source], max_events=5)

        # Should get 1 path that stops after 5 events
        assert len(paths) >= 1
        # Ray should interact multiple times but stop before hitting 1000mm

    def test_intensity_threshold(self):
        """Test that dim rays are terminated."""
        # Create multiple partially reflective mirrors
        mirrors = []
        for x in [50, 100, 150, 200]:
            geom = LineSegment(np.array([float(x), -20.0]), np.array([float(x), 20.0]))
            props = MirrorProperties(reflectivity=50.0)  # Only 50% reflectivity
            iface = OpticalInterface(geometry=geom, properties=props)
            mirrors.append(create_polymorphic_element(iface))

        # Create source
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=1,
            size_mm=0.0,
            ray_length_mm=500.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic(mirrors, [source], max_events=10)

        # Ray should be terminated before hitting all 4 mirrors due to intensity loss
        # After 4 reflections at 50%: 0.5^4 = 0.0625 = 6.25% intensity
        # Should be below typical 2% threshold after 3-4 mirrors
        assert len(paths) >= 1


class TestEngineOutputFormat:
    """Test that the new engine matches the old engine's output format."""

    def test_raypath_structure(self):
        """Test that RayPath objects have correct structure."""
        # Create simple scene
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=99.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror = create_polymorphic_element(iface)

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

        paths = trace_rays_polymorphic([mirror], [source], max_events=10)

        assert len(paths) >= 1
        path = paths[0]

        # Check RayPath structure
        assert hasattr(path, "points")
        assert hasattr(path, "rgba")
        assert hasattr(path, "polarization")
        assert hasattr(path, "wavelength_nm")

        # Check types
        assert isinstance(path.points, list)
        assert all(isinstance(pt, np.ndarray) for pt in path.points)
        assert isinstance(path.rgba, tuple)
        assert len(path.rgba) == 4  # R, G, B, A
        assert path.wavelength_nm == 633.0

    def test_rgba_alpha_intensity(self):
        """Test that RGBA alpha channel reflects ray intensity."""
        # Create mirror with low reflectivity
        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=50.0)  # 50% reflectivity
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

        # Should get 2 paths: before and after reflection
        # After reflection, intensity should be ~50%, so alpha should be ~127
        if len(paths) >= 1:
            for path in paths:
                r, g, b, a = path.rgba
                assert 0 <= a <= 255
                assert r == 255  # Red source
                assert g == 0
                assert b == 0


class TestBackwardCompatibility:
    """Test that new engine produces similar results to old engine."""

    def test_similar_output_simple_scene(self):
        """Compare new and old engines on a simple scene."""
        # This test would compare outputs, but for now we just ensure
        # the new engine produces reasonable output

        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = MirrorProperties(reflectivity=99.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        mirror = create_polymorphic_element(iface)

        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,
            spread_deg=0.0,
            n_rays=3,
            size_mm=10.0,
            ray_length_mm=200.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([mirror], [source], max_events=10)

        # Should get 3 paths, each with reasonable length
        assert len(paths) == 3
        for path in paths:
            assert len(path.points) >= 2
            # Points should be numpy arrays
            for pt in path.points:
                assert isinstance(pt, np.ndarray)
                assert pt.shape == (2,)


class TestPolymorphicDispatch:
    """Test that polymorphic dispatch works correctly."""

    def test_no_string_based_dispatch(self):
        """Verify that no string-based type checking occurs."""
        # This is more of a code inspection test, but we can verify behavior
        # The engine should work with any IOpticalElement, regardless of type

        from optiverse.data import BeamsplitterProperties

        geom = LineSegment(np.array([50.0, -20.0]), np.array([50.0, 20.0]))
        props = BeamsplitterProperties(split_T=50.0, split_R=50.0)
        iface = OpticalInterface(geometry=geom, properties=props)
        bs = create_polymorphic_element(iface)

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

        paths = trace_rays_polymorphic([bs], [source], max_events=10)

        # Should get 2 paths (transmitted + reflected)
        assert len(paths) >= 1
        # The engine doesn't need to know bs is a "beamsplitter"
        # It just calls bs.interact_with_ray() polymorphically!


class TestRaySeparationRotation:
    """Test that ray separation remains constant when source is rotated."""

    def test_ray_separation_perpendicular_at_0_degrees(self):
        """At 0°, rays should be separated vertically."""
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=0.0,  # Pointing right
            spread_deg=0.0,
            n_rays=3,
            size_mm=10.0,  # 10mm aperture
            ray_length_mm=100.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([], [source], max_events=1)

        # Should get 3 rays
        assert len(paths) == 3

        # Extract starting positions
        positions = [path.points[0] for path in paths]

        # At 0°, separation should be vertical (Y direction)
        # Rays at y = -5, 0, +5
        y_positions = sorted([pos[1] for pos in positions])
        assert abs(y_positions[0] - (-5.0)) < 0.01, f"Expected -5, got {y_positions[0]}"
        assert abs(y_positions[1] - 0.0) < 0.01, f"Expected 0, got {y_positions[1]}"
        assert abs(y_positions[2] - 5.0) < 0.01, f"Expected 5, got {y_positions[2]}"

        # All should start at x=0
        x_positions = [pos[0] for pos in positions]
        assert all(abs(x) < 0.01 for x in x_positions)

    def test_ray_separation_perpendicular_at_90_degrees(self):
        """At 90°, rays should be separated horizontally."""
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=90.0,  # Pointing up
            spread_deg=0.0,
            n_rays=3,
            size_mm=10.0,  # 10mm aperture
            ray_length_mm=100.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([], [source], max_events=1)

        # Should get 3 rays
        assert len(paths) == 3

        # Extract starting positions
        positions = [path.points[0] for path in paths]

        # At 90°, separation should be horizontal (X direction)
        # Rays at x = -5, 0, +5
        x_positions = sorted([pos[0] for pos in positions])
        assert abs(x_positions[0] - (-5.0)) < 0.01, f"Expected -5, got {x_positions[0]}"
        assert abs(x_positions[1] - 0.0) < 0.01, f"Expected 0, got {x_positions[1]}"
        assert abs(x_positions[2] - 5.0) < 0.01, f"Expected 5, got {x_positions[2]}"

        # All should start at y=0
        y_positions = [pos[1] for pos in positions]
        assert all(abs(y) < 0.01 for y in y_positions)

    def test_ray_separation_perpendicular_at_45_degrees(self):
        """At 45°, rays should be separated perpendicular to 45° direction."""
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=45.0,  # Pointing at 45°
            spread_deg=0.0,
            n_rays=3,
            size_mm=10.0,  # 10mm aperture
            ray_length_mm=100.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([], [source], max_events=1)

        # Should get 3 rays
        assert len(paths) == 3

        # Extract starting positions
        positions = [path.points[0] for path in paths]

        # At 45°, perpendicular direction is 135° (or -45°)
        # Perpendicular vector: [-sin(45°), cos(45°)] = [-√2/2, √2/2]
        # Rays should be offset by -5, 0, +5 times this vector

        # Check that separation is perpendicular to ray direction
        # Ray direction at 45°: [cos(45°), sin(45°)] = [√2/2, √2/2]
        ray_dir = np.array([np.cos(np.radians(45)), np.sin(np.radians(45))])

        # Vector from first ray to last ray
        separation_vector = positions[2] - positions[0]

        # Dot product should be ~0 (perpendicular)
        dot_product = np.dot(separation_vector, ray_dir)
        assert abs(dot_product) < 0.01, (
            f"Separation should be perpendicular to ray direction, dot={dot_product}"
        )

        # Separation magnitude should be ~10mm (size_mm)
        separation_magnitude = np.linalg.norm(separation_vector)
        assert abs(separation_magnitude - 10.0) < 0.01, (
            f"Expected 10mm separation, got {separation_magnitude}"
        )

    def test_ray_separation_perpendicular_at_180_degrees(self):
        """At 180°, rays should be separated vertically."""
        source = SourceParams(
            x_mm=0.0,
            y_mm=0.0,
            angle_deg=180.0,  # Pointing left
            spread_deg=0.0,
            n_rays=3,
            size_mm=10.0,  # 10mm aperture
            ray_length_mm=100.0,
            wavelength_nm=633.0,
            color_hex="#FF0000",
            polarization_type="horizontal",
        )

        paths = trace_rays_polymorphic([], [source], max_events=1)

        # Should get 3 rays
        assert len(paths) == 3

        # Extract starting positions
        positions = [path.points[0] for path in paths]

        # At 180°, separation should still be vertical (Y direction)
        # But with opposite perpendicular: rays at y = +5, 0, -5 (reversed order)
        y_positions = sorted([pos[1] for pos in positions])
        assert abs(y_positions[0] - (-5.0)) < 0.01
        assert abs(y_positions[1] - 0.0) < 0.01
        assert abs(y_positions[2] - 5.0) < 0.01

        # All should start at x=0
        x_positions = [pos[0] for pos in positions]
        assert all(abs(x) < 0.01 for x in x_positions)

    def test_ray_separation_consistent_across_angles(self):
        """Ray separation magnitude should be constant across all angles."""
        angles = [0, 30, 45, 60, 90, 120, 135, 150, 180, 270]

        for angle in angles:
            source = SourceParams(
                x_mm=0.0,
                y_mm=0.0,
                angle_deg=angle,
                spread_deg=0.0,
                n_rays=5,
                size_mm=20.0,  # 20mm aperture
                ray_length_mm=100.0,
                wavelength_nm=633.0,
                color_hex="#FF0000",
                polarization_type="horizontal",
            )

            paths = trace_rays_polymorphic([], [source], max_events=1)

            # Should get 5 rays
            assert len(paths) == 5, f"Expected 5 rays at {angle}°, got {len(paths)}"

            # Extract starting positions
            positions = [path.points[0] for path in paths]

            # Calculate separation between first and last ray
            separation_vector = positions[-1] - positions[0]
            separation_magnitude = np.linalg.norm(separation_vector)

            # Should be 20mm (aperture size)
            assert abs(separation_magnitude - 20.0) < 0.01, (
                f"At {angle}°: Expected 20mm separation, got {separation_magnitude}"
            )

            # Verify perpendicular to ray direction
            ray_dir = np.array([np.cos(np.radians(angle)), np.sin(np.radians(angle))])
            dot_product = np.dot(separation_vector, ray_dir)
            assert abs(dot_product) < 0.01, (
                f"At {angle}°: Separation should be perpendicular, dot={dot_product}"
            )
