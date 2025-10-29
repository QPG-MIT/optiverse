# Refractive Objects Implementation

## Overview

This document describes the implementation of realistic refractive optical components with multiple interfaces, specifically designed to handle beam splitter cubes with proper physics simulation.

## Motivation

The original beam splitter implementation treated beam splitters as single-interface elements that ignored:
1. **Refraction at glass-air boundaries** - Rays entering/exiting glass should bend according to Snell's law
2. **Fresnel reflections** - Partial reflections occur at all glass-air interfaces (~4% for normal incidence)
3. **Path length changes** - Rays traveling through glass experience optical path differences
4. **Multiple surface interactions** - Real beam splitter cubes have 4 external surfaces + 1 internal coating

## Architecture

### 1. Data Models (`core/models.py`)

#### `RefractiveInterface`
Represents a single planar optical interface with:
- **Geometry**: Start/end points in local coordinates (x1, y1, x2, y2)
- **Refractive indices**: n1 (incident side), n2 (transmitted side)
- **Beam splitter properties**: Optional coating with T/R ratios
- **Polarization**: Optional PBS behavior

```python
@dataclass
class RefractiveInterface:
    x1_mm: float
    y1_mm: float
    x2_mm: float
    y2_mm: float
    n1: float = 1.0  # Air
    n2: float = 1.5  # Glass
    is_beam_splitter: bool = False
    split_T: float = 50.0
    split_R: float = 50.0
    is_polarizing: bool = False
    pbs_transmission_axis_deg: float = 0.0
```

#### `RefractiveObjectParams`
Represents a complete optical component with multiple interfaces:
- Position and rotation in scene
- List of interfaces (in local coordinates)
- Optional sprite image for rendering

```python
@dataclass
class RefractiveObjectParams:
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    object_height_mm: float = 80.0
    interfaces: List[RefractiveInterface] = None
    image_path: Optional[str] = None
    name: Optional[str] = None
```

### 2. Physics Implementation (`core/geometry.py`)

#### Snell's Law - `refract_vector_snell()`
Implements vector form of Snell's law:
```
n1 * sin(θ1) = n2 * sin(θ2)
```

Handles:
- **Normal refraction**: Bends ray according to index ratio
- **Total internal reflection**: When sin(θ2) > 1, reflects ray
- **Bidirectional**: Works for rays traveling either direction through interface

Returns: `(refracted_direction, is_total_reflection)`

#### Fresnel Equations - `fresnel_coefficients()`
Computes intensity reflection/transmission at dielectric interfaces:
```
R = reflectance (0 to 1)
T = transmittance (0 to 1)
R + T = 1 (energy conservation)
```

Averages s and p polarizations for unpolarized light:
- **Normal incidence**: R ≈ ((n1-n2)/(n1+n2))² ≈ 4% for air-glass
- **Grazing angles**: R → 1
- **Brewster angle**: R minimized for p-polarization

### 3. Ray Tracing Integration (`core/use_cases.py`)

The ray tracer handles refractive interfaces specially:

1. **Interface Detection**: Checks all refractive interfaces for ray intersections
2. **Beam Splitter Mode**: If `is_beam_splitter=True`, applies coating physics (no refraction)
3. **Refraction Mode**: Otherwise applies:
   - Snell's law for direction change
   - Fresnel equations for partial reflection
   - Creates both transmitted and reflected rays

```python
if kind == "refractive":
    iface = obj  # obj is the RefractiveInterface
    
    if iface.is_beam_splitter:
        # Beam splitter coating - no refraction
        # Apply T/R ratios (or PBS physics)
        ...
    else:
        # Regular interface - apply Snell + Fresnel
        V_refracted, is_TIR = refract_vector_snell(V, n_hat, n1, n2)
        R, T = fresnel_coefficients(theta, n1, n2)
        # Create transmitted and reflected rays
        ...
```

### 4. UI Components

#### `RefractiveObjectItem` (`objects/refractive/refractive_object_item.py`)
Qt graphics item for rendering and interacting with refractive objects:
- **Rendering**: Draws all interfaces with color coding
  - Blue: Refractive interfaces
  - Teal: Beam splitter coatings
  - Gray: Same-index interfaces
- **Editing**: Dialog for adding/editing/removing interfaces
- **Scene Integration**: Transforms local coordinates to scene coordinates

#### Interface Editor
Each interface can be edited with:
- Geometry (start/end points in local coords)
- Refractive indices (n1, n2)
- Beam splitter properties (if applicable)
- PBS settings (if polarizing)

### 5. Factory Functions (`objects/refractive/beamsplitter_cube_factory.py`)

#### `create_beamsplitter_cube_50_50()`
Creates a realistic beam splitter cube with 5 interfaces:

**Interface Layout** (for 45° rotation):
```
              Top (exit)
                 |
    Left --- Diagonal --- Right
    (entrance)  (BS)    (exit)
                 |
              Bottom (entrance)
```

**Interfaces**:
1. **Left edge**: Air → Glass (entrance from left)
2. **Bottom edge**: Air → Glass (entrance from below)
3. **Diagonal coating**: Glass → Glass with beam splitting
4. **Right edge**: Glass → Air (exit to right)
5. **Top edge**: Glass → Air (exit upward)

