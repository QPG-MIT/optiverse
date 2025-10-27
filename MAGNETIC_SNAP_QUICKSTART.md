# Magnetic Snap - Quick Start Guide

## What is Magnetic Snap?

Magnetic snap automatically aligns components to each other as you drag them, just like in PowerPoint or other design tools. When components get close to alignment, they "snap" into place with visual guide lines.

## How to Use

### 1. **Enable/Disable Magnetic Snap**
   - Go to **View** menu → **Magnetic snap** (checked = enabled)
   - Keyboard shortcut: *(none assigned yet)*
   - Default: **Enabled**

### 2. **Drag Components to Align**
   - Click and drag any optical component (lens, mirror, etc.)
   - When you get close to another component, you'll see:
     - **Magenta dashed guide lines** appear
     - Component position "snaps" to align perfectly
   - Release mouse to keep the alignment

### 3. **Guide Line Colors**
   - **Horizontal line** (—): Y-axis alignment (same height)
   - **Vertical line** (|): X-axis alignment (same horizontal position)
   - Both lines can appear simultaneously for perfect center-to-center alignment

## Examples

### Example 1: Align Two Lenses Horizontally
```
1. Add Lens 1 at position (0, 0)
2. Add Lens 2 at position (200, 15)
3. Drag Lens 2 - when Y gets close to 0:
   → Magenta horizontal line appears
   → Lens 2 snaps to Y=0
   → Both lenses now perfectly aligned horizontally
```

### Example 2: Create Grid Layout
```
1. Place reference lens at (0, 0)
2. Add lens at (100, 5)
   → Snaps to (100, 0) - horizontal alignment
3. Add lens at (5, 100)
   → Snaps to (0, 100) - vertical alignment
4. Add lens at (95, 105)
   → Snaps to (100, 100) - both axes aligned
   → Perfect grid layout!
```

## Tips

- **Snap Tolerance**: Components snap when within ~10 pixels of alignment
- **Works with Zoom**: Snap tolerance automatically adjusts to zoom level
- **Multiple Targets**: Snaps to the *closest* aligned component
- **Grid Snap Compatible**: Works alongside "Snap to mm grid"
- **Setting Persists**: Your preference is saved between sessions

## Troubleshooting

### Snap Not Working?
1. Check View menu - is "Magnetic snap" checked?
2. Are components close enough? (within ~10 pixels)
3. Try dragging slower for easier control

### Guide Lines Not Showing?
1. Ensure magnetic snap is enabled
2. Check that you're dragging a component (not panning)
3. Verify there are other components to snap to

### Too Sensitive / Not Sensitive Enough?
Currently fixed at 10 pixels. Future versions may add UI control.

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Toggle magnetic snap | *(none)* |
| Temporary disable | *(none)* |

*Shortcuts can be customized in future versions*

## Technical Details

- **Snap Type**: Center-to-center alignment
- **Tolerance**: 10 pixels (view coordinates)
- **Performance**: Minimal impact, only active during drag
- **Guide Color**: Magenta (#FF00FF)
- **Persistence**: Saved via QSettings

## See Also

- `MAGNETIC_SNAP_IMPLEMENTATION.md` - Full technical documentation
- `test_magnetic_snap_manual.py` - Manual test script
- View menu → "Snap to mm grid" - Complementary grid snapping

