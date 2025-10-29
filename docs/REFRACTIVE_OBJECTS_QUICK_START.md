# Refractive Objects - Quick Start Guide

## What's New?

Optiverse now supports realistic beam splitter cubes and custom refractive objects with proper physics simulation including:

- ✅ **Snell's Law** - Ray refraction at all glass-air interfaces
- ✅ **Fresnel Reflections** - Realistic ~4% reflections at surfaces
- ✅ **Path Length Changes** - Beam displacement through glass
- ✅ **Multiple Interfaces** - 4 external surfaces + 1 internal coating for BS cubes
- ✅ **Total Internal Reflection** - Critical angle effects
- ✅ **PBS Support** - Polarization-dependent beam splitting

## Creating a Beam Splitter Cube (Programmatic)

```python
from optiverse.objects.refractive import RefractiveObjectItem
from optiverse.objects.refractive.beamsplitter_cube_factory import (
    create_beamsplitter_cube_50_50,
    create_pbs_cube
)

# Example 1: Standard 50/50 Beam Splitter Cube (1 inch)
bs_params = create_beamsplitter_cube_50_50(
    size_mm=25.4,          # 1 inch cube
    center_x=0.0,
    center_y=0.0,
    rotation_deg=45.0,     # Standard orientation
    n_glass=1.517,         # BK7 glass
    split_ratio=50.0,      # 50/50 split
    is_polarizing=False,
    name="BS Cube 50/50"
)

# Create the graphics item and add to scene
bs_cube = RefractiveObjectItem(bs_params)
scene.addItem(bs_cube)

# Example 2: Polarizing Beam Splitter (PBS) Cube (2 inches)
pbs_params = create_pbs_cube(
    size_mm=50.8,          # 2 inch cube
    center_x=100.0,
    center_y=0.0,
    rotation_deg=45.0,
    pbs_axis_deg=0.0,      # Horizontal transmission axis
    n_glass=1.517,
    name="PBS Cube 2\""
)

pbs_cube = RefractiveObjectItem(pbs_params)
scene.addItem(pbs_cube)
```

## Creating a Custom Refractive Object

```python
from optiverse.core.models import RefractiveObjectParams, RefractiveInterface

# Define interfaces (in local coordinates)
interfaces = []

# Interface 1: Left surface (air to glass)
interfaces.append(RefractiveInterface(
    x1_mm=-10.0, y1_mm=-10.0,
    x2_mm=-10.0, y2_mm=+10.0,
    n1=1.0,      # Air
    n2=1.517,    # BK7 glass
    is_beam_splitter=False
))

# Interface 2: Right surface (glass to air)
interfaces.append(RefractiveInterface(
    x1_mm=+10.0, y1_mm=-10.0,
    x2_mm=+10.0, y2_mm=+10.0,
    n1=1.517,    # Glass
    n2=1.0,      # Air
    is_beam_splitter=False
))

# Create the refractive object
params = RefractiveObjectParams(
    x_mm=0.0,
    y_mm=0.0,
    angle_deg=0.0,
    object_height_mm=20.0,
    interfaces=interfaces,
    name="Glass Window"
)

window = RefractiveObjectItem(params)
scene.addItem(window)
```

## Beam Splitter Cube Physics

### Interface Structure
A typical beam splitter cube at 45° has 5 interfaces:

```
           Interface 5: Top Exit
           (Glass → Air)
                |
                |
Interface 1 ----+---- Interface 4
Left Entry      |      Right Exit
(Air → Glass)   |     (Glass → Air)
                |
          Interface 3
        Diagonal Coating
    (Glass → Glass + BS coating)
                |
                |
        Interface 2: Bottom Entry
          (Air → Glass)
```

### Ray Behavior

**Transmitted Ray** (entering from left):
1. Refracts at left surface (air→glass)
2. Travels through glass
3. Hits diagonal coating → 50% transmitted
4. Travels through glass
5. Refracts at right surface (glass→air)
6. **Result**: Lateral beam displacement + slight angular deviation

**Reflected Ray**:
1-2. Same as transmitted
3. Hits diagonal coating → 50% reflected
4. Travels through glass  
5. Refracts at top surface (glass→air)
6. **Result**: 90° deflection + path length difference

## Key Parameters

### `RefractiveInterface`
- **x1_mm, y1_mm, x2_mm, y2_mm**: Interface endpoints (local coordinates)
- **n1**: Refractive index on "left" side (side normal points away from)
- **n2**: Refractive index on "right" side (side normal points toward)
- **is_beam_splitter**: True for coated splitting interfaces
- **split_T, split_R**: Transmission/reflection percentages (if BS)
- **is_polarizing**: Enable PBS mode
- **pbs_transmission_axis_deg**: PBS axis angle (absolute, in lab frame)

### Refractive Indices
- **Air**: n = 1.0
- **BK7 Glass**: n = 1.517 (at 589nm)
- **Fused Silica**: n = 1.458
- **SF11 (dense flint)**: n = 1.785

### Critical Angles
Total internal reflection occurs when light exits from denser to less dense medium at angles beyond:

θ_critical = arcsin(n₂/n₁)

