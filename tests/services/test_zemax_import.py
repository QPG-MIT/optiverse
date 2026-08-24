"""
Tests for Zemax file import functionality.
"""

import math
import textwrap

import pytest

from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.services.glass_catalog import GlassCatalog
from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
from optiverse.services.zemax_parser import ZemaxFile, ZemaxParser, ZemaxSurface


def _parse_zmx_text(text: str) -> ZemaxFile:
    """Helper: feed an in-memory .zmx string through ZemaxParser."""
    parser = ZemaxParser()
    return parser._parse_lines(textwrap.dedent(text).splitlines(keepends=True))


class TestZemaxParser:
    """Test Zemax file parsing."""

    def test_zemax_surface_creation(self):
        """Test creating a Zemax surface."""
        surf = ZemaxSurface(
            number=1, curvature=0.015, thickness=4.0, glass="N-BK7", semi_diameter_mm=12.7
        )

        assert surf.number == 1
        assert surf.curvature == 0.015
        assert abs(surf.radius_mm - 66.67) < 0.1  # 1/0.015
        assert surf.thickness == 4.0
        assert surf.glass == "N-BK7"
        assert surf.semi_diameter_mm == 12.7
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

    # Add surfaces — DIAM in Zemax is the *semi*-diameter, so a 1" achromat
    # has semi_diameter_mm = 12.7 (full aperture = 25.4 mm).
    zmx.surfaces = [
        ZemaxSurface(number=0),  # Object
        ZemaxSurface(
            number=1, curvature=0.015, thickness=4.0, glass="N-BK7", semi_diameter_mm=12.7
        ),
        ZemaxSurface(
            number=2, curvature=-0.02, thickness=1.5, glass="N-SF11", semi_diameter_mm=12.7
        ),
        ZemaxSurface(
            number=3, curvature=-0.004, thickness=100.0, glass="", semi_diameter_mm=12.7
        ),
        ZemaxSurface(number=4),  # Image
    ]

    # Convert
    catalog = GlassCatalog()
    converter = ZemaxToInterfaceConverter(catalog)
    component = converter.convert(zmx)

    # Verify
    assert component.name == "Test Doublet"
    # 1" achromat should import as 25.4 mm tall, not 12.7 mm.
    assert component.object_height_mm == 25.4
    assert len(component.interfaces) == 3

    # Check first interface
    iface1 = component.interfaces[0]
    assert iface1.n1 == 1.0  # Air
    assert 1.51 < iface1.n2 < 1.52  # BK7
    assert iface1.is_curved
    assert iface1.radius_of_curvature_mm > 0  # Convex
    # Interface should span the full clear aperture: y from -12.7 to +12.7 mm.
    assert iface1.y1_mm == pytest.approx(-12.7)
    assert iface1.y2_mm == pytest.approx(12.7)
    assert iface1.length_mm() == pytest.approx(25.4)


