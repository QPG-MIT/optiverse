# Quick Reference: Save/Load with Relative Paths

## What Changed?

Image paths in saved assembly files now use **relative paths** for package images instead of absolute paths.

## Visual Comparison

### Before ❌
```json
{
  "lenses": [{
    "name": "1 inch Mounted Lens",
    "image_path": "C:/Users/cohasset/Desktop/repos/optiverse/src/optiverse/objects/images/lens_1_inch_mounted.png",
    "x_mm": 100.0
  }]
}
```
Problem: Won't work on another computer!

### After ✅
```json
{
  "lenses": [{
    "name": "1 inch Mounted Lens", 
    "image_path": "objects/images/lens_1_inch_mounted.png",
    "x_mm": 100.0
  }]
}
```
Solution: Works on any installation!

## Package Images (Now Relative)
- `lens_1_inch_mounted.png`
- `lens_2_inch_100mm_mounted.png`
- `pbs_2_inch.png`
- `beamsplitter_50_50_1_inch.png`
- `objective.png`
- `standard_mirror_1_inch.png`
- `slm.png`

All stored in: `objects/images/`

## External Images (Stay Absolute)
If you use custom images from outside the package:
- `C:/Users/yourname/Pictures/my_lens.png` → Stays absolute
- Works on your computer, needs manual path adjustment on others

## SLM Components ✅

Confirmed working:
- SLMs are saved in the `"slms"` section
- Image paths follow the same relative/absolute logic
- Example: `"image_path": "objects/images/slm.png"`

## Key Functions

```python
# In src/optiverse/platform/paths.py

to_relative_path(image_path)
# Package image: "/full/path/to/optiverse/objects/images/lens.png"
# Returns: "objects/images/lens.png"
# External image: "/home/user/my_image.png"  
# Returns: "/home/user/my_image.png" (unchanged)

to_absolute_path(image_path)
# Relative: "objects/images/lens.png"
# Returns: "/full/path/to/optiverse/objects/images/lens.png"
# Absolute: "/home/user/my_image.png"
# Returns: "/home/user/my_image.png" (unchanged)
```

## Testing Your Changes

1. Open Optiverse
2. Place some components with package images
3. Save assembly (File → Save Assembly)
4. Open the JSON file - you'll see relative paths!
5. Load assembly (File → Open Assembly) - works perfectly!

## Backward Compatibility

Old assembly files with absolute paths? **Still work!** The code automatically handles both formats.

## Documentation

- Full details: `docs/SAVE_LOAD_RELATIVE_PATHS.md`
- Summary: `IMPLEMENTATION_SUMMARY.md`

