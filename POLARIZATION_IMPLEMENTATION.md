# Polarization Implementation Summary

## Overview

Polarization support has been successfully implemented in the Optiverse optical raytracing package using Jones vector formalism. This implementation allows users to:

1. Configure source light with various polarization states
2. Simulate how optical components (mirrors, lenses, beamsplitters) interact with polarized light
3. Use Polarizing Beam Splitters (PBS) to separate light by polarization

## Implementation Details

### Files Modified/Created

#### Core Models (`src/optiverse/core/models.py`)

**Added:**
- `Polarization` dataclass - Represents polarization using Jones vectors
  - Factory methods: `horizontal()`, `vertical()`, `diagonal_plus_45()`, `diagonal_minus_45()`, `circular_right()`, `circular_left()`, `linear(angle)`
  - Methods: `normalize()`, `intensity()`, `to_dict()`, `from_dict()`
  
**Modified:**
- `SourceParams` - Added polarization configuration:
  - `polarization_type`: str - Type of polarization
  - `polarization_angle_deg`: float - Angle for linear polarization
  - `custom_jones_*`: float - Custom Jones vector components
  - `use_custom_jones`: bool - Flag to use custom Jones vector
  - `get_polarization()` method - Returns configured `Polarization` object

- `BeamsplitterParams` - Added PBS support:
  - `is_polarizing`: bool - Enable PBS mode
  - `pbs_transmission_axis_deg`: float - PBS transmission axis angle

- `OpticalElement` - Added polarization properties:
  - `is_polarizing`: bool
  - `pbs_transmission_axis_deg`: float

- `RayPath` - Added polarization tracking:
  - `polarization`: Optional[Polarization] - Polarization state of ray

#### Geometry Functions (`src/optiverse/core/geometry.py`)

**Added:**
- `jones_matrix_rotation(angle_deg)` - Create rotation matrix for Jones vectors
- `transform_polarization_mirror(pol, v_in, n_hat)` - Transform polarization through mirror
  - Applies proper s/p phase shifts
- `transform_polarization_lens(pol)` - Transform through lens (preserves polarization)
- `transform_polarization_beamsplitter(pol, v_in, n_hat, t_hat, is_polarizing, pbs_axis_deg, is_transmitted)` - Transform through beamsplitter
  - Supports both non-polarizing and PBS modes
  - Returns tuple of (transformed_polarization, intensity_factor)

#### Ray Tracing (`src/optiverse/core/use_cases.py`)

**Modified:**
- `trace_rays()` function:
  - Gets initial polarization from source using `src.get_polarization()`
  - Ray stack now includes polarization state (8-tuple instead of 7-tuple)
  - Applies polarization transformations at each interaction:
    - Mirror: Uses `transform_polarization_mirror()`
    - Lens: Uses `transform_polarization_lens()`
    - Beamsplitter: Uses `transform_polarization_beamsplitter()`
  - Stores polarization state in each `RayPath`

#### UI Components

**Modified `src/optiverse/widgets/source_item.py`:**
- Added polarization controls to source editor dialog:
  - Dropdown to select polarization type
  - Angle spinbox for linear polarization (enabled only when "linear" is selected)
  - Saves polarization settings when dialog is accepted

**Modified `src/optiverse/widgets/beamsplitter_item.py`:**
- Added PBS controls to beamsplitter editor dialog:
  - Checkbox to enable PBS mode
  - PBS transmission axis angle spinbox
  - Disables T/R controls when PBS mode is active
  - Saves PBS settings when dialog is accepted

**Modified `src/optiverse/ui/views/main_window.py`:**
- Updated beamsplitter `OpticalElement` creation to include polarization properties:
  - `is_polarizing` from params
  - `pbs_transmission_axis_deg` from params

#### Tests

**Created `tests/core/test_polarization.py`:**
- Comprehensive test suite covering:
  - Basic polarization creation and operations
  - Polarization transformations through optical elements
  - SourceParams polarization interface
  - Ray tracing with polarization
  - PBS functionality

### Key Design Decisions

1. **Jones Vector Formalism**: Chosen for its simplicity and accuracy for fully polarized light
   - Complex 2-vectors representing Ex and Ey components
   - Natural representation for linear, circular, and elliptical polarization
   - Efficient computation with matrix operations

2. **Default Behavior**: Horizontal linear polarization by default
   - Most intuitive for users
   - Matches common laboratory conventions

3. **UI Integration**: Seamless integration with existing editor dialogs
   - Polarization controls in source editor
   - PBS mode in beamsplitter editor
   - No changes to main UI layout

4. **Backward Compatibility**: 
   - Existing assemblies without polarization data will use defaults
   - Non-polarizing beamsplitters work as before
   - All new fields have sensible defaults

5. **Physics Accuracy**:
   - Mirror reflections apply proper phase shifts (s vs p polarization)
   - PBS correctly separates polarizations
   - Intensity conservation maintained

## Testing

All polarization functionality has been tested:

✓ Basic polarization states (horizontal, vertical, diagonal, circular)
✓ Source parameter polarization configuration
✓ Polarization serialization/deserialization
✓ Transformations through mirrors, lenses, beamsplitters
✓ PBS mode correctly separates polarizations
✓ Integration with ray tracing engine

Test results: All tests pass successfully.

## Usage Example

```python
from optiverse.core.models import SourceParams, OpticalElement
from optiverse.core.use_cases import trace_rays
import numpy as np

# Create a source with 45° polarization
source = SourceParams(
    x_mm=-100.0,
    y_mm=0.0,
    polarization_type="+45",
    n_rays=5
)

# Create a PBS
pbs = OpticalElement(
    kind="bs",
    p1=np.array([0.0, -50.0]),
    p2=np.array([0.0, 50.0]),
    is_polarizing=True,
    pbs_transmission_axis_deg=0.0
)

# Trace rays
paths = trace_rays([pbs], [source])

# Examine polarization states
for path in paths:
    pol = path.polarization
    print(f"Jones vector: {pol.jones_vector}")
    print(f"Intensity: {pol.intensity()}")
```

## Known Limitations

1. **Ideal Components**: Implementation assumes ideal optical components
   - Mirrors have perfect reflection with standard phase shifts
   - Lenses have no birefringence
   - No material dispersion effects

2. **Fully Polarized Light**: Jones formalism only handles fully polarized light
   - Cannot represent partially polarized or unpolarized light
   - For unpolarized light, Stokes parameters would be needed

3. **No Waveplates**: Current implementation doesn't include waveplate elements
   - Could be added in future as a new optical element type

4. **2D Simulation**: As the underlying ray tracer is 2D, some 3D polarization effects are not captured
   - However, the mathematical framework is correct for the simulated geometry

## Future Enhancements

1. **Polarization Visualization**:
   - Add visual indicators showing polarization state
   - Color-code rays by polarization
   - Display polarization ellipse at key points

2. **Additional Optical Elements**:
   - Quarter-wave plates (QWP)
   - Half-wave plates (HWP)
   - Linear polarizers
   - Optical rotators

3. **Advanced Features**:
   - Stokes parameter representation for partially polarized light
   - Müller matrix formalism as alternative to Jones
   - Birefringent materials
   - Dichroic materials

4. **Analysis Tools**:
   - Malus's law verification
   - Polarization state analyzer
   - Degree of polarization calculations

## Conclusion

The polarization implementation is complete and fully functional. It adds significant capability to the Optiverse package while maintaining backward compatibility and clean code structure. Users can now simulate realistic polarization effects in their optical systems, including the important case of polarizing beam splitters.

The implementation follows established optical physics principles and uses industry-standard Jones vector formalism. All functionality has been tested and documented.

