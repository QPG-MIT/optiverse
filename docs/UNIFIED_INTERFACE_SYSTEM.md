# Unified Interface System - Design Document

## Concept Unification

### Problem
Originally, the component editor had two separate concepts:
1. **line_px** - A single line for calibration (defining optical axis)
2. **interfaces** - Multiple interface definitions for refractive objects (in a list widget, not visual)

This created confusion and inconsistency.

### Solution
**Unified Optical Interfaces:**
- Every component has **optical interfaces** (visual lines on canvas)
- Simple components (lens, mirror, BS) → 1 interface
- Refractive objects → N interfaces
- All interfaces are:
  - Visually drawn on the canvas
  - Color-coded by type
  - Draggable endpoints
  - Stored in the same data structure

## Data Model

### InterfaceLine
Each optical interface is represented as:

```python
@dataclass
class InterfaceLine:
    x1: float  # Start X (image pixels)
    y1: float  # Start Y
    x2: float  # End X
    y2: float  # End Y
    color: QtGui.QColor  # Visual color
    label: str  # Optional label
    properties: Dict[str, Any]  # n1, n2, is_BS, etc.
```

### Properties Dictionary
For refractive interfaces:
```python
properties = {
    'n1': 1.0,              # Incident refractive index
    'n2': 1.517,            # Transmitted refractive index
    'is_beam_splitter': False,
    'split_T': 50.0,
    'split_R': 50.0,
    'is_polarizing': False,
    'pbs_transmission_axis_deg': 0.0
}
```

## Color Coding

### Interface Colors
- **Blue (100, 100, 255)**: Regular refractive interface
- **Green (0, 150, 120)**: Beam splitter coating
- **Purple (150, 0, 150)**: PBS (polarizing BS)
- **Orange (255, 140, 0)**: Mirror/reflection
- **Cyan (0, 180, 180)**: Lens (thin lens approximation)

### Visual Feedback
- **Normal line**: 2px width
- **Hovered line**: 2.5px width
- **Selected line**: 3px width, lighter color
- **Endpoints**: Circles (5px normal, 6px when hovered/selected)

## Component Types Mapping

### Lens (1 interface)
```
Type: lens
Interfaces: 1 line (optical axis)
Color: Cyan
Properties: {type: 'lens', efl_mm: float}
```

### Mirror (1 interface)
```
Type: mirror
Interfaces: 1 line (reflective surface)
Color: Orange
Properties: {type: 'mirror'}
```

### Beamsplitter (1 interface)
```
Type: beamsplitter
Interfaces: 1 line (splitting surface)
Color: Green (regular) or Purple (PBS)
Properties: {
    type: 'beamsplitter',
    is_polarizing: bool,
    split_T: float,
    split_R: float
}
```

### Dichroic (1 interface)
```
Type: dichroic
Interfaces: 1 line (wavelength-selective surface)
Color: Magenta
Properties: {
    type: 'dichroic',
    cutoff_wavelength_nm: float,
    transition_width_nm: float,
    pass_type: str
}
```

### Refractive Object (N interfaces)
```
Type: refractive_object
Interfaces: N lines (one per optical surface)
Colors: Mixed (blue for refraction, green for BS coating)
Properties per interface: {
    n1: float,
    n2: float,
    is_beam_splitter: bool,
    split_T: float,
    split_R: float,
    is_polarizing: bool,
    pbs_transmission_axis_deg: float
}
```

## Workflow

### Simple Component (Lens Example)

1. User selects "lens" type
2. Canvas shows 1 line (optical axis) in cyan
3. User drags endpoints to define lens position
4. Sets EFL in properties
5. Saves → stored as 1 interface with lens properties

### Refractive Object (BS Cube Example)

1. User selects "refractive_object" type
2. Clicks "BS Cube Preset"
3. Canvas shows 5 lines:
   - Line 1 (blue): Left surface
   - Line 2 (blue): Bottom surface
   - Line 3 (green): Diagonal coating (BS)
   - Line 4 (blue): Right surface
   - Line 5 (blue): Top surface
