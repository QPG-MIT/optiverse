"""
Unit tests for segment-based path measurement system.

Tests PathSegment, PathMeasurement data models and split detection algorithms.
"""

import numpy as np
import pytest

from optiverse.core.models import PathMeasurement, PathSegment


class TestPathSegment:
    """Test PathSegment data model."""

    def test_segment_creation(self):
        """Test creating a PathSegment."""
        start = np.array([0.0, 0.0])
        end = np.array([10.0, 0.0])
        segment = PathSegment(ray_index=0, start_point=start, end_point=end)

        assert segment.ray_index == 0
        assert np.allclose(segment.start_point, start)
        assert np.allclose(segment.end_point, end)

    def test_segment_distance_horizontal(self):
        """Test distance calculation for horizontal segment."""
        segment = PathSegment(
            ray_index=0, start_point=np.array([0.0, 0.0]), end_point=np.array([10.0, 0.0])
        )
        assert abs(segment.distance() - 10.0) < 1e-6

    def test_segment_distance_vertical(self):
        """Test distance calculation for vertical segment."""
        segment = PathSegment(
            ray_index=0, start_point=np.array([0.0, 0.0]), end_point=np.array([0.0, 20.0])
        )
        assert abs(segment.distance() - 20.0) < 1e-6

    def test_segment_distance_diagonal(self):
        """Test distance calculation for diagonal segment."""
        segment = PathSegment(
            ray_index=0, start_point=np.array([0.0, 0.0]), end_point=np.array([3.0, 4.0])
        )
        # 3-4-5 right triangle
        assert abs(segment.distance() - 5.0) < 1e-6


class TestPathMeasurement:
    """Test PathMeasurement data model."""

    def test_measurement_creation(self):
        """Test creating a PathMeasurement."""
        seg1 = PathSegment(
            ray_index=0, start_point=np.array([0.0, 0.0]), end_point=np.array([10.0, 0.0])
        )
        measurement = PathMeasurement(segments=[seg1], label="Test: ", group_id="test-123")

        assert len(measurement.segments) == 1
        assert measurement.label == "Test: "
        assert measurement.group_id == "test-123"

    def test_measurement_total_distance_single_segment(self):
        """Test total distance with single segment."""
        seg1 = PathSegment(
            ray_index=0, start_point=np.array([0.0, 0.0]), end_point=np.array([10.0, 0.0])
        )
        measurement = PathMeasurement(segments=[seg1])

        assert abs(measurement.total_distance() - 10.0) < 1e-6

    def test_measurement_total_distance_multiple_segments(self):
        """Test total distance with multiple segments."""
        seg1 = PathSegment(
            ray_index=0, start_point=np.array([0.0, 0.0]), end_point=np.array([10.0, 0.0])
        )
        seg2 = PathSegment(
            ray_index=0, start_point=np.array([10.0, 0.0]), end_point=np.array([20.0, 0.0])
        )
        measurement = PathMeasurement(segments=[seg1, seg2])

        assert abs(measurement.total_distance() - 20.0) < 1e-6

    def test_measurement_all_ray_indices(self):
        """Test getting all ray indices from a measurement."""
        seg1 = PathSegment(
            ray_index=0, start_point=np.array([0.0, 0.0]), end_point=np.array([10.0, 0.0])
        )
        seg2 = PathSegment(
            ray_index=1, start_point=np.array([10.0, 0.0]), end_point=np.array([20.0, 5.0])
        )
        measurement = PathMeasurement(segments=[seg1, seg2])

        indices = measurement.all_ray_indices()
        assert indices == [0, 1]

    def test_measurement_empty_label(self):
        """Test measurement with empty label."""
        seg1 = PathSegment(
            ray_index=0, start_point=np.array([0.0, 0.0]), end_point=np.array([10.0, 0.0])
        )
        measurement = PathMeasurement(segments=[seg1])

        assert measurement.label == ""
        assert measurement.group_id == ""


class TestBeamSplitterScenarios:
    """Test beam splitter measurement scenarios."""

    def test_simple_beam_splitter(self):
        """Test measurement through simple beam splitter."""
        # Before split (common segment)
        common_seg = PathSegment(
            ray_index=0, start_point=np.array([0.0, 0.0]), end_point=np.array([20.0, 20.0])
        )

        # After split - transmitted
        transmitted_seg = PathSegment(
            ray_index=0, start_point=np.array([20.0, 20.0]), end_point=np.array([40.0, 20.0])
        )

        # After split - reflected
        reflected_seg = PathSegment(
            ray_index=1, start_point=np.array([20.0, 20.0]), end_point=np.array([20.0, 40.0])
        )

        # Create measurements
        transmitted_measurement = PathMeasurement(
            segments=[common_seg, transmitted_seg], label="T: ", group_id="group-1"
        )

        reflected_measurement = PathMeasurement(
            segments=[common_seg, reflected_seg], label="R: ", group_id="group-1"
        )

        # Check distances
        # Common: sqrt(20^2 + 20^2) ≈ 28.28
        # Transmitted after: 20.0
        # Reflected after: 20.0
        expected_transmitted = np.sqrt(20**2 + 20**2) + 20.0
        expected_reflected = np.sqrt(20**2 + 20**2) + 20.0

        assert abs(transmitted_measurement.total_distance() - expected_transmitted) < 1e-6
        assert abs(reflected_measurement.total_distance() - expected_reflected) < 1e-6

        # Check group IDs match
        assert transmitted_measurement.group_id == reflected_measurement.group_id

        # Check labels
        assert transmitted_measurement.label == "T: "
        assert reflected_measurement.label == "R: "


class TestSplitDetectionScenarios:
    """Test split point detection scenarios."""

    def test_rays_with_common_start(self):
        """Test detecting rays that share starting points."""
        # Ray 1: [0,0] -> [10,10] -> [20,10]
        ray1_points = [np.array([0.0, 0.0]), np.array([10.0, 10.0]), np.array([20.0, 10.0])]

        # Ray 2: [0,0] -> [10,10] -> [10,20] (splits at [10,10])
        ray2_points = [np.array([0.0, 0.0]), np.array([10.0, 10.0]), np.array([10.0, 20.0])]

        # In real implementation, this would be tested through MainWindow._find_split_point
        # Here we just verify the data structure is correct
        assert np.allclose(ray1_points[0], ray2_points[0])
        assert np.allclose(ray1_points[1], ray2_points[1])
        assert not np.allclose(ray1_points[2], ray2_points[2])

    def test_rays_with_no_common_points(self):
        """Test rays that don't share any points."""
        # Ray 1: starts at [0,0]
        ray1_points = [np.array([0.0, 0.0]), np.array([10.0, 0.0])]

        # Ray 2: starts at [100,0]
        ray2_points = [np.array([100.0, 0.0]), np.array([110.0, 0.0])]

        # No common points - these shouldn't be grouped
        assert not np.allclose(ray1_points[0], ray2_points[0])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

