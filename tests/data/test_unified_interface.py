"""
Test suite for unified optical interface model.

This test suite defines the expected behavior of the new unified interface model
before implementation (TDD approach).
"""

from dataclasses import asdict

import numpy as np
import pytest


class TestOpticalProperties:
    """Test type-safe optical property classes"""

    def test_refractive_properties_creation(self):
        """Test creating refractive properties"""
        from optiverse.data.optical_properties import RefractiveProperties

        props = RefractiveProperties(n1=1.0, n2=1.5)

        assert props.n1 == 1.0
        assert props.n2 == 1.5
        assert props.curvature_radius_mm is None

    def test_refractive_properties_with_curvature(self):
        """Test refractive properties with curved surface"""
        from optiverse.data.optical_properties import RefractiveProperties

        props = RefractiveProperties(n1=1.0, n2=1.5, curvature_radius_mm=50.0)

        assert props.curvature_radius_mm == 50.0

    def test_lens_properties_creation(self):
        """Test creating lens properties"""
        from optiverse.data.optical_properties import LensProperties

        props = LensProperties(efl_mm=100.0)

        assert props.efl_mm == 100.0

    def test_mirror_properties_creation(self):
        """Test creating mirror properties"""
        from optiverse.data.optical_properties import MirrorProperties

        props = MirrorProperties(reflectivity=0.99)

        assert props.reflectivity == 0.99

    def test_mirror_properties_default_reflectivity(self):
        """Test mirror properties with default reflectivity"""
        from optiverse.data.optical_properties import MirrorProperties

        props = MirrorProperties()

        assert props.reflectivity == 0.99

    def test_beamsplitter_properties_creation(self):
        """Test creating beamsplitter properties"""
        from optiverse.data.optical_properties import BeamsplitterProperties

        props = BeamsplitterProperties(transmission=0.5, reflection=0.5)

        assert props.transmission == 0.5
        assert props.reflection == 0.5
        assert props.is_polarizing is False

    def test_pbs_properties_creation(self):
        """Test creating PBS (polarizing beamsplitter) properties"""
        from optiverse.data.optical_properties import BeamsplitterProperties

        props = BeamsplitterProperties(
            transmission=0.99, reflection=0.99, is_polarizing=True, polarization_axis_deg=0.0
        )

        assert props.is_polarizing is True
        assert props.polarization_axis_deg == 0.0

    def test_waveplate_properties_creation(self):
        """Test creating waveplate properties"""
        from optiverse.data.optical_properties import WaveplateProperties

        props = WaveplateProperties(phase_shift_deg=90.0, fast_axis_deg=45.0)

        assert props.phase_shift_deg == 90.0
        assert props.fast_axis_deg == 45.0

    def test_dichroic_properties_creation(self):
        """Test creating dichroic properties"""
        from optiverse.data.optical_properties import DichroicProperties

        props = DichroicProperties(
            cutoff_wavelength_nm=550.0, transition_width_nm=50.0, pass_type="longpass"
        )

        assert props.cutoff_wavelength_nm == 550.0
        assert props.transition_width_nm == 50.0
        assert props.pass_type == "longpass"

    def test_properties_are_serializable(self):
        """Test that all properties can be converted to dict"""
        from optiverse.data.optical_properties import (
            BeamsplitterProperties,
            DichroicProperties,
            LensProperties,
            MirrorProperties,
            RefractiveProperties,
            WaveplateProperties,
        )

        props_list = [
            RefractiveProperties(n1=1.0, n2=1.5),
            LensProperties(efl_mm=100.0),
            MirrorProperties(),
            BeamsplitterProperties(transmission=0.5, reflection=0.5),
            WaveplateProperties(phase_shift_deg=90.0, fast_axis_deg=45.0),
            DichroicProperties(
                cutoff_wavelength_nm=550.0, transition_width_nm=50.0, pass_type="longpass"
            ),
        ]

        for props in props_list:
            # Should be able to convert to dict
            props_dict = asdict(props)
            assert isinstance(props_dict, dict)


class TestLineSegment:
    """Test line segment geometry"""

    def test_line_segment_creation(self):
        """Test creating a line segment"""
        from optiverse.data.geometry import LineSegment

        p1 = np.array([0.0, -10.0])
        p2 = np.array([0.0, 10.0])

        segment = LineSegment(p1=p1, p2=p2)

        assert np.array_equal(segment.p1, p1)
        assert np.array_equal(segment.p2, p2)

    def test_line_segment_length(self):
        """Test computing line segment length"""
        from optiverse.data.geometry import LineSegment

        p1 = np.array([0.0, 0.0])
        p2 = np.array([3.0, 4.0])

        segment = LineSegment(p1=p1, p2=p2)

        assert segment.length() == 5.0  # 3-4-5 triangle

    def test_line_segment_midpoint(self):
        """Test computing line segment midpoint"""
        from optiverse.data.geometry import LineSegment

        p1 = np.array([0.0, 0.0])
        p2 = np.array([10.0, 20.0])

        segment = LineSegment(p1=p1, p2=p2)
        midpoint = segment.midpoint()

        assert np.array_equal(midpoint, np.array([5.0, 10.0]))

    def test_line_segment_direction(self):
        """Test computing line segment direction (normalized)"""
        from optiverse.data.geometry import LineSegment

        p1 = np.array([0.0, 0.0])
        p2 = np.array([3.0, 4.0])

        segment = LineSegment(p1=p1, p2=p2)
        direction = segment.direction()

        expected = np.array([0.6, 0.8])  # [3, 4] normalized
        assert np.allclose(direction, expected)

    def test_line_segment_normal(self):
        """Test computing line segment normal (perpendicular)"""
        from optiverse.data.geometry import LineSegment

        p1 = np.array([0.0, 0.0])
        p2 = np.array([1.0, 0.0])  # Horizontal line

        segment = LineSegment(p1=p1, p2=p2)
        normal = segment.normal()

        # Normal to horizontal line should be vertical
        expected = np.array([0.0, 1.0])
        assert np.allclose(normal, expected)


