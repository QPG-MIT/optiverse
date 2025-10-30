# Interface Coordinate System Fix Strategy

## Problem Analysis

When optical interfaces are created in the component editor and then dragged to the scene, the interfaces appear at incorrect positions. This is due to a mismatch in coordinate systems.

### Coordinate Systems

#### 1. Component Editor Canvas (`MultiLineCanvas`)
- **Origin**: CENTER of the image
- **Y-axis**: FLIPPED (positive Y goes UP)
- **Units**: Millimeters
- **Conversion** (in `_draw_line` lines 284-298):
  ```python
  img_center_x_px = img_rect.width() / (2 * self._scale_fit)
  img_center_y_px = img_rect.height() / (2 * self._scale_fit)
  x_screen = img_rect.x() + (x_img_px + img_center_x_px) * self._scale_fit
  y_screen = img_rect.y() + (img_center_y_px - y_img_px) * self._scale_fit  # Y FLIPPED!
  ```

#### 2. Scene/RefractiveObjectItem
- **Origin**: CENTER of component (aligned to picked line center via `ComponentSprite.setOffset`)
- **Y-axis**: Standard Qt (positive Y goes DOWN)
- **Units**: Millimeters
- **No coordinate transformation** - uses mm coordinates directly

### Root Cause

The component editor canvas uses:
- **Centered + Y-flipped** coordinate system for display
- Stores interface coordinates directly in mm from this system
- When interfaces are loaded in scene, they're used as-is
- Scene expects **Centered + Y-standard** (not flipped)

**Result**: Interfaces appear vertically flipped and potentially offset.

### Additional Issue: Picked Line Reference

- Simple components (lens, mirror, etc.) align their sprite to the **picked line center**
- The picked line acts as the local origin (0, 0)
- ComponentSprite offsets the image so the picked line center is at (0, 0)
- RefractiveObjectItem doesn't have a "picked line" concept - it should use the image center or a similar reference point

## Solution Strategy

### Option 1: Fix Canvas Storage (RECOMMENDED)
Convert coordinates when syncing FROM canvas TO interfaces:
- Remove the Y-flip when storing
- Keep centered origin
- Store in standard Qt coordinates (Y down)

**Changes needed:**
1. `component_editor_dialog.py:_on_canvas_lines_changed()` (line 418-443)
   - When copying from canvas lines to interfaces, UN-flip the Y coordinate
2. `component_editor_dialog.py:_sync_interfaces_to_canvas()` (line 369-416)
   - When syncing interfaces to canvas, FLIP the Y coordinate for display

### Option 2: Fix Scene Loading
Convert coordinates when loading into scene:
- Keep canvas as-is
- Transform coordinates in RefractiveObjectItem

**Changes needed:**
1. `refractive_object_item.py:__init__()` or `_update_geom()`
   - Transform stored coordinates to scene coordinate system

### Option 3: Unified Coordinate System
Change canvas to use standard Qt coordinates (no Y-flip):
- More invasive change
- Would affect all canvas interactions
- Cleaner long-term solution

## Recommended Approach: Option 1

Fix the storage conversion in `component_editor_dialog.py`:

### Step 1: Fix `_on_canvas_lines_changed()`
When canvas lines change (user dragging), we copy coordinates from canvas to interfaces:

```python
def _on_canvas_lines_changed(self):
    """Called when canvas lines change (user dragging) - v2 system."""
    interfaces = self.interface_panel.get_interfaces()
    if not interfaces:
        return
    
    self.interface_panel.blockSignals(True)
    
    try:
        lines = self.canvas.get_all_lines()
        for i, line in enumerate(lines):
            if i < len(interfaces):
                # Canvas uses centered + Y-flipped coordinates
                # We need to store in centered + Y-standard (Qt standard)
                # FIX: Flip Y when storing
                interfaces[i].x1_mm = line.x1
                interfaces[i].y1_mm = -line.y1  # Flip Y!
                interfaces[i].x2_mm = line.x2
                interfaces[i].y2_mm = -line.y2  # Flip Y!
                
                self.interface_panel.update_interface(i, interfaces[i])
    finally:
        self.interface_panel.blockSignals(False)
```

### Step 2: Fix `_sync_interfaces_to_canvas()`
When syncing interfaces to canvas for display:

