# Middle Mouse Button Panning - Bug Analysis & Resolution

## Problem Report

User reports two critical issues with middle mouse button panning:
1. **Panning only works when zoomed in enough**
2. **Scale bar artifacts appear during panning** (multiple scale bars visible at different positions)

## Root Cause Analysis

### Issue 1: ViewportUpdateMode - BoundingRectViewportUpdate

**Location**: `graphics_view.py` line 14

```python
self.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
```

**Problem**:
- `BoundingRectViewportUpdate` is an optimization that only updates the bounding rectangle of items that changed in the scene
- The scale bar is drawn in `drawForeground()` which is NOT part of the scene items
- During panning, Qt doesn't realize the foreground needs repainting
- Old scale bars remain visible as "ghosts" because they're never erased

**Why It Causes Artifacts**:
1. User presses middle button and drags
2. View scrolls, exposing a new region
3. Qt updates only the scene item bounding rectangles (the optical components)
4. The old scale bar stays rendered in its previous position
5. A new scale bar is drawn in the new position
6. Result: Multiple scale bars visible simultaneously

**Evidence**: Screenshot shows ~9 scale bars at different positions, all showing "68.6 mm"

### Issue 2: Transformation Anchor During Panning

**Location**: `graphics_view.py` line 15

```python
self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
```

**Problem**:
- `AnchorUnderMouse` is great for zooming (keeps zoom centered on mouse)
- But during panning in `ScrollHandDrag` mode, this can cause unexpected behavior
- The view tries to keep the item under the mouse anchored while the scrollbars change
- This can make panning feel "sticky" or unresponsive, especially at low zoom levels

**Why Panning Works Better When Zoomed In**:
- At higher zoom levels, there's more "room" in the scrollable area
- The anchor behavior has less impact because the transform matrix is larger
- At low zoom (zoomed out), the scene might fit entirely in the viewport
- With no scrollable area, panning has nowhere to go!

### Issue 3: Fake Mouse Event Approach

**Location**: `graphics_view.py` lines 380-412

**Current Implementation**:
- Creates fake left button events to trick Qt's `ScrollHandDrag` mode
- While clever, this approach has limitations:
  - Event coordinates might not map perfectly
  - Can confuse other event handlers
  - Doesn't directly control the pan operation

**Better Approach**:
- Directly manipulate scrollbars in `mouseMoveEvent`
- Track middle button state explicitly
- More control over pan behavior
- Cleaner event handling

## Detailed Problem Breakdown

### ViewportUpdateMode Options in Qt

1. **FullViewportUpdate** (recommended for foreground/background drawing)
   - Repaints the entire viewport on any change
   - Slower but guarantees correct rendering
   - Necessary when using `drawForeground()` or `drawBackground()`

2. **MinimalViewportUpdate**
   - Minimal repainting (most optimal)
   - Works if you don't draw outside scene items

3. **SmartViewportUpdate** (default)
   - Analyzes what changed and updates smartly
   - Good balance for most cases

4. **BoundingRectViewportUpdate** (current, problematic)
   - Only updates bounding rects of changed items
   - Fastest but doesn't handle foreground/background
   - **Causes our scale bar artifacts**

5. **NoViewportUpdate**
   - No automatic updates (manual control)

### Why Current Implementation Fails

```
User Action              Qt Behavior                      Result
────────────────────────────────────────────────────────────────────
Middle button drag   →   ScrollHandDrag mode active   →   OK
View scrolls         →   Scene items update           →   OK
                     →   BoundingRect optimization    →   PROBLEM!
                     →   Foreground NOT repainted     →   PROBLEM!
Old scale bar        →   Never erased                 →   ARTIFACT!
New scale bar drawn  →   At new position              →   ARTIFACT!
Result: Multiple scale bars visible on screen
```

### Transformation Anchor Impact

```
Zoom Level    Scrollable Area    Anchor Impact       Pan Feel
──────────────────────────────────────────────────────────────
Zoomed Out    Minimal/None       High                Broken
Normal        Some               Medium              Sluggish
Zoomed In     Large              Low                 Good
```

## Solution Design

### Fix 1: Change ViewportUpdateMode

**Change**: `BoundingRectViewportUpdate` → `FullViewportUpdate`

**Rationale**:
- We use `drawForeground()` for scale bar rendering
- We need full viewport repaints during panning
- Performance impact is minimal (only during pan/zoom)
- Guarantees correct rendering

