# Optical Axis Storage - Complete Implementation ✅

## Summary

The optical axis angle (`angle_deg`) for components is now **fully saved and loaded** from the component library.

---

## Where is `angle_deg` Stored?

### 1. Component Library File (JSON)
**Location:** User's app data directory (via `get_library_path()`)

**Format:**
```json
{
  "name": "Standard Lens (1\" mounted)",
  "kind": "lens",
  "efl_mm": 100.0,
  "length_mm": 25.4,
  "angle_deg": 90.0,  ← OPTICAL AXIS SAVED HERE
  "image_path": "/path/to/lens_1_inch_mounted.png",
  "mm_per_pixel": 0.1,
  "line_px": [100, 150, 300, 150]
}
```

### 2. ComponentRecord (Data Structure)
**File:** `src/optiverse/core/models.py`

```python
@dataclass
class ComponentRecord:
    name: str
    kind: str
    image_path: str
    mm_per_pixel: float
    line_px: Tuple[float, float, float, float]
    length_mm: float
    efl_mm: float = 0.0
    split_TR: Tuple[float, float] = (50.0, 50.0)
    angle_deg: float = 0.0  ← NEW FIELD ADDED
    notes: str = ""
```

### 3. Standard Components (Defaults)
**File:** `src/optiverse/objects/component_registry.py`

Standard components now include default angles:
- **Lens**: `angle_deg: 90.0` (vertical)
- **Mirror**: `angle_deg: 0.0` (horizontal)
- **Beamsplitter**: `angle_deg: 45.0` (diagonal)

---

## How It Works

### When Saving Components

**Component Editor → Library**

1. User creates/edits component in Component Editor
2. `ComponentRecord` is created with all parameters
3. `serialize_component()` converts to JSON dict **including angle_deg**
4. Saved to library file via `StorageService.save_library()`

**Code Flow:**
```
ComponentEditor._build_record_from_ui()
  → ComponentRecord(angle_deg=...)
  → serialize_component(rec)
  → {"angle_deg": 90.0, ...}
  → storage.save_library(rows)
  → library.json updated
```

### When Loading Components

**Library → Canvas**

1. User drags component from library to canvas
2. `on_drop_component()` reads component dict
3. Extracts `angle_deg` from dict (or uses smart defaults)
4. Creates component params with optical axis angle
5. Component placed on canvas with saved orientation

**Code Flow:**
```
LibraryTree.startDrag()
  → MainWindow.on_drop_component(rec, pos)
  → angle_deg = rec.get("angle_deg", default)
  → LensParams(angle_deg=angle_deg)
  → LensItem(params)
  → Component rendered with correct angle
```

---

## Files Modified

### Core Model Changes
✅ **`src/optiverse/core/models.py`**
- Added `angle_deg: float = 0.0` to `ComponentRecord`
- Updated `serialize_component()` to save `angle_deg`
- Updated `deserialize_component()` to load `angle_deg`

### Standard Components
✅ **`src/optiverse/objects/component_registry.py`**
- Added `"angle_deg": 90.0` to standard lens
- Added `"angle_deg": 0.0` to standard mirror
- Added `"angle_deg": 45.0` to standard beamsplitter

### Drop Handler
✅ **`src/optiverse/ui/views/main_window.py`**
- Changed `on_drop_component()` to read `angle_deg` from library
- No more hardcoded angles!
- Smart fallback for legacy components without angle_deg

---

## Default Angles

When a component is dropped from the library:

| Component | Default Angle | Meaning |
|-----------|---------------|---------|
| **Lens** | 90° | Vertical (↑) |
| **Mirror** | 0° | Horizontal (→) |
| **Beamsplitter** | 45° | Diagonal (↗) |
| **Source** | 0° | Horizontal (→) |

These defaults apply when:
- Component is newly created
- Old library component without `angle_deg` field
- Standard component from registry

---

## Backward Compatibility

### Old Library Files (No `angle_deg`)
✅ **Handled Gracefully**
- `deserialize_component()` provides default: `0.0`
- `on_drop_component()` provides smart defaults:
  - Lens → 90°
  - Beamsplitter → 45°
  - Mirror → 0°

### New Library Files (With `angle_deg`)
✅ **Fully Supported**
- Angle is read and applied
- Custom angles are preserved
- Components place with saved orientation

---

## How to Set Custom Angles

### Method 1: Component Editor
1. Open Component Editor (Tools → Component Editor)
2. Create or load component
3. Note: Component Editor doesn't currently have angle field
   - *Future enhancement: Add angle field to editor*
4. Manually edit library JSON for now

### Method 2: Manual JSON Edit
1. Find library file: `Tools → Reload Library` shows path
2. Edit JSON:
```json
{
  "name": "My Custom Lens",
  "kind": "lens",
  "angle_deg": 45.0,  ← Set custom angle here
  ...
}
```
3. Reload library in app

### Method 3: On Canvas (After Placement)
1. Drag component from library
2. Right-click → Edit
3. Change "Optical Axis Angle"
4. Note: This changes instance, not library template

---

## Storage Locations

### Component Library JSON
```
Windows: C:\Users\<user>\AppData\Local\optiverse\library.json
macOS:   ~/Library/Application Support/optiverse/library.json
Linux:   ~/.local/share/optiverse/library.json
```

### Example Library Entry
```json
[
  {
    "name": "Standard Lens (1\" mounted)",
    "kind": "lens",
    "image_path": "/path/to/objects/images/lens_1_inch_mounted.png",
    "mm_per_pixel": 0.1,
    "line_px": [100, 150, 300, 150],
    "length_mm": 25.4,
    "angle_deg": 90.0,
    "efl_mm": 100.0,
    "notes": ""
  }
]
```

---

## Testing

To verify optical axis is saved:

1. **Check Standard Components:**
   - Open app
   - Drag "Standard Lens" to canvas
   - Should appear vertical (90°)
   - Right-click → Edit → Check "Optical Axis Angle" = 90°

2. **Check Persistence:**
   - Drag lens to canvas, rotate it
   - Right-click → Edit → Set angle to 45°
   - Delete it
   - Drag same component again
   - Should still use original library angle (90°), not modified (45°)

3. **Check Library File:**
   - Tools → Reload Library (shows path)
   - Open library.json
   - Verify `"angle_deg": 90.0` exists in component entries

---

## Future Enhancements

### 1. Component Editor Integration
Add angle field to Component Editor UI:
```python
angle = QtWidgets.QDoubleSpinBox()
angle.setRange(-180, 180)
angle.setSuffix(" °")
angle.setValue(0.0)
f.addRow("Default Optical Axis", angle)
```

### 2. Copy Angle from Canvas
Button to copy angle from selected canvas item to library:
```python
# Get angle from selected item on canvas
selected_angle = item.rotation()
# Apply to library component
component["angle_deg"] = selected_angle
```

### 3. Angle Presets
Quick preset buttons in Component Editor:
- Horizontal (0°)
- Vertical (90°)
- Diagonal (45°)
- Custom

---

## Summary

✅ **Problem Solved:** Optical axis angle is now saved in library  
✅ **Storage:** ComponentRecord → JSON → library.json  
✅ **Loading:** JSON → on_drop_component → LensParams  
✅ **Defaults:** Smart defaults for all component types  
✅ **Backward Compatible:** Old libraries still work  
✅ **Standard Components:** Include proper default angles  

**The optical axis angle is now a first-class property of library components!**

