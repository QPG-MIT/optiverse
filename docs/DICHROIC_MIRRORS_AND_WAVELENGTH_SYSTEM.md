---
layout: default
title: Dichroic Mirrors & Wavelength System
nav_order: 22
parent: Physics & Optics
---

# Dichroic Mirrors and Wavelength System Implementation

## Overview

This document describes the implementation of dichroic mirrors and the wavelength-based color system for the optiverse optical simulation tool. This feature enables physically accurate simulation of wavelength-dependent optical elements and proper color representation based on spectral properties.

## Features Implemented

### 1. Wavelength System

#### Source Wavelength Support
- Sources can now be configured with a specific wavelength (in nanometers)
- Two modes available:
  - **Custom Color Mode**: Traditional hex color picker (legacy behavior)
  - **Wavelength Mode**: Physical wavelength specification with automatic color computation

#### Wavelength-to-Color Conversion
- Physically accurate conversion from wavelength to RGB colors
- Based on the visible spectrum (380-750 nm)
- Uses an improved approximation of CIE color matching functions
- Handles UV (< 380 nm) and IR (> 750 nm) with appropriate visual representation

#### Common Laser Wavelength Presets
Predefined wavelengths for common laser sources:
- UV (355nm Nd:YAG 3rd harmonic)
- Violet (405nm diode)
- Blue (450nm diode)
- Cyan (488nm Ar-ion)
- Green (532nm Nd:YAG 2nd harmonic)
- Yellow (589nm sodium)
- Red (633nm HeNe)
- Deep Red (650nm diode)
- IR (808nm diode)
- IR (1064nm Nd:YAG fundamental)

### 2. Dichroic Mirrors

#### Physical Model
Dichroic mirrors use a wavelength-dependent reflection/transmission model:

```
R(λ) = 1 / (1 + exp((λ - λ_cutoff) / Δλ))
T(λ) = 1 - R(λ)
```

Where:
- `λ` is the incident wavelength
- `λ_cutoff` is the cutoff wavelength (50% transition point)
- `Δλ` is the transition width (steepness of the transition)

**Behavior:**
- Short wavelengths (λ < λ_cutoff): **Reflected**
- Long wavelengths (λ > λ_cutoff): **Transmitted**
- Transition region: Smooth sigmoid function

#### Component Properties
- **Cutoff Wavelength**: The wavelength at which R = T = 50%
- **Transition Width**: Width of the transition region (smaller = sharper cutoff)
- **Physical Size**: Standard 1-inch optic (25.4 mm)
- **Default Angle**: 45° for beam combining/splitting

#### Use Cases
1. **Wavelength Multiplexing**: Combine multiple laser wavelengths onto a single beam path
2. **Beam Splitting by Color**: Separate different wavelengths from a polychromatic source
3. **Fluorescence Applications**: Separate excitation and emission wavelengths
4. **Multi-wavelength Interferometry**: Wavelength-dependent beam paths

## Architecture

### Data Models

#### `SourceParams`
Extended with wavelength support:
```python
@dataclass
class SourceParams:
    # ... existing fields ...
    wavelength_nm: float = 0.0  # 0 = use color_hex, >0 = compute from wavelength
```

#### `DichroicParams`
New model for dichroic mirrors:
```python
@dataclass
class DichroicParams:
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    object_height_mm: float = 80.0
    cutoff_wavelength_nm: float = 550.0  # Green cutoff
    transition_width_nm: float = 50.0    # Transition width
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float, float, float, float]] = None
    name: Optional[str] = None
```

#### `OpticalElement`
Extended to support dichroic properties:
```python
@dataclass
class OpticalElement:
    kind: str  # 'lens' | 'mirror' | 'bs' | 'waveplate' | 'dichroic'
    # ... existing fields ...
    cutoff_wavelength_nm: float = 550.0
    transition_width_nm: float = 50.0
```

#### `RayPath`
Extended to carry wavelength information:
```python
@dataclass
class RayPath:
    points: List[np.ndarray]
    rgba: Tuple[int, int, int, int]
    polarization: Optional[Polarization] = None
    wavelength_nm: float = 0.0  # Wavelength in nm (0 = not specified)
```

### Ray Tracing

The ray tracing engine has been updated to:
1. **Propagate wavelength** through the optical system
2. **Compute dichroic reflectance/transmittance** based on wavelength
3. **Generate split rays** (reflected and transmitted) with appropriate intensities
4. **Preserve polarization** through dichroic interactions

#### Physics Implementation

```python
def compute_dichroic_reflectance(
    wavelength_nm: float,
    cutoff_wavelength_nm: float,
    transition_width_nm: float
) -> Tuple[float, float]:
    """
    Compute R and T for a dichroic mirror using sigmoid function.
    Returns (reflectance, transmittance).
    """
    delta = (wavelength_nm - cutoff_wavelength_nm) / max(1.0, transition_width_nm)
    reflectance = 1.0 / (1.0 + np.exp(delta))
    transmittance = 1.0 - reflectance
    return reflectance, transmittance
```

### User Interface

#### Source Editor
The source editor now includes:
- **Color Mode dropdown**: Choose between "Custom Color" and "Wavelength"
- **Wavelength Preset dropdown**: Quick selection of common laser wavelengths
- **Wavelength spinbox**: Fine control (200-2000 nm range)
- **Custom Color picker**: Traditional hex color selection (disabled in wavelength mode)
- **Live color preview**: Updates automatically based on wavelength or custom color