```python
def _sync_interfaces_to_canvas(self):
    """Sync interface panel to canvas visual display (v2 system)."""
    if not self.canvas.has_image():
        return
    
    self.canvas.blockSignals(True)
    self.canvas.clear_lines()
    
    interfaces = self.interface_panel.get_interfaces()
    if not interfaces:
        self.canvas.blockSignals(False)
        return
    
    object_height = self.object_height_mm.value()
    w, h = self.canvas.image_pixel_size()
    
    if h > 0 and object_height > 0:
        mm_per_px = object_height / h
    else:
        mm_per_px = 1.0
    
    self.canvas.set_mm_per_pixel(mm_per_px)
    
    for i, interface in enumerate(interfaces):
        r, g, b = interface.get_color()
        color = QtGui.QColor(r, g, b)
        
        # FIX: Flip Y when displaying (interfaces stored with Y-standard, canvas uses Y-flipped)
        line = InterfaceLine(
            x1=interface.x1_mm, y1=-interface.y1_mm,  # Flip Y for display!
            x2=interface.x2_mm, y2=-interface.y2_mm,  # Flip Y for display!
            color=color,
            label=interface.get_label(),
            properties={'interface': interface}
        )
        self.canvas.add_line(line)
    
    self.canvas.blockSignals(False)
    self.canvas.update()
```

### Step 3: Verify RefractiveObjectItem
Check that RefractiveObjectItem uses coordinates correctly:
- It should expect centered coordinates with Y-standard (Qt convention)
- No changes needed if we fix the storage correctly

### Step 4: Handle ComponentSprite Alignment
For refractive objects with sprites, we need to ensure the sprite aligns correctly.
- ComponentSprite centers around the picked line
- RefractiveObjectItem interfaces should be relative to this center
- May need to adjust interface coordinates relative to picked line center

## Testing Plan

1. **Create simple refractive object** (no sprite):
   - Add interface at canvas center (0, 0)
   - Save and drag to scene
   - Verify interface appears at component center

2. **Create refractive object with sprite**:
   - Load image
   - Set object height
   - Add interfaces aligned to image features
   - Save and drag to scene
   - Verify interfaces align with sprite correctly

3. **Create BS cube preset**:
   - Use BS Cube preset
   - Drag to scene
   - Verify all 5 interfaces appear correctly positioned

4. **Import from Zemax**:
   - Import ZMX file
   - Drag to scene
   - Verify interfaces match Zemax geometry

## Implementation Order

1. ✅ Create strategy document (this file)
2. ✅ Fix `_on_canvas_lines_changed()` - full coordinate transformation (center→top-left, Y-flip)
3. ✅ Fix `_sync_interfaces_to_canvas()` - full coordinate transformation (top-left→center, Y-flip)
4. ✅ Add detailed coordinate system comments in code
5. Test with simple interface (no sprite)
6. Test with sprite alignment
7. Test with BS cube preset
8. Test with Zemax import
9. Update any existing components in library to new coordinate system

## Coordinate System Details (FINAL)

### Storage Format (InterfaceDefinition)
- **Origin**: (0, 0) at TOP-LEFT of image
- **X-axis**: Increases to the RIGHT
- **Y-axis**: Increases DOWNWARD (standard image/Qt coordinates)
- **Units**: Millimeters
- **Range**: 
  - X: 0 to image_width_mm
  - Y: 0 to object_height_mm (same as image_height_mm)

### Canvas Display (MultiLineCanvas)
- **Origin**: (0, 0) at CENTER of image
- **X-axis**: Increases to the RIGHT
- **Y-axis**: Increases UPWARD (flipped for intuitive display)
- **Units**: Millimeters  
- **Range**:
  - X: -image_width_mm/2 to +image_width_mm/2
  - Y: -image_height_mm/2 to +image_height_mm/2

### Scene (RefractiveObjectItem)
- **Origin**: (0, 0) at component position (set by item.setPos)
- **X-axis**: Increases to the RIGHT
- **Y-axis**: Increases DOWNWARD (standard Qt)
- **Units**: Millimeters
- **Coordinates**: Same as storage format (top-left, Y-down)

### Conversion Formulas

**Storage → Canvas Display:**
```python
# Get image dimensions
w_mm = image_width_px * mm_per_px
h_mm = object_height_mm

# Step 1: Shift origin (top-left → center)
x_centered = x_storage - (w_mm / 2)
y_centered = y_storage - (h_mm / 2)

# Step 2: Flip Y axis
x_canvas = x_centered
y_canvas = -y_centered
```

**Canvas Display → Storage:**
```python
# Step 1: Flip Y axis
x_centered = x_canvas
y_centered = -y_canvas

# Step 2: Shift origin (center → top-left)
x_storage = x_centered + (w_mm / 2)
y_storage = y_centered + (h_mm / 2)
```

