"""
Tests for Zemax file import functionality.
"""

import pytest

from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.services.glass_catalog import GlassCatalog
from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
from optiverse.services.zemax_parser import ZemaxFile, ZemaxSurface


class TestZemaxParser:
    """Test Zemax file parsing."""

    def test_zemax_surface_creation(self):
        """Test creating a Zemax surface."""
        surf = ZemaxSurface(number=1, curvature=0.015, thickness=4.0, glass="N-BK7", diameter=12.7)

        assert surf.number == 1
        assert surf.curvature == 0.015
        assert abs(surf.radius_mm - 66.67) < 0.1  # 1/0.015
        assert surf.thickness == 4.0
        assert surf.glass == "N-BK7"
        assert surf.diameter == 12.7
        assert not surf.is_flat

    def test_flat_surface(self):
        """Test flat surface detection."""
        surf = ZemaxSurface(number=1, curvature=0.0)
        assert surf.is_flat
        assert surf.radius_mm == float("inf")

    def test_zemax_file_creation(self):
        """Test creating a Zemax file object."""
        zmx = ZemaxFile(
            name="Test Lens", wavelengths_um=[0.486, 0.5876, 0.656], primary_wavelength_idx=2
        )

        assert zmx.name == "Test Lens"
        assert len(zmx.wavelengths_um) == 3
        assert zmx.primary_wavelength_um == 0.5876


class TestGlassCatalog:
    """Test glass catalog and refractive index calculations."""

    def test_catalog_creation(self):
        """Test creating glass catalog."""
        catalog = GlassCatalog()
        assert len(catalog.list_glasses()) > 0

    def test_bk7_index(self):
        """Test BK7 refractive index."""
        catalog = GlassCatalog()
        n = catalog.get_refractive_index("N-BK7", 0.5876)  # d-line

        assert n is not None
        assert 1.51 < n < 1.52  # BK7 is ~1.517 at d-line

    def test_air_index(self):
        """Test air/vacuum index."""
        catalog = GlassCatalog()

        assert catalog.get_refractive_index("AIR", 0.55) == 1.0
        assert catalog.get_refractive_index("", 0.55) == 1.0
        assert catalog.get_refractive_index("VACUUM", 0.55) == 1.0

    def test_unknown_glass(self):
        """Test unknown glass material."""
        catalog = GlassCatalog()
        n = catalog.get_refractive_index("UNKNOWN_MATERIAL", 0.55)

        assert n is None  # Should return None for unknown


class TestInterfaceDefinition:
    """Test interface definition with curved surfaces."""

    def test_flat_interface(self):
        """Test flat interface."""
        iface = InterfaceDefinition(
            x1_mm=0, y1_mm=-5, x2_mm=0, y2_mm=5, n1=1.0, n2=1.5, is_curved=False
        )

        assert iface.is_flat()
        assert iface.length_mm() == 10.0

    def test_curved_interface(self):
        """Test curved interface."""
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
        assert center_x == 100.0  # R=100, so center at x=0+100=100
        assert center_y == 0.0

    def test_surface_sag(self):
        """Test surface sag calculation."""
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

        # At edge (y=5mm)
        sag = iface.surface_sag_at_y(5.0)
        assert sag > 0  # Convex surface (R>0)
        assert sag < 1.0  # Should be small for this geometry

        # At center (y=0)
        sag_center = iface.surface_sag_at_y(0.0)
        assert abs(sag_center) < 1e-10  # Should be ~0 at center

    def test_serialization(self):
        """Test interface serialization with curvature."""
        iface = InterfaceDefinition(
            x1_mm=0,
            y1_mm=-5,
            x2_mm=0,
            y2_mm=5,
            n1=1.0,
            n2=1.5,
            is_curved=True,
            radius_of_curvature_mm=66.68,
        )

        # Serialize
        data = iface.to_dict()
        assert data["is_curved"]
        assert data["radius_of_curvature_mm"] == 66.68

        # Deserialize
        iface2 = InterfaceDefinition.from_dict(data)
        assert iface2.is_curved
        assert iface2.radius_of_curvature_mm == 66.68


class TestZemaxConverter:
    """Test Zemax to Interface conversion."""

    def test_converter_creation(self):
        """Test creating converter."""
        catalog = GlassCatalog()
        converter = ZemaxToInterfaceConverter(catalog)

        assert converter.catalog is not None

    def test_material_name_generation(self):
        """Test material name generation."""
        catalog = GlassCatalog()
        converter = ZemaxToInterfaceConverter(catalog)

        assert converter._material_name(1.0) == "Air"
        assert "n=" in converter._material_name(1.5)


def test_integration_example():
    """Test complete integration with example data."""
    # Create a simple Zemax file programmatically
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

    # Check first interface
    iface1 = component.interfaces_v2[0]
    assert iface1.n1 == 1.0  # Air
    assert 1.51 < iface1.n2 < 1.52  # BK7
    assert iface1.is_curved
    assert iface1.radius_of_curvature_mm > 0  # Convex


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