class TestOpticalInterface:
    """Test unified optical interface model"""

    def test_create_lens_interface(self):
        """Test creating a lens interface"""
        from optiverse.data.geometry import LineSegment
        from optiverse.data.optical_interface import OpticalInterface
        from optiverse.data.optical_properties import LensProperties

        geometry = LineSegment(p1=np.array([0.0, -15.0]), p2=np.array([0.0, 15.0]))
        properties = LensProperties(efl_mm=100.0)

        interface = OpticalInterface(geometry=geometry, properties=properties, name="Test Lens")

        assert interface.name == "Test Lens"
        assert interface.geometry.length() == 30.0
        assert interface.properties.efl_mm == 100.0

    def test_create_mirror_interface(self):
        """Test creating a mirror interface"""
        from optiverse.data.geometry import LineSegment
        from optiverse.data.optical_interface import OpticalInterface
        from optiverse.data.optical_properties import MirrorProperties

        geometry = LineSegment(p1=np.array([0.0, -20.0]), p2=np.array([0.0, 20.0]))
        properties = MirrorProperties(reflectivity=0.99)

        interface = OpticalInterface(geometry=geometry, properties=properties)

        assert interface.properties.reflectivity == 0.99

    def test_create_refractive_interface(self):
        """Test creating a refractive interface"""
        from optiverse.data.geometry import LineSegment
        from optiverse.data.optical_interface import OpticalInterface
        from optiverse.data.optical_properties import RefractiveProperties

        geometry = LineSegment(p1=np.array([0.0, -5.0]), p2=np.array([0.0, 5.0]))
        properties = RefractiveProperties(n1=1.0, n2=1.5)

        interface = OpticalInterface(
            geometry=geometry, properties=properties, name="Air-Glass Interface"
        )

        assert interface.properties.n1 == 1.0
        assert interface.properties.n2 == 1.5
        assert interface.name == "Air-Glass Interface"

    def test_interface_get_element_type(self):
        """Test getting element type from interface"""
        from optiverse.data.geometry import LineSegment
        from optiverse.data.optical_interface import OpticalInterface
        from optiverse.data.optical_properties import (
            BeamsplitterProperties,
            DichroicProperties,
            LensProperties,
            MirrorProperties,
            RefractiveProperties,
            WaveplateProperties,
        )

        geometry = LineSegment(p1=np.array([0.0, -5.0]), p2=np.array([0.0, 5.0]))

        # Test different property types
        test_cases = [
            (LensProperties(efl_mm=100.0), "lens"),
            (MirrorProperties(), "mirror"),
            (RefractiveProperties(n1=1.0, n2=1.5), "refractive"),
            (BeamsplitterProperties(transmission=0.5, reflection=0.5), "beamsplitter"),
            (WaveplateProperties(phase_shift_deg=90.0, fast_axis_deg=0.0), "waveplate"),
            (
                DichroicProperties(
                    cutoff_wavelength_nm=550.0, transition_width_nm=50.0, pass_type="longpass"
                ),
                "dichroic",
            ),
        ]

        for properties, expected_type in test_cases:
            interface = OpticalInterface(geometry=geometry, properties=properties)
            assert interface.get_element_type() == expected_type

    def test_interface_serialization(self):
        """Test interface serialization to dict"""
        from optiverse.data.geometry import LineSegment
        from optiverse.data.optical_interface import OpticalInterface
        from optiverse.data.optical_properties import LensProperties

        geometry = LineSegment(p1=np.array([0.0, -15.0]), p2=np.array([0.0, 15.0]))
        properties = LensProperties(efl_mm=100.0)

        interface = OpticalInterface(geometry=geometry, properties=properties, name="Test Lens")

        # Serialize
        data = interface.to_dict()

        # Check structure
        assert "geometry" in data
        assert "properties" in data
        assert "property_type" in data
        assert "name" in data

        assert data["geometry"]["p1"] == [0.0, -15.0]
        assert data["geometry"]["p2"] == [0.0, 15.0]
        assert data["properties"]["efl_mm"] == 100.0
        assert data["property_type"] == "lens"
        assert data["name"] == "Test Lens"

    def test_interface_deserialization(self):
        """Test interface deserialization from dict"""
        from optiverse.data.optical_interface import OpticalInterface

        data = {
            "geometry": {"p1": [0.0, -15.0], "p2": [0.0, 15.0]},
            "properties": {"efl_mm": 100.0},
            "property_type": "lens",
            "name": "Test Lens",
        }

        # Deserialize
        interface = OpticalInterface.from_dict(data)

        # Check values
        assert np.array_equal(interface.geometry.p1, np.array([0.0, -15.0]))
        assert np.array_equal(interface.geometry.p2, np.array([0.0, 15.0]))
        assert interface.properties.efl_mm == 100.0
        assert interface.name == "Test Lens"

    def test_interface_roundtrip_serialization(self):
        """Test that serialization roundtrip preserves data"""
        from optiverse.data.geometry import LineSegment
        from optiverse.data.optical_interface import OpticalInterface
        from optiverse.data.optical_properties import RefractiveProperties

        # Create interface
        original = OpticalInterface(
            geometry=LineSegment(p1=np.array([1.0, 2.0]), p2=np.array([3.0, 4.0])),
            properties=RefractiveProperties(n1=1.0, n2=1.5, curvature_radius_mm=50.0),
            name="Glass Surface",
        )

        # Roundtrip
        data = original.to_dict()
        restored = OpticalInterface.from_dict(data)

        # Check everything matches
        assert np.array_equal(restored.geometry.p1, original.geometry.p1)
        assert np.array_equal(restored.geometry.p2, original.geometry.p2)
        assert restored.properties.n1 == original.properties.n1
        assert restored.properties.n2 == original.properties.n2
        assert restored.properties.curvature_radius_mm == original.properties.curvature_radius_mm
        assert restored.name == original.name


