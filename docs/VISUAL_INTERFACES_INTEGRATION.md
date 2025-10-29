# Visual Interfaces Integration - Implementation Guide

## Overview

I've created the foundation for a unified visual interface system. Here's what's been implemented and what remains to complete the integration.

## ✅ Completed

### 1. MultiLineCanvas Widget
**File:** `src/optiverse/objects/views/multi_line_canvas.py`

A new canvas widget that supports:
- Multiple colored lines (interfaces)
- Draggable endpoints for all lines
- Line selection and hover feedback
- Color coding by interface type
- Backward compatible with single-line API

**Key Features:**
```python
# Add a line
line = InterfaceLine(
    x1=10, y1=20, x2=100, y2=200,
    color=QtGui.QColor(0, 150, 120),  # Green for BS
    label="BS Interface",
    properties={'n1': 1.0, 'n2': 1.517, 'is_beam_splitter': True}
)
canvas.add_line(line)

# Get all lines
lines = canvas.get_all_lines()

# Select a line
canvas.select_line(0)

# Backward compatibility
p1, p2 = canvas.get_points()  # Still works for simple components
```

### 2. Design Documentation
**Files:**
- `docs/UNIFIED_INTERFACE_SYSTEM.md` - Design philosophy and data model
- `docs/VISUAL_INTERFACES_INTEGRATION.md` - This file

## 🔨 To Complete

### Step 1: Update Component Editor Imports

```python
# In src/optiverse/ui/views/component_editor_dialog.py

# Replace:
from ...objects import ImageCanvas

# With:
from ...objects.views.multi_line_canvas import MultiLineCanvas, InterfaceLine
```

### Step 2: Replace Canvas Instance

```python
# In ComponentEditor.__init__():

# Replace:
self.canvas = ImageCanvas()

# With:
self.canvas = MultiLineCanvas()

# Add signal connection:
self.canvas.lineSelected.connect(self._on_line_selected)
self.canvas.linesChanged.connect(self._on_lines_changed)
```

### Step 3: Add Color Coding Helper

```python
# In ComponentEditor class:

def _get_interface_color(self, iface: Dict[str, Any]) -> QtGui.QColor:
    """Get color for interface based on its properties."""
    if iface.get('is_beam_splitter', False):
        if iface.get('is_polarizing', False):
            return QtGui.QColor(150, 0, 150)  # Purple for PBS
        else:
            return QtGui.QColor(0, 150, 120)  # Green for BS
    else:
        # Regular refractive interface
        n1 = iface.get('n1', 1.0)
        n2 = iface.get('n2', 1.0)
        if abs(n1 - n2) > 0.01:
            return QtGui.QColor(100, 100, 255)  # Blue for refraction
        else:
            return QtGui.QColor(150, 150, 150)  # Gray for same index
```

### Step 4: Sync Interfaces to Canvas

```python
def _sync_interfaces_to_canvas(self):
    """Sync interface list to canvas visual display."""
    # Clear existing lines
    self.canvas.clear_lines()
    
    if not self.canvas.has_image():
        return
    
    # For refractive objects, show all interfaces
    if self.kind_combo.currentText() == "refractive_object":
        for i, iface in enumerate(self._interfaces):
            # Convert from mm to pixels
            # (You'll need to implement coordinate conversion)
            line = InterfaceLine(
                x1=iface['x1_mm'],  # TODO: Convert to pixels
                y1=iface['y1_mm'],
                x2=iface['x2_mm'],
                y2=iface['y2_mm'],
                color=self._get_interface_color(iface),
                label=f"Interface {i+1}",
                properties=iface
            )
            self.canvas.add_line(line)
    else:
        # For simple components, show the calibration line
        p1, p2 = self.canvas.get_points()
        if p1 and p2:
            # Convert to single interface
            line = InterfaceLine(
                x1=p1[0], y1=p1[1],
                x2=p2[0], y2=p2[1],
                color=self._get_simple_component_color(),
                label=self.kind_combo.currentText().capitalize(),
                properties={'type': self.kind_combo.currentText()}
            )
            self.canvas.add_line(line)

def _get_simple_component_color(self) -> QtGui.QColor:
    """Get color for simple component types."""
    kind = self.kind_combo.currentText()
    colors = {
        'lens': QtGui.QColor(0, 180, 180),      # Cyan
        'mirror': QtGui.QColor(255, 140, 0),    # Orange
        'beamsplitter': QtGui.QColor(0, 150, 120),  # Green
        'dichroic': QtGui.QColor(255, 0, 255),  # Magenta
    }
    return colors.get(kind, QtGui.QColor(100, 100, 255))
```

