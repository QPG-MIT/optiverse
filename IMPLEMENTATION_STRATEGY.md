# Implementation Strategy: RaytracingV2.py → Optiverse Package

## Executive Summary

This document outlines the differences between the monolithic `RaytracingV2.py` and the current modular `optiverse` package, and provides a detailed strategy for implementing the improvements found in V2 back into the package.

**Note:** This analysis excludes PyQt5 vs PyQt6 differences as those are framework-level changes already completed.

---

## Major Differences Found

### 1. **ComponentSprite Selection Feedback** ✨ HIGH PRIORITY

**Location in V2:** Lines 399-406  
**Status in Package:** Missing

**What's Different:**
- V2's `ComponentSprite.paint()` adds a translucent blue overlay when the parent item is selected
- Provides visual feedback that the sprite "belongs" to the selected element
- Uses `QGraphicsColorizeEffect` as an alternative approach (lines 481-487, 624-630)

**Implementation Impact:** Medium  
**User Benefit:** High - Better visual feedback

---

### 2. **BaseObj Sprite Helper Methods** ✨ HIGH PRIORITY

**Location in V2:** Lines 165-187, 235-243  
**Status in Package:** Missing

**What's Different:**
V2 includes helper methods in `BaseObj`:
- `_sprite_rect_in_item()`: Gets sprite rect in item-local coords
- `_shape_union_sprite()`: Unions sprite bounds into shape for hit testing
- `_bounds_union_sprite()`: Unions sprite bounds into bounding rect
- `_sprite_hitshape_union()`: Alternative hit shape union method

**Why It Matters:**
- Makes sprites clickable/selectable (not just the vector geometry)
- Improves UX when components have large decorative images
- Ensures accurate bounds calculation

**Implementation Impact:** Medium  
**User Benefit:** High - Much easier to select components with sprites

---

### 3. **BaseObj itemChange Selection Handling** ✨ MEDIUM PRIORITY

**Location in V2:** Lines 195-203  
**Status in Package:** Partial (missing sprite update logic)

**What's Different:**
- V2 calls `update()` on both the item and sprite when selection state changes
- Ensures sprite tint effect appears/disappears immediately
- Prevents lingering visual artifacts

**Implementation Impact:** Low  
**User Benefit:** Medium - Cleaner selection feedback

---

### 4. **Ghost Preview During Drag** ✨✨ HIGHEST PRIORITY

**Location in V2:** Lines 1212-1350  
**Status in Package:** Missing entirely

**What's Different:**
V2 implements a "ghost" preview system:
- `_ghost_item` and `_ghost_rec` instance variables
- `_clear_ghost()`: Removes ghost from scene
- `_make_ghost()`: Creates semi-transparent preview item
- `dragEnterEvent()`: Creates ghost when drag enters (line 1299-1310)
- `dragMoveEvent()`: Moves ghost with cursor (line 1312-1325)
- `dragLeaveEvent()`: Removes ghost (line 1327-1329)
- `dropEvent()`: Clears ghost before creating real item (line 1331-1350)

**Why It Matters:**
- Users can see exactly what they're about to drop and where
- Preview includes the component's decorative sprite
- Huge UX improvement for drag-and-drop workflow

**Implementation Impact:** High (significant new code)  
**User Benefit:** Very High - Major UX enhancement

---

### 5. **GraphicsView Pan Controls** ✨ MEDIUM PRIORITY

**Location in V2:** Lines 1354-1383  
**Status in Package:** Missing

**What's Different:**
V2 implements two pan modes not in the package:
- **Space key pan:** Hold space → drag to pan (lines 1354-1366)
- **Middle mouse button pan:** Middle-click drag to pan (lines 1368-1383)

**Implementation Details:**
- `_hand` flag tracks space key state
- Temporarily switches drag mode to `ScrollHandDrag`
- Middle button creates fake left button event in scroll mode

**Implementation Impact:** Low  
**User Benefit:** Medium - More intuitive navigation

---

### 6. **Improved Sprite Attachment** ✨ LOW PRIORITY

**Location in V2:** Lines 431-492 (LensItem)  
**Status in Package:** Present but simpler

**What's Different:**
- V2 calls `prepareGeometryChange()` before sprite operations
- More robust error handling in sprite removal
- Selection effect logic (colorize effect)
- Makes sprite non-interactive more explicitly

**Implementation Impact:** Low (refinement of existing code)  
**User Benefit:** Low - Prevents edge case bugs

---

### 7. **Selection Halo on Elements** ✨ LOW PRIORITY

