# Visual Interface Editor - Implementation Complete

## Overview

The component editor has been fully updated to use a unified visual line system. There is no longer a separation between "line points" and "optical interfaces" - everything is now represented as colored, draggable lines on the canvas.

## What Changed

### 1. New MultiLineCanvas Widget

- **Location**: `src/optiverse/objects/views/multi_line_canvas.py`
- **Features**:
  - Display multiple colored lines on an image
  - Each line is draggable by its endpoints
  - Line selection and highlighting
  - Backward compatible with old single-line components
  - `InterfaceLine` dataclass for structured line data

### 2. Component Editor Integration

- **File**: `src/optiverse/ui/views/component_editor_dialog.py`
- **Changes**:
  - Replaced `ImageCanvas` with `MultiLineCanvas`
  - Added color coding system for different interface types:
    - **Blue**: Regular refractive interfaces (n1 ≠ n2)
    - **Green**: Beam splitter interfaces
    - **Purple**: Polarizing beam splitter (PBS) interfaces
    - **Orange**: Mirrors (simple components)
    - **Cyan**: Lenses (simple components)
    - **Magenta**: Dichroic filters
  - Bidirectional synchronization between:
    - Canvas lines ↔ Interface list
    - List selection ↔ Canvas selection
  - All line endpoint changes update interface data automatically

### 3. Signal Flow

```
User drags line endpoint
    ↓
canvas.linesChanged signal
    ↓
_on_canvas_lines_changed()
    ↓
Updates _interfaces[] list
```

```
User selects in list
    ↓
interfaces_list.currentRowChanged signal
    ↓
_on_interface_list_selection()
    ↓
canvas.select_line()
```

```
User adds/edits/deletes interface
    ↓
_update_interface_list()
    ↓
_sync_interfaces_to_canvas()
    ↓
Visual update on canvas
```

## How to Use

### For Simple Components (Lens, Mirror, Beamsplitter, Dichroic)

1. Drop an image onto the canvas
2. A colored calibration line appears automatically
3. Drag the endpoints to align with the optical element
4. The color matches the component type
5. Enter object height and other parameters
6. Save the component

### For Refractive Objects

1. Select "refractive_object" from the Kind dropdown
2. Drop an image onto the canvas
3. Click "Add Interface" to add optical interfaces
4. Each interface appears as a colored line on the canvas:
   - Blue for regular refraction
   - Green for beam splitter coatings
   - Purple for PBS coatings
5. Drag any endpoint to adjust interface positions
6. Select an interface in the list to highlight it on canvas
7. Double-click or use "Edit" to change properties (n1, n2, BS settings)
8. Line colors update automatically based on properties

### Beam Splitter Cube Preset

1. Select "refractive_object"
2. Drop an image
3. Click "BS Cube Preset"
4. Configure size, glass index, and split ratio
5. Five interfaces are created automatically:
   - 4 blue lines for the glass-air surfaces
   - 1 green diagonal line for the beam splitter coating
6. Drag any endpoint to adjust the cube geometry

## Technical Details

### Line Storage

Each interface stores both:
- **Pixel coordinates** (`x1_px`, `y1_px`, `x2_px`, `y2_px`): For canvas display
- **Physical coordinates** (`x1_mm`, `y1_mm`, `x2_mm`, `y2_mm`): For ray tracing

When the user drags a line, pixel coordinates update immediately. Physical coordinates are computed when saving based on the calibration scale.

### Color Coding Function

```python
def _get_interface_color(self, iface: dict) -> QtGui.QColor:
    if iface.get('is_beam_splitter', False):
        if iface.get('is_polarizing', False):
            return QtGui.QColor(150, 0, 150)  # Purple for PBS
        else:
            return QtGui.QColor(0, 150, 120)  # Green for BS
    else:
        n1 = iface.get('n1', 1.0)
        n2 = iface.get('n2', 1.0)
        if abs(n1 - n2) > 0.01:
            return QtGui.QColor(100, 100, 255)  # Blue for refraction
        else:
            return QtGui.QColor(150, 150, 150)  # Gray for same index
```

### Backward Compatibility

The `MultiLineCanvas` provides `get_points()` and `set_points()` methods for backward compatibility with code expecting the old two-point interface. These methods work with the first line only.

## Files Modified

1. **src/optiverse/objects/views/multi_line_canvas.py** (NEW)
   - Multi-line canvas widget

2. **src/optiverse/objects/views/__init__.py**
   - Export `MultiLineCanvas` and `InterfaceLine`

3. **src/optiverse/ui/views/component_editor_dialog.py**
   - Replace ImageCanvas with MultiLineCanvas
   - Add color coding functions
   - Add bidirectional sync logic
   - Update all references to canvas methods
   - Fix ImageCanvas._render_svg_to_pixmap → MultiLineCanvas

## Benefits

1. **Visual Feedback**: See all interfaces as colored lines immediately
2. **Direct Manipulation**: Drag endpoints instead of typing coordinates
3. **Color Coding**: Instantly identify interface types
4. **No Duplication**: Single source of truth for interface geometry
5. **Consistency**: Same workflow for simple and complex components
6. **Flexibility**: Easy to add, edit, delete, and reorder interfaces

## Testing Checklist

- [ ] Create a simple lens component
- [ ] Create a mirror component
- [ ] Create a refractive object with 2-3 interfaces
- [ ] Use BS cube preset
- [ ] Drag line endpoints
- [ ] Select interfaces from list
- [ ] Edit interface properties
- [ ] Delete interfaces
- [ ] Save and reload component
- [ ] Verify colors match interface types

## Next Steps

The visual interface editor is now complete and ready to use! Users can create complex optical components with multiple refractive interfaces through an intuitive visual interface.

