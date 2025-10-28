# Dichroic Component Editor Integration

## Summary
Added dichroic mirror support to the component editor UI, completing the integration that was already present in the main application.

## Changes Made

### 1. Component Type Selection
**File:** `src/optiverse/ui/views/component_editor_dialog.py`

Added "dichroic" to the component type dropdown:
- Line 182: Added "dichroic" to kind_combo items: `["lens", "mirror", "beamsplitter", "dichroic"]`

### 2. Dichroic-Specific UI Fields
Added three new fields for dichroic mirror parameters:

#### Cutoff Wavelength (lines 234-238)
- Range: 200-2000 nm
- Default: 550 nm
- Controls the wavelength at which the dichroic mirror transitions between reflection and transmission

#### Transition Width (lines 241-245)
- Range: 1-200 nm  
- Default: 50 nm
- Controls the width of the transition region between reflection and transmission

#### Pass Type (lines 248-249)
- Options: "longpass" or "shortpass"
- Default: "longpass"
- Determines whether the dichroic reflects short wavelengths (longpass) or long wavelengths (shortpass)

### 3. Form Layout
**Lines 282-284:** Added dichroic fields to the properties section:
```python
f.addRow("Cutoff λ (dichroic)", self.cutoff_wavelength)
f.addRow("Trans. Width (dichroic)", self.transition_width)
f.addRow("Pass Type (dichroic)", self.pass_type)
```

### 4. Show/Hide Logic
**Lines 308-318:** Updated `_on_kind_changed` method to show/hide dichroic fields:
```python
def _on_kind_changed(self, kind: str):
    """Show/hide type-specific fields."""
    is_lens = (kind == "lens")
    is_bs = (kind == "beamsplitter")
    is_dichroic = (kind == "dichroic")
    self.efl_mm.setVisible(is_lens)
    self.split_T.setVisible(is_bs)
    self.split_R.setVisible(is_bs)
    self.cutoff_wavelength.setVisible(is_dichroic)
    self.transition_width.setVisible(is_dichroic)
    self.pass_type.setVisible(is_dichroic)
```

### 5. Save Component Logic
**Lines 626-628, 638-640:** Updated `_build_record_from_ui` to include dichroic parameters:
```python
cutoff_wavelength = float(self.cutoff_wavelength.value()) if kind == "dichroic" else 550.0
transition_width = float(self.transition_width.value()) if kind == "dichroic" else 50.0
pass_type_value = self.pass_type.currentText() if kind == "dichroic" else "longpass"
```

Added to ComponentRecord constructor:
```python
cutoff_wavelength_nm=cutoff_wavelength,
transition_width_nm=transition_width,
pass_type=pass_type_value,
```

### 6. Load Component Logic
**Lines 773, 783-788:** Updated `_load_from_dict` to load dichroic parameters:
```python
self.kind_combo.setCurrentText(
    rec.kind if rec.kind in ("lens", "mirror", "beamsplitter", "dichroic") else "lens"
)

self.cutoff_wavelength.setValue(rec.cutoff_wavelength_nm if rec.kind == "dichroic" else 550.0)
self.transition_width.setValue(rec.transition_width_nm if rec.kind == "dichroic" else 50.0)
if rec.kind == "dichroic":
    idx = self.pass_type.findText(rec.pass_type)
    if idx >= 0:
        self.pass_type.setCurrentIndex(idx)
```

### 7. New Component Reset
**Lines 450-452:** Updated `_new_component` to reset dichroic fields:
```python
self.cutoff_wavelength.setValue(550.0)
self.transition_width.setValue(50.0)
self.pass_type.setCurrentIndex(0)  # longpass
```

## Existing Infrastructure
The following components were already in place and did not require changes:

1. **DichroicParams model** (`src/optiverse/core/models.py`): Defines dichroic mirror parameters
2. **DichroicItem** (`src/optiverse/objects/dichroics/dichroic_item.py`): Graphics item for dichroic mirrors
3. **ComponentRecord serialization** (`src/optiverse/core/models.py`): Already handles dichroic parameters
4. **Main window integration** (`src/optiverse/ui/views/main_window.py`): Already supports dropping/creating dichroic items
5. **Component registry** (`src/optiverse/objects/component_registry.py`): Already includes standard dichroic components

## Testing
Users can now:
1. Open the Component Editor
2. Select "dichroic" from the Type dropdown
3. Configure cutoff wavelength, transition width, and pass type
4. Load an image and calibrate the component
5. Save the dichroic component to the library
6. Drag and drop the dichroic component onto the canvas

## Notes
- All dichroic parameters use the same normalized 1000px coordinate system as other components
- Default values match the standard dichroic mirror definition in the component registry (550nm cutoff, 50nm transition width, longpass)
- The UI properly shows/hides dichroic-specific fields based on the selected component type

