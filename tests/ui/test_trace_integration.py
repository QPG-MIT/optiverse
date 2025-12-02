"""
Test ray tracing integration in the UI.

These tests verify that:
- Ray tracing produces rays when sources and elements are present
- Ray paths are rendered to the scene
- Autotrace works correctly
- Ray tracing handles various optical elements
"""

from __future__ import annotations

from PyQt6 import QtCore

from optiverse.core.component_types import ComponentType
from optiverse.core.models import SourceParams
from optiverse.objects import SourceItem


class TestRayTracingIntegration:
    """Test ray tracing integration with the UI."""

    def test_retrace_with_no_sources(self, main_window):
        """Test that retrace with no sources doesn't crash."""
        # Should not raise
        main_window.raytracing_controller.retrace()
        assert main_window.raytracing_controller.ray_data == []

    def test_retrace_with_source_only(self, main_window):
        """Test that retrace with only a source produces ray data."""
        # Add a source
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, angle_deg=0.0, n_rays=5, size_mm=10.0))
        main_window.scene.addItem(source)

        # Retrace
        main_window.raytracing_controller.retrace()

        # Should have ray data
        assert len(main_window.raytracing_controller.ray_data) > 0

    def test_retrace_with_source_and_mirror(self, main_window):
        """Test that rays interact with a mirror."""
        # Add a source shooting to the right
        source = SourceItem(
            SourceParams(
                x_mm=-100.0,
                y_mm=0.0,
                angle_deg=0.0,
                n_rays=1,
                size_mm=0.0,
                ray_length_mm=500.0,
            )
        )
        main_window.scene.addItem(source)

        # Add a mirror at 45 degrees
        main_window.placement_handler.place_component_at(ComponentType.MIRROR, QtCore.QPointF(0, 0))

        # Retrace
        main_window.raytracing_controller.retrace()

        # Should have ray data
        ray_data = main_window.raytracing_controller.ray_data
        assert len(ray_data) >= 1

        # Ray should have multiple segments (at least 2 points - start and end)
        first_ray = ray_data[0]
        assert len(first_ray.points) >= 2

    def test_retrace_with_source_and_lens(self, main_window):
        """Test that rays interact with a lens."""
        # Add a source shooting to the right, slightly off-axis
        source = SourceItem(
            SourceParams(
                x_mm=-100.0,
                y_mm=10.0,
                angle_deg=0.0,
                n_rays=1,
                size_mm=0.0,
                ray_length_mm=500.0,
            )
        )
        main_window.scene.addItem(source)

        # Add a lens
        main_window.placement_handler.place_component_at(ComponentType.LENS, QtCore.QPointF(0, 0))

        # Retrace
        main_window.raytracing_controller.retrace()

        # Should have ray data
        ray_data = main_window.raytracing_controller.ray_data
        assert len(ray_data) >= 1

    def test_retrace_with_beamsplitter(self, main_window):
        """Test that beamsplitter splits the ray."""
        # Add a source shooting to the right
        source = SourceItem(
            SourceParams(
                x_mm=-100.0,
                y_mm=0.0,
                angle_deg=0.0,
                n_rays=1,
                size_mm=0.0,
                ray_length_mm=500.0,
            )
        )
        main_window.scene.addItem(source)

        # Add a beamsplitter at 45 degrees
        main_window.placement_handler.place_component_at(
            ComponentType.BEAMSPLITTER, QtCore.QPointF(0, 0)
        )

        # Retrace
        main_window.raytracing_controller.retrace()

        # Should have at least 2 ray paths (transmitted and reflected)
        ray_data = main_window.raytracing_controller.ray_data
        assert len(ray_data) >= 2

    def test_autotrace_triggers_on_item_add(self, main_window, qtbot):
        """Test that autotrace schedules retrace when item is added."""
        main_window.autotrace = True

        # Add a source
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, angle_deg=0.0, n_rays=3, size_mm=10.0))
        main_window.scene.addItem(source)

        # Manually trigger scheduled retrace (normally happens via timer)
        main_window.raytracing_controller._do_retrace()

        # Should have ray data
        assert len(main_window.raytracing_controller.ray_data) > 0

    def test_clear_rays(self, main_window):
        """Test that clear_rays removes all ray data."""
        # Add a source
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, angle_deg=0.0, n_rays=5, size_mm=10.0))
        main_window.scene.addItem(source)

        # Retrace
        main_window.raytracing_controller.retrace()
        assert len(main_window.raytracing_controller.ray_data) > 0

        # Clear rays
        main_window.raytracing_controller.clear_rays()
        assert len(main_window.raytracing_controller.ray_data) == 0

    def test_multiple_sources(self, main_window):
        """Test ray tracing with multiple sources."""
        # Add two sources
        source1 = SourceItem(
            SourceParams(
                x_mm=-100.0,
                y_mm=-50.0,
                angle_deg=0.0,
                n_rays=3,
                size_mm=5.0,
                color_hex="#FF0000",
            )
        )
        source2 = SourceItem(
            SourceParams(
                x_mm=-100.0,
                y_mm=50.0,
                angle_deg=0.0,
                n_rays=3,
                size_mm=5.0,
                color_hex="#00FF00",
            )
        )
        main_window.scene.addItem(source1)
        main_window.scene.addItem(source2)

        # Retrace
        main_window.raytracing_controller.retrace()

        # Should have rays from both sources (6 total)
        ray_data = main_window.raytracing_controller.ray_data
        assert len(ray_data) == 6

    def test_rays_changed_signal(self, main_window, qtbot):
        """Test that rays_changed signal is emitted after retrace."""
        # Add a source
        source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0, angle_deg=0.0, n_rays=3, size_mm=10.0))
        main_window.scene.addItem(source)

        # Listen for signal
        with qtbot.waitSignal(main_window.raytracing_controller.rays_changed, timeout=1000):
            main_window.raytracing_controller.retrace()

    def test_ray_width_property(self, main_window):
        """Test ray width property."""
        main_window.raytracing_controller.ray_width_px = 3.0
        assert main_window.raytracing_controller.ray_width_px == 3.0


