# Component Editor - Adding Refractive Interfaces

## Overview

The component editor now fully supports creating **refractive objects** with multiple optical interfaces. This allows you to design realistic beam splitter cubes, prisms, and custom refractive components directly in the UI.

## Quick Start

### 1. Open Component Editor

From the main window menu: **File → Component Editor** (or press the Component Editor toolbar button)

### 2. Select Refractive Object Type

1. In the **Component Settings** panel, find the **Type** dropdown
2. Select **"refractive_object"** from the list
3. The interface management UI will appear

### 3. Load an Image (Optional)

- Click **"Open Image…"** to load a picture of your component
- Or paste an image from clipboard
- The image serves as a visual reference

### 4. Create a Beam Splitter Cube (Easy Way)

**Using the BS Cube Preset:**

1. Click **"BS Cube Preset"** button
2. A dialog appears with these options:
   - **Cube Size**: Enter the side length (e.g., 25.4mm for 1 inch)
   - **Glass Index**: Refractive index (default: 1.517 for BK7 glass)
   - **Split T%**: Transmission percentage (50% for 50/50 split)
   - **Polarizing Beam Splitter (PBS)**: Check for PBS mode
   - **PBS Axis**: Transmission axis angle (if PBS mode)
3. Click **OK**
4. The editor creates 5 interfaces automatically:
   - Interface 1: Left edge (air → glass)
   - Interface 2: Bottom edge (air → glass)
   - Interface 3: Diagonal coating (beam splitter)
   - Interface 4: Right edge (glass → air)
   - Interface 5: Top edge (glass → air)

### 5. Manually Add/Edit Interfaces

**Adding an Interface:**

1. Click **"Add"** button
2. Interface editor dialog opens
3. Configure the interface:

**Geometry:**
- **Start X, Start Y**: First endpoint (in mm, local coordinates)
- **End X, End Y**: Second endpoint
- Coordinates are relative to component center (0,0)

**Refractive Indices:**
- **n1**: Index on "left" side (where ray comes from)
- **n2**: Index on "right" side (where ray goes to)
- Common values:
  - Air: n = 1.0
  - BK7 Glass: n = 1.517
  - Fused Silica: n = 1.458

**Beam Splitter Coating (Optional):**
- ☑ **Beam Splitter Coating**: Check if this interface has a BS coating
- **Transmission %**: Percentage transmitted
- **Reflection %**: Percentage reflected (auto-calculated)
- ☑ **Polarizing (PBS)**: Check for polarization-dependent splitting
- **PBS Axis**: Transmission axis angle (lab frame, absolute)

**Editing an Interface:**

1. Select interface from list
2. Click **"Edit"** button
3. Modify properties
4. Click **OK** to save

**Deleting an Interface:**

1. Select interface from list
2. Click **"Delete"** button
3. Confirm deletion

### 6. Set Component Properties

- **Name**: Give your component a descriptive name
- **Object Height**: Physical size of the component (in mm)
- **Notes**: Optional description

### 7. Save to Library

1. Click **"Save Component"** in toolbar
2. Component is saved to the component library
3. It will appear in the **Library** panel on the right

## Examples

### Example 1: Simple Glass Window

A parallel-sided glass plate (demonstrates beam displacement):

```
1. Select "refractive_object" type
2. Click "Add" to add Interface 1:
   - Start: (-20, -2) mm
   - End: (20, -2) mm
   - n1: 1.0 (air)
   - n2: 1.5 (glass)
   
3. Click "Add" to add Interface 2:
   - Start: (-20, 2) mm
   - End: (20, 2) mm
   - n1: 1.5 (glass)
   - n2: 1.0 (air)
   
4. Save as "Glass Window 4mm"
```

Result: Ray enters at bottom, refracts, travels through glass, refracts again at top, exits parallel but laterally displaced.

### Example 2: 50/50 Beam Splitter Cube

Using the preset (easiest):

```
1. Select "refractive_object"
2. Click "BS Cube Preset"
3. Set:
   - Cube Size: 25.4 mm (1 inch)
   - Glass Index: 1.517 (BK7)
   - Split T%: 50.0
   - PBS: Unchecked
4. Click OK
5. Save as "BS Cube 50/50 1-inch"
```

Result: Full 5-interface beam splitter cube with proper refraction at all surfaces.

### Example 3: PBS Cube

Creating a polarizing beam splitter:

```
1. Select "refractive_object"
2. Click "BS Cube Preset"
3. Set:
   - Cube Size: 50.8 mm (2 inches)
   - Glass Index: 1.517
   - Split T%: 50.0 (not used for PBS)
   - PBS: ☑ Checked
   - PBS Axis: 0.0° (horizontal)
4. Click OK
5. Save as "PBS Cube 2-inch"
```

Result: PBS cube that transmits p-polarization (horizontal) and reflects s-polarization (vertical).

### Example 4: Triangular Prism

Manual interface creation:

