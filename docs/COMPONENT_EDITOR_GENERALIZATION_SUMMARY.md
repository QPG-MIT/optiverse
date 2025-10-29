# Component Editor Generalization - Summary

## Executive Summary

This document provides a high-level overview of the component editor generalization project. The goal is to transform the editor from a **component-type-based** system to a more flexible **interface-based** system where each interface can have its own element type and properties.

## Current vs Target

### Current System ❌

**Problems:**
- Component has single type (lens, mirror, beamsplitter, dichroic, refractive_object)
- Type-specific properties scattered across UI
- Can't mix interface types in one component
- Coordinates in pixels (not physically meaningful)
- Two different systems for simple vs complex components

**Example:** Can't create a component with both a lens and a beam splitter interface

### Target System ✅

**Benefits:**
- Component is a container of interfaces
- Each interface has its own type and properties
- Mix any interface types in one component
- Coordinates in millimeters (physically meaningful)
- Unified system for all components
- Collapsible UI for clarity

**Example:** Create a component with lens + BS + dichroic interfaces, all in one

## Architecture Changes

### Data Model

**Before:**
```python
ComponentRecord:
  kind: str  # 'lens' | 'mirror' | 'beamsplitter' | ...
  efl_mm: float  # Only for lenses
  split_TR: tuple  # Only for beamsplitters
  interfaces: list  # Only for refractive_objects
```

**After:**
```python
ComponentRecord:
  name: str
  object_height_mm: float
  interfaces: List[InterfaceDefinition]

InterfaceDefinition:
  element_type: str  # 'lens' | 'mirror' | 'beam_splitter' | ...
  x1_mm, y1_mm, x2_mm, y2_mm: float  # Geometry in mm
  # Type-specific properties
  efl_mm: float  # Lens
  split_T, split_R: float  # Beam splitter
  n1, n2: float  # Refractive interface
  # etc.
```

### UI Layout

**Before:**
```
┌─────────────────────────┐
│ Type: [Lens ▼]          │
│ Object Height: [ ]      │
│ Interfaces (list)       │
│ ─── Properties ───      │
│ EFL: [ ]                │
│ Split T: [ ]            │
│ Cutoff: [ ]             │
│ (all properties shown)  │
└─────────────────────────┘
```

**After:**
```
┌─────────────────────────┐
│ Name: [ ]               │
│ Object Height: [ ]      │
│                         │
│ Interfaces              │
│ ▼ Interface 1: Lens     │
│   Type: [Lens ▼]        │
│   x₁,y₁: [ ] [ ]        │
│   x₂,y₂: [ ] [ ]        │
│   ─ Lens Properties ─   │
│   EFL: [ ]              │
│                         │
│ ▶ Interface 2: BS       │
│                         │
│ [Add Interface ▼]       │
└─────────────────────────┘
```

## Key Features

### 1. Interface-Based Design
- Each interface is self-contained
- Properties specific to each interface
- Visual color coding

### 2. Collapsible UI
- Expand only what you need
- Reduces visual clutter
- Better for many interfaces

### 3. Physical Units
- Coordinates in millimeters
- Physically meaningful
- Easier to understand

### 4. Flexible Composition
- Mix any interface types
- No artificial constraints
- Real-world modeling

### 5. Backward Compatible
- Automatic migration
- Old components still work
- No data loss

## Implementation Phases

### Phase 1: Data Model (2 days)
- Create `InterfaceDefinition` class
- Create interface type registry
- Update `ComponentRecord`
- Implement migration utilities
- Write unit tests

### Phase 2: UI Widgets (3 days)
- Create `CollapsibleInterfaceWidget`
- Create `InterfacePropertiesPanel`
- Implement property field factory
- Test widget interactions

### Phase 3: Integration (2 days)
- Update `ComponentEditor` layout
- Remove old type-specific UI
- Update canvas synchronization
- Implement coordinate conversion

### Phase 4: Testing & Polish (1 day)
- Comprehensive testing
- Backward compatibility validation
- UI refinements
- Documentation

**Total: ~1-2 weeks**

## Technical Highlights

### Coordinate System
- **Storage:** Millimeters (local coordinate system)
- **Display:** Millimeters + pixels (for reference)
- **Canvas:** Pixels (for rendering)
- **Conversion:** `mm_per_px = object_height_mm / calibration_line_length_px`

### Type Registry
```python
INTERFACE_TYPES = {
    'lens': {
        'color': (0, 180, 180),  # Cyan
        'properties': ['efl_mm'],
    },
    'beam_splitter': {
        'color': (0, 150, 120),  # Green
        'properties': ['split_T', 'split_R', 'is_polarizing'],
    },
    # ...
}
```

