# Library Path Portability - Implementation Summary

## Problem Solved

**Issue**: Assembly files contained absolute paths to component images (e.g., `/Users/benny/Documents/Optiverse/...`), making them non-portable between different computers.

**Solution**: Implemented library-relative path system with configurable library directories via preferences dialog.

## What Was Implemented

### 1. Library-Relative Path Format

Component image paths now use a special format when within a configured library:

**Format**: `@library/{library_name}/{component_folder}/images/{filename}`

**Example**: 
```
@library/user_library/achromat_doublet/images/lens.png
```

**Benefits**:
- Portable across different computers
- Self-documenting (clearly indicates library reference)
- Works with multiple library directories
- Backward compatible with old absolute paths

### 2. Preferences Dialog

**Location**: Edit → Preferences...

**Features**:
- General-purpose settings dialog organized by categories
- Library settings tab for managing component library paths
- Add/Remove library directories
- Preview component count in each library
- Open library in file manager
- Default user library always included
- Easy to extend with new settings categories

**File**: `src/optiverse/ui/views/settings_dialog.py`

### 3. Enhanced Path Utilities

**File**: `src/optiverse/platform/paths.py`

**New Functions**:
- `get_all_library_roots(settings_service)` - Get all configured library directories
- `resolve_library_relative_path(rel_path, library_roots)` - Resolve `@library/...` to absolute path
- `make_library_relative(abs_path, library_roots)` - Convert absolute to library-relative format
- `to_absolute_path()` - Enhanced to support library-relative paths

### 4. Updated Serialization System

**File**: `src/optiverse/core/models.py`

**Changes**:
- `serialize_component(rec, settings_service)` - Now accepts settings_service parameter
  - Tries library-relative format first (portable)
  - Falls back to package-relative (built-in components)
  - Falls back to absolute (outside all libraries)

- `deserialize_component(data, settings_service)` - Now accepts settings_service parameter
  - Resolves `@library/...` paths using configured libraries
  - Handles package-relative paths (built-in components)
  - Backward compatible with old absolute paths

### 5. Updated Services

**StorageService** (`src/optiverse/services/storage_service.py`):
- Now accepts `settings_service` parameter in constructor
- Uses configured library paths for loading/saving
- New method: `get_all_library_roots()` returns all configured libraries

**SettingsService** (`src/optiverse/services/settings_service.py`):
- Stores library paths as list in QSettings
- Key: `"library_paths"` (JSON array)
- Default user library always included implicitly

### 6. Integration Points

**MainWindow** (`src/optiverse/ui/views/main_window.py`):
- Initialize `SettingsService` before `StorageService`
- Pass `settings_service` to `StorageService` constructor
- Added "Preferences..." menu item under Edit menu
- `open_preferences()` method opens settings dialog
- `_on_settings_changed()` reloads library when settings change

**ComponentEditor** (`src/optiverse/ui/views/component_editor_dialog.py`):
- Updated all `serialize_component()` calls to pass `self.storage.settings_service`
- Updated all `deserialize_component()` calls to pass `self.storage.settings_service`

## Usage Examples

### For Users

**Adding a Custom Library**:
1. Edit → Preferences...
2. Click "Add..." button
3. Select directory containing component folders
4. Components from this library now available in main window
5. Save assemblies - component paths will be library-relative

**Sharing Assemblies**:
1. Create assembly with components from your library
2. Save assembly (paths are now `@library/...`)
3. Share assembly JSON + component library folder
4. Recipient adds library folder in Preferences
5. Assembly loads correctly on recipient's computer!

### For Developers

**Creating Components Programmatically**:
```python
from optiverse.core.models import ComponentRecord, serialize_component
from optiverse.services.settings_service import SettingsService

settings = SettingsService()
rec = ComponentRecord(
    name="My Component",
    image_path="/path/to/library/my_component/images/img.png",
    object_height_mm=25.4
)

# Serialize with library-relative path
data = serialize_component(rec, settings)
# Result: data["image_path"] = "@library/user_library/my_component/images/img.png"
```

**Loading Components**:
```python
from optiverse.core.models import deserialize_component
from optiverse.services.settings_service import SettingsService

settings = SettingsService()
data = {
    "name": "My Component",
    "image_path": "@library/user_library/my_component/images/img.png",
    "object_height_mm": 25.4
}

rec = deserialize_component(data, settings)
# Result: rec.image_path is absolute path to image on this computer
```

## Path Resolution Priority

When serializing component images:
1. **Library-relative** if within any configured library → `@library/...`
2. **Package-relative** if within package → `objects/...`
3. **Absolute** as fallback → `/full/path/...`

When deserializing component images:
1. **Library-relative** (`@library/...`) → resolve against configured libraries
2. **Package-relative** (no `/`) → resolve against package root
3. **Absolute** → use as-is (backward compatibility)

## Backward Compatibility

- Old assemblies with absolute paths still work
- Deserialization tries library resolution but falls back to absolute
- No migration script needed
- Gradual migration: components re-saved will use new format

## Multi-Library Support

Users can configure multiple library directories:
- Default: `~/Documents/Optiverse/ComponentLibraries/user_library/`
- Custom: Any directory with component folders
- All libraries scanned and combined in UI
- Components can reference images from any configured library

## Settings Storage

**QSettings Keys**:
- `library_paths`: JSON array of additional library directories
- Example: `["~/Projects/lab_optics", "/shared/vendor_catalog"]`

**Default Library**:
- Always included: `~/Documents/Optiverse/ComponentLibraries/user_library/`
- Cannot be removed from list
- Created automatically if doesn't exist

## Testing

**Manual Test**:
1. Create a component in component editor
2. Save assembly with that component
3. Check assembly JSON - image path should be `@library/...`
4. Copy assembly to different computer
5. Configure same library in Preferences
6. Open assembly - component should load with image

**Cross-Platform Test**:
- Windows: `C:\Users\...\Documents\Optiverse\ComponentLibraries\...`
- macOS: `~/Documents/Optiverse/ComponentLibraries/...`
- Linux: `~/Documents/Optiverse/ComponentLibraries/...`
- Same relative structure works on all platforms

## Future Enhancements

Possible additions to Preferences dialog:
- **Appearance** category: Theme, colors, font size
- **Performance** category: Numba settings, thread count, OpenGL options
- **Raytracing** category: Max events, parallel threshold
- **Collaboration** category: Default server, username
- **Keyboard** category: Custom shortcuts

The dialog architecture supports easy addition of new categories.

## Files Modified

1. `src/optiverse/ui/views/settings_dialog.py` (NEW)
2. `src/optiverse/platform/paths.py`
3. `src/optiverse/core/models.py`
4. `src/optiverse/services/storage_service.py`
5. `src/optiverse/ui/views/main_window.py`
6. `src/optiverse/ui/views/component_editor_dialog.py`
7. `src/optiverse/objects/definitions_loader.py`
8. `.github/copilot-instructions.md`

## Key Design Decisions

1. **`@library/` prefix**: Clear, self-documenting, easy to parse
2. **Settings-based**: User-configurable, persistent across sessions
3. **Backward compatible**: Old absolute paths still work
4. **Multi-library**: Support project-specific or shared libraries
5. **General preferences**: Easy to extend with new settings
6. **QSettings storage**: Cross-platform, standard Qt approach