4. User can drag any endpoint to adjust geometry
5. User can select line to edit properties
6. Saves → stored as 5 interfaces

### Adding Interface Manually

1. Click "Add Interface" button
2. New line appears on canvas (default position)
3. Dialog opens to set properties (n1, n2, etc.)
4. User drags endpoints to position
5. Line color updates based on properties

## Implementation Details

### MultiLineCanvas
New canvas widget supporting:
- Multiple lines with individual colors
- Draggable endpoints for all lines
- Line selection (click to select)
- Hover feedback
- Backward compatible with old single-line API

### Component Editor Integration

**Data Flow:**
```
User Action → Canvas Update → Interface List Update → Properties Update
     ↑                                                         ↓
     └────────────────── Sync ───────────────────────────────┘
```

**Synchronization:**
- Canvas lines ↔ Interface list always in sync
- Selecting in canvas → highlights in list
- Selecting in list → highlights on canvas
- Dragging endpoint → updates coordinates in properties
- Changing properties → updates line appearance

### Serialization

**Storage Format:**
```json
{
  "kind": "refractive_object",
  "interfaces": [
    {
      "x1_mm": -12.7,  // In mm (local coords)
      "y1_mm": -12.7,
      "x2_mm": -12.7,
      "y2_mm": 12.7,
      "n1": 1.0,
      "n2": 1.517,
      "is_beam_splitter": false
    },
    // ... more interfaces
  ]
}
```

**Coordinate Conversion:**
- Canvas: Image pixels (e.g., 0-1000)
- Storage: Millimeters (local coordinate system)
- Conversion factor: mm_per_pixel (computed from object_height_mm and line length)

## Benefits

### 1. Visual Clarity
- See all optical interfaces on the image
- Immediate visual feedback
- No hidden geometry

### 2. Direct Manipulation
- Drag endpoints to adjust
- Visual WYSIWYG editing
- Intuitive workflow

### 3. Consistency
- Same UI for simple and complex components
- Unified data model
- Less confusion

### 4. Flexibility
- Easy to add/remove interfaces
- Visual debugging of geometry
- Quick adjustments

### 5. Color Coding
- Instant identification of interface types
- BS coatings stand out in green
- Refractive surfaces in blue

## Migration Path

### Backward Compatibility

**Old Components:**
- Automatically converted to single-interface format
- `line_px` → first interface
- No breaking changes

**New Components:**
- Use multi-interface system
- Can have 1 or more interfaces
- Old API still works for simple cases

### API Compatibility

```python
# Old API (still works):
canvas.get_points()  # Returns first line as (p1, p2)
canvas.set_points(p1, p2)  # Sets first line

# New API:
canvas.get_all_lines()  # Returns List[InterfaceLine]
canvas.add_line(line)  # Add new line
canvas.select_line(index)  # Select line
```

## Future Enhancements

### 1. Curved Interfaces
- Support for circular arcs
- Spherical mirrors and lenses
- Bezier curves

### 2. 3D Visualization
- Extrude 2D interfaces into 3D
- Rotate view
- Better understanding of geometry

### 3. Smart Snapping
- Snap endpoints to grid
- Snap to other interfaces
- Alignment guides

### 4. Templates
- Save interface patterns as templates
- Quick insertion of common shapes
- Community template library

### 5. Parametric Interfaces
- Define interfaces with formulas
- Update multiple interfaces together
- Constraints and relationships

## Summary

The unified interface system provides a consistent, visual way to define optical elements:

✅ All optical surfaces are **visible lines on canvas**
✅ **Color-coded** by function (blue=refraction, green=BS)
✅ **Draggable endpoints** for direct manipulation
✅ **Same workflow** for simple and complex components
✅ **Backward compatible** with existing components

This makes the component editor more intuitive and powerful while maintaining simplicity for basic use cases.

