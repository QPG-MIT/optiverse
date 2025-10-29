# Coordinate System: Normalized to Object Height

## Summary

The component editor coordinate system has been updated to normalize the Y-axis to the object height.

### What Changed

**Before**: 
- Coordinate scale determined by first interface length
- `mm_per_px = object_height_mm / first_interface_length_mm`
- Changing object height didn't scale coordinates uniformly

**After**:
- Coordinate scale determined by image height
- `mm_per_px = object_height_mm / image_height_px`
- Y-axis: 0mm (top) → object_height_mm (bottom)
- X-axis: 0mm (left) → (object_height_mm × aspect_ratio) (right)

## Benefits

### 1. Intuitive Scaling
The object_height parameter now directly defines the Y-axis range:
- Set object_height = 25mm → Y goes from 0 to 25mm
- Set object_height = 50mm → Y goes from 0 to 50mm

### 2. Independent of Interface Positions
The coordinate system no longer depends on where the first interface is placed. This eliminates the circular dependency where:
- Interface positions depend on mm_per_px
- mm_per_px depends on interface positions

### 3. Proportional Scaling
Changing object_height scales all coordinates uniformly:
- Double object_height → all interfaces appear at same relative positions
- No need to recalibrate individual interfaces

### 4. Standard Convention
Matches standard image coordinate systems:
- (0, 0) at top-left
- Y increases downward
- Direct mapping: image height → physical height

## Technical Implementation

### Conversion Formula

```python
# Given:
# - Image size: W × H pixels
# - Object height: OH mm

# Calculate scale factor:
mm_per_px = OH / H

# Conversions:
x_mm = x_px * mm_per_px
y_mm = y_px * mm_per_px

x_px = x_mm / mm_per_px
y_px = y_mm / mm_per_px
```

### Example Calculation

**Image**: 1200×800 pixels  
**Object Height**: 30mm

```python
mm_per_px = 30 / 800 = 0.0375 mm/px

# Coordinate ranges:
Y: 0 to 30mm (covers full image height)
X: 0 to 45mm (1200 × 0.0375 = 45mm)

# Center point (pixels):
center_px = (600px, 400px)

# Center point (mm):
center_mm = (22.5mm, 15mm)
```

### Code Changes

**Files Modified**:
1. `src/optiverse/ui/views/component_editor_dialog.py`
   - `_sync_interfaces_to_canvas()`: Changed to use `mm_per_px = object_height / H`
   - `_on_canvas_lines_changed()`: Updated coordinate conversion

2. `src/optiverse/ui/widgets/interface_tree_panel.py`
   - `_add_interface()`: Updated default positions for new coordinate system

3. `src/optiverse/core/component_migration.py`
   - `_migrate_simple_component()`: Updated legacy conversion
   - `convert_v2_to_legacy()`: Updated reverse conversion
   - `_migrate_refractive_object()`: Updated pixel-to-mm conversion

## User Impact

### For New Components
- Add interface → appears at expected position
- Coordinates directly relate to physical dimensions
- Y coordinate = distance from top in mm

### For Existing Components
- Automatically migrated on load
- Coordinates converted from old to new system
- No user action required
- Visual appearance may shift slightly due to new scaling

### Workflow Example

**Creating a Lens Component**:
1. Load lens image (1000×800 pixels)
2. Set object height: 25mm
3. Add lens interface
4. Position endpoints:
   - Top edge: Y = 5mm
   - Bottom edge: Y = 20mm
   - Center: Y = 12.5mm
5. Interface length: 15mm (bottom - top)

The coordinate values directly represent physical distances from the top of the image.

## Migration Notes

### Automatic Migration
Legacy components stored with old coordinate system are automatically converted:
- Old system used center-based or first-interface-based scaling
- New system uses image-height-based scaling
- Conversion happens transparently on component load

### Compatibility
- **Forward Compatible**: New components work with updated code
- **Backward Compatible**: Old components automatically migrate
- **No Data Loss**: All geometric information preserved

### Testing Migration
To verify migration:
1. Load old component
2. Check interface positions match visual appearance
3. Verify Y coordinates range from ~0 to ~object_height
4. Save component (saves in new format)

## Future Enhancements

Potential improvements enabled by this system:

1. **Aspect Ratio Lock**: 
   - Option to maintain X/Y aspect ratio when changing object_height
   - Useful for components with square images

2. **Multiple Reference Dimensions**:
   - Object width as additional parameter
   - Non-uniform scaling for wide/tall components

3. **Grid Overlay**:
   - Display mm grid on canvas
   - Snap to grid at physical distances (1mm, 5mm, etc.)

4. **Dimension Display**:
   - Show ruler along image edges
   - Mark 0mm, 5mm, 10mm, etc. positions

## Summary

The normalized coordinate system makes the component editor more intuitive by directly linking the Y-axis range to the object height parameter. This eliminates scaling ambiguities and makes coordinate values directly interpretable as physical distances.

**Key Takeaway**: Y = 0mm at top, Y = object_height_mm at bottom. Simple and predictable.

