# Coordinate Edit Dialog for Simple Components

## Overview

Simple components (lens, mirror, beamsplitter, dichroic) now have a **coordinate edit dialog** that allows you to view and adjust line endpoint positions both visually and numerically.

## Features

### Dual Input Methods

1. **Visual Dragging**: Drag line endpoints on the canvas
2. **Numeric Entry**: Type precise coordinates in spinboxes

### Real-Time Synchronization

- **Drag on canvas** → Spinboxes update automatically
- **Type in spinboxes** → Line moves on canvas immediately
- **Bidirectional sync**: Both methods work simultaneously

### Physical Coordinates Display

- Shows converted physical coordinates (mm) in real-time
- Read-only reference labels below each coordinate
- Automatically calculated from mm/px calibration

## User Interface

### Dialog Layout

```
┌─ Edit Calibration Line ─────────┐
│                                  │
│ Point 1 (Start)                  │
│ X₁: [450.00] px                  │
│   → Physical: 12.150 mm          │
│ Y₁: [300.00] px                  │
│   → Physical: 8.100 mm           │
│                                  │
│ Point 2 (End)                    │
│ X₂: [550.00] px                  │
│   → Physical: 14.850 mm          │
│ Y₂: [300.00] px                  │
│   → Physical: 8.100 mm           │
│                                  │
│ 💡 Drag line endpoints on        │
│    canvas to adjust visually     │
│                                  │
│ [Close]                          │
└──────────────────────────────────┘
```

### Visual Feedback

- **Dialog stays on top**: Can see canvas while editing
- **Non-modal**: Doesn't block interaction with canvas
- **Locked line**: Only selected line can be dragged
- **Other lines dimmed**: Visual indication of lock
- **Status bar**: "Editing: Drag endpoints or enter coordinates"

## How to Use

### Basic Workflow

1. **Select component** from interfaces list (e.g., "Calibration line (lens)")
2. **Click "Edit" button**
3. **Dialog opens** with current coordinates
4. **Adjust using either method**:
   - Drag endpoints on canvas, OR
   - Type values in spinboxes
5. **Watch real-time updates**:
   - Canvas updates as you type
   - Spinboxes update as you drag
   - Physical coordinates update automatically
6. **Click "Close"** when done

### Example: Precise Alignment

**Scenario**: Align lens line exactly at center

1. Load lens component
2. Note image dimensions in status (e.g., 1000x600 px)
3. Click "Edit" on calibration line
4. Type in spinboxes:
   - X₁: `450.00` px
   - Y₁: `300.00` px (center Y)
   - X₂: `550.00` px
   - Y₂: `300.00` px (same Y = horizontal)
5. Line snaps to exact position
6. Physical coordinates show mm values
7. Click "Close"

### Example: Visual + Fine-Tuning

**Scenario**: Rough visual placement, then precision

1. Load mirror component
2. Click "Edit"
3. **Drag** endpoints roughly into position
4. Watch spinboxes update in real-time
5. **Fine-tune** by typing exact values:
   - X₁: `252.43` → `252.00` (round to whole)
   - Y₁: `187.65` → `188.00`
6. Line adjusts to precise position
7. Click "Close"

## Coordinate Systems

### Pixel Coordinates (Normalized)

- **Range**: 0 to 1000 px
- **Normalized**: Always relative to 1000px image height
- **Independent of actual image size**
- **Stored/displayed** in dialog spinboxes

### Physical Coordinates (mm)

- **Calculated**: px × mm/px scale factor
- **Read-only**: Display only, not editable
- **Depends on**: Object height and line length calibration
- **Shows below** each pixel coordinate

### Conversion

```
Physical (mm) = Pixel (normalized) × mm_per_px

Where:
  mm_per_px = Object_Height_mm / Line_Length_px
```

**Example**:
- Object height: 25.4 mm (1 inch)
- Line length: 500 px
- mm/px = 25.4 / 500 = 0.0508
- X₁ = 450 px → 450 × 0.0508 = 22.86 mm

## Technical Implementation

### Bidirectional Binding

```python
# Spinbox → Canvas
def apply_spinbox_changes():
    line.x1 = x1_spin.value() / scale_norm
    line.y1 = y1_spin.value() / scale_norm
    line.x2 = x2_spin.value() / scale_norm
    line.y2 = y2_spin.value() / scale_norm
    canvas.update_line(row, line)

x1_spin.valueChanged.connect(apply_spinbox_changes)

# Canvas → Spinbox
def update_spinboxes_from_canvas():
    x1_spin.blockSignals(True)  # Prevent loop
    x1_spin.setValue(line.x1 * scale_norm)
    x1_spin.blockSignals(False)
    update_mm_labels()

canvas.linesChanged.connect(update_spinboxes_from_canvas)
```

### Signal Blocking

