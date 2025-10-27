# Polarizing Beam Splitter (PBS) Physics Implementation

## Overview

The PBS implementation in Optiverse correctly handles arbitrary angles and follows fundamental optical physics principles. The implementation has been validated with comprehensive tests verifying Malus's Law and intensity conservation.

## Physical Principles

### Transmission Axis

A PBS has a **transmission axis** that defines which polarization component passes through:
- **p-polarization** (parallel to transmission axis) → **transmitted**
- **s-polarization** (perpendicular to transmission axis) → **reflected**

### Malus's Law

The intensity of transmitted/reflected light follows **Malus's Law**:

```
I_transmitted = I₀ × cos²(θ)
I_reflected = I₀ × sin²(θ)
```

Where θ is the angle between the input polarization and the transmission axis.

### Energy Conservation

Total intensity is always conserved:
```
I_transmitted + I_reflected = I₀
```

## Implementation Details

### Coordinate System

1. **Element Angle** (`angle_deg`): Orientation of the PBS element in the scene (affects splitting geometry)
2. **Transmission Axis** (`pbs_transmission_axis_deg`): **ABSOLUTE** angle of transmission axis in lab frame
   - 0° = horizontal transmission axis
   - 90° = vertical transmission axis
   - This does NOT rotate with the element - it's fixed in lab coordinates

### Jones Vector Formalism

The implementation uses Jones vectors to represent polarization states:
- Horizontal: `[1, 0]`
- Vertical: `[0, 1]`
- +45°: `[1/√2, 1/√2]`
- Linear at angle θ: `[cos(θ), sin(θ)]`

### Algorithm

For a PBS with transmission axis at angle α, and input polarization with Jones vector `[Ex, Ey]`:

1. Define transmission axis unit vector:
   ```
   p_axis = [cos(α), sin(α)]
   s_axis = [-sin(α), cos(α)]  # Perpendicular
   ```

2. Project Jones vector onto axes:
   ```
   p_component = dot([Ex, Ey], p_axis)
   s_component = dot([Ex, Ey], s_axis)
   ```

3. Compute intensities:
   ```
   I_transmitted = |p_component|²
   I_reflected = |s_component|²
   ```

4. Generate output polarizations:
   ```
   transmitted_jones = p_component × p_axis / sqrt(I_transmitted)
   reflected_jones = -s_component × s_axis / sqrt(I_reflected)
   ```
   (Note: π phase shift on reflection)

## Examples

### Example 1: Standard Configuration
- **Element angle**: 45° (diagonal orientation for 90° beam splitting)
- **Transmission axis**: 0° (horizontal, absolute)
- **Result**: 
  - Horizontal polarization → 100% transmission
  - Vertical polarization → 100% reflection

### Example 2: 45° Transmission Axis
- **Element angle**: 45° (doesn't affect polarization, only geometry)
- **Transmission axis**: 45° (diagonal, absolute)
- **Input**: Horizontal polarization (0°)
- **Result**: 
  - Transmitted: cos²(45°) = 50%
  - Reflected: sin²(45°) = 50%

### Example 3: Vertical Transmission Axis
- **Element angle**: 45°
- **Transmission axis**: 90° (vertical, absolute)
- **Input**: Horizontal polarization (0°)
- **Result**:
  - Transmitted: cos²(90°) = 0% (no transmission)
  - Reflected: sin²(90°) = 100% (all reflected)

## Test Results

The implementation has been verified with comprehensive tests:

✓ **Malus's Law**: Verified for 0° to 90° in 15° increments
✓ **Intensity Conservation**: Verified for 22 different angle combinations
✓ **Arbitrary Angles**: Works correctly for any (polarization, axis) pair

All tests achieve numerical precision better than 10⁻⁶.

## Usage in Optiverse

### Creating a PBS

```python
# In component registry
pbs = {
    "kind": "beamsplitter",
    "angle_deg": 45,  # Element orientation (affects splitting geometry)
    "is_polarizing": True,
    "pbs_transmission_axis_deg": 0,  # ABSOLUTE angle in lab frame
    # 0° = horizontal transmission, 90° = vertical transmission
}
```

### Changing Transmission Axis

To change which polarization transmits:
1. **Rotate the element** (`angle_deg`): Changes the splitting geometry (where reflected beam goes) but does NOT affect transmission axis
2. **Adjust transmission axis** (`pbs_transmission_axis_deg`): Changes which polarization transmits
   - Set to 0° for horizontal transmission
   - Set to 90° for vertical transmission  
   - Set to 45° for diagonal (50/50 split of H/V polarizations)

### Viewing Polarization Effects

To see PBS effects:
- Use sources with different polarization types (horizontal, vertical, +45°, linear at custom angles)
- +45° polarization creates a 50/50 split (both beams visible)
- Aligned polarization gives 100% transmission
- Perpendicular polarization gives 100% reflection

## Physics References

1. **Jones Calculus**: Standard formalism for polarization optics
2. **Malus's Law**: I = I₀cos²(θ), discovered by Étienne-Louis Malus (1808)
3. **PBS Operation**: Based on Brewster's angle or dielectric coatings
4. **Energy Conservation**: Fundamental principle ensuring T + R = 1

## Code Location

- **Core Physics**: `src/optiverse/core/geometry.py` → `transform_polarization_beamsplitter()`
- **Models**: `src/optiverse/core/models.py` → `BeamsplitterParams`, `OpticalElement`
- **Ray Tracing**: `src/optiverse/core/use_cases.py` → `trace_rays()`
- **Tests**: `tests/core/test_pbs_arbitrary_angles.py`

