"""
Test Zemax to OptiVerse converter functionality.
"""

import pytest
from optiverse.services.zemax_parser import ZemaxParser
from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
from optiverse.services.glass_catalog import GlassCatalog


@pytest.fixture
def zemax_data():
    """Load the AC254-100-B Zemax file for testing."""
    parser = ZemaxParser()
    return parser.parse("/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx")


@pytest.fixture
def converter():
    """Create a converter with glass catalog."""
    catalog = GlassCatalog()
    return ZemaxToInterfaceConverter(catalog)


def test_converter_basic(zemax_data, converter):
    """Test basic conversion to ComponentRecord."""
    component = converter.convert(zemax_data)

    assert component is not None
    assert component.name == "AC254-100-B AC254-100-B NEAR IR ACHROMATS: Infinite Conjugate 100"
    assert component.kind == "multi_element"
    assert component.interfaces_v2 is not None
    assert len(component.interfaces_v2) == 3  # 3 optical interfaces (excluding object and image)
    assert abs(component.object_height_mm - 12.7) < 0.1


def test_converter_interface1_entry(zemax_data, converter):
    """Test first interface (S1: Air → N-LAK22)."""
    component = converter.convert(zemax_data)
    iface = component.interfaces_v2[0]

    # Position
    assert abs(iface.x1_mm - 0.0) < 0.01
    assert abs(iface.x2_mm - 0.0) < 0.01

    # Aperture (diameter = 12.7mm → half = 6.35mm)
    assert abs(iface.y1_mm - (-6.35)) < 0.01
    assert abs(iface.y2_mm - 6.35) < 0.01

    # Refractive indices
    assert abs(iface.n1 - 1.0) < 0.01  # Air
    assert abs(iface.n2 - 1.641) < 0.01  # N-LAK22 at 855nm

    # Curvature
    assert iface.is_curved
    assert abs(iface.radius_of_curvature_mm - 66.68) < 0.1

    # Type
    assert iface.element_type == "refractive_interface"


def test_converter_interface2_cemented(zemax_data, converter):
    """Test second interface (S2: N-LAK22 → N-SF6HT)."""
    component = converter.convert(zemax_data)
    iface = component.interfaces_v2[1]

    # Position (0 + 4mm thickness of S1)
    assert abs(iface.x1_mm - 4.0) < 0.01
    assert abs(iface.x2_mm - 4.0) < 0.01

    # Aperture
    assert abs(iface.y1_mm - (-6.35)) < 0.01
    assert abs(iface.y2_mm - 6.35) < 0.01

    # Refractive indices
    assert abs(iface.n1 - 1.641) < 0.01  # N-LAK22
    assert abs(iface.n2 - 1.781) < 0.01  # N-SF6HT at 855nm

    # Curvature (negative = concave from left)
    assert iface.is_curved
    assert abs(iface.radius_of_curvature_mm - (-53.70)) < 0.1


def test_converter_interface3_exit(zemax_data, converter):
    """Test third interface (S3: N-SF6HT → Air)."""
    component = converter.convert(zemax_data)
    iface = component.interfaces_v2[2]

    # Position (4mm + 1.5mm thickness of S2)
    assert abs(iface.x1_mm - 5.5) < 0.01
    assert abs(iface.x2_mm - 5.5) < 0.01

    # Aperture
    assert abs(iface.y1_mm - (-6.35)) < 0.01
    assert abs(iface.y2_mm - 6.35) < 0.01

    # Refractive indices
    assert abs(iface.n1 - 1.781) < 0.01  # N-SF6HT
    assert abs(iface.n2 - 1.0) < 0.01  # Air

    # Curvature (negative = concave from left)
    assert iface.is_curved
    assert abs(iface.radius_of_curvature_mm - (-259.41)) < 1.0


