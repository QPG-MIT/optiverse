"""
Test interface-based component storage and raytracing.

This test suite validates that all component types properly store and expose
multiple optical interfaces for raytracing.
"""

from __future__ import annotations

import numpy as np
import pytest

from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.core.models import ComponentParams
from optiverse.objects import ComponentItem
from tests.fixtures.factories import create_lens_item


class TestInterfaceStorage:
    """Test that ComponentParams can store interfaces."""

    def test_component_params_has_interfaces_field(self):
        """ComponentParams should have an interfaces field."""
        params = ComponentParams()
        assert hasattr(params, "interfaces")
        assert params.interfaces is not None
        assert isinstance(params.interfaces, list)

    def test_component_params_accepts_interfaces(self):
        """ComponentParams should accept interfaces in constructor."""
        interface = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0, x2_mm=0.0, y2_mm=10.0, element_type="lens", efl_mm=100.0
        )
        params = ComponentParams(interfaces=[interface])
        assert len(params.interfaces) == 1
        assert params.interfaces[0].efl_mm == 100.0


class TestGetInterfacesScene:
    """Test that ComponentItem exposes get_interfaces_scene() method."""

    def test_component_item_has_get_interfaces_scene(self):
        """ComponentItem should have get_interfaces_scene() method."""
        item = create_lens_item()
        assert hasattr(item, "get_interfaces_scene")
        assert callable(item.get_interfaces_scene)

    def test_component_item_returns_interface_tuples(self):
        """ComponentItem.get_interfaces_scene() should return list of (p1, p2, interface) tuples."""
        item = create_lens_item()
        interfaces = item.get_interfaces_scene()

        assert isinstance(interfaces, list)
        assert len(interfaces) > 0

        # Check tuple structure
        p1, p2, iface = interfaces[0]
        assert isinstance(p1, np.ndarray)
        assert isinstance(p2, np.ndarray)
        assert isinstance(iface, InterfaceDefinition)
        assert len(p1) == 2
        assert len(p2) == 2


class TestMultipleInterfaces:
    """Test handling of components with multiple interfaces."""

    def test_lens_with_multiple_interfaces(self):
        """Component with multiple interfaces (e.g., doublet) should expose all."""
        # Create a doublet with 3 interfaces
        interfaces = [
            InterfaceDefinition(
                x1_mm=-2.0,
                y1_mm=-10.0,
                x2_mm=-2.0,
                y2_mm=10.0,
                element_type="refractive_interface",
                n1=1.0,
                n2=1.517,
            ),
            InterfaceDefinition(
                x1_mm=0.0,
                y1_mm=-10.0,
                x2_mm=0.0,
                y2_mm=10.0,
                element_type="refractive_interface",
                n1=1.517,
                n2=1.620,
            ),
            InterfaceDefinition(
                x1_mm=2.0,
                y1_mm=-10.0,
                x2_mm=2.0,
                y2_mm=10.0,
                element_type="refractive_interface",
                n1=1.620,
                n2=1.0,
            ),
        ]

        params = ComponentParams(x_mm=0.0, y_mm=0.0, angle_deg=90.0, interfaces=interfaces)
        item = ComponentItem(params)

        interfaces_scene = item.get_interfaces_scene()
        assert len(interfaces_scene) == 3

        # Verify all interfaces are present
        for _i, (_p1, _p2, iface) in enumerate(interfaces_scene):
            assert isinstance(iface, InterfaceDefinition)
            assert iface.element_type == "refractive_interface"

    def test_mirror_with_ar_coating(self):
        """Mirror with AR coating should expose both interfaces."""
        # AR coating + reflective surface
        interfaces = [
            InterfaceDefinition(
                x1_mm=-10.0,
                y1_mm=-10.0,
                x2_mm=10.0,
                y2_mm=10.0,
                element_type="refractive_interface",
                n1=1.0,
                n2=1.38,  # AR coating
            ),
            InterfaceDefinition(
                x1_mm=-10.0,
                y1_mm=-10.0,
                x2_mm=10.0,
                y2_mm=10.0,
                element_type="mirror",
                reflectivity=99.9,
            ),
        ]

        params = ComponentParams(x_mm=0.0, y_mm=0.0, angle_deg=45.0, interfaces=interfaces)
        item = ComponentItem(params)

        interfaces_scene = item.get_interfaces_scene()
        assert len(interfaces_scene) == 2

        # Verify AR coating
        _, _, ar_iface = interfaces_scene[0]
        assert ar_iface.element_type == "refractive_interface"
        assert ar_iface.n2 == pytest.approx(1.38)

        # Verify mirror
        _, _, mirror_iface = interfaces_scene[1]
        assert mirror_iface.element_type == "mirror"
        assert mirror_iface.reflectivity == pytest.approx(99.9)


