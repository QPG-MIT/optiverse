# Zemax Curved Surfaces and 3D→2D Projection

## Overview

This document explains how Zemax's 3D rotationally symmetric optical surfaces are mapped to OptiVerse's 2D cross-sectional representation, with full support for curved refractive interfaces.

## The Challenge: 3D Zemax → 2D OptiVerse

### Zemax Coordinate System (3D)

Zemax uses a 3D coordinate system with **rotational symmetry around the optical axis (z-axis)**:

```
    y
    ↑
    │     ╱
    │    ╱  Ray (in 3D)
    │   ╱
    │  ╱
    │ ╱
    │╱____________→ z (optical axis)
   ╱│
  ╱ │
 ╱  │
x   │
```

- **Z-axis**: Optical axis (beam propagation direction)
- **X-Y plane**: Perpendicular to optical axis
- **Surfaces**: Rotationally symmetric around Z
  - A sphere centered on the z-axis
  - Defined by radius of curvature and diameter

### OptiVerse Coordinate System (2D)

OptiVerse shows a **2D cross-section through the optical axis**:

```
    y (mm)
     ↑
 +6.35│    ╱│╲         ╱│╲         ╱│╲
      │   ╱ │ ╲       ╱ │ ╲       ╱ │ ╲
      │  │  │  │     │  │  │     │  │  │
      │  │  │  │     │  │  │     │  │  │
─────┼──│──┼──│─────│──┼──│─────│──┼──│───→ x (mm, optical axis)
 0.00 │  │  │  │     │  │  │     │  │  │
      │  │  │  │     │  │  │     │  │  │
      │   ╲ │ ╱       ╲ │ ╱       ╲ │ ╱
-6.35│    ╲│╱         ╲│╱         ╲│╱
      
      S1          S2          S3
    (convex)   (concave)   (concave)
```

- **X-axis**: Optical axis (corresponds to Zemax Z)
- **Y-axis**: Aperture height (cross-section through Zemax X-Y plane)
- **Interfaces**: Shown as curves (for 3D spherical surfaces projected to 2D)

## Surface Curvature: Zemax Convention

### Radius of Curvature

In Zemax, surfaces are defined by **curvature** (stored in CURV field):

```
curvature = 1 / radius

Example:
  CURV 1.499700E-2  →  R = 1 / 0.0149970 = 66.68 mm
  CURV -1.862197E-2 →  R = 1 / -0.018622 = -53.70 mm
```

### Sign Convention

**Critical**: Zemax uses a specific sign convention for radius:

- **Positive radius (R > 0)**: Center of curvature is **to the right** (downstream)
  - Surface is **convex** when viewed from the left
  - Light hits the "bulging" side first
  
- **Negative radius (R < 0)**: Center of curvature is **to the left** (upstream)
  - Surface is **concave** when viewed from the left
  - Light hits the "dented" side first

```
Positive Radius (Convex from left):
    
    Light →    ╱│╲
              ╱ │ ╲      Center of curvature
             │  │  │          is here →  ●
              ╲ │ ╱
               ╲│╱

Negative Radius (Concave from left):
    
    Light →     ╲│╱
                 │         ●  ← Center of curvature
                ╱│╲           is here (to the left)
```

## Surface Sag Calculation

**Sag** is the distance from the vertex (center point) to the edge of the surface along the optical axis.

### Formula

For a spherical surface with radius R and semi-diameter h:

```
sag = R - √(R² - h²)

where:
  R = |radius of curvature|
  h = half of the clear aperture diameter
```

### Example: AC254-100-B Surface 1

```
Surface 1 (Entry surface):
  Radius: R = 66.68 mm (positive, convex)
  Diameter: D = 12.7 mm
  Semi-diameter: h = 6.35 mm

Calculate sag:
  sag = 66.68 - √(66.68² - 6.35²)
      = 66.68 - √(4446.22 - 40.32)
      = 66.68 - √4405.90
      = 66.68 - 66.377
      = 0.303 mm

This means the center of the lens surface is 0.303mm 
further forward than a flat surface would be.
```

