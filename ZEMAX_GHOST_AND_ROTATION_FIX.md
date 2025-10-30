# Zemax Ghost Preview and Rotation Fixes - COMPLETE

## Issues Fixed

### 1. Spurious Horizontal Blue Line - FIXED

**Problem**: A thick horizontal blue line appeared on refractive objects imported from Zemax.

**Root Cause**: The perpendicular reference line calculation was creating a degenerate or very short interface that was being drawn.

**Solution**: 
- Added validation to skip drawing interfaces shorter than 0.1mm
- This filters out any spurious lines created during coordinate transformations

**Files Changed**:
- `src/optiverse/objects/refractive/refractive_object_item.py` - Added interface length check in paint()

### 2. Ghost Preview Rotation (90° and Flipping) - FIXED

**Problem**: When dragging a Zemax-imported component from the library, the ghost preview appeared rotated 90° and would flip when placed.

**Root Cause**: The `_make_ghost()` method in `graphics_view.py` didn't handle `RefractiveObjectItem` at all. Zemax imports with `element_type="refractive_interface"` should create `RefractiveObjectItem`, but the ghost was defaulting to `MirrorItem`.

**Solution**: Added proper detection and handling for `RefractiveObjectItem` in the ghost preview:
- Check if all interfaces are `refractive_interface` type OR if there are mixed interface types
- If so, create `RefractiveObjectItem` ghost with proper interface conversion
- This ensures the ghost preview matches what will actually be dropped

**Files Changed**:
- `src/optiverse/objects/views/graphics_view.py` - Added RefractiveObjectItem support in `_make_ghost()`

### 3. Sprite Rotation Direction Correction - FIXED

**Problem**: The sprite orientation was off by 180° after initial perpendicular calculation fix.

**Root Cause**: The perpendicular reference line direction needed to point in the opposite direction to match sprite image orientation.

**Solution**: 
1. Compute perpendicular line (counterclockwise rotation: `(-dy, dx)`)
2. **Flip 180°** by swapping the endpoints of the reference line
3. This ensures the sprite aligns correctly with the optical axis

**Example**:
```python
# Interface: (5, -10) to (5, +10) - vertical, pointing UP
# dx=0, dy=20
# Perpendicular (counterclockwise): perp = (-dy, dx) = (-20, 0) → LEFT

# Create reference line with 180° flip (swap endpoints):
# reference_line_mm = (cx - perp_dx, cy - perp_dy, cx + perp_dx, cy + perp_dy)
# Instead of: (cx + perp_dx, cy + perp_dy, cx - perp_dx, cy - perp_dy)
```

**Files Changed**:
- `src/optiverse/objects/refractive/refractive_object_item.py` - Flipped reference line endpoints

### 3. Coordinate Offset Calculation

**Problem**: Used redundant recalculation of interface center instead of using the already-computed center.

**Solution**: Simplified `_picked_line_offset_mm` calculation to use `(cx, cy)` directly since reference line is centered at interface center.

**Files Changed**:
- `src/optiverse/objects/refractive/refractive_object_item.py` - Simplified offset calculation

## Changes Summary

### `graphics_view.py`

Added detection logic for RefractiveObjectItem components:
```python
# Check if this should be a RefractiveObjectItem (for multi-interface Zemax imports)
use_refractive_item = False
if has_interfaces:
    interface_types = [iface.get("element_type", "lens") for iface in interfaces_data]
    first_type = interface_types[0]
    
    all_refractive = all(t == "refractive_interface" for t in interface_types)
    all_same_type = all(t == first_type for t in interface_types)
    
    use_refractive_item = all_refractive or (len(interfaces_data) > 1 and not all_same_type)
```

Then creates proper `RefractiveObjectItem` ghost with interface conversion.

### `refractive_object_item.py`

Fixed perpendicular rotation to be clockwise:
```python
# Perpendicular: rotate 90° CLOCKWISE: (dx, dy) → (dy, -dx)
perp_dx = dy / interface_length * half_length
perp_dy = -dx / interface_length * half_length
```

## Testing

1. **Import Zemax file** with refractive interfaces
2. **Drag from library** - ghost should show correct orientation
3. **Drop on canvas** - component should maintain same orientation as ghost
4. **Sprite orientation** - should align with interface lines (not rotated 90°)

## Final Implementation

### Reference Line Calculation

The final solution uses a perpendicular line to the first interface, flipped 180° to match sprite orientation:

```python
# Get interface direction and length
dx = first_interface.x2_mm - first_interface.x1_mm
dy = first_interface.y2_mm - first_interface.y1_mm
interface_length = (dx**2 + dy**2)**0.5

# Get interface center
cx = 0.5 * (first_interface.x1_mm + first_interface.x2_mm)
cy = 0.5 * (first_interface.y1_mm + first_interface.y2_mm)

# Create perpendicular (90° counterclockwise)
half_length = interface_length / 2.0
perp_dx = -dy / interface_length * half_length
perp_dy = dx / interface_length * half_length

# Flip 180° by swapping endpoints
reference_line_mm = (
    cx - perp_dx,  # Swapped
    cy - perp_dy,  # Swapped
    cx + perp_dx,  # Swapped
    cy + perp_dy   # Swapped
)
```

### Interface Drawing Validation

Added length check to prevent drawing degenerate interfaces:

```python
# Skip drawing if interface is too short (degenerate/invalid)
dx_check = p2.x() - p1.x()
dy_check = p2.y() - p1.y()
length_check = (dx_check**2 + dy_check**2)**0.5
if length_check < 0.1:  # Skip very short interfaces
    continue
```

## Related Files

- `src/optiverse/objects/views/graphics_view.py` - Ghost preview system
- `src/optiverse/objects/refractive/refractive_object_item.py` - Sprite positioning
- `src/optiverse/objects/component_sprite.py` - Sprite rendering (no changes)
- `src/optiverse/ui/views/main_window.py` - Component dropping (reference for routing logic)

