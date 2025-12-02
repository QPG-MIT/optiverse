"""
Tests for polarization functionality.
"""

import numpy as np

from optiverse.core.models import OpticalElement, Polarization, SourceParams
from optiverse.core.raytracing_math import (
    transform_polarization_beamsplitter,
    transform_polarization_lens,
    transform_polarization_mirror,
)
from optiverse.core.use_cases import trace_rays


class TestPolarization:
    """Test Polarization class and Jones vector operations."""

    def test_horizontal_polarization(self):
        """Test horizontal polarization creation."""
        pol = Polarization.horizontal()
        assert np.allclose(pol.jones_vector, [1.0, 0.0])
        assert np.isclose(pol.intensity(), 1.0)

    def test_vertical_polarization(self):
        """Test vertical polarization creation."""
        pol = Polarization.vertical()
        assert np.allclose(pol.jones_vector, [0.0, 1.0])
        assert np.isclose(pol.intensity(), 1.0)

    def test_diagonal_polarization(self):
        """Test diagonal polarization."""
        pol = Polarization.diagonal_plus_45()
        expected = np.array([1.0, 1.0]) / np.sqrt(2)
        assert np.allclose(pol.jones_vector, expected)
        assert np.isclose(pol.intensity(), 1.0)

    def test_circular_polarization(self):
        """Test circular polarization."""
        pol = Polarization.circular_right()
        expected = np.array([1.0, 1j]) / np.sqrt(2)
        assert np.allclose(pol.jones_vector, expected)
        assert np.isclose(pol.intensity(), 1.0)

    def test_linear_at_angle(self):
        """Test linear polarization at arbitrary angle."""
        pol = Polarization.linear(45.0)
        expected = np.array([np.cos(np.pi / 4), np.sin(np.pi / 4)])
        assert np.allclose(pol.jones_vector, expected)

    def test_normalization(self):
        """Test polarization normalization."""
        pol = Polarization(np.array([3.0, 4.0], dtype=complex))
        pol_norm = pol.normalize()
        assert np.isclose(pol_norm.intensity(), 1.0)

    def test_serialization(self):
        """Test polarization serialization and deserialization."""
        pol = Polarization(np.array([1.0 + 2j, 3.0 - 4j], dtype=complex))
        d = pol.to_dict()
        pol2 = Polarization.from_dict(d)
        assert np.allclose(pol.jones_vector, pol2.jones_vector)


class TestPolarizationTransforms:
    """Test polarization transformations through optical elements."""

    def test_mirror_preserves_s_polarization(self):
        """Test that s-polarization is preserved (phase) on mirror reflection."""
        pol = Polarization.horizontal()
        v_in = np.array([1.0, 0.0])  # Ray traveling horizontally
        n_hat = np.array([1.0, 0.0])  # Mirror normal pointing horizontally

        pol_out = transform_polarization_mirror(pol, v_in, n_hat)
        # s-polarization should maintain intensity
        assert pol_out.intensity() > 0.9

    def test_mirror_phase_shift_p_polarization(self):
        """Test that p-polarization gets phase shift on mirror reflection."""
        pol = Polarization.vertical()
        v_in = np.array([1.0, 0.0])
        n_hat = np.array([1.0, 0.0])

        pol_out = transform_polarization_mirror(pol, v_in, n_hat)
        # Intensity should be preserved
        assert pol_out.intensity() > 0.9

    def test_lens_preserves_polarization(self):
        """Test that lens preserves polarization."""
        pol = Polarization.diagonal_plus_45()
        pol_out = transform_polarization_lens(pol)
        assert np.allclose(pol.jones_vector, pol_out.jones_vector)

    def test_pbs_separates_polarizations(self):
        """Test PBS separates horizontal and vertical polarizations."""
        # 45-degree polarization (equal H and V components)
        pol = Polarization.diagonal_plus_45()
        v_in = np.array([1.0, 0.0])
        n_hat = np.array([0.0, 1.0])
        t_hat = np.array([1.0, 0.0])

        # PBS with transmission axis at 0° (horizontal)
        pol_t, intensity_t = transform_polarization_beamsplitter(
            pol, v_in, n_hat, t_hat, is_polarizing=True, pbs_axis_deg=0.0, is_transmitted=True
        )
        pol_r, intensity_r = transform_polarization_beamsplitter(
            pol, v_in, n_hat, t_hat, is_polarizing=True, pbs_axis_deg=0.0, is_transmitted=False
        )

        # Each output should get 50% of intensity (since input is 45°)
        assert np.isclose(intensity_t, 0.5, atol=0.1)
        assert np.isclose(intensity_r, 0.5, atol=0.1)

        # Transmitted should be mostly horizontal
        assert np.abs(pol_t.jones_vector[0]) > np.abs(pol_t.jones_vector[1])
        # Reflected should be mostly vertical
        assert np.abs(pol_r.jones_vector[1]) > np.abs(pol_r.jones_vector[0])

    def test_non_polarizing_bs_preserves_polarization(self):
        """Test non-polarizing BS preserves polarization state."""
        pol = Polarization.circular_right()
        v_in = np.array([1.0, 0.0])
        n_hat = np.array([0.0, 1.0])
        t_hat = np.array([1.0, 0.0])

        pol_t, intensity_t = transform_polarization_beamsplitter(
            pol, v_in, n_hat, t_hat, is_polarizing=False, pbs_axis_deg=0.0, is_transmitted=True
        )

        # Should preserve circular polarization
        assert intensity_t == 1.0
        # Circular polarization should be maintained
        assert np.allclose(pol.jones_vector, pol_t.jones_vector)


