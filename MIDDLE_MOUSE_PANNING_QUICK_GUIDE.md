# Middle Mouse Button Panning - Quick Guide

## ✅ Feature Status: ALREADY IMPLEMENTED

The middle mouse button panning feature is fully functional in Optiverse!

## How to Use

### Middle Mouse Button Panning
1. **Press and hold** the middle mouse button (mouse wheel button)
2. **Drag** the mouse to pan the canvas
3. **Release** the middle button to return to normal selection mode

### Alternative: Space Bar Panning
1. **Press and hold** the space bar
2. **Click and drag** with the left mouse button to pan
3. **Release** the space bar to return to normal selection mode

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MIDDLE BUTTON PANNING                     │
└─────────────────────────────────────────────────────────────┘

Initial State:
┌───────────────────┐
│  RubberBandDrag   │ ← Default mode (selection with left button)
│  Mode Active      │
└───────────────────┘
         │
         │ User presses middle button
         ↓
┌───────────────────┐
│ Detect Middle Btn │
│  mousePressEvent  │
└───────────────────┘
         │
         │ Switch drag mode
         ↓
┌───────────────────┐
│ ScrollHandDrag    │ ← Pan mode activated
│   Mode Active     │
└───────────────────┘
         │
         │ Create fake left button event
         ↓
┌───────────────────┐
│  Qt Handles Pan   │ ← Built-in Qt panning logic
│  User drags view  │
└───────────────────┘
         │
         │ User releases middle button
         ↓
┌───────────────────┐
│ Detect Middle Btn │
│ mouseReleaseEvent │
└───────────────────┘
         │
         │ Create fake left button release
         │ Switch drag mode back
         ↓
┌───────────────────┐
│  RubberBandDrag   │ ← Back to selection mode
│  Mode Restored    │
└───────────────────┘
```

## Implementation Summary

### Files
- **Implementation**: `src/optiverse/objects/views/graphics_view.py` (lines 380-412)
- **Tests**: `tests/objects/test_pan_controls.py` (311 lines, comprehensive coverage)

### Code Snippets

**Middle Button Press Handler**:
```python
def mousePressEvent(self, e: QtGui.QMouseEvent):
    if e.button() == QtCore.Qt.MouseButton.MiddleButton:
        self.setDragMode(self.DragMode.ScrollHandDrag)
        # Create fake left button event to activate Qt's pan handling
        fake = QtGui.QMouseEvent(...)
        super().mousePressEvent(fake)
    else:
        super().mousePressEvent(e)
```

**Middle Button Release Handler**:
```python
def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
    if e.button() == QtCore.Qt.MouseButton.MiddleButton:
        # Create fake left button release
        fake = QtGui.QMouseEvent(...)
        super().mouseReleaseEvent(fake)
        self.setDragMode(self.DragMode.RubberBandDrag)
    else:
        super().mouseReleaseEvent(e)
```

## Test Coverage

✅ **27 test cases** covering:
- State management
- Drag mode switching
- Middle button press/release behavior
- Left button isolation (no conflicts)
- Space bar + middle button interaction
- Rapid clicking edge cases
- Integration tests

## Key Design Decisions

### 1. Fake Event Strategy
**Problem**: Qt's `ScrollHandDrag` mode works with left button only.

**Solution**: When middle button is pressed, create a fake left button event to activate Qt's built-in pan logic.

**Benefits**:
- Leverages Qt's tested panning code
- No custom pan implementation needed
- Clean and maintainable

### 2. Mode Switching
**Problem**: Need to switch between selection and pan modes.

**Solution**: Use Qt's drag mode system:
- `RubberBandDrag` for selection (default)
- `ScrollHandDrag` for panning (temporary)

**Benefits**:
- Qt handles the mode logic
- No conflicts between modes
- Automatic cursor changes

### 3. State Independence
**Problem**: Space bar and middle button should work independently.

**Solution**: 
- Space bar uses `_hand` flag
- Middle button uses drag mode directly
- Each can activate pan mode without interfering

**Benefits**:
- Two ways to pan
- No modal conflicts
- Flexible UX

## User Experience

### Current Behavior
| Action | Result |
|--------|--------|
| Middle button press | Switches to pan mode |
| Drag while holding middle button | Canvas pans smoothly |
| Release middle button | Returns to selection mode |
| Left button click | Normal selection (unaffected) |
| Space + left drag | Alternative pan method |
| Mouse wheel scroll | Zoom in/out (unaffected) |

### Pan Mode Indicators
- **Cursor**: Qt automatically changes cursor to open/closed hand
- **Drag mode**: Internally switches between modes
- **Visual feedback**: Smooth canvas movement

## Verification Steps

To verify the feature works:

1. **Launch the application**:
   ```powershell
   python -m optiverse.app.main
   ```

2. **Test middle button panning**:
   - Press and hold middle mouse button
   - Observe cursor change to hand icon
   - Drag to pan the canvas
   - Release middle button
   - Verify selection still works with left button

3. **Test space bar panning**:
   - Press and hold space bar
   - Click and drag with left button
   - Observe canvas panning
   - Release space bar
   - Verify selection works normally

## Technical Notes

### Qt Drag Modes
- `QGraphicsView.DragMode.RubberBandDrag`: Draw selection rectangle
- `QGraphicsView.DragMode.ScrollHandDrag`: Pan/scroll the view
- Mode switching is instantaneous and efficient

### Event Handling
- Mouse events are processed in `mousePressEvent` and `mouseReleaseEvent`
- Key events are processed in `keyPressEvent` and `keyReleaseEvent`
- All handlers call `super()` to maintain Qt's default behaviors

### Viewport Anchoring
The view uses `AnchorUnderMouse` for both transformation and resize anchoring, ensuring intuitive zoom and pan behavior.

## Troubleshooting

### Issue: Middle button doesn't pan
**Cause**: OS or mouse driver might be capturing middle button.

**Solution**: Check mouse settings in OS, disable special middle button actions.

### Issue: Cursor doesn't change
**Cause**: Qt theme or cursor not loading.

**Solution**: This is cosmetic; panning still works.

### Issue: Pan mode "sticks"
**Cause**: Rare - middle button release not detected.

**Solution**: Click middle button again or press/release space bar.

## Conclusion

The middle mouse button panning feature is:
- ✅ Fully implemented
- ✅ Comprehensively tested (27 test cases)
- ✅ Following Qt best practices
- ✅ Ready to use

**No additional work is needed** - the feature is complete and functional!

