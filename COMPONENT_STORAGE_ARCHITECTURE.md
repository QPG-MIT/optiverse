# Component Storage Architecture

## Current System (Recommended)

### Two-Tier Storage

#### Tier 1: Python Registry (Templates)
- **File**: `src/optiverse/objects/component_registry.py`
- **Purpose**: Default component templates shipped with app
- **Used for**: First-run initialization, restoring defaults
- **Version controlled**: Yes, part of codebase

#### Tier 2: JSON Library (Runtime Database)
- **File**: `%LOCALAPPDATA%\Optiverse\library\components_library.json`
- **Purpose**: User's actual component library
- **Contains**: Standard components + user custom components
- **User editable**: Yes, can manually edit JSON

### Flow Diagram

```
App First Run:
  Python Registry (component_registry.py)
    ↓ [copy templates]
  JSON Library (components_library.json)
    ↓ [load at runtime]
  Component Library UI

User Creates Component:
  Component Editor
    ↓ [save_component()]
  JSON Library (append)
    ↓ [reload]
  Component Library UI

Subsequent Runs:
  JSON Library (components_library.json)
    ↓ [load directly]
  Component Library UI
```

## Storage Locations

### Standard Components (Python)
```python
# src/optiverse/objects/component_registry.py
class ComponentRegistry:
    @staticmethod
    def get_standard_lens():
        return {
            "name": "Standard Lens (1\" mounted)",
            "kind": "lens",
            "efl_mm": 100.0,
            "length_mm": 25.4,
            "angle_deg": 90.0,
            "image_path": _get_image_path("lens_1_inch_mounted.png"),
            "mm_per_pixel": 0.1,
            "line_px": (100, 150, 300, 150),
        }
```

### User Library (JSON)
```
Windows: C:\Users\<user>\AppData\Local\Optiverse\library\components_library.json
macOS:   ~/Library/Application Support/Optiverse/library/components_library.json
Linux:   ~/.local/share/Optiverse/library/components_library.json
```

### Library Format
```json
[
  {
    "name": "Standard Lens (1\" mounted)",
    "kind": "lens",
    "efl_mm": 100.0,
    "length_mm": 25.4,
    "angle_deg": 90.0,
    "image_path": "/path/to/lens_1_inch_mounted.png",
    "mm_per_pixel": 0.1,
    "line_px": [100, 150, 300, 150],
    "notes": ""
  },
  {
    "name": "My Custom 200mm Lens",
    "kind": "lens",
    "efl_mm": 200.0,
    "length_mm": 50.0,
    "angle_deg": 90.0,
    "image_path": "/path/to/my-custom-lens.png",
    "mm_per_pixel": 0.15,
    "line_px": [80, 120, 320, 120],
    "notes": "Custom telephoto lens"
  }
]
```

### Asset Storage
```
Windows: C:\Users\<user>\AppData\Local\Optiverse\library\assets\
macOS:   ~/Library/Application Support/Optiverse/library/assets/
Linux:   ~/.local/share/Optiverse/library/assets/
```

Images saved as: `my-custom-lens-20251027-143022.png`

## Code Flow

### Initialization (First Run)

```python
# storage_service.py
def load_library() -> List[Dict[str, Any]]:
    if not os.path.exists(library_path):
        return self._initialize_library()
    # ...

def _initialize_library() -> List[Dict[str, Any]]:
    from ..objects.component_registry import ComponentRegistry
    standard = ComponentRegistry.get_standard_components()
    self.save_library(standard)  # Write to JSON
    return standard
```

### Creating Custom Component

```python
# component_editor_dialog.py
def save_component(self):
    rec = self._build_record_from_ui()  # ComponentRecord
    
    allrows = self.storage.load_library()  # Load JSON
    
    # Replace or append
    for i, row in enumerate(allrows):
        if row.get("name") == rec.name:
            allrows[i] = serialize_component(rec)
            break
    else:
        allrows.append(serialize_component(rec))
    
    self.storage.save_library(allrows)  # Save JSON
```

### Loading Library (Runtime)

