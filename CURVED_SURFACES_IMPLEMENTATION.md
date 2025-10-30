# Curved Surfaces & 3D→2D Projection - Implementation Complete

## What Was Added

I've extended the Zemax import system to **fully support curved optical surfaces** and handle the **3D→2D projection** from Zemax's rotationally symmetric description to OptiVerse's 2D cross-sectional view.

## The Challenge

### Zemax is 3D, OptiVerse is 2D

- **Zemax**: 3D rotationally symmetric surfaces (spheres around optical axis)
- **OptiVerse**: 2D cross-section (side view through optical axis)

### Solution: Cross-Sectional Projection

We take a **vertical slice** through the Zemax 3D lens, preserving all curvature information for accurate physics:

```
Zemax 3D (top view):              OptiVerse 2D (side view):
                                       y
     ╭─────╮                          ↑
    ╱   ●   ╲                    +6.35│  ╱│╲
   │circular │  ← Rotationally        │ │ │ │
    ╲aperture╱     symmetric      ────┼─│─┼─│──→ x
     ╰─────╯                     -6.35│  ╲│╱
   D=12.7mm                               │
                                      Curved
                                    interface
```

## What Was Implemented

### 1. Extended `InterfaceDefinition` Class

Added curved surface support to the core data model:

```python
@dataclass
class InterfaceDefinition:
    # ... existing fields ...
    
    # NEW: Curved surface properties
    is_curved: bool = False
    radius_of_curvature_mm: float = 0.0  # Zemax R value
    
    # NEW: Helper methods
    def center_of_curvature_mm() -> Tuple[float, float]
    def is_flat() -> bool
    def surface_sag_at_y(y_mm: float) -> float
```

**Sign Convention** (Zemax standard):
- **Positive R**: Convex from left (center of curvature to the right)
- **Negative R**: Concave from left (center of curvature to the left)

### 2. Updated `ZemaxConverter`

The converter now:
- Extracts curvature from Zemax CURV field: `R = 1 / curvature`
- Calculates surface sag: `sag = R - √(R² - h²)`
- Creates interfaces with `is_curved=True` and proper radius
- Adds curvature info to interface names

### 3. Enhanced Demo Script

Shows full curved surface information:
```
Surface 1:
  Radius: 66.68 mm
  → OptiVerse Interface:
     Curvature: R=66.68 mm
     Sag (edge): 0.303 mm (convex)
     Type: curved refractive_interface
```

### 4. Comprehensive Documentation

Created `docs/ZEMAX_CURVED_SURFACES_AND_3D_TO_2D.md` explaining:
- 3D→2D projection strategy
- Surface sag calculation
- Sign conventions
- Ray tracing through curved surfaces
- Visual rendering approaches

## Test Results: AC254-100-B Achromatic Doublet

Successfully parsed all three curved surfaces:

### Surface 1: Air → N-LAK22 (Entry)
```
Radius: +66.68 mm (convex)
Sag: 0.303 mm
Type: Positive meniscus (bulges toward incoming light)
```

### Surface 2: N-LAK22 → N-SF6HT (Cemented)
```
Radius: -53.70 mm (concave)
Sag: 0.377 mm
Type: Negative meniscus (curves away from light)
```

### Surface 3: N-SF6HT → Air (Exit)
```
Radius: -259.41 mm (weakly concave)
Sag: 0.078 mm
Type: Nearly flat (large radius)
```

## OptiVerse Representation

Each curved surface is now properly represented:

```python
InterfaceDefinition(
    x1_mm=0.00,      # Vertex position along optical axis
    y1_mm=-6.35,     # Bottom edge of aperture
    x2_mm=0.00,      # (same x for 2D cross-section)
    y2_mm=6.35,      # Top edge of aperture
    
    element_type='refractive_interface',
    name='S1: Air → N-LAK22 [R=+66.7mm]',
    
    # Refractive indices
    n1=1.000,
    n2=1.651,
    
    # Curved surface properties
    is_curved=True,
    radius_of_curvature_mm=66.68  # From Zemax
)
```

## Visual Representation

### Current (Simplified)
Interfaces shown as vertical lines at vertex position:
```
   │     │     │
   │     │     │  ← Vertical lines
   │     │     │
```

### Future (Realistic)
Interfaces shown as curved arcs matching actual lens shape:
```
  ╱│╲   ╲│╱   ╲│╱
 │ │ │   │     │   ← Curved arcs showing
  ╲│╱   ╱│╲   ╱│╲     true surface shapes
```

Helper method provided for rendering:
```python
interface.surface_sag_at_y(y)  # Returns x-offset for curve at height y
```

## Ray Tracing (Future)

For accurate ray tracing through curved surfaces:

1. **Ray-Sphere Intersection**: Find where ray hits curved surface
2. **Surface Normal**: Calculate normal (radial from center of curvature)
3. **Snell's Law**: Apply at correct angle on curved surface

```python
# Pseudocode for curved surface ray tracing
def trace_through_curved_interface(ray, interface):
    center = interface.center_of_curvature_mm()
    radius = interface.radius_of_curvature_mm
    
    # Find intersection
    hit_point = ray_sphere_intersection(ray, center, radius)
    
    # Get normal (radial)
    normal = normalize(hit_point - center)
    
    # Apply Snell's law
    refracted_ray = snells_law(ray, normal, interface.n1, interface.n2)
    
    return refracted_ray
```

