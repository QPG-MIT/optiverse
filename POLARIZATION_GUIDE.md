# Polarization Support in Optiverse

This guide explains the polarization functionality added to the Optiverse optical raytracing package.

## Overview

Optiverse now includes full support for polarization using the Jones vector formalism. Every optical source can emit polarized light, and all optical components (mirrors, lenses, and beamsplitters) react appropriately to the polarization state.

## Key Features

1. **Jones Vector Representation**: Polarization is represented using complex 2D Jones vectors `[Ex, Ey]`, allowing accurate simulation of:
   - Linear polarization (horizontal, vertical, or at any angle)
   - Circular polarization (left or right)
   - Elliptical polarization (any combination)

2. **Source Polarization Control**: Sources can be configured with various polarization states through an intuitive UI.

3. **Optical Element Interactions**:
   - **Mirrors**: Apply proper phase shifts (s-polarization preserved, p-polarization gets π phase shift)
   - **Lenses**: Preserve polarization (ideal thin lens approximation)
   - **Beamsplitters**: Support both non-polarizing and polarizing (PBS) modes

4. **Polarizing Beam Splitters (PBS)**: Beamsplitters can operate in PBS mode, where they separate light based on polarization:
   - p-polarization (parallel to transmission axis) is transmitted
   - s-polarization (perpendicular to transmission axis) is reflected

## Using Polarization

### Setting Source Polarization

When editing a source (double-click on a source element), you'll see polarization controls:

1. **Polarization Type**: Choose from:
   - `horizontal` - Linear horizontal polarization (default)
   - `vertical` - Linear vertical polarization
   - `+45` - Linear polarization at +45°
   - `-45` - Linear polarization at -45°
   - `circular_right` - Right circular polarization
   - `circular_left` - Left circular polarization
   - `linear` - Linear polarization at custom angle

2. **Polarization Angle**: When "linear" is selected, specify the angle in degrees (0° = horizontal)

### Configuring Polarizing Beam Splitters

When editing a beamsplitter:

1. Check **"Polarizing Beam Splitter (PBS)"** to enable PBS mode
2. Set **"PBS transmission axis"** to define the angle of p-polarization that transmits
3. When PBS mode is enabled, the T/R split ratios are automatically determined by polarization

### Programmatic Usage

#### Creating Polarization States

```python
from optiverse.core.models import Polarization

# Predefined states
pol_h = Polarization.horizontal()           # [1, 0]
pol_v = Polarization.vertical()             # [0, 1]
pol_45 = Polarization.diagonal_plus_45()    # [1, 1]/√2
pol_rc = Polarization.circular_right()      # [1, 1j]/√2

# Custom linear polarization
pol_30 = Polarization.linear(30.0)          # 30° from horizontal

# Arbitrary Jones vector
pol_custom = Polarization(np.array([1+2j, 3-4j], dtype=complex))
```

#### Source with Polarization

```python
from optiverse.core.models import SourceParams

# Simple configuration
src = SourceParams(
    x_mm=-100.0,
    y_mm=0.0,
    angle_deg=0.0,
    polarization_type="vertical"
)

# Custom angle
src = SourceParams(
    x_mm=-100.0,
    y_mm=0.0,
    angle_deg=0.0,
    polarization_type="linear",
    polarization_angle_deg=30.0
)

# Custom Jones vector
src = SourceParams(
    x_mm=-100.0,
    y_mm=0.0,
    angle_deg=0.0,
    use_custom_jones=True,
    custom_jones_ex_real=1.0,
    custom_jones_ex_imag=0.0,
    custom_jones_ey_real=0.0,
    custom_jones_ey_imag=1.0
)
```

#### Polarizing Beam Splitter

```python
from optiverse.core.models import BeamsplitterParams

# Non-polarizing BS (default)
bs = BeamsplitterParams(
    split_T=50.0,
    split_R=50.0,
    is_polarizing=False
)

# Polarizing BS
pbs = BeamsplitterParams(
    is_polarizing=True,
    pbs_transmission_axis_deg=0.0  # Horizontal transmission
)
```

#### Ray Tracing with Polarization

```python
from optiverse.core.use_cases import trace_rays
from optiverse.core.models import OpticalElement, SourceParams
import numpy as np

# Create a PBS
pbs = OpticalElement(
    kind="bs",
    p1=np.array([0.0, -50.0]),
    p2=np.array([0.0, 50.0]),
    is_polarizing=True,
    pbs_transmission_axis_deg=0.0
)

# Create a 45° polarized source
src = SourceParams(
    x_mm=-100.0,
    y_mm=0.0,
    angle_deg=0.0,
    polarization_type="+45",
    n_rays=1
)

# Trace rays
paths = trace_rays([pbs], [src])

# Each RayPath now has polarization information
for path in paths:
    if path.polarization:
        print(f"Polarization: {path.polarization.jones_vector}")
        print(f"Intensity: {path.polarization.intensity()}")
```