```python
# main_window.py
def populate_library(self):
    self.libraryTree.clear()
    
    # Ensure standard components present
    self.storage_service.ensure_standard_components()
    
    # Load all components from JSON
    records = self.storage_service.load_library()
    
    # Organize and display
    # ...
```

## Advantages of Current System

### 1. Separation of Concerns
- **Code**: Templates/defaults
- **Data**: User instances

### 2. Version Control
- Standard components tracked in git
- User customizations in their own files

### 3. Upgradability
- App updates can add new standard components
- User's custom components preserved
- `ensure_standard_components()` adds missing standards

### 4. Type Safety
- Python code has type hints
- IDE autocomplete for standard components
- Compile-time checks

### 5. User Freedom
- Can edit JSON directly if needed
- Can back up/share component libraries
- Can reset to defaults

## Alternative Architectures

### Option 1: Pure JSON (Bundled Defaults)

```
src/optiverse/data/
  └── default_components.json  (bundled with app)

%APPDATA%/Optiverse/library/
  └── components_library.json  (user's copy)
```

**Pros**: Single format
**Cons**: No type safety, bundle management

### Option 2: Database (SQLite)

```
%APPDATA%/Optiverse/
  └── library.db
    ├── components table
    ├── assets table
    └── metadata table
```

**Pros**: Better querying, referential integrity
**Cons**: Overkill for current needs, harder to edit manually

### Option 3: Hybrid (Python + Bundled JSON)

```
Python Registry → default_components.json → user library.json
```

**Pros**: Best of both worlds
**Cons**: More complex initialization

## Recommended Enhancements

### 1. Add "Reset to Defaults" Feature

```python
# storage_service.py
def reset_to_defaults(self):
    """Replace library with fresh standard components."""
    from ..objects.component_registry import ComponentRegistry
    standard = ComponentRegistry.get_standard_components()
    self.save_library(standard)
```

Add to UI:
- Tools → Reset Library to Defaults
- With confirmation dialog
- Option to backup current library first

### 2. Add "Export/Import Library" Feature

```python
def export_library(self, path: str):
    """Export library to external file."""
    shutil.copy(self._lib_path, path)

def import_library(self, path: str, merge: bool = False):
    """Import library from external file."""
    if merge:
        existing = self.load_library()
        imported = json.load(open(path))
        # Merge logic
    else:
        shutil.copy(path, self._lib_path)
```

### 3. Add Library Validation

```python
def validate_library(self) -> List[str]:
    """Check library for issues."""
    issues = []
    records = self.load_library()
    
    for rec in records:
        # Check required fields
        if not rec.get("name"):
            issues.append("Component missing name")
        
        # Check image exists
        img = rec.get("image_path")
        if img and not os.path.exists(img):
            issues.append(f"Missing image: {img}")
    
    return issues
```

### 4. Add Component Templates

Allow users to mark components as "templates" vs "instances":

```json
{
  "name": "My Custom Lens",
  "is_template": true,  // Show in library
  "is_instance": false  // Not on canvas
}
```

## Best Practices

### For Developers

1. **Add new standard components** in `component_registry.py`
2. **Version the registry** when changing defaults
3. **Test initialization** after modifying registry
4. **Document component fields** in ComponentRecord

### For Users

1. **Edit JSON carefully** - syntax errors break library
2. **Backup library** before major edits
3. **Use Component Editor** when possible
4. **Check paths** are absolute, not relative

### For Both

1. **Keep images in assets folder** for portability
2. **Use descriptive names** for components
3. **Document custom components** in notes field
4. **Share component JSONs** for collaboration

## Migration Path

If you want to move to pure JSON in future:

1. Export current registry to JSON:
```python
ComponentRegistry.get_standard_components()
# → save to src/optiverse/data/defaults.json
```

2. Bundle JSON with app (in package_data)

3. Update initialization to copy bundled JSON

4. Deprecate Python registry gradually

This preserves all functionality while moving to JSON-first approach.

## Conclusion

**Current architecture is solid** because:
- ✅ Standard components are code (version controlled)
- ✅ User library is JSON (editable, portable)
- ✅ Clear separation of templates vs instances
- ✅ Easy to extend in either layer

**Keep it** unless you have specific needs for pure JSON approach.

