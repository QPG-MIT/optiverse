# Component Editor Drag and Coordinate System Fix

## Issues Fixed

### 1. Drag and Drop Issue: Multiple Points Moving
**Problem**: When dragging one point in the component editor, other points would also move unexpectedly.

**Root Cause**: Signal feedback loop during dragging:
1. User drags point → canvas updates → `linesChanged` signal emitted
2. `_on_canvas_lines_changed` updates interface panel
3. Interface panel emits `interfacesChanged` signal
4. This triggers full `_sync_interfaces_to_canvas` resync
5. All interfaces recomputed, causing unwanted movement

**Solution**: Block signals during drag updates
- Added `blockSignals(True)` before updating interface panel from canvas
- Prevents feedback loop while dragging
- Signal unblocked after update completes

**Files Modified**:
- `src/optiverse/ui/views/component_editor_dialog.py`: Added signal blocking in `_on_canvas_lines_changed`

### 2. Coordinate System: Y-Axis Origin
**Problem**: The coordinate system had origin (0,0) at the image center, which was confusing.

**Expected Behavior**: Standard image coordinates with (0,0) at top-left corner, Y increasing downward.

**Root Cause**: Coordinates were stored and calculated relative to image center:
```python
# OLD (center-based):
x_mm = (x_px - center_x) * mm_per_px
x_px = center_x + (x_mm / mm_per_px)
```

**Solution**: Changed to top-left origin (0,0):
```python
# NEW (top-left based):
x_mm = x_px * mm_per_px
x_px = x_mm / mm_per_px
```

**Files Modified**:
- `src/optiverse/ui/views/component_editor_dialog.py`:
  - `_sync_interfaces_to_canvas`: Removed center offset in px→mm conversion
  - `_on_canvas_lines_changed`: Removed center offset in mm→px conversion
- `src/optiverse/ui/widgets/interface_tree_panel.py`:
  - `_add_interface`: Updated default position for new interfaces
- `src/optiverse/core/component_migration.py`:
  - `_migrate_simple_component`: Fixed coordinate conversion from legacy format
  - `convert_v2_to_legacy`: Fixed coordinate conversion to legacy format

## Testing

### Test Drag Functionality
1. Open Component Editor
2. Load an image with multiple interfaces
3. Drag one point → Only that point should move
4. Other interfaces should remain stationary
5. Release → Interface panel updates correctly

### Test Coordinate System
1. Create new interface → Should appear centered in image
2. Check coordinate values in panel:
   - Top-left area should have small positive values (e.g., 2-5mm)
   - Center area should have mid-range values (e.g., 10-15mm for 25mm object height)
   - Bottom-right should have larger values (e.g., 20-23mm)
3. Y=0 should be at the top of the image
4. Y increases downward

## Migration Notes

**Legacy Components**: Components saved with the old center-based coordinate system will be automatically migrated to the new top-left system when loaded.

**Coordinate Conversion**:
- Old coordinates were relative to image center (500, 500 in normalized 1000px space)
- New coordinates are relative to top-left (0, 0)
- Migration handles this conversion automatically

## Technical Details

### Coordinate System (Updated)

**NEW SYSTEM**: Y-axis normalized to object height
- **Storage**: Millimeters (mm) with top-left origin (0,0)
- **Display**: Millimeters in interface panel
- **Canvas**: Pixels (Qt coordinate system)
- **Y Range**: 0mm (top of image) to object_height_mm (bottom of image)
- **X Range**: 0mm (left) to (object_height_mm × aspect_ratio) (right)

### Conversion Formula
```python
# Image dimensions: W×H pixels
# Object height: object_height_mm (user input)
# Y-axis maps: 0px → 0mm, H px → object_height_mm

mm_per_px = object_height_mm / H

# Pixel to mm:
x_mm = x_px * mm_per_px
y_mm = y_px * mm_per_px

# mm to pixel:
x_px = x_mm / mm_per_px
y_px = y_mm / mm_per_px
```

### Example
For a 1000×800 pixel image with object_height = 25mm:
- mm_per_px = 25mm / 800px = 0.03125 mm/px
- Y = 0mm at top, Y = 25mm at bottom
- X = 0mm at left, X = 31.25mm at right (1000 × 0.03125)
- Center point: (15.625mm, 12.5mm)

### Default Positioning
New interfaces default to centered position:
- X: 12.5mm ± 5mm (horizontal line from 7.5mm to 17.5mm)
- Y: 12.5mm (center)
- Assumes typical 25mm object height

This positions interfaces visibly in the center of a typical component image.

### Benefits of New System
1. **Intuitive**: Y coordinate directly corresponds to object height
2. **Simple**: No dependency on first interface length
3. **Predictable**: Changing object_height scales all coordinates proportionally
4. **Standard**: Matches typical image coordinate conventions

