# Component Editor Generalization Strategy

## Overview

This document outlines the strategy to generalize the component editor from a **component-type-based** design to an **interface-based** design, where each interface can have its own element type and properties.

## Current State Analysis

### Current Architecture

**Component-centric design:**
- Component has a single `category` (lens, mirror, beamsplitter, dichroic, refractive_object)
- Simple components: 1 calibration line with type-specific properties
- Refractive objects: Multiple interfaces with refraction/BS properties
- Type-specific UI fields shown/hidden based on component category

**Current Data Model:**
```python
ComponentRecord:
  - category: str  # Component type
  - line_px: Tuple[float, float, float, float]  # For simple components
  - interfaces: List[Dict]  # For refractive objects
  - efl_mm: float  # Lens-specific
  - split_TR: Tuple[float, float]  # BS-specific
  - cutoff_wavelength_nm: float  # Dichroic-specific
  - etc.
```

**Interface storage (refractive objects):**
```python
{
  'x1_px': float, 'y1_px': float, 'x2_px': float, 'y2_px': float,
  'n1': float, 'n2': float,
  'is_beam_splitter': bool,
  'split_T': float, 'split_R': float,
  'is_polarizing': bool,
  'pbs_transmission_axis_deg': float
}
```

## Target State Design

### Interface-centric Architecture

**Unified interface-based design:**
- Component is simply a container with a name and interfaces
- Each interface has its own element type
- Each interface has type-specific properties
- All interfaces displayed with collapsible property editors

### Target UI Layout

```
┌─────────────────────────────────────┐
│ Component Settings                  │
├─────────────────────────────────────┤
│ Name: [My Component          ]      │
│ Object Height: [25.4] mm            │
│                                     │
│ Interfaces                          │
│ ┌─────────────────────────────┐    │
│ │ ▼ Interface 1               │    │
│ │   Element Type: [Lens ▼]    │    │
│ │   x₁: [0.0] mm  y₁: [0.0] mm│    │
│ │   x₂: [10.0] mm y₂: [0.0] mm│    │
│ │   ─── Lens Properties ───    │    │
│ │   EFL: [100.0] mm           │    │
│ └─────────────────────────────┘    │
│ ┌─────────────────────────────┐    │
│ │ ▶ Interface 2               │    │
│ └─────────────────────────────┘    │
│                                     │
│ [Add] [Edit] [Delete]              │
│                                     │
│ ─────────────────────────────      │
│ Library                             │
│ ┌─────────────────────────────┐    │
│ │ [icon] Lens 1"              │    │
│ │ [icon] Mirror 2"            │    │
│ └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

### Target Data Model

**Unified ComponentRecord:**
```python
@dataclass
class ComponentRecord:
    name: str
    object_height_mm: float
    interfaces: List[InterfaceDefinition]
    notes: str = ""
    
@dataclass
class InterfaceDefinition:
    # Geometry (in mm, local coordinate system)
    x1_mm: float
    y1_mm: float
    x2_mm: float
    y2_mm: float
    
    # Element type
    element_type: str  # 'lens' | 'mirror' | 'beam_splitter' | 'dichroic' | 'refractive_interface'
    
    # Common properties
    name: str = ""
    
    # Lens properties
    efl_mm: float = 0.0
    
    # Mirror properties (no additional properties needed)
    
    # Beam splitter properties
    split_T: float = 50.0
    split_R: float = 50.0
    is_polarizing: bool = False
    pbs_transmission_axis_deg: float = 0.0
    
    # Dichroic properties
    cutoff_wavelength_nm: float = 550.0
    transition_width_nm: float = 50.0
    pass_type: str = "longpass"  # "longpass" | "shortpass"
    
    # Refractive interface properties
    n1: float = 1.0
    n2: float = 1.5
