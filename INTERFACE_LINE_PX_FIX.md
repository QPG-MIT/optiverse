# Interface Line_px Fix - Sprite Positioning

## Problem
After migrating from `line_px` to optical interfaces, components were displaying incorrectly on the main canvas - showing only as "a little shape at the top" instead of properly positioned across the entire image.

## Root Cause
When the component system was migrated to use optical interfaces instead of a simple `line_px` calibration line, the `line_px` value was no longer being computed and saved. However, the `ComponentSprite` still required `line_px` to:

1. **Position the sprite** - Center the image on the reference line
2. **Calculate picked line offset** - Transform interface coordinates from image-center to picked-line-center origin

Without a valid `line_px`, the sprite positioning broke, causing all interfaces to appear in the wrong location.

## Solution
Compute `line_px` from the first interface when saving a component, so the sprite can properly position itself.

### Coordinate Transformation

The conversion from interface mm coordinates to `line_px` pixel coordinates:

**Input (Interface):**
- Coordinates in mm
- Origin at image center (0,0)
- Y-axis down (Qt standard)

**Output (line_px):**
- Coordinates in pixels (normalized 1000px space)
- Origin at top-left (0,0)
- Y-axis down

**Formula:**
```python
mm_per_px = object_height_mm / 1000.0
x_px = (x_mm / mm_per_px) + 500.0  # +500 shifts from center to top-left
y_px = (y_mm / mm_per_px) + 500.0
```

## Files Modified

### 1. `src/optiverse/core/models.py`
- **Added `line_px` field to `ComponentRecord`**
  - Optional tuple for sprite positioning
  - Computed from first interface
  - Stored in normalized 1000px space

- **Updated `serialize_component()`**
  - Serialize line_px if available
  
- **Updated `deserialize_component()`**
  - Deserialize line_px from saved data

### 2. `src/optiverse/ui/views/component_editor_dialog.py`
- **Added `_compute_line_px_from_interface()`**
  - Converts interface mm coords to line_px
  - Uses first interface as reference
  - Applies coordinate transformation

- **Updated `_build_record_from_ui()`**
  - Compute line_px from interfaces when saving
  - Include in ComponentRecord

### 3. `src/optiverse/objects/component_registry.py`
- **Added `_compute_line_px_from_interface_coords()` helper**
  - Shared utility for computing line_px
  - Used by standard component definitions

- **Updated standard components**
  - `get_standard_lens()` - includes line_px
  - `get_standard_mirror()` - includes line_px
  - `get_standard_beamsplitter()` - includes line_px
  - (Other components should follow same pattern)

## Technical Details

### Why line_px is Still Needed

Even though components now use interfaces in mm coordinates, `line_px` serves a critical purpose:

1. **Sprite Centering**
   - `ComponentSprite` needs to know which line to center on
   - The picked line defines the optical axis
   - Sprite is centered and rotated to align with this line

2. **Picked Line Offset**
   - Interfaces are stored relative to image center
   - Sprite is displayed relative to picked line center
   - `picked_line_offset_mm` transforms between these origins
   - This offset is computed from `line_px`

### The Reference Line

- **First interface** is used as the reference line
- For single-interface components (lens, mirror, BS), this is the optical axis
- For multi-interface components, the first interface defines the positioning

### Backward Compatibility

- Old components without interfaces still work (line_px only)
- New components with interfaces include both:
  - `interfaces[]` - full optical interface definitions
  - `line_px` - reference for sprite positioning
- Loading works with either format

## Testing

To verify the fix:

1. Open component editor
2. Load an image and add an interface
3. Set object height and position interface
4. Save component (line_px is computed automatically)
5. Drop component on main canvas
6. Verify:
   - Sprite centers correctly on interface
   - Interface displays at correct position
   - Interface spans full extent as drawn in editor

## Example

For a standard lens with object height 30.5mm:

**Interface coordinates (mm, centered):**
```python
x1_mm = 0.0, y1_mm = -15.25  # Top endpoint
x2_mm = 0.0, y2_mm = 15.25   # Bottom endpoint
```

**Computed line_px (normalized 1000px space):**
```python
mm_per_px = 30.5 / 1000.0 = 0.0305
x1_px = (0.0 / 0.0305) + 500.0 = 500.0
y1_px = (-15.25 / 0.0305) + 500.0 = 0.0
x2_px = (0.0 / 0.0305) + 500.0 = 500.0
y2_px = (15.25 / 0.0305) + 500.0 = 1000.0
```

Result: Vertical line from top to bottom of image, horizontally centered.

## Resolution

The interface-based system now works correctly:
- ✅ Interfaces display properly in component editor
- ✅ Components save with both interfaces and line_px
- ✅ Components display correctly on main canvas
- ✅ Sprite centers properly on reference line
- ✅ Interfaces appear at correct positions
- ✅ Backward compatibility maintained

Users can now create and use interface-based components without positioning issues.

