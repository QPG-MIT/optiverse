# Zemax Sprite Rotation Fix - 90° Misalignment

## Problem

Zemax imported lenses displayed with sprites rotated 90° relative to the optical axis.

**Symptom**: Import Zemax lens → Add sprite image → Drop on canvas → Sprite appears rotated 90° from where it should be relative to the interface lines.

## Root Cause

The issue was in `RefractiveObjectItem._maybe_attach_sprite()` which uses the first interface as the reference line for sprite positioning. 

**Conceptual Mismatch:**
- **Interface line**: Represents the physical optical surface (perpendicular to optical axis)
- **Reference line**: Should represent the OPTICAL AXIS direction in the sprite image

For Zemax imports:
1. Zemax creates **vertical interface lines** (x1=x2, perpendicular to horizontal optical axis)
2. `RefractiveObjectItem` was using this vertical interface AS the reference line
3. `ComponentSprite` interpreted the reference line as the optical axis direction
4. Result: Sprite rotated to align vertical line with +X, but the sprite image expects horizontal optical axis
5. **90° rotation mismatch!**

### Example of the Bug

**Zemax interface:**
```python
(x1=5, y1=-10, x2=5, y2=+10)  # Vertical line (perpendicular to horizontal optical axis)
```

**Old behavior:**
- Reference line = interface = vertical (5, -10, 5, +10)
- ComponentSprite thinks: "Optical axis is vertical, rotate -90° to make it horizontal"
- But sprite image (lens.png) already has horizontal optical axis
- Result: Sprite rotates 90° in wrong direction ❌

## Solution

Changed `RefractiveObjectItem._maybe_attach_sprite()` to compute a **perpendicular line** to the interface as the reference line. This perpendicular line represents the optical axis direction, which matches the sprite image convention.

### Code Changes

**File:** `src/optiverse/objects/refractive/refractive_object_item.py`

**Before:**
```python
# Use first interface as reference line for sprite positioning
first_interface = self.params.interfaces[0]
reference_line_mm = (
    first_interface.x1_mm,
    first_interface.y1_mm,
    first_interface.x2_mm,
    first_interface.y2_mm
)
```

**After:**
```python
# Get interface direction
dx = first_interface.x2_mm - first_interface.x1_mm
dy = first_interface.y2_mm - first_interface.y1_mm
interface_length = (dx**2 + dy**2)**0.5

# Get interface center
cx = 0.5 * (first_interface.x1_mm + first_interface.x2_mm)
cy = 0.5 * (first_interface.y1_mm + first_interface.y2_mm)

# Create perpendicular line (optical axis direction) centered at interface
# Perpendicular: rotate 90°: (dx, dy) → (-dy, dx)
half_length = interface_length / 2.0
if interface_length > 0:
    perp_dx = -dy / interface_length * half_length
    perp_dy = dx / interface_length * half_length
else:
    perp_dx = half_length
    perp_dy = 0.0

reference_line_mm = (
    cx + perp_dx,
    cy + perp_dy,
    cx - perp_dx,
    cy - perp_dy
)
```

### How It Works Now

**Zemax interface:**
```python
(x1=5, y1=-10, x2=5, y2=+10)  # Vertical line
```

**New behavior:**
1. Interface: vertical (dx=0, dy=20)
2. Perpendicular: horizontal (-dy, dx) = (-20, 0) 
3. Normalized to half length: (-10, 0)
4. Reference line: (5-10, 0) to (5+10, 0) = (-5, 0, 15, 0) **horizontal** ✅
5. ComponentSprite: "Optical axis is horizontal (0°), no rotation needed"
6. Sprite aligns correctly with interface lines!

## Testing

To verify the fix:

1. **Import Zemax lens:**
   ```bash
   # In Component Editor:
   # Click "Import Zemax…"
   # Select: AC254-100-B-Zemax.zmx
   ```

2. **Add sprite image:**
   ```bash
   # In Component Editor:
   # Click "Open Image…"
   # Select: lens.png (or any lens sprite)
   ```

3. **Save to library and drop on canvas:**
   - Sprite should now align correctly with interface lines
   - Optical axis in sprite should match optical axis of interfaces

## Impact

- ✅ Zemax imported lenses now display correctly
- ✅ Sprite orientation matches interface orientation
- ✅ No impact on standard library components (they use simple items like LensItem, not RefractiveObjectItem)
- ✅ Works for any interface orientation (vertical, horizontal, diagonal)

## Related Files

- `src/optiverse/objects/refractive/refractive_object_item.py` - Fixed sprite reference line calculation
- `src/optiverse/objects/component_sprite.py` - Sprite rotation logic (unchanged)
- `src/optiverse/services/zemax_converter.py` - Creates vertical interfaces (unchanged, correct)

## Notes

The key insight is that **interface geometry** (perpendicular to beam) and **sprite reference line** (along beam direction) are **perpendicular to each other**. The old code was conflating these two concepts, causing the 90° rotation error.

