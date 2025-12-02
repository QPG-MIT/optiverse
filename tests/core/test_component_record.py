"""Tests for ComponentRecord dataclass and serialization."""

import pytest

from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.core.models import ComponentRecord, deserialize_component, serialize_component


class TestComponentRecordCreation:
    """Test ComponentRecord creation with various configurations."""

    def test_component_record_lens(self):
        """Test ComponentRecord creation with lens interface."""
        lens_interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-20.0,
            x2_mm=0.0,
            y2_mm=20.0,
            element_type="lens",
            efl_mm=100.0,
        )
        rec = ComponentRecord(
            name="Test Lens",
            image_path="/path/to/image.png",
            object_height_mm=40.0,
            interfaces=[lens_interface],
            notes="Test notes",
        )
        assert rec.name == "Test Lens"
        assert rec.object_height_mm == 40.0
        assert len(rec.interfaces) == 1
        assert rec.interfaces[0].element_type == "lens"
        assert rec.interfaces[0].efl_mm == 100.0

    def test_component_record_mirror(self):
        """Test ComponentRecord creation with mirror interface."""
        mirror_interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-35.0,
            x2_mm=0.0,
            y2_mm=35.0,
            element_type="mirror",
            reflectivity=99.9,
        )
        rec = ComponentRecord(
            name="Test Mirror",
            image_path="/path/to/mirror.png",
            object_height_mm=70.0,
            interfaces=[mirror_interface],
            notes="",
        )
        assert rec.name == "Test Mirror"
        assert len(rec.interfaces) == 1
        assert rec.interfaces[0].element_type == "mirror"
        assert rec.interfaces[0].reflectivity == pytest.approx(99.9)

    def test_component_record_beamsplitter(self):
        """Test ComponentRecord creation with beamsplitter interface."""
        bs_interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-10.0,
            x2_mm=0.0,
            y2_mm=10.0,
            element_type="beam_splitter",
            split_T=30.0,
            split_R=70.0,
        )
        rec = ComponentRecord(
            name="50/50 BS",
            image_path="/path/to/bs.png",
            object_height_mm=20.0,
            interfaces=[bs_interface],
            notes="Custom split ratio",
        )
        assert rec.name == "50/50 BS"
        assert len(rec.interfaces) == 1
        assert rec.interfaces[0].element_type == "beam_splitter"
        assert rec.interfaces[0].split_T == 30.0
        assert rec.interfaces[0].split_R == 70.0


class TestSerializeComponent:
    """Test component serialization."""

    def test_serialize_lens(self):
        """Test lens serialization includes only relevant fields."""
        lens_interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-5.0,
            x2_mm=0.0,
            y2_mm=5.0,
            element_type="lens",
            efl_mm=75.0,
        )
        rec = ComponentRecord(
            name="Lens1",
            image_path="/img.png",
            object_height_mm=10.0,
            interfaces=[lens_interface],
            notes="Note",
        )
        data = serialize_component(rec)
        assert data["name"] == "Lens1"
        assert len(data["interfaces"]) == 1
        assert data["interfaces"][0]["element_type"] == "lens"
        assert data["interfaces"][0]["efl_mm"] == 75.0
        assert data["notes"] == "Note"

    def test_serialize_mirror(self):
        """Test mirror serialization includes reflectivity."""
        mirror_interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-25.0,
            x2_mm=0.0,
            y2_mm=25.0,
            element_type="mirror",
            reflectivity=98.0,
        )
        rec = ComponentRecord(
            name="Mirror1",
            image_path="/img.png",
            object_height_mm=50.0,
            interfaces=[mirror_interface],
            notes="",
        )
        data = serialize_component(rec)
        assert len(data["interfaces"]) == 1
        assert data["interfaces"][0]["element_type"] == "mirror"
        assert data["interfaces"][0]["reflectivity"] == 98.0

    def test_serialize_beamsplitter(self):
        """Test beamsplitter serialization includes T/R split."""
        bs_interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-25.0,
            x2_mm=0.0,
            y2_mm=25.0,
            element_type="beam_splitter",
            split_T=40.0,
            split_R=60.0,
        )
        rec = ComponentRecord(
            name="BS1",
            image_path="/img.png",
            object_height_mm=50.0,
            interfaces=[bs_interface],
            notes="",
        )
        data = serialize_component(rec)
        assert len(data["interfaces"]) == 1
        assert data["interfaces"][0]["split_T"] == 40.0
        assert data["interfaces"][0]["split_R"] == 60.0