```

## Implementation Strategy

### Phase 1: Data Model Refactoring

**Step 1.1: Create new InterfaceDefinition class**
- Location: `src/optiverse/core/models.py`
- Define complete interface data structure
- Include all element types and their properties
- Add serialization/deserialization methods

**Step 1.2: Update ComponentRecord**
- Deprecate `kind` field (or make it auto-computed from interfaces)
- Deprecate type-specific top-level fields (efl_mm, split_TR, etc.)
- Make `interfaces` the primary data container
- Ensure backward compatibility for loading old components

**Step 1.3: Implement migration utilities**
```python
def migrate_legacy_component(old_record: ComponentRecord) -> ComponentRecord:
    """Convert old component format to new interface-based format."""
    # Convert simple components to single-interface format
    # Convert refractive objects to new interface schema
```

### Phase 2: UI Components

**Step 2.1: Create CollapsibleInterfaceWidget**
- Location: `src/optiverse/ui/widgets/collapsible_interface_widget.py`
- Custom widget for displaying interface with collapsible properties
- Features:
  - Header with expand/collapse toggle
  - Element type dropdown
  - Coordinate spinboxes (x1, y1, x2, y2 in mm)
  - Dynamic property section based on element type
  - Visual indicator color matching canvas line

**Step 2.2: Create InterfacePropertiesPanel**
- Composite widget containing stack of CollapsibleInterfaceWidget
- Handles add/delete/reorder operations
- Synchronizes with canvas selection

**Step 2.3: Update ComponentEditor layout**
- Remove old `kind_combo` (component type selector)
- Remove type-specific property fields at top level
- Integrate new InterfacePropertiesPanel
- Simplify toolbar actions

### Phase 3: Coordinate System Updates

**Step 3.1: Implement mm coordinate system**
- Current: Interfaces store pixel coordinates (x1_px, y1_px, etc.)
- Target: Interfaces store mm coordinates (x1_mm, y1_mm, etc.)
- Conversion factor: Computed from object_height_mm and calibration line

**Step 3.2: Update canvas synchronization**
```python
def _sync_canvas_to_interfaces(self):
    """Convert mm coordinates to pixels for canvas display."""
    mm_per_px = self._compute_mm_per_px()
    for i, iface in enumerate(self._interfaces):
        x1_px = iface.x1_mm / mm_per_px
        y1_px = iface.y1_mm / mm_per_px
        # ... create InterfaceLine
        
def _sync_interfaces_to_canvas(self):
    """Convert canvas pixel coordinates back to mm."""
    mm_per_px = self._compute_mm_per_px()
    lines = self.canvas.get_all_lines()
    for i, line in enumerate(lines):
        self._interfaces[i].x1_mm = line.x1 * mm_per_px
        self._interfaces[i].y1_mm = line.y1 * mm_per_px
        # ...
```

**Step 3.3: Handle calibration line**
- First interface serves as calibration reference
- Its length in pixels + object_height_mm determines mm_per_px scale
- Alternative: Add explicit "calibration line" that's not an optical interface

### Phase 4: Interface Type System

**Step 4.1: Define interface type registry**
```python
INTERFACE_TYPES = {
    'lens': {
        'name': 'Lens',
        'color': (0, 180, 180),  # Cyan
        'properties': ['efl_mm']
    },
    'mirror': {
        'name': 'Mirror',
        'color': (255, 140, 0),  # Orange
        'properties': []
    },
    'beam_splitter': {
        'name': 'Beam Splitter',
        'color': (0, 150, 120),  # Green
        'properties': ['split_T', 'split_R', 'is_polarizing', 'pbs_transmission_axis_deg']
    },
    'dichroic': {
        'name': 'Dichroic',
        'color': (255, 0, 255),  # Magenta
        'properties': ['cutoff_wavelength_nm', 'transition_width_nm', 'pass_type']
    },
    'refractive_interface': {
        'name': 'Refractive Interface',
        'color': (100, 100, 255),  # Blue
        'properties': ['n1', 'n2']
    }
}
```

**Step 4.2: Implement property field factory**
```python
def create_property_widgets(element_type: str) -> List[QtWidgets.QWidget]:
    """Create appropriate property widgets based on element type."""
    type_info = INTERFACE_TYPES[element_type]
    widgets = []
    
    for prop_name in type_info['properties']:
        widget = create_property_widget(prop_name)
        widgets.append(widget)
    
    return widgets
