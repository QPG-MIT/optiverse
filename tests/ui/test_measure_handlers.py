"""Tests for AngleMeasureToolHandler and PathMeasureToolHandler."""
from unittest.mock import Mock, MagicMock
import numpy as np
from PyQt6 import QtCore, QtWidgets


def test_angle_measure_handler_activation():
    """Test AngleMeasureToolHandler activation and deactivation."""
    from optiverse.ui.views.tool_handlers import AngleMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    undo_stack = Mock()
    parent_widget = Mock()
    on_complete = Mock()

    handler = AngleMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        parent_widget=parent_widget,
        on_complete=on_complete
    )

    # Initially not active
    assert not handler.is_active()

    # Activate
    handler.activate()
    assert handler.is_active()
    assert handler._state == 'waiting_point1'

    # Deactivate
    handler.deactivate()
    assert not handler.is_active()


def test_angle_measure_handler_escape():
    """Test AngleMeasureToolHandler escape handling."""
    from optiverse.ui.views.tool_handlers import AngleMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    undo_stack = Mock()
    parent_widget = Mock()
    on_complete = Mock()

    handler = AngleMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        parent_widget=parent_widget,
        on_complete=on_complete
    )

    # Activate and start measurement
    handler.activate()

    # Escape should work
    result = handler.handle_escape()
    assert result is True
    assert not handler.is_active()
    on_complete.assert_called_once()


def test_angle_measure_handler_escape_not_active():
    """Test AngleMeasureToolHandler escape when not active."""
    from optiverse.ui.views.tool_handlers import AngleMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    undo_stack = Mock()
    parent_widget = Mock()
    on_complete = Mock()

    handler = AngleMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        parent_widget=parent_widget,
        on_complete=on_complete
    )

    # Escape should return False when not active
    result = handler.handle_escape()
    assert result is False
    on_complete.assert_not_called()


def test_angle_measure_handler_click_workflow():
    """Test the three-click workflow for angle measurement."""
    from optiverse.ui.views.tool_handlers import AngleMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    undo_stack = Mock()
    parent_widget = Mock()
    on_complete = Mock()

    handler = AngleMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        parent_widget=parent_widget,
        on_complete=on_complete
    )

    handler.activate()

    # First click: set point1
    handler.handle_click(QtCore.QPointF(0, 0))
    assert handler._state == 'waiting_vertex'
    assert handler._point1 is not None

    # Second click: set vertex
    handler.handle_click(QtCore.QPointF(50, 50))
    assert handler._state == 'waiting_point2'
    assert handler._vertex is not None

    # Third click: set point2 and create measurement
    handler.handle_click(QtCore.QPointF(100, 0))

    # Should have reset state
    assert handler._state is None

    # Should have pushed command to undo stack
    undo_stack.push.assert_called()

    # Should have called completion callback
    on_complete.assert_called_once()


def test_path_measure_handler_activation():
    """Test PathMeasureToolHandler activation and deactivation."""
    from optiverse.ui.views.tool_handlers import PathMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    view.transform.return_value.m11.return_value = 1.0
    undo_stack = Mock()
    get_ray_data = Mock(return_value=[])
    parent_widget = Mock()
    on_complete = Mock()

    handler = PathMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        get_ray_data=get_ray_data,
        parent_widget=parent_widget,
        on_complete=on_complete
    )

    # Initially not active
    assert not handler.is_active()

    # Activate
    handler.activate()
    assert handler.is_active()
    assert handler._state == 'waiting_first_click'

    # Deactivate
    handler.deactivate()
    assert not handler.is_active()


def test_path_measure_handler_escape():
    """Test PathMeasureToolHandler escape handling."""
    from optiverse.ui.views.tool_handlers import PathMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    undo_stack = Mock()
    get_ray_data = Mock(return_value=[])
    parent_widget = Mock()
    on_complete = Mock()

    handler = PathMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        get_ray_data=get_ray_data,
        parent_widget=parent_widget,
        on_complete=on_complete
    )

    # Activate
    handler.activate()

    # Escape should work
    result = handler.handle_escape()
    assert result is True
    assert not handler.is_active()
    on_complete.assert_called_once()


def test_path_measure_handler_escape_not_active():
    """Test PathMeasureToolHandler escape when not active."""
    from optiverse.ui.views.tool_handlers import PathMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    undo_stack = Mock()
    get_ray_data = Mock(return_value=[])
    parent_widget = Mock()
    on_complete = Mock()

    handler = PathMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        get_ray_data=get_ray_data,
        parent_widget=parent_widget,
        on_complete=on_complete
    )

    # Escape should return False when not active
    result = handler.handle_escape()
    assert result is False
    on_complete.assert_not_called()


def test_angle_measure_handler_cleanup_on_deactivate():
    """Test that temporary items are cleaned up on deactivation."""
    from optiverse.ui.views.tool_handlers import AngleMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    undo_stack = Mock()
    parent_widget = Mock()

    handler = AngleMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        parent_widget=parent_widget
    )

    handler.activate()

    # First click creates preview line
    handler.handle_click(QtCore.QPointF(0, 0))
    assert handler._preview_line is not None

    # Deactivate should clean up
    handler.deactivate()
    assert handler._preview_line is None


def test_path_measure_handler_handle_item_delete():
    """Test the _handle_item_delete method."""
    from optiverse.ui.views.tool_handlers import PathMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    undo_stack = Mock()
    get_ray_data = Mock(return_value=[])
    parent_widget = Mock()

    handler = PathMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        get_ray_data=get_ray_data,
        parent_widget=parent_widget
    )

    # Create mock item with scene
    mock_item = Mock()
    mock_item.scene.return_value = scene

    # Call delete handler
    handler._handle_item_delete(mock_item)

    # Should have pushed a RemoveItemCommand
    undo_stack.push.assert_called_once()


def test_angle_measure_handler_handle_item_delete():
    """Test the _handle_item_delete method."""
    from optiverse.ui.views.tool_handlers import AngleMeasureToolHandler

    scene = QtWidgets.QGraphicsScene()
    view = Mock()
    undo_stack = Mock()
    parent_widget = Mock()

    handler = AngleMeasureToolHandler(
        scene=scene,
        view=view,
        undo_stack=undo_stack,
        parent_widget=parent_widget
    )

    # Create mock item with scene
    mock_item = Mock()
    mock_item.scene.return_value = scene

    # Call delete handler
    handler._handle_item_delete(mock_item)

    # Should have pushed a RemoveItemCommand
    undo_stack.push.assert_called_once()



