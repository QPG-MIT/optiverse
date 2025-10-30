# Aspect Ratio Fix - Line_px Computation

## The Bug

When computing `line_px` from interface coordinates, the code assumed a **square 1000x1000 image**. However, images are normalized to **1000px height while preserving aspect ratio**, so non-square images have different widths.

### Example of the Bug

For a 1500x1000 (width x height) image with an interface at the center:

**Old (Broken) Code:**
```python
mm_per_px = object_height_mm / 1000.0
x1_px = (x1_mm / mm_per_px) + 500.0  # WRONG! Assumes center at X=500
```

Result: `line_px = (336, 500, 664, 500)`
- Assumes image center is at X=500
- But for a 1500px wide image, center should be at X=750!
- **X-offset error: 250 pixels** - interface appears way off to the side

**New (Correct) Code:**
```python
aspect_ratio = image_width / image_height
normalized_width = 1000.0 * aspect_ratio  # 1500 for 1.5:1 aspect
center_x_px = normalized_width / 2.0      # 750 for wide image
x1_px = (x1_mm / mm_per_px) + center_x_px  # CORRECT!
```

Result: `line_px = (586, 500, 914, 500)`
- Correctly accounts for actual image aspect ratio
- Interface appears at the correct position

## Root Cause

The normalized coordinate system documentation said "normalized 1000px space" but didn't clearly specify that:
1. **Height** is always normalized to 1000px
2. **Width** scales proportionally based on aspect ratio
3. The **center offset** must account for actual width, not assume 1000px

## The Fix

### 1. Updated `_compute_line_px_from_interface()` in `component_editor_dialog.py`

```python
# Get actual canvas image dimensions
w_px, h_px = self.canvas.image_pixel_size()

# Compute actual normalized width based on aspect ratio
aspect_ratio = float(w_px) / float(h_px)
normalized_width = 1000.0 * aspect_ratio
normalized_height = 1000.0

# Use actual center offsets
center_x_px = normalized_width / 2.0  # NOT always 500!
center_y_px = normalized_height / 2.0  # Always 500 for height

x1_px = (interface.x1_mm / mm_per_px) + center_x_px
y1_px = (interface.y1_mm / mm_per_px) + center_y_px
```

### 2. Updated `_compute_line_px_from_interface_coords()` in `component_registry.py`

```python
# Load image to get actual aspect ratio
if image_path and os.path.exists(image_path):
    pix = QtGui.QPixmap(image_path)
    w_px = pix.width()
    h_px = pix.height()
    aspect_ratio = float(w_px) / float(h_px)
else:
    aspect_ratio = 1.0  # Fallback to square

# Compute normalized dimensions
normalized_width = 1000.0 * aspect_ratio
center_x_px = normalized_width / 2.0
```

### 3. Updated standard component definitions

All standard components now pass `image_path` to the helper function so it can determine the correct aspect ratio.

## Impact

### Before the Fix
- ❌ Interfaces on non-square images appeared offset
- ❌ User reported "little shape at the top" instead of full interface
- ❌ Sprite positioning was wrong
- ❌ Worse for images with extreme aspect ratios

### After the Fix
- ✅ Interfaces display at correct positions on any aspect ratio
- ✅ Sprite centers correctly on reference line
- ✅ Line_px accurately represents interface location
- ✅ Works for square, wide, and tall images

## Testing

Test with different aspect ratios:

| Aspect Ratio | Image Size | Center X | Result |
|--------------|------------|----------|---------|
| 1:1 (square) | 1000x1000 | 500 | ✅ Correct |
| 1.5:1 (wide) | 1500x1000 | 750 | ✅ Correct |
| 2:1 (very wide) | 2000x1000 | 1000 | ✅ Correct |
| 0.75:1 (tall) | 750x1000 | 375 | ✅ Correct |

## Files Modified

1. `src/optiverse/ui/views/component_editor_dialog.py`
   - `_compute_line_px_from_interface()` - now aspect-ratio aware

2. `src/optiverse/objects/component_registry.py`
   - `_compute_line_px_from_interface_coords()` - accepts image_path parameter
   - `get_standard_lens()` - passes image_path
   - `get_standard_mirror()` - passes image_path
   - `get_standard_beamsplitter()` - passes image_path

## Resolution

The interface display issue is now fixed. Components with any aspect ratio image will display correctly with interfaces at their proper positions across the full extent of the image.

