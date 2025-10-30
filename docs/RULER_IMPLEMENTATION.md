# Ruler Implementation - Photoshop-Style Rulers

## Overview

The component editor now includes Photoshop-style rulers with triangular cursor position indicators. This feature helps users visualize the exact position and size of optical components in millimeters.

## Features

### Visual Elements

1. **Horizontal Ruler** (top)
   - Shows X-axis measurements
   - Red triangular indicator tracks horizontal cursor position
   - Tick marks at regular intervals
   - Labels showing measurements in mm

2. **Vertical Ruler** (left)
   - Shows Y-axis measurements  
   - Red triangular indicator tracks vertical cursor position
   - Tick marks at regular intervals
   - Rotated labels showing measurements in mm

3. **Corner Widget** (top-left)
   - Gray corner piece at the intersection of rulers
   - Completes the ruler frame

### Coordinate System

The rulers use the same centered coordinate system as the canvas:
- **Origin (0, 0)**: Center of the image
- **X-axis**: Increases to the right (positive) and left (negative)
- **Y-axis**: Increases upward (positive) and downward (negative)
- **Units**: Millimeters (mm)

### Dynamic Scaling

The rulers automatically adjust to the canvas zoom level:
- Tick spacing adapts to maintain readability
- Scale factor updates in real-time as you resize the window
- Measurements remain accurate regardless of zoom

## Architecture

### Components

#### 1. `RulerWidget` (`src/optiverse/ui/widgets/ruler_widget.py`)

Base class for horizontal and vertical rulers.

**Key Methods:**
- `set_cursor_position(pos_mm)`: Update the red triangle position
- `set_view_parameters(scale, offset, range_mm)`: Update ruler scaling
- `paintEvent()`: Draw ruler markings and cursor indicator

**Features:**
- Automatic tick interval calculation
- Major and minor tick marks
- Centered coordinate system support
- Triangular cursor indicator

#### 2. `CanvasWithRulers` (`src/optiverse/ui/widgets/ruler_widget.py`)

Container widget that wraps the canvas with rulers.

**Structure:**
```
┌──────┬─────────────────────────┐
│Corner│   Horizontal Ruler      │
├──────┼─────────────────────────┤
│  V   │                         │
│  e   │      Canvas             │
│  r   │                         │
│  t   │                         │
│  i   │                         │
│  c   │                         │
│  a   │                         │
│  l   │                         │
│      │                         │
│  R   │                         │
│  u   │                         │
│  l   │                         │
│  e   │                         │
│  r   │                         │
└──────┴─────────────────────────┘
```

**Key Features:**
- Grid layout with rulers and canvas
- Event filtering to track mouse movement
- Periodic updates for ruler parameters
- Automatic hiding of indicators when mouse leaves canvas

#### 3. `MultiLineCanvas` Updates (`src/optiverse/objects/views/multi_line_canvas.py`)

Added helper methods to support rulers:

**New Methods:**
- `_screen_to_mm_coords(screen_pos)`: Convert screen coordinates to mm
- `_get_ruler_view_params()`: Provide ruler scaling parameters

**Return Values from `_get_ruler_view_params()`:**
```python
{
    'h_scale': float,      # Horizontal scale (screen pixels per mm)
    'h_offset': float,     # Horizontal offset (where 0mm is on screen)
    'h_range': (min, max), # Horizontal visible range in mm
    'v_scale': float,      # Vertical scale (screen pixels per mm)
    'v_offset': float,     # Vertical offset (where 0mm is on screen)
    'v_range': (min, max), # Vertical visible range in mm
    'show_mm': bool        # Whether to show mm units
}
```

### Integration

The component editor (`ComponentEditor`) now uses `CanvasWithRulers`:

```python
# Before:
self.canvas = MultiLineCanvas()
self.setCentralWidget(self.canvas)

# After:
self.canvas = MultiLineCanvas()
self.canvas_with_rulers = CanvasWithRulers(self.canvas)
self.setCentralWidget(self.canvas_with_rulers)
```

This maintains backward compatibility - all existing code that accesses `self.canvas` continues to work.

## Usage

### For Users

1. **Open the Component Editor**
   - File → Component Editor (in main application)
   - Or run directly: `python examples/ruler_demo.py`

