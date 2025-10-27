# Coordinate Editing and Dragging Feature

## Overview

Added comprehensive coordinate editing capabilities to the Component Editor, allowing users to both drag points visually and manually edit coordinates numerically.

## Features Implemented

### 1. Draggable Points in ImageCanvas

**File**: `src/optiverse/objects/views/image_canvas.py`

#### New Capabilities:
- **Visual Dragging**: Click and drag points to reposition them
- **Hover Feedback**: Cursor changes to open/closed hand when hovering over points
- **Visual Highlighting**: Points highlight when hovered or dragged
- **Smooth Updates**: Real-time updates during dragging

#### Technical Details:
- Added `_dragging_point` and `_hover_point` state tracking
- Implemented `mouseMoveEvent()` for drag handling
- Implemented `mouseReleaseEvent()` for drag completion
- Added `_get_point_at_screen_pos()` for hit detection (8px threshold)
- Added `_screen_to_image_coords()` for coordinate conversion
- Added `pointsChanged` signal for external synchronization
- Enabled mouse tracking for hover effects

#### Visual Feedback:
- Point 1 (blue): RGB(0, 180, 255)
- Point 2 (orange): RGB(255, 80, 0)
- Normal state: 5px radius, alpha 100
- Active state (hover/drag): 6px radius, alpha 150
- Cursor states: Arrow → Open Hand → Closed Hand

### 2. Manual Coordinate Editing in Component Editor

**File**: `src/optiverse/ui/views/component_editor_dialog.py`

#### New UI Controls:
Four spinboxes added to the side dock panel:
- **Point 1 X**: X coordinate of first point (px)
- **Point 1 Y**: Y coordinate of first point (px)
- **Point 2 X**: X coordinate of second point (px)
- **Point 2 Y**: Y coordinate of second point (px)

#### Configuration:
- Range: 0 to 1,000,000 pixels
- Precision: 2 decimal places
- Suffix: " px" for clarity

#### Bidirectional Synchronization:
- **Canvas → Spinboxes**: Updates when points are clicked or dragged
- **Spinboxes → Canvas**: Updates canvas when values are manually changed
- Signal blocking prevents infinite update loops

#### New Methods:
- `_on_manual_point_changed()`: Handles spinbox value changes
- Enhanced `_update_derived_labels()`: Updates spinboxes when canvas changes

## User Workflow

### Dragging Points:
1. Load an image in the Component Editor
2. Click two points to define the optical line
3. Hover over a point - cursor changes to open hand
4. Click and drag to reposition - cursor changes to closed hand
5. Release to finalize position

### Manual Editing:
1. Load an image and place points (or drag them)
2. View coordinates in the "Line Points (px)" section
3. Edit X/Y values using the spinboxes
4. Canvas updates immediately as you type

### Combined Usage:
- Use dragging for quick, visual adjustments
- Use spinboxes for precise, numerical placement
- Both methods stay synchronized at all times

## Implementation Notes

### Coordinate System:
- Image coordinates: (0, 0) at top-left
- Coordinates clamped to image bounds during dragging
- Sub-pixel precision supported (float values)

### Signal Flow:
```
User Action → Canvas Update → pointsChanged signal → 
  _update_derived_labels() → Spinbox Update (no recursion)

Spinbox Change → _on_manual_point_changed() → 
  Canvas Update → _update_derived_labels() → 
  Spinbox Update (blocked to prevent recursion)
```

### Performance:
- Real-time updates during dragging
- No lag or flicker
- Efficient coordinate conversion using cached scale factor

## Testing

### Manual Testing Checklist:
- [x] Drag point 1
- [x] Drag point 2
- [x] Hover cursor feedback works
- [x] Visual highlighting during hover
- [x] Visual highlighting during drag
- [x] Coordinates update in spinboxes during drag
- [x] Edit spinbox → canvas updates
- [x] Edit canvas → spinbox updates
- [x] No infinite loops
- [x] Coordinates stay within image bounds
- [x] Works with different image sizes

### Verification Script:
Run `verify_coord_editing.py` to verify all features are present and functional.

## Files Modified

1. `src/optiverse/objects/views/image_canvas.py`
   - Added drag and hover functionality
   - Added helper methods for coordinate conversion
   - Enhanced paint event for visual feedback

2. `src/optiverse/ui/views/component_editor_dialog.py`
   - Added coordinate spinboxes to UI
   - Added bidirectional synchronization
   - Connected canvas signals to update handlers

3. `tests/ui/test_component_editor_coords.py` (new)
   - Comprehensive test suite for new features
   - Tests drag, hover, sync, and coordinate conversion

## Backward Compatibility

All changes are backward compatible:
- Existing point-clicking behavior preserved
- Right-click to clear points still works
- No changes to saved component format
- No changes to public API

## Future Enhancements (Optional)

Potential improvements for future development:
- Snap-to-grid for precise placement
- Undo/redo for point moves
- Keyboard arrow keys for fine-tuning
- Copy/paste point coordinates
- Visual grid overlay
- Measurement display during drag

