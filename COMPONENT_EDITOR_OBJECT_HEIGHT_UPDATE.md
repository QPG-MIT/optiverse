# Component Editor: Object Height UI Update ✅

## Summary

Updated Component Editor UI to use **"Object height"** instead of **"Image height"**, aligning with the component registry convention.

## What Changed

### Before (Confusing Workflow)
1. User enters "Image height" (full image height in mm)
2. System calculates `mm_per_pixel = image_height / image_height_px`
3. User clicks two points
4. System calculates `object_height = line_length_px * mm_per_pixel`

### After (Intuitive Workflow) ✅
1. User enters **"Object height"** (physical element size in mm) - **what they actually know!**
2. User clicks two points on the element
3. System calculates `mm_per_pixel = object_height / line_length_px`
4. System displays computed image height for reference

## UI Changes

**Component Settings Panel:**

```
Before:
┌─────────────────────────┐
│ Name: [          ]      │
│ Type: [lens ▼]          │
│ Image height: [50.0] mm │  ← Confusing!
│ mm per pixel: 0.05 mm/px│
│ Element length: 1000 px │
└─────────────────────────┘

After:
┌─────────────────────────────────────────┐
│ Name: [          ]                      │
│ Type: [lens ▼]                          │
│ Object height: [30.5] mm  ⓘ            │ ← Clear! Physical size
│ Line length: 800.00 px                  │
│ → mm/px: 0.038125 mm/px                 │ ← Computed
│ → Image height: 38.13 mm (norm 1000px)  │ ← Computed
└─────────────────────────────────────────┘
```

## Benefits

✅ **Intuitive**: User enters physical size they know (e.g., "25.4mm for 1-inch optic")  
✅ **Consistent**: Matches `object_height` in component registry  
✅ **Informative**: Shows computed values (mm/px, image height)  
✅ **Tooltip**: "Physical height of the optical element (e.g., 25.4mm for 1-inch optic)"

## Example Usage

**Creating a 1-inch lens:**

1. Load image of lens
2. Enter object height: `25.4 mm` (1 inch)
3. Click top and bottom of lens element
4. System shows:
   - Line length: `800 px`
   - mm/px: `0.03175 mm/px`
   - Image height: `31.75 mm` (normalized to 1000px)
5. Save → object_height stored as `25.4`

## Code Changes

**Field renamed:**
```python
# Before:
self.height_mm = QtWidgets.QDoubleSpinBox()  # Image height
self.height_mm.setValue(50.0)

# After:
self.object_height_mm = QtWidgets.QDoubleSpinBox()  # Object height
self.object_height_mm.setValue(30.0)  # Default: ~1 inch
self.object_height_mm.setToolTip("Physical height of the optical element")
```

**Logic simplified:**
```python
# Before: Compute object_height from image height
def _get_object_height(self) -> float:
    px_len = distance(p1, p2)
    return px_len * (image_height / image_height_px)

# After: Direct access
def _get_object_height(self) -> float:
    return float(self.object_height_mm.value())
```

**Display updated:**
```python
# Before: Show element length in px and mm
self.line_len_lbl.setText(f"{px_len:.2f} px / {mm_len:.3f} mm")

# After: Show computed values separately
mm_per_px = object_height / px_len
image_height = mm_per_px * 1000.0
self.line_len_lbl.setText(f"{px_len:.2f} px")
self.mm_per_px_lbl.setText(f"{mm_per_px:.6g} mm/px")
self.image_height_lbl.setText(f"{image_height:.2f} mm (normalized to 1000px)")
```

## Loading Components

When loading from library:
```python
# Before: Compute image height from mm_per_pixel
self.height_mm.setValue(rec.mm_per_pixel * image_height_px)

# After: Set object height directly
self.object_height_mm.setValue(rec.object_height)
```

## Files Modified

- `src/optiverse/ui/views/component_editor_dialog.py`

## Testing Status

- ✅ No linter errors
- ✅ Consistent with component registry
- ✅ Intuitive user workflow
- ✅ Proper tooltips and help text

---

**Result:** Component Editor now uses "Object height" consistently with the registry! 🎯

