"""Tests for ComponentRecord dataclass and serialization."""

import pytest

from optiverse.core.models import ComponentRecord, deserialize_component, serialize_component


def test_component_record_lens():
    """Test ComponentRecord creation for lens."""
    rec = ComponentRecord(
        name="Test Lens",
        kind="lens",
        image_path="/path/to/image.png",
        mm_per_pixel=0.5,
        line_px=(10.0, 20.0, 90.0, 20.0),
        length_mm=40.0,
        efl_mm=100.0,
        split_TR=(50.0, 50.0),
        notes="Test notes",
    )
    assert rec.name == "Test Lens"
    assert rec.kind == "lens"
    assert rec.efl_mm == 100.0
    assert rec.length_mm == 40.0


def test_component_record_mirror():
    """Test ComponentRecord creation for mirror."""
    rec = ComponentRecord(
        name="Test Mirror",
        kind="mirror",
        image_path="/path/to/mirror.png",
        mm_per_pixel=0.3,
        line_px=(0.0, 0.0, 50.0, 50.0),
        length_mm=70.7,
        efl_mm=0.0,
        split_TR=(50.0, 50.0),
        notes="",
    )
    assert rec.kind == "mirror"
    assert rec.efl_mm == 0.0
    assert rec.length_mm == pytest.approx(70.7)


def test_component_record_beamsplitter():
    """Test ComponentRecord creation for beamsplitter."""
    rec = ComponentRecord(
        name="50/50 BS",
        kind="beamsplitter",
        image_path="/path/to/bs.png",
        mm_per_pixel=0.2,
        line_px=(0.0, 0.0, 100.0, 0.0),
        length_mm=20.0,
        efl_mm=0.0,
        split_TR=(30.0, 70.0),
        notes="Custom split ratio",
    )
    assert rec.kind == "beamsplitter"
    assert rec.split_TR == (30.0, 70.0)


def test_serialize_lens():
    """Test lens serialization includes only relevant fields."""
    rec = ComponentRecord(
        name="Lens1",
        kind="lens",
        image_path="/img.png",
        mm_per_pixel=0.5,
        line_px=(0.0, 0.0, 10.0, 0.0),
        length_mm=5.0,
        efl_mm=75.0,
        split_TR=(50.0, 50.0),
        notes="Note",
    )
    data = serialize_component(rec)
    assert data["name"] == "Lens1"
    assert data["kind"] == "lens"
    assert data["efl_mm"] == 75.0
    assert data["length_mm"] == 5.0
    assert data["notes"] == "Note"
    # Should not include beamsplitter fields for lens
    assert "split_TR" not in data
    assert "split_T" not in data
    assert "split_R" not in data


def test_serialize_mirror():
    """Test mirror serialization excludes type-specific fields."""
    rec = ComponentRecord(
        name="Mirror1",
        kind="mirror",
        image_path="/img.png",
        mm_per_pixel=0.5,
        line_px=(0.0, 0.0, 10.0, 0.0),
        length_mm=5.0,
        efl_mm=0.0,
        split_TR=(50.0, 50.0),
        notes="",
    )
    data = serialize_component(rec)
    assert data["kind"] == "mirror"
    # Mirror should not have efl or split fields
    assert "efl_mm" not in data
    assert "split_TR" not in data


def test_serialize_beamsplitter():
    """Test beamsplitter serialization includes T/R with legacy compatibility."""
    rec = ComponentRecord(
        name="BS1",
        kind="beamsplitter",
        image_path="/img.png",
        mm_per_pixel=0.5,
        line_px=(0.0, 0.0, 10.0, 0.0),
        length_mm=5.0,
        efl_mm=0.0,
        split_TR=(40.0, 60.0),
        notes="",
    )
    data = serialize_component(rec)
    assert data["split_TR"] == [40.0, 60.0]
    # Legacy backward compatibility
    assert data["split_T"] == 40.0
    assert data["split_R"] == 60.0
    # Should not include efl for beamsplitter
    assert "efl_mm" not in data


def test_deserialize_lens():
    """Test lens deserialization."""
    data = {
        "name": "TestLens",
        "kind": "lens",
        "image_path": "/test.png",
        "mm_per_pixel": 0.25,
        "line_px": [5.0, 5.0, 15.0, 5.0],
        "length_mm": 2.5,
        "efl_mm": 50.0,
        "notes": "My lens",
    }
    rec = deserialize_component(data)
    assert rec.name == "TestLens"
    assert rec.kind == "lens"
    assert rec.efl_mm == 50.0
    assert rec.line_px == (5.0, 5.0, 15.0, 5.0)
    assert rec.notes == "My lens"