### Sign Convention for Sag

- **Positive sag**: Surface curves forward (convex from left)
- **Negative sag**: Surface curves backward (concave from left)

In our implementation:
```python
if radius > 0:
    sag = positive  # Convex
else:
    sag = -positive  # Concave (flip sign)
```

## 3D→2D Projection Strategy

### Approach: Cross-Sectional Slice

We project the 3D rotationally symmetric lens onto a 2D plane by taking a **vertical slice through the optical axis**:

```
3D View (looking down the optical axis):

         ╭─────────╮
        ╱           ╲
       │      ●      │  ← Circular aperture
        ╲           ╱     (rotationally symmetric)
         ╰─────────╯
         
         Diameter = 12.7mm


2D Cross-Section (side view):

    y=+6.35mm  ─────
                     │  ← Top edge of aperture
    y=0mm      ─────┼───  ← Optical axis
                     │
    y=-6.35mm  ─────     ← Bottom edge of aperture
```

### Interface Representation

Each Zemax surface becomes an `InterfaceDefinition` in OptiVerse:

```python
InterfaceDefinition(
    # Endpoints: show aperture extent in cross-section
    x1_mm=x_pos,              # Vertex x-position
    y1_mm=-half_diameter,      # Bottom edge
    x2_mm=x_pos,              # Same x (vertical line at vertex)
    y2_mm=+half_diameter,      # Top edge
    
    # Curvature info
    is_curved=True,
    radius_of_curvature_mm=66.68,  # Preserved from Zemax
    
    # Optical properties
    n1=1.000,  # Air
    n2=1.651,  # N-LAK22
)
```

### Visual Rendering (2D Canvas)

The interface can be rendered as:

1. **Simplified (current)**: Vertical line at vertex position
   ```
   │  ← Vertical line at x=0.00mm
   │     from y=-6.35 to y=+6.35
   │
   ```

2. **Realistic (future)**: Curved arc showing actual surface shape
   ```
    ╱│╲  ← Arc with radius R=66.68mm
   │ │ │    showing convex surface
    ╲│╱
   ```

For the realistic rendering, calculate points on the arc:
```python
def get_surface_points(interface: InterfaceDefinition, num_points: int = 20):
    """Generate points along curved surface for rendering."""
    if interface.is_flat():
        # Flat: just return endpoints
        return [(interface.x1_mm, interface.y1_mm),
                (interface.x2_mm, interface.y2_mm)]
    
    points = []
    y_min = interface.y1_mm
    y_max = interface.y2_mm
    
    for i in range(num_points):
        y = y_min + (y_max - y_min) * i / (num_points - 1)
        
        # Calculate sag at this y-position
        sag = interface.surface_sag_at_y(y)
        x = interface.x1_mm + sag  # Vertex x-position + sag
        
        points.append((x, y))
    
    return points
```

## Mapping Zemax Surfaces to OptiVerse Interfaces

### AC254-100-B Example

**Zemax Prescription:**
```
SURF 1:  CURV=0.01497,  R=+66.68mm,  t=4.0mm,   GLAS=N-LAK22,  D=12.7mm
SURF 2:  CURV=-0.01862, R=-53.70mm,  t=1.5mm,   GLAS=N-SF6HT,  D=12.7mm
SURF 3:  CURV=-0.00385, R=-259.41mm, t=97.09mm, GLAS=(Air),    D=12.7mm
```

**OptiVerse Interfaces:**

#### Interface 1: Air → N-LAK22 (Entry surface)
```python
InterfaceDefinition(
    x1_mm=0.00, y1_mm=-6.35,
    x2_mm=0.00, y2_mm=6.35,
    element_type='refractive_interface',
    name='S1: Air → N-LAK22 [R=+66.7mm]',
    n1=1.000, n2=1.651,
    is_curved=True,
    radius_of_curvature_mm=66.68
)
```

**Visualization:**
```
        ╱│╲         ← Convex surface
       │ │ │           R = +66.68 mm
      │  │  │          sag = 0.303 mm
       │ │ │
        ╲│╱

    x=0.00mm (vertex)
```

