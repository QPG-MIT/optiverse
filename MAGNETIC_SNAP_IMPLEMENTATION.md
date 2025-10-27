# Magnetic Snap Feature Implementation

## Overview
Implemented a PowerPoint-style magnetic snap feature that automatically aligns components to each other when dragging, with visual feedback through alignment guide lines.

## Features Implemented

### 1. **Core Snap Logic** (`src/optiverse/core/snap_helper.py`)
- `SnapHelper` class that calculates snap positions
- **Center-to-center alignment**: Components snap when their centers align
- **Configurable tolerance**: Default 10 pixels (adjustable)
- **Multi-axis snapping**: Snaps on both X and Y axes independently
- **View-aware**: Handles zoom levels correctly

```python
snap_result = snap_helper.calculate_snap(
    target_position,
    moving_item,
    scene,
    view
)
```

### 2. **Visual Feedback** (`src/optiverse/widgets/graphics_view.py`)
- **Magenta alignment guide lines** that appear during snap
- Horizontal guides for Y-axis alignment
- Vertical guides for X-axis alignment
- Guides automatically clear when snap ends or is disabled

### 3. **UI Integration** (`src/optiverse/ui/views/main_window.py`)
- **Menu toggle**: View → Magnetic snap (checkable)
- **Automatic application**: Applies during drag operations
- **Real-time feedback**: Shows guides as you drag
- **Independent from grid snap**: Works alongside "Snap to mm grid"

### 4. **Settings Persistence**
- Uses `SettingsService` to remember user preference
- Saves to system registry/config automatically
- Loads saved state on application startup

### 5. **Test Coverage**
- **Unit tests**: `tests/core/test_snap_helper.py`
  - Snap calculations
  - Tolerance handling
  - Multi-axis alignment
  - View transforms
  
- **Integration tests**: `tests/ui/test_magnetic_snap.py`
  - Toggle functionality
  - Component alignment
  - Guide display
  - Persistence

- **Manual test**: `test_magnetic_snap_manual.py`

## How It Works

### User Workflow
1. **Enable/Disable**: View menu → Magnetic snap (checked by default)
2. **Drag components**: Click and drag any optical component
3. **Watch for guides**: Magenta dashed lines appear when near alignment
4. **Feel the snap**: Component position adjusts to align with others
5. **Release**: Guides disappear, component stays aligned

### Technical Flow
1. User starts dragging a component (mouse press)
2. On mouse move, `eventFilter` captures the event
3. If magnetic snap is enabled:
   - `SnapHelper.calculate_snap()` finds nearby components
   - Calculates closest alignment points within tolerance
   - Returns snapped position and guide line data
4. Position is applied to component
5. Guide lines are rendered in `drawForeground()`
6. On mouse release, guides are cleared

### Snap Algorithm
```
For each axis (X and Y):
  1. Find all other components in scene
  2. Calculate distance from moving component center to each target center
  3. If distance < tolerance:
     - Record as snap candidate
  4. Choose closest candidate
  5. Return snapped coordinate and guide line info
```

## Key Design Decisions

### 1. **Center-to-Center Only (Phase 1)**
Currently implements center-to-center alignment. Edge-to-edge and custom alignment points can be added later.

### 2. **Visual Style**
- Magenta color: High contrast, distinct from other UI elements
- Dashed lines: Clearly temporary/guide nature
- Cosmetic pen: Stays same width regardless of zoom

### 3. **Tolerance**
- 10 pixels in view coordinates (scales with zoom)
- Reasonable default for most use cases
- Can be adjusted via `SnapHelper(tolerance_px=...)`

### 4. **Performance**
- Efficient O(n) scan of components
- Only active during drag operations
- No continuous polling

### 5. **Integration with Existing Systems**
- Works alongside grid snap (independent toggles)
- Integrates with undo/redo system
- Uses existing event filter infrastructure

## Files Modified