- **Prevents infinite loops**: Block signals when updating from opposite direction
- **Canvas changes spinbox**: Block spinbox signals
- **Spinbox changes canvas**: No need to block (canvas doesn't auto-update spinboxes)

### Dialog Lifecycle

```python
# Open dialog (non-modal)
d.setModal(False)
d.setWindowFlags(... | WindowStaysOnTopHint)
d.show()

# Lock canvas
canvas.set_drag_lock(row)

# On close
canvas.clear_drag_lock()
canvas.linesChanged.disconnect(connection)
d.close()
```

## Benefits

✅ **Precision**: Type exact coordinates  
✅ **Visual**: See changes immediately on canvas  
✅ **Flexible**: Use method that suits your workflow  
✅ **Physical units**: See mm values in real-time  
✅ **Non-blocking**: Drag while dialog is open  
✅ **Locked**: Only edit selected line  
✅ **Intuitive**: Familiar spinbox + drag interaction  

## Use Cases

### 1. Precise Centering
```
Goal: Center line horizontally at Y=300
Method: Type Y₁=300, Y₂=300 in spinboxes
Result: Perfect horizontal line
```

### 2. Specific Angle
```
Goal: 45° diagonal line
Method: Calculate endpoints, type in spinboxes
  X₁=400, Y₁=400
  X₂=500, Y₂=500
Result: Exact 45° angle
```

### 3. Quick Rough Placement
```
Goal: Approximate alignment
Method: Drag endpoints visually
Result: Close enough, fast
```

### 4. Rough + Fine
```
Goal: Best of both worlds
Method: 
  1. Drag roughly into place
  2. Watch spinbox values
  3. Round to nice numbers (252.43 → 252.00)
  4. Type rounded values
Result: Precise and efficient
```

## Comparison: Refractive vs Simple

| Feature | Simple Component | Refractive Object |
|---------|------------------|-------------------|
| **Dialog** | Coordinate editor | Property editor |
| **Fields** | X₁, Y₁, X₂, Y₂ | n₁, n₂, BS, PBS, etc. |
| **Physical coords** | Yes (display only) | Yes (editable) |
| **Drag while open** | ✅ Yes | ✅ Yes |
| **Real-time sync** | ✅ Yes | ❌ No (Apply button) |
| **Apply button** | ❌ Not needed | ✅ Required |

### Why Different?

**Simple components**: Only geometry matters
- Coordinates are primary data
- Direct manipulation makes sense
- Real-time sync is natural

**Refractive objects**: Physics properties matter
- Refractive indices, beam splitter ratios
- Multiple interfaces with complex properties
- Apply button prevents accidental changes

## Keyboard Shortcuts

- **Tab**: Move between spinboxes
- **Arrow keys**: Fine-tune values (±1)
- **Shift+Arrow**: Larger steps (±10)
- **Enter**: Accept value, move to next field
- **Esc** (in spinbox): Reset to previous value
- **Close dialog**: Click Close button

## Tips & Tricks

### Tip 1: Use Tab for Efficiency
```
1. Click in X₁ spinbox
2. Type value, press Tab
3. Type Y₁ value, press Tab
4. Type X₂ value, press Tab
5. Type Y₂ value
6. Done - no mouse needed!
```

### Tip 2: Arrow Keys for Fine-Tuning
```
1. Click spinbox
2. Use ↑↓ arrows to adjust by 1 px
3. Hold Shift + ↑↓ for 10 px steps
4. Perfect for micro-adjustments
```

### Tip 3: Watch Physical Coordinates
```
If you need line at specific physical position:
1. Open dialog
2. Adjust spinboxes
3. Watch "→ Physical:" labels
4. Stop when you hit target mm value
```

### Tip 4: Keep Dialog Open
```
Dialog is non-modal:
- Keep it open while working
- Drag, type, drag, type
- Only close when completely done
- No need to reopen repeatedly
```

## Troubleshooting

### Spinboxes Don't Update When Dragging
**Cause**: Dialog wasn't opened with Edit button  
**Solution**: Click Edit button first, then drag

### Can't Type in Spinboxes
**Cause**: Dialog might not have focus  
**Solution**: Click in the spinbox field

### Physical Coordinates Show "—"
**Cause**: No calibration (mm/px = 0)  
**Solution**: Enter object height and click two points first

### Line Jumps When Typing
**Cause**: Normal - line updates as you type each digit  
**Solution**: Type quickly or press Esc to cancel

## Testing

### Test 1: Open Dialog
```
1. Load lens component
2. Select "Calibration line (lens)"
3. Click "Edit"
4. EXPECT: Dialog opens
5. EXPECT: Shows X₁, Y₁, X₂, Y₂ values
6. EXPECT: Shows physical mm values (if calibrated)
```

### Test 2: Type → Canvas
```
1. Open edit dialog
2. Change X₁ from 450 to 500
3. EXPECT: Line endpoint moves on canvas
4. EXPECT: Physical coordinate updates
5. Type X₁ = 450 again
6. EXPECT: Line returns to original position
```

### Test 3: Drag → Spinbox
```
1. Open edit dialog
2. Drag left endpoint right (+50 px)
3. EXPECT: X₁ spinbox increases by ~50
4. EXPECT: Physical mm increases
5. EXPECT: Other spinboxes (Y₁, X₂, Y₂) unchanged
```

### Test 4: Real-Time Sync
```
1. Open dialog
2. Type X₁ = 400
3. EXPECT: Line moves immediately
4. Drag endpoint
5. EXPECT: Spinbox updates immediately
6. Continuous back-and-forth works
```

## Files Modified

- ✅ `src/optiverse/ui/views/component_editor_dialog.py`
  - Modified `_edit_interface()` for simple components
  - Added coordinate edit dialog
  - Added bidirectional sync logic
  - Added physical coordinate display

## Future Enhancements

Possible improvements:
- Copy/paste coordinates
- Undo/redo for coordinate changes
- Snap to grid option
- Angle/length display (computed from endpoints)
- Preset positions (center, corners, etc.)

## Success Criteria

✅ Dialog opens for simple components  
✅ Shows current coordinates  
✅ Type in spinbox → canvas updates  
✅ Drag on canvas → spinbox updates  
✅ Physical coordinates display  
✅ Non-modal (can drag while open)  
✅ Drag lock active  
✅ Close button unlocks  

**The coordinate edit dialog is complete and working!**

