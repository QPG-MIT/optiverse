# Scaling Fix - Complete Solution

## Problems Fixed

### Issue 1: Incorrect Image Scaling
Objects in the scene were rendering at incorrect sizes. For example:
- Microscope objective (40mm) was rendering at ~50mm (25% too large)
- Standard lens (30.5mm) was rendering at ~36.6mm (20% too large)
- Standard mirror (49.4mm) was rendering at ~88mm (78% too large)

### Issue 2: Incorrect Line Length
After fixing the image scaling, the optical axis lines drawn on components were still too large:
- Microscope objective: Line was 40mm (should be 32mm - 25% too large)
- Standard lens: Line was 30.5mm (should be 25.4mm - 20% too large)
- Standard mirror: Line was 49.4mm (should be 27.7mm - 78% too large)

## Root Cause
The bug was in `ComponentSprite` class (`src/optiverse/objects/component_sprite.py`). The scaling calculation was **incorrectly based on the picked line length** instead of the full image height.

### Original (Incorrect) Logic:
```python
picked_line_length = math.hypot(dx, dy)
mm_per_pixel = object_height_mm / picked_line_length  # ❌ WRONG!
```

This meant that if the picked line was only 80% of the image height, the entire image would render 25% too large.

### The Purpose of the Picked Line
The picked line should **ONLY** define the optical axis:
1. **Position**: Line midpoint → component origin
2. **Angle**: Line angle → optical axis orientation

The picked line should **NOT** affect the scale!

## Solutions

### Fix 1: Image Scaling (Component Sprite)
Changed the scaling to be based on the **full image height**:

```python
# Scale image so that the FULL IMAGE HEIGHT is exactly object_height_mm
# The picked line is ONLY used for optical axis (position and angle), NOT for scaling
mm_per_pixel = object_height_mm / actual_height  # ✅ CORRECT!
```

### Fix 2: Line Length (All Item Classes)
The optical axis lines should match the actual picked line length on the image, not the full image height.

Changed from:
```python
self._actual_length_mm = self.params.object_height_mm  # ❌ Full image height
```

To:
```python
self._actual_length_mm = self._sprite.picked_line_length_mm  # ✅ Actual line length
```

## Changes Made

### File: `src/optiverse/objects/component_sprite.py`

**Line 32-33**: Store picked line length for parent to use
```python
# Store the actual picked line length in mm (for parent to use)
self.picked_line_length_mm = 0.0
```

**Line 69-71**: Calculate and store the picked line length
```python
# Calculate the actual length of the picked line in mm
picked_line_length_px = math.hypot(dx, dy)
self.picked_line_length_mm = picked_line_length_px * mm_per_pixel
```

**Line 60-67**: Fixed the scaling calculation
```python
# OLD (incorrect):
picked_line_length = math.hypot(dx, dy)
mm_per_pixel = object_height_mm / picked_line_length

# NEW (correct):
mm_per_pixel = object_height_mm / actual_height
```

**Docstring**: Updated to clarify the system
```python
"""
NORMALIZED 1000px SYSTEM:
- Images are normalized to 1000px height coordinate space
- line_px coordinates are in normalized 1000px space
- object_height_mm represents the physical size of the FULL IMAGE HEIGHT
- mm_per_pixel is computed as: object_height_mm / actual_image_height
- The picked line defines the OPTICAL AXIS only (position and orientation)
- Picked line's midpoint is aligned to the parent's local origin
- Pre-rotated so picked line lies on +X in local coords
"""
```

### All Item Classes

Updated to use the actual picked line length instead of full image height:
- `src/optiverse/objects/lenses/lens_item.py` (line 66)
- `src/optiverse/objects/mirrors/mirror_item.py` (line 66)  
- `src/optiverse/objects/beamsplitters/beamsplitter_item.py` (line 66)
- `src/optiverse/objects/waveplates/waveplate_item.py` (line 70)
- `src/optiverse/objects/dichroics/dichroic_item.py` (line 69)

```python
# OLD (incorrect):
self._actual_length_mm = self.params.object_height_mm

# NEW (correct):
self._actual_length_mm = self._sprite.picked_line_length_mm
```

## Verification

### Image Scaling
All components now render at **exactly** their specified sizes (0% error):

| Component | Specified | Actual | Error |
|-----------|-----------|--------|-------|
| Standard Lens 1" | 30.5 mm | 30.50 mm | 0% ✅ |
| Standard Mirror 1" | 49.4 mm | 49.40 mm | 0% ✅ |
| Beamsplitter 50/50 | 25.4 mm | 25.40 mm | 0% ✅ |
| PBS 2" | 50.8 mm | 50.80 mm | 0% ✅ |
| Microscope Objective | 40.0 mm | 40.00 mm | 0% ✅ |

### Line Length
Optical axis lines now render at their actual picked lengths:

| Component | Image Height | Line Length | Ratio |
|-----------|--------------|-------------|-------|
| Standard Lens 1" | 30.5 mm | 25.41 mm | 83% ✅ |
| Standard Mirror 1" | 49.4 mm | 27.66 mm | 56% ✅ |
| Beamsplitter 50/50 | 25.4 mm | 35.92 mm | 141% ✅* |
| PBS 2" | 50.8 mm | 71.84 mm | 141% ✅* |
| Microscope Objective | 40.0 mm | 32.00 mm | 80% ✅ |

*Diagonal lines on square images are √2 ≈ 1.414 times the side length

## How It Works Now

1. **Image Loading**: Load component image with actual dimensions (e.g., 795x380 px)
2. **Line Denormalization**: Convert `line_px` from 1000px normalized space to actual pixels
3. **Scaling**: Calculate `mm_per_pixel = object_height_mm / actual_image_height`
4. **Alignment**: Position image so line midpoint aligns with parent origin
5. **Rotation**: Rotate image so picked line points along +X axis
6. **Apply Scale**: Scale entire image by `mm_per_pixel`

Result:
- **Image**: Full height renders at exactly `object_height_mm` millimeters
- **Optical axis line**: Renders at the actual picked line length from the image
- **Alignment**: Line midpoint aligns with component origin
- **Orientation**: Line angle defines the optical axis direction

## Key Insight
The `object_height_mm` parameter represents the **physical height of the entire component image**, not the picked line length. The picked line is a **reference line for optical axis only**, similar to how you might mark the optical axis on a drawing - it doesn't change the scale of the drawing.

## Benefits
- ✅ All components render at exact specified sizes
- ✅ Optical axis lines accurately represent the marked line on the image
- ✅ Lines are not artificially stretched or compressed
- ✅ Picked line can be placed anywhere on the image (doesn't affect image scale)
- ✅ Intuitive: `object_height_mm` = actual physical height of the component image
- ✅ Flexible: Line can be short or long as needed to clearly define optical axis
- ✅ Separate control: Image size and line length are independently correct