class TestDeserializeComponent:
    """Test component deserialization."""

    def test_deserialize_lens(self):
        """Test lens deserialization."""
        data = {
            "name": "TestLens",
            "image_path": "/test.png",
            "object_height_mm": 25.4,
            "interfaces": [
                {
                    "x1_mm": 0.0,
                    "y1_mm": -12.7,
                    "x2_mm": 0.0,
                    "y2_mm": 12.7,
                    "element_type": "lens",
                    "efl_mm": 50.0,
                }
            ],
            "notes": "My lens",
        }
        rec = deserialize_component(data)
        assert rec.name == "TestLens"
        assert rec.object_height_mm == 25.4
        assert len(rec.interfaces) == 1
        assert rec.interfaces[0].element_type == "lens"
        assert rec.interfaces[0].efl_mm == 50.0
        assert rec.notes == "My lens"

    def test_deserialize_mirror(self):
        """Test mirror deserialization."""
        data = {
            "name": "TestMirror",
            "image_path": "/mirror.png",
            "object_height_mm": 50.0,
            "interfaces": [
                {
                    "x1_mm": 0.0,
                    "y1_mm": -25.0,
                    "x2_mm": 0.0,
                    "y2_mm": 25.0,
                    "element_type": "mirror",
                    "reflectivity": 99.5,
                }
            ],
            "notes": "",
        }
        rec = deserialize_component(data)
        assert rec.name == "TestMirror"
        assert len(rec.interfaces) == 1
        assert rec.interfaces[0].element_type == "mirror"
        assert rec.interfaces[0].reflectivity == pytest.approx(99.5)

    def test_deserialize_beamsplitter(self):
        """Test beamsplitter deserialization."""
        data = {
            "name": "BS",
            "image_path": "/bs.png",
            "object_height_mm": 40.0,
            "interfaces": [
                {
                    "x1_mm": 0.0,
                    "y1_mm": -20.0,
                    "x2_mm": 0.0,
                    "y2_mm": 20.0,
                    "element_type": "beam_splitter",
                    "split_T": 30.0,
                    "split_R": 70.0,
                }
            ],
            "notes": "",
        }
        rec = deserialize_component(data)
        assert rec.name == "BS"
        assert len(rec.interfaces) == 1
        assert rec.interfaces[0].element_type == "beam_splitter"
        assert rec.interfaces[0].split_T == 30.0
        assert rec.interfaces[0].split_R == 70.0

    def test_deserialize_handles_missing_fields(self):
        """Test deserialization handles missing optional fields gracefully."""
        data = {
            "name": "Minimal",
            "image_path": "",
            "object_height_mm": 25.4,
        }
        rec = deserialize_component(data)
        assert rec.name == "Minimal"
        assert rec.interfaces == []
        assert rec.notes == ""

    def test_deserialize_ignores_unknown_keys(self):
        """Test that unknown keys in JSON are silently ignored."""
        data = {
            "name": "Test",
            "image_path": "/test.png",
            "object_height_mm": 25.4,
            "interfaces": [
                {
                    "x1_mm": 0.0,
                    "y1_mm": -12.7,
                    "x2_mm": 0.0,
                    "y2_mm": 12.7,
                    "element_type": "lens",
                    "efl_mm": 100.0,
                }
            ],
            "notes": "",
            "unknown_field": "should be ignored",
            "another_unknown": 123,
        }
        rec = deserialize_component(data)
        assert rec.name == "Test"
        assert len(rec.interfaces) == 1

    def test_deserialize_invalid_data_returns_none(self):
        """Test that invalid data returns None."""
        rec = deserialize_component("not a dict")
        assert rec is None


class TestRoundtripSerialization:
    """Test roundtrip serialization preserves data."""

    def test_roundtrip_lens(self):
        """Test roundtrip serialization for lens."""
        lens_interface = InterfaceDefinition(
            x1_mm=0.0,
            y1_mm=-12.7,
            x2_mm=0.0,
            y2_mm=12.7,
            element_type="lens",
            efl_mm=75.0,
        )
        original = ComponentRecord(
            name="Roundtrip Lens",
            image_path="/path/test.png",
            object_height_mm=25.4,
            interfaces=[lens_interface],
            angle_deg=90.0,
            notes="Test roundtrip",
        )
        data = serialize_component(original)
        restored = deserialize_component(data)

        assert restored.name == original.name
        assert restored.object_height_mm == pytest.approx(original.object_height_mm)
        assert restored.angle_deg == pytest.approx(original.angle_deg)
        assert restored.notes == original.notes
        assert len(restored.interfaces) == 1
        assert restored.interfaces[0].element_type == "lens"
        assert restored.interfaces[0].efl_mm == pytest.approx(75.0)

    def test_roundtrip_multiple_interfaces(self):
        """Test roundtrip with multiple interfaces (e.g., beam splitter cube)."""
        interfaces = [
            InterfaceDefinition(
                x1_mm=-10.0,
                y1_mm=-20.0,
                x2_mm=-10.0,
                y2_mm=20.0,
                element_type="refractive_interface",
                n1=1.0,
                n2=1.517,
            ),
            InterfaceDefinition(
                x1_mm=-20.0,
                y1_mm=-20.0,
                x2_mm=20.0,
                y2_mm=20.0,
                element_type="beam_splitter",
                split_T=50.0,
                split_R=50.0,
            ),
            InterfaceDefinition(
                x1_mm=10.0,
                y1_mm=-20.0,
                x2_mm=10.0,
                y2_mm=20.0,
                element_type="refractive_interface",
                n1=1.517,
                n2=1.0,
            ),
        ]
        original = ComponentRecord(
            name="BS Cube",
            image_path="/path/cube.png",
            object_height_mm=40.0,
            interfaces=interfaces,
            notes="Multi-interface component",
        )
        data = serialize_component(original)
        restored = deserialize_component(data)

        assert restored.name == original.name
        assert len(restored.interfaces) == 3
        assert restored.interfaces[0].element_type == "refractive_interface"
        assert restored.interfaces[0].n2 == pytest.approx(1.517)
        assert restored.interfaces[1].element_type == "beam_splitter"
        assert restored.interfaces[1].split_T == 50.0
        assert restored.interfaces[2].element_type == "refractive_interface"
        assert restored.interfaces[2].n1 == pytest.approx(1.517)
