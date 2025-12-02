---
layout: default
title: Polarizing Interfaces
nav_order: 23
parent: Physics & Optics
---

# Polarizing Interface System

## Overview

The **Polarizing Interface** system provides a unified, extensible framework for handling polarization-modifying optical elements in Optiverse. This system fixes the previously broken waveplate implementation and provides a clean architecture for adding future polarization optics.

## Architecture

### Element Type

All polarizing elements use the same `element_type`:
```
element_type: "polarizing_interface"
```

### Polarizer Subtypes

Different types of polarizers are distinguished using the `polarizer_subtype` field:

| Subtype | Description | Status |
|---------|-------------|--------|
| `waveplate` | Phase retarders (QWP, HWP, custom) | ✅ Implemented |
| `linear_polarizer` | Absorbs one polarization direction | 🔜 Future |
| `circular_polarizer` | Passes only circular polarization | 🔜 Future |
| `faraday_rotator` | Non-reciprocal rotation | 🔜 Future |

## Data Model

### InterfaceDefinition Fields

```python
# Polarizing interface properties
polarizer_subtype: str = "waveplate"  # Subtype identifier

# Waveplate properties
phase_shift_deg: float = 90.0  # Phase shift (90° for QWP, 180° for HWP)
fast_axis_deg: float = 0.0  # Fast axis angle in lab frame

# Linear polarizer properties (future)
transmission_axis_deg: float = 0.0  # Transmission axis angle
extinction_ratio_db: float = 40.0  # Extinction ratio

# Faraday rotator properties (future)
rotation_angle_deg: float = 45.0  # Rotation angle (non-reciprocal)
```

### Type Registry

The `interface_types.py` registry contains metadata for UI generation:

```python
'polarizing_interface': {
    'name': 'Polarizing Interface',
    'color': (255, 215, 0),  # Gold
    'emoji': '🟡',
    'properties': ['polarizer_subtype', 'phase_shift_deg', 'fast_axis_deg', ...],
    'property_labels': {...},
    'property_units': {...},
    'property_ranges': {...},
    'property_defaults': {...},
}
```

## Waveplates

### Physics

Waveplates introduce a phase shift between orthogonal polarization components:

- **Quarter Waveplate (QWP)**: 90° phase shift
  - Converts linear ↔ circular polarization
  - Critical for optical isolators

- **Half Waveplate (HWP)**: 180° phase shift
  - Rotates linear polarization
  - Switches handedness of circular polarization

### Directionality

Waveplates are **directional**:
- Forward direction: phase shift = +δ
- Backward direction: phase shift = -δ

This is critical for QWPs in double-pass configurations (e.g., optical isolators).

See [WAVEPLATE_DIRECTIONALITY.md](WAVEPLATE_DIRECTIONALITY.md) for detailed implementation notes.

### Creating Waveplates

#### From Library

Use the built-in library components:
- **Quarter Waveplate (QWP)**: 90° phase shift
- **Half Waveplate (HWP)**: 180° phase shift

#### Programmatically

```python
from optiverse.core.interface_definition import InterfaceDefinition

waveplate = InterfaceDefinition(
    x1_mm=0.0,
    y1_mm=-15.0,
    x2_mm=0.0,
    y2_mm=15.0,
    element_type="polarizing_interface",
    polarizer_subtype="waveplate",
    phase_shift_deg=90.0,  # QWP
    fast_axis_deg=45.0,    # Fast axis at 45°
    name="QWP @ 45°"
)
```

#### In JSON

```json
{
  "element_type": "polarizing_interface",
  "polarizer_subtype": "waveplate",
  "phase_shift_deg": 90.0,
  "fast_axis_deg": 45.0,
  "x1_mm": 0.0,
  "y1_mm": -15.0,
  "x2_mm": 0.0,
  "y2_mm": 15.0
}
```

## UI Integration

### Properties Widget

The interface properties widget automatically displays relevant properties based on `polarizer_subtype`:

For waveplates:
- **Polarizer Type**: Dropdown (waveplate, linear_polarizer, etc.)
- **Phase Shift**: Numeric input with range 0-360°
- **Fast Axis Angle**: Numeric input with range -180 to 180°

### Color Coding

Polarizing interfaces are displayed in **gold** (RGB: 255, 215, 0) to distinguish them from other optical elements.

### Labels

The system generates descriptive labels:
- `QWP (45°)` - Quarter waveplate with 45° fast axis
- `HWP (0°)` - Half waveplate with 0° fast axis
- `Waveplate (37°, 60°)` - Custom phase shift and fast axis