2. **Load an Image**
   - Drag and drop an image onto the canvas
   - Or use File → Open Image
   - Or paste from clipboard (Ctrl+V)

3. **Set Object Height**
   - Enter the physical height of your component in mm
   - This calibrates the coordinate system

4. **See Rulers in Action**
   - Move your mouse over the canvas
   - Red triangular indicators on both rulers track your position
   - Read precise X and Y coordinates in mm

### For Developers

#### Creating a Ruler-Wrapped Canvas

```python
from optiverse.objects.views import MultiLineCanvas
from optiverse.ui.widgets.ruler_widget import CanvasWithRulers

# Create canvas
canvas = MultiLineCanvas()

# Wrap with rulers
canvas_with_rulers = CanvasWithRulers(canvas)

# Use as central widget
window.setCentralWidget(canvas_with_rulers)
```

#### Customizing Ruler Behavior

```python
# Access ruler widgets
h_ruler = canvas_with_rulers.h_ruler
v_ruler = canvas_with_rulers.v_ruler

# Change units (mm vs pixels)
h_ruler.set_show_mm(False)  # Show pixels instead of mm
v_ruler.set_show_mm(False)

# Manually set cursor position
h_ruler.set_cursor_position(10.5)  # 10.5 mm
v_ruler.set_cursor_position(-5.2)  # -5.2 mm

# Hide cursor indicators
h_ruler.set_cursor_position(None)
v_ruler.set_cursor_position(None)
```

#### Implementing Ruler Support in Custom Canvases

Your canvas widget needs two methods:

```python
def _screen_to_mm_coords(self, screen_pos: QtCore.QPoint) -> Tuple[float, float]:
    """Convert screen coordinates to mm coordinates."""
    # Your conversion logic here
    return (x_mm, y_mm)

def _get_ruler_view_params(self) -> dict:
    """Return ruler view parameters."""
    return {
        'h_scale': screen_pixels_per_mm,
        'h_offset': center_x_screen_pixels,
        'h_range': (min_mm, max_mm),
        'v_scale': screen_pixels_per_mm,
        'v_offset': center_y_screen_pixels,
        'v_range': (min_mm, max_mm),
        'show_mm': True
    }
```

## Visual Design

### Colors

- **Ruler Background**: `#E8E8E8` (light gray)
- **Ruler Border**: `#999` (medium gray)
- **Corner Widget**: `#D0D0D0` (slightly darker gray)
- **Tick Marks**: `#333` (dark gray)
- **Cursor Indicator**: `#FF4444` (red fill), `#CC0000` (red border)

### Dimensions

- **Ruler Height/Width**: 25 pixels
- **Major Tick Length**: 20 pixels (horizontal) / 20 pixels (vertical)
- **Minor Tick Length**: 5 pixels
- **Cursor Triangle**: 7 pixels wide, 5 pixels from edge
- **Font Size**: 8pt for labels

### Tick Spacing

The ruler automatically calculates tick spacing to maintain readability:
- Target: ~75 pixels between major ticks
- Intervals are rounded to "nice" values: 1, 2, 5, 10, 20, 50, 100, etc.
- Minor ticks: 5 subdivisions between major ticks

## Implementation Details

### Coordinate Conversion

The rulers handle the canvas's centered coordinate system:

1. **Screen to MM Conversion**:
   ```python
   # Get image rectangle and scale
   img_rect = canvas._target_rect()
   scale_fit = canvas._scale_fit
   mm_per_px = canvas._mm_per_px
   
   # Convert screen to image pixels (centered)
   img_center_x = img_rect.width() / (2 * scale_fit)
   img_center_y = img_rect.height() / (2 * scale_fit)
   x_img_px = (screen_x - img_rect.x()) / scale_fit - img_center_x
   y_img_px = img_center_y - (screen_y - img_rect.y()) / scale_fit
   
   # Convert to mm
   x_mm = x_img_px * mm_per_px
   y_mm = y_img_px * mm_per_px
   ```

2. **MM to Screen Conversion** (for drawing):
   ```python
   # For horizontal ruler
   screen_x = offset + mm * scale
   
   # For vertical ruler (Y-axis flipped)
   screen_y = offset - mm * scale
   ```

