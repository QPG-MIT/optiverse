# Drag-and-Drop Zoom Bug Fix

## Problem
After dragging an element from the toolbar to the canvas, trackpad zoom functionality would become buggy. The cursor symbol would change and zoom in/out would not work correctly, particularly affecting zoom-to-cursor behavior on Mac trackpads.

## Root Cause
After completing a drag-and-drop operation, Qt's internal mouse position tracking was not being updated properly. This caused several issues:

1. **Zoom-to-cursor broken**: The zoom would not center correctly on the cursor position
2. **Trackpad gestures unreliable**: Two-finger pinch and Command+scroll zoom would behave erratically
3. **Cursor state lingering**: The drag cursor appearance would persist even after the drag completed

The issue occurred because Qt's drag-and-drop event handling can leave the view's internal mouse tracking state out of sync with the actual cursor position. When zoom operations rely on knowing the cursor position (as they do with `AnchorUnderMouse` transformation anchor), this stale position data causes incorrect zoom behavior.

## Solution
Added synthetic mouse move events after all drag-and-drop operations to force Qt to update its internal mouse position tracking. This is the same fix that was already being used for placement mode cancellation.

### Files Modified
`src/optiverse/objects/views/graphics_view.py`

### Changes Made

1. **In `dragLeaveEvent` (lines 721-741)**:
   - Added synthetic mouse move event after restoring transformation anchor
   - Ensures tracking is correct even if drag is cancelled

2. **In `dropEvent` - Component Drop (lines 771-795)**:
   - Added synthetic mouse move event after dropping component from library
   - Ensures zoom works correctly immediately after placing a component

3. **In `dropEvent` - Image Drop (lines 818-830)**:
   - Added synthetic mouse move event after dropping image
   - Handles direct image drops from files or clipboard

4. **In `dropEvent` - URL Drop (lines 848-860)**:
   - Added synthetic mouse move event after dropping image from URL
   - Handles drag-and-drop of image files from Finder/Explorer

5. **In `dropEvent` - Rejected Drop (lines 867-878)**:
   - Added synthetic mouse move event even if drop is rejected
   - Ensures tracking is restored regardless of drop outcome

### Code Pattern
```python
# Force Qt to update its internal mouse position tracking
# This ensures zoom-to-cursor works correctly after drag-and-drop operations
# Without this, Qt's internal mouse tracking can get stuck, causing buggy zoom behavior
cursor_pos = self.mapFromGlobal(QtGui.QCursor.pos())
move_event = QtGui.QMouseEvent(
    QtCore.QEvent.Type.MouseMove,
    QtCore.QPointF(cursor_pos),
    QtCore.Qt.MouseButton.NoButton,
    QtCore.Qt.MouseButton.NoButton,
    QtCore.Qt.KeyboardModifier.NoModifier
)
QtWidgets.QApplication.sendEvent(self.viewport(), move_event)
```

## Benefits
✅ Trackpad zoom works smoothly after drag-and-drop operations  
✅ Zoom-to-cursor behavior is correct immediately after dropping components  
✅ No lingering cursor or tracking state issues  
✅ Consistent behavior across all drop paths (components, images, URLs)  
✅ Works correctly even if drag is cancelled or rejected  
✅ Compatible with Mac trackpad gestures (pinch, Command+scroll)  
✅ Also fixes mouse wheel zoom behavior after drag operations  

## Testing
To verify the fix:
1. Open Optiverse
2. Drag a component from the toolbar (e.g., Lens, Mirror)
3. Drop it on the canvas
4. Immediately try to zoom using:
   - Trackpad pinch gesture
   - Command + scroll (two-finger scroll with Command key)
   - Mouse wheel
5. Verify that zoom centers correctly on the cursor position
6. Repeat test by cancelling a drag (drag out and back to toolbar)
7. Verify zoom still works correctly

## Related Issues
This fix is related to the previous `ZOOM_DRAG_BUG_FIX.md` which addressed transformation anchor conflicts during drag operations. That fix prevented zoom from being buggy **during** the drag, while this fix prevents zoom from being buggy **after** the drag completes.

Both fixes work together to provide smooth zoom behavior:
- **During drag**: Transformation anchor temporarily set to `NoAnchor` to prevent conflicts
- **After drag**: Synthetic mouse move event updates Qt's internal tracking

## Technical Details
Qt's `QGraphicsView` maintains internal state about mouse position for various operations including zoom-to-cursor. During drag-and-drop operations, Qt's event handling can leave this state out of sync. The synthetic mouse move event forces Qt to recalculate and update its internal mouse position tracking, ensuring subsequent zoom operations have correct position data.

This is a well-known Qt behavior that affects various applications, and the synthetic mouse move workaround is a standard solution used in many Qt-based applications (including placement mode cleanup in this same codebase).

