# Polarization Feature - Implementation Complete ✓

## Summary

Full polarization support has been successfully implemented in the Optiverse optical raytracing package. Users can now simulate polarized light propagation through optical systems, including Polarizing Beam Splitters (PBS).

## What's New

### 1. Source Polarization Configuration

Sources can now emit light with any polarization state:
- **Linear polarization**: Horizontal, vertical, or at any custom angle
- **Circular polarization**: Left or right circular
- **Diagonal polarization**: ±45° linear
- **Custom Jones vectors**: For advanced users

**How to use:**
1. Double-click on a source element
2. Select "Polarization" type from dropdown
3. For "linear" type, specify the angle
4. Click OK to apply

### 2. Polarizing Beam Splitters (PBS)

Beamsplitters can now operate in PBS mode:
- **PBS mode**: Separates light by polarization
  - p-polarization (parallel to transmission axis) transmits
  - s-polarization (perpendicular) reflects
- **Standard mode**: Non-polarizing beam splitter (default behavior)

**How to use:**
1. Double-click on a beamsplitter element
2. Check "Polarizing Beam Splitter (PBS)"
3. Set "PBS transmission axis" angle
4. Click OK to apply

### 3. Optical Component Behavior

All optical components now react to polarization:
- **Mirrors**: Apply correct phase shifts (s-pol preserved, p-pol π shift)
- **Lenses**: Preserve polarization (ideal thin lens)
- **Beamsplitters**: 
  - Non-polarizing: Split by T/R ratios, preserve polarization
  - Polarizing: Split by polarization state

### 4. Ray Tracing with Polarization

Ray tracing now tracks and transforms polarization:
- Each ray carries its polarization state
- Polarization is transformed at each interaction
- Intensity is modulated by polarization for PBS

## Files Modified

### Core Implementation
- `src/optiverse/core/models.py` - Added `Polarization` class and updated params
- `src/optiverse/core/geometry.py` - Added polarization transformation functions
- `src/optiverse/core/use_cases.py` - Updated ray tracing to handle polarization

### UI Components
- `src/optiverse/widgets/source_item.py` - Added polarization controls
- `src/optiverse/widgets/beamsplitter_item.py` - Added PBS controls
- `src/optiverse/ui/views/main_window.py` - Updated element creation

### Tests & Examples
- `tests/core/test_polarization.py` - Comprehensive test suite
- `examples/polarization_demo.py` - Interactive demonstration

### Documentation
- `POLARIZATION_GUIDE.md` - User guide and API reference
- `POLARIZATION_IMPLEMENTATION.md` - Technical implementation details
- `POLARIZATION_FEATURE_SUMMARY.md` - This file

## Quick Start

### Example 1: Horizontal Polarized Source

```python
from optiverse.core.models import SourceParams

src = SourceParams(
    x_mm=-100.0,
    y_mm=0.0,
    polarization_type="horizontal"  # Default
)
```

### Example 2: Vertical Polarized Source

```python
src = SourceParams(
    x_mm=-100.0,
    y_mm=0.0,
    polarization_type="vertical"
)
```

### Example 3: PBS Setup

```python
from optiverse.core.models import BeamsplitterParams

pbs = BeamsplitterParams(
    x_mm=0.0,
    y_mm=0.0,
    is_polarizing=True,              # Enable PBS mode
    pbs_transmission_axis_deg=0.0    # Horizontal transmission
)
```

### Example 4: 45° Polarized Light Through PBS

```python
from optiverse.core.models import SourceParams, OpticalElement
from optiverse.core.use_cases import trace_rays
import numpy as np

# Create source with +45° polarization
src = SourceParams(
    x_mm=-100.0,
    y_mm=0.0,
    polarization_type="+45",
    n_rays=5
)

# Create PBS with horizontal transmission axis
pbs = OpticalElement(
    kind="bs",
    p1=np.array([0.0, -50.0]),
    p2=np.array([0.0, 50.0]),
    is_polarizing=True,
    pbs_transmission_axis_deg=0.0
)

# Trace rays - will split 50/50 into transmitted and reflected
paths = trace_rays([pbs], [src])

# Examine results
for path in paths:
    print(f"Polarization: {path.polarization.jones_vector}")
    print(f"Intensity: {path.polarization.intensity()}")
```

