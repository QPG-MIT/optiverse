# Interface Display Fix - Summary

## Problem
Optical interfaces were displayed correctly in the Component Editor but not visible on the main canvas when components were placed.

## Root Cause
The `RefractiveObjectItem._update_geom()` method calculated the bounding rectangle using raw interface coordinates (relative to image center), but the `paint()` method applied a coordinate transformation by subtracting the `picked_line_offset_mm`. This mismatch caused Qt's rendering system to believe the interfaces were in a different location than where they were actually being painted, resulting in the interfaces not being rendered on the canvas.

### Coordinate System Details
- **Component Editor (MultiLineCanvas)**: Uses Y-up coordinates for intuitive display (flips Y when rendering)
- **Storage**: Interfaces stored with Y-down coordinates (Qt standard), relative to image center
- **Main Canvas**: Uses Y-down coordinates (Qt standard QGraphicsScene)
- **RefractiveObjectItem**: Local origin (0,0) is at the picked line center, not image center

### The Offset Issue
When a component has a sprite image:
1. The sprite is centered on the "picked line" (the reference line drawn in the component editor)
2. Interfaces are stored relative to the image center
3. A `picked_line_offset_mm` is calculated to transform from image-center coords to picked-line-center coords
4. The `paint()` method correctly applied this offset
5. **BUG**: The `boundingRect()` did NOT account for this offset

This caused Qt to think the item occupied a different screen region, preventing proper rendering.

## Solution
Modified `RefractiveObjectItem._update_geom()` to apply the `picked_line_offset_mm` transformation when calculating the bounding rectangle, ensuring consistency between the bounding rect and the actual paint location.

### Changes Made
**File**: `src/optiverse/objects/refractive/refractive_object_item.py`

**Method**: `_update_geom()`

Added offset retrieval and applied it when computing interface bounds:

```python
def _update_geom(self):
    """Update geometry based on interfaces."""
    self.prepareGeometryChange()
    
    # Get picked line offset for coordinate transformation
    offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
    
    # Compute bounding box from all interfaces
    if self.params.interfaces:
        all_x = []
        all_y = []
        for iface in self.params.interfaces:
            # Apply picked line offset transformation
            # Interfaces are stored relative to image center, but item (0,0) is at picked line center
            all_x.extend([iface.x1_mm - offset_x, iface.x2_mm - offset_x])
            all_y.extend([iface.y1_mm - offset_y, iface.y2_mm - offset_y])
        
        # ... rest of method
```

## Initialization Sequence
The fix works correctly because:
1. `__init__` calls `_update_geom()` (offset is (0,0) initially)
2. `__init__` calls `_maybe_attach_sprite()`
3. `_maybe_attach_sprite()` calculates and sets `_picked_line_offset_mm`
4. `_maybe_attach_sprite()` calls `_update_geom()` again (now with correct offset)

So the bounding rectangle is recalculated with the proper offset after sprite attachment completes.

## Testing
To verify the fix:
1. Open the Component Editor
2. Import or create a component with multiple interfaces (e.g., from Zemax)
3. Save the component to the library
4. Drag and drop the component onto the main canvas
5. **Expected Result**: Interface lines should now be visible on the canvas, matching their position in the Component Editor

## Impact
This fix ensures that:
- All refractive components with sprites display their interfaces correctly on the main canvas
- Zemax-imported lenses and optical components show their surfaces properly
- Ray tracing can correctly intersect with the visible interfaces
- The visual representation matches the underlying optical model

## Related Files
- `src/optiverse/objects/refractive/refractive_object_item.py` (FIXED)
- `src/optiverse/objects/component_sprite.py` (coordinate system reference)
- `src/optiverse/objects/views/multi_line_canvas.py` (component editor canvas)
- `src/optiverse/ui/views/component_editor_dialog.py` (component editor)
- `src/optiverse/ui/views/main_window.py` (main canvas)

## Date
October 30, 2025

