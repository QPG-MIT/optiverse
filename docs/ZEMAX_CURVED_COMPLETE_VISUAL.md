# Zemax Import with Curved Surfaces - Complete Visual Guide

## AC254-100-B Achromatic Doublet: From Zemax to OptiVerse

### Zemax 3D View (Rotationally Symmetric)

Looking down the optical axis (beam coming toward you):

```
         ╭───────────────╮
        ╱                 ╲
       ╱                   ╲
      │         ●           │  ← Circular aperture
      │     (optical        │     Diameter = 12.7 mm
      │       axis)         │     (rotationally symmetric)
       ╲                   ╱
        ╲                 ╱
         ╰───────────────╯

  Surface 1: R = +66.68 mm (spherical, convex)
  Surface 2: R = -53.70 mm (spherical, concave)
  Surface 3: R = -259.41 mm (spherical, weakly concave)
```

### OptiVerse 2D Cross-Section (Side View)

Taking a vertical slice through the optical axis:

```
    y (mm)
     ↑
+6.35│                                                          
     │         ╱─╲                                             Ray converges
     │        ╱   ╲         ╲───╱         ╲───╱                    ↘
     │       │     │         │             │                        ↘
     │       │     │        ╱─────╲       ╱─────╲                   ↘
     │       │     │         │             │                         ↘
     │       │ N-LAK22│    N-SF6HT    Air           ╲                ↘●
     │       │ n=1.651│    n=1.805    n=1.0          ╲           Focal point
     │       │     │         │             │          ↘        @ x≈102.5mm
─────┼───────│─────┼─────────┼─────────────┼───────────────────────────→ x (mm)
 0.00│       │     │         │             │   (optical axis)
     │       │     │         │             │
     │       │     │        ╲─────╱       ╲─────╱
     │        ╲   ╱         │             │
     │         ╲─╱         ╱─────╲       ╱─────╲
-6.35│                                                          
     
     │       │     │         │             │
     x=0     │   x=4.0       │           x=5.5
     │       │     │         │             │
   Surface 1│  Surface 2  Surface 3
     Entry  │  Cemented    Exit
  (convex)  │ (concave)  (concave)
            │
         4.0mm thick     1.5mm thick

├────────────────────┤
   N-LAK22 element
   
                      ├──────────────┤
                        N-SF6HT element
```

## Surface Details with Curvature

### Surface 1: Air → N-LAK22 (Entry Surface)

**3D Zemax:**
```
    Spherical surface
    Radius = +66.68 mm
    Center of curvature is 66.68mm to the right
    
         ╭─────╮
        ╱       ╲
       │    ●    │  ← Sphere radius 66.68mm
        ╲   ↑   ╱
         ╰─↑─╯
           │
        Center here
```

**2D OptiVerse:**
```
    Convex surface (bulges toward incoming light)
    
    y
 +6.35│      ╱─╲
      │     ╱   ╲       ← Arc of circle R=66.68mm
      │    │     │
      │    │  ●  │      ● = vertex at x=0.00mm
      │    │     │
      │     ╲   ╱
 -6.35│      ╲─╱
      
      Sag = 0.303 mm (how much it bulges)
```

**InterfaceDefinition:**
```python
InterfaceDefinition(
    x1_mm=0.00, y1_mm=-6.35,
    x2_mm=0.00, y2_mm=6.35,
    name='S1: Air → N-LAK22 [R=+66.7mm]',
    n1=1.000, n2=1.651,
    is_curved=True,
    radius_of_curvature_mm=66.68  # Positive = convex
)
```

### Surface 2: N-LAK22 → N-SF6HT (Cemented Interface)

**3D Zemax:**
```
    Spherical surface
    Radius = -53.70 mm (negative!)
    Center of curvature is 53.70mm to the left
    
       ╭─────╮
      ╱       ╲
     │    ●    │  ← Sphere radius 53.70mm
      ╲       ╱
       ╰─────╯
         ↑
    Center here (to the left)
```

**2D OptiVerse:**
```
    Concave surface (curves away from light)
    
    y
 +6.35│      ╲─╱
      │       │         ← Arc curves inward
      │      ╱─╲
      │      │ ●│       ● = vertex at x=4.00mm
      │      ╲─╱
      │       │
 -6.35│      ╱─╲
      
      Sag = -0.377 mm (negative = curves backward)
```