### Step 5: Sync Canvas to Interfaces

```python
def _on_lines_changed(self):
    """Called when canvas lines change (dragging)."""
    if self.kind_combo.currentText() != "refractive_object":
        return
    
    # Update interface coordinates from canvas
    lines = self.canvas.get_all_lines()
    for i, line in enumerate(lines):
        if i < len(self._interfaces):
            # Convert from pixels to mm (TODO: implement conversion)
            self._interfaces[i]['x1_mm'] = line.x1
            self._interfaces[i]['y1_mm'] = line.y1
            self._interfaces[i]['x2_mm'] = line.x2
            self._interfaces[i]['y2_mm'] = line.y2
    
    # Update list display
    self._update_interface_list()

def _on_line_selected(self, index: int):
    """Called when a line is selected on canvas."""
    # Highlight corresponding item in list
    self.interfaces_list.setCurrentRow(index)
```

### Step 6: Update Add Interface

```python
def _add_interface(self):
    """Add a new interface."""
    # ... existing dialog code ...
    
    if d.exec():
        # Create interface dict
        iface = {
            'x1_mm': x1.value(),
            'y1_mm': y1.value(),
            'x2_mm': x2.value(),
            'y2_mm': y2.value(),
            'n1': n1.value(),
            'n2': n2.value(),
            'is_beam_splitter': is_bs.isChecked(),
            'split_T': split_t.value(),
            'split_R': split_r.value(),
            'is_polarizing': is_pbs.isChecked(),
            'pbs_transmission_axis_deg': pbs_axis.value()
        }
        self._interfaces.append(iface)
        self._update_interface_list()
        
        # NEW: Add to canvas
        self._sync_interfaces_to_canvas()
```

### Step 7: Update Interface List Click Handler

```python
# Connect list selection to canvas:
self.interfaces_list.currentRowChanged.connect(self._on_list_selection_changed)

def _on_list_selection_changed(self, row: int):
    """Sync list selection to canvas."""
    if row >= 0:
        self.canvas.select_line(row)
```

### Step 8: Update BS Cube Preset

```python
def _create_bs_cube_preset(self):
    """Create a beam splitter cube preset (5 interfaces)."""
    # ... existing dialog and interface creation ...
    
    # After creating interfaces:
    self._update_interface_list()
    self._sync_interfaces_to_canvas()  # NEW: Show on canvas
    
    # Auto-select the diagonal coating
    self.canvas.select_line(2)  # Index 2 is the BS coating
```

## Color Reference

### Interface Colors

```python
COLORS = {
    'refractive': QtGui.QColor(100, 100, 255),  # Blue
    'beamsplitter': QtGui.QColor(0, 150, 120),  # Green
    'pbs': QtGui.QColor(150, 0, 150),           # Purple
    'mirror': QtGui.QColor(255, 140, 0),        # Orange
    'lens': QtGui.QColor(0, 180, 180),          # Cyan
    'dichroic': QtGui.QColor(255, 0, 255),      # Magenta
    'same_index': QtGui.QColor(150, 150, 150),  # Gray
}
```

## Coordinate Conversion

You'll need to handle two coordinate systems:

