# Sprite Rotation Fix - Final Solution

## Problem

When dragging optical components from the component library, the sprite (visual image) was rotated incorrectly, even though the optical axis appeared correct. 

**Initial attempt**: Using `RefractiveObjectItem` fixed sprite orientation but broke the optical axis drawing because interfaces were stored in image coordinates but drawn in the rotated sprite coordinate system.

**Final solution**: Pass interface coordinates from the component registry to simple items so they can create the correct reference line for sprite positioning.

## Root Cause

The issue occurred because:

1. **Component Registry Definitions**: The `ComponentRegistry` properly defines interface coordinates with correct orientations in the image:
   - Lenses: Vertical reference line (0, -15.25) to (0, 15.25) - 90° in image
   - Beamsplitters: Diagonal reference line (-12.7, -12.7) to (12.7, 12.7) - 45° in image
   - Mirrors: Vertical reference line (0, -24.7) to (0, 24.7) - 90° in image

2. **Simple Item Creation**: When components were dropped from the library, they were created as simple items (LensItem, MirrorItem, BeamsplitterItem) which **ignored** the interface coordinates.

3. **Incorrect Reference Line**: Simple items always created a horizontal reference line:
   ```python
   reference_line_mm = (-half_width, 0.0, half_width, 0.0)  # Always horizontal!
   ```

4. **Sprite Misalignment**: The ComponentSprite class rotates the image to align the reference line with the +X axis. When the reference line was always horizontal (0°) but the actual image content was at a different angle (e.g., 45° for beamsplitters), the sprite appeared rotated incorrectly.

## Solution

Modified the component creation logic to extract interface coordinates from the registry and pass them to simple items (LensItem, MirrorItem, BeamsplitterItem, etc.) via the params object. The simple items then use these coordinates as the reference line for `ComponentSprite`, ensuring proper sprite orientation while maintaining correct optical axis behavior.

**Key insight**: Simple items always create a **horizontal** reference line by default: `(-half_width, 0.0, half_width, 0.0)`. But component registry defines interfaces with their actual orientations (vertical for lenses, 45° for beamsplitters, etc.). By passing the first interface's coordinates as the reference line, the sprite is positioned correctly.

### Changes Made

1. **main_window.py - `on_drop_component` method**:
   - Extract reference line coordinates from first interface if available
   - Set `_reference_line_mm` attribute on params object before creating item
   - Applied to all simple item types: lens, mirror, beamsplitter, waveplate, dichroic, SLM

2. **graphics_view.py - `_make_ghost` method**:
   - Applied same logic to ghost preview items
   - Ensures drag preview shows correct rotation before dropping

3. **Simple Item Classes** (lens_item.py, mirror_item.py, beamsplitter_item.py, waveplate_item.py, dichroic_item.py, slm_item.py):
   - Modified `_maybe_attach_sprite` method to check for `_reference_line_mm` on params
   - If present, use those coordinates instead of default horizontal line
   - Falls back to horizontal line for items without interface data

### Code Changes

**In main_window.py on_drop_component**:
```python
# Extract reference line from first interface if available
reference_line_mm = None
if "interfaces" in rec and rec["interfaces"] and len(rec["interfaces"]) > 0:
    first_iface = rec["interfaces"][0]
    reference_line_mm = (
        float(first_iface.get("x1_mm", 0.0)),
        float(first_iface.get("y1_mm", 0.0)),
        float(first_iface.get("x2_mm", 0.0)),
        float(first_iface.get("y2_mm", 0.0)),
    )

# Pass reference line to params
if kind == "lens":
    params = LensParams(...)
    if reference_line_mm:
        params._reference_line_mm = reference_line_mm  # type: ignore
    item = LensItem(params)
# ... similar for other types ...
```

**In simple item classes (e.g., lens_item.py)**:
```python
def _maybe_attach_sprite(self):
    if self.params.image_path:
        # Check if component has a reference line from interface definition
        if hasattr(self.params, '_reference_line_mm'):
            reference_line_mm = self.params._reference_line_mm
        else:
            # Default: horizontal line
            half_width = self.params.object_height_mm / 2.0
            reference_line_mm = (-half_width, 0.0, half_width, 0.0)
        
        self._sprite = ComponentSprite(
            self.params.image_path,
            reference_line_mm,
            self.params.object_height_mm,
            self,
        )
```

This ensures components from the registry use proper interface-based sprite positioning, while maintaining correct optical axis behavior and backward compatibility.

## How It Works

1. **Reference Line from Interfaces**: The `RefractiveObjectItem` uses the first interface's coordinates as the reference line for sprite positioning.

2. **ComponentSprite Alignment**: The `ComponentSprite` class calculates the angle of the reference line in the image and rotates the sprite to align it with the +X axis in the parent's coordinate system.

3. **Item Rotation**: The item itself is then rotated by `angle_deg` to achieve the desired optical axis orientation in the scene.

4. **Correct Final Orientation**: The combination of sprite rotation (to align with +X) and item rotation (to achieve desired angle) results in correct sprite orientation.

## Example: Beamsplitter

Before fix:
- Image has beamsplitter at 45° 
- Reference line created: horizontal (0°)
- Sprite rotation: 0° (no rotation needed for horizontal line)
- Item rotation: 45°
- **Result**: Sprite at 45°, but image content also at 45°, final appears at 90° ❌

After fix:
- Image has beamsplitter at 45°
- Reference line from interface: diagonal 45° (-12.7, -12.7) to (12.7, 12.7)
- Sprite rotation: -45° (to align diagonal line with +X)
- Item rotation: 45°
- **Result**: Sprite properly aligned, beamsplitter appears at 45° ✓

## Testing

To verify the fix:
1. Open Optiverse
2. Drag components from the library (lenses, mirrors, beamsplitters, waveplates, etc.)
3. Verify that the sprite (image) is correctly oriented
4. Verify that the optical axis (drawn line) matches the sprite orientation

## Affected Components

All standard components in the ComponentRegistry with interface definitions:
- Standard Lens (1" mounted)
- Standard Lens (2" mounted)
- Standard Mirror (1")
- Standard Mirror (2")
- Standard Beamsplitter (50/50 1")
- PBS (2" Polarizing)
- Microscope Objective
- Dichroic Mirror (550nm cutoff)
- Quarter Waveplate (QWP)
- Half Waveplate (HWP)
- Spatial Light Modulator (SLM)

## Related Files

- `/src/optiverse/ui/views/main_window.py` - Component drop handler
- `/src/optiverse/objects/views/graphics_view.py` - Ghost preview handler
- `/src/optiverse/objects/component_sprite.py` - Sprite positioning and rotation
- `/src/optiverse/objects/component_registry.py` - Component definitions with interfaces
- `/src/optiverse/objects/refractive/refractive_object_item.py` - Interface-based component item

## Date

Fixed: October 30, 2025

