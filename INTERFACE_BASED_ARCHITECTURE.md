# Interface-Based Component Architecture

## Overview

The component system has been refactored to be **interface-driven** rather than **kind-driven**. This allows for better handling of complex multi-interface components (like Zemax imports) and prepares the codebase for deprecating the `kind` field.

## Key Changes

### Before (Kind-Based)
```python
kind = rec.get("kind", "lens")
if kind == "lens":
    create LensItem
elif kind == "beamsplitter":
    create BeamsplitterItem
elif kind == "refractive_object" or kind == "multi_element":
    create RefractiveObjectItem  # This was missing!
```

**Problem:** When Zemax files were imported with multiple interfaces, `ComponentRecord._compute_kind()` returned `"multi_element"`, but `on_drop_component()` didn't check for this, so it fell through to the default `MirrorItem` case, showing only 1 line instead of all interfaces.

### After (Interface-Based)
```python
# 1. Check for interfaces first
interfaces_data = rec.get("interfaces", [])
has_interfaces = interfaces_data and len(interfaces_data) > 0

# 2. Multiple interfaces? Create RefractiveObjectItem
if has_interfaces and len(interfaces_data) > 1:
    create RefractiveObjectItem with all interfaces

# 3. Single interface? Check element_type or fall back to kind
elif rec.get("kind") == "lens" or (has_interfaces and interfaces_data[0].get("element_type") == "lens"):
    create LensItem
```

**Benefits:**
- ✅ Works with any number of interfaces
- ✅ Doesn't depend on `kind` being correct
- ✅ Allows gradual deprecation of `kind` field
- ✅ More data-driven and robust

## Component Drop Logic Flow

```
on_drop_component(rec)
    │
    ├─ Extract interfaces_data = rec.get("interfaces", [])
    │
    ├─ has_interfaces = len(interfaces_data) > 0
    │
    ├─ Multiple interfaces (len > 1)?
    │  └─ YES → RefractiveObjectItem (all interfaces rendered)
    │
    ├─ Single interface with element_type="lens"?
    │  └─ YES → LensItem
    │
    ├─ Single interface with element_type="beam_splitter"?
    │  └─ YES → BeamsplitterItem
    │
    ├─ ... (other single-interface types)
    │
    └─ Fallback → MirrorItem (legacy)
```

## Migration Path for Deprecating `kind`

### Phase 1: ✅ COMPLETE (Current State)
- Interface-first logic in `on_drop_component()`
- `kind` used as fallback only
- All Zemax imports work correctly

### Phase 2: Future
- Update all component creation to include interfaces
- Ensure all saved components have `interfaces` field populated
- `kind` becomes optional

### Phase 3: Future
- Remove all `kind` references
- Pure interface-based system
- `element_type` determines component behavior

## Testing

### Multi-Interface Components (Zemax)
1. Import Zemax file → 3 interfaces loaded
2. Save component → interfaces saved correctly
3. Drag to canvas → All 3 interfaces visible ✅

### Single-Interface Components (Legacy)
1. Drop lens from library → LensItem created
2. Drop beamsplitter → BeamsplitterItem created
3. Works with or without interfaces field ✅

## Files Modified

1. **src/optiverse/ui/views/main_window.py**
   - `on_drop_component()`: Interface-first logic
   - Angle defaults based on `element_type` or `kind`

2. **src/optiverse/ui/views/component_editor_dialog.py**
   - `_build_record_from_ui()`: Allow saving without image if interfaces exist
   - Debug output for interface count

3. **src/optiverse/objects/component_registry.py**
   - Added `"multi_element"` and `"refractive_object"` to category mapping

## Data Format

### ComponentRecord (JSON)
```json
{
  "name": "AC254-100-B Achromat",
  "object_height_mm": 12.7,
  "kind": "multi_element",  // Auto-computed, soon deprecated
  "interfaces": [
    {
      "element_type": "refractive_interface",
      "x1_mm": 0.0, "y1_mm": -6.35,
      "x2_mm": 0.0, "y2_mm": 6.35,
      "n1": 1.0, "n2": 1.651,
      "name": "S1: Air → N-LAK22"
    },
    {
      "element_type": "refractive_interface",
      "x1_mm": 4.0, "y1_mm": -6.35,
      "x2_mm": 4.0, "y2_mm": 6.35,
      "n1": 1.651, "n2": 1.805,
      "name": "S2: N-LAK22 → N-SF6HT"
    },
    {
      "element_type": "refractive_interface",
      "x1_mm": 5.5, "y1_mm": -6.35,
      "x2_mm": 5.5, "y2_mm": 6.35,
      "n1": 1.805, "n2": 1.0,
      "name": "S3: N-SF6HT → Air"
    }
  ]
}
```

### How It's Used
```python
# Check for interfaces first
if rec.get("interfaces") and len(rec["interfaces"]) > 1:
    # Multi-interface component
    for iface in rec["interfaces"]:
        element_type = iface["element_type"]  # Not rec["kind"]!
        # Create interface based on element_type
```

## Benefits of This Approach

1. **Zemax Support**: Multi-interface components from Zemax work immediately
2. **Future-Proof**: Easy to deprecate `kind` field
3. **Data-Driven**: Behavior determined by actual data, not metadata
4. **Backward Compatible**: Legacy components with `kind` still work
5. **Extensible**: Easy to add new interface types without touching `kind` logic

## Questions?

This architecture allows us to gradually migrate away from `kind` while maintaining full backward compatibility. When ready, we can simply remove the `kind` fallbacks and rely entirely on `interfaces` and `element_type`.