## Technical Details

### Jones Vector Formalism

The polarization state is described by a complex 2-vector:

```
|ψ⟩ = [Ex]
      [Ey]
```

Where `Ex` and `Ey` are complex amplitudes representing:
- Magnitude: Electric field amplitude
- Phase: Temporal phase

Common states:
- **Horizontal**: `[1, 0]`
- **Vertical**: `[0, 1]`
- **+45° Linear**: `[1, 1]/√2`
- **Right Circular**: `[1, i]/√2`
- **Left Circular**: `[1, -i]/√2`

### Polarization Transformations

#### Mirror Reflection

Mirrors apply phase shifts based on the plane of incidence:
- **s-polarization** (perpendicular to plane): Phase preserved
- **p-polarization** (parallel to plane): π phase shift

This is implemented in `transform_polarization_mirror()` in `core/geometry.py`.

#### Lens Transmission

Ideal thin lenses preserve polarization state without modification. This is implemented in `transform_polarization_lens()`.

#### Beamsplitter Interaction

**Non-polarizing mode:**
- Transmitted ray: Polarization preserved
- Reflected ray: Apply mirror-like phase transformation

**PBS mode:**
- Decomposes input polarization into p and s components relative to transmission axis
- p-component transmits (no phase shift)
- s-component reflects (π phase shift)
- Intensity split determined by polarization state

This is implemented in `transform_polarization_beamsplitter()`.

## Data Persistence

Polarization settings are automatically saved and loaded with your optical assemblies:

- Source polarization type and angle
- Beamsplitter PBS mode and transmission axis
- Custom Jones vectors

All polarization parameters are serialized to JSON when saving assemblies.

## Examples

### Example 1: PBS Analyzer

Create a PBS to analyze the polarization state of a source:

1. Add a source with `+45°` polarization
2. Add a beamsplitter in PBS mode with 0° transmission axis
3. Enable ray tracing
4. Observe that light splits equally into transmitted (horizontal component) and reflected (vertical component) paths

### Example 2: Polarization Rotation

Create a series of components to rotate polarization:

1. Add a horizontal polarized source
2. Add mirrors at specific angles to induce phase shifts
3. Observe the polarization evolution through the system

### Example 3: Circular Polarization

1. Set source to `circular_right` polarization
2. Add optical elements
3. Trace rays to see how circular polarization interacts with components

## API Reference

### Core Classes

- `Polarization` - Represents polarization state with Jones vector
- `SourceParams` - Source configuration including polarization
- `BeamsplitterParams` - Beamsplitter configuration including PBS mode
- `OpticalElement` - Optical element with polarization properties
- `RayPath` - Ray path including polarization state

### Core Functions

- `transform_polarization_mirror(pol, v_in, n_hat)` - Mirror transformation
- `transform_polarization_lens(pol)` - Lens transformation
- `transform_polarization_beamsplitter(pol, v_in, n_hat, t_hat, is_polarizing, pbs_axis_deg, is_transmitted)` - Beamsplitter transformation
- `trace_rays(elements, sources, max_events)` - Ray tracing with polarization

## Implementation Notes

1. **Coordinate System**: Jones vectors are defined in the lab frame with:
   - Ex: Horizontal (x-direction) component
   - Ey: Vertical (y-direction) component

2. **Phase Conventions**: We follow standard conventions:
   - Mirror reflection: p-pol gets π shift, s-pol preserved
   - PBS: p-pol transmits, s-pol reflects with π shift

3. **Intensity Calculation**: Intensity is computed as `|Ex|² + |Ey|²`

4. **Normalization**: Polarization states can be normalized using `.normalize()` method

## Future Enhancements

Possible extensions to the polarization system:

1. **Waveplates**: Add quarter-wave and half-wave plate elements
2. **Polarizers**: Add linear polarizer elements
3. **Birefringent Materials**: Add materials with different refractive indices for different polarizations
4. **Polarization Visualization**: Add visual indicators for polarization state in the UI
5. **Stokes Parameters**: Add Stokes parameter representation alongside Jones vectors
6. **Dichroism**: Add materials with polarization-dependent absorption

## References

- Born, M., & Wolf, E. (1999). *Principles of Optics* (7th ed.). Cambridge University Press.
- Hecht, E. (2016). *Optics* (5th ed.). Pearson Education.
- Fowles, G. R. (1989). *Introduction to Modern Optics* (2nd ed.). Dover Publications.