**Parameters**:
- `size_mm`: Cube side length (25.4mm for 1")
- `n_glass`: Refractive index (1.517 for BK7)
- `split_ratio`: T/R percentage (50/50 typical)
- `is_polarizing`: Enable PBS mode
- `pbs_axis_deg`: PBS transmission axis

#### `create_pbs_cube()`
Specialized PBS cube with polarization-dependent splitting.

#### `create_prism()`
Simple triangular prism for dispersion/refraction demos.

## Physical Effects Captured

### 1. Refraction (Snell's Law)
- Ray bending at glass-air boundaries
- Path length changes through glass
- Beam displacement for non-perpendicular incidence

### 2. Fresnel Reflections
- ~4% reflection at each air-glass interface
- Multiple ghost reflections in beam splitter cubes
- Intensity-correct beam splitting

### 3. Total Internal Reflection
- Occurs when ray exits glass at grazing angles
- Critical angle: θc = arcsin(n_air / n_glass) ≈ 42° for BK7

### 4. Beam Splitter Coating
- Wavelength-independent splitting (unlike dichroics)
- Optional polarization dependence (PBS)
- Proper intensity distribution

## Usage Example

### Creating a Realistic Beam Splitter Cube

```python
from optiverse.objects.refractive import RefractiveObjectItem
from optiverse.objects.refractive.beamsplitter_cube_factory import create_beamsplitter_cube_50_50

# Create a 1-inch 50/50 beam splitter cube
params = create_beamsplitter_cube_50_50(
    size_mm=25.4,          # 1 inch
    center_x=0.0,
    center_y=0.0,
    rotation_deg=45.0,     # Typical orientation
    n_glass=1.517,         # BK7 glass
    split_ratio=50.0,      # 50/50 split
    is_polarizing=False,   # Regular BS (not PBS)
    name="BS Cube 50/50"
)

# Create the graphics item
bs_cube = RefractiveObjectItem(params)

# Add to scene
scene.addItem(bs_cube)
```

### Creating a PBS Cube

```python
from optiverse.objects.refractive.beamsplitter_cube_factory import create_pbs_cube

params = create_pbs_cube(
    size_mm=50.8,          # 2 inches
    center_x=0.0,
    center_y=0.0,
    rotation_deg=45.0,
    pbs_axis_deg=0.0,      # Horizontal transmission
    n_glass=1.517
)

pbs_cube = RefractiveObjectItem(params)
scene.addItem(pbs_cube)
```

### Custom Refractive Object

```python
from optiverse.core.models import RefractiveObjectParams, RefractiveInterface

# Create custom interfaces
interfaces = [
    RefractiveInterface(
        x1_mm=-10, y1_mm=0,
        x2_mm=10, y2_mm=0,
        n1=1.0, n2=1.5  # Air to glass
    ),
    # Add more interfaces...
]

params = RefractiveObjectParams(
    x_mm=0, y_mm=0,
    angle_deg=0,
    interfaces=interfaces
)

custom = RefractiveObjectItem(params)
```

## Component Editor Integration

The component editor can be extended to support refractive objects:

1. **New component type**: "refractive_object"
2. **Interface list editor**: Add/edit/delete interfaces
3. **Visual feedback**: Show interfaces overlaid on component image
4. **Library storage**: Save refractive components to library

## Performance Considerations

### Ray Tracing Performance
- Each interface is checked independently for intersections
- Beam splitter cubes have 5 interfaces → 5× intersection tests
- Use spatial acceleration structures for complex scenes with many refractive objects

### Optimization Strategies
1. **Bounding box culling**: Skip interfaces outside ray's path
2. **Interface grouping**: Group interfaces by parent object for faster rejection
3. **Numba JIT**: Geometry calculations are JIT-compiled for speed

## Limitations and Future Work

### Current Limitations
1. **Polarization**: Simplified model (Fresnel for average of s/p)
2. **Dispersion**: Single refractive index (no wavelength dependence)
3. **Absorption**: No material absorption modeling
4. **Coatings**: Simplified beam splitter coating model

### Future Enhancements
1. **Full polarization**: Separate s and p Fresnel coefficients
2. **Dispersion**: Sellmeier equation for n(λ)
3. **Anti-reflection coatings**: Model AR coating effects
4. **Curved surfaces**: Extend to lenses, spherical mirrors
5. **Gradient index**: Support GRIN media

## Testing

### Test Cases
1. **Normal incidence**: No deflection at perpendicular incidence
2. **45° incidence**: Verify Snell's law angles
3. **Total internal reflection**: Test critical angle
4. **Fresnel reflections**: Verify ~4% reflection at air-glass
5. **Beam displacement**: Verify lateral offset through parallel plate
6. **Energy conservation**: Sum of all output intensities equals input

### Example Test
```python
def test_beam_splitter_cube_path_deviation():
    """Test that ray path changes when passing through BS cube at angle."""
    # Create beam splitter cube
    bs = create_beamsplitter_cube_50_50(size_mm=25.4, n_glass=1.5)
    
    # Trace horizontal ray through center
    # Ray should experience:
    # 1. Refraction at left surface
    # 2. Splitting at diagonal
    # 3. Refraction at exit surfaces
    # 4. Lateral displacement (beam walk)
    
    # Verify output positions differ from straight-through case
    ...
```

## Summary

This implementation provides a realistic physics model for multi-interface optical components:

✅ **Snell's law** - Proper refraction at all interfaces
✅ **Fresnel equations** - Realistic partial reflections  
✅ **Multiple surfaces** - Handle complex geometries
✅ **Beam splitter cubes** - Correct 4-surface + coating model
✅ **PBS support** - Polarization-dependent splitting
✅ **Extensible** - Easy to create custom refractive objects

The modular design allows users to:
- Create realistic beam splitter cubes with proper physics
- Build custom refractive components (prisms, windows, etc.)
- Add multiple interfaces to any component via the editor
- Achieve physically accurate ray tracing with refraction

This addresses the original limitation where beam splitters ignored surface refraction and path length effects.