def test_converter_cumulative_positions(zemax_data, converter):
    """Test that interface positions are cumulative (based on thickness)."""
    component = converter.convert(zemax_data)

    # Expected positions:
    # S1: x=0mm
    # S2: x=0+4mm = 4mm
    # S3: x=4+1.5mm = 5.5mm

    assert abs(component.interfaces_v2[0].x1_mm - 0.0) < 0.01
    assert abs(component.interfaces_v2[1].x1_mm - 4.0) < 0.01
    assert abs(component.interfaces_v2[2].x1_mm - 5.5) < 0.01


def test_converter_refractive_index_progression(zemax_data, converter):
    """Test that refractive indices progress correctly through the lens."""
    component = converter.convert(zemax_data)

    # S1: Air (1.0) → N-LAK22 (1.641)
    # S2: N-LAK22 (1.641) → N-SF6HT (1.781)
    # S3: N-SF6HT (1.781) → Air (1.0)

    # Check that n2 of interface i matches n1 of interface i+1
    assert abs(component.interfaces_v2[0].n2 - component.interfaces_v2[1].n1) < 0.01
    assert abs(component.interfaces_v2[1].n2 - component.interfaces_v2[2].n1) < 0.01


def test_converter_all_curved(zemax_data, converter):
    """Test that all interfaces are correctly identified as curved."""
    component = converter.convert(zemax_data)

    for iface in component.interfaces_v2:
        assert iface.is_curved
        assert abs(iface.radius_of_curvature_mm) > 1.0  # Not flat


def test_converter_center_of_curvature(zemax_data, converter):
    """Test center of curvature calculation."""
    component = converter.convert(zemax_data)

    # Interface 1: R=+66.68mm, center should be to the right
    iface1 = component.interfaces_v2[0]
    center_x, center_y = iface1.center_of_curvature_mm()
    assert center_x > iface1.x1_mm  # Center is to the right
    assert abs(center_x - (iface1.x1_mm + 66.68)) < 0.1

    # Interface 2: R=-53.70mm, center should be to the left
    iface2 = component.interfaces_v2[1]
    center_x, center_y = iface2.center_of_curvature_mm()
    assert center_x < iface2.x1_mm  # Center is to the left
    assert abs(center_x - (iface2.x1_mm - 53.70)) < 0.1


def test_converter_surface_sag(zemax_data, converter):
    """Test surface sag calculation for curved surfaces."""
    component = converter.convert(zemax_data)

    # Interface 1: R=+66.68mm, diameter=12.7mm
    iface1 = component.interfaces_v2[0]

    # At center (y=0), sag should be 0
    assert abs(iface1.surface_sag_at_y(0.0)) < 0.01

    # At edge (y=6.35mm), sag should be positive (convex from left)
    sag_edge = iface1.surface_sag_at_y(6.35)
    assert sag_edge > 0  # Convex bulges forward

    # Calculate expected sag: s = R - sqrt(R² - h²)
    R = 66.68
    h = 6.35
    expected_sag = R - (R**2 - h**2)**0.5
    assert abs(sag_edge - expected_sag) < 0.01


def test_converter_notes(zemax_data, converter):
    """Test that converter includes useful notes."""
    component = converter.convert(zemax_data)

    assert component.notes is not None
    assert "Imported from Zemax" in component.notes
    assert "855" in component.notes  # Wavelength in nm


def test_glass_catalog_lookup():
    """Test glass catalog refractive index lookup."""
    catalog = GlassCatalog()

    # Test at 855nm (NIR wavelength from Zemax file)
    n_lak22 = catalog.get_refractive_index("N-LAK22", 0.855)
    n_sf6ht = catalog.get_refractive_index("N-SF6HT", 0.855)

    assert n_lak22 is not None
    assert n_sf6ht is not None
    assert abs(n_lak22 - 1.641) < 0.01
    assert abs(n_sf6ht - 1.781) < 0.01

    # Air should always return 1.0
    assert catalog.get_refractive_index("", 0.855) == 1.0
    assert catalog.get_refractive_index("AIR", 0.855) == 1.0



