"""
Simple direct test of Zemax import functionality (no pytest/numpy issues).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.services.glass_catalog import GlassCatalog
from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
from optiverse.services.zemax_parser import ZemaxFile, ZemaxSurface


def test_zemax_surface():
    """Test Zemax surface creation."""
    print("Testing ZemaxSurface...")
    surf = ZemaxSurface(number=1, curvature=0.015, thickness=4.0, glass="N-BK7", diameter=12.7)

    assert surf.number == 1
    assert surf.curvature == 0.015
    assert abs(surf.radius_mm - 66.67) < 0.1
    assert not surf.is_flat
    print("  ✓ ZemaxSurface works")


def test_glass_catalog():
    """Test glass catalog."""
    print("Testing GlassCatalog...")
    catalog = GlassCatalog()

    # Test BK7
    n_bk7 = catalog.get_refractive_index("N-BK7", 0.5876)
    assert n_bk7 is not None
    assert 1.51 < n_bk7 < 1.52
    print(f"  ✓ BK7 index: {n_bk7:.4f}")

    # Test air
    n_air = catalog.get_refractive_index("", 0.55)
    assert n_air == 1.0
    print(f"  ✓ Air index: {n_air:.4f}")

    print("  ✓ GlassCatalog works")


def test_curved_interface():
    """Test curved interface definition."""
    print("Testing curved InterfaceDefinition...")
    iface = InterfaceDefinition(
        x1_mm=0,
        y1_mm=-5,
        x2_mm=0,
        y2_mm=5,
        n1=1.0,
        n2=1.5,
        is_curved=True,
        radius_of_curvature_mm=100.0,
    )

    assert not iface.is_flat()
    assert iface.radius_of_curvature_mm == 100.0

    # Test center of curvature
    center_x, center_y = iface.center_of_curvature_mm()
    assert center_x == 100.0
    print(f"  ✓ Center of curvature: ({center_x:.1f}, {center_y:.1f})")

    # Test surface sag
    sag = iface.surface_sag_at_y(5.0)
    assert sag > 0  # Convex
    print(f"  ✓ Surface sag at edge: {sag:.4f} mm")

    # Test serialization
    data = iface.to_dict()
    assert data["is_curved"]
    assert data["radius_of_curvature_mm"] == 100.0

    iface2 = InterfaceDefinition.from_dict(data)
    assert iface2.is_curved
    assert iface2.radius_of_curvature_mm == 100.0
    print("  ✓ Serialization works")

    print("  ✓ Curved InterfaceDefinition works")


def test_zemax_converter():
    """Test Zemax to Interface conversion."""
    print("Testing ZemaxToInterfaceConverter...")

    # Create a simple Zemax file
    zmx = ZemaxFile(name="Test Doublet", wavelengths_um=[0.5876], primary_wavelength_idx=1)

    # Add surfaces
    zmx.surfaces = [
        ZemaxSurface(number=0),  # Object
        ZemaxSurface(number=1, curvature=0.015, thickness=4.0, glass="N-BK7", diameter=12.7),
        ZemaxSurface(number=2, curvature=-0.02, thickness=1.5, glass="N-SF11", diameter=12.7),
        ZemaxSurface(number=3, curvature=-0.004, thickness=100.0, glass="", diameter=12.7),
        ZemaxSurface(number=4),  # Image
    ]

    # Convert
    catalog = GlassCatalog()
    converter = ZemaxToInterfaceConverter(catalog)
    component = converter.convert(zmx)

    # Verify
    assert component.name == "Test Doublet"
    assert component.kind == "multi_element"
    assert component.object_height_mm == 12.7
    assert len(component.interfaces_v2) == 3
    print(f"  ✓ Converted to {len(component.interfaces_v2)} interfaces")

    # Check first interface
    iface1 = component.interfaces_v2[0]
    assert iface1.n1 == 1.0  # Air
    assert 1.51 < iface1.n2 < 1.52  # BK7
    assert iface1.is_curved
    assert iface1.radius_of_curvature_mm > 0  # Convex
    print(
        f"  ✓ Interface 1: n={iface1.n1:.3f}→{iface1.n2:.3f}, "
        f"R={iface1.radius_of_curvature_mm:.1f}mm"
    )

    print("  ✓ ZemaxToInterfaceConverter works")


def main():
    """Run all tests."""
    print("=" * 70)
    print("ZEMAX IMPORT FUNCTIONALITY TESTS")
    print("=" * 70)
    print()

    try:
        test_zemax_surface()
        print()
        test_glass_catalog()
        print()
        test_curved_interface()
        print()
        test_zemax_converter()
        print()
        print("=" * 70)
        print("ALL TESTS PASSED! ✓")
        print("=" * 70)
        return 0
    except Exception as e:
        print()
        print("=" * 70)
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