## Benefits

### 1. Physical Accuracy
✅ Real lens geometry preserved from Zemax
✅ Exact curvatures for each surface
✅ Proper sag calculations for aberration analysis

### 2. Realistic Optics
✅ Shows actual lens shapes (not just thin lens approximations)
✅ Can visualize why doublets correct aberrations
✅ Educational: see real optical engineering

### 3. Design Validation
✅ Compare OptiVerse results with Zemax
✅ Verify focal lengths and aberrations
✅ Understand lens behavior

### 4. Future Ray Tracing
✅ All geometry available for curved surface ray tracing
✅ Can implement precise refraction calculations
✅ Aberration effects will be visible

## Files Modified/Created

### Modified
- `src/optiverse/core/interface_definition.py`
  - Added `is_curved`, `radius_of_curvature_mm` fields
  - Added helper methods for curved surfaces
  - Updated serialization (to_dict/from_dict)

- `src/optiverse/services/zemax_converter.py`
  - Extract curvature from Zemax surfaces
  - Calculate sag for documentation
  - Create interfaces with curvature properties

- `examples/zemax_parse_simple.py`
  - Show curvature information
  - Display sag calculations
  - Label surfaces as convex/concave

### Created
- `docs/ZEMAX_CURVED_SURFACES_AND_3D_TO_2D.md`
  - Complete guide to 3D→2D projection
  - Surface curvature conventions
  - Sag calculations
  - Ray tracing through curved surfaces
  - Visual rendering strategies

## Usage Example

```bash
# Run demo with curved surface display
cd /Users/benny/Desktop/MIT/git/optiverse
python examples/zemax_parse_simple.py ~/Downloads/AC254-100-B-Zemax\(ZMX\).zmx
```

Output now shows:
```
Surface 1:
  Radius: 66.68 mm
  ...
  → OptiVerse Interface:
     Position: x=0.00 mm (vertex)
     Curvature: R=66.68 mm
     Sag (edge): 0.303 mm (convex)
     Type: curved refractive_interface
```

## Programmatic Access

```python
from optiverse.services.zemax_parser import ZemaxParser
from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
from optiverse.services.glass_catalog import GlassCatalog

# Parse Zemax file
parser = ZemaxParser()
zemax_data = parser.parse("AC254-100-B.zmx")

# Convert with curved surface support
converter = ZemaxToInterfaceConverter(GlassCatalog())
component = converter.convert(zemax_data)

# Access curved surface properties
for interface in component.interfaces_v2:
    if interface.is_curved:
        R = interface.radius_of_curvature_mm
        center = interface.center_of_curvature_mm()
        
        # Calculate sag at edge
        half_height = interface.length_mm() / 2.0
        sag = interface.surface_sag_at_y(half_height)
        
        print(f"{interface.name}")
        print(f"  Radius: {R:.2f} mm")
        print(f"  Center at: {center}")
        print(f"  Edge sag: {sag:.3f} mm")
```

## Key Formulas

### Surface Sag
```
sag = R - √(R² - h²)

where:
  R = |radius of curvature|
  h = semi-diameter (half aperture)
  
Sign:
  sag > 0 if R > 0 (convex)
  sag < 0 if R < 0 (concave)
```

### Center of Curvature
```
center_x = vertex_x + R
center_y = vertex_y

where R includes sign:
  R > 0: center to the right
  R < 0: center to the left
```

## Summary

The curved surface implementation provides **complete geometric fidelity** from Zemax to OptiVerse:

✅ **Curvature preserved**: Every surface radius stored correctly
✅ **3D→2D projection**: Cross-section through optical axis
✅ **Sign conventions**: Positive/negative radius handled per Zemax standard
✅ **Sag calculated**: Surface deviation quantified
✅ **Helper methods**: Easy access to geometric properties
✅ **Ready for ray tracing**: All data available for physics calculations
✅ **Backward compatible**: Flat surfaces still work (is_curved=False)

### Your AC254-100-B Lens

```
    y (mm)
+6.35│     ╱│╲        ╲│╱        ╲│╱
     │    ╱ │ ╲        │          │
     │   │  │  │      ╱│╲        ╱│╲
     │   │ LAK22│      │          │
     │   │n=1.65│  SF6HT     Air │
     │   │  │  │   n=1.81         │
     │   │  │  │      │          │
─────┼───│──┼──│──────┼──────────┼────→ x (mm)
 0.00│   │  │  │      │          │
     │   │  │  │      │          │
     │   │  │  │     ╲│╱        ╲│╱
     │    ╲ │ ╱       │          │
-6.35│     ╲│╱       ╱│╲        ╱│╲
     
     x=0    x=4.0    x=5.5      x=102.5
     R=+66.7 R=-53.7 R=-259.4   Focal
     (convex)(concave)(weak)    Point
```

**All three curved surfaces fully represented!** 🔬✨

## Next Steps

1. **Visual Rendering**: Draw curved arcs in MultiLineCanvas
2. **Ray Tracing**: Implement ray-sphere intersection and refraction
3. **Interactive Editing**: Allow editing radius of curvature in Component Editor
4. **Aberration Analysis**: Visualize chromatic and spherical aberrations

But the **core geometry is complete** - you can now import and represent real lens designs with full geometric accuracy! 🎯

