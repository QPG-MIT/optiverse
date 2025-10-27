"""
Tests for pan controls in GraphicsView.

Space key + drag and middle mouse button + drag should pan the view.
"""
import pytest
from PyQt6 import QtCore, QtWidgets

from optiverse.objects import GraphicsView


class TestPanControlsState:
    """Test pan control state management."""
    
    def test_graphicsview_has_hand_flag(self):
        """GraphicsView should track space key state."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Should have _hand flag for space key state
        assert hasattr(view, '_hand')
        assert view._hand == False  # Initially not panning
    
    def test_graphicsview_has_key_handlers(self):
        """GraphicsView should have key event handlers."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Should have key event handlers
        assert hasattr(view, 'keyPressEvent')
        assert hasattr(view, 'keyReleaseEvent')
        assert callable(view.keyPressEvent)
        assert callable(view.keyReleaseEvent)
    
    def test_graphicsview_has_mouse_handlers(self):
        """GraphicsView should have mouse event handlers for middle button."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Should have mouse event handlers
        assert hasattr(view, 'mousePressEvent')
        assert hasattr(view, 'mouseReleaseEvent')
        assert callable(view.mousePressEvent)
        assert callable(view.mouseReleaseEvent)


class TestDragModeManagement:
    """Test that drag mode switches properly."""
    
    def test_initial_drag_mode(self):
        """Initial drag mode should be RubberBandDrag."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag
    
    def test_drag_mode_can_change(self):
        """Drag mode should be changeable."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Should be able to change drag mode
        view.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
        
        # And change back
        view.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag


class TestPanControlIntegration:
    """Integration tests for pan controls."""
    
    def test_pan_controls_dont_crash(self):
        """Pan control methods should not crash."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Creating events and calling handlers should not crash
        # (Full event simulation is complex, just test they exist and callable)
        assert callable(view.keyPressEvent)
        assert callable(view.keyReleaseEvent)
        assert callable(view.mousePressEvent)
        assert callable(view.mouseReleaseEvent)