**Trade-off**:
- Slightly slower (repaints entire viewport)
- But necessary for foreground/background rendering
- Modern hardware handles this easily

### Fix 2: Adjust Transformation Anchor During Panning

**Strategy**: Temporarily change anchor when panning

**Implementation**:
```python
def mousePressEvent(self, e):
    if e.button() == MiddleButton:
        # Save current anchor
        self._saved_anchor = self.transformationAnchor()
        # Use NoAnchor or AnchorViewCenter for panning
        self.setTransformationAnchor(ViewportAnchor.NoAnchor)
        # ... start pan

def mouseReleaseEvent(self, e):
    if e.button() == MiddleButton:
        # Restore anchor for zooming
        self.setTransformationAnchor(self._saved_anchor)
        # ... end pan
```

**Rationale**:
- `AnchorUnderMouse` perfect for zoom
- `NoAnchor` better for panning (more direct control)
- Switch between them based on current operation

### Fix 3: Better Pan Implementation (Optional Enhancement)

**Current**: Fake mouse events
**Improved**: Direct scrollbar manipulation

**Implementation**:
```python
def __init__(self):
    # ... existing code ...
    self._panning = False
    self._pan_start_pos = None

def mousePressEvent(self, e):
    if e.button() == MiddleButton:
        self._panning = True
        self._pan_start_pos = e.pos()
        self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        e.accept()
    else:
        super().mousePressEvent(e)

def mouseMoveEvent(self, e):
    if self._panning:
        delta = e.pos() - self._pan_start_pos
        self._pan_start_pos = e.pos()
        
        # Directly adjust scrollbars
        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value() - delta.x()
        )
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() - delta.y()
        )
        e.accept()
    else:
        super().mouseMoveEvent(e)

def mouseReleaseEvent(self, e):
    if e.button() == MiddleButton and self._panning:
        self._panning = False
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        e.accept()
    else:
        super().mouseReleaseEvent(e)
```

**Advantages**:
- Direct control over panning
- No fake events needed
- Works at all zoom levels
- More predictable behavior
- Cleaner code

## Implementation Priority

### Critical Fixes (Must Do)
1. ✅ Change `ViewportUpdateMode` to `FullViewportUpdate`
2. ✅ Add transformation anchor switching during pan

### Enhancement (Nice to Have)
3. ⚠️ Replace fake events with direct scrollbar manipulation

## Testing Strategy

### Test Cases to Verify Fixes

1. **Scale Bar Artifacts** (Critical)
   - Pan at various zoom levels
   - Verify only ONE scale bar visible
   - Check scale bar position stays bottom-left

2. **Pan at Low Zoom** (Critical)
   - Zoom out until scene fits viewport
   - Try middle button pan
   - Verify panning works or gracefully disabled

3. **Pan at Medium Zoom**
   - Set moderate zoom level
   - Pan in all directions
   - Verify smooth, responsive panning

4. **Pan at High Zoom**
   - Zoom in significantly
   - Pan around scene
   - Verify no performance issues

5. **Pan + Zoom Interaction**
   - Pan while panning (shouldn't happen but test)
   - Zoom during pan (release middle button, use wheel)
   - Verify anchor switches correctly

6. **Space Bar Pan Still Works**
   - Verify space bar panning unaffected
   - Test interaction between space and middle button

### Performance Testing
- Pan for 30 seconds continuously
- Check CPU usage
- Monitor frame rate
- Verify no memory leaks

## Expected Outcomes

### After Fix 1 (ViewportUpdateMode)
- ✅ No more scale bar artifacts
- ✅ Clean rendering during pan
- ⚠️ Slight performance decrease (acceptable)

### After Fix 2 (Transformation Anchor)
- ✅ Pan works at all zoom levels
- ✅ More responsive panning
- ✅ Zoom still smooth and centered

### After Fix 3 (Direct Pan - Optional)
- ✅ Even better pan control
- ✅ No fake event issues
- ✅ Cleaner, more maintainable code

## Conclusion

The bugs are caused by:
1. **Wrong viewport update mode** for foreground rendering → Scale bar artifacts
2. **Wrong transformation anchor** during panning → Poor responsiveness at low zoom

The fixes are:
1. Change to `FullViewportUpdate`
2. Switch anchor to `NoAnchor` during pan
3. (Optional) Replace fake events with direct scrollbar control

These changes will provide smooth, artifact-free panning at all zoom levels.