**Location in V2:** Lines 515-519 (LensItem.paint)  
**Status in Package:** Missing

**What's Different:**
- Draws a translucent blue "halo" around selected items
- Uses `State_Selected` flag to detect selection
- Only in V2's LensItem, not in other items

**Note:** Inconsistently applied in V2 (only LensItem has it)

**Implementation Impact:** Very Low  
**User Benefit:** Low - Qt already provides selection feedback

---

### 8. **BUG: Duplicate _build_menubar Method** ❌ BUG

**Location in V2:** Lines 1634-1664 and 1675-1693  
**Status in Package:** Not present

**What It Is:**
V2 has `_build_menubar()` defined twice, second definition overrides the first

**Action:** Do not port this bug

---

### 9. **Insert Menu** ✨ LOW PRIORITY

**Location in V2:** Lines 1641-1648  
**Status in Package:** Missing

**What's Different:**
- V2 has an "Insert" menu with all component/tool additions
- Package only has View, Tools, and File menus
- Better organization of UI commands

**Implementation Impact:** Very Low  
**User Benefit:** Low - Nice organizational touch

---

## Implementation Priority Ranking

### 🔴 PHASE 1: Critical UX Improvements

1. **Ghost Preview During Drag** (Item #4)
   - Most impactful user experience enhancement
   - Clearly shows what will be dropped
   - Estimated time: 3-4 hours

2. **Sprite Helper Methods + Shape Union** (Items #2, #6)
   - Makes sprites properly clickable
   - Essential for good component interaction
   - Estimated time: 2-3 hours

### 🟡 PHASE 2: Visual Feedback Enhancements

3. **ComponentSprite Selection Feedback** (Item #1)
   - Blue tint when selected
   - Clear visual indication
   - Estimated time: 1-2 hours

4. **BaseObj itemChange Sprite Updates** (Item #3)
   - Prevents visual artifacts
   - Estimated time: 30 minutes

### 🟢 PHASE 3: Nice-to-Have Improvements

5. **Pan Controls** (Item #5)
   - Space key and middle button pan
   - Estimated time: 1 hour

6. **Insert Menu** (Item #9)
   - Better menu organization
   - Estimated time: 15 minutes

### ⚪ PHASE 4: Optional Polish

7. **Selection Halo** (Item #7)
   - Visual polish (low value since Qt handles this)
   - Estimated time: 30 minutes

---

## Detailed Implementation Plan

### PHASE 1.1: Ghost Preview System

**Files to modify:**
- `src/optiverse/widgets/graphics_view.py`

**Steps:**
1. Add instance variables to `GraphicsView.__init__()`:
   ```python
   self._ghost_item: Optional[QtWidgets.QGraphicsItem] = None
   self._ghost_rec: Optional[dict] = None
   ```

2. Add helper methods:
   - `_clear_ghost()`: Remove and delete ghost item
   - `_make_ghost(rec: dict, scene_pos: QtCore.QPointF)`: Create preview item

3. Modify drag/drop event handlers:
   - `dragEnterEvent()`: Create ghost on entry
   - `dragMoveEvent()`: Move ghost with cursor
   - `dragLeaveEvent()`: Clear ghost
   - `dropEvent()`: Clear ghost before creating real item

4. Ghost item characteristics:
   - Set `setOpacity(0.7)` for transparency
   - Set `setAcceptedMouseButtons(QtCore.Qt.NoButton)` to prevent interaction
   - Set `ItemIsMovable` and `ItemIsSelectable` to `False`
   - Set `setZValue(9_999)` to render on top
   - Call `_maybe_attach_sprite()` so decorative image shows

**Testing:**
- Drag components from library → ghost should appear
- Move cursor → ghost should follow
- Cancel drag → ghost should disappear
- Complete drop → real item should appear, ghost gone

---

### PHASE 1.2: Sprite Shape/Bounds Union

**Files to modify:**
- `src/optiverse/widgets/base_obj.py`
- `src/optiverse/widgets/lens_item.py`
- `src/optiverse/widgets/mirror_item.py`
- `src/optiverse/widgets/beamsplitter_item.py`

**Steps:**

1. **Add to BaseObj** (`base_obj.py`):
   ```python
   def _sprite_rect_in_item(self) -> Optional[QtCore.QRectF]:
       """Get sprite bounds in item-local coordinates."""
       sp = getattr(self, "_sprite", None)
       if sp is None or not sp.isVisible():
           return None
       return sp.mapRectToParent(sp.boundingRect())
   
   def _shape_union_sprite(self, shape_path: QtGui.QPainterPath) -> QtGui.QPainterPath:
       """Union sprite bounds into shape for hit testing."""
       r = self._sprite_rect_in_item()
       if r is not None:
           pad = 1.0
           rp = QtGui.QPainterPath()
           rp.addRect(r.adjusted(-pad, -pad, pad, pad))
           shape_path = shape_path.united(rp)
       return shape_path
   
   def _bounds_union_sprite(self, base_rect: QtCore.QRectF) -> QtCore.QRectF:
       """Union sprite bounds into bounding rect."""
       r = self._sprite_rect_in_item()
       if r is not None:
           pad = 2.0
           r = r.adjusted(-pad, -pad, pad, pad)
           base_rect = base_rect.united(r)
       return base_rect
   ```

2. **Modify element items** (LensItem, MirrorItem, BeamsplitterItem):
   - In `boundingRect()`: Wrap return with `return self._bounds_union_sprite(rect)`
   - In `shape()`: Wrap return with `return self._shape_union_sprite(shp)`

**Testing:**
- Drop component with sprite
- Click on sprite image → should select the item
- Hover over sprite → should show hand cursor
- Bounding box should encompass entire sprite

---

### PHASE 2.1: ComponentSprite Selection Feedback

**Files to modify:**
- `src/optiverse/widgets/component_sprite.py`

**Steps:**

1. **Add paint override** to `ComponentSprite`:
   ```python
   def paint(self, p: QtGui.QPainter, opt, widget=None):
       super().paint(p, opt, widget)
       par = self.parentItem()
       if par is not None and par.isSelected():
           p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
           p.setPen(QtCore.Qt.PenStyle.NoPen)
           p.setBrush(QtGui.QColor(30, 144, 255, 70))  # translucent blue
           p.drawRect(self.boundingRect())
   ```

**Alternative approach (using effects):**
In element items' `_maybe_attach_sprite()`:
```python
if self.isSelected():
    eff = QtWidgets.QGraphicsColorizeEffect()
    eff.setColor(QtGui.QColor(64, 128, 255))
    eff.setStrength(0.28)
    sp.setGraphicsEffect(eff)
else:
    sp.setGraphicsEffect(None)
```

**Recommendation:** Use the `paint()` override approach (simpler, less overhead)

**Testing:**
- Select component with sprite → sprite should have blue tint
- Deselect → tint should disappear
- Multiple components → only selected ones tinted

---

### PHASE 2.2: ItemChange Sprite Updates

**Files to modify:**
- `src/optiverse/widgets/base_obj.py`

**Steps:**

1. **Modify itemChange()** in BaseObj:
   ```python
   def itemChange(self, change, value):
       """Sync params when position or rotation changes."""
       if change in (
           QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
           QtWidgets.QGraphicsItem.GraphicsItemChange.ItemRotationHasChanged,
       ):
           if getattr(self, "_ready", False) and self.scene() is not None:
               self._sync_params_from_item()
               self.edited.emit()
       
       # Ensure sprite re-renders when selection toggles
       if change in (
           QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedChange,
           QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged,
       ):
           self.update()
           sp = getattr(self, "_sprite", None)
           if sp is not None:
               sp.update()
       
       return super().itemChange(change, value)
   ```

**Testing:**
- Select/deselect components rapidly → tint should update cleanly
- No visual artifacts or lingering effects

---

### PHASE 3.1: Pan Controls

**Files to modify:**
- `src/optiverse/widgets/graphics_view.py`

**Steps:**

1. **Add instance variable** to `GraphicsView.__init__()`:
   ```python
   self._hand = False
   ```

2. **Add key handlers:**
   ```python
   def keyPressEvent(self, e: QtGui.QKeyEvent):
       if e.key() == QtCore.Qt.Key.Key_Space:
           self._hand = True
           self.setDragMode(self.DragMode.ScrollHandDrag)
           return
       super().keyPressEvent(e)
   
   def keyReleaseEvent(self, e: QtGui.QKeyEvent):
       if e.key() == QtCore.Qt.Key.Key_Space and self._hand:
           self._hand = False
           self.setDragMode(self.DragMode.RubberBandDrag)
           return
       super().keyReleaseEvent(e)
   ```

3. **Add middle button handler:**
   ```python
   def mousePressEvent(self, e: QtGui.QMouseEvent):
       if e.button() == QtCore.Qt.MouseButton.MiddleButton:
           self.setDragMode(self.DragMode.ScrollHandDrag)
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
   
   def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
       if e.button() == QtCore.Qt.MouseButton.MiddleButton:
           fake = QtGui.QMouseEvent(
               QtCore.QEvent.Type.MouseButtonRelease,
               e.position(),
               QtCore.Qt.MouseButton.LeftButton,
               QtCore.Qt.MouseButton.NoButton,
               e.modifiers()
           )
           super().mouseReleaseEvent(fake)
           self.setDragMode(self.DragMode.RubberBandDrag)
       else:
           super().mouseReleaseEvent(e)
   ```

**Testing:**
- Hold space → cursor changes → drag pans view → release space → back to select mode
- Click middle button → drag pans → release → back to select mode
- Both methods should feel natural and responsive

---

### PHASE 3.2: Insert Menu

**Files to modify:**
- `src/optiverse/ui/views/main_window.py`

**Steps:**

1. **Modify _build_menubar():**
   ```python
   def _build_menubar(self):
       mb = self.menuBar()
       
       # File menu
       mFile = mb.addMenu("&File")
       mFile.addAction(self.act_open)
       mFile.addAction(self.act_save)
       
       # Insert menu (NEW)
       mInsert = mb.addMenu("&Insert")
       mInsert.addAction(self.act_add_source)
       mInsert.addAction(self.act_add_lens)
       mInsert.addAction(self.act_add_mirror)
       mInsert.addAction(self.act_add_bs)
       mInsert.addSeparator()
       mInsert.addAction(self.act_add_ruler)
       mInsert.addAction(self.act_add_text)
       
       # View menu (unchanged)
       mView = mb.addMenu("&View")
       ...
       
       # Tools menu (unchanged)
       mTools = mb.addMenu("&Tools")
       ...
   ```

**Testing:**
- Check menu bar has Insert menu between File and View
- All insert actions work correctly
- Keyboard shortcuts still functional

---

## Testing Checklist

After implementing each phase, verify:

### Ghost Preview
- [ ] Ghost appears when dragging component from library
- [ ] Ghost follows cursor smoothly
- [ ] Ghost includes component sprite if available
- [ ] Ghost disappears on drag cancel
- [ ] Real component appears on drop, ghost is cleaned up
- [ ] No memory leaks (ghost items properly removed)

### Sprite Interaction
- [ ] Can click on sprite to select component
- [ ] Can drag component by clicking sprite
- [ ] Bounding box encompasses sprite
- [ ] Selection feedback visible on sprite
- [ ] No performance issues with large sprites

### Pan Controls
- [ ] Space + drag pans view
- [ ] Middle button + drag pans view
- [ ] Both methods restore selection mode after release
- [ ] No conflicts with existing shortcuts

### Visual Feedback
- [ ] Selected components show blue tint on sprite
- [ ] Tint appears/disappears cleanly
- [ ] No artifacts or flickering
- [ ] Works with multiple selected items

---

## Risk Assessment

### Low Risk
- Insert menu addition
- ItemChange sprite updates
- Selection feedback on sprites

### Medium Risk
- Sprite shape/bounds union (affects hit testing)
- Pan controls (could conflict with existing shortcuts)

### High Risk
- Ghost preview system (complex state management, potential memory leaks)

**Mitigation:**
- Implement in order of priority
- Test thoroughly after each phase
- Keep V2 file as reference
- Git commit after each working phase

---

## Backwards Compatibility

All changes are additive or refinements:
- No breaking API changes
- No changes to save file format
- No changes to core ray tracing logic
- Existing user workflows unchanged

---

## Estimated Total Time

- Phase 1: 5-7 hours
- Phase 2: 2-3 hours  
- Phase 3: 1.5 hours
- Testing: 2-3 hours

**Total: 10.5-14.5 hours**

---

## Notes

1. **_default_angle_for_record()**: V2 has this helper (lines 29-41) but current package handles angles differently. Check if needed during ghost implementation.

2. **ComponentSprite caching**: V2 uses `NoCache` (line 396), current uses `DeviceCoordinateCache`. V2 comment says "important" but unclear why. Investigate if causes issues.

3. **RulerItem**: Both versions are identical, no porting needed.

4. **TextNoteItem**: Both versions are identical, no porting needed.

5. **Event filter logic**: Both versions handle snap and ruler placement in main window event filter. No changes needed.

---

## Success Criteria

Implementation is successful when:
1. ✅ Ghost preview works smoothly during drag/drop
2. ✅ Component sprites are fully interactive (clickable/hoverable)
3. ✅ Selection feedback is clear and immediate
4. ✅ Pan controls feel natural and intuitive
5. ✅ All existing functionality still works
6. ✅ No performance regressions
7. ✅ No memory leaks
8. ✅ UI feels more polished and professional

