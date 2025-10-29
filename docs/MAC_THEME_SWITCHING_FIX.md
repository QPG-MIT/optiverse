# Mac Theme Switching Fix

## Summary

Fixed multiple issues with theme switching on macOS, particularly when the system is in dark mode but the application is set to light mode.

## Issues Fixed

### 1. ✅ Toolbar Text Color in Bright Mode
**Problem**: Toolbar button text was white (invisible) in bright mode, but only on Mac.

**Root Cause**: The light mode stylesheet didn't explicitly set text color for toolbar buttons, causing macOS to default to white text.

**Solution**: 
- Added explicit `color: black;` to all `QToolBar QToolButton` states in the light stylesheet
- Added `color: palette(window-text);` to custom toolbar stylesheets for automatic theme adaptation

**Files Modified**:
- `src/optiverse/app/main.py` - Light stylesheet
- `src/optiverse/ui/views/main_window.py` - Main toolbar
- `src/optiverse/ui/views/component_editor_dialog.py` - Component editor toolbar

### 2. ✅ Incomplete Theme Switching
**Problem**: When toggling dark mode off while macOS system is in dark mode, many UI components remained dark.

**Root Cause**: macOS Qt applies system-level styling that conflicts with application stylesheets. Simply changing the stylesheet wasn't sufficient to override the system's dark mode styling.

**Solution**: Comprehensive theme application with three-part strategy:

#### A. Explicit Palette Management
Created explicit color palettes for both themes to override system colors:

```python
def apply_theme(dark_mode: bool):
    palette = QtGui.QPalette()
    
    if dark_mode:
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#1a1c21"))
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("white"))
        # ... (11 color roles set)
    else:
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("white"))
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("black"))
        # ... (11 color roles set)
    
    app.setPalette(palette)
```

Color roles set:
- Window (background)
- WindowText (foreground text)
- Base (input fields background)
- AlternateBase (alternating row colors)
- Text (general text)
- Button (button background)
- ButtonText (button text)
- BrightText (emphasized text)
- Link (hyperlinks)
- Highlight (selection background)
- HighlightedText (selection text)

#### B. Complete Stylesheet
Enhanced light mode stylesheet to match dark mode completeness:

Added to light stylesheet:
- `QMainWindow, QWidget` - Base window and widget colors
- `QMenu` and `QMenu::item:selected` - Menu styling

#### C. Force Style Refresh
Added widget refresh loop to force complete style recomputation:

```python
for widget in app.allWidgets():
    widget.style().unpolish(widget)  # Remove old styling
    widget.style().polish(widget)    # Reapply new styling
    widget.update()                  # Trigger repaint
```

This ensures every widget recomputes its style with the new palette and stylesheet.

## How It Works Now

### Theme Toggle Flow

1. User clicks **View → Dark mode** checkbox
2. `_toggle_dark_mode()` is called in `MainWindow`
3. Canvas dark mode is set: `self.view.set_dark_mode(on)`
4. Preference is saved: `self.settings_service.set_value("dark_mode", on)`
5. **`apply_theme(on)` is called**, which:
   - Creates appropriate color palette
   - Applies palette to override system colors
   - Sets comprehensive stylesheet
   - Forces all widgets to refresh styling
6. Library tree is repopulated to update colors

### macOS System Dark Mode Independence

The application now properly overrides macOS system styling:

| macOS System Mode | App Dark Mode Setting | Result |
|-------------------|----------------------|---------|
| Dark | ✓ Enabled | Dark theme ✅ |
| Dark | ✗ Disabled | Light theme ✅ (Fixed!) |
| Light | ✓ Enabled | Dark theme ✅ |
| Light | ✗ Disabled | Light theme ✅ |

## Technical Details

### Why Multiple Approaches Are Needed

On macOS, Qt6 uses three layers of styling:
1. **System native styling** - Respects macOS appearance settings
2. **Application palette** - Qt's color scheme
3. **Application stylesheet** - CSS-like styling

When only the stylesheet is changed, macOS native styling can leak through. The fix addresses all three layers:
- Palette overrides system colors
- Stylesheet provides comprehensive CSS rules
- Polish/unpolish cycle forces complete style recomputation

### Platform-Specific Behavior

The `palette(window-text)` approach in toolbar styling is particularly elegant:
- Automatically uses the palette we set
- Works consistently across all platforms
- No hardcoded color values in local stylesheets

## Testing

Test these scenarios on macOS:

1. **System Dark + App Dark**: Should be consistently dark ✅
2. **System Dark + App Light**: Should be consistently light (was broken, now fixed) ✅
3. **System Light + App Dark**: Should be consistently dark ✅
4. **System Light + App Light**: Should be consistently light ✅

Verify these elements switch properly:
- Main window background
- Dock panels (Library, Interfaces)
- Toolbar text
- Tree widget items
- Dialog backgrounds (Component Editor, Collaboration, etc.)
- Buttons and inputs
- Menu colors
- Scrollbars

## Files Changed

1. `src/optiverse/app/main.py`:
   - Enhanced `apply_theme()` with palette management and widget refresh
   - Added explicit colors to light mode stylesheet
   - Fixed toolbar button text colors

2. `src/optiverse/ui/views/main_window.py`:
   - Added `color: palette(window-text);` to toolbar stylesheet

3. `src/optiverse/ui/views/component_editor_dialog.py`:
   - Added toolbar text color styling for Mac compatibility

## Future Improvements

If theme issues persist on specific widgets:
1. Check if the widget is created after theme application
2. Ensure it's not using hardcoded styles that override the theme
3. Consider emitting a theme change signal that widgets can listen to
4. Use `palette()` colors instead of hardcoded colors where possible