### Migration Strategy
1. Detect legacy format
2. Convert to new format automatically
3. Preserve all information
4. Test round-trip

### Canvas Synchronization
```
User drags endpoint on canvas
    ↓
Convert pixels → mm
    ↓
Update InterfaceDefinition
    ↓
Update UI spinboxes
    ↓
(bidirectional)
```

## Files to Create

### Core
- `src/optiverse/core/interface_definition.py`
- `src/optiverse/core/interface_types.py`
- `src/optiverse/core/component_migration.py`

### UI
- `src/optiverse/ui/widgets/collapsible_interface_widget.py`
- `src/optiverse/ui/widgets/interface_properties_panel.py`

### Tests
- `tests/core/test_interface_definition.py`
- `tests/core/test_component_migration.py`
- `tests/ui/test_collapsible_interface_widget.py`

### Modified
- `src/optiverse/core/models.py`
- `src/optiverse/ui/views/component_editor_dialog.py`

## Example Use Cases

### Use Case 1: Simple Lens
```python
component = ComponentRecord(
    name="Lens 1-inch f=100mm",
    object_height_mm=25.4,
    interfaces=[
        InterfaceDefinition(
            element_type="lens",
            x1_mm=-12.7, y1_mm=0.0,
            x2_mm=12.7, y2_mm=0.0,
            efl_mm=100.0,
        )
    ]
)
```

### Use Case 2: PBS Cube
```python
component = ComponentRecord(
    name="PBS Cube 1-inch",
    object_height_mm=25.4,
    interfaces=[
        # 4 refractive interfaces (cube faces)
        InterfaceDefinition(element_type="refractive_interface", ...),
        InterfaceDefinition(element_type="refractive_interface", ...),
        InterfaceDefinition(element_type="refractive_interface", ...),
        InterfaceDefinition(element_type="refractive_interface", ...),
        # 1 PBS interface (diagonal coating)
        InterfaceDefinition(
            element_type="beam_splitter",
            is_polarizing=True,
            split_T=50.0,
            split_R=50.0,
            ...
        ),
    ]
)
```

### Use Case 3: Custom Multi-Element
```python
component = ComponentRecord(
    name="Lens + Dichroic + Mirror",
    object_height_mm=50.0,
    interfaces=[
        InterfaceDefinition(element_type="lens", efl_mm=100.0, ...),
        InterfaceDefinition(element_type="dichroic", cutoff_wavelength_nm=550.0, ...),
        InterfaceDefinition(element_type="mirror", ...),
    ]
)
```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing components | Comprehensive migration + testing |
| UI too complex | Progressive disclosure, good defaults |
| Performance with many interfaces | Virtual scrolling, lazy loading |
| Coordinate conversion bugs | Extensive unit tests |

## Success Criteria

✅ All existing components load correctly  
✅ Can create components with mixed interface types  
✅ Coordinates displayed in mm  
✅ No visual regressions  
✅ Performance acceptable (<100ms for 50 interfaces)  
✅ User feedback positive  

## Related Documents

📄 **Full Strategy** → `docs/COMPONENT_EDITOR_GENERALIZATION_STRATEGY.md`  
📄 **UI Mockups** → `docs/COMPONENT_EDITOR_UI_MOCKUP.md`  
📄 **Implementation Guide** → `docs/COMPONENT_EDITOR_IMPLEMENTATION_GUIDE.md`  
📄 **Current System** → `docs/UNIFIED_INTERFACE_SYSTEM.md`  

## Questions?

**Q: Will old components still work?**  
A: Yes! Automatic migration preserves all data.

**Q: Can I mix interface types?**  
A: Yes! That's the whole point. Lens + BS + dichroic in one component.

**Q: Do I need to recreate my library?**  
A: No. Migration is automatic on load.

**Q: What about performance?**  
A: Designed to handle 50+ interfaces efficiently.

**Q: How do coordinates work?**  
A: Stored in mm (physically meaningful), displayed in mm + px for reference.

## Next Steps

1. **Review** these documents with the team
2. **Prototype** `CollapsibleInterfaceWidget` to validate UX
3. **Implement** `InterfaceDefinition` data model
4. **Test** migration on existing library
5. **Integrate** into component editor
6. **Test** thoroughly
7. **Deploy** to production

## Timeline

```
Week 1: Data model + migration + tests
Week 2: UI widgets + integration + polish
Week 3: Beta testing + bug fixes
Week 4: Production release
```

## Contact

For questions or clarifications, please refer to the detailed strategy documents or reach out to the development team.

---

**Status**: 📝 Strategy Complete, Implementation Ready  
**Last Updated**: 2025-10-29  
**Version**: 1.0

