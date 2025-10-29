# Drag Lock Feature - Selective Interface Editing

## Overview

The component editor now supports **drag locking**, which restricts dragging to only the selected interface. This prevents accidentally moving other interfaces while you're editing one specific interface.

## Problem Solved

**Before:**
- Clicking "Edit" on simple components (lens, mirror) failed because they don't use the `_interfaces` list
- When editing one interface, you could accidentally drag other interfaces too
- No visual feedback about which interface you're editing

**After:**
- ✅ "Edit" works for all component types
- ✅ Can only drag the locked interface
- ✅ Other interfaces are dimmed and non-interactive
- ✅ Click outside or close dialog to unlock

## How It Works

### For Simple Components (Lens, Mirror, BS, Dichroic)

1. Select the calibration line in the interfaces list
2. Click "Edit"
3. **No dialog opens** (simple components don't need property dialogs)
4. The line is **locked** for editing
5. **Drag the line endpoints** - only this line moves
6. **Click on empty space** to finish editing
7. Status bar shows: "Editing: Drag only this line. Click outside to finish editing."

### For Refractive Objects

1. Select an interface from the list
2. Click "Edit"
3. Dialog opens with interface properties
4. The selected interface is **locked** for editing
5. **Drag only this interface's endpoints** while the dialog is open
6. Other interfaces are **dimmed** and cannot be dragged
7. Adjust properties in dialog, click "Apply"
8. Click "Close" to finish editing and unlock

## Visual Feedback

### Locked Interface
- **Thick line** (3px width)
- **Full color** (bright)
- **Large endpoint circles** (6px)
- **Hand cursor** when hovering
- Can be dragged

### Non-Locked Interfaces (when lock is active)
- **Thin line** (1.5px width)
- **Dimmed** (80% transparent)
- **No endpoint circles**
- **Arrow cursor** when hovering
- Cannot be dragged

### Example (BS Cube with Interface 3 Locked)
```
Interface 1: ────── (dimmed, can't drag)
Interface 2: ────── (dimmed, can't drag)
Interface 3: ══════ (bright, can drag) ← LOCKED
Interface 4: ────── (dimmed, can't drag)
Interface 5: ────── (dimmed, can't drag)
```

## User Workflow

### Simple Component
```
1. Load lens component
2. Interfaces list shows: "Calibration line (lens)"
3. Click in list to select
4. Click "Edit" button
5. ✅ Line locks (status bar message)
6. Drag endpoints to adjust
7. Click outside image to unlock
8. Done!
```

### Refractive Object
```
1. Load BS cube (5 interfaces)
2. Select "Interface 3" (diagonal green line)
3. Click "Edit"
4. ✅ Dialog opens, line locks
5. ✅ Other 4 lines dim out
6. Drag endpoints of Interface 3 only
7. Adjust properties: T=70%, R=30%
8. Click "Apply"
9. Keep dragging if needed
10. Click "Close" to unlock
11. All lines return to normal
```

## Technical Implementation

### Canvas Drag Lock State

```python
self._drag_locked_line: int = -1  # -1 = no lock, ≥0 = locked line index

def set_drag_lock(self, line_index: int):
    """Lock dragging to only this line."""
    self._drag_locked_line = line_index
    self._selected_line = line_index
    self.update()

def clear_drag_lock(self):
    """Clear lock, allow all lines to be dragged."""
    self._drag_locked_line = -1
    self.update()
```

### Mouse Event Filtering

```python
def mousePressEvent(self, e):
    line_idx, point_num = self._get_line_and_point_at(e.pos())
    
    # Check drag lock
    if self._drag_locked_line >= 0 and line_idx != self._drag_locked_line:
        # Trying to drag wrong line - ignore!
        return
    
    # Allow dragging the locked line
    self._dragging_line = line_idx
    ...
```

### Unlock Triggers

1. **Click on empty space** (outside any line)
   ```python
   if self._drag_locked_line >= 0:
       self.clear_drag_lock()
   ```

2. **Close edit dialog** (for refractive objects)
   ```python
   def on_dialog_close():
       self.canvas.clear_drag_lock()
       self.statusBar().showMessage("Ready")
   ```

3. **Dialog finished signal** (backup)
   ```python
   d.finished.connect(lambda: self.canvas.clear_drag_lock())
   ```

## Keyboard Shortcuts

While a line is locked, you can:
- **ESC**: Click outside to unlock (no specific key binding yet, but clicking works)
- **Drag**: Only the locked line responds

## Status Bar Messages

| Action | Message |
|--------|---------|
| Simple component edit | "Editing: Drag only this line. Click outside to finish editing." |
| Dialog opened | (No change, shows last message) |
| Unlock | "Ready" |

## Benefits

✅ **Precision editing**: Can't accidentally move wrong interface  
✅ **Visual clarity**: Dimmed lines show what's locked  
✅ **Works everywhere**: Simple and complex components  
✅ **Intuitive**: Click outside to unlock  
✅ **Non-blocking**: Edit dialog doesn't prevent dragging  
✅ **Feedback**: Status bar and visual cues guide user  

## Edge Cases Handled

1. **No interface selected**: Shows "Please select an interface to edit."
2. **Simple component**: No dialog, just locks the line
3. **Multiple interfaces**: Only locked one can be dragged
4. **Dialog closed unexpectedly**: Lock clears automatically
5. **Click outside**: Unlocks immediately

## Testing

### Test 1: Simple Component Lock
```
1. Open lens component
2. Select "Calibration line (lens)"
3. Click "Edit"
4. EXPECT: Status bar shows "Editing: Drag only..."
5. EXPECT: Can drag line
6. Click on empty canvas
7. EXPECT: Lock clears, status shows "Ready"
```

### Test 2: Multi-Interface Lock
```
1. Open BS cube (5 lines)
2. Select Interface 3 (diagonal)
3. Click "Edit"
4. EXPECT: Dialog opens
5. EXPECT: Interfaces 1,2,4,5 dimmed
6. EXPECT: Interface 3 bright
7. Try to drag Interface 1
8. EXPECT: Nothing happens (blocked)
9. Drag Interface 3
10. EXPECT: Moves normally
11. Click "Close"
12. EXPECT: All lines normal brightness
```

### Test 3: Visual Feedback
```
1. Create refractive object with 3 interfaces
2. Lock Interface 2
3. EXPECT: Interface 2 has thick line (3px)
4. EXPECT: Interfaces 1,3 have thin dimmed lines (1.5px, transparent)
5. Hover over Interface 1
6. EXPECT: Cursor stays as arrow (no hand)
7. Hover over Interface 2
8. EXPECT: Cursor changes to hand
```

## Files Modified

1. **`src/optiverse/ui/views/component_editor_dialog.py`**
   - Modified `_edit_interface()` to handle simple components
   - Added drag lock call for simple components
   - Added drag lock call for refractive objects
   - Added unlock on dialog close

2. **`src/optiverse/objects/views/multi_line_canvas.py`**
   - Added `_drag_locked_line` state variable
   - Added `set_drag_lock()` method
   - Added `clear_drag_lock()` method
   - Modified `mousePressEvent()` to check lock
   - Modified `mouseMoveEvent()` hover detection
   - Modified `_draw_line()` to dim non-locked lines

## Future Enhancements

Possible improvements:
- ESC key to unlock (in addition to clicking outside)
- Lock indicator in interface list (e.g., 🔒 icon)
- Multi-line lock (edit multiple interfaces simultaneously)
- Lock persistence across sessions

## Success Criteria

✅ Edit works for simple components  
✅ Only locked line can be dragged  
✅ Other lines are visually dimmed  
✅ Hover only works on locked line  
✅ Click outside unlocks  
✅ Dialog close unlocks  
✅ Status bar provides feedback  
✅ No accidental drags  

**The drag lock feature is complete and working!**