### New Files
- `src/optiverse/core/snap_helper.py` - Core snap logic
- `tests/core/test_snap_helper.py` - Unit tests
- `tests/ui/test_magnetic_snap.py` - Integration tests
- `test_magnetic_snap_manual.py` - Manual testing script
- `MAGNETIC_SNAP_IMPLEMENTATION.md` - This document

### Modified Files
- `src/optiverse/widgets/graphics_view.py`
  - Added `_snap_guides` state
  - Added `set_snap_guides()` and `clear_snap_guides()` methods
  - Modified `drawForeground()` to render guides

- `src/optiverse/ui/views/main_window.py`
  - Imported `SnapHelper` and `SettingsService`
  - Added `magnetic_snap` state variable
  - Created `SnapHelper` instance
  - Added `act_magnetic_snap` menu action
  - Added `_toggle_magnetic_snap()` handler
  - Modified `eventFilter()` to apply snap on mouse move
  - Added settings persistence

## Usage Examples

### Basic Usage (User)
```
1. Open Optiverse
2. Add several components (lenses, mirrors, etc.)
3. Drag one component near another
4. See magenta guides and feel the snap
5. Release to keep alignment
```

### Toggle On/Off
```
View Menu → Magnetic snap (check/uncheck)
```

### Programmatic Usage
```python
# Create snap helper
snap_helper = SnapHelper(tolerance_px=15.0)

# Calculate snap during drag
result = snap_helper.calculate_snap(
    current_position,
    item_being_moved,
    scene,
    view
)

if result.snapped:
    item.setPos(result.position)
    view.set_snap_guides(result.guide_lines)
else:
    view.clear_snap_guides()
```

## Future Enhancements

### Possible Extensions
1. **Edge-to-edge alignment**: Snap component edges together
2. **Spacing guides**: Maintain equal spacing between components
3. **Smart guides**: Show distances and angles (like Sketch/Figma)
4. **Custom snap points**: Let users define alignment points
5. **Snap to angles**: Align rotation angles (e.g., 0°, 45°, 90°)
6. **Snap tolerance adjustment**: UI control for tolerance
7. **Visual style options**: Color/style customization
8. **Multiple component snap**: Align multiple selected items at once

## Testing Instructions

### Automated Tests
```bash
# Run unit tests
pytest tests/core/test_snap_helper.py -v

# Run integration tests
pytest tests/ui/test_magnetic_snap.py -v

# Run all tests
pytest tests/ -v
```

### Manual Testing
```bash
python test_magnetic_snap_manual.py
```

**What to test:**
1. ✅ Drag component near another - should snap and show guides
2. ✅ Drag component far from others - should not snap
3. ✅ Toggle magnetic snap off - should not snap
4. ✅ Toggle magnetic snap on - should snap again
5. ✅ Restart application - setting should persist
6. ✅ Zoom in/out - snap tolerance should scale appropriately
7. ✅ Multiple components - should snap to closest

## Performance Notes

- **Minimal overhead**: Only active during drag operations
- **O(n) complexity**: Scans all components once per move event
- **Optimized rendering**: Guides use cosmetic pens (no transform)
- **Event throttling**: Qt's natural event throttling prevents excessive calculations

## Compatibility

- **Qt Version**: PyQt6 6.5+
- **Python**: 3.10+
- **Platform**: Windows, macOS, Linux (tested on Windows)
- **Dependencies**: No additional dependencies required

## Known Limitations

1. **Center-only snap**: Only snaps component centers (by design for v1)
2. **No grouped alignment**: Doesn't align multiple selected items together
3. **No angular snap**: Doesn't snap rotation angles
4. **Fixed tolerance**: Tolerance is hardcoded (can be adjusted in code)

## Summary

Successfully implemented a complete PowerPoint-style magnetic snap feature with:
- ✅ Core snap calculation engine
- ✅ Visual alignment guides
- ✅ UI toggle control
- ✅ Settings persistence
- ✅ Comprehensive tests
- ✅ Full integration with existing systems

The feature is production-ready and follows the existing codebase patterns and conventions.