**InterfaceDefinition:**
```python
InterfaceDefinition(
    x1_mm=4.00, y1_mm=-6.35,
    x2_mm=4.00, y2_mm=6.35,
    name='S2: N-LAK22 → N-SF6HT [R=-53.7mm]',
    n1=1.651, n2=1.805,
    is_curved=True,
    radius_of_curvature_mm=-53.70  # Negative = concave
)
```

### Surface 3: N-SF6HT → Air (Exit Surface)

**3D Zemax:**
```
    Spherical surface
    Radius = -259.41 mm (large negative)
    Weakly curved (nearly flat)
    
    Very large sphere
       ╭───────────╮
      ╱             ╲
     │       ●       │  ← Sphere radius 259.41mm
      ╲             ╱
       ╰───────────╯
              ↑
         Center here
```

**2D OptiVerse:**
```
    Weakly concave (almost flat)
    
    y
 +6.35│      ╲─╱
      │       │         ← Very slight curve
      │       │            (large radius)
      │       ●│         ● = vertex at x=5.50mm
      │       │
      │       │
 -6.35│      ╱─╲
      
      Sag = -0.078 mm (small curvature)
```

**InterfaceDefinition:**
```python
InterfaceDefinition(
    x1_mm=5.50, y1_mm=-6.35,
    x2_mm=5.50, y2_mm=6.35,
    name='S3: N-SF6HT → Air [R=-259.4mm]',
    n1=1.805, n2=1.000,
    is_curved=True,
    radius_of_curvature_mm=-259.41  # Large negative = weakly concave
)
```

## Ray Path Through Doublet

### Top View (in 2D cross-section):

```
Ray from infinity →

    ╱
   ╱
  ╱                    Air (n=1.0)
 ╱   ┌─────────────────────────────────┐
╱    │  ╱────╲                          │  Surface 1
────────│      │    N-LAK22 (n=1.651)   │  R=+66.68mm (convex)
     │  ╲────╱                          │  Refracts INTO glass
     │       │                          │  Ray bends toward normal
     │       │      ╲─────╱             │  
     │       │       │                  │  Surface 2
     │       │      ╱─────╲    N-SF6HT │  R=-53.70mm (concave)
     │       │       │     (n=1.805)   │  Slight refraction
     │       │       │                  │  (glass to denser glass)
     │       │       │      ╲─────╱    │
     │       │       │       │         │  Surface 3
     │       │       │      ╱─────╲    │  R=-259.41mm (weak concave)
     │       │       │       │         │  Refracts OUT OF glass
     │       │       │       │   Air   │  Ray bends away from normal
     └───────┴───────┴───────┴─────────┘
             │       │       │
             │       │        ╲
             │       │         ╲
             │        ╲         ╲
              ╲        ╲         ╲
               ╲        ╲         ╲
                ╲        ╲         ╲_____ All rays converge
                 ╲________╲______________● Focal point
                           ╲               @ 100mm EFL
                            ╲
```

### Why the Curves Matter

**Flat surfaces (wrong):**
```
│  │  │  ← All surfaces flat
│  │  │     Bad focus, lots of aberrations
│  │  │
```

**Curved surfaces (correct):**
```
╱│╲ ╲│╱ ╲│╱  ← Curved surfaces
│ │  │   │      Each curve optimized
│ │  │   │      Corrects aberrations
│ │  │   │      Sharp focus!
```

## Sign Convention Summary

### Positive Radius (Convex from left)

```
    Light →    ╱│╲
              ╱ │ ╲
             │  │  │    ● ← Center of curvature
              ╲ │ ╱         to the RIGHT
               ╲│╱

    R > 0:  Center is downstream (to the right)
    Vertex is closest point to incoming light
    Surface "bulges" toward light source
```

### Negative Radius (Concave from left)

```
    Light →     ╲│╱
                 │
    ●  ← Center ╱│╲    Center of curvature
       to LEFT           to the LEFT

    R < 0:  Center is upstream (to the left)
    Vertex is farthest point from incoming light
    Surface "curves away" from light source
```

## Surface Sag Visualization

**Sag** = deviation from flat surface at the edge

### Convex (R > 0):
```
    Flat reference:  │
                    │
    Curved surface: ╱╲   ← Surface extends forward
                   │  │
                    ╲╱
                    
    |←sag→|  = 0.303 mm
```