#### Interface 2: N-LAK22 → N-SF6HT (Cemented interface)
```python
InterfaceDefinition(
    x1_mm=4.00, y1_mm=-6.35,
    x2_mm=4.00, y2_mm=6.35,
    element_type='refractive_interface',
    name='S2: N-LAK22 → N-SF6HT [R=-53.7mm]',
    n1=1.651, n2=1.805,
    is_curved=True,
    radius_of_curvature_mm=-53.70
)
```

**Visualization:**
```
     ╲│╱         ← Concave surface
      │             R = -53.70 mm
     ╱│╲            sag = -0.377 mm

  x=4.00mm (vertex)
```

#### Interface 3: N-SF6HT → Air (Exit surface)
```python
InterfaceDefinition(
    x1_mm=5.50, y1_mm=-6.35,
    x2_mm=5.50, y2_mm=6.35,
    element_type='refractive_interface',
    name='S3: N-SF6HT → Air [R=-259.4mm]',
    n1=1.805, n2=1.000,
    is_curved=True,
    radius_of_curvature_mm=-259.41
)
```

**Visualization:**
```
     ╲│╱         ← Slightly concave
      │             R = -259.41 mm
     ╱│╲            sag = -0.078 mm (small!)

  x=5.50mm (vertex)
```

### Complete Cross-Section View

```
    y (mm)
 +6.35│     ╱│╲      ╲│╱      ╲│╱
      │    ╱ │ ╲      │        │
      │   │  │  │    ╱│╲      ╱│╲
      │   │  │  │     │        │
      │   │  N-LAK22 │ N-SF6HT│
      │   │  │  │     │        │
      │   │  n=1.651 │ n=1.805│
─────┼───│──┼──│─────┼────────┼─────→ x (mm)
 0.00 │   │  │  │     │        │
      │   │  │  │     │        │
      │   │  │  │    ╲│╱      ╲│╱
      │    ╲ │ ╱      │        │
-6.35│     ╲│╱      ╱│╲      ╱│╲
      
      x=0    x=4.0   x=5.5   x=102.5
      S1      S2      S3     Focal
    (convex) (concave) (weak  point
              cemented concave)
```

## Ray Tracing Through Curved Surfaces

### Flat Surface (Simple)

For flat surfaces, ray tracing is straightforward:
1. Ray hits interface at some point (x, y)
2. Surface normal is horizontal (perpendicular to vertical interface)
3. Apply Snell's law: n₁ sin θ₁ = n₂ sin θ₂

### Curved Surface (Advanced)

For curved surfaces, ray tracing requires:

1. **Ray-Sphere Intersection**
   - Find where ray intersects the spherical surface
   - Solve quadratic equation for intersection point

2. **Surface Normal at Intersection**
   - Normal is radial: points from surface point to center of curvature
   - For point P on surface and center C:
     ```
     normal = normalize(P - C)  # Convex (R > 0)
     normal = normalize(C - P)  # Concave (R < 0)
     ```

3. **Apply Snell's Law at Curved Surface**
   ```python
   def refract_at_curved_surface(
       ray_pos, ray_dir, 
       center_of_curv, radius,
       n1, n2
   ):
       # Find intersection point
       intersection = ray_sphere_intersection(
           ray_pos, ray_dir, 
           center_of_curv, radius
       )
       
       # Calculate normal at intersection
       normal = normalize(intersection - center_of_curv)
       
       # Apply Snell's law
       # n1 * sin(θ1) = n2 * sin(θ2)
       cos_theta1 = dot(-ray_dir, normal)
       sin_theta1_sq = 1 - cos_theta1**2
       sin_theta2_sq = (n1/n2)**2 * sin_theta1_sq
       
       if sin_theta2_sq > 1:
           # Total internal reflection
           return reflect(ray_dir, normal)
       
       # Refracted ray direction
       cos_theta2 = sqrt(1 - sin_theta2_sq)
       refracted = (n1/n2) * ray_dir + \
                   (n1/n2 * cos_theta1 - cos_theta2) * normal
       
       return normalize(refracted)
   ```

