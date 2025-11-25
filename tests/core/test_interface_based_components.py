"""
Test interface-based component storage and raytracing.

This test suite validates that all component types properly store and expose
multiple optical interfaces for raytracing.
"""

from __future__ import annotations

import numpy as np
import pytest

from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.core.models import (
    BeamsplitterParams,
    DichroicParams,
    LensParams,
    MirrorParams,
    WaveplateParams,
)
from optiverse.objects import (
    BeamsplitterItem,
    DichroicItem,
    LensItem,
    MirrorItem,
    WaveplateItem,
)


class TestInterfaceStorage:
    """Test that all Params classes can store interfaces."""

    def test_lens_params_has_interfaces_field(self):
        """LensParams should have an interfaces field."""
        params = LensParams()
        assert hasattr(params, "interfaces")
        assert params.interfaces is not None
        assert isinstance(params.interfaces, list)

    def test_mirror_params_has_interfaces_field(self):
        """MirrorParams should have an interfaces field."""
        params = MirrorParams()
        assert hasattr(params, "interfaces")
        assert params.interfaces is not None
        assert isinstance(params.interfaces, list)

    def test_beamsplitter_params_has_interfaces_field(self):
        """BeamsplitterParams should have an interfaces field."""
        params = BeamsplitterParams()
        assert hasattr(params, "interfaces")
        assert params.interfaces is not None
        assert isinstance(params.interfaces, list)

    def test_dichroic_params_has_interfaces_field(self):
        """DichroicParams should have an interfaces field."""
        params = DichroicParams()
        assert hasattr(params, "interfaces")
        assert params.interfaces is not None
        assert isinstance(params.interfaces, list)

    def test_waveplate_params_has_interfaces_field(self):
        """WaveplateParams should have an interfaces field."""
        params = WaveplateParams()
        assert hasattr(params, "interfaces")
        assert params.interfaces is not None
        assert isinstance(params.interfaces, list)

    def test_lens_params_accepts_interfaces(self):
        """LensParams should accept interfaces in constructor."""
        interface = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0, x2_mm=0.0, y2_mm=10.0, element_type="lens", efl_mm=100.0
        )
        params = LensParams(interfaces=[interface])
        assert len(params.interfaces) == 1
        assert params.interfaces[0].efl_mm == 100.0

    def test_mirror_params_accepts_interfaces(self):
        """MirrorParams should accept interfaces in constructor."""
        interface = InterfaceDefinition(
            x1_mm=-10.0,
            y1_mm=-10.0,
            x2_mm=10.0,
            y2_mm=10.0,
            element_type="mirror",
            reflectivity=99.0,
        )
        params = MirrorParams(interfaces=[interface])
        assert len(params.interfaces) == 1
        assert params.interfaces[0].reflectivity == 99.0


class TestGetInterfacesScene:
    """Test that all item classes expose get_interfaces_scene() method."""

    def test_lens_item_has_get_interfaces_scene(self):
        """LensItem should have get_interfaces_scene() method."""
        params = LensParams()
        item = LensItem(params)
        assert hasattr(item, "get_interfaces_scene")
        assert callable(item.get_interfaces_scene)

    def test_mirror_item_has_get_interfaces_scene(self):
        """MirrorItem should have get_interfaces_scene() method."""
        params = MirrorParams()
        item = MirrorItem(params)
        assert hasattr(item, "get_interfaces_scene")
        assert callable(item.get_interfaces_scene)

    def test_beamsplitter_item_has_get_interfaces_scene(self):
        """BeamsplitterItem should have get_interfaces_scene() method."""
        params = BeamsplitterParams()
        item = BeamsplitterItem(params)
        assert hasattr(item, "get_interfaces_scene")
        assert callable(item.get_interfaces_scene)

    def test_dichroic_item_has_get_interfaces_scene(self):
        """DichroicItem should have get_interfaces_scene() method."""
        params = DichroicParams()
        item = DichroicItem(params)
        assert hasattr(item, "get_interfaces_scene")
        assert callable(item.get_interfaces_scene)

    def test_waveplate_item_has_get_interfaces_scene(self):
        """WaveplateItem should have get_interfaces_scene() method."""
        params = WaveplateParams()
        item = WaveplateItem(params)
        assert hasattr(item, "get_interfaces_scene")
        assert callable(item.get_interfaces_scene)

    def test_lens_item_returns_interface_tuples(self):
        """LensItem.get_interfaces_scene() should return list of (p1, p2, interface) tuples."""
        params = LensParams()
        item = LensItem(params)
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
        """Lens with multiple interfaces (e.g., doublet) should expose all."""
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

        params = LensParams(interfaces=interfaces)
        item = LensItem(params)

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

        params = MirrorParams(interfaces=interfaces)
        item = MirrorItem(params)

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


