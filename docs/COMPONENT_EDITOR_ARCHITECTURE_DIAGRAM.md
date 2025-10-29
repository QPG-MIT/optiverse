# Component Editor Architecture - Visual Diagrams

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Component Editor                       │
│                                                         │
│  ┌───────────────────────┐  ┌─────────────────────┐   │
│  │                       │  │                     │   │
│  │   MultiLineCanvas     │  │  Settings Panel     │   │
│  │   (Visual Display)    │  │                     │   │
│  │                       │  │  ┌───────────────┐  │   │
│  │  • Image background   │  │  │ Name         │  │   │
│  │  • Colored lines      │◄─┼──┤ Object Height│  │   │
│  │  • Draggable endpoints│  │  └───────────────┘  │   │
│  │  • Selection feedback │  │                     │   │
│  │                       │  │  ┌───────────────┐  │   │
│  └───────────────────────┘  │  │ Interface     │  │   │
│                              │  │ Properties    │  │   │
│                              │  │ Panel         │  │   │
│                              │  │               │  │   │
│                              │  │  ▼ Iface 1    │  │   │
│                              │  │  ▶ Iface 2    │  │   │
│                              │  │  ▶ Iface 3    │  │   │
│                              │  └───────────────┘  │   │
│                              │                     │   │
│                              │  ┌───────────────┐  │   │
│                              │  │ Library       │  │   │
│                              │  └───────────────┘  │   │
│                              └─────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      User Actions                        │
└────────────┬─────────────────────────────┬───────────────┘
             │                             │
             ▼                             ▼
    ┌────────────────┐          ┌────────────────────┐
    │  Drag Endpoint │          │  Edit Properties   │
    │   on Canvas    │          │   in Widget        │
    └────────┬───────┘          └─────────┬──────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────────────────────────────────────┐
    │         ComponentEditor Controller              │
    │  • Coordinate conversion (px ↔ mm)              │
    │  • Interface synchronization                    │
    │  • Signal routing                               │
    └────────────┬───────────────┬────────────────────┘
                 │               │
                 ▼               ▼
    ┌────────────────┐  ┌────────────────────┐
    │ Canvas Updates │  │ Widget Updates     │
    │ • Redraw lines │  │ • Update spinboxes │
    │ • Colors       │  │ • Update labels    │
    └────────────────┘  └────────────────────┘
                 │               │
                 └───────┬───────┘
                         ▼
              ┌─────────────────────┐
              │ InterfaceDefinition │
              │   (Data Model)      │
              └─────────────────────┘
```

### Class Hierarchy

```
ComponentRecord
  ├─ name: str
  ├─ object_height_mm: float
  ├─ interfaces: List[InterfaceDefinition]
  └─ notes: str

InterfaceDefinition
  ├─ Geometry
  │   ├─ x1_mm, y1_mm: float
  │   └─ x2_mm, y2_mm: float
  ├─ Type
  │   └─ element_type: str
  └─ Properties (type-dependent)
      ├─ Lens: efl_mm
      ├─ Mirror: reflectivity
      ├─ BeamSplitter: split_T, split_R, is_polarizing, pbs_axis
      ├─ Dichroic: cutoff_wavelength_nm, transition_width_nm, pass_type
      └─ Refractive: n1, n2
```

### Signal Flow Diagram

```
Canvas Drag Event
      ↓
  mouseMoveEvent()
      ↓
  _dragging_line updated
      ↓
  linesChanged signal ──────────────────┐
      ↓                                 │
ComponentEditor._on_canvas_lines_changed()
      ↓                                 │
  pixels → mm conversion                │
      ↓                                 │
  InterfaceDefinition updated           │
      ↓                                 ▼
InterfacePropertiesPanel.update() ◄─────┘
      ↓
  CollapsibleInterfaceWidget.update()
      ↓
  Spinboxes show new mm values
```

### Coordinate System Diagram

```
┌──────────────────────────────────────────────────┐
│         Image Coordinate System                  │
│                                                  │
│  (0,0)                                           │
│    ┌────────────────────────────────┐           │
│    │                                │           │
│    │     Image (e.g. 800x600 px)    │           │
│    │                                │           │
│    │       ●────────●  ← Line       │           │
│    │      (x1,y1) (x2,y2)           │           │
│    │                                │           │
│    └────────────────────────────────┘           │
│                                      (W, H)      │
└──────────────────────────────────────────────────┘
                    ↕
            Conversion Factor
         mm_per_px = object_height_mm / line_length_px
                    ↕