```
1. Select "refractive_object"
2. Add Interface 1 (Bottom):
   - Start: (-20, -10)
   - End: (20, -10)
   - n1: 1.0, n2: 1.5
   
3. Add Interface 2 (Right hypotenuse):
   - Start: (20, -10)
   - End: (0, 10)
   - n1: 1.0, n2: 1.5
   
4. Add Interface 3 (Left hypotenuse):
   - Start: (0, 10)
   - End: (-20, -10)
   - n1: 1.0, n2: 1.5
   
5. Save as "45-45-90 Prism"
```

Result: Triangular prism for dispersion and refraction experiments.

## Interface List Display

The interface list shows a summary of each interface:

- **"Interface N:"** - Interface number
- **"BS"** - Appears if beam splitter coating
- **"n=X.XXX→Y.YYY"** - Refractive indices (from → to)
- **"T/R=XX/YY"** - Split ratios (if beam splitter)

Example displays:
```
Interface 1: n=1.000→1.517
Interface 2: n=1.000→1.517
Interface 3: BS n=1.517→1.517 T/R=50/50
Interface 4: n=1.517→1.000
Interface 5: n=1.517→1.000
```

## Coordinate System

**Local Coordinates:**
- Origin (0,0) is at the component center
- X-axis: Horizontal (positive = right)
- Y-axis: Vertical (positive = up)
- All interface points are specified in mm

**When placed in scene:**
- Local coordinates transform according to component position and rotation
- Interface normals adjust automatically

## Tips & Best Practices

### 1. Interface Ordering
- Add interfaces in the order a ray would encounter them
- Not strictly necessary (ray tracer handles any order) but easier to understand

### 2. Normal Direction
- Normal points from "left" (n1) to "right" (n2)
- Ray traveling with normal: n1 → n2
- Ray traveling against normal: n2 → n1
- The system handles both directions automatically

### 3. Beam Splitter Coatings
- Set **n1 = n2** for beam splitter interface (both sides are glass)
- Enable **Beam Splitter Coating** checkbox
- Coating doesn't refract (stays on beam splitter interface)
- External surfaces still refract normally

### 4. PBS Configuration
- Only works on beam splitter interfaces
- PBS axis is in **lab frame** (absolute angle)
- 0° = horizontal transmission axis
- 90° = vertical transmission axis

### 5. Object Height
- Set this to the physical size of your component
- For beam splitter cube: set to diagonal length (~1.414 × side)
- Used for sizing when placing in scene

### 6. Testing Your Component
After saving:
1. Open main window
2. Drag component from library to scene
3. Add a light source
4. Trace rays to see refraction behavior
5. Adjust interfaces if needed

## Troubleshooting

### Issue: Rays disappear inside component
**Solution:** Make sure you have exit surfaces defined. Every entry surface needs a corresponding exit surface.

### Issue: Interface list is empty after creating BS cube preset
**Possible cause:** You're not in "refractive_object" mode.
**Solution:** Set Type to "refractive_object" first, then click BS Cube Preset.

### Issue: Can't see interfaces in scene
**Explanation:** Interfaces only show when component is selected in main window. They're rendered as:
- Blue lines: Regular refractive interfaces
- Teal lines: Beam splitter coatings
- Dashed normals: Surface normal direction

### Issue: PBS not working
**Check:**
1. Is interface marked as "Beam Splitter Coating"? ✓
2. Is "Polarizing (PBS)" checkbox enabled? ✓
3. Is PBS axis set correctly? ✓
4. Does input light have defined polarization? ✓

### Issue: Wrong refraction direction
**Solution:** Swap n1 and n2 values. The direction matters:
- n1 < n2: Ray bends toward normal (entering denser medium)
- n1 > n2: Ray bends away from normal (entering less dense medium)

## Advanced Usage

### Custom Refractive Indices

Different glasses have different indices:
- **BK7**: 1.517 (common crown glass)
- **Fused Silica**: 1.458 (UV applications)
- **SF11**: 1.785 (dense flint glass)
- **Sapphire**: 1.768
- **Diamond**: 2.417

### Wavelength Dispersion

Currently, the refractive index is fixed (no dispersion). Future versions may support:
- Wavelength-dependent n(λ) using Sellmeier equations
- Chromatic aberration visualization
- Prism spectrum separation

### Complex Geometries

You can create any polygonal shape:
- Multi-surface optics
- Compound lenses
- Dichroic filters with substrates
- Windowed vacuum chambers

Just add interfaces for each surface!

### Export/Import

Components saved to the library are stored as JSON files in:
```
~/.optiverse/library/components/
```

You can:
- Share component files with colleagues
- Version control your component library
- Edit JSON manually for batch creation

## Keyboard Shortcuts

In Component Editor:
- **Ctrl+V**: Paste image or component JSON
- **Ctrl+C**: Copy component as JSON
- **Ctrl+S**: Save component (if supported)

## Next Steps

1. **Try the BS Cube Preset** - Easiest way to get started
2. **Experiment with interface parameters** - See how n1/n2 affects refraction
3. **Create custom components** - Build your own optical elements
4. **Test in main window** - Trace rays through your components
5. **Share your library** - Export components for others

## See Also

- `REFRACTIVE_OBJECTS_IMPLEMENTATION.md` - Technical details
- `REFRACTIVE_OBJECTS_QUICK_START.md` - Programmatic usage
- Main application documentation

---

**Have fun creating realistic optical components!** 🔬✨

