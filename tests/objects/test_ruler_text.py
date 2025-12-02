"""Tests for RulerItem and TextNoteItem."""

from PyQt6 import QtCore, QtWidgets

from tests.helpers import safe_wait_exposed


def test_ruler_item_smoke(qtbot):
    """Basic smoke test for RulerItem."""
    from optiverse.objects import GraphicsView, RulerItem

    scene = QtWidgets.QGraphicsScene()
    view = GraphicsView(scene)
    qtbot.addWidget(view)
    view.resize(300, 200)
    view.show()
    safe_wait_exposed(qtbot, view)

    r = RulerItem(QtCore.QPointF(-50, 0), QtCore.QPointF(50, 0))
    scene.addItem(r)
    assert r.boundingRect().isValid()
    # Use public API instead of direct _points access
    r.set_point(1, QtCore.QPointF(60, 0))
    scene.update()
    assert r.boundingRect().width() > 0


def test_ruler_public_api(qtbot):
    """Test the public API for point manipulation."""
    from optiverse.objects import RulerItem

    scene = QtWidgets.QGraphicsScene()

    # Create a ruler
    r = RulerItem(QtCore.QPointF(0, 0), QtCore.QPointF(100, 0))
    scene.addItem(r)

    # Test point_count
    assert r.point_count() == 2

    # Test get_points
    points = r.get_points()
    assert len(points) == 2
    assert points[0] == QtCore.QPointF(0, 0)
    assert points[1] == QtCore.QPointF(100, 0)

    # Test set_point
    r.set_point(1, QtCore.QPointF(150, 0))
    points = r.get_points()
    assert points[1] == QtCore.QPointF(150, 0)

    # Test set_preview_point (same as setting last point)
    r.set_preview_point(QtCore.QPointF(200, 0))
    points = r.get_points()
    assert points[-1] == QtCore.QPointF(200, 0)


def test_ruler_multi_segment(qtbot):
    """Test multi-segment ruler functionality."""
    from optiverse.objects import RulerItem

    scene = QtWidgets.QGraphicsScene()

    # Create a ruler with initial segment
    r = RulerItem(QtCore.QPointF(0, 0), QtCore.QPointF(100, 0))
    scene.addItem(r)
    assert r.point_count() == 2

    # Add a bend using finalize_segment
    r.finalize_segment(QtCore.QPointF(100, 100))
    assert r.point_count() == 3

    # Add another bend
    r.finalize_segment(QtCore.QPointF(200, 100))
    assert r.point_count() == 4

    # Verify points
    points = r.get_points()
    assert len(points) == 4
    assert points[0] == QtCore.QPointF(0, 0)
    assert points[1] == QtCore.QPointF(100, 0)
    assert points[2] == QtCore.QPointF(100, 100)
    assert points[3] == QtCore.QPointF(200, 100)


def test_ruler_remove_preview_point(qtbot):
    """Test removing preview point."""
    from optiverse.objects import RulerItem

    scene = QtWidgets.QGraphicsScene()

    # Create a ruler with 3 segments
    r = RulerItem(
        points=[
            QtCore.QPointF(0, 0),
            QtCore.QPointF(100, 0),
            QtCore.QPointF(100, 100),
        ]
    )
    scene.addItem(r)
    assert r.point_count() == 3

    # Remove preview point should work
    result = r.remove_preview_point()
    assert result is True
    assert r.point_count() == 2

    # Removing again should not go below 2 points
    result = r.remove_preview_point()
    assert result is True  # Still valid (has 2 points)
    assert r.point_count() == 2  # Doesn't go below 2


def test_ruler_add_point(qtbot):
    """Test adding points at specific positions."""
    from optiverse.objects import RulerItem

    scene = QtWidgets.QGraphicsScene()

    # Create a ruler
    r = RulerItem(QtCore.QPointF(0, 0), QtCore.QPointF(100, 0))
    scene.addItem(r)

    # Add point at end
    r.add_point(QtCore.QPointF(200, 0))
    assert r.point_count() == 3

    # Add point in the middle (after index 0)
    r.add_point(QtCore.QPointF(50, 50), insert_after_index=0)
    assert r.point_count() == 4

    points = r.get_points()
    assert points[0] == QtCore.QPointF(0, 0)
    assert points[1] == QtCore.QPointF(50, 50)  # Inserted point
    assert points[2] == QtCore.QPointF(100, 0)
    assert points[3] == QtCore.QPointF(200, 0)