### Update Strategy

The system uses two update mechanisms:

1. **Mouse Movement** (event-driven)
   - Canvas mouse move events are filtered
   - Cursor position immediately updates rulers
   - Provides real-time feedback

2. **View Parameters** (periodic)
   - Timer updates ruler parameters every 100ms
   - Handles window resizing, zoom changes
   - Ensures rulers stay synchronized

### Performance Considerations

- Rulers use efficient QPainter operations
- Only visible tick marks are drawn
- Update frequency is throttled (100ms timer)
- Mouse tracking is lightweight (event filtering)

## Testing

### Manual Testing

1. **Load the Demo**:
   ```bash
   python examples/ruler_demo.py
   ```

2. **Test Scenarios**:
   - Load an image and verify rulers appear
   - Move mouse and verify triangular indicators follow
   - Resize window and verify rulers rescale
   - Change object height and verify measurements update
   - Test with different image sizes
   - Test with images having different aspect ratios

### Verification Checklist

- ✓ Rulers appear when image is loaded
- ✓ Rulers hidden when no image is loaded
- ✓ Red triangles follow mouse cursor
- ✓ Triangles disappear when mouse leaves canvas
- ✓ Measurements are in millimeters
- ✓ Zero point (0,0) is at image center
- ✓ Tick spacing is readable at all zoom levels
- ✓ Rulers resize with window
- ✓ Rulers update when object height changes
- ✓ Performance is smooth (no lag)

## Future Enhancements

### Possible Improvements

1. **Unit Switching**
   - Toggle between mm, cm, inches, pixels
   - Context menu or keyboard shortcut

2. **Zoom Indicator**
   - Show current zoom percentage
   - Display in corner widget

3. **Grid Overlay**
   - Optional grid lines at major tick intervals
   - Helps with alignment

4. **Ruler Origin Control**
   - Allow user to set custom origin point
   - Reset to center button

5. **Measurement Tools**
   - Click-and-drag distance measurement
   - Show length/angle in tooltip

6. **Ruler Preferences**
   - Customizable colors
   - Adjustable ruler size
   - Hide/show rulers toggle

## Troubleshooting

### Rulers Not Appearing

**Problem**: Rulers don't show up in the component editor.

**Solutions**:
1. Make sure an image is loaded
2. Check that `CanvasWithRulers` is used as central widget
3. Verify imports are correct

### Cursor Indicators Not Moving

**Problem**: Red triangles don't follow the mouse.

**Solutions**:
1. Ensure `_screen_to_mm_coords()` is implemented
2. Check that event filter is installed
3. Verify mouse tracking is enabled on canvas

### Wrong Measurements

**Problem**: Ruler measurements don't match expected values.

**Solutions**:
1. Verify object height is set correctly
2. Check `_get_ruler_view_params()` implementation
3. Ensure coordinate system matches (centered, Y-up)

### Performance Issues

**Problem**: Rulers cause lag or slow updates.

**Solutions**:
1. Increase timer interval (default 100ms)
2. Reduce tick mark density
3. Optimize coordinate conversion

## Related Files

- **Implementation**: `src/optiverse/ui/widgets/ruler_widget.py`
- **Canvas Updates**: `src/optiverse/objects/views/multi_line_canvas.py`
- **Component Editor**: `src/optiverse/ui/views/component_editor_dialog.py`
- **Demo**: `examples/ruler_demo.py`
- **Tests**: (to be added)

## References

- **Photoshop Rulers**: Inspiration for the design
- **PyQt6 Documentation**: QPainter, QWidget, event filtering
- **Coordinate Systems**: Centered coordinates with Y-up axis

## Changelog

### Version 1.0 (Initial Implementation)

- ✓ Horizontal and vertical rulers with tick marks
- ✓ Red triangular cursor position indicators
- ✓ Centered coordinate system (0,0 at image center)
- ✓ Automatic tick spacing calculation
- ✓ Real-time mouse tracking
- ✓ Integration with component editor
- ✓ Support for mm measurements
- ✓ Dynamic scaling with zoom

---

**Last Updated**: October 30, 2025
**Author**: AI Assistant
**Status**: Implemented and Ready for Use