def test_deserialize_mirror():
    """Test mirror deserialization."""
    data = {
        "name": "TestMirror",
        "kind": "mirror",
        "image_path": "/mirror.png",
        "mm_per_pixel": 0.1,
        "line_px": [0.0, 0.0, 10.0, 10.0],
        "length_mm": 14.14,
        "notes": "",
    }
    rec = deserialize_component(data)
    assert rec.kind == "mirror"
    assert rec.efl_mm == 0.0
    assert rec.length_mm == pytest.approx(14.14)


def test_deserialize_beamsplitter_new_format():
    """Test beamsplitter deserialization with new split_TR format."""
    data = {
        "name": "BS",
        "kind": "beamsplitter",
        "image_path": "/bs.png",
        "mm_per_pixel": 0.2,
        "line_px": [0.0, 0.0, 20.0, 0.0],
        "length_mm": 4.0,
        "split_TR": [30.0, 70.0],
        "notes": "",
    }
    rec = deserialize_component(data)
    assert rec.kind == "beamsplitter"
    assert rec.split_TR == (30.0, 70.0)


def test_deserialize_beamsplitter_legacy_format():
    """Test beamsplitter deserialization with legacy split_T/split_R."""
    data = {
        "name": "BS",
        "kind": "beamsplitter",
        "image_path": "/bs.png",
        "mm_per_pixel": 0.2,
        "line_px": [0.0, 0.0, 20.0, 0.0],
        "length_mm": 4.0,
        "split_T": 25.0,
        "split_R": 75.0,
        "notes": "",
    }
    rec = deserialize_component(data)
    assert rec.split_TR == (25.0, 75.0)


def test_deserialize_handles_missing_fields():
    """Test deserialization handles missing optional fields gracefully."""
    data = {
        "name": "Minimal",
        "kind": "lens",
        "image_path": "",
        "mm_per_pixel": 0.1,
        "line_px": [0.0, 0.0, 1.0, 0.0],
        "length_mm": 0.1,
    }
    rec = deserialize_component(data)
    assert rec.name == "Minimal"
    assert rec.efl_mm == 0.0
    assert rec.notes == ""


def test_deserialize_ignores_unknown_keys():
    """Test that unknown keys in JSON are silently ignored."""
    data = {
        "name": "Test",
        "kind": "lens",
        "image_path": "/test.png",
        "mm_per_pixel": 0.5,
        "line_px": [0.0, 0.0, 10.0, 0.0],
        "length_mm": 5.0,
        "efl_mm": 100.0,
        "notes": "",
        "unknown_field": "should be ignored",
        "another_unknown": 123,
    }
    rec = deserialize_component(data)
    assert rec.name == "Test"
    assert rec.kind == "lens"


def test_deserialize_malformed_line_px():
    """Test that malformed line_px returns None."""
    data = {
        "name": "Bad",
        "kind": "lens",
        "image_path": "/test.png",
        "mm_per_pixel": 0.5,
        "line_px": [0.0, 0.0, 10.0],  # Only 3 values
        "length_mm": 5.0,
    }
    rec = deserialize_component(data)
    assert rec is None


def test_roundtrip_serialization():
    """Test that serialize -> deserialize preserves data."""
    original = ComponentRecord(
        name="Roundtrip Test",
        kind="beamsplitter",
        image_path="/path/test.png",
        mm_per_pixel=0.123,
        line_px=(1.5, 2.5, 3.5, 4.5),
        length_mm=12.34,
        efl_mm=0.0,
        split_TR=(35.5, 64.5),
        notes="Round and round",
    )
    data = serialize_component(original)
    restored = deserialize_component(data)

    assert restored.name == original.name
    assert restored.kind == original.kind
    assert restored.image_path == original.image_path
    assert restored.mm_per_pixel == pytest.approx(original.mm_per_pixel)
    assert restored.line_px == original.line_px
    assert restored.length_mm == pytest.approx(original.length_mm)
    assert restored.split_TR == original.split_TR
    assert restored.notes == original.notes