#### Dichroic Editor
Double-click a dichroic mirror to edit:
- Position (X, Y coordinates)
- Optical axis angle
- Length (physical size)
- **Cutoff wavelength** (200-2000 nm)
- **Transition width** (1-200 nm)

#### Component Library
Dichroics appear in their own category in the component library dock:
- **Dichroics** category
  - Dichroic Mirror (550nm cutoff) - standard green/red splitter

## Usage Examples

### Example 1: Wavelength Multiplexing
**Goal**: Combine red (633nm) and green (532nm) lasers onto a single path

1. Add a green laser source (532nm)
   - Set wavelength to 532.0 nm (or use "Green (532nm Nd:YAG 2nd)" preset)
   - Position at (-400, 50)
   - Aim horizontally (0°)

2. Add a red laser source (633nm)
   - Set wavelength to 633.0 nm (or use "Red (633nm HeNe)" preset)
   - Position at (0, -400)
   - Aim vertically (90°)

3. Add a dichroic mirror (550nm cutoff)
   - Position at (0, 0)
   - Angle at 45°
   - The 532nm (green) light reflects, 633nm (red) transmits
   - Both beams exit along the same path

### Example 2: Spectral Separation
**Goal**: Separate a multi-wavelength beam

1. Create multiple sources at the same position with different wavelengths
   - Blue (450nm), Green (532nm), Red (650nm)

2. Add dichroic mirrors at appropriate positions:
   - First dichroic at 500nm cutoff (separates blue from green+red)
   - Second dichroic at 590nm cutoff (separates green from red)

3. Each wavelength exits in a different direction

### Example 3: Fluorescence Simulation
**Goal**: Model excitation/emission separation

1. Excitation source: 488nm (cyan/blue)
2. Sample position with "emission" (simulate with 520nm green source)
3. Dichroic at 510nm cutoff
   - Reflects 488nm excitation to sample
   - Transmits 520nm emission to detector

## Technical Details

### Color Conversion Algorithm

The wavelength-to-RGB conversion uses a piecewise linear approximation with gamma correction:

```python
def wavelength_to_rgb(wavelength_nm: float) -> tuple[int, int, int]:
    """
    Convert wavelength (nm) to RGB using spectral approximation.
    
    Spectrum regions:
    - 380-440 nm: Violet to Blue
    - 440-490 nm: Blue to Cyan
    - 490-510 nm: Cyan to Green
    - 510-580 nm: Green to Yellow
    - 580-645 nm: Yellow to Red
    - 645-750 nm: Red (with intensity falloff)
    """
    # ... (see implementation in color_utils.py)
```

### Dichroic Physics

The sigmoid transition function provides:
- **Energy conservation**: R + T ≈ 1 at all wavelengths
- **Realistic transitions**: Not infinitely sharp, has finite width
- **Physical accuracy**: Matches real thin-film interference coatings

**Transition width interpretation**:
- **Small width (10-20 nm)**: Sharp cutoff (high-quality coating)
- **Medium width (50 nm)**: Standard dichroic
- **Large width (100+ nm)**: Broadband or color filter

### Performance Considerations

- Wavelength checking adds minimal overhead (single comparison per ray-element interaction)
- Color computation happens once per source, cached for all rays
- Dichroic splitting handled same as regular beamsplitters (bifurcation in ray tree)

## Component Editor Integration

### Creating Custom Dichroics

1. Open Component Editor (Tools menu)
2. Load or drop a dichroic mirror image
3. Set component kind to "dichroic"
4. Click two points on the optical element to calibrate
5. Enter:
   - Physical height (object_height_mm)
   - Cutoff wavelength (cutoff_wavelength_nm)
   - Transition width (transition_width_nm)
6. Save to library

### Library Storage

Dichroic components serialize with these fields:
```json
{
  "name": "Dichroic Mirror (550nm cutoff)",
  "kind": "dichroic",
  "cutoff_wavelength_nm": 550.0,
  "transition_width_nm": 50.0,
  "object_height_mm": 25.4,
  "image_path": "path/to/image.png",
  "line_px": [x1, y1, x2, y2],
  "angle_deg": 45.0
}
```

## Future Enhancements

Possible extensions to this system:

1. **Wavelength-dependent refractive indices**: Chromatic aberration in lenses
2. **Dispersion modeling**: Prisms and gratings
3. **Bandpass filters**: Transmission curves for optical filters
4. **Multi-band dichroics**: Multiple cutoff wavelengths
5. **Polarization-dependent dichroics**: Combine PBS and dichroic behavior
6. **Fluorescence sources**: Wavelength conversion (e.g., 488nm → 520nm)

## Testing

The implementation includes:
- Unit tests for wavelength-to-RGB conversion
- Validation of dichroic physics (energy conservation)
- Integration tests for ray tracing with wavelength-dependent elements
- UI tests for source editor wavelength controls

## References

1. Dan Bruton's wavelength-to-RGB algorithm (improved version)
2. CIE color matching functions
3. Thin-film interference theory (dichroic coatings)
4. Jones calculus for polarization

## Summary

This implementation provides a physically accurate, user-friendly system for simulating wavelength-dependent optical systems. The dichroic mirrors enable realistic modeling of:
- Laser beam combining
- Spectral separation
- Fluorescence microscopy
- Multi-wavelength interferometry
- Color-dependent beam routing

The wavelength system integrates seamlessly with existing polarization and ray tracing features, providing a comprehensive optical simulation environment.