┌──────────────────────────────────────────────────┐
│      Physical Coordinate System (mm)             │
│                                                  │
│        (-W/2 * mm_per_px, +H/2 * mm_per_px)      │
│              ┌──────────────────┐                │
│              │                  │                │
│              │   ●────────●     │                │
│              │ (x1mm) (x2mm)    │                │
│      Origin→ │        ●         │                │
│        (0,0) │                  │                │
│              └──────────────────┘                │
│        (+W/2 * mm_per_px, -H/2 * mm_per_px)      │
└──────────────────────────────────────────────────┘
```

### Widget Composition

```
ComponentEditor (QMainWindow)
│
├─ Toolbar
│   ├─ [New] [Open] [Paste] [Clear]
│   └─ [Copy] [Save] [Reload]
│
├─ Central Widget
│   └─ MultiLineCanvas
│       ├─ Background pixmap
│       ├─ InterfaceLine 1 (red)
│       ├─ InterfaceLine 2 (blue)
│       └─ InterfaceLine 3 (green)
│
└─ Right Dock Widget
    ├─ Settings Group
    │   ├─ Name [QLineEdit]
    │   └─ Object Height [QDoubleSpinBox]
    │
    ├─ InterfacePropertiesPanel [QScrollArea]
    │   ├─ CollapsibleInterfaceWidget 1
    │   │   ├─ Header [collapsed/expanded]
    │   │   ├─ Element Type [QComboBox]
    │   │   ├─ Geometry Group
    │   │   │   ├─ x1, y1 [QDoubleSpinBox]
    │   │   │   └─ x2, y2 [QDoubleSpinBox]
    │   │   └─ Properties Group (dynamic)
    │   │       └─ [Type-specific widgets]
    │   │
    │   ├─ CollapsibleInterfaceWidget 2
    │   └─ CollapsibleInterfaceWidget 3
    │
    └─ Library Widget
        └─ [QListWidget with icons]
```

### State Machine - Interface Editing

```
              ┌──────────┐
              │  Idle    │
              └────┬─────┘
                   │
       ┌───────────┼───────────┐
       │                       │
   [Drag Start]          [Select Interface]
       │                       │
       ▼                       ▼
  ┌─────────┐            ┌──────────┐
  │Dragging │            │ Selected │
  └────┬────┘            └────┬─────┘
       │                      │
   [Drag End]          [Edit Property]
       │                      │
       ▼                      ▼
  ┌─────────┐            ┌──────────┐
  │ Update  │            │ Editing  │
  │Geometry │            │Properties│
  └────┬────┘            └────┬─────┘
       │                      │
       └──────────┬───────────┘
                  │
              [Commit]
                  ▼
              ┌──────────┐
              │  Idle    │
              └──────────┘
```

## Migration Architecture

### Legacy to New Format

```
┌─────────────────────────────────────────────┐
│         Legacy Component Format             │
│  ┌───────────────────────────────────┐     │
│  │ kind: "lens"                      │     │
│  │ efl_mm: 100.0                     │     │
│  │ line_px: (x1, y1, x2, y2)         │     │
│  │ object_height_mm: 25.4            │     │
│  └───────────────────────────────────┘     │
└─────────────┬───────────────────────────────┘
              │
              ▼
    ┌──────────────────────┐
    │ Migration Utility    │
    │  • Detect format     │
    │  • Convert coords    │
    │  • Map properties    │
    └─────────┬────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         New Component Format                │
