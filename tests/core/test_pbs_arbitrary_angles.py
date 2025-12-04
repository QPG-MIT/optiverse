"""
Test PBS (Polarizing Beam Splitter) functionality at arbitrary angles.

Physics background:
- A PBS has a transmission axis that defines which polarization passes through
- p-polarization (parallel to transmission axis) is transmitted
- s-polarization (perpendicular to transmission axis) is reflected
- For polarization at angle θ to transmission axis:
  - Transmitted intensity = cos²(θ)
  - Reflected intensity = sin²(θ)
- The transmission axis rotates with the PBS element
"""

import numpy as np

from optiverse.core.models import Polarization, SourceParams
from optiverse.core.raytracing_math import transform_polarization_beamsplitter
from optiverse.data import BeamsplitterProperties, LineSegment, OpticalInterface
from optiverse.integration import create_polymorphic_element
from optiverse.raytracing import trace_rays_polymorphic


def _create_pbs(pbs_axis_deg: float):
    """Create a PBS element with specified transmission axis."""
    geom = LineSegment(np.array([0.0, -50.0]), np.array([0.0, 50.0]))
    props = BeamsplitterProperties(
        transmission=0.5,
        reflection=0.5,
        is_polarizing=True,
        polarization_axis_deg=pbs_axis_deg,
    )
    iface = OpticalInterface(geometry=geom, properties=props)
    return create_polymorphic_element(iface)


class TestPBSArbitraryAngles:
    """Test PBS functionality at various angles."""

    def test_pbs_horizontal_axis_horizontal_input(self):
        """PBS with horizontal transmission axis + horizontal input → 100% transmission."""
        # Create horizontal polarized source
        src = SourceParams(
            x_mm=-100.0,
            y_mm=0.0,
            angle_deg=0.0,
            n_rays=1,
            spread_deg=0.0,
            polarization_type="horizontal",
        )

        pbs = _create_pbs(0.0)  # Horizontal transmission axis
        paths = trace_rays_polymorphic([pbs], [src])

        # Should have 1 path (transmitted), no reflected path
        assert len(paths) == 1, f"Expected 1 path (transmitted), got {len(paths)}"
        # The transmitted path should have high intensity
        assert len(paths[0].points) >= 2, "Path should have at least 2 points"

    def test_pbs_horizontal_axis_vertical_input(self):
        """PBS with horizontal transmission axis + vertical input → 100% reflection."""
        src = SourceParams(
            x_mm=-100.0,
            y_mm=0.0,
            angle_deg=0.0,
            n_rays=1,
            spread_deg=0.0,
            polarization_type="vertical",
        )

        pbs = _create_pbs(0.0)  # Horizontal transmission axis
        paths = trace_rays_polymorphic([pbs], [src])

        # Should have 1 path (reflected), no transmitted path
        assert len(paths) == 1, f"Expected 1 path (reflected), got {len(paths)}"

    def test_pbs_horizontal_axis_45deg_input(self):
        """PBS with horizontal transmission axis + 45° input → 50/50 split."""
        src = SourceParams(
            x_mm=-100.0, y_mm=0.0, angle_deg=0.0, n_rays=1, spread_deg=0.0, polarization_type="+45"
        )

        pbs = _create_pbs(0.0)  # Horizontal transmission axis
        paths = trace_rays_polymorphic([pbs], [src])

        # Should have 2 paths (50% transmitted, 50% reflected)
        assert len(paths) == 2, f"Expected 2 paths (50/50 split), got {len(paths)}"

    def test_pbs_30deg_axis_30deg_input(self):
        """PBS with 30° transmission axis + 30° input → 100% transmission."""
        src = SourceParams(
            x_mm=-100.0,
            y_mm=0.0,
            angle_deg=0.0,
            n_rays=1,
            spread_deg=0.0,
            polarization_type="linear",
            polarization_angle_deg=30.0,
        )

        pbs = _create_pbs(30.0)  # 30° transmission axis
        paths = trace_rays_polymorphic([pbs], [src])

        # Should have 1 path (transmitted) - polarization aligned with axis
        assert len(paths) == 1, f"Expected 1 path (transmitted), got {len(paths)}"

    def test_pbs_30deg_axis_120deg_input(self):
        """PBS with 30° transmission axis + 120° input (perpendicular) → 100% reflection."""
        src = SourceParams(
            x_mm=-100.0,
            y_mm=0.0,
            angle_deg=0.0,
            n_rays=1,
            spread_deg=0.0,
            polarization_type="linear",
            polarization_angle_deg=120.0,  # 90° from 30° axis
        )

        pbs = _create_pbs(30.0)  # 30° transmission axis
        paths = trace_rays_polymorphic([pbs], [src])

        # Should have 1 path (reflected) - polarization perpendicular to axis
        assert len(paths) == 1, f"Expected 1 path (reflected), got {len(paths)}"

    def test_pbs_60deg_axis_30deg_input_cosine_squared_law(self):
        """PBS at 60° with 30° input → verify cos²(θ) law for intensity."""
        # Angle difference = 30°, so cos²(30°) ≈ 0.75, sin²(30°) ≈ 0.25
        src = SourceParams(
            x_mm=-100.0,
            y_mm=0.0,
            angle_deg=0.0,
            n_rays=1,
            spread_deg=0.0,
            polarization_type="linear",
            polarization_angle_deg=30.0,
        )

        pbs = _create_pbs(60.0)  # 60° transmission axis
        paths = trace_rays_polymorphic([pbs], [src])

        # Should have 2 paths with intensity ratio ~3:1
        assert len(paths) == 2, f"Expected 2 paths, got {len(paths)}"

        # Calculate intensities from alpha channel (normalized to 1.0)
        intensities = [p.rgba[3] / 255.0 for p in paths]
        intensities.sort(reverse=True)  # [higher, lower]

        # Expected: cos²(30°) ≈ 0.75, sin²(30°) ≈ 0.25
        expected_high = np.cos(np.deg2rad(30)) ** 2
        expected_low = np.sin(np.deg2rad(30)) ** 2

        assert (
            abs(intensities[0] - expected_high) < 0.1
        ), f"Expected high intensity {expected_high:.3f}, got {intensities[0]:.3f}"
        assert (
            abs(intensities[1] - expected_low) < 0.1
        ), f"Expected low intensity {expected_low:.3f}, got {intensities[1]:.3f}"


