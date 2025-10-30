# Interface Coordinate System Fix - Quick Start

## ✅ **FIX COMPLETE**

The issue where optical interfaces appeared "completely off" when dragging components from the editor to the scene has been **FIXED**.

## What Was Fixed

**Problem**: Coordinate system mismatch between component editor canvas (centered, Y-up) and scene (top-left, Y-down)

**Solution**: Proper coordinate transformation in both directions:
- Editor → Storage: Convert from centered+Y-up to top-left+Y-down
- Storage → Editor: Convert from top-left+Y-down to centered+Y-up

## Files Changed

1. **`src/optiverse/ui/views/component_editor_dialog.py`**
   - Fixed `_sync_interfaces_to_canvas()` method (lines ~396-437)
   - Fixed `_on_canvas_lines_changed()` method (lines ~439-482)
   - Added detailed comments explaining coordinate transformations

## Testing

### Quick Test
```bash
python test_interface_coordinates.py
```
✅ All tests pass - coordinate transformations are mathematically correct

### Manual Testing Checklist

1. **Create simple interface**
   - Open Component Editor
   - Add interface at canvas center
   - Save and drag to scene
   - ✓ Should appear at component center

2. **Test with image sprite**
   - Load an image
   - Add interfaces aligned to image features
   - Save and drag to scene
   - ✓ Interfaces should align with sprite

3. **Test BS Cube preset**
   - Create BS cube with preset
   - Drag to scene
   - ✓ All 5 interfaces should be correctly positioned

4. **Test Zemax import**
   - Import .zmx file
   - Drag to scene
   - ✓ Interfaces should match Zemax geometry

## Coordinate Systems Explained

### Storage (InterfaceDefinition)
```
(0,0) ────────> +X
  |
  |
  v +Y (down)
```
- Standard image coordinates
- Y increases downward
- Used for JSON storage and scene rendering

### Canvas Display (Component Editor)
```
      +Y (up)
       |
-X <───┼───> +X
       |
      -Y (down)
       
    (0,0) = center
```
- Intuitive for editing
- Y increases upward
- Center origin for symmetry

### Transformation Formulas

**Storage → Canvas:**
```python
x_canvas = (x_storage - w_mm/2)
y_canvas = -(y_storage - h_mm/2)
```

**Canvas → Storage:**
```python
x_storage = x_canvas + (w_mm/2)
y_storage = -y_canvas + (h_mm/2)
```

## Known Issues

### ⚠️ Legacy Components
Components created BEFORE this fix may need to be recreated or migrated. They were stored in the old coordinate system (centered + Y-up) and will appear incorrectly.

**Solution**: Re-create affected components or run migration script (TBD)

### ⚠️ Sprite Alignment
RefractiveObjectItem with sprites assumes the sprite's picked line is at the image center. If not, additional alignment may be needed.

## Documentation

- **INTERFACE_COORDINATE_SYSTEM_FIX_STRATEGY.md** - Detailed analysis and strategy
- **INTERFACE_COORDINATE_FIX_COMPLETE.md** - Complete implementation guide
- **COORDINATE_FIX_README.md** - This quick reference (you are here)
- **test_interface_coordinates.py** - Automated test suite

## Next Steps

1. **Test the fix** with your existing components
2. **Report any issues** if interfaces still appear incorrectly
3. **Recreate legacy components** if they show problems
4. **Verify Zemax imports** work correctly with your files

## Questions?

If you encounter issues:
1. Check that object_height_mm is set correctly in the editor
2. Verify interfaces are within image bounds (0 to width, 0 to height)
3. Try the test script: `python test_interface_coordinates.py`
4. Check console output for coordinate values
5. Refer to detailed docs in INTERFACE_COORDINATE_FIX_COMPLETE.md

## Technical Summary

- **Root Cause**: Canvas used centered+Y-up coords, scene expected top-left+Y-down coords
- **Fix Location**: Component editor sync functions
- **Impact**: Minimal - only affects coordinate transformation, no changes to scene rendering
- **Backward Compatibility**: Legacy components may need recreation
- **Test Coverage**: Automated test suite verifies transformation correctness

---

**Status**: ✅ **FIX IMPLEMENTED AND TESTED**

The coordinate transformation is mathematically correct and ready for use. Test with your actual components and report any issues!

