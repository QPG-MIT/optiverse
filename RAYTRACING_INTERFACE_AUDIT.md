# Raytracing Interface Audit - Summary

## ❌ Current Status: Raytracing Does NOT Properly Use Interfaces

### The Problem

Your raytracing algorithm **does NOT interact with the optical interface architecture** for most component types. Here's what I found:

### What Works (✅)

1. **RefractiveObjectItem** - ONLY this component type properly exposes multiple interfaces
   - Has `get_interfaces_scene()` method
   - Raytracing iterates through all its interfaces
   - Example: Beam splitter cubes, prisms from Zemax

### What Doesn't Work (❌)

2. **All other components** (LensItem, MirrorItem, BeamsplitterItem, DichroicItem, WaveplateItem):
   - ❌ Do NOT store interfaces in scene items
   - ❌ Do NOT expose `get_interfaces_scene()` 
   - ❌ Only expose single line segment via `endpoints_scene()`
   - ❌ Raytracing only sees ONE interface per component

### Concrete Example of the Problem

```python
# In Component Library (ComponentRecord):
# Zemax achromatic doublet with 4 interfaces:
{
    "name": "Achromat 100mm",
    "interfaces": [
        {"element_type": "refractive_interface", "n1": 1.0, "n2": 1.517, ...},  # Front surface
        {"element_type": "refractive_interface", "n1": 1.517, "n2": 1.620, ...}, # Cement
        {"element_type": "refractive_interface", "n1": 1.620, "n2": 1.0, ...},   # Back surface
    ]
}

# When dropped on scene:
# If single interface → becomes LensItem with ONLY efl_mm
# All interface data is LOST!

# Raytracing sees:
elems.append(OpticalElement(kind="lens", p1=p1, p2=p2, efl_mm=100.0))
# ❌ Only ONE thin lens, not 3 refractive surfaces!
```

---

## Root Cause Analysis

### The Data Flow

```
ComponentRecord (library)
    └─ interfaces: [InterfaceDefinition, InterfaceDefinition, ...]  ✅ Has interfaces
           │
           ▼
    on_drop_component()
           │
           ├─ Multiple interfaces? → RefractiveObjectItem  ✅ Preserves interfaces
           │                              └─ get_interfaces_scene()  ✅ Exposes all
           │
           └─ Single interface? → LensItem/MirrorItem/etc.  ❌ LOSES interface data
                                      └─ endpoints_scene()  ❌ Only one line!
           
           ▼
    retrace()
           │
           ├─ For RefractiveObjectItem: interfaces_scene = R.get_interfaces_scene()  ✅ Multiple
           │
           └─ For others: p1, p2 = L.endpoints_scene()  ❌ Single line only
           
           ▼
    trace_rays()
           └─ OpticalElement list (one per interface, but simple components only have 1!)
```

### Why This Happened

The interface architecture was added later (for Zemax import), but:
1. Simple component types (LensItem, MirrorItem, etc.) were NOT updated to store/expose interfaces
2. Only RefractiveObjectItem was designed as interface-based from the start
3. The logic assumes "multiple interfaces → RefractiveObjectItem, single interface → simple type"
4. This breaks when you want a lens with 2 surfaces, or any multi-interface simple component

---

## Impact

### What You CANNOT Do Currently

1. ❌ Lens with 2 curved refractive surfaces (only thin lens approximation)
2. ❌ Mirror with AR coating + reflective coating (only single mirror surface)
3. ❌ Beamsplitter with entrance/exit glass surfaces + coating (only thin coating)
4. ❌ Dichroic with glass substrate (only thin dichroic coating)
5. ❌ Import Zemax lenses as proper LensItem (forced to use RefractiveObjectItem)

### What You CAN Do (Workaround)

- Use RefractiveObjectItem for everything with multiple interfaces
- But then you lose specialized UI/editing for lenses, mirrors, etc.

---

## Recommended Solution

See `INTERFACE_BASED_RAYTRACING_STRATEGY.md` for detailed refactor plan.

**High-level approach**:

1. **Add interface storage to all component types**
   - LensParams, MirrorParams, etc. get `interfaces: List[InterfaceDefinition]` field
   - All items get `get_interfaces_scene()` method

2. **Update component loading**
   - Always preserve all interfaces, regardless of count
   - Choose item type based on first interface, but store ALL interfaces

3. **Refactor raytracing**
   - Single loop: iterate through ALL items that have `get_interfaces_scene()`
   - Create OpticalElement for each interface
   - Delete component-type-specific code paths

4. **Backward compatibility**
   - Legacy components auto-generate single interface from current params
   - No changes to file format (interfaces already supported)

---

## Verification Questions

To confirm this diagnosis, check:

1. ✅ Does RefractiveObjectItem work with multiple interfaces? **YES**
2. ❌ Do LensItem/MirrorItem expose multiple interfaces? **NO**
3. ❌ Can you import Zemax doublet as LensItem with 2 surfaces? **NO**
4. ❌ Does raytracing iterate all interfaces from all components? **NO** (only RefractiveObjectItem)

---

## Next Steps

1. Review the strategy document: `INTERFACE_BASED_RAYTRACING_STRATEGY.md`
2. Decide on implementation approach
3. Start with Phase 1 (add interface storage to simple components)
4. Test with Zemax imported components
5. Move to Phase 2 (refactor raytracing)

Let me know if you want me to start implementing the refactor!

