# Zemax Lens Interface Fix

## Problem

Zemax lenses imported from the library were NOT interacting with raytracing because `on_drop_component()` was not preserving interfaces when creating scene items.

**Symptom**: Import Zemax doublet → Drop on scene → Rays don't interact with it

**Root Cause**: The `on_drop_component()` method was:
1. Creating RefractiveObjectItem for components with >1 interface (losing lens-specific UI)
2. NOT passing interfaces to LensParams/MirrorParams/etc. constructors
3. Interfaces were lost when single-type components were created

---

## Solution

### Changes to `on_drop_component()`

**1. Smart Routing Logic**

**OLD**:
```python
if len(interfaces_data) > 1:
    # Force RefractiveObjectItem
    item = RefractiveObjectItem(params)
elif element_type == "lens":
    # Create LensItem WITHOUT interfaces
    params = LensParams(efl_mm=..., ...)  # ❌ No interfaces!
```

**NEW**:
```python
# Convert all interfaces first
interfaces = [InterfaceDefinition.from_dict(iface_data) for iface_data in interfaces_data]

# Smart routing based on interface types
all_same_type = all(iface.element_type == element_type for iface in interfaces)
all_refractive = all(iface.element_type == "refractive_interface" for iface in interfaces)

if all_refractive or (len(interfaces) > 1 and not all_same_type):
    # Mixed types or all refractive → RefractiveObjectItem
    item = RefractiveObjectItem(params)
elif element_type == "lens":
    # All lens type → LensItem WITH interfaces
    params = LensParams(..., interfaces=interfaces)  # ✅ Preserves ALL!
```

**2. Preserve Interfaces in ALL Params**

Every component type now receives `interfaces=interfaces` in its Params constructor:

```python
params = LensParams(
    x_mm=scene_pos.x(),
    y_mm=scene_pos.y(),
    angle_deg=angle_deg,
    efl_mm=efl_mm,
    object_height_mm=object_height_mm,
    image_path=img,
    name=name,
    interfaces=interfaces,  # ✅ PRESERVE ALL INTERFACES!
)
```

Applied to:
- ✅ LensParams
- ✅ MirrorParams
- ✅ BeamsplitterParams
- ✅ DichroicParams
- ✅ WaveplateParams

---

## How It Works Now

### Case 1: Zemax Doublet (All Refractive Interfaces)

```python
# Zemax file has 3 refractive_interface entries
interfaces = [
    InterfaceDefinition(element_type="refractive_interface", n1=1.0, n2=1.517),
    InterfaceDefinition(element_type="refractive_interface", n1=1.517, n2=1.620),
    InterfaceDefinition(element_type="refractive_interface", n1=1.620, n2=1.0),
]

# Drop on scene:
# → all_refractive = True
# → Creates RefractiveObjectItem with all 3 interfaces
# → Raytracing iterates through all 3 → ✅ Works!
```

### Case 2: Simplified Lens Model (All Lens Interfaces)

```python
# Component with multiple lens interfaces
interfaces = [
    InterfaceDefinition(element_type="lens", efl_mm=100.0),
    InterfaceDefinition(element_type="lens", efl_mm=-50.0),
]

# Drop on scene:
# → all_same_type = True (all "lens")
# → Creates LensItem with both interfaces
# → Raytracing iterates through both → ✅ Works!
```

### Case 3: Single Interface (Legacy or Simple)

```python
# Simple lens
interfaces = [
    InterfaceDefinition(element_type="lens", efl_mm=100.0),
]

# Drop on scene:
# → Creates LensItem with 1 interface
# → Raytracing uses that interface → ✅ Works!
```

### Case 4: AR-Coated Mirror (Mixed Types)

```python
# Mirror with AR coating
interfaces = [
    InterfaceDefinition(element_type="refractive_interface", n1=1.0, n2=1.38),  # AR
    InterfaceDefinition(element_type="mirror"),
]

# Drop on scene:
# → not all_same_type (mixed)
# → Creates RefractiveObjectItem with both interfaces
# → Raytracing handles AR + mirror → ✅ Works!
```

---

## What Was Fixed

### Before

```
Zemax Doublet → Library (3 interfaces) ✅
    ↓
Drop on scene → LensItem created ❌
    ↓
LensParams(efl_mm=100.0, interfaces=[]) ❌ Empty!
    ↓
get_interfaces_scene() → Returns 1 default interface ❌
    ↓
Raytracing → Single thin lens ❌ WRONG!
```

### After

```
Zemax Doublet → Library (3 interfaces) ✅
    ↓
Drop on scene → RefractiveObjectItem created ✅
    ↓
RefractiveObjectParams(interfaces=[iface1, iface2, iface3]) ✅
    ↓
get_interfaces_scene() → Returns 3 actual interfaces ✅
    ↓
Raytracing → 3 refractive surfaces ✅ CORRECT!
```

---

## Testing

### Verify Fix Works

1. **Import Zemax lens** (e.g., AC254-100-B doublet)
2. **Drop on scene** from component library
3. **Add source** and enable raytracing
4. **Verify**: Rays should refract through ALL surfaces

### Check Interface Count

```python
# In Python console or debug:
lens = scene.items()[0]  # Your dropped lens
interfaces = lens.get_interfaces_scene()
print(f"Number of interfaces: {len(interfaces)}")
# Should print 3 (or actual count) not 1!
```

---

## Files Modified

- `src/optiverse/ui/views/main_window.py::on_drop_component()`
  - Smart routing logic based on interface types
  - Pass `interfaces=interfaces` to all Params constructors

---

## Status

✅ **FIXED** - Zemax lenses now properly interact with raytracing!

All optical interfaces are preserved when dropping components from library, and raytracing iterates through them correctly.