class TestPBSPolarizationTransform:
    """Test the polarization transformation function directly."""

    def test_transform_horizontal_through_horizontal_axis(self):
        """Horizontal polarization through PBS with horizontal axis."""
        pol_in = Polarization.horizontal()
        v_in = np.array([1.0, 0.0])
        n_hat = np.array([0.0, 1.0])
        t_hat = np.array([1.0, 0.0])

        # Transmitted beam
        pol_t, int_t = transform_polarization_beamsplitter(
            pol_in,
            v_in,
            n_hat,
            t_hat,
            is_polarizing=True,
            pbs_axis_deg=0.0,  # Horizontal axis
            is_transmitted=True,
        )

        # Reflected beam
        pol_r, int_r = transform_polarization_beamsplitter(
            pol_in, v_in, n_hat, t_hat, is_polarizing=True, pbs_axis_deg=0.0, is_transmitted=False
        )

        # Horizontal input + horizontal axis → 100% transmission, 0% reflection
        assert abs(int_t - 1.0) < 1e-6, f"Expected transmission intensity 1.0, got {int_t}"
        assert abs(int_r - 0.0) < 1e-6, f"Expected reflection intensity 0.0, got {int_r}"

        # Total intensity should be conserved
        assert abs((int_t + int_r) - 1.0) < 1e-6, "Intensity not conserved"

    def test_transform_vertical_through_horizontal_axis(self):
        """Vertical polarization through PBS with horizontal axis."""
        pol_in = Polarization.vertical()
        v_in = np.array([1.0, 0.0])
        n_hat = np.array([0.0, 1.0])
        t_hat = np.array([1.0, 0.0])

        pol_t, int_t = transform_polarization_beamsplitter(
            pol_in,
            v_in,
            n_hat,
            t_hat,
            is_polarizing=True,
            pbs_axis_deg=0.0,  # Horizontal axis
            is_transmitted=True,
        )

        pol_r, int_r = transform_polarization_beamsplitter(
            pol_in, v_in, n_hat, t_hat, is_polarizing=True, pbs_axis_deg=0.0, is_transmitted=False
        )

        # Vertical input + horizontal axis → 0% transmission, 100% reflection
        assert abs(int_t - 0.0) < 1e-6, f"Expected transmission intensity 0.0, got {int_t}"
        assert abs(int_r - 1.0) < 1e-6, f"Expected reflection intensity 1.0, got {int_r}"
        assert abs((int_t + int_r) - 1.0) < 1e-6, "Intensity not conserved"

    def test_transform_45deg_through_horizontal_axis(self):
        """45° polarization through PBS with horizontal axis."""
        pol_in = Polarization.diagonal_plus_45()
        v_in = np.array([1.0, 0.0])
        n_hat = np.array([0.0, 1.0])
        t_hat = np.array([1.0, 0.0])

        pol_t, int_t = transform_polarization_beamsplitter(
            pol_in,
            v_in,
            n_hat,
            t_hat,
            is_polarizing=True,
            pbs_axis_deg=0.0,  # Horizontal axis
            is_transmitted=True,
        )

        pol_r, int_r = transform_polarization_beamsplitter(
            pol_in, v_in, n_hat, t_hat, is_polarizing=True, pbs_axis_deg=0.0, is_transmitted=False
        )

        # 45° input → 50% transmission, 50% reflection
        assert abs(int_t - 0.5) < 1e-6, f"Expected transmission intensity 0.5, got {int_t}"
        assert abs(int_r - 0.5) < 1e-6, f"Expected reflection intensity 0.5, got {int_r}"
        assert abs((int_t + int_r) - 1.0) < 1e-6, "Intensity not conserved"

    def test_transform_30deg_input_60deg_axis(self):
        """Test cos²/sin² law: 30° input through 60° axis."""
        pol_in = Polarization.linear(30.0)
        v_in = np.array([1.0, 0.0])
        n_hat = np.array([0.0, 1.0])
        t_hat = np.array([1.0, 0.0])

        pol_t, int_t = transform_polarization_beamsplitter(
            pol_in, v_in, n_hat, t_hat, is_polarizing=True, pbs_axis_deg=60.0, is_transmitted=True
        )

        pol_r, int_r = transform_polarization_beamsplitter(
            pol_in, v_in, n_hat, t_hat, is_polarizing=True, pbs_axis_deg=60.0, is_transmitted=False
        )

        # Angle difference = 30°
        # Transmitted = cos²(30°) = 0.75
        # Reflected = sin²(30°) = 0.25
        expected_t = np.cos(np.deg2rad(30)) ** 2
        expected_r = np.sin(np.deg2rad(30)) ** 2

        assert (
            abs(int_t - expected_t) < 1e-6
        ), f"Expected transmission {expected_t:.6f}, got {int_t:.6f}"
        assert (
            abs(int_r - expected_r) < 1e-6
        ), f"Expected reflection {expected_r:.6f}, got {int_r:.6f}"
        assert abs((int_t + int_r) - 1.0) < 1e-6, "Intensity not conserved"

    def test_arbitrary_angles_intensity_conservation(self):
        """Test that intensity is conserved for arbitrary angles."""
        test_cases = [
            (0, 0),  # Horizontal input, horizontal axis
            (0, 45),  # Horizontal input, 45° axis
            (0, 90),  # Horizontal input, vertical axis
            (30, 60),  # 30° input, 60° axis
            (45, 15),  # 45° input, 15° axis
            (75, 120),  # 75° input, 120° axis
            (90, 0),  # Vertical input, horizontal axis
            (135, 45),  # 135° input, 45° axis
        ]

        v_in = np.array([1.0, 0.0])
        n_hat = np.array([0.0, 1.0])
        t_hat = np.array([1.0, 0.0])

        for pol_angle, axis_angle in test_cases:
            pol_in = Polarization.linear(pol_angle)

            pol_t, int_t = transform_polarization_beamsplitter(
                pol_in,
                v_in,
                n_hat,
                t_hat,
                is_polarizing=True,
                pbs_axis_deg=axis_angle,
                is_transmitted=True,
            )

            pol_r, int_r = transform_polarization_beamsplitter(
                pol_in,
                v_in,
                n_hat,
                t_hat,
                is_polarizing=True,
                pbs_axis_deg=axis_angle,
                is_transmitted=False,
            )

            total_intensity = int_t + int_r
            assert abs(total_intensity - 1.0) < 1e-6, (
                f"Intensity not conserved for pol={pol_angle}°, axis={axis_angle}°: "
                f"T={int_t:.6f}, R={int_r:.6f}, total={total_intensity:.6f}"
            )

    def test_malus_law_verification(self):
        """Verify Malus's Law: I = I₀ cos²(θ) for various angles."""
        v_in = np.array([1.0, 0.0])
        n_hat = np.array([0.0, 1.0])
        t_hat = np.array([1.0, 0.0])

        # Test for 0° to 90° in 15° increments
        for angle_diff in range(0, 91, 15):
            pol_in = Polarization.linear(0.0)  # Horizontal input
            axis_angle = float(angle_diff)

            pol_t, int_t = transform_polarization_beamsplitter(
                pol_in,
                v_in,
                n_hat,
                t_hat,
                is_polarizing=True,
                pbs_axis_deg=axis_angle,
                is_transmitted=True,
            )

            expected = np.cos(np.deg2rad(angle_diff)) ** 2
            assert (
                abs(int_t - expected) < 1e-6
            ), f"Malus's Law violation at {angle_diff}°: expected {expected:.6f}, got {int_t:.6f}"
