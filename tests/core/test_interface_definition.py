"""Tests for InterfaceDefinition."""

import pytest
from optiverse.core.interface_definition import InterfaceDefinition


def test_interface_definition_default():
    """Test default interface creation."""
    iface = InterfaceDefinition()
    assert iface.element_type == "refractive_interface"
    assert iface.x1_mm == 0.0
    assert iface.n1 == 1.0
    assert iface.n2 == 1.5


def test_interface_definition_lens():
    """Test lens interface creation."""
    iface = InterfaceDefinition(
        element_type="lens",
        x1_mm=-12.7, y1_mm=0.0,
        x2_mm=12.7, y2_mm=0.0,
        efl_mm=100.0
    )
    assert iface.element_type == "lens"
    assert iface.efl_mm == 100.0
    assert iface.get_color() == (0, 180, 180)  # Cyan


def test_interface_definition_serialization():
    """Test serialization round-trip."""
    iface = InterfaceDefinition(
        x1_mm=-10.0, y1_mm=5.0,
        x2_mm=10.0, y2_mm=5.0,
        element_type="lens",
        efl_mm=50.0,
        name="Test Lens"
    )
    
    data = iface.to_dict()
    iface2 = InterfaceDefinition.from_dict(data)
    
    assert iface2.x1_mm == iface.x1_mm
    assert iface2.element_type == "lens"
    assert iface2.efl_mm == 50.0
    assert iface2.name == "Test Lens"


def test_interface_colors():
    """Test color coding for different interface types."""
    lens = InterfaceDefinition(element_type="lens")
    assert lens.get_color() == (0, 180, 180)  # Cyan
    
    mirror = InterfaceDefinition(element_type="mirror")
    assert mirror.get_color() == (255, 140, 0)  # Orange
    
    bs = InterfaceDefinition(element_type="beam_splitter")
    assert bs.get_color() == (0, 150, 120)  # Green
    
    pbs = InterfaceDefinition(element_type="beam_splitter", is_polarizing=True)
    assert pbs.get_color() == (150, 0, 150)  # Purple
    
    dichroic = InterfaceDefinition(element_type="dichroic")
    assert dichroic.get_color() == (255, 0, 255)  # Magenta
    
    refr = InterfaceDefinition(element_type="refractive_interface", n1=1.0, n2=1.5)
    assert refr.get_color() == (100, 100, 255)  # Blue


def test_interface_color_same_index():
    """Test that same refractive index gives gray color."""
    iface = InterfaceDefinition(
        element_type="refractive_interface",
        n1=1.5,
        n2=1.5
    )
    assert iface.get_color() == (150, 150, 150)  # Gray


def test_interface_length():
    """Test length calculation."""
    iface = InterfaceDefinition(
        x1_mm=0.0, y1_mm=0.0,
        x2_mm=3.0, y2_mm=4.0
    )
    assert iface.length_mm() == pytest.approx(5.0)


def test_interface_angle():
    """Test angle calculation."""
    # Horizontal line
    h_iface = InterfaceDefinition(
        x1_mm=0.0, y1_mm=0.0,
        x2_mm=10.0, y2_mm=0.0
    )
    assert h_iface.angle_deg() == pytest.approx(0.0)
    
    # Vertical line
    v_iface = InterfaceDefinition(
        x1_mm=0.0, y1_mm=0.0,
        x2_mm=0.0, y2_mm=10.0
    )
    assert v_iface.angle_deg() == pytest.approx(90.0)
    
    # 45 degree line
    d_iface = InterfaceDefinition(
        x1_mm=0.0, y1_mm=0.0,
        x2_mm=10.0, y2_mm=10.0
    )
    assert d_iface.angle_deg() == pytest.approx(45.0)


def test_interface_midpoint():
    """Test midpoint calculation."""
    iface = InterfaceDefinition(
        x1_mm=0.0, y1_mm=0.0,
        x2_mm=10.0, y2_mm=20.0
    )
    mid_x, mid_y = iface.midpoint_mm()
    assert mid_x == pytest.approx(5.0)
    assert mid_y == pytest.approx(10.0)


def test_interface_labels():
    """Test label generation."""
    lens = InterfaceDefinition(element_type="lens", efl_mm=100.0)
    assert "100.0" in lens.get_label()
    assert "Lens" in lens.get_label()
    
    mirror = InterfaceDefinition(element_type="mirror")
    assert "Mirror" in mirror.get_label()
    
    bs = InterfaceDefinition(element_type="beam_splitter", split_T=60.0, split_R=40.0)
    label = bs.get_label()
    assert "60" in label and "40" in label
    
    pbs = InterfaceDefinition(element_type="beam_splitter", is_polarizing=True)
    assert "PBS" in pbs.get_label()
    
    dichroic = InterfaceDefinition(element_type="dichroic", cutoff_wavelength_nm=550.0)
    assert "550" in dichroic.get_label()
    
    refr = InterfaceDefinition(element_type="refractive_interface", n1=1.0, n2=1.517)
    label = refr.get_label()
    assert "1.000" in label and "1.517" in label


def test_interface_custom_name():
    """Test that custom name overrides auto-generated label."""
    iface = InterfaceDefinition(
        element_type="lens",
        name="My Custom Lens"
    )
    assert iface.get_label() == "My Custom Lens"


def test_interface_copy():
    """Test interface copying."""
    original = InterfaceDefinition(
        element_type="lens",
        x1_mm=1.0, y1_mm=2.0,
        x2_mm=3.0, y2_mm=4.0,
        efl_mm=75.0,
        name="Original"
    )
    
    copy = original.copy()
    
    assert copy.element_type == original.element_type
    assert copy.x1_mm == original.x1_mm
    assert copy.efl_mm == original.efl_mm
    assert copy.name == original.name
    
    # Verify it's a separate object
    copy.name = "Copy"
    assert original.name == "Original"
    assert copy.name == "Copy"


def test_interface_all_element_types():
    """Test creating interfaces of all supported types."""
    types = ['lens', 'mirror', 'beam_splitter', 'dichroic', 'refractive_interface']
    
    for elem_type in types:
        iface = InterfaceDefinition(element_type=elem_type)
        assert iface.element_type == elem_type
        assert len(iface.get_color()) == 3  # Valid RGB tuple
        assert len(iface.get_label()) > 0  # Has a label