│  ┌───────────────────────────────────┐     │
│  │ interfaces: [                     │     │
│  │   InterfaceDefinition(            │     │
│  │     element_type: "lens",         │     │
│  │     x1_mm: -12.7, y1_mm: 0.0,     │     │
│  │     x2_mm: 12.7, y2_mm: 0.0,      │     │
│  │     efl_mm: 100.0                 │     │
│  │   )                               │     │
│  │ ]                                 │     │
│  └───────────────────────────────────┘     │
└─────────────────────────────────────────────┘
```

## Type System Architecture

### Interface Type Registry

```
┌──────────────────────────────────────────────────┐
│           INTERFACE_TYPES Registry               │
├──────────────────────────────────────────────────┤
│  'lens'                                          │
│    ├─ color: (0, 180, 180)                       │
│    ├─ emoji: 🔵                                   │
│    ├─ properties: ['efl_mm']                     │
│    ├─ property_ranges: {efl_mm: (-10000, 10000)}│
│    └─ property_units: {efl_mm: 'mm'}             │
│                                                  │
│  'mirror'                                        │
│    ├─ color: (255, 140, 0)                       │
│    ├─ emoji: 🟠                                   │
│    ├─ properties: ['reflectivity']               │
│    └─ ...                                        │
│                                                  │
│  'beam_splitter'                                 │
│    ├─ color: (0, 150, 120) or (150, 0, 150)     │
│    ├─ emoji: 🟢 or 🟣                            │
│    ├─ properties: ['split_T', 'split_R', ...]   │
│    └─ ...                                        │
│                                                  │
│  'dichroic'                                      │
│  'refractive_interface'                          │
└──────────────────────────────────────────────────┘
```

### Property Widget Factory

```
create_property_widgets(element_type)
              │
              ├─ if element_type == 'lens':
              │     return [EFL_SpinBox]
              │
              ├─ if element_type == 'mirror':
              │     return [Reflectivity_SpinBox]
              │
              ├─ if element_type == 'beam_splitter':
              │     return [SplitT_SpinBox,
              │             SplitR_SpinBox,
              │             IsPolarizing_CheckBox,
              │             PBSAxis_SpinBox]
              │
              ├─ if element_type == 'dichroic':
              │     return [Cutoff_SpinBox,
              │             Width_SpinBox,
              │             PassType_ComboBox]
              │
              └─ if element_type == 'refractive_interface':
                    return [N1_SpinBox,
                            N2_SpinBox]
```

## Performance Considerations

### Lazy Loading Strategy

```
Initial Load
      │
      ├─ Load component data
      │     └─ InterfaceDefinition objects created
      │
      ├─ Create canvas lines
      │     └─ All lines rendered (O(N))
      │
      └─ Create interface widgets
            ├─ First 5 expanded (widgets created)
            └─ Rest collapsed (no widgets yet)

User Expands Interface
      │
      └─ Create property widgets on-demand
            └─ Connect signals
```

### Update Throttling

```
User Drags Endpoint (many events/sec)
      │
      ├─ Throttle to 60 FPS
      │     └─ Update canvas immediately
      │
      └─ Debounce property updates
            └─ Update after 50ms idle
```

## Testing Architecture

```
┌────────────────────────────────────────────┐
│              Test Pyramid                  │
├────────────────────────────────────────────┤
│                                            │
│         ▲  Integration Tests               │
│        ╱│╲  • Load/save components         │
│       ╱ │ ╲  • Canvas ↔ widgets sync       │
│      ╱  │  ╲                               │
│     ╱───┴───╲                              │
│    ╱    │    ╲  Unit Tests                 │
│   ╱     │     ╲  • InterfaceDefinition     │
│  ╱      │      ╲  • Coordinate conversion  │
│ ╱       │       ╲  • Type registry         │
│╱────────┴────────╲  • Migration utils      │
└────────────────────────────────────────────┘
```

## File Structure

```
src/optiverse/
├─ core/
│  ├─ models.py                    [Modified]
│  ├─ interface_definition.py      [New]
│  ├─ interface_types.py           [New]
│  └─ component_migration.py       [New]
│
├─ ui/
│  ├─ views/
│  │  └─ component_editor_dialog.py [Modified]
│  │
│  └─ widgets/
│     ├─ __init__.py               [New]
│     ├─ collapsible_interface_widget.py  [New]
│     └─ interface_properties_panel.py    [New]
│
└─ objects/
   └─ views/
      └─ multi_line_canvas.py      [Existing]

tests/
├─ core/
│  ├─ test_interface_definition.py [New]
│  ├─ test_interface_types.py      [New]
│  └─ test_component_migration.py  [New]
│
└─ ui/
   ├─ test_collapsible_interface_widget.py  [New]
   └─ test_interface_properties_panel.py    [New]
```

## Summary

This architecture provides:

✅ **Separation of Concerns**
- Data model independent of UI
- Type system separate from implementation
- Migration logic isolated

✅ **Extensibility**
- Easy to add new interface types
- Plugin system possible
- Custom properties supported

✅ **Maintainability**
- Clear module boundaries
- Well-defined interfaces
- Comprehensive tests

✅ **Performance**
- Lazy loading
- Update throttling
- Efficient rendering

✅ **User Experience**
- Responsive UI
- Visual feedback
- Intuitive workflow