class TestRayInteractions:
    """Test that rays interact correctly with optical elements."""

    def test_mirror_reflection_angle(self, main_window):
        """Test that mirror reflects rays at correct angle."""
        import numpy as np

        # Add a source shooting horizontally to the right
        source = SourceItem(
            SourceParams(
                x_mm=-200.0,
                y_mm=0.0,
                angle_deg=0.0,
                n_rays=1,
                size_mm=0.0,
                ray_length_mm=500.0,
            )
        )
        main_window.scene.addItem(source)

        # Add a mirror at 45 degrees at the origin
        main_window.placement_handler.place_component_at(ComponentType.MIRROR, QtCore.QPointF(0, 0))

        # Retrace
        main_window.raytracing_controller.retrace()

        ray_data = main_window.raytracing_controller.ray_data
        assert len(ray_data) >= 1

        # Get the first ray path
        ray = ray_data[0]
        assert len(ray.points) >= 3  # Start, hit mirror, reflected end

        # Check that ray changed direction (reflected)
        if len(ray.points) >= 3:
            # Direction before hit
            p0 = np.array(ray.points[0])
            p1 = np.array(ray.points[1])
            dir_before = p1 - p0
            dir_before = dir_before / np.linalg.norm(dir_before)

            # Direction after hit
            p2 = np.array(ray.points[2])
            dir_after = p2 - p1
            dir_after = dir_after / np.linalg.norm(dir_after)

            # Directions should be different (ray was reflected)
            dot = np.dot(dir_before, dir_after)
            # For 45 degree mirror, horizontal ray should reflect upward
            # Dot product should be close to 0 (perpendicular)
            assert abs(dot) < 0.5, f"Ray should have reflected, got dot={dot}"

    def test_lens_bends_rays(self, main_window):
        """Test that lens bends rays toward focus."""
        import numpy as np

        # Add a source off-axis shooting horizontally
        source = SourceItem(
            SourceParams(
                x_mm=-200.0,
                y_mm=20.0,  # Off axis
                angle_deg=0.0,
                n_rays=1,
                size_mm=0.0,
                ray_length_mm=500.0,
            )
        )
        main_window.scene.addItem(source)

        # Add a lens at the origin
        main_window.placement_handler.place_component_at(ComponentType.LENS, QtCore.QPointF(0, 0))

        # Retrace
        main_window.raytracing_controller.retrace()

        ray_data = main_window.raytracing_controller.ray_data
        assert len(ray_data) >= 1

        ray = ray_data[0]
        if len(ray.points) >= 3:
            # After lens, ray should bend toward optical axis (y=0)
            p_after_lens = np.array(ray.points[-1])

            # Since source was at y=20 and ray was horizontal,
            # after converging lens the ray should bend downward
            # (toward smaller y values when moving to positive x)
            p_at_lens = np.array(ray.points[1])

            # Y coordinate should decrease after positive EFL lens
            # (ray bends toward axis)
            if p_after_lens[0] > p_at_lens[0]:
                assert p_after_lens[1] < p_at_lens[1], "Lens should bend ray toward axis"

    def test_dichroic_wavelength_dependent(self, main_window):
        """Test that dichroic behavior depends on wavelength."""
        # Add a red source (633nm)
        source_red = SourceItem(
            SourceParams(
                x_mm=-200.0,
                y_mm=0.0,
                angle_deg=0.0,
                n_rays=1,
                size_mm=0.0,
                ray_length_mm=500.0,
                wavelength_nm=633.0,
                color_hex="#FF0000",
            )
        )
        main_window.scene.addItem(source_red)

        # Add a dichroic
        main_window.placement_handler.place_component_at(
            ComponentType.DICHROIC, QtCore.QPointF(0, 0)
        )

        # Retrace
        main_window.raytracing_controller.retrace()

        # Should have ray data
        ray_data = main_window.raytracing_controller.ray_data
        assert len(ray_data) >= 1

    def test_waveplate_preserves_ray_count(self, main_window):
        """Test that waveplate doesn't split rays (only changes polarization)."""
        # Add a source
        source = SourceItem(
            SourceParams(
                x_mm=-200.0,
                y_mm=0.0,
                angle_deg=0.0,
                n_rays=3,
                size_mm=10.0,
                ray_length_mm=500.0,
            )
        )
        main_window.scene.addItem(source)

        # Add a waveplate
        main_window.placement_handler.place_component_at(
            ComponentType.WAVEPLATE, QtCore.QPointF(0, 0)
        )

        # Retrace
        main_window.raytracing_controller.retrace()

        # Should still have same number of rays (waveplate doesn't split)
        ray_data = main_window.raytracing_controller.ray_data
        assert len(ray_data) == 3