### Concave (R < 0):
```
    Flat reference:  │
                    │
    Curved surface: ╲╱   ← Surface pulls backward
                     │
                    ╱╲
                    
    |←sag→|  = -0.377 mm (negative)
```

## Complete Component Structure

```python
ComponentRecord(
    name="AC254-100-B Achromatic Doublet",
    kind="multi_element",
    object_height_mm=12.7,
    notes="Imported from Zemax\n"
          "Primary wavelength: 855.0 nm\n"
          "Near-IR achromatic doublet, 100mm EFL",
    
    interfaces_v2=[
        # Entry surface
        InterfaceDefinition(
            x1_mm=0.00, y1_mm=-6.35,
            x2_mm=0.00, y2_mm=6.35,
            name='S1: Air → N-LAK22 [R=+66.7mm]',
            n1=1.000, n2=1.651,
            is_curved=True,
            radius_of_curvature_mm=66.68
        ),
        
        # Cemented interface
        InterfaceDefinition(
            x1_mm=4.00, y1_mm=-6.35,
            x2_mm=4.00, y2_mm=6.35,
            name='S2: N-LAK22 → N-SF6HT [R=-53.7mm]',
            n1=1.651, n2=1.805,
            is_curved=True,
            radius_of_curvature_mm=-53.70
        ),
        
        # Exit surface
        InterfaceDefinition(
            x1_mm=5.50, y1_mm=-6.35,
            x2_mm=5.50, y2_mm=6.35,
            name='S3: N-SF6HT → Air [R=-259.4mm]',
            n1=1.805, n2=1.000,
            is_curved=True,
            radius_of_curvature_mm=-259.41
        ),
    ]
)
```

## Summary Table

| Surface | Position | Radius | Type | n₁ → n₂ | Sag (edge) |
|---------|----------|--------|------|---------|------------|
| **S1** | x=0.00mm | +66.68mm | Convex | 1.000 → 1.651 | +0.303mm |
| **S2** | x=4.00mm | -53.70mm | Concave | 1.651 → 1.805 | -0.377mm |
| **S3** | x=5.50mm | -259.41mm | Weak concave | 1.805 → 1.000 | -0.078mm |

**Total element thickness**: 5.5mm
**Working distance to focus**: 97.09mm
**Effective focal length**: 100mm

## Benefits of Curved Surface Support

### Before (Flat Approximation)
```
│   │   │  ← All flat, no geometric accuracy
│   │   │     Can't model aberrations
│   │   │     Poor physics
```

### After (Full Curvature)
```
╱│╲ ╲│╱ ╲│╱  ← True lens geometry
│ │  │   │     Accurate sag calculations
│ │  │   │     Ready for aberration analysis
│ │  │   │     Real optical engineering!
```

### What You Get

1. ✅ **Exact Geometry**: All radii preserved from Zemax
2. ✅ **Sag Calculated**: Know how much each surface deviates
3. ✅ **Sign Convention**: Convex/concave properly identified  
4. ✅ **3D→2D Projection**: Cross-section accurately represents 3D lens
5. ✅ **Ray Tracing Ready**: All data available for curved surface refraction
6. ✅ **Visualization Ready**: Can render realistic lens shapes
7. ✅ **Educational**: See real optical design, not approximations

## Usage

```bash
# View your lens with full curved surface info
python examples/zemax_parse_simple.py AC254-100-B.zmx
```

**Output:**
```
Surface 1:
  Radius: 66.68 mm
  Curvature: R=66.68 mm
  Sag (edge): 0.303 mm (convex)
  Type: curved refractive_interface

Surface 2:
  Radius: -53.70 mm
  Curvature: R=-53.70 mm
  Sag (edge): 0.377 mm (concave)
  Type: curved refractive_interface

Surface 3:
  Radius: -259.41 mm
  Curvature: R=-259.41 mm
  Sag (edge): 0.078 mm (concave)
  Type: curved refractive_interface
```

## Conclusion

You now have **complete geometric fidelity** from Zemax to OptiVerse:
- ✅ All curved surfaces imported
- ✅ 3D → 2D projection handled correctly
- ✅ Sign conventions respected
- ✅ Sag calculations accurate
- ✅ Ready for ray tracing
- ✅ Ready for visualization

**Your real lenses are now fully represented in 2D!** 🔬✨

