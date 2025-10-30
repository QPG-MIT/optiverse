# Raytracing Architecture Comparison

## Current Architecture (❌ Broken for Multi-Interface Components)

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMPONENT LIBRARY                            │
│  ComponentRecord with InterfaceDefinition list                   │
│                                                                   │
│  Example: Achromat Doublet                                       │
│  ├─ Interface 1: refractive (n1=1.0, n2=1.517, curved)          │
│  ├─ Interface 2: refractive (n1=1.517, n2=1.620, flat)          │
│  └─ Interface 3: refractive (n1=1.620, n2=1.0, curved)          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   on_drop_component()                            │
│                                                                   │
│  if len(interfaces) > 1:                                         │
│      create RefractiveObjectItem  ✅                             │
│  else:                                                           │
│      create LensItem(efl_mm=100.0)  ❌ LOSES INTERFACES!        │
└─────────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────────┐  ┌──────────────────────────┐
│   RefractiveObjectItem   │  │      LensItem            │
│                          │  │                          │
│  ✅ Has interfaces       │  │  ❌ NO interfaces        │
│  ✅ get_interfaces_scene│  │  ❌ endpoints_scene()    │
│     returns:             │  │     returns:             │
│     [(p1,p2,iface1),    │  │     (p1, p2)             │
│      (p1,p2,iface2),    │  │     ^ single line only   │
│      (p1,p2,iface3)]    │  │                          │
└─────────────────────────┘  └──────────────────────────┘
              │                           │
              └─────────────┬─────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        retrace()                                 │
│                                                                   │
│  for R in refractive_objects:                                    │
│      for p1, p2, iface in R.get_interfaces_scene():  ✅         │
│          elem = OpticalElement(...from interface...)             │
│                                                                   │
│  for L in lenses:                                                │
│      p1, p2 = L.endpoints_scene()  ❌ ONLY ONE LINE             │
│      elem = OpticalElement(kind="lens", efl_mm=...)             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    trace_rays()                                  │
│                                                                   │
│  OpticalElement list:                                            │
│  ├─ 3 elements from RefractiveObjectItem  ✅                     │
│  └─ 1 element from LensItem  ❌ (should be 3!)                  │
│                                                                   │
│  Result: Doublet NOT properly modeled as thin lens!              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Proposed Architecture (✅ Unified Interface-Based)

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMPONENT LIBRARY                            │
│  ComponentRecord with InterfaceDefinition list                   │
│                                                                   │
│  Example: Achromat Doublet                                       │
│  ├─ Interface 1: refractive (n1=1.0, n2=1.517, curved)          │
│  ├─ Interface 2: refractive (n1=1.517, n2=1.620, flat)          │
│  └─ Interface 3: refractive (n1=1.620, n2=1.0, curved)          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   on_drop_component()                            │
│                                                                   │
│  # NEW: Always preserve ALL interfaces                           │
│  first_type = interfaces[0].element_type                         │
│                                                                   │
│  if first_type == "lens":                                        │
│      params = LensParams(                                        │
│          interfaces=interfaces  ✅ PRESERVE ALL                  │
│      )                                                           │
│      create LensItem(params)  ✅ Has all 3 interfaces!          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LensItem                                    │
│                                                                   │
│  ✅ params.interfaces = [iface1, iface2, iface3]                │
│  ✅ get_interfaces_scene() returns:                             │
│      [(p1, p2, iface1),                                          │
│       (p1, p2, iface2),                                          │
│       (p1, p2, iface3)]                                          │
│                                                                   │
│  ✅ Still has lens-specific UI/editing                          │
│  ✅ First interface used for primary properties                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        retrace()                                 │
│                                                                   │
│  # NEW: Unified approach for ALL components                      │
│  for item in self.scene.items():                                 │
│      if hasattr(item, 'get_interfaces_scene'):                  │
│          for p1, p2, iface in item.get_interfaces_scene():      │
│              elem = _create_element_from_interface(iface)       │
│              elems.append(elem)  ✅                             │
│                                                                   │
│  # No more component-type-specific code paths!                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    trace_rays()                                  │
│                                                                   │
│  OpticalElement list:                                            │
│  ├─ Element from interface 1 (refractive, n1→n2)  ✅           │
│  ├─ Element from interface 2 (refractive, n2→n3)  ✅           │
│  └─ Element from interface 3 (refractive, n3→n1)  ✅           │
│                                                                   │
│  Result: Doublet properly modeled with 3 refractive surfaces!    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Side-by-Side Comparison

| Feature | Current | Proposed |
|---------|---------|----------|
| **Lenses with multiple surfaces** | ❌ Only thin lens | ✅ Full surface model |
| **Mirrors with AR coating** | ❌ Single surface | ✅ Multi-layer coating |
| **Component type determines UI** | ✅ Yes | ✅ Yes (unchanged) |
| **Raytracing complexity** | ❌ Complex (type-specific) | ✅ Simple (unified) |
| **Zemax import support** | ⚠️ As RefractiveObjectItem only | ✅ As proper type (Lens, Mirror, etc.) |
| **Interface storage** | ⚠️ Only RefractiveObjectItem | ✅ All component types |
| **Backward compatibility** | N/A | ✅ Legacy components auto-generate interface |
| **Code maintainability** | ❌ Multiple code paths | ✅ Single unified path |

---

## Example: Raytracing a Doublet

### Current Behavior (Incorrect)

```
Achromat Doublet (from library, 3 interfaces)
    │
    ├─ Dropped as LensItem (interfaces lost!)
    │   └─ params.efl_mm = 100.0  (only property kept)
    │
    ▼
Raytracing sees:
    └─ Single thin lens at z=0 with f=100mm
    
Result: ❌ Incorrect! No chromatic correction modeled.
```

### Proposed Behavior (Correct)

```
Achromat Doublet (from library, 3 interfaces)
    │
    ├─ Dropped as LensItem WITH all 3 interfaces
    │   └─ params.interfaces = [iface1, iface2, iface3]
    │   └─ params.efl_mm = 100.0  (for display)
    │
    ▼
Raytracing sees:
    ├─ Refractive surface 1: air→glass1 (curved, R=50mm)
    ├─ Refractive surface 2: glass1→glass2 (flat)
    └─ Refractive surface 3: glass2→air (curved, R=-30mm)
    
Result: ✅ Correct! Full chromatic correction modeled.
```

---

## Key Insight

**The interface architecture already exists and works!**

The problem is that it's only used for RefractiveObjectItem. We just need to:
1. Extend it to LensItem, MirrorItem, etc.
2. Update raytracing to iterate interfaces from all components

No new architecture needed - just unify what's already there!

---

## Implementation Complexity

| Task | Complexity | Time Estimate |
|------|------------|---------------|
| Add interfaces field to Params classes | 🟢 Low | 30 min |
| Add get_interfaces_scene() to all items | 🟡 Medium | 2 hours |
| Update on_drop_component() | 🟡 Medium | 1 hour |
| Refactor retrace() | 🟢 Low | 1 hour |
| Backward compatibility | 🟡 Medium | 1 hour |
| Testing | 🟡 Medium | 2 hours |
| **Total** | | **~8 hours** |

Not a massive refactor - mostly connecting existing pieces!

