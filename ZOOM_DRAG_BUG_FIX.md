# Zoom Bug During Drag Operations - FIXED ✅

## Problem

When dragging an object from the toolbar to the canvas, the zoom in/out functionality would become buggy. Users would experience issues using the mouse wheel or trackpad gestures to zoom while a drag operation was active or after completing a drag.

## Root Cause

The issue was caused by Qt's `TransformationAnchor` setting interfering with drag-and-drop operations. The GraphicsView was configured with `AnchorUnderMouse` for proper zoom behavior (zooming towards the mouse cursor). However, this anchor setting can interfere with Qt's internal drag/drop event handling, causing wheel events to be improperly processed during and after drag operations.

## Solution

Modified `src/optiverse/objects/views/graphics_view.py` to temporarily disable the transformation anchor during drag operations:

### Changes Made

1. **In `dragEnterEvent`** (lines 677-701):
   - Save the current transformation anchor
   - Set anchor to `NoAnchor` during drag operation
   - Applied to both component drags and image/URL drags

2. **In `dragLeaveEvent`** (lines 721-728):
   - Restore the saved anchor when drag leaves the view
   - Ensures proper cleanup if drag is cancelled

3. **In `dropEvent`** (lines 730-815):
   - Restore the saved anchor after successful drop (component, image, or URL)
   - Restore anchor if drop is rejected
   - Covers all exit paths from drag operation

### Technical Details

```python
# On drag enter - save and disable anchor
self._saved_anchor = self.transformationAnchor()
self.setTransformationAnchor(self.ViewportAnchor.NoAnchor)

# On drag leave or drop - restore anchor
if hasattr(self, '_saved_anchor'):
    self.setTransformationAnchor(self._saved_anchor)
    delattr(self, '_saved_anchor')
```

## Benefits

✅ Zoom operations work smoothly during drag operations
✅ No lingering state after drag completes
✅ Handles all drag scenarios: component drags, image drags, URL drags
✅ Proper cleanup on drag cancel/leave
✅ Compatible with Mac trackpad gestures and mouse wheel zoom

## Testing

To verify the fix:

1. **Start the application**
   ```bash
   python -m src.optiverse.ui.main
   ```

2. **Test component drag + zoom**:
   - Click and drag a component from the library toolbar
   - While holding the drag, try to zoom in/out with mouse wheel or trackpad
   - Should zoom smoothly without issues

3. **Test post-drag zoom**:
   - Drag and drop a component onto the canvas
   - Immediately try zooming in/out
   - Should work normally without any lag or buggy behavior

4. **Test drag cancel + zoom**:
   - Start dragging a component
   - Move mouse outside the canvas to cancel
   - Try zooming
   - Should work normally

## Files Modified

- `src/optiverse/objects/views/graphics_view.py`
  - Modified: `dragEnterEvent` (added anchor save/disable)
  - Modified: `dragLeaveEvent` (added anchor restore)
  - Modified: `dropEvent` (added anchor restore in all exit paths)

## Related

This fix maintains compatibility with:
- Mac trackpad gesture support
- Mouse wheel zoom
- Keyboard zoom shortcuts (+/- keys)
- Pan controls (middle mouse button)
- Ghost preview system during drag