### 1. Image Pixels (Canvas)
- Used by MultiLineCanvas
- Range: 0 to image width/height
- For visual display

### 2. Millimeters (Storage)
- Used in component records
- Local coordinate system (centered at 0,0)
- For physics simulation

### Conversion Functions

```python
def _mm_to_pixels(self, x_mm: float, y_mm: float) -> Tuple[float, float]:
    """Convert mm (local coords) to image pixels."""
    # Get image center
    w, h = self.canvas.image_pixel_size()
    center_x = w / 2
    center_y = h / 2
    
    # Get scale factor (mm per pixel)
    mm_per_px = self._compute_mm_per_pixel()
    
    if mm_per_px > 0:
        x_px = center_x + (x_mm / mm_per_px)
        y_px = center_y - (y_mm / mm_per_px)  # Y inverted (image coords)
        return (x_px, y_px)
    return (center_x, center_y)

def _pixels_to_mm(self, x_px: float, y_px: float) -> Tuple[float, float]:
    """Convert image pixels to mm (local coords)."""
    # Get image center
    w, h = self.canvas.image_pixel_size()
    center_x = w / 2
    center_y = h / 2
    
    # Get scale factor
    mm_per_px = self._compute_mm_per_pixel()
    
    if mm_per_px > 0:
        x_mm = (x_px - center_x) * mm_per_px
        y_mm = (center_y - y_px) * mm_per_px  # Y inverted
        return (x_mm, y_mm)
    return (0.0, 0.0)

def _compute_mm_per_pixel(self) -> float:
    """Compute mm per pixel from object height and line length."""
    object_height_mm = self.object_height_mm.value()
    
    # Get first line length in pixels
    lines = self.canvas.get_all_lines()
    if lines:
        line = lines[0]
        dx = line.x2 - line.x1
        dy = line.y2 - line.y1
        length_px = (dx*dx + dy*dy) ** 0.5
        
        if length_px > 0:
            return object_height_mm / length_px
    
    return 0.1  # Default fallback
```

## Testing Workflow

### Test 1: Simple Component (Lens)
1. Select "lens" type
2. Load image
3. Click two points to define optical axis
4. **Expected:** See ONE cyan line on canvas
5. Drag endpoints → line moves
6. Save → loads correctly

### Test 2: BS Cube Preset
1. Select "refractive_object"
2. Load image
3. Click "BS Cube Preset" → configure → OK
4. **Expected:** See 5 lines on canvas:
   - 4 blue lines (surfaces)
   - 1 green line (BS coating)
5. Click any line → highlights in list
6. Drag endpoint → geometry updates
7. Save → loads correctly with all interfaces

### Test 3: Manual Interface
1. Select "refractive_object"
2. Click "Add" → configure → OK
3. **Expected:** New line appears on canvas
4. Color matches interface type (blue/green)
5. Drag to position
6. Click "Edit" → change to BS → line turns green

## Benefits Summary

### Before (Separate Concepts)
- ❌ line_px: One line (not visual for refract objects)
- ❌ interfaces: List only (no visual)
- ❌ Confusing dual system
- ❌ No direct manipulation

### After (Unified System)
- ✅ All interfaces are visual lines
- ✅ Color-coded by function
- ✅ Draggable endpoints
- ✅ Consistent workflow
- ✅ WYSIWYG editing

## Next Steps

1. ✅ MultiLineCanvas created
2. ⬜ Integrate into component editor
3. ⬜ Add coordinate conversion
4. ⬜ Test with simple components
5. ⬜ Test with refractive objects
6. ⬜ Add to objects/__init__.py exports

## Need Help?

The foundation is solid. The main work remaining is:
1. Wire up the signals
2. Implement coordinate conversion
3. Update add/edit/delete to sync with canvas
4. Test and refine

The `MultiLineCanvas` widget is ready to use - it's just a matter of integration into the existing component editor workflow.

---

Let me know if you'd like me to implement the full integration or if you'd prefer to do it yourself with this guide!

