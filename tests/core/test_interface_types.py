"""Tests for interface type registry."""

from optiverse.core.interface_types import (
    INTERFACE_TYPES,
    get_all_type_names,
    get_property_default,
    get_property_label,
    get_property_range,
    get_property_unit,
    get_type_color,
    get_type_display_name,
    get_type_emoji,
    get_type_info,
    get_type_properties,
    validate_property_value,
)


def test_all_types_defined():
    """Test that all expected interface types are defined."""
    expected_types = ["lens", "mirror", "beam_splitter", "dichroic", "refractive_interface"]
    type_names = get_all_type_names()

    for expected in expected_types:
        assert expected in type_names


def test_get_type_info():
    """Test getting type info."""
    lens_info = get_type_info("lens")
    assert lens_info["name"] == "Lens"
    assert "efl_mm" in lens_info["properties"]

    # Unknown type returns empty dict
    unknown = get_type_info("unknown_type")
    assert unknown == {}


def test_get_type_display_name():
    """Test getting display names."""
    assert get_type_display_name("lens") == "Lens"
    assert get_type_display_name("beam_splitter") == "Beam Splitter"
    assert get_type_display_name("unknown") == "unknown"


def test_get_property_label():
    """Test getting property labels."""
    label = get_property_label("lens", "efl_mm")
    assert label == "Effective Focal Length"

    # Unknown property returns property name
    unknown = get_property_label("lens", "unknown_prop")
    assert unknown == "unknown_prop"


def test_get_property_unit():
    """Test getting property units."""
    assert get_property_unit("lens", "efl_mm") == "mm"
    assert get_property_unit("beam_splitter", "split_T") == "%"
    assert get_property_unit("beam_splitter", "pbs_transmission_axis_deg") == "°"
    assert get_property_unit("refractive_interface", "n1") == ""  # No unit


def test_get_property_range():
    """Test getting property ranges."""
    efl_range = get_property_range("lens", "efl_mm")
    assert efl_range == (-10000.0, 10000.0)

    split_range = get_property_range("beam_splitter", "split_T")
    assert split_range == (0.0, 100.0)

    # Unknown property returns wide range
    unknown_range = get_property_range("lens", "unknown_prop")
    assert unknown_range[0] < -1e9
    assert unknown_range[1] > 1e9


def test_get_property_default():
    """Test getting property defaults."""
    assert get_property_default("lens", "efl_mm") == 100.0
    assert get_property_default("mirror", "reflectivity") == 99.0
    assert get_property_default("beam_splitter", "split_T") == 50.0
    assert get_property_default("dichroic", "pass_type") == "longpass"


def test_get_type_color():
    """Test getting type colors."""
    assert get_type_color("lens") == (0, 180, 180)  # Cyan
    assert get_type_color("mirror") == (255, 140, 0)  # Orange
    assert get_type_color("beam_splitter") == (0, 150, 120)  # Green
    assert get_type_color("beam_splitter", is_polarizing=True) == (150, 0, 150)  # Purple
    assert get_type_color("dichroic") == (255, 0, 255)  # Magenta
    assert get_type_color("refractive_interface") == (100, 100, 255)  # Blue


def test_get_type_emoji():
    """Test getting type emojis."""
    assert get_type_emoji("lens") == "🔵"
    assert get_type_emoji("mirror") == "🟠"
    assert get_type_emoji("beam_splitter") == "🟢"
    assert get_type_emoji("unknown") == "⚪"  # Default


def test_get_type_properties():
    """Test getting property lists."""
    lens_props = get_type_properties("lens")
    assert "efl_mm" in lens_props

    bs_props = get_type_properties("beam_splitter")
    assert "split_T" in bs_props
    assert "split_R" in bs_props
    assert "is_polarizing" in bs_props

    refr_props = get_type_properties("refractive_interface")
    assert "n1" in refr_props
    assert "n2" in refr_props


def test_validate_property_value():
    """Test property value validation."""
    # Valid values
    assert validate_property_value("lens", "efl_mm", 100.0)
    assert validate_property_value("beam_splitter", "split_T", 50.0)

    # Out of range values
    assert not validate_property_value("beam_splitter", "split_T", 150.0)
    assert not validate_property_value("beam_splitter", "split_T", -10.0)

    # Edge cases
    assert validate_property_value("beam_splitter", "split_T", 0.0)
    assert validate_property_value("beam_splitter", "split_T", 100.0)

    # Non-numeric values (always valid)
    assert validate_property_value("dichroic", "pass_type", "longpass")


def test_interface_types_completeness():
    """Test that all types have required metadata fields."""
    required_fields = ["name", "description", "color", "emoji", "properties"]

    for type_name, type_info in INTERFACE_TYPES.items():
        for field in required_fields:
            assert field in type_info, f"Type '{type_name}' missing field '{field}'"

        # Check that color is valid RGB tuple
        color = type_info["color"]
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)

        # Check that properties have corresponding labels
        for prop in type_info["properties"]:
            assert prop in type_info.get("property_labels", {}), (
                f"Type '{type_name}' property '{prop}' has no label"
            )


def test_all_properties_have_metadata():
    """Test that all properties have complete metadata."""
    for type_name, type_info in INTERFACE_TYPES.items():
        for prop in type_info["properties"]:
            # Every property should have a label
            assert prop in type_info.get("property_labels", {}), f"{type_name}.{prop} has no label"

            # Every property should have a default (may be None)
            assert prop in type_info.get("property_defaults", {}), (
                f"{type_name}.{prop} has no default"
            )

            # Numeric properties should have ranges
            default = type_info["property_defaults"][prop]
            if isinstance(default, (int, float)):
                assert prop in type_info.get("property_ranges", {}), (
                    f"{type_name}.{prop} has no range"
                )
