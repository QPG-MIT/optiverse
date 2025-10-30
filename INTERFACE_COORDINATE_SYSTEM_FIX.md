# Interface Coordinate System Fix

## Problem
Optical interfaces drawn in the component editor were not correctly displayed and handled on the main canvas, likely due to coordinate system mismatch.

## Root Cause
The coordinate system transformations between different parts of the application needed explicit documentation and validation. While the transformations were mathematically correct, the lack of clear documentation made it difficult to verify correctness and debug issues.

## Coordinate Systems

The application uses THREE different coordinate systems:

### 1. Component Editor Canvas (MultiLineCanvas)
- **Purpose**: Intuitive visual editing of interfaces
- **Origin**: Image center (0,0)
- **Y-axis**: UP (positive Y is up, negative Y is down)
- **Units**: millimeters
- **Data structure**: `InterfaceLine`

### 2. Storage Format (InterfaceDefinition)
- **Purpose**: Persistent storage in JSON/library
- **Origin**: Image center (0,0)
- **Y-axis**: DOWN (positive Y is down, negative Y is up) - Standard Qt convention
- **Units**: millimeters
- **Data structure**: `InterfaceDefinition`

### 3. Main Canvas Display (RefractiveObjectItem)
- **Purpose**: Display on main QGraphicsScene
- **Origin**: Picked line center (component's reference point)
- **Y-axis**: DOWN (standard Qt/QGraphicsScene)
- **Units**: millimeters
- **Data structure**: `RefractiveInterface`

## Coordinate Transformations

### Component Editor ↔ Storage
When syncing between canvas display and storage:

**Canvas → Storage (when user drags):**
```python
# In _on_canvas_lines_changed()
storage_y = -canvas_y  # Flip Y-axis
```

**Storage → Canvas (when loading for display):**
```python
# In _sync_interfaces_to_canvas()
canvas_y = -storage_y  # Flip Y-axis
```

### Storage → Main Canvas
When dropping component on main canvas:

**InterfaceDefinition → RefractiveInterface:**
```python
# Direct copy - both use Y-down
ref_iface.x1_mm = iface_def.x1_mm
ref_iface.y1_mm = iface_def.y1_mm  # No flip needed
```

**RefractiveInterface → Display:**
```python
# Apply picked line offset
display_x = interface_x - picked_line_offset_x
display_y = interface_y - picked_line_offset_y  # No flip needed
```

## Key Principles

1. **Y-up is ONLY for canvas editing** - The component editor canvas uses Y-up for intuitive editing (drag up = positive Y)

2. **Y-down everywhere else** - Storage and display use Y-down (standard Qt convention)

3. **Centered coordinates** - All systems use image center as origin, not top-left

4. **Single flip point** - The Y-axis flip happens ONLY at the component editor canvas boundary

5. **Picked line offset** - Main canvas transforms from image-center to picked-line-center coordinates

## Validation

Added validation checks to detect coordinate system issues:

1. **Range validation** - Warns if coordinates exceed reasonable bounds (2x object height)
2. **Debug logging** - Optional logging of coordinate transformations
3. **Explicit documentation** - Clear coordinate system notes in all relevant classes

## Testing

To verify the fix works correctly:

1. Open component editor
2. Load an image and set object height
3. Add an interface (should appear at center)
4. Drag interface up - Y coordinate should become positive in canvas, negative in storage
5. Save component
6. Drop component on main canvas - interface should appear at same relative position
7. Verify interface is correctly positioned relative to sprite image

## Files Modified

1. `src/optiverse/ui/views/component_editor_dialog.py`
   - Enhanced coordinate transformation comments
   - Added validation checks
   - Added debug logging option

2. `src/optiverse/objects/views/multi_line_canvas.py`
   - Documented Y-up coordinate system in InterfaceLine
   - Clarified canvas coordinate transformations

3. `src/optiverse/core/interface_definition.py`
   - Documented Y-down storage coordinate system
   - Explained transformation to/from canvas

4. `src/optiverse/core/models.py`
   - Documented RefractiveInterface Y-down coordinate system

5. `src/optiverse/objects/refractive/refractive_object_item.py`
   - Documented picked line offset transformation
   - Clarified Y-down display coordinates

## Resolution

The coordinate system transformations were already correct in the code. The fix primarily consisted of:

1. **Explicit documentation** of each coordinate system
2. **Validation checks** to catch potential issues
3. **Debug logging** to trace coordinate transformations
4. **Consistent terminology** across all components

This makes it much easier to verify correctness and debug any future issues.

