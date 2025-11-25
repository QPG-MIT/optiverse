"""
Test Zemax parser functionality.
"""

import pytest
from optiverse.services.zemax_parser import ZemaxParser, ZemaxSurface, ZemaxFile


def test_zemax_parser_basic():
    """Test basic Zemax file parsing."""
    parser = ZemaxParser()
    zemax_file = "/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx"

    data = parser.parse(zemax_file)

    assert data is not None
    assert len(data.surfaces) == 5
    assert data.name == "AC254-100-B AC254-100-B NEAR IR ACHROMATS: Infinite Conjugate 100"
    assert data.mode == "SEQ"


def test_zemax_parser_wavelengths():
    """Test wavelength extraction."""
    parser = ZemaxParser()
    zemax_file = "/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx"

    data = parser.parse(zemax_file)

    assert len(data.wavelengths_um) > 0
    assert data.primary_wavelength_idx == 2  # 1-indexed
    assert abs(data.primary_wavelength_um - 0.855) < 0.001  # 855nm


def test_zemax_parser_surface_object():
    """Test object surface (S0)."""
    parser = ZemaxParser()
    zemax_file = "/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx"

    data = parser.parse(zemax_file)
    surf0 = data.surfaces[0]

    assert surf0.number == 0
    assert surf0.type == "STANDARD"
    assert surf0.curvature == 0.0
    assert surf0.is_flat
    assert surf0.thickness == float('inf')


def test_zemax_parser_surface1_entry():
    """Test entry surface (S1) - first lens surface."""
    parser = ZemaxParser()
    zemax_file = "/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx"

    data = parser.parse(zemax_file)
    surf1 = data.surfaces[1]

    assert surf1.number == 1
    assert surf1.type == "STANDARD"
    assert abs(surf1.curvature - 0.014997) < 0.000001
    assert abs(surf1.radius_mm - 66.68) < 0.01
    assert not surf1.is_flat
    assert abs(surf1.thickness - 4.0) < 0.01
    assert surf1.glass == "N-LAK22"
    assert abs(surf1.diameter - 12.7) < 0.1
    assert surf1.coating == "THORB"
    assert surf1.comment == "AC254-100-B"


def test_zemax_parser_surface2_cemented():
    """Test cemented surface (S2) - interface between two glasses."""
    parser = ZemaxParser()
    zemax_file = "/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx"

    data = parser.parse(zemax_file)
    surf2 = data.surfaces[2]

    assert surf2.number == 2
    assert abs(surf2.curvature - (-0.018622)) < 0.00001
    assert abs(surf2.radius_mm - (-53.70)) < 0.01
    assert not surf2.is_flat
    assert abs(surf2.thickness - 1.5) < 0.01
    assert surf2.glass == "N-SF6HT"
    assert abs(surf2.diameter - 12.7) < 0.1


def test_zemax_parser_surface3_exit():
    """Test exit surface (S3) - last lens surface."""
    parser = ZemaxParser()
    zemax_file = "/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx"

    data = parser.parse(zemax_file)
    surf3 = data.surfaces[3]

    assert surf3.number == 3
    assert abs(surf3.curvature - (-0.003854)) < 0.000001
    assert abs(surf3.radius_mm - (-259.41)) < 0.1
    assert not surf3.is_flat
    assert abs(surf3.thickness - 97.09) < 0.01
    assert surf3.glass == ""  # Air
    assert abs(surf3.diameter - 12.7) < 0.1
    assert surf3.coating == "THORBSLAH64"


def test_zemax_parser_surface4_image():
    """Test image surface (S4)."""
    parser = ZemaxParser()
    zemax_file = "/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx"

    data = parser.parse(zemax_file)
    surf4 = data.surfaces[4]

    assert surf4.number == 4
    assert surf4.is_flat
    assert abs(surf4.diameter - 0.0052) < 0.001  # Very small diameter