```

### Phase 5: Edit Dialog Redesign

**Step 5.1: Simplify edit dialog**
- Current dialog mixes geometry and properties
- New design: Properties are in collapsible widget, edit dialog only for detailed editing
- Or: Remove edit dialog entirely, edit inline in collapsible widget

**Step 5.2: Coordinate editing modes**
- Visual mode: Drag endpoints on canvas
- Precise mode: Enter mm coordinates in spinboxes
- Both stay synchronized via signals

### Phase 6: Backward Compatibility

**Step 6.1: Legacy component loader**
- Detect old component format
- Convert automatically on load
- Preserve all information
- Log migration for user awareness

**Step 6.2: Export options**
- New format (interface-based): Primary format
- Legacy format: Optional export for compatibility

**Step 6.3: Validation**
- Test loading all existing library components
- Verify visual appearance matches
- Ensure optical properties preserved

## Implementation Phases Timeline

### Phase 1: Foundation (Week 1)
1. Create InterfaceDefinition data model
2. Update ComponentRecord structure
3. Implement serialization/deserialization
4. Create migration utilities
5. Write unit tests

### Phase 2: UI Widgets (Week 1-2)
1. Implement CollapsibleInterfaceWidget
2. Build InterfacePropertiesPanel
3. Create property field factory
4. Test widget interactions

### Phase 3: Integration (Week 2)
1. Update ComponentEditor layout
2. Remove old type-specific UI
3. Integrate new interface panel
4. Update canvas synchronization

### Phase 4: Coordinate System (Week 2-3)
1. Implement mm coordinate conversion
2. Update all coordinate handling
3. Fix calibration line logic
4. Test coordinate accuracy

### Phase 5: Testing & Polish (Week 3)
1. Comprehensive testing
2. Backward compatibility validation
3. UI polish and refinements
4. Documentation updates

## Key Design Decisions

### Decision 1: Calibration vs Optical Interfaces

**Option A: First interface is calibration**
- Pros: Simpler data model, fewer UI elements
- Cons: First interface has dual purpose, potentially confusing

**Option B: Separate calibration line**
- Pros: Clear separation of concerns
- Cons: Extra UI complexity, more data to manage

**Recommendation: Option A** - Keep first interface as calibration, but make it clear in UI

### Decision 2: Coordinate Display Units

**Current: Pixels (normalized to 1000px)**
- Pros: Simple, no conversion needed
- Cons: Not physically meaningful

**Target: Millimeters (physical units)**
- Pros: Physically meaningful, matches real-world measurements
- Cons: Requires conversion, dependent on calibration

**Recommendation: Show both** - Primary display in mm, secondary in pixels

### Decision 3: Component Type Field

**Option A: Keep `kind` field for backward compatibility**
- Auto-compute from interfaces
- Used only for migration and display

**Option B: Remove `kind` entirely**
- Cleaner data model
- May break existing code

**Recommendation: Option A** - Keep but deprecate, compute automatically

### Decision 4: Property Editing Location

**Option A: Inline collapsible widgets**
- Edit properties directly in sidebar
- No separate dialog needed

**Option B: Modal edit dialog**
- Current approach
- More screen real estate

**Option C: Non-modal dockable properties**
- Edit while viewing canvas
- Most flexible

**Recommendation: Option A** - Inline editing with "advanced" button for modal dialog if needed

## Technical Challenges

### Challenge 1: Coordinate Conversion Accuracy
- **Issue:** Pixel ↔ mm conversion can accumulate errors
- **Solution:** Store mm as source of truth, compute pixels on demand
- **Validation:** Test round-trip conversion accuracy

### Challenge 2: UI Responsiveness with Many Interfaces
- **Issue:** Large components (50+ interfaces) may lag
- **Solution:** Virtual scrolling, lazy widget creation
- **Optimization:** Only create visible collapsible widgets

### Challenge 3: Canvas Synchronization
- **Issue:** Bi-directional sync can create loops
- **Solution:** Use signal blocking during programmatic updates
- **Pattern:**
```python
self.blockSignals(True)
# Update values
self.blockSignals(False)
```

### Challenge 4: Backward Compatibility
- **Issue:** Existing components must still work
- **Solution:** Comprehensive migration with validation
- **Testing:** Load every component in existing library

### Challenge 5: Type-specific Property Validation
- **Issue:** Each element type has different valid ranges
- **Solution:** Property metadata registry with validators
- **Example:**
```python
PROPERTY_VALIDATORS = {
    'efl_mm': lambda v: -1e7 < v < 1e7,
    'n1': lambda v: 1.0 <= v <= 3.0,
    # ...
}
```

## File Structure Changes

### New Files
```
src/optiverse/
  core/
    interface_definition.py  # InterfaceDefinition class
    interface_types.py       # Type registry and metadata
  ui/
    widgets/
      collapsible_interface_widget.py  # Single interface UI
      interface_properties_panel.py    # Multi-interface container