class TestSerialization:
    """Test serialization/deserialization with interfaces."""

    def test_component_serialization_preserves_interfaces(self):
        """ComponentItem serialization should preserve interfaces."""
        interface = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0, x2_mm=0.0, y2_mm=10.0, element_type="lens", efl_mm=100.0
        )
        params = ComponentParams(interfaces=[interface])
        item = ComponentItem(params)

        # Serialize
        data = item.to_dict()
        assert "interfaces" in data
        assert len(data["interfaces"]) == 1
        assert data["interfaces"][0]["efl_mm"] == pytest.approx(100.0)

        # Deserialize
        item2 = ComponentItem.from_dict(data)
        assert len(item2.params.interfaces) == 1
        assert item2.params.interfaces[0].efl_mm == pytest.approx(100.0)

    def test_component_serialization_preserves_multiple_interfaces(self):
        """ComponentItem serialization should preserve multiple interfaces."""
        interfaces = [
            InterfaceDefinition(
                x1_mm=-10.0,
                y1_mm=-10.0,
                x2_mm=10.0,
                y2_mm=10.0,
                element_type="refractive_interface",
                n1=1.0,
                n2=1.38,
            ),
            InterfaceDefinition(
                x1_mm=-10.0,
                y1_mm=-10.0,
                x2_mm=10.0,
                y2_mm=10.0,
                element_type="mirror",
                reflectivity=99.9,
            ),
        ]
        params = ComponentParams(interfaces=interfaces)
        item = ComponentItem(params)

        # Serialize
        data = item.to_dict()
        assert "interfaces" in data
        assert len(data["interfaces"]) == 2

        # Deserialize
        item2 = ComponentItem.from_dict(data)
        assert len(item2.params.interfaces) == 2


class TestSceneCoordinates:
    """Test that scene coordinates are correctly transformed."""

    def test_interface_scene_coords_with_rotation(self):
        """Interface coordinates should account for item rotation."""
        interface = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0, x2_mm=0.0, y2_mm=10.0, element_type="lens", efl_mm=100.0
        )
        params = ComponentParams(
            x_mm=100.0, y_mm=200.0, angle_deg=45.0, interfaces=[interface]
        )
        item = ComponentItem(params)

        interfaces = item.get_interfaces_scene()
        p1, p2, _ = interfaces[0]

        # p1 and p2 should be in scene coordinates (affected by position and rotation)
        # Check that they're not at origin
        assert p1[0] != 0.0 or p1[1] != 0.0
        assert p2[0] != 0.0 or p2[1] != 0.0

    def test_interface_scene_coords_with_position(self):
        """Interface coordinates should account for item position."""
        interface = InterfaceDefinition(
            x1_mm=-10.0, y1_mm=0.0, x2_mm=10.0, y2_mm=0.0, element_type="mirror"
        )
        params = ComponentParams(x_mm=50.0, y_mm=100.0, interfaces=[interface])
        item = ComponentItem(params)

        interfaces = item.get_interfaces_scene()
        p1, p2, _ = interfaces[0]

        # Midpoint should be near item position
        mid_x = (p1[0] + p2[0]) / 2
        mid_y = (p1[1] + p2[1]) / 2

        assert mid_x == pytest.approx(50.0, abs=1.0)
        assert mid_y == pytest.approx(100.0, abs=1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