## Running the Demo

To see polarization in action:

```bash
python examples/polarization_demo.py
```

This will demonstrate:
- Different polarization states
- Source configuration
- PBS behavior
- Mirror reflections
- Serialization

## Testing

Run the test suite:

```bash
python -m pytest tests/core/test_polarization.py -v
```

All tests pass successfully ✓

## Key Features

✓ **Complete Jones vector formalism**
- Full support for linear, circular, and elliptical polarization
- Complex amplitude representation
- Proper phase tracking

✓ **Physical accuracy**
- Correct s/p polarization phase shifts on mirrors
- Proper PBS separation by polarization
- Intensity conservation

✓ **User-friendly UI**
- Simple dropdown for common polarization types
- Intuitive PBS controls
- Seamless integration with existing dialogs

✓ **Backward compatible**
- Existing assemblies work without modification
- All new parameters have sensible defaults
- Non-polarizing mode is default for beamsplitters

✓ **Well tested**
- Comprehensive unit tests
- Integration tests with ray tracing
- Demo script for validation

✓ **Well documented**
- User guide with examples
- Technical implementation details
- API reference

## Technical Highlights

### Jones Vector Representation

Polarization is represented as a complex 2-vector:
```
|ψ⟩ = [Ex]
      [Ey]
```

Where Ex and Ey are complex amplitudes in horizontal and vertical directions.

### Common States

| State | Jones Vector |
|-------|--------------|
| Horizontal | `[1, 0]` |
| Vertical | `[0, 1]` |
| +45° | `[1, 1]/√2` |
| -45° | `[1, -1]/√2` |
| Right Circular | `[1, i]/√2` |
| Left Circular | `[1, -i]/√2` |

### Transformations

**Mirror reflection:**
```python
pol_out = transform_polarization_mirror(pol_in, v_in, n_hat)
# s-polarization: phase preserved
# p-polarization: π phase shift
```

**Lens transmission:**
```python
pol_out = transform_polarization_lens(pol_in)
# Polarization preserved (ideal lens)
```

**PBS:**
```python
pol_t, int_t = transform_polarization_beamsplitter(
    pol_in, v_in, n_hat, t_hat,
    is_polarizing=True,
    pbs_axis_deg=0.0,
    is_transmitted=True
)
# Separates into p and s components
```

## Performance

No significant performance impact:
- Polarization tracking adds minimal overhead to ray tracing
- Jones vector operations are efficient (2x2 complex arithmetic)
- Same ray tracing algorithm, just with additional state

## Data Persistence

Polarization settings are fully serialized:
- Source polarization type and angle saved with assemblies
- PBS mode and transmission axis saved with beamsplitters
- Custom Jones vectors preserved
- JSON format remains readable

## Future Possibilities

The implementation provides a foundation for:
- Wave plates (QWP, HWP)
- Linear polarizers
- Birefringent materials
- Polarization visualization in GUI
- Stokes parameter representation
- Degree of polarization analysis

## Conclusion

The polarization feature is **complete, tested, and ready to use**. It adds significant scientific capability to Optiverse while maintaining ease of use and backward compatibility.

Users can now:
- ✓ Configure source polarization easily
- ✓ Simulate Polarizing Beam Splitters
- ✓ Analyze polarization through optical systems
- ✓ Design polarization-sensitive optical setups
- ✓ Save and load assemblies with polarization settings

**Default behavior:** Horizontal linear polarization, which is intuitive and matches common laboratory conventions.

---

*Implementation completed successfully with full test coverage and comprehensive documentation.*

