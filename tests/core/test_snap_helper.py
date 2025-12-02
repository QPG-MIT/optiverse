"""
Tests for magnetic snap helper functionality.

Tests snap calculations for center-to-center and edge-to-edge alignment.
"""

from PyQt6 import QtCore, QtWidgets

from optiverse.core.snap_helper import SnapHelper, SnapResult
from tests.fixtures.factories import create_lens_item, create_mirror_item


def test_snap_result_no_snap():
    """Test SnapResult when no snap occurs."""
    result = SnapResult(QtCore.QPointF(100, 200), False, [])
    assert result.position.x() == 100
    assert result.position.y() == 200
    assert not result.snapped
    assert len(result.guide_lines) == 0


def test_snap_result_with_snap():
    """Test SnapResult when snap occurs."""
    guides = [("horizontal", 150.0), ("vertical", 250.0)]
    result = SnapResult(QtCore.QPointF(150, 250), True, guides)
    assert result.position.x() == 150
    assert result.position.y() == 250
    assert result.snapped
    assert len(result.guide_lines) == 2


def test_snap_helper_initialization():
    """Test SnapHelper initialization with default tolerance."""
    helper = SnapHelper(tolerance_px=10.0)
    assert helper.tolerance_px == 10.0


def test_snap_to_center_horizontal(qtbot):
    """Test center-to-center snap on horizontal axis."""
    scene = QtWidgets.QGraphicsScene()

    # Create a fixed lens at (100, 200)
    fixed = create_lens_item(x_mm=100, y_mm=200)
    scene.addItem(fixed)

    # Create moving lens near the same Y coordinate
    moving = create_lens_item(x_mm=300, y_mm=204)  # 4px offset
    scene.addItem(moving)

    helper = SnapHelper(tolerance_px=10.0)

    # Try to snap at position (300, 204)
    result = helper.calculate_snap(QtCore.QPointF(300, 204), moving, scene)

    # Should snap Y to 200 (center of fixed item)
    assert result.snapped
    assert result.position.x() == 300  # X unchanged
    assert result.position.y() == 200  # Y snapped
    assert any(guide[0] == "horizontal" for guide in result.guide_lines)


def test_snap_to_center_vertical(qtbot):
    """Test center-to-center snap on vertical axis."""
    scene = QtWidgets.QGraphicsScene()

    # Create a fixed mirror at (100, 200)
    fixed = create_mirror_item(x_mm=100, y_mm=200)
    scene.addItem(fixed)

    # Create moving mirror near the same X coordinate
    moving = create_mirror_item(x_mm=103, y_mm=400)  # 3px offset
    scene.addItem(moving)

    helper = SnapHelper(tolerance_px=10.0)

    # Try to snap at position (103, 400)
    result = helper.calculate_snap(QtCore.QPointF(103, 400), moving, scene)

    # Should snap X to 100 (center of fixed item)
    assert result.snapped
    assert result.position.x() == 100  # X snapped
    assert result.position.y() == 400  # Y unchanged
    assert any(guide[0] == "vertical" for guide in result.guide_lines)


def test_snap_both_axes(qtbot):
    """Test simultaneous snap on both axes."""
    scene = QtWidgets.QGraphicsScene()

    # Create a fixed lens at (100, 200)
    fixed = create_lens_item(x_mm=100, y_mm=200)
    scene.addItem(fixed)

    # Create moving lens near the same position
    moving = create_lens_item(x_mm=105, y_mm=205)
    scene.addItem(moving)

    helper = SnapHelper(tolerance_px=10.0)

    # Try to snap at position (105, 205)
    result = helper.calculate_snap(QtCore.QPointF(105, 205), moving, scene)

    # Should snap both X and Y
    assert result.snapped
    assert result.position.x() == 100
    assert result.position.y() == 200
    assert any(guide[0] == "horizontal" for guide in result.guide_lines)
    assert any(guide[0] == "vertical" for guide in result.guide_lines)


def test_no_snap_beyond_tolerance(qtbot):
    """Test that no snap occurs beyond tolerance distance."""
    scene = QtWidgets.QGraphicsScene()

    # Create a fixed lens at (100, 200)
    fixed = create_lens_item(x_mm=100, y_mm=200)
    scene.addItem(fixed)

    # Create moving lens far from fixed
    moving = create_lens_item(x_mm=300, y_mm=250)
    scene.addItem(moving)

    helper = SnapHelper(tolerance_px=10.0)

    # Try to snap at position too far away (50px difference)
    result = helper.calculate_snap(QtCore.QPointF(300, 250), moving, scene)

    # Should NOT snap
    assert not result.snapped
    assert result.position.x() == 300
    assert result.position.y() == 250
    assert len(result.guide_lines) == 0


def test_snap_ignores_moving_item(qtbot):
    """Test that snap doesn't consider the moving item itself."""
    scene = QtWidgets.QGraphicsScene()

    # Create only one lens
    moving = create_lens_item(x_mm=100, y_mm=200)
    scene.addItem(moving)

    helper = SnapHelper(tolerance_px=10.0)

    # Try to snap with only itself in the scene
    result = helper.calculate_snap(QtCore.QPointF(105, 205), moving, scene)

    # Should NOT snap (no other items)
    assert not result.snapped
    assert result.position.x() == 105
    assert result.position.y() == 205


def test_snap_multiple_candidates_closest(qtbot):
    """Test that snap chooses the closest candidate."""
    scene = QtWidgets.QGraphicsScene()

    # Create two fixed items at different Y positions
    fixed1 = create_lens_item(x_mm=100, y_mm=200)
    fixed2 = create_lens_item(x_mm=200, y_mm=210)
    scene.addItem(fixed1)
    scene.addItem(fixed2)

    # Create moving item closer to fixed1
    moving = create_lens_item(x_mm=300, y_mm=203)
    scene.addItem(moving)

    helper = SnapHelper(tolerance_px=10.0)

    # Try to snap
    result = helper.calculate_snap(QtCore.QPointF(300, 203), moving, scene)

    # Should snap to 200 (closer) not 210
    assert result.snapped
    assert result.position.y() == 200


def test_snap_with_view_transform(qtbot):
    """Test that snap calculations work with view zoom/transform."""
    scene = QtWidgets.QGraphicsScene()
    view = QtWidgets.QGraphicsView(scene)

    # Zoom in 2x
    view.scale(2.0, 2.0)

    # Create fixed item
    fixed = create_lens_item(x_mm=100, y_mm=200)
    scene.addItem(fixed)

    # Create moving item
    moving = create_lens_item(x_mm=300, y_mm=205)
    scene.addItem(moving)

    helper = SnapHelper(tolerance_px=10.0)

    # Try to snap - should work in scene coordinates
    result = helper.calculate_snap(QtCore.QPointF(300, 205), moving, scene, view)

    # Should still snap (tolerance is in view pixels, converted to scene)
    assert result.snapped
    assert result.position.y() == 200
