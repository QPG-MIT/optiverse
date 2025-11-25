"""Tests for AngleMeasureItem and PathMeasureItem."""

import numpy as np
from PyQt6 import QtCore, QtWidgets


def test_angle_measure_item_smoke(qtbot):
    """Basic smoke test for AngleMeasureItem."""
    from optiverse.objects import GraphicsView
    from optiverse.objects.annotations.angle_measure_item import AngleMeasureItem

    scene = QtWidgets.QGraphicsScene()
    view = GraphicsView(scene)
    qtbot.addWidget(view)
    view.resize(300, 200)
    view.show()
    qtbot.waitExposed(view)

    # Create angle measure with 90 degree angle
    vertex = QtCore.QPointF(0, 0)
    point1 = QtCore.QPointF(100, 0)
    point2 = QtCore.QPointF(0, 100)

    item = AngleMeasureItem(vertex, point1, point2)
    scene.addItem(item)

    assert item.boundingRect().isValid()
    assert item.item_uuid is not None

    # Check angle is approximately 90 degrees
    assert abs(item.angle - 90.0) < 0.1


def test_angle_measure_item_angle_calculation():
    """Test angle calculation for various angles."""
    from optiverse.objects.annotations.angle_measure_item import AngleMeasureItem

    scene = QtWidgets.QGraphicsScene()

    # 45 degree angle
    vertex = QtCore.QPointF(0, 0)
    point1 = QtCore.QPointF(100, 0)
    point2 = QtCore.QPointF(100, 100)

    item = AngleMeasureItem(vertex, point1, point2)
    scene.addItem(item)

    assert abs(item.angle - 45.0) < 0.1

    # 180 degree angle (straight line)
    vertex2 = QtCore.QPointF(0, 0)
    point1_2 = QtCore.QPointF(100, 0)
    point2_2 = QtCore.QPointF(-100, 0)

    item2 = AngleMeasureItem(vertex2, point1_2, point2_2)
    scene.addItem(item2)

    assert abs(item2.angle - 180.0) < 0.1


def test_angle_measure_item_serialization():
    """Test angle measure serialization round-trip."""
    from optiverse.objects.annotations.angle_measure_item import AngleMeasureItem

    scene = QtWidgets.QGraphicsScene()

    vertex = QtCore.QPointF(10, 20)
    point1 = QtCore.QPointF(110, 20)
    point2 = QtCore.QPointF(10, 120)

    original = AngleMeasureItem(vertex, point1, point2)
    original.setZValue(123.0)
    scene.addItem(original)

    # Serialize
    data = original.to_dict()
    assert data["type"] == "angle_measure"
    assert data["z_value"] == 123.0

    # Deserialize
    restored = AngleMeasureItem.from_dict(data)
    assert restored.zValue() == 123.0
    assert abs(restored.angle - original.angle) < 0.1


def test_angle_measure_item_capture_apply_state():
    """Test state capture and restore for undo/redo."""
    from optiverse.objects.annotations.angle_measure_item import AngleMeasureItem

    scene = QtWidgets.QGraphicsScene()

    vertex = QtCore.QPointF(0, 0)
    point1 = QtCore.QPointF(100, 0)
    point2 = QtCore.QPointF(0, 100)

    item = AngleMeasureItem(vertex, point1, point2)
    scene.addItem(item)

    # Capture initial state
    state1 = item.capture_state()
    angle1 = item.angle

    # Modify the item by setting point2
    item.set_point2(QtCore.QPointF(50, 50))
    angle2 = item.angle

    # Verify angle changed
    assert abs(angle1 - angle2) > 1.0

    # Restore original state
    item.apply_state(state1)

    # Verify angle restored
    assert abs(item.angle - angle1) < 0.1


def test_angle_measure_item_has_command_signal():
    """Test that AngleMeasureItem has commandCreated and requestDelete signals."""
    from optiverse.objects.annotations.angle_measure_item import AngleMeasureItem

    item = AngleMeasureItem(QtCore.QPointF(0, 0), QtCore.QPointF(100, 0), QtCore.QPointF(0, 100))

    # Verify signals exist
    assert hasattr(item, "commandCreated")
    assert hasattr(item, "requestDelete")


