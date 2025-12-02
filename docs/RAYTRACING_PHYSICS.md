---
layout: default
title: Raytracing Physics
nav_order: 21
parent: Physics & Optics
---

# Raytracing Physics and Optical Interface Structure

This document provides a comprehensive mathematical and physical description of how raytracing works in Optiverse, including detailed equations and the structure of optical interfaces.

## Table of Contents

1. [Raytracing Algorithm Overview](#raytracing-algorithm-overview)
2. [Mathematical Foundations](#mathematical-foundations)
3. [Optical Interface Structure](#optical-interface-structure)
4. [Element Types and Physics](#element-types-and-physics)
5. [Coordinate Systems](#coordinate-systems)

---

## Raytracing Algorithm Overview

### High-Level Algorithm

The raytracing engine follows a **polymorphic, event-driven** approach:

```
For each source:
    Generate initial rays (position, direction, polarization, wavelength)
    
    For each ray:
        While ray intensity > threshold AND events < max_events:
            1. Find nearest intersection with any optical element
            2. If intersection found:
                - Advance ray to intersection point
                - Call element.interact() (polymorphic dispatch)
                - Process output rays (may be multiple for beamsplitters)
                - Push output rays onto stack for continued tracing
            3. If no intersection:
                - Extend ray to maximum length
                - Finalize ray path
```

### Key Data Structures

#### Ray State (`RayState`)

```python
@dataclass
class RayState:
    position: np.ndarray          # Current position [x, y] in mm
    direction: np.ndarray         # Normalized direction vector [dx, dy]
    intensity: float              # Ray intensity (0.0 to 1.0)
    polarization: Polarization    # Jones vector [Ex, Ey]
    wavelength_nm: float          # Wavelength in nanometers
    path_points: List[np.ndarray] # Points for visualization
    remaining_length: float       # Maximum propagation distance
    events: int                   # Number of interactions so far
    base_rgb: Tuple[int, int, int] # Base color for visualization
```

#### Ray Intersection (`RayIntersection`)

```python
@dataclass
class RayIntersection:
    distance: float               # Distance along ray to intersection
    point: np.ndarray             # Intersection point [x, y] in mm
    tangent: np.ndarray           # Surface tangent vector (normalized)
    normal: np.ndarray             # Surface normal vector (normalized)
    center: np.ndarray             # Center of surface segment
    length: float                  # Length of surface segment
    interface: Optional[object]   # Reference to optical interface
```

### Algorithm Complexity

- **Current**: O(n) per ray, where n = number of optical elements
- **Future (BVH)**: O(log n) per ray with spatial indexing
- **Parallelization**: Each ray is independent, enabling perfect parallelization

---

## Mathematical Foundations

### 1. Ray-Surface Intersection

#### Flat Surface Intersection

For a ray defined as **P + t·V** (where P is origin, V is direction, t > 0) and a line segment from **A** to **B**:

**Step 1: Compute surface normal**

The surface normal **n̂** is perpendicular to the tangent **t̂**:

```
t̂ = (A - B) / ||A - B||
n̂ = [-t̂_y, t̂_x]
```

**Step 2: Check if ray intersects plane**

The ray intersects the plane containing the segment if:

```
denominator = V · n̂ ≠ 0
```

**Step 3: Compute intersection parameter**

```
t = ((C - P) · n̂) / (V · n̂)
```

where **C** = (A + B) / 2 is the segment center.

**Step 4: Compute intersection point**

```
X = P + t·V
```

**Step 5: Check if intersection is within segment bounds**

```
s = (X - C) · t̂
```

Intersection is valid if: `|s| ≤ L/2`, where L = ||A - B||.

#### Curved Surface Intersection

For spherical surfaces with radius of curvature **R** and center **O**:

**Step 1: Ray-sphere intersection**

A ray **P + t·V** intersects a sphere centered at **O** with radius **R** if:

```
Δ = P - O
a = V · V = 1  (V is normalized)
b = 2(V · Δ)
c = Δ · Δ - R²

Discriminant: D = b² - 4ac
```

**Step 2: Find intersection point**

If D ≥ 0:

```
t = (-b - √D) / 2a  (use smaller t for first intersection)
X = P + t·V
```

**Step 3: Compute surface normal at intersection**

```
n̂ = (X - O) / ||X - O||
```

**Step 4: Check if intersection is within segment bounds**

Project intersection onto the line segment and verify it's within the segment endpoints.

---

### 2. Snell's Law (Refraction)

When a ray passes from medium 1 (refractive index **n₁**) to medium 2 (refractive index **n₂**):

#### Snell's Law

```
n₁·sin(θ₁) = n₂·sin(θ₂)
```

where:
- **θ₁** = angle of incidence (between ray and surface normal)
- **θ₂** = angle of refraction (between refracted ray and surface normal)

#### Vector Formulation

Given:
- Incident ray direction: **v_in** (normalized)
- Surface normal: **n̂** (normalized, pointing into medium 2)
- Refractive indices: **n₁**, **n₂**

**Step 1: Compute incident angle**

```
cos(θ₁) = -v_in · n̂
sin(θ₁) = √(1 - cos²(θ₁))
```

**Step 2: Check for total internal reflection**

```
sin(θ₂) = (n₁/n₂)·sin(θ₁)
```

If `sin(θ₂) > 1`, total internal reflection occurs (all light reflects).

**Step 3: Compute refracted direction**

If refraction occurs:

```
η = n₁/n₂
cos(θ₂) = √(1 - sin²(θ₂))

v_refracted = η·v_in + (η·cos(θ₁) - cos(θ₂))·n̂
v_refracted = normalize(v_refracted)
```

**Critical Angle**

Total internal reflection occurs when:

```
θ₁ > θ_critical = arcsin(n₂/n₁)
```

This only happens when **n₁ > n₂** (ray going from higher to lower index).

---

### 3. Fresnel Equations

Fresnel equations determine the **reflectance R** and **transmittance T** at an interface.

#### For Unpolarized Light (Average of s and p polarizations)

**s-polarization** (perpendicular to plane of incidence):

```
r_s = (n₁·cos(θ₁) - n₂·cos(θ₂)) / (n₁·cos(θ₁) + n₂·cos(θ₂))
R_s = r_s²
```

**p-polarization** (parallel to plane of incidence):

```
r_p = (n₂·cos(θ₁) - n₁·cos(θ₂)) / (n₂·cos(θ₁) + n₁·cos(θ₂))
R_p = r_p²
```

**Unpolarized reflectance** (average):

```
R = (R_s + R_p) / 2
T = 1 - R
```

#### Special Cases

**Normal incidence** (θ₁ = 0°):

```
R = ((n₁ - n₂) / (n₁ + n₂))²
T = 1 - R
```

**Grazing incidence** (θ₁ → 90°):

```
R → 1
T → 0
```

**Total internal reflection**:

```
R = 1
T = 0
```

---

### 4. Law of Reflection

For a perfect mirror:

**Reflection Law**:

```
Angle of incidence = Angle of reflection
```

**Vector Formulation**:

Given incident direction **v_in** and surface normal **n̂**:

```
v_reflected = v_in - 2(v_in · n̂)·n̂
```

This is equivalent to:

```
v_reflected = reflect_vec(v_in, n̂)
```

**Polarization Transformation**:

Upon reflection from an ideal metallic mirror:
- **s-polarization** (perpendicular): Phase unchanged
- **p-polarization** (parallel): Phase shifted by **π** (180°)

In Jones matrix form (s-p basis):

```
J_mirror = [[1,  0],
            [0, -1]]
```

---

### 5. Thin Lens Equation

Optiverse uses the **paraxial (thin lens) approximation**:

#### Thin Lens Formula

```
θ_out = θ_in - y/f
```

where:
- **θ_in** = incident angle (relative to optical axis)
- **θ_out** = output angle (relative to optical axis)
- **y** = height of ray on lens (distance from optical axis)
- **f** = effective focal length (EFL)

#### Ray Height Calculation

For a lens with endpoints **p₁** and **p₂**:

```
center = (p₁ + p₂) / 2
tangent = normalize(p₂ - p₁)
y = (hit_point - center) · tangent
```

#### Direction Update

**Step 1: Decompose incident direction**

```
a_n = direction · normal
a_t = direction · tangent
θ_in = atan2(a_t, a_n)
```

**Step 2: Apply thin lens equation**

```
θ_out = θ_in - y/f
```

**Step 3: Reconstruct output direction**

```
direction_out = normalize(cos(θ_out)·normal + sin(θ_out)·tangent)
```

#### Limitations

- **Paraxial approximation**: Only valid for small angles (typically < 10°)
- **Thin lens**: Assumes lens thickness is negligible
- **No aberrations**: Does not model spherical aberration, coma, etc.

---

### 6. Polarization Transformations

#### Jones Vector Representation

Polarization state is represented as a complex Jones vector:

```
E = [E_x, E_y] = [|E_x|·exp(i·φ_x), |E_y|·exp(i·φ_y)]
```

where:
- **E_x**, **E_y** = complex electric field components
- **|E_x|**, **|E_y|** = amplitudes
- **φ_x**, **φ_y** = phases

#### Waveplate Transformation

A waveplate introduces a phase shift **δ** between fast and slow axes:

**Jones Matrix** (fast axis at angle **θ**):

```
J = R(-θ) · [[1,        0],
             [0, exp(i·δ)]] · R(θ)
```

where **R(θ)** is the rotation matrix:

```
R(θ) = [[cos(θ),  sin(θ)],
        [-sin(θ), cos(θ)]]
```

**Common Waveplates**:

- **Quarter waveplate (QWP)**: δ = 90° = π/2
  - Converts linear ↔ circular polarization
- **Half waveplate (HWP)**: δ = 180° = π
  - Rotates linear polarization by 2θ

**Directionality**:

- **Forward** (with normal): phase shift = **+δ**
- **Backward** (against normal): phase shift = **-δ**

This is critical for QWP: forward gives right circular, backward gives left circular.

---

## Optical Interface Structure

### Interface Hierarchy

Optiverse uses a **unified interface system** where all optical elements are represented as interfaces:

```
OpticalInterface
├── Geometry (LineSegment or CurvedSegment)
│   ├── p1: [x, y] in mm
│   ├── p2: [x, y] in mm
│   ├── is_curved: bool
│   └── radius_of_curvature_mm: float (if curved)
│
└── Properties (Union type)
    ├── RefractiveProperties
    │   ├── n1: float
    │   ├── n2: float
    │   └── curvature_radius_mm: Optional[float]
    │
    ├── LensProperties
    │   └── efl_mm: float
    │
    ├── MirrorProperties
    │   └── reflectivity: float
    │
    ├── BeamsplitterProperties
    │   ├── split_T: float
    │   ├── split_R: float
    │   ├── is_polarizing: bool
    │   └── pbs_transmission_axis_deg: float
    │
    ├── WaveplateProperties
    │   ├── phase_shift_deg: float
    │   └── fast_axis_deg: float
    │
    └── DichroicProperties
        ├── cutoff_wavelength_nm: float
        ├── transition_width_nm: float
        └── pass_type: str ("longpass" | "shortpass")
```

### Interface Definition (`InterfaceDefinition`)

The component editor uses `InterfaceDefinition` for storage:

```python
@dataclass
class InterfaceDefinition:
    # Geometry (in mm, local coordinate system, Y-up)
    x1_mm: float
    y1_mm: float
    x2_mm: float
    y2_mm: float
    
    # Element type
    element_type: str  # "lens" | "mirror" | "beamsplitter" | 
                       # "dichroic" | "refractive_interface" | 
                       # "polarizing_interface"
    
    # Type-specific properties (only relevant fields are used)
    # Lens
    efl_mm: float = 100.0
    
    # Mirror
    reflectivity: float = 100.0
    
    # Beam splitter
    split_T: float = 50.0
    split_R: float = 50.0
    is_polarizing: bool = False
    pbs_transmission_axis_deg: float = 0.0
    
    # Dichroic
    cutoff_wavelength_nm: float = 550.0
    transition_width_nm: float = 50.0
    pass_type: str = "longpass"
    
    # Refractive interface
    n1: float = 1.0
    n2: float = 1.5
    
    # Polarizing interface
    polarizer_subtype: str = "waveplate"
    phase_shift_deg: float = 90.0
    fast_axis_deg: float = 0.0
```

### Polymorphic Element Interface (`IOpticalElement`)

All optical elements implement the `IOpticalElement` interface:

```python
class IOpticalElement(ABC):
    @abstractmethod
    def get_geometry(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (p1, p2) endpoints in mm"""
        pass
    
    @abstractmethod
    def interact(
        self,
        ray: RayState,
        hit_point: np.ndarray,
        normal: np.ndarray,
        tangent: np.ndarray
    ) -> List[RayState]:
        """
        Process ray interaction.
        Returns list of output rays (may be multiple for beamsplitters).
        """
        pass
    
    @abstractmethod
    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (min_corner, max_corner) for spatial indexing"""
        pass
```

---

## Element Types and Physics

### 1. Refractive Interface (`RefractiveElement`)

**Physics**: Snell's law + Fresnel equations

**Input**: Ray with direction **v_in**, intensity **I_in**

**Process**:
1. Determine which side ray is coming from (check **v_in · n̂**)
2. Apply Snell's law to compute refracted direction
3. Check for total internal reflection
4. Compute Fresnel coefficients **R** and **T**
5. Generate transmitted ray (intensity **I_in · T**)
6. Generate reflected ray (intensity **I_in · R**)

**Output**: List of rays (transmitted + reflected, if both above threshold)

**Equations**:
- Snell's law: `n₁·sin(θ₁) = n₂·sin(θ₂)`
- Fresnel: `R = (R_s + R_p)/2`, `T = 1 - R`

---

### 2. Lens (`LensElement`)

**Physics**: Thin lens approximation (paraxial optics)

**Input**: Ray with direction **v_in**, height **y** on lens

**Process**:
1. Compute ray height **y** from optical axis
2. Apply thin lens equation: `θ_out = θ_in - y/f`
3. Reconstruct output direction
4. Preserve polarization (ideal lens)

**Output**: Single refracted ray

**Equations**:
- Thin lens: `θ_out = θ_in - y/f`
- No intensity loss (ideal lens)

---

### 3. Mirror (`MirrorElement`)

**Physics**: Law of reflection

**Input**: Ray with direction **v_in**, intensity **I_in**

**Process**:
1. Compute reflected direction: `v_reflected = v_in - 2(v_in·n̂)·n̂`
2. Transform polarization (s-pol unchanged, p-pol gets π shift)
3. Apply reflectivity: `I_out = I_in · reflectivity`

**Output**: Single reflected ray

**Equations**:
- Reflection: `v_reflected = reflect_vec(v_in, n̂)`
- Intensity: `I_out = I_in · R` (where R = reflectivity)

---

### 4. Beam Splitter (`BeamsplitterElement`)

**Physics**: Partial reflection + transmission

**Input**: Ray with direction **v_in**, intensity **I_in**

**Process**:
1. Compute transmitted ray (direction unchanged, intensity **I_in · T**)
2. Compute reflected ray (direction reflected, intensity **I_in · R**)
3. If polarizing: Apply polarization-dependent splitting

**Output**: Two rays (transmitted + reflected)

**Equations**:
- Transmission: `I_T = I_in · (T/100)`
- Reflection: `I_R = I_in · (R/100)`
- Energy conservation: `T + R = 100%` (typically)

---

### 5. Waveplate (`WaveplateElement`)

**Physics**: Jones matrix transformation

**Input**: Ray with polarization **E_in**, direction **v_in**

**Process**:
1. Determine propagation direction (forward/backward)
2. Apply Jones matrix with phase shift **±δ** (sign depends on direction)
3. Rotate to fast/slow axis basis
4. Apply phase shift
5. Rotate back to lab frame

**Output**: Single ray with transformed polarization

**Equations**:
- Jones matrix: `E_out = J(θ, ±δ) · E_in`
- Direction-dependent: `δ_effective = +δ` (forward) or `-δ` (backward)

---

### 6. Dichroic Filter (`DichroicElement`)

**Physics**: Wavelength-dependent reflection/transmission

**Input**: Ray with wavelength **λ**, direction **v_in**, intensity **I_in**

**Process**:
1. Compute wavelength-dependent reflectance:
   ```
   R(λ) = 1 / (1 + exp((λ - λ_cutoff) / Δλ))
   ```
2. For longpass: Reflect short wavelengths, transmit long
3. For shortpass: Transmit short wavelengths, reflect long
4. Generate transmitted ray (if T > threshold)
5. Generate reflected ray (if R > threshold)

**Output**: Two rays (transmitted + reflected, if both above threshold)

**Equations**:
- Reflectance: `R(λ) = 1 / (1 + exp((λ - λ_cutoff) / Δλ))`
- Transmittance: `T(λ) = 1 - R(λ)`

---

## Coordinate Systems

### Storage Coordinate System (Component Editor)

- **Origin**: Image center (0, 0)
- **X-axis**: Positive right, negative left
- **Y-axis**: Positive UP, negative DOWN (Y-up, mathematical convention)
- **Units**: Millimeters (mm)

### Scene Coordinate System (Main Canvas)

- **Origin**: Canvas center (0, 0)
- **X-axis**: Positive right, negative left
- **Y-axis**: Positive DOWN, negative UP (Y-down, screen convention)
- **Units**: Millimeters (mm)

### Conversion

When rendering interfaces from component editor to main canvas:

```
y_scene = -y_component  (flip Y-axis)
```

This conversion happens in `ComponentSprite` during rendering.

---

## Summary

Optiverse implements physically accurate raytracing using:

1. **Snell's law** for refraction
2. **Fresnel equations** for partial reflection
3. **Law of reflection** for mirrors
4. **Thin lens approximation** for lenses
5. **Jones matrix formalism** for polarization
6. **Wavelength-dependent models** for dichroic filters

All optical elements are represented as **interfaces** with:
- **Geometry**: Line segments or curved surfaces
- **Properties**: Type-specific optical parameters
- **Polymorphic interaction**: Each element implements `interact()` method

The raytracing engine uses **polymorphic dispatch** for clean, extensible code without type checking or if-elif chains.