- **Glass (1.517) → Air (1.0)**: θ_c ≈ 41.3°
- **Glass (1.5) → Air**: θ_c ≈ 41.8°

## Interactive Editing

### Editing Interfaces
1. Double-click refractive object
2. Dialog shows position, rotation, and interface list
3. Click "Edit Selected" to modify interface properties:
   - Geometry (start/end points)
   - Refractive indices (n1, n2)
   - Beam splitter settings
   - PBS properties

### Adding Interfaces
1. Click "Add Interface" in editor dialog
2. Default interface created at object center
3. Edit geometry and optical properties
4. Interface appears immediately on canvas

### Visual Feedback
Interfaces are color-coded:
- **Blue (2px)**: Regular refractive interface (n1 ≠ n2)
- **Teal (3px)**: Beam splitter coating
- **Gray (1px)**: Same-index interface (n1 = n2)
- **Dashed line**: Surface normal direction

## Example: Beam Displacement Experiment

```python
# Create a glass plate (parallel surfaces)
plate = RefractiveObjectParams(
    x_mm=0, y_mm=0,
    angle_deg=30.0,  # Tilted plate
    interfaces=[
        RefractiveInterface(  # Entry surface
            x1_mm=-20, y1_mm=-5,
            x2_mm=20, y2_mm=-5,
            n1=1.0, n2=1.5
        ),
        RefractiveInterface(  # Exit surface (parallel)
            x1_mm=-20, y1_mm=5,
            x2_mm=20, y2_mm=5,
            n1=1.5, n2=1.0
        )
    ]
)

plate_item = RefractiveObjectItem(plate)
scene.addItem(plate_item)

# Trace a ray through the plate
# Observe: Ray exits parallel to input, but laterally displaced
```

## Tips and Tricks

### 1. Beam Splitter Cube Orientation
- **45° rotation** (standard): Input from left/bottom, outputs to right/top
- **135° rotation**: Input from right/bottom, outputs to left/top
- Adjust rotation to fit your optical layout

### 2. PBS Axis Configuration
- `pbs_axis_deg` is in **absolute lab coordinates**, not relative to cube
- 0° = horizontal transmission axis
- 90° = vertical transmission axis  
- For horizontal input, 0° transmits H-pol, reflects V-pol

### 3. Multiple Beam Splitter Cubes
- Cubes can be cascaded for complex splitting
- Each cube contributes its own Fresnel losses
- Watch for ghost reflections from multiple surfaces

### 4. Glass Selection
- Higher index → larger refraction angles
- Higher index → more Fresnel reflection
- BK7 (n=1.517) is standard for most optics

### 5. Performance
- Each interface adds intersection tests to ray tracing
- For complex scenes, use fewer interfaces where possible
- Beam splitter cubes (5 interfaces) are well-optimized

## Comparison: Old vs New Beam Splitters

### Old Implementation (Single Interface)
```python
BeamsplitterItem(params)
# - Single line segment
# - No refraction
# - No Fresnel reflections
# - No path length changes
# - Idealized splitting only
```

### New Implementation (Refractive Object)
```python
RefractiveObjectItem(create_beamsplitter_cube_50_50(...))
# - 5 interfaces (4 surfaces + 1 coating)
# - Full Snell's law refraction
# - Fresnel reflections at all surfaces
# - Accurate path lengths through glass
# - Realistic beam displacement
# - Optional polarization dependence
```

## Common Issues and Solutions

### Issue: Rays not hitting interfaces
**Solution**: Check interface coordinates in local space. Use the editor to verify geometry visually.

### Issue: Unexpected reflections
**Explanation**: Fresnel reflections (~4%) occur at all glass-air boundaries. This is physical and expected.

### Issue: Ray disappears in glass
**Check**: 
1. Are exit surfaces defined?
2. Is total internal reflection occurring? (Check angles)
3. Is intensity below threshold? (Multiple reflections reduce intensity)

### Issue: PBS not splitting correctly
**Check**:
1. `is_polarizing=True` on coating interface
2. `pbs_axis_deg` set correctly (absolute angle)
3. Input light has defined polarization state

## Next Steps

- **Experiment**: Create beam splitter cubes and trace rays through them
- **Compare**: Note the beam displacement vs. old beam splitter model
- **Extend**: Try creating prisms, windows, and other refractive elements
- **Read**: See `REFRACTIVE_OBJECTS_IMPLEMENTATION.md` for full technical details

## Quick Reference

### Factory Functions
- `create_beamsplitter_cube_50_50()` - Standard BS cube
- `create_pbs_cube()` - Polarizing BS cube
- `create_prism()` - Triangular prism

### Classes
- `RefractiveObjectItem` - Graphics item for refractive components
- `RefractiveInterface` - Single optical interface
- `RefractiveObjectParams` - Complete component parameters

### Key Physics
- **Snell's law**: n₁ sin θ₁ = n₂ sin θ₂
- **Fresnel (normal)**: R ≈ ((n₁-n₂)/(n₁+n₂))²
- **Critical angle**: θc = arcsin(n₂/n₁)

Enjoy realistic beam splitter physics! 🔬✨