def test_path_measure_item_smoke(qtbot):
    """Basic smoke test for PathMeasureItem."""
    from optiverse.objects import GraphicsView
    from optiverse.objects.annotations.path_measure_item import PathMeasureItem

    scene = QtWidgets.QGraphicsScene()
    view = GraphicsView(scene)
    qtbot.addWidget(view)
    view.resize(300, 200)
    view.show()
    qtbot.waitExposed(view)

    # Create path measure with simple path
    points = [np.array([0, 0]), np.array([100, 0]), np.array([100, 100])]

    item = PathMeasureItem(ray_path_points=points, start_param=0.0, end_param=1.0, ray_index=0)
    scene.addItem(item)

    assert item.boundingRect().isValid()
    assert item.item_uuid is not None

    # Check segment length (should be 200: 100 + 100)
    assert abs(item.segment_length - 200.0) < 0.1


def test_path_measure_item_partial_path():
    """Test path measure with partial path (not full path)."""
    from optiverse.objects.annotations.path_measure_item import PathMeasureItem

    scene = QtWidgets.QGraphicsScene()

    # Create path with 3 segments of 100mm each
    points = [np.array([0, 0]), np.array([100, 0]), np.array([200, 0]), np.array([300, 0])]

    # Measure only the middle portion
    item = PathMeasureItem(
        ray_path_points=points,
        start_param=0.25,  # 75mm from start
        end_param=0.75,  # 225mm from start
        ray_index=0,
    )
    scene.addItem(item)

    # Should measure 150mm
    assert abs(item.segment_length - 150.0) < 1.0


def test_path_measure_item_capture_apply_state():
    """Test state capture and restore for undo/redo."""
    from optiverse.objects.annotations.path_measure_item import PathMeasureItem

    scene = QtWidgets.QGraphicsScene()

    points = [np.array([0, 0]), np.array([100, 0]), np.array([200, 0])]

    item = PathMeasureItem(ray_path_points=points, start_param=0.0, end_param=1.0, ray_index=0)
    scene.addItem(item)

    # Capture initial state
    state1 = item.capture_state()
    length1 = item.segment_length

    # Modify the item
    item.start_param = 0.25
    item.end_param = 0.75
    item.apply_state({"start_param": 0.25, "end_param": 0.75})
    length2 = item.segment_length

    # Verify length changed
    assert abs(length1 - length2) > 1.0

    # Restore original state
    item.apply_state(state1)

    # Verify length restored
    assert abs(item.segment_length - length1) < 0.1


def test_path_measure_item_has_command_signal():
    """Test that PathMeasureItem has commandCreated and requestDelete signals."""
    from optiverse.objects.annotations.path_measure_item import PathMeasureItem

    points = [np.array([0, 0]), np.array([100, 0])]
    item = PathMeasureItem(ray_path_points=points)

    # Verify signals exist
    assert hasattr(item, "commandCreated")
    assert hasattr(item, "requestDelete")


def test_path_measure_item_serialization():
    """Test path measure serialization."""
    from optiverse.objects.annotations.path_measure_item import PathMeasureItem

    scene = QtWidgets.QGraphicsScene()

    points = [np.array([0, 0]), np.array([100, 0]), np.array([100, 100])]

    original = PathMeasureItem(
        ray_path_points=points, start_param=0.1, end_param=0.9, ray_index=5, label_prefix="Test: "
    )
    original.setZValue(456.0)
    scene.addItem(original)

    # Serialize
    data = original.to_dict()
    assert data["type"] == "path_measure"
    assert data["ray_index"] == 5
    assert abs(data["start_param"] - 0.1) < 0.01
    assert abs(data["end_param"] - 0.9) < 0.01
    assert data["z_value"] == 456.0
    assert data["label_prefix"] == "Test: "


def test_ruler_item_has_delete_signal():
    """Test that RulerItem has requestDelete signal."""
    from optiverse.objects.annotations.ruler_item import RulerItem

    item = RulerItem(QtCore.QPointF(0, 0), QtCore.QPointF(100, 0))

    # Verify signal exists
    assert hasattr(item, "requestDelete")
