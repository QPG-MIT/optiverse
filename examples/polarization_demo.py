#!/usr/bin/env python3
"""
Polarization Demo - Demonstrates the polarization features in Optiverse

This script shows how to:
1. Create sources with different polarization states
2. Set up a Polarizing Beam Splitter (PBS)
3. Trace rays and examine their polarization states
"""

import os
import sys

import numpy as np

# Add src to path if running standalone
root = os.path.dirname(os.path.dirname(__file__))
src = os.path.join(root, "src")
if os.path.isdir(src) and src not in sys.path:
    sys.path.insert(0, src)

# Import after path manipulation (required for standalone execution)
from optiverse.core.models import (  # noqa: E402
    Polarization,
    SourceParams,
)


def demo_polarization_states():
    """Demonstrate different polarization states."""
    print("=" * 60)
    print("POLARIZATION STATES DEMO")
    print("=" * 60)

    states = [
        ("Horizontal", Polarization.horizontal()),
        ("Vertical", Polarization.vertical()),
        ("+45° Linear", Polarization.diagonal_plus_45()),
        ("-45° Linear", Polarization.diagonal_minus_45()),
        ("Right Circular", Polarization.circular_right()),
        ("Left Circular", Polarization.circular_left()),
        ("30° Linear", Polarization.linear(30.0)),
    ]

    for name, pol in states:
        jones = pol.jones_vector
        intensity = pol.intensity()
        print(f"\n{name}:")
        print(f"  Jones vector: [{jones[0]:.3f}, {jones[1]:.3f}]")
        print(f"  Intensity: {intensity:.3f}")

        # Show real and imaginary parts for complex values
        if abs(jones[0].imag) > 1e-6 or abs(jones[1].imag) > 1e-6:
            print(f"  Ex: {jones[0].real:.3f} + {jones[0].imag:.3f}j")
            print(f"  Ey: {jones[1].real:.3f} + {jones[1].imag:.3f}j")


def demo_source_configuration():
    """Demonstrate source polarization configuration."""
    print("\n" + "=" * 60)
    print("SOURCE POLARIZATION CONFIGURATION")
    print("=" * 60)

    configs = [
        ("Default (horizontal)", {"polarization_type": "horizontal"}),
        ("Vertical", {"polarization_type": "vertical"}),
        ("+45°", {"polarization_type": "+45"}),
        ("Circular right", {"polarization_type": "circular_right"}),
        ("30° linear", {"polarization_type": "linear", "polarization_angle_deg": 30.0}),
        (
            "Custom Jones",
            {"use_custom_jones": True, "custom_jones_ex_real": 1.0, "custom_jones_ey_imag": 1.0},
        ),
    ]

    for name, kwargs in configs:
        src = SourceParams(**kwargs)
        pol = src.get_polarization()
        print(f"\n{name}:")
        print(f"  Jones vector: {pol.jones_vector}")
        print(f"  Type setting: {src.polarization_type}")
        if src.polarization_type == "linear":
            print(f"  Angle: {src.polarization_angle_deg}°")


def demo_pbs_simulation():
    """Demonstrate PBS behavior with different input polarizations."""
    print("\n" + "=" * 60)
    print("POLARIZING BEAM SPLITTER (PBS) SIMULATION")
    print("=" * 60)

    from optiverse.core.geometry import transform_polarization_beamsplitter

    # PBS with horizontal transmission axis
    pbs_axis = 0.0

    test_cases = [
        ("Horizontal input", Polarization.horizontal()),
        ("Vertical input", Polarization.vertical()),
        ("+45° input", Polarization.diagonal_plus_45()),
        ("Circular input", Polarization.circular_right()),
    ]

    v_in = np.array([1.0, 0.0])  # Ray direction
    n_hat = np.array([0.0, 1.0])  # Surface normal
    t_hat = np.array([1.0, 0.0])  # Surface tangent

    for name, pol_in in test_cases:
        print(f"\n{name}:")
        print(f"  Input Jones: {pol_in.jones_vector}")
        print(f"  Input intensity: {pol_in.intensity():.3f}")

        # Transmitted beam
        pol_t, int_t = transform_polarization_beamsplitter(
            pol_in,
            v_in,
            n_hat,
            t_hat,
            is_polarizing=True,
            pbs_axis_deg=pbs_axis,
            is_transmitted=True,
        )

        # Reflected beam
        pol_r, int_r = transform_polarization_beamsplitter(
            pol_in,
            v_in,
            n_hat,
            t_hat,
            is_polarizing=True,
            pbs_axis_deg=pbs_axis,
            is_transmitted=False,
        )

        print("  Transmitted:")
        print(f"    Jones: {pol_t.jones_vector}")
        print(f"    Intensity factor: {int_t:.3f}")
        print("  Reflected:")
        print(f"    Jones: {pol_r.jones_vector}")
        print(f"    Intensity factor: {int_r:.3f}")
        print(f"  Total intensity: {int_t + int_r:.3f} (should be ~1.0)")


def demo_mirror_reflection():
    """Demonstrate mirror polarization transformation."""
    print("\n" + "=" * 60)
    print("MIRROR REFLECTION POLARIZATION TRANSFORMATION")
    print("=" * 60)

    from optiverse.core.geometry import transform_polarization_mirror

    # Vertical mirror
    v_in = np.array([1.0, 0.0])  # Ray traveling right
    n_hat = np.array([1.0, 0.0])  # Mirror normal pointing right

    test_cases = [
        ("Horizontal (s-polarization)", Polarization.horizontal()),
        ("Vertical (p-polarization)", Polarization.vertical()),
        ("+45°", Polarization.diagonal_plus_45()),
    ]

    for name, pol_in in test_cases:
        pol_out = transform_polarization_mirror(pol_in, v_in, n_hat)

        print(f"\n{name}:")
        print(f"  Input Jones: {pol_in.jones_vector}")
        print(f"  Output Jones: {pol_out.jones_vector}")
        print(f"  Intensity preserved: {np.isclose(pol_in.intensity(), pol_out.intensity())}")


def demo_serialization():
    """Demonstrate polarization serialization."""
    print("\n" + "=" * 60)
    print("POLARIZATION SERIALIZATION")
    print("=" * 60)

    # Create a complex polarization state
    pol = Polarization(np.array([1.0 + 0.5j, 0.8 - 0.3j], dtype=complex))
    print("\nOriginal polarization:")
    print(f"  Jones vector: {pol.jones_vector}")

    # Serialize
    data = pol.to_dict()
    print("\nSerialized data:")
    for key, val in data.items():
        print(f"  {key}: {val}")

    # Deserialize
    pol_restored = Polarization.from_dict(data)
    print("\nRestored polarization:")
    print(f"  Jones vector: {pol_restored.jones_vector}")

    # Verify
    match = np.allclose(pol.jones_vector, pol_restored.jones_vector)
    print(f"\nSerialization successful: {match}")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "OPTIVERSE POLARIZATION DEMO" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        demo_polarization_states()
        demo_source_configuration()
        demo_pbs_simulation()
        demo_mirror_reflection()
        demo_serialization()

        print("\n" + "=" * 60)
        print("All demos completed successfully! ✓")
        print("=" * 60)
        print("\nTo use polarization in the GUI:")
        print("1. Double-click a source to set its polarization")
        print("2. Double-click a beamsplitter to enable PBS mode")
        print("3. Enable ray tracing to see the results")
        print("\n")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
