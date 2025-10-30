# Raytracing Interface Fix - October 30, 2025

## Problem

After adjusting the raytracing algorithm to work with optical interfaces, there was **no interaction between sources and interfaces**. Rays were not hitting any optical components.

## Root Cause

The issue was that `LensItem`, `MirrorItem`, `BeamsplitterItem`, `WaveplateItem`, and `DichroicItem` did not properly calculate and store the `_picked_line_offset_mm` attribute that is needed for coordinate transformation.

### Why This Matters

When components are dropped from the library:
1. They come with **interfaces** defined in image-center coordinates (Y-down, mm)
2. The component sprite is **positioned using a reference line** (e.g., the optical axis)
3. The reference line's center becomes the item's local origin (0,0)
4. But interfaces are still stored relative to the **image center**, not the reference line center

Without `_picked_line_offset_mm`, the `get_interfaces_scene()` method couldn't properly transform interface coordinates from image-center to scene coordinates, resulting in interfaces being positioned incorrectly (or at degenerate coordinates).

### The Transform Chain

```
Interface Definition (stored)
  → x1_mm, y1_mm, x2_mm, y2_mm (relative to image center)
  
Transform 1: Subtract _picked_line_offset_mm
  → Convert from image-center coords to item-local coords (reference line center)
  
Transform 2: mapToScene()
  → Convert from item-local coords to scene coords (accounting for position, rotation, etc.)
  
Result: p1, p2 in scene coordinates
  → Used by raytracing algorithm
```

## The Fix

Added calculation of `_picked_line_offset_mm` to the `_maybe_attach_sprite()` method in all item types:

```python
# Calculate picked line offset for coordinate transformation
self._picked_line_offset_mm = (0.0, 0.0)  # Default: no offset

if self.params.image_path:
    # ... create sprite with reference_line_mm ...
    
    # Calculate offset from image center to reference line center
    # ComponentSprite centers the component on the reference line, but interfaces
    # are stored relative to image center. We need to account for this offset.
    # Reference line center in mm (centered coordinate system)
    cx_mm = 0.5 * (reference_line_mm[0] + reference_line_mm[2])
    cy_mm = 0.5 * (reference_line_mm[1] + reference_line_mm[3])
    
    # Store offset: interfaces are at image center, but item (0,0) is at reference line center
    self._picked_line_offset_mm = (cx_mm, cy_mm)
```

## Files Modified

1. `src/optiverse/objects/lenses/lens_item.py`
2. `src/optiverse/objects/mirrors/mirror_item.py`
3. `src/optiverse/objects/beamsplitters/beamsplitter_item.py`
4. `src/optiverse/objects/waveplates/waveplate_item.py`
5. `src/optiverse/objects/dichroics/dichroic_item.py`

Note: `RefractiveObjectItem` already had this calculation implemented correctly.

## Testing

After the fix:
- Components dropped from the library now have their interfaces positioned correctly
- Raytracing properly detects intersections with these interfaces
- Sources interact with all optical components as expected

## Related Documentation

- `INTERFACE_BASED_RAYTRACING_IMPLEMENTATION_COMPLETE.md` - Original interface-based raytracing implementation
- `src/optiverse/objects/component_sprite.py` - How sprites handle reference lines
- `src/optiverse/core/interface_definition.py` - Interface coordinate system documentation

