"""
Tests for Zemax import functionality.

These tests verify:
- ZemaxSurface creation and properties
- GlassCatalog refractive index lookup
- Curved interface definition
- Zemax to interface conversion
"""

from __future__ import annotations

from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.services.glass_catalog import GlassCatalog
from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
from optiverse.services.zemax_parser import ZemaxFile, ZemaxSurface


class TestZemaxSurface:
    """Tests for ZemaxSurface class."""

    def test_zemax_surface_creation(self):
        """Test Zemax surface creation."""
        surf = ZemaxSurface(number=1, curvature=0.015, thickness=4.0, glass="N-BK7", diameter=12.7)

        assert surf.number == 1
        assert surf.curvature == 0.015
        assert abs(surf.radius_mm - 66.67) < 0.1
        assert not surf.is_flat

    def test_zemax_surface_flat(self):
        """Test flat Zemax surface (zero curvature)."""
        surf = ZemaxSurface(number=1, curvature=0.0, thickness=2.0, glass="N-BK7", diameter=10.0)

        assert surf.is_flat
        assert surf.curvature == 0.0

    def test_zemax_surface_object(self):
        """Test object surface (surface 0)."""
        surf = ZemaxSurface(number=0)

        assert surf.number == 0


class TestGlassCatalog:
    """Tests for GlassCatalog class."""

    def test_bk7_refractive_index(self):
        """Test BK7 refractive index lookup."""
        catalog = GlassCatalog()

        n_bk7 = catalog.get_refractive_index("N-BK7", 0.5876)
        assert n_bk7 is not None
        assert 1.51 < n_bk7 < 1.52

    def test_air_refractive_index(self):
        """Test air refractive index (empty glass name)."""
        catalog = GlassCatalog()

        n_air = catalog.get_refractive_index("", 0.55)
        assert n_air == 1.0

    def test_unknown_glass(self):
        """Test unknown glass name returns None or default."""
        catalog = GlassCatalog()

        result = catalog.get_refractive_index("UNKNOWN_GLASS_123", 0.55)
        # Should return None or a default value
        assert result is None or result == 1.0

    def test_sf11_refractive_index(self):
        """Test SF11 glass refractive index."""
        catalog = GlassCatalog()

        n_sf11 = catalog.get_refractive_index("N-SF11", 0.5876)
        # SF11 is a dense flint glass with high index
        if n_sf11 is not None:
            assert n_sf11 > 1.7


class TestCurvedInterface:
    """Tests for curved interface definitions."""

    def test_curved_interface_creation(self):
        """Test curved interface definition creation."""
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

    def test_curved_interface_center_of_curvature(self):
        """Test center of curvature calculation."""
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

        center_x, center_y = iface.center_of_curvature_mm()
        assert center_x == 100.0

    def test_curved_interface_surface_sag(self):
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

        sag = iface.surface_sag_at_y(5.0)
        assert sag > 0  # Convex

    def test_curved_interface_serialization(self):
        """Test curved interface serialization round-trip."""
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

        data = iface.to_dict()
        assert data["is_curved"]
        assert data["radius_of_curvature_mm"] == 100.0

        iface2 = InterfaceDefinition.from_dict(data)
        assert iface2.is_curved
        assert iface2.radius_of_curvature_mm == 100.0


class TestZemaxConverter:
    """Tests for Zemax to Interface conversion."""

    def test_zemax_converter_basic(self):
        """Test Zemax to Interface conversion."""
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

    def test_zemax_converter_first_interface(self):
        """Test first interface properties after conversion."""
        zmx = ZemaxFile(name="Test Lens", wavelengths_um=[0.5876], primary_wavelength_idx=1)

        zmx.surfaces = [
            ZemaxSurface(number=0),
            ZemaxSurface(number=1, curvature=0.015, thickness=4.0, glass="N-BK7", diameter=12.7),
            ZemaxSurface(number=2, curvature=-0.02, thickness=100.0, glass="", diameter=12.7),
            ZemaxSurface(number=3),
        ]

        catalog = GlassCatalog()
        converter = ZemaxToInterfaceConverter(catalog)
        component = converter.convert(zmx)

        # Check first interface
        iface1 = component.interfaces_v2[0]
        assert iface1.n1 == 1.0  # Air
        assert 1.51 < iface1.n2 < 1.52  # BK7
        assert iface1.is_curved
        assert iface1.radius_of_curvature_mm > 0  # Convex

    def test_zemax_converter_empty_file(self):
        """Test converter with minimal Zemax file."""
        zmx = ZemaxFile(name="Empty", wavelengths_um=[0.55], primary_wavelength_idx=1)
        zmx.surfaces = [
            ZemaxSurface(number=0),  # Object
            ZemaxSurface(number=1),  # Image
        ]

        catalog = GlassCatalog()
        converter = ZemaxToInterfaceConverter(catalog)
        component = converter.convert(zmx)

        assert component.name == "Empty"
        # With only object and image surfaces, no optical interfaces
        assert len(component.interfaces_v2) == 0