class TestBackwardCompatibility:
    """Test backward compatibility with legacy components."""

    def test_lens_without_interfaces_creates_default(self):
        """Lens without interfaces should auto-generate default interface."""
        params = LensParams(efl_mm=100.0, object_height_mm=25.4)
        # Clear interfaces to simulate legacy component
        params.interfaces = []

        item = LensItem(params)
        interfaces = item.get_interfaces_scene()

        # Should auto-generate one interface
        assert len(interfaces) == 1
        p1, p2, iface = interfaces[0]
        assert iface.element_type == "lens"
        assert iface.efl_mm == pytest.approx(100.0)

    def test_mirror_without_interfaces_creates_default(self):
        """Mirror without interfaces should auto-generate default interface."""
        params = MirrorParams(object_height_mm=25.4)
        params.interfaces = []

        item = MirrorItem(params)
        interfaces = item.get_interfaces_scene()

        assert len(interfaces) == 1
        _, _, iface = interfaces[0]
        assert iface.element_type == "mirror"

    def test_beamsplitter_without_interfaces_creates_default(self):
        """Beamsplitter without interfaces should auto-generate default interface."""
        params = BeamsplitterParams(split_T=50.0, split_R=50.0)
        params.interfaces = []

        item = BeamsplitterItem(params)
        interfaces = item.get_interfaces_scene()

        assert len(interfaces) == 1
        _, _, iface = interfaces[0]
        assert iface.element_type == "beam_splitter"
        assert iface.split_T == pytest.approx(50.0)


class TestSerialization:
    """Test serialization/deserialization with interfaces."""

    def test_lens_serialization_preserves_interfaces(self):
        """LensItem serialization should preserve interfaces."""
        interface = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0, x2_mm=0.0, y2_mm=10.0, element_type="lens", efl_mm=100.0
        )
        params = LensParams(interfaces=[interface])
        item = LensItem(params)

        # Serialize
        data = item.to_dict()
        assert "interfaces" in data
        assert len(data["interfaces"]) == 1
        assert data["interfaces"][0]["efl_mm"] == pytest.approx(100.0)

        # Deserialize
        item2 = LensItem.from_dict(data)
        assert len(item2.params.interfaces) == 1
        assert item2.params.interfaces[0].efl_mm == pytest.approx(100.0)

    def test_mirror_serialization_preserves_interfaces(self):
        """MirrorItem serialization should preserve interfaces."""
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
        params = MirrorParams(interfaces=interfaces)
        item = MirrorItem(params)

        # Serialize
        data = item.to_dict()
        assert "interfaces" in data
        assert len(data["interfaces"]) == 2

        # Deserialize
        item2 = MirrorItem.from_dict(data)
        assert len(item2.params.interfaces) == 2


class TestSceneCoordinates:
    """Test that scene coordinates are correctly transformed."""

    def test_lens_interface_scene_coords_with_rotation(self):
        """Interface coordinates should account for item rotation."""
        interface = InterfaceDefinition(
            x1_mm=0.0, y1_mm=-10.0, x2_mm=0.0, y2_mm=10.0, element_type="lens", efl_mm=100.0
        )
        params = LensParams(x_mm=100.0, y_mm=200.0, angle_deg=45.0, interfaces=[interface])
        item = LensItem(params)

        interfaces = item.get_interfaces_scene()
        p1, p2, _ = interfaces[0]

        # p1 and p2 should be in scene coordinates (affected by position and rotation)
        # Check that they're not at origin
        assert p1[0] != 0.0 or p1[1] != 0.0
        assert p2[0] != 0.0 or p2[1] != 0.0

    def test_mirror_interface_scene_coords_with_position(self):
        """Interface coordinates should account for item position."""
        interface = InterfaceDefinition(
            x1_mm=-10.0, y1_mm=0.0, x2_mm=10.0, y2_mm=0.0, element_type="mirror"
        )
        params = MirrorParams(x_mm=50.0, y_mm=100.0, interfaces=[interface])
        item = MirrorItem(params)

        interfaces = item.get_interfaces_scene()
        p1, p2, _ = interfaces[0]

        # Midpoint should be near item position
        mid_x = (p1[0] + p2[0]) / 2
        mid_y = (p1[1] + p2[1]) / 2

        assert mid_x == pytest.approx(50.0, abs=1.0)
        assert mid_y == pytest.approx(100.0, abs=1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