class TestUnitParsing:
    """UNIT card scales all lengths so downstream code sees mm."""

    def test_default_unit_is_mm(self):
        zmx = _parse_zmx_text(
            """\
            MODE SEQ
            SURF 0
              TYPE STANDARD
              CURV 0
              DISZ INFINITY
            SURF 1
              TYPE STANDARD
              CURV 0.01
              DISZ 5.0
              DIAM 12.7
            """
        )
        s1 = zmx.surfaces[1]
        assert s1.curvature == pytest.approx(0.01)  # 1/mm
        assert s1.thickness == pytest.approx(5.0)
        assert s1.semi_diameter_mm == pytest.approx(12.7)

    def test_unit_cm_scales_lengths(self):
        zmx = _parse_zmx_text(
            """\
            MODE SEQ
            UNIT CM X W X CM MR CPMM
            SURF 0
              TYPE STANDARD
              DISZ INFINITY
            SURF 1
              TYPE STANDARD
              CURV 0.1
              DISZ 0.5
              DIAM 1.27
            """
        )
        s1 = zmx.surfaces[1]
        # 1 cm = 10 mm: lengths × 10, curvatures / 10
        assert s1.curvature == pytest.approx(0.01)  # 0.1/cm = 0.01/mm
        assert s1.thickness == pytest.approx(5.0)  # 0.5 cm = 5 mm
        assert s1.semi_diameter_mm == pytest.approx(12.7)  # 1.27 cm = 12.7 mm

    def test_unit_inches_converts_to_mm(self):
        zmx = _parse_zmx_text(
            """\
            MODE SEQ
            UNIT IN X W X CM MR CPMM
            ENPD 1.0
            SURF 0
              TYPE STANDARD
              DISZ INFINITY
            SURF 1
              TYPE STANDARD
              CURV 0.0254
              DISZ 0.157480315
              DIAM 0.5
            """
        )
        s1 = zmx.surfaces[1]
        # 1 in = 25.4 mm
        assert s1.curvature == pytest.approx(0.001, rel=1e-3)  # 0.0254/in → 0.001/mm
        assert s1.thickness == pytest.approx(4.0, rel=1e-3)  # 0.1575 in → 4.0 mm
        assert s1.semi_diameter_mm == pytest.approx(12.7)  # 0.5 in semi-d → 12.7 mm
        assert zmx.entrance_pupil_diameter == pytest.approx(25.4)  # 1 in → 25.4 mm

    def test_unknown_unit_falls_back_to_mm(self):
        zmx = _parse_zmx_text(
            """\
            MODE SEQ
            UNIT BOGUS X
            SURF 0
              DISZ INFINITY
            SURF 1
              CURV 0.01
              DISZ 3.0
              DIAM 5.0
            """
        )
        s1 = zmx.surfaces[1]
        assert s1.thickness == pytest.approx(3.0)
        assert s1.semi_diameter_mm == pytest.approx(5.0)

    def test_inch_units_end_to_end_through_converter(self):
        """An inch-unit prescription imports at the right physical size."""
        zmx = _parse_zmx_text(
            """\
            MODE SEQ
            UNIT IN X W X CM MR CPMM
            WAVM 1 0.5876 1
            PWAV 1
            SURF 0
              TYPE STANDARD
              DISZ INFINITY
            SURF 1
              TYPE STANDARD
              CURV 0.005905512
              DISZ 0.157480315
              GLAS N-BK7
              DIAM 0.5
            SURF 2
              TYPE STANDARD
              CURV -0.005905512
              DISZ 4.0
              DIAM 0.5
            SURF 3
              TYPE STANDARD
              CURV 0
              DISZ 0
              DIAM 0.0001
            """
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        # 1" lens (semi_d = 0.5 in = 12.7 mm) → full aperture 25.4 mm
        assert component.object_height_mm == pytest.approx(25.4, abs=0.01)
        # 4 mm centre thickness preserved
        assert len(component.interfaces) == 2
        assert component.interfaces[1].x1_mm == pytest.approx(4.0, abs=0.01)


class TestMirrorHandling:
    """``GLAS MIRROR`` produces a mirror element and flips axis direction."""

    def _fold_mirror_zmx(self) -> ZemaxFile:
        # Lens at x=0, fold mirror at x=20 mm, then 30 mm back to detector.
        # After the mirror the propagation direction flips, so the detector
        # plane lands at x = 20 - 30 = -10 mm in unfolded coordinates.
        return _parse_zmx_text(
            """\
            MODE SEQ
            UNIT MM X W X CM MR CPMM
            WAVM 1 0.5876 1
            PWAV 1
            SURF 0
              TYPE STANDARD
              DISZ INFINITY
            SURF 1
              TYPE STANDARD
              CURV 0.01
              DISZ 5.0
              GLAS N-BK7
              DIAM 12.7
            SURF 2
              TYPE STANDARD
              CURV 0
              DISZ 15.0
              DIAM 12.7
            SURF 3
              TYPE STANDARD
              CURV 0
              DISZ 30.0
              GLAS MIRROR
              DIAM 25.0
            SURF 4
              TYPE STANDARD
              CURV 0
              DISZ 0
              DIAM 0.0001
            """
        )

    def test_mirror_glass_becomes_mirror_element(self):
        zmx = self._fold_mirror_zmx()
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        mirror_ifaces = [i for i in component.interfaces if i.element_type == "mirror"]
        assert len(mirror_ifaces) == 1
        assert mirror_ifaces[0].reflectivity == pytest.approx(100.0)

    def test_mirror_flips_subsequent_position_direction(self):
        zmx = self._fold_mirror_zmx()
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        # S1 at x=0, S2 at x=5 (S1 thickness), mirror S3 at x=5+15=20, then
        # direction flips. No surfaces after the mirror emit interfaces (S4
        # is the image), so we only check the mirror position itself.
        mirror = next(i for i in component.interfaces if i.element_type == "mirror")
        assert mirror.x1_mm == pytest.approx(20.0)

    def test_mirror_with_curvature_is_curved(self):
        zmx = _parse_zmx_text(
            """\
            MODE SEQ
            WAVM 1 0.5876 1
            PWAV 1
            SURF 0
              DISZ INFINITY
            SURF 1
              CURV 0.005
              DISZ 100.0
              GLAS MIRROR
              DIAM 25.0
            SURF 2
              DISZ 0
              DIAM 0.001
            """
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        mirror = component.interfaces[0]
        assert mirror.element_type == "mirror"
        assert mirror.is_curved
        assert mirror.radius_of_curvature_mm == pytest.approx(200.0)  # 1 / 0.005


class TestSurfaceFiltering:
    """Image / dummy / stop surfaces shouldn't produce ghost interfaces."""

    def test_image_surface_omitted(self):
        zmx = ZemaxFile(
            name="x",
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(number=1, curvature=0.01, glass="N-BK7", semi_diameter_mm=12.7),
                ZemaxSurface(number=2, curvature=-0.01, glass="", semi_diameter_mm=12.7),
                ZemaxSurface(number=3, curvature=0.0, semi_diameter_mm=0.001),  # image
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        assert len(component.interfaces) == 2

    def test_dummy_flat_air_to_air_surface_filtered(self):
        zmx = ZemaxFile(
            name="x",
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(number=1, curvature=0.01, glass="N-BK7", semi_diameter_mm=12.7),
                ZemaxSurface(number=2, curvature=-0.01, glass="", semi_diameter_mm=12.7),
                # Dummy: flat, air → air → should be skipped
                ZemaxSurface(number=3, curvature=0.0, glass="", semi_diameter_mm=12.7),
                ZemaxSurface(number=4, curvature=0.0, semi_diameter_mm=0.001),  # image
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        assert len(component.interfaces) == 2

    def test_flat_refractive_surface_is_kept(self):
        """A flat surface with a real material change is still an interface."""
        zmx = ZemaxFile(
            name="x",
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                # Flat air → glass (e.g. front face of a window)
                ZemaxSurface(number=1, curvature=0.0, glass="N-BK7", semi_diameter_mm=12.7),
                # Flat glass → air (back face)
                ZemaxSurface(number=2, curvature=0.0, glass="", semi_diameter_mm=12.7),
                ZemaxSurface(number=3, curvature=0.0, semi_diameter_mm=0.001),  # image
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        assert len(component.interfaces) == 2
        # Both flat refractive interfaces should be preserved
        for iface in component.interfaces:
            assert iface.element_type == "refractive_interface"
            assert not iface.is_curved


class TestNamePreservation:
    """Zemax COMM is preserved without dropping descriptive info."""

    def test_comm_prefixes_descriptive_name(self):
        zmx = ZemaxFile(
            name="x",
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(
                    number=1,
                    curvature=0.015,
                    glass="N-BK7",
                    semi_diameter_mm=12.7,
                    comment="AC254-100-B",
                ),
                ZemaxSurface(number=2, curvature=0.0, semi_diameter_mm=0.001),  # image
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        name = component.interfaces[0].name
        # COMM survives, but so does the auto-generated material/curvature info
        assert "AC254-100-B" in name
        assert "Air" in name  # material before
        assert "BK7" in name or "n=" in name  # material after
        assert "R=" in name  # curvature info

    def test_no_comm_uses_descriptive_name(self):
        zmx = ZemaxFile(
            name="x",
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(
                    number=1, curvature=0.015, glass="N-BK7", semi_diameter_mm=12.7
                ),
                ZemaxSurface(number=2, curvature=0.0, semi_diameter_mm=0.001),
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        name = component.interfaces[0].name
        assert name.startswith("S1:")
        assert "Air" in name


class TestCoordinateBreak:
    """COORDBRK PARMs rotate / decenter the optical axis in-plane."""

    def test_parm_parsing_and_unit_scaling(self):
        """PARM 1 / PARM 2 on COORDBRK are length-valued and scaled by UNIT."""
        zmx = _parse_zmx_text(
            """\
            MODE SEQ
            UNIT CM X W X CM MR CPMM
            SURF 0
              DISZ INFINITY
            SURF 1
              TYPE COORDBRK
              PARM 1 0.5
              PARM 2 0.3
              PARM 3 5.0
              PARM 4 10.0
              PARM 5 0.0
              PARM 6 0
              DISZ 1.0
            """
        )
        cb = zmx.surfaces[1]
        assert cb.is_coordinate_break
        # 0.5 cm → 5 mm, 0.3 cm → 3 mm
        assert cb.parm[1] == pytest.approx(5.0)
        assert cb.parm[2] == pytest.approx(3.0)
        # Tilts (degrees) are NOT scaled by UNIT.
        assert cb.parm[3] == pytest.approx(5.0)
        assert cb.parm[4] == pytest.approx(10.0)
        # DISZ on a coord break is a length: scaled.
        assert cb.thickness == pytest.approx(10.0)

    def test_coordbrk_does_not_emit_an_interface(self):
        """A coord break shouldn't appear as an interface in the output."""
        zmx = ZemaxFile(
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(number=1, curvature=0.01, glass="N-BK7", semi_diameter_mm=12.7),
                ZemaxSurface(
                    number=2, type="COORDBRK", thickness=10.0, parm={4: 30.0}
                ),
                ZemaxSurface(
                    number=3, curvature=-0.01, semi_diameter_mm=12.7
                ),
                ZemaxSurface(number=4, semi_diameter_mm=0.001),  # image
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        # 2 refractive interfaces — the COORDBRK is consumed silently.
        assert len(component.interfaces) == 2

    def test_tilt_rotates_subsequent_surface_orientation(self):
        """A 30° tilt about y rotates the next interface line in-plane."""
        zmx = ZemaxFile(
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                # First surface at origin, axis-aligned.
                ZemaxSurface(number=1, curvature=0.01, glass="N-BK7", semi_diameter_mm=10.0),
                # Coord break: no decenter, +30° tilt, advance 5 mm along new axis.
                ZemaxSurface(
                    number=2, type="COORDBRK", thickness=5.0, parm={4: 30.0}
                ),
                ZemaxSurface(
                    number=3, curvature=-0.01, semi_diameter_mm=10.0
                ),
                ZemaxSurface(number=4, semi_diameter_mm=0.001),
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        first, second = component.interfaces[0], component.interfaces[1]
        # First surface is axis-aligned: vertical line at x=0
        assert first.x1_mm == pytest.approx(0.0)
        assert first.x2_mm == pytest.approx(0.0)
        # Second is rotated 30°: its line is perpendicular to the +30° axis.
        assert second.angle_deg() == pytest.approx(120.0, abs=0.01)  # 90° + 30°
        # And its vertex sits ~5 mm down the rotated axis from the origin.
        assert second.midpoint_mm()[0] == pytest.approx(5.0 * math.cos(math.radians(30)))
        assert second.midpoint_mm()[1] == pytest.approx(5.0 * math.sin(math.radians(30)))

    def test_decenter_shifts_perpendicular_to_axis(self):
        """PARM 1 decenter shifts vertex perpendicular to current direction."""
        zmx = ZemaxFile(
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                # Decenter +5 mm in +y (axis is +x at this point).
                ZemaxSurface(
                    number=1, type="COORDBRK", thickness=0.0, parm={1: 5.0}
                ),
                ZemaxSurface(number=2, curvature=0.0, glass="N-BK7", semi_diameter_mm=10.0),
                ZemaxSurface(number=3, semi_diameter_mm=0.001),
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        iface = component.interfaces[0]
        # Vertex shifted by +5 mm in y, line still axis-aligned vertical.
        assert iface.midpoint_mm() == pytest.approx((0.0, 5.0))


class TestPeriscope:
    """A two-mirror periscope ends with the axis parallel-offset to entry."""

    def test_periscope_returns_to_parallel_axis(self):
        """Two 45° fold mirrors should leave the optical axis parallel to entry."""
        # Walk a periscope geometry by hand:
        #   S1 entry window (air → BK7), then BK7 → air on S2 so the rest of
        #   the system propagates in air. After this point, only mirrors
        #   change the axis direction.
        #   S3..S5: first fold (tilt +45°, mirror, tilt +45°) — axis now -y.
        #   S6..S8: second fold (tilt -45°, mirror, tilt -45°) — axis +x again.
        #   S9 exit window (air → BK7), S10 BK7 → air — both flat refractives
        #   that survive the dummy filter so we can measure exit orientation.
        zmx = ZemaxFile(
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(number=1, curvature=0.0, glass="N-BK7", semi_diameter_mm=10.0),
                ZemaxSurface(number=2, curvature=0.0, glass="", semi_diameter_mm=10.0),
                ZemaxSurface(number=3, type="COORDBRK", thickness=0.0, parm={4: 45.0}),
                ZemaxSurface(number=4, curvature=0.0, glass="MIRROR", semi_diameter_mm=15.0),
                ZemaxSurface(number=5, type="COORDBRK", thickness=20.0, parm={4: 45.0}),
                ZemaxSurface(number=6, type="COORDBRK", thickness=0.0, parm={4: -45.0}),
                ZemaxSurface(number=7, curvature=0.0, glass="MIRROR", semi_diameter_mm=15.0),
                ZemaxSurface(number=8, type="COORDBRK", thickness=10.0, parm={4: -45.0}),
                ZemaxSurface(number=9, curvature=0.0, glass="N-BK7", semi_diameter_mm=10.0),
                ZemaxSurface(number=10, curvature=0.0, glass="", semi_diameter_mm=10.0),
                ZemaxSurface(number=11, semi_diameter_mm=0.001),  # image
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)

        # 4 refractives (S1, S2, S9, S10) + 2 mirrors (S4, S7) = 6.
        assert len(component.interfaces) == 6
        entry = component.interfaces[0]
        exit_ = component.interfaces[-1]

        # Entry and exit lines must be parallel (axis-aligned, line angle ≡ 90°).
        # Compare modulo 180° because angle_deg can be ±90° depending on
        # which endpoint is y1.
        delta = (exit_.angle_deg() - entry.angle_deg()) % 180
        assert delta == pytest.approx(0, abs=0.5) or delta == pytest.approx(
            180, abs=0.5
        )

        # The exit axis is offset in y from the entry — that's the whole point
        # of a periscope.
        assert abs(exit_.midpoint_mm()[1] - entry.midpoint_mm()[1]) > 1.0

        # And the two mirrors should be oriented at ±45° to the entry axis
        # (their interface lines are perpendicular to a 45°-tilted optical
        # axis, so the line angle is 90° + 45° = 135°, modulo 180°).
        mirrors = [i for i in component.interfaces if i.element_type == "mirror"]
        assert len(mirrors) == 2
        for m in mirrors:
            assert m.angle_deg() % 180 == pytest.approx(135.0, abs=0.5)


class TestAsphereAnnotation:
    """EVENASPH surfaces are approximated as spheres and annotated."""

    def test_even_asphere_imports_with_base_radius(self):
        zmx = ZemaxFile(
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(
                    number=1,
                    type="EVENASPH",
                    curvature=0.01,  # base R = 100 mm
                    glass="N-BK7",
                    semi_diameter_mm=12.7,
                    parm={1: 0.0, 2: 0.001, 3: 1e-5},  # conic + aspheric coeffs
                ),
                ZemaxSurface(number=2, semi_diameter_mm=0.001),
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        iface = component.interfaces[0]
        assert iface.is_curved
        assert iface.radius_of_curvature_mm == pytest.approx(100.0)
        assert "Asphere approx." in iface.name

    def test_asphere_note_added_to_component(self):
        zmx = ZemaxFile(
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(
                    number=1,
                    type="EVENASPH",
                    curvature=0.01,
                    glass="N-BK7",
                    semi_diameter_mm=12.7,
                ),
                ZemaxSurface(number=2, semi_diameter_mm=0.001),
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        assert "aspheric surface" in component.notes.lower()
        assert "S1" in component.notes


class TestStopAnnotation:
    """Aperture stops are annotated in the interface name when kept."""

    def test_stop_surface_with_material_change_is_annotated(self):
        zmx = ZemaxFile(
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(
                    number=1,
                    curvature=0.01,
                    glass="N-BK7",
                    semi_diameter_mm=12.7,
                    is_stop=True,
                ),
                ZemaxSurface(number=2, semi_diameter_mm=0.001),
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        assert "Aperture Stop" in component.interfaces[0].name

    def test_dummy_stop_surface_still_filtered(self):
        """A flat air-to-air stop has no optical effect and is still skipped."""
        zmx = ZemaxFile(
            wavelengths_um=[0.5876],
            primary_wavelength_idx=1,
            surfaces=[
                ZemaxSurface(number=0),
                ZemaxSurface(number=1, curvature=0.01, glass="N-BK7", semi_diameter_mm=12.7),
                ZemaxSurface(number=2, curvature=-0.01, glass="", semi_diameter_mm=12.7),
                # Aperture stop after the lens (air → air, flat) — filtered.
                ZemaxSurface(
                    number=3, curvature=0.0, glass="", semi_diameter_mm=10.0, is_stop=True
                ),
                ZemaxSurface(number=4, semi_diameter_mm=0.001),
            ],
        )
        component = ZemaxToInterfaceConverter(GlassCatalog()).convert(zmx)
        assert len(component.interfaces) == 2


class TestMirrorFlag:
    """ZemaxSurface.is_mirror returns True only for GLAS MIRROR."""

    def test_is_mirror_true_for_mirror_glass(self):
        assert ZemaxSurface(number=1, glass="MIRROR").is_mirror
        assert ZemaxSurface(number=1, glass="mirror").is_mirror
        assert ZemaxSurface(number=1, glass=" Mirror ").is_mirror

    def test_is_mirror_false_for_other_glass(self):
        assert not ZemaxSurface(number=1, glass="N-BK7").is_mirror
        assert not ZemaxSurface(number=1, glass="").is_mirror


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