class TestSourceParamsPolarization:
    """Test SourceParams polarization interface."""

    def test_default_polarization(self):
        """Test default horizontal polarization."""
        src = SourceParams()
        pol = src.get_polarization()
        assert np.allclose(pol.jones_vector, [1.0, 0.0])

    def test_vertical_polarization(self):
        """Test vertical polarization."""
        src = SourceParams(polarization_type="vertical")
        pol = src.get_polarization()
        assert np.allclose(pol.jones_vector, [0.0, 1.0])

    def test_linear_polarization(self):
        """Test linear polarization at custom angle."""
        src = SourceParams(polarization_type="linear", polarization_angle_deg=30.0)
        pol = src.get_polarization()
        expected = Polarization.linear(30.0)
        assert np.allclose(pol.jones_vector, expected.jones_vector)

    def test_custom_jones_vector(self):
        """Test custom Jones vector."""
        src = SourceParams(
            use_custom_jones=True,
            custom_jones_ex_real=1.0,
            custom_jones_ex_imag=0.0,
            custom_jones_ey_real=0.0,
            custom_jones_ey_imag=1.0,
        )
        pol = src.get_polarization()
        assert np.allclose(pol.jones_vector, [1.0, 1j])


class TestRayTracingWithPolarization:
    """Test ray tracing with polarization."""

    def test_trace_with_polarization(self):
        """Test basic ray tracing includes polarization."""
        # Create a simple source
        src = SourceParams(
            x_mm=-100.0,
            y_mm=0.0,
            angle_deg=0.0,
            n_rays=1,
            ray_length_mm=200.0,
            polarization_type="horizontal",
        )

        # No optical elements
        paths = trace_rays([], [src])

        assert len(paths) > 0
        # Each path should have polarization
        for path in paths:
            assert path.polarization is not None
            assert np.allclose(path.polarization.jones_vector, [1.0, 0.0])

    def test_trace_mirror_transforms_polarization(self):
        """Test mirror reflection transforms polarization."""
        src = SourceParams(
            x_mm=-100.0,
            y_mm=0.0,
            angle_deg=0.0,
            n_rays=1,
            ray_length_mm=200.0,
            polarization_type="horizontal",
        )

        # Add a mirror
        mirror = OpticalElement(kind="mirror", p1=np.array([0.0, -50.0]), p2=np.array([0.0, 50.0]))

        paths = trace_rays([mirror], [src])

        # Should have ray paths (source ray + reflected ray segments)
        assert len(paths) > 0
        # At least some paths should have polarization
        for path in paths:
            assert path.polarization is not None

    def test_pbs_splits_by_polarization(self):
        """Test PBS splits rays by polarization."""
        # 45-degree polarized source
        src = SourceParams(
            x_mm=-100.0,
            y_mm=0.0,
            angle_deg=0.0,
            n_rays=1,
            ray_length_mm=200.0,
            polarization_type="+45",
        )

        # PBS at 45 degrees
        pbs = OpticalElement(
            kind="bs",
            p1=np.array([0.0, -50.0]),
            p2=np.array([0.0, 50.0]),
            is_polarizing=True,
            pbs_transmission_axis_deg=0.0,  # Horizontal transmission
        )

        paths = trace_rays([pbs], [src])

        # Should have multiple ray paths (transmitted and reflected)
        # The 45-degree input should split into both outputs
        assert len(paths) >= 2