## Implementation Status

### ✅ Completed

1. **InterfaceDefinition Extended**
   - Added `is_curved: bool`
   - Added `radius_of_curvature_mm: float`
   - Added helper methods:
     - `center_of_curvature_mm()` - Calculate center position
     - `is_flat()` - Check if surface is flat
     - `surface_sag_at_y()` - Calculate sag at any y-coordinate

2. **ZemaxConverter Updated**
   - Extracts curvature from Zemax surfaces
   - Calculates radius: R = 1 / curvature
   - Creates InterfaceDefinition with curved properties
   - Calculates surface sag for documentation

3. **Demo Script Enhanced**
   - Shows curvature info (R value, sag)
   - Labels surfaces as convex/concave
   - Displays proper InterfaceDefinition code with curvature

### 🚧 To Do (Future)

4. **Visual Rendering**
   - Draw curved arcs in MultiLineCanvas
   - Show realistic lens shapes
   - Color-code by surface type (convex/concave)

5. **Ray Tracing Engine**
   - Implement ray-sphere intersection
   - Calculate surface normals at intersection
   - Apply Snell's law at curved surfaces
   - Handle total internal reflection

6. **Interactive Editing**
   - Edit radius of curvature in Component Editor
   - Visual feedback when dragging curved surfaces
   - Real-time ray trace updates

## Usage Example

### Parse Zemax File with Curved Surfaces

```bash
python examples/zemax_parse_simple.py AC254-100-B.zmx
```

**Output:**
```
Surface 1:
  Radius: 66.68 mm
  ...
  → OptiVerse Interface:
     Position: x=0.00 mm (vertex)
     Height: 12.70 mm (±6.35 mm from axis)
     Indices: n₁=1.000 (Air) → n₂=1.651 (N-LAK22)
     Curvature: R=66.68 mm
     Sag (edge): 0.303 mm (convex)
     Type: curved refractive_interface
```

### Programmatic Access

```python
from optiverse.services.zemax_parser import ZemaxParser
from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
from optiverse.services.glass_catalog import GlassCatalog

# Parse and convert
parser = ZemaxParser()
zemax_data = parser.parse("AC254-100-B.zmx")

converter = ZemaxToInterfaceConverter(GlassCatalog())
component = converter.convert(zemax_data)

# Access curved surface info
for interface in component.interfaces_v2:
    if interface.is_curved:
        print(f"{interface.name}")
        print(f"  Radius: {interface.radius_of_curvature_mm:.2f} mm")
        print(f"  Center: {interface.center_of_curvature_mm()}")
        
        # Calculate sag at edge
        half_height = interface.length_mm() / 2
        sag = interface.surface_sag_at_y(half_height)
        print(f"  Sag at edge: {sag:.3f} mm")
```

## Benefits of Curved Surface Support

1. **Physical Accuracy**: Preserves actual lens geometry from Zemax
2. **Realistic Visualization**: Can render true lens shapes (future)
3. **Precise Ray Tracing**: Apply Snell's law at correct angles
4. **Aberration Analysis**: Spherical and chromatic aberrations visible
5. **Design Validation**: Compare OptiVerse results with Zemax
6. **Education**: Shows real optical physics, not thin-lens approximations

## Summary

The curved surface implementation provides a **complete bridge** from Zemax's 3D rotationally symmetric surfaces to OptiVerse's 2D cross-sectional representation:

- ✅ **Curvature preserved**: Radius of curvature stored in InterfaceDefinition
- ✅ **Sign convention respected**: Positive/negative radius handled correctly
- ✅ **Sag calculated**: Surface deviation from flat computed accurately
- ✅ **3D→2D projection**: Cross-section through optical axis
- ✅ **Ready for rendering**: Helper methods for visualization
- ✅ **Ray tracing ready**: All geometry available for physics calculations

**Result**: Real lens designs from Zemax can now be fully represented in OptiVerse! 🔬✨