class TestBackwardCompatibility:
    """Test backward compatibility with old InterfaceDefinition format"""

    def test_convert_from_old_interface_definition(self):
        """Test converting old InterfaceDefinition to new OpticalInterface"""
        from optiverse.core.interface_definition import InterfaceDefinition
        from optiverse.data.optical_interface import OpticalInterface

        # Create old-style interface
        old_interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-10.0,
            x2_mm=0.0,
            y2_mm=10.0,
            element_type="lens",
            efl_mm=100.0,
            name="Old Lens",
        )

        # Convert to new format
        new_interface = OpticalInterface.from_legacy_interface_definition(old_interface)

        # Check conversion
        assert np.array_equal(new_interface.geometry.p1, np.array([0.0, -10.0]))
        assert np.array_equal(new_interface.geometry.p2, np.array([0.0, 10.0]))
        assert new_interface.properties.efl_mm == 100.0
        assert new_interface.name == "Old Lens"

    def test_convert_from_old_refractive_interface(self):
        """Test converting old RefractiveInterface to new OpticalInterface"""
        from optiverse.core.models import RefractiveInterface
        from optiverse.data.optical_interface import OpticalInterface

        # Create old-style refractive interface
        old_interface = RefractiveInterface(
            x1_mm=0.0, y1_mm=-5.0, x2_mm=0.0, y2_mm=5.0, n1=1.0, n2=1.5, is_beam_splitter=False
        )

        # Convert to new format
        new_interface = OpticalInterface.from_legacy_refractive_interface(old_interface)

        # Check conversion
        assert np.array_equal(new_interface.geometry.p1, np.array([0.0, -5.0]))
        assert np.array_equal(new_interface.geometry.p2, np.array([0.0, 5.0]))
        assert new_interface.properties.n1 == 1.0
        assert new_interface.properties.n2 == 1.5


class TestTypeChecking:
    """Test type checking with isinstance for Union types"""

    def test_type_checking_lens_properties(self):
        """Test type checking for lens properties"""
        from optiverse.data.optical_properties import LensProperties, MirrorProperties

        lens_props = LensProperties(efl_mm=100.0)
        mirror_props = MirrorProperties()

        assert isinstance(lens_props, LensProperties)
        assert not isinstance(lens_props, MirrorProperties)
        assert isinstance(mirror_props, MirrorProperties)
        assert not isinstance(mirror_props, LensProperties)

    def test_interface_property_type_checking(self):
        """Test checking what type of properties an interface has"""
        from optiverse.data.geometry import LineSegment
        from optiverse.data.optical_interface import OpticalInterface
        from optiverse.data.optical_properties import (
            LensProperties,
            MirrorProperties,
            RefractiveProperties,
        )

        geometry = LineSegment(p1=np.array([0.0, -5.0]), p2=np.array([0.0, 5.0]))

        # Test with different property types
        lens_interface = OpticalInterface(
            geometry=geometry, properties=LensProperties(efl_mm=100.0)
        )
        mirror_interface = OpticalInterface(geometry=geometry, properties=MirrorProperties())
        refractive_interface = OpticalInterface(
            geometry=geometry, properties=RefractiveProperties(n1=1.0, n2=1.5)
        )

        assert isinstance(lens_interface.properties, LensProperties)
        assert isinstance(mirror_interface.properties, MirrorProperties)
        assert isinstance(refractive_interface.properties, RefractiveProperties)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