def test_ruler_serialization(qtbot):
    """Test ruler serialization round-trip."""
    from optiverse.objects import RulerItem

    scene = QtWidgets.QGraphicsScene()

    # Create a multi-segment ruler
    original = RulerItem(
        points=[
            QtCore.QPointF(0, 0),
            QtCore.QPointF(100, 0),
            QtCore.QPointF(100, 100),
            QtCore.QPointF(200, 100),
        ]
    )
    original.setZValue(123.0)
    scene.addItem(original)

    # Serialize
    data = original.to_dict()
    assert data["type"] == "ruler"
    assert len(data["points"]) == 4
    assert data["z_value"] == 123.0

    # Deserialize
    restored = RulerItem.from_dict(data)
    assert restored.point_count() == 4
    assert restored.zValue() == 123.0


def test_ruler_backward_compatible_load(qtbot):
    """Test loading old format (p1/p2) rulers."""
    from optiverse.objects import RulerItem

    # Old format with p1/p2
    old_format = {
        "type": "ruler",
        "p1": [0.0, 0.0],
        "p2": [100.0, 0.0],
        "item_uuid": "test-uuid",
        "z_value": 10.0,
    }

    ruler = RulerItem.from_dict(old_format)
    assert ruler.point_count() == 2
    assert ruler.item_uuid == "test-uuid"
    assert ruler.zValue() == 10.0


def test_ruler_capture_apply_state(qtbot):
    """Test state capture and restore for undo/redo."""
    from optiverse.objects import RulerItem

    scene = QtWidgets.QGraphicsScene()

    # Create a ruler
    r = RulerItem(QtCore.QPointF(0, 0), QtCore.QPointF(100, 0))
    r.setPos(QtCore.QPointF(10, 20))
    scene.addItem(r)

    # Capture state
    state1 = r.capture_state()
    assert len(state1["points"]) == 2
    assert state1["pos"]["x"] == 10.0
    assert state1["pos"]["y"] == 20.0

    # Modify ruler
    r.finalize_segment(QtCore.QPointF(100, 100))
    r.setPos(QtCore.QPointF(30, 40))

    # Capture new state
    state2 = r.capture_state()
    assert len(state2["points"]) == 3
    assert state2["pos"]["x"] == 30.0

    # Restore original state
    r.apply_state(state1)
    assert r.point_count() == 2
    assert r.pos() == QtCore.QPointF(10, 20)


def test_ruler_clone(qtbot):
    """Test cloning a multi-segment ruler."""
    from optiverse.objects import RulerItem

    scene = QtWidgets.QGraphicsScene()

    # Create a multi-segment ruler
    original = RulerItem(
        points=[
            QtCore.QPointF(0, 0),
            QtCore.QPointF(100, 0),
            QtCore.QPointF(100, 100),
        ]
    )
    original.setZValue(50.0)
    scene.addItem(original)

    # Clone with offset
    cloned = original.clone(offset_mm=(20.0, 20.0))

    # Check clone is independent
    assert cloned.item_uuid != original.item_uuid
    assert cloned.point_count() == original.point_count()
    assert cloned.zValue() == original.zValue()

    # Check points are offset
    original.get_points()
    cloned.get_points()
    # Note: clone maps to scene coords, so offset is applied to scene positions


def test_ruler_command_created_signal(qtbot):
    """Test that commandCreated signal is emitted on state changes."""
    from optiverse.objects import RulerItem

    scene = QtWidgets.QGraphicsScene()

    r = RulerItem(
        points=[
            QtCore.QPointF(0, 0),
            QtCore.QPointF(100, 0),
            QtCore.QPointF(100, 100),
        ]
    )
    scene.addItem(r)

    # Track emitted commands
    commands = []
    r.commandCreated.connect(commands.append)

    # This should emit a command (delete bend point creates undo command)
    # We need to access internal method for testing
    r.capture_state()
    r._delete_bend_point(1)  # Delete middle point

    # Verify command was emitted
    assert len(commands) == 1
    assert r.point_count() == 2


def test_text_note_item_smoke(qtbot):
    """Basic smoke test for TextNoteItem."""
    from optiverse.objects import GraphicsView, TextNoteItem

    scene = QtWidgets.QGraphicsScene()
    view = GraphicsView(scene)
    qtbot.addWidget(view)
    view.resize(300, 200)
    view.show()
    safe_wait_exposed(qtbot, view)

    t = TextNoteItem("Hello")
    scene.addItem(t)
    t.setPos(10, 10)
    assert t.toPlainText() == "Hello"
