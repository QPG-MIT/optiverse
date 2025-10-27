# Middle Mouse Button Panning - Implementation Strategy

## Executive Summary

Middle mouse button panning is **ALREADY IMPLEMENTED** in the Optiverse application. This document explains the implementation strategy, test-driven development approach, and how the feature works.

## Feature Requirements

### User Story
As a user, when I press and hold the middle mouse button (mouse wheel button), I want to drag the canvas around to pan the view, similar to common CAD and graphics applications.

### Acceptance Criteria
1. ✅ Middle mouse button press activates pan mode
2. ✅ While holding middle button, dragging moves the canvas
3. ✅ Releasing middle button deactivates pan mode and returns to selection mode
4. ✅ Left mouse button functionality is not affected
5. ✅ Space bar panning continues to work independently

## Implementation Strategy

### Architecture Overview

The implementation is in `src/optiverse/objects/views/graphics_view.py` and follows Qt's standard drag mode pattern.

### Key Components

1. **GraphicsView Class** (`graphics_view.py`)
   - Inherits from `QGraphicsView`
   - Has two drag modes:
     - `RubberBandDrag`: Default mode for selection
     - `ScrollHandDrag`: Pan mode for dragging the view

2. **State Management**
   - `_hand` flag: Tracks space key state (for space bar panning)
   - Drag mode: Qt's built-in drag mode system

### Implementation Details

#### Mouse Event Handling

**Middle Button Press** (lines 380-396):
```python
def mousePressEvent(self, e: QtGui.QMouseEvent):
    """Handle middle button press for pan mode."""
    if e.button() == QtCore.Qt.MouseButton.MiddleButton:
        # Middle button → drag to pan
        self.setDragMode(self.DragMode.ScrollHandDrag)
        # Create fake left button event for pan mode
        fake = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonPress,
            e.position(),
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.MouseButton.LeftButton,
            e.modifiers()
        )
        super().mousePressEvent(fake)
    else:
        super().mousePressEvent(e)
```

**Middle Button Release** (lines 397-412):
```python
def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
    """Handle middle button release to exit pan mode."""
    if e.button() == QtCore.Qt.MouseButton.MiddleButton:
        # Create fake left button release
        fake = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonRelease,
            e.position(),
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.MouseButton.NoButton,
            e.modifiers()
        )
        super().mouseReleaseEvent(fake)
        # Back to select mode
        self.setDragMode(self.DragMode.RubberBandDrag)
    else:
        super().mouseReleaseEvent(e)
```

### How It Works

1. **User presses middle button**
   - `mousePressEvent` detects `MiddleButton`
   - Switches drag mode to `ScrollHandDrag`
   - Creates a fake `LeftButton` press event
   - Qt's `ScrollHandDrag` mode activates, capturing mouse movement

2. **User drags while holding middle button**
   - Qt's built-in `ScrollHandDrag` handles the panning
   - The view scrolls/pans following the mouse

3. **User releases middle button**
   - `mouseReleaseEvent` detects `MiddleButton` release
   - Creates a fake `LeftButton` release event
   - Switches drag mode back to `RubberBandDrag`
   - Normal selection mode resumes

### Why Fake Events?

Qt's `ScrollHandDrag` mode is designed to work with the left mouse button. By creating "fake" left button events when the middle button is pressed/released, we trick Qt into activating pan mode for the middle button while keeping left button selection intact.

## Test-Driven Development Approach

### Test Structure

The tests are in `tests/objects/test_pan_controls.py` with 311 lines of comprehensive coverage.

### Test Classes

1. **TestPanControlsState** (lines 12-45)
   - Tests state management attributes exist
   - Verifies handlers are present and callable

2. **TestDragModeManagement** (lines 47-69)
   - Tests initial drag mode is `RubberBandDrag`
   - Verifies drag mode can be changed

3. **TestMiddleButtonPanning** (lines 71-158)
   - ✅ Middle button press enables `ScrollHandDrag` mode
   - ✅ Middle button release restores `RubberBandDrag` mode
   - ✅ Left button is not affected by middle button logic

4. **TestSpaceKeyPanning** (lines 160-211)
   - Tests space bar panning independently
   - Verifies space key enables/disables hand mode

5. **TestPanControlInteraction** (lines 213-294)
   - Tests space and middle button don't conflict
   - Tests rapid middle button clicks maintain correct state

6. **TestPanControlIntegration** (lines 296-311)
   - Integration tests to ensure no crashes

### Key Test Examples

**Test: Middle Button Enables Panning**
```python
def test_middle_button_press_enables_scroll_hand_drag(self):
    """Middle button press should switch to ScrollHandDrag mode."""
    scene = QtWidgets.QGraphicsScene()
    view = GraphicsView(scene)
    
    # Initial state should be RubberBandDrag
    assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag
    
    # Simulate middle button press
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
```

**Test: Middle Button Release Restores Selection**
```python
def test_middle_button_release_restores_rubber_band_drag(self):
    """Middle button release should restore RubberBandDrag mode."""
    scene = QtWidgets.QGraphicsScene()
    view = GraphicsView(scene)
    
    # Press and release middle button
    press_event = QtGui.QMouseEvent(...)
    view.mousePressEvent(press_event)
    assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.ScrollHandDrag
    
    release_event = QtGui.QMouseEvent(...)
    view.mouseReleaseEvent(release_event)
    
    # Should restore to RubberBandDrag
    assert view.dragMode() == QtWidgets.QGraphicsView.DragMode.RubberBandDrag
```

### Test Coverage

✅ **State Management**: Verified `_hand` flag exists and initializes correctly
✅ **Mode Switching**: Tests drag mode changes between RubberBand and ScrollHand
✅ **Middle Button Logic**: Comprehensive tests for press/release behavior
✅ **Left Button Isolation**: Ensures left button is unaffected
✅ **Interaction Testing**: Tests space and middle button don't conflict
✅ **Rapid Input**: Tests rapid clicking maintains correct state
✅ **Integration**: Smoke tests to prevent crashes

## Additional Features

The same file implements **Space Bar Panning** (lines 350-378):
- Press space bar to activate pan mode
- Drag with left button to pan
- Release space bar to return to selection mode

This provides two ways to pan:
1. Hold space + drag with left button
2. Hold middle button + drag

## Qt Framework Integration

### ViewportAnchor Settings (lines 15-16)
```python
self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
```

These settings ensure that zooming and resizing keep the content under the mouse cursor anchored, providing intuitive zoom behavior.

### DragMode Options

Qt provides several drag modes:
- `NoDrag`: No dragging
- `ScrollHandDrag`: Pan/scroll the view (used for middle button panning)
- `RubberBandDrag`: Draw selection rectangle (used for normal selection)

## Benefits of This Approach

1. **Simple**: Uses Qt's built-in drag handling
2. **Reliable**: Leverages well-tested Qt framework code
3. **Clean**: Minimal custom code, easy to maintain
4. **Tested**: Comprehensive test coverage ensures correctness
5. **Non-invasive**: Doesn't affect other mouse button behaviors

## Future Enhancements

Potential improvements (not currently needed):
1. Custom cursor during pan mode (Qt handles this automatically)
2. Configurable pan sensitivity (Qt's default is good)
3. Momentum scrolling (would require custom implementation)
4. Touch gesture support for tablets

## Conclusion

The middle mouse button panning feature is fully implemented and tested. The implementation follows Qt best practices, uses test-driven development, and provides a smooth user experience. The feature works seamlessly alongside other input methods (space bar panning, wheel zoom, selection) without conflicts.
