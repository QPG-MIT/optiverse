# Save/Load Assembly - Relative Path Implementation

## Summary

The save/load assembly functionality has been updated to use **relative paths for package images** and **absolute paths for external images**. This makes saved assembly files portable across different installations while still supporting custom user images.

## Changes Made

### 1. New Path Utility Module (`src/optiverse/platform/paths.py`)

Added new utility functions for handling image paths:

- **`to_relative_path(image_path)`**: Converts absolute paths to relative if within the package
- **`to_absolute_path(image_path)`**: Converts relative paths back to absolute  
- **`is_package_image(image_path)`**: Checks if an image is within the package
- **`get_package_root()`**: Returns the package root directory
- **`get_package_images_dir()`**: Returns the package images directory

### 2. Updated Serialization (`src/optiverse/core/models.py`)

- **`serialize_component()`**: Now converts image paths to relative before saving
- **`deserialize_component()`**: Now converts relative paths back to absolute when loading

### 3. Updated All Item Classes

Modified `to_dict()` and `from_dict()` methods in all optical component classes:

- ✅ `LensItem` (`src/optiverse/objects/lenses/lens_item.py`)
- ✅ `MirrorItem` (`src/optiverse/objects/mirrors/mirror_item.py`)
- ✅ `BeamsplitterItem` (`src/optiverse/objects/beamsplitters/beamsplitter_item.py`)
- ✅ `WaveplateItem` (`src/optiverse/objects/waveplates/waveplate_item.py`)
- ✅ `DichroicItem` (`src/optiverse/objects/dichroics/dichroic_item.py`)
- ✅ `SLMItem` (`src/optiverse/objects/misc/slm_item.py`)
- ✅ `RefractiveObjectItem` (`src/optiverse/objects/refractive/refractive_object_item.py`)

Each class now:
- **Saves**: Converts image_path to relative if within package
- **Loads**: Converts relative paths back to absolute

## How It Works

### Saving

When saving an assembly:

1. **Package images** (e.g., `C:\...\optiverse\objects\images\lens.png`):
   - Converted to relative: `objects/images/lens.png`
   - Portable across installations

2. **External images** (e.g., `C:\Users\john\my_custom_lens.png`):
   - Kept as absolute: `C:/Users/john/my_custom_lens.png`
   - Still works on the same machine

### Loading

When loading an assembly:

1. **Relative paths** (e.g., `objects/images/lens.png`):
   - Converted to absolute: `C:\...\optiverse\objects\images\lens.png`
   - Resolved relative to package root

2. **Absolute paths** (e.g., `C:/Users/john/my_custom_lens.png`):
   - Used as-is
   - External images still work

## Example

### Before (All Absolute Paths)

```json
{
  "lenses": [
    {
      "name": "Standard Lens",
      "image_path": "C:/Users/alice/optiverse/src/optiverse/objects/images/lens_1_inch_mounted.png",
      "x_mm": 100.0
    }
  ]
}
```

❌ **Problem**: Won't work on Bob's computer (different path)

### After (Relative Paths for Package Images)

```json
{
  "lenses": [
    {
      "name": "Standard Lens",
      "image_path": "objects/images/lens_1_inch_mounted.png",
      "x_mm": 100.0
    }
  ]
}
```

✅ **Solution**: Works on any computer with Optiverse installed!

## SLM Component Verification

✅ **Confirmed**: SLM (Spatial Light Modulator) components are properly saved and loaded:

- Saved in the `"slms"` key in the JSON file
- `SLMItem` handled in both `save_assembly()` and `open_assembly()`
- Image paths follow the same relative/absolute path logic as other components

## Backward Compatibility

✅ The implementation is **fully backward compatible**:

- Old assembly files with absolute paths still load correctly
- `to_absolute_path()` handles both relative and absolute paths gracefully
- No breaking changes to existing files

## Testing

Run the test script to verify functionality:

```bash
python test_relative_path_save.py
```

Expected output:
- ✅ Package image paths converted to relative
- ✅ External image paths stay absolute
- ✅ Round-trip save/load preserves all paths correctly

## Benefits

1. **Portability**: Assembly files work across different installations
2. **Version Control**: Relative paths work better with git
3. **Sharing**: Users can share assembly files without path issues
4. **Flexibility**: External images still supported for custom components
5. **Cross-Platform**: Uses forward slashes (/) for maximum compatibility

## Files Modified

```
src/optiverse/platform/paths.py              (NEW - path utilities)
src/optiverse/core/models.py                 (updated serialization)
src/optiverse/objects/lenses/lens_item.py
src/optiverse/objects/mirrors/mirror_item.py
src/optiverse/objects/beamsplitters/beamsplitter_item.py
src/optiverse/objects/waveplates/waveplate_item.py
src/optiverse/objects/dichroics/dichroic_item.py
src/optiverse/objects/misc/slm_item.py
src/optiverse/objects/refractive/refractive_object_item.py
```

## Notes

- All paths use **forward slashes** (`/`) in saved files for cross-platform compatibility
- Windows backslashes (`\`) are converted to forward slashes when saving
- The package images directory: `src/optiverse/objects/images/`
- Image paths in component library files also benefit from this change