## Raytracing Integration

### Conversion Path

```
WaveplateItem → InterfaceDefinition (polarizing_interface)
                ↓
            OpticalInterface (Phase 1)
                ↓
            WaveplateElement (Phase 2)
                ↓
            Ray interaction (transform_polarization_waveplate)
```

### Adapter Functions

The integration adapter handles conversion:

```python
# In adapter.py
elif element_type == "polarizing_interface":
    if iface.polarizer_subtype == "waveplate":
        return OpticalElement(
            kind="waveplate",
            p1=p1, p2=p2,
            phase_shift_deg=iface.phase_shift_deg,
            fast_axis_deg=iface.fast_axis_deg,
            angle_deg=angle_deg  # For directionality detection
        )
```

## Backward Compatibility

The system maintains backward compatibility with the old `"waveplate"` element type:

```python
# Old format (still supported)
{
  "element_type": "waveplate",
  "phase_shift_deg": 90.0,
  "fast_axis_deg": 0.0
}

# New format (recommended)
{
  "element_type": "polarizing_interface",
  "polarizer_subtype": "waveplate",
  "phase_shift_deg": 90.0,
  "fast_axis_deg": 0.0
}
```

Both formats are converted correctly during loading.

## Future Extensions

### Linear Polarizer

```python
polarizer = InterfaceDefinition(
    element_type="polarizing_interface",
    polarizer_subtype="linear_polarizer",
    transmission_axis_deg=0.0,  # Horizontal transmission
    extinction_ratio_db=40.0,   # 40 dB extinction
)
```

**Physics**: Absorbs light polarized orthogonal to transmission axis.

### Circular Polarizer

```python
polarizer = InterfaceDefinition(
    element_type="polarizing_interface",
    polarizer_subtype="circular_polarizer",
    handedness="right",  # "right" or "left"
)
```

**Physics**: Passes only right or left circular polarization.

### Faraday Rotator

```python
rotator = InterfaceDefinition(
    element_type="polarizing_interface",
    polarizer_subtype="faraday_rotator",
    rotation_angle_deg=45.0,  # Non-reciprocal rotation
)
```

**Physics**: Rotates polarization non-reciprocally (same direction for forward and backward passes). Essential for true optical isolators.

## Benefits

✅ **Fixes broken waveplates** - Proper integration with interface-based architecture  
✅ **First-class components** - Same structure as lenses, mirrors, beamsplitters  
✅ **Extensible design** - Easy to add new polarizer types  
✅ **Type-safe** - Properties validated by interface system  
✅ **Auto-generated UI** - Properties widget reads from type registry  
✅ **Backward compatible** - Old "waveplate" element_type still works  
✅ **Clean architecture** - Single element_type with subtypes

## Testing

Run the waveplate tests:

```bash
pytest tests/core/test_waveplates.py -v
pytest tests/objects/test_component_factory.py::TestComponentFactoryWaveplate -v
pytest tests/integration/test_adapter.py::test_convert_waveplate_interface -v
```

All tests should pass with the new polarizing_interface system.

## References

- [WAVEPLATE_DIRECTIONALITY.md](WAVEPLATE_DIRECTIONALITY.md) - Detailed physics and directionality implementation
- [COMPONENT_EDITOR_GENERALIZATION_SUMMARY.md](COMPONENT_EDITOR_GENERALIZATION_SUMMARY.md) - Interface-based component architecture
- [interface_types.py](../src/optiverse/core/interface_types.py) - Type registry source code
- [interface_definition.py](../src/optiverse/core/interface_definition.py) - Data model source code

## Migration Guide

### For Existing Code

If you have code that creates waveplates programmatically:

**Before:**
```python
iface = InterfaceDefinition(
    element_type="waveplate",
)
iface.phase_shift_deg = 90.0  # Ad-hoc attribute
iface.fast_axis_deg = 0.0     # Ad-hoc attribute
```

**After:**
```python
iface = InterfaceDefinition(
    element_type="polarizing_interface",
    polarizer_subtype="waveplate",
    phase_shift_deg=90.0,
    fast_axis_deg=0.0,
)
```

### For Saved Files

Saved files with the old `"waveplate"` element_type will load correctly due to backward compatibility. They will be automatically converted to the new format when saved again.

## Summary

The Polarizing Interface system provides a clean, extensible framework for all polarization optics in Optiverse. It fixes the broken waveplate implementation while laying the groundwork for future additions like linear polarizers, circular polarizers, and Faraday rotators.