```

### Modified Files
```
src/optiverse/
  core/
    models.py  # Update ComponentRecord
  ui/
    views/
      component_editor_dialog.py  # Major refactoring
  objects/
    views/
      multi_line_canvas.py  # Coordinate system updates
```

## Testing Strategy

### Unit Tests
- InterfaceDefinition serialization
- Coordinate conversion accuracy
- Property validation
- Type registry lookups

### Integration Tests
- Component migration (old → new format)
- UI widget creation for all types
- Canvas synchronization
- Save/load round-trip

### Manual Testing Checklist
- [ ] Create component with each interface type
- [ ] Mix multiple interface types in one component
- [ ] Drag endpoints, verify mm coordinates update
- [ ] Edit properties, verify canvas updates
- [ ] Save and reload component
- [ ] Load legacy components
- [ ] Export and re-import
- [ ] Test with 1, 5, 20, 50 interfaces

## Success Criteria

1. ✅ Can create components with mixed interface types
2. ✅ All interface properties editable inline with collapsible UI
3. ✅ Coordinates displayed in mm (with px reference)
4. ✅ Canvas synchronization works flawlessly
5. ✅ All legacy components load and display correctly
6. ✅ Performance acceptable with 50+ interfaces
7. ✅ No regressions in existing functionality
8. ✅ Code is maintainable and well-documented

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing components | High | Medium | Comprehensive migration + testing |
| UI complexity overwhelming | Medium | Low | Progressive disclosure, good defaults |
| Performance degradation | Medium | Low | Virtual scrolling, lazy loading |
| Coordinate conversion bugs | High | Medium | Extensive unit tests, validation |
| User confusion | Medium | Medium | Clear labeling, documentation, tooltips |

## Open Questions

1. **Should we support interface ordering/reordering?**
   - Light travels through interfaces in order
   - Drag-to-reorder in list?

2. **How to handle interface dependencies?**
   - Some interfaces may reference others (e.g., "this is the reflected beam from interface 3")
   - Need dependency tracking?

3. **Naming interfaces vs numbering?**
   - "Interface 1, 2, 3" vs "Input Surface, BS Coating, Output"
   - Allow user-defined names?

4. **Presets system?**
   - Keep BS Cube preset?
   - Add more presets (Prism, PBS Cube, etc.)?
   - Make presets customizable?

5. **Validation strictness?**
   - Warn on invalid configurations or block?
   - Example: Lens with EFL=0

## Next Steps

1. **Review this strategy document** with team/stakeholders
2. **Prototype CollapsibleInterfaceWidget** to validate UX
3. **Create InterfaceDefinition data model** with tests
4. **Implement migration utility** and test on existing library
5. **Begin UI integration** once data model is stable

## References

- Current implementation: `src/optiverse/ui/views/component_editor_dialog.py`
- Data model: `src/optiverse/core/models.py`
- Canvas system: `src/optiverse/objects/views/multi_line_canvas.py`
- Existing docs:
  - `docs/UNIFIED_INTERFACE_SYSTEM.md`
  - `docs/VISUAL_INTERFACE_EDITOR_COMPLETE.md`
  - `docs/COORDINATE_EDIT_DIALOG.md`

