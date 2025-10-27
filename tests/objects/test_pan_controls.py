"""
Tests for pan controls in GraphicsView.

Space key + drag and middle mouse button + drag should pan the view.
"""
import pytest
from PyQt6 import QtCore, QtGui, QtWidgets

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


class TestMiddleButtonPanning:
    """Test middle mouse button panning behavior."""
    
    def test_middle_button_press_enables_scroll_hand_drag(self):
        """Middle button press should switch to ScrollHandDrag mode."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Initial state should be RubberBandDrag
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag
        
        # Simulate middle button press
        event = QtCore.QEvent(QtCore.QEvent.Type.MouseButtonPress)
        mouse_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonPress,
            QtCore.QPointF(100, 100),
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        
        view.mousePressEvent(mouse_event)
        
        # Drag mode should now be ScrollHandDrag
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
    
    def test_middle_button_release_restores_rubber_band_drag(self):
        """Middle button release should restore RubberBandDrag mode."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Simulate middle button press then release
        press_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonPress,
            QtCore.QPointF(100, 100),
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mousePressEvent(press_event)
        
        # Should be in ScrollHandDrag
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
        
        # Release middle button
        release_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonRelease,
            QtCore.QPointF(150, 150),
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mouseReleaseEvent(release_event)
        
        # Should restore to RubberBandDrag
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag
    
    def test_left_button_not_affected_by_middle_button_logic(self):
        """Left button clicks should work normally, unaffected by middle button logic."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Simulate left button press
        left_press = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonPress,
            QtCore.QPointF(100, 100),
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mousePressEvent(left_press)
        
        # Should still be RubberBandDrag (for selection)
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag
        
        # Release left button
        left_release = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonRelease,
            QtCore.QPointF(150, 150),
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mouseReleaseEvent(left_release)
        
        # Should still be RubberBandDrag
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag


class TestSpaceKeyPanning:
    """Test space key panning behavior."""
    
    def test_space_key_press_enables_scroll_hand_drag(self):
        """Space key press should switch to ScrollHandDrag mode."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Initial state
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag
        assert view._hand == False
        
        # Simulate space key press
        key_event = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyPress,
            QtCore.Qt.Key.Key_Space,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.keyPressEvent(key_event)
        
        # Should enable hand mode
        assert view._hand == True
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
    
    def test_space_key_release_restores_rubber_band_drag(self):
        """Space key release should restore RubberBandDrag mode."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Press space
        key_press = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyPress,
            QtCore.Qt.Key.Key_Space,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.keyPressEvent(key_press)
        
        assert view._hand == True
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
        
        # Release space
        key_release = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyRelease,
            QtCore.Qt.Key.Key_Space,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.keyReleaseEvent(key_release)
        
        # Should restore to normal mode
        assert view._hand == False
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag


class TestPanControlInteraction:
    """Test interaction between different pan control methods."""
    
    def test_space_and_middle_button_dont_conflict(self):
        """Space key and middle button should not conflict with each other."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Press space first
        key_press = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyPress,
            QtCore.Qt.Key.Key_Space,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.keyPressEvent(key_press)
        assert view._hand == True
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
        
        # Release space - should go back to RubberBandDrag
        key_release = QtGui.QKeyEvent(
            QtCore.QEvent.Type.KeyRelease,
            QtCore.Qt.Key.Key_Space,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.keyReleaseEvent(key_release)
        assert view._hand == False
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag
        
        # Now try middle button
        middle_press = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonPress,
            QtCore.QPointF(100, 100),
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mousePressEvent(middle_press)
        
        # Should enable ScrollHandDrag again
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
        
        # Release middle button
        middle_release = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonRelease,
            QtCore.QPointF(150, 150),
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mouseReleaseEvent(middle_release)
        
        # Should restore to RubberBandDrag
        assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag
    
    def test_multiple_rapid_middle_button_clicks(self):
        """Rapid middle button clicks should maintain correct state."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        for i in range(3):
            # Press
            press = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseButtonPress,
                QtCore.QPointF(100 + i * 10, 100),
                QtCore.Qt.MouseButton.MiddleButton,
                QtCore.Qt.MouseButton.MiddleButton,
                QtCore.Qt.KeyboardModifier.NoModifier
            )
            view.mousePressEvent(press)
            assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
            
            # Release
            release = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseButtonRelease,
                QtCore.QPointF(100 + i * 10, 100),
                QtCore.Qt.MouseButton.MiddleButton,
                QtCore.Qt.MouseButton.NoButton,
                QtCore.Qt.KeyboardModifier.NoModifier
            )
            view.mouseReleaseEvent(release)
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


class TestViewportUpdateMode:
    """Test viewport update mode configuration for proper rendering."""
    
    def test_viewport_update_mode_supports_foreground_drawing(self):
        """Viewport update mode should support drawForeground rendering.
        
        BoundingRectViewportUpdate causes artifacts with scale bar.
        FullViewportUpdate ensures foreground is properly redrawn.
        """
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Should use FullViewportUpdate to avoid scale bar artifacts
        # during panning (scale bar is drawn in drawForeground)
        assert view.viewportUpdateMode() == QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate


class TestTransformationAnchorBehavior:
    """Test transformation anchor behavior during panning."""
    
    def test_initial_transformation_anchor(self):
        """Initial transformation anchor should be AnchorUnderMouse for zooming."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Should start with AnchorUnderMouse for intuitive zooming
        assert view.transformationAnchor() == QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
    
    def test_transformation_anchor_changes_during_middle_button_pan(self):
        """Transformation anchor should change during middle button panning.
        
        AnchorUnderMouse causes issues during panning at low zoom.
        Should temporarily switch to NoAnchor during pan operation.
        """
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        # Initial anchor for zooming
        assert view.transformationAnchor() == QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
        
        # Press middle button
        press_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonPress,
            QtCore.QPointF(100, 100),
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mousePressEvent(press_event)
        
        # Anchor should switch to NoAnchor for better panning
        assert view.transformationAnchor() == QtWidgets.QGraphicsView.ViewportAnchor.NoAnchor
        
        # Release middle button
        release_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonRelease,
            QtCore.QPointF(150, 150),
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mouseReleaseEvent(release_event)
        
        # Anchor should restore to AnchorUnderMouse for zooming
        assert view.transformationAnchor() == QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
    
    def test_transformation_anchor_unchanged_by_left_button(self):
        """Left button should not affect transformation anchor."""
        scene = QtWidgets.QGraphicsScene()
        view = GraphicsView(scene)
        
        initial_anchor = view.transformationAnchor()
        
        # Press and release left button
        press_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonPress,
            QtCore.QPointF(100, 100),
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mousePressEvent(press_event)
        
        # Anchor should not change
        assert view.transformationAnchor() == initial_anchor
        
        release_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonRelease,
            QtCore.QPointF(150, 150),
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        view.mouseReleaseEvent(release_event)
        
        # Anchor should still not change
        assert view.transformationAnchor() == initial_anchor

