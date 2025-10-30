# Zemax Import - Quick Start Guide

## Overview

You can now import Zemax ZMX files directly into OptiVerse! This allows you to use manufacturer-provided lens prescriptions (from Thorlabs, Edmund Optics, etc.) in your optical raytracing simulations.

## How It Works

### Zemax → OptiVerse Mapping

| Zemax Concept | OptiVerse Concept |
|---------------|-------------------|
| Sequential surfaces | `InterfaceDefinition` objects |
| GLAS (glass material) | `n1`, `n2` (refractive indices) |
| DISZ (thickness) | x-position in local coordinates |
| DIAM (diameter) | Interface line length |
| Multi-surface system | `ComponentRecord` with `interfaces_v2` |

### Example: AC254-100-B Achromatic Doublet

The provided Zemax file contains a Near-IR achromatic doublet with:
- **3 optical interfaces** (Air → N-LAK22 → N-SF6HT → Air)
- **Focal length**: 100mm
- **Clear aperture**: 12.7mm (0.5 inch)
- **Primary wavelength**: 855nm (Near-IR)

This maps to OptiVerse as:

```python
ComponentRecord(
  name="AC254-100-B Achromatic Doublet",
  kind="multi_element",
  object_height_mm=12.70,
  interfaces_v2=[
    InterfaceDefinition(
      x1_mm=0.00, y1_mm=-6.35,
      x2_mm=0.00, y2_mm=6.35,
      element_type='refractive_interface',
      name='S1: Air → N-LAK22',
      n1=1.0000,  # Air
      n2=1.6510   # N-LAK22 @ 855nm
    ),
    InterfaceDefinition(
      x1_mm=4.00, y1_mm=-6.35,    # 4mm from first surface
      x2_mm=4.00, y2_mm=6.35,
      element_type='refractive_interface',
      name='S2: N-LAK22 → N-SF6HT',
      n1=1.6510,  # N-LAK22
      n2=1.8050   # N-SF6HT @ 855nm
    ),
    InterfaceDefinition(
      x1_mm=5.50, y1_mm=-6.35,    # 5.5mm from first surface
      x2_mm=5.50, y2_mm=6.35,
      element_type='refractive_interface',
      name='S3: N-SF6HT → Air',
      n1=1.8050,  # N-SF6HT
      n2=1.0000   # Air
    ),
  ]
)
```

## Implementation Status

### ✅ Completed

1. **Zemax Parser** (`src/optiverse/services/zemax_parser.py`)
   - Parses ZMX files
   - Extracts surfaces, curvatures, thicknesses, materials, diameters
   - Handles wavelength data

2. **Glass Catalog** (`src/optiverse/services/glass_catalog.py`)
   - Refractive index database
   - Sellmeier equation calculations
   - Common Schott glasses (N-BK7, N-LAK22, N-SF6HT, etc.)

3. **Zemax → Interface Converter** (`src/optiverse/services/zemax_converter.py`)
   - Converts Zemax surfaces to `InterfaceDefinition` objects
   - Calculates positions from cumulative thicknesses
   - Maps glass materials to refractive indices

4. **Demo Script** (`examples/zemax_parse_simple.py`)
   - Standalone demonstration
   - No heavy dependencies
   - Shows complete mapping process

### 🚧 To Do (Future Enhancement)

5. **UI Integration** (Component Editor)
   - Add "Import Zemax…" button to toolbar
   - Load ZMX file → auto-populate interfaces
   - Visual editing of imported components

## Usage (Current)

### Testing the Parser

```bash
# Run the simple demo
python examples/zemax_parse_simple.py /path/to/file.zmx

# Example with your file:
python examples/zemax_parse_simple.py ~/Downloads/AC254-100-B-Zemax\(ZMX\).zmx
```

### Example Output

```
======================================================================
ZEMAX FILE PARSER - Simple Demonstration
======================================================================

Name: AC254-100-B NEAR IR ACHROMATS: Infinite Conjugate 100
Primary wavelength: 855.0 nm
Number of surfaces: 5

SURFACES:
----------------------------------------------------------------------

Surface 1:
  Radius: 66.68 mm
  Thickness to next: 4.00 mm
  Material: N-LAK22
  Diameter: 12.70 mm

  → OptiVerse Interface:
     Position: x=0.00 mm
     Height: 12.70 mm (±6.35 mm from axis)
     Indices: n₁=1.000 (Air) → n₂=1.651 (N-LAK22)
     Type: refractive_interface

Surface 2:
  Radius: -53.70 mm
  Thickness to next: 1.50 mm
  Material: N-SF6HT
  Diameter: 12.70 mm

  → OptiVerse Interface:
     Position: x=4.00 mm
     Height: 12.70 mm (±6.35 mm from axis)
     Indices: n₁=1.651 (N-LAK22) → n₂=1.805 (N-SF6HT)
     Type: refractive_interface

Surface 3:
  Radius: -259.41 mm
  Thickness to next: 97.09 mm
  Material: Air
  Diameter: 12.70 mm

  → OptiVerse Interface:
     Position: x=5.50 mm
     Height: 12.70 mm (±6.35 mm from axis)
     Indices: n₁=1.805 (N-SF6HT) → n₂=1.000 (Air)
     Type: refractive_interface
```

### Programmatic Usage

```python
from optiverse.services.zemax_parser import ZemaxParser
from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
from optiverse.services.glass_catalog import GlassCatalog

# Parse Zemax file
parser = ZemaxParser()
zemax_data = parser.parse("AC254-100-B.zmx")

# Convert to OptiVerse component
catalog = GlassCatalog()
converter = ZemaxToInterfaceConverter(catalog)
component = converter.convert(zemax_data)

# Access interfaces
for i, interface in enumerate(component.interfaces_v2):
    print(f"Interface {i+1}: {interface.name}")
    print(f"  Position: {interface.x1_mm:.2f} mm")
    print(f"  Indices: n={interface.n1:.4f} → {interface.n2:.4f}")

# Save to library
from optiverse.services.storage_service import StorageService
storage = StorageService()
storage.save_component(component)
```

## Files Created

```
src/optiverse/services/
  ├── zemax_parser.py          # Parse ZMX files
  ├── zemax_converter.py       # Convert to InterfaceDefinition
  └── glass_catalog.py         # Refractive index database

examples/
  └── zemax_parse_simple.py    # Standalone demo (no Qt dependencies)

docs/
  ├── ZEMAX_INTEGRATION_STRATEGY.md  # Detailed implementation strategy
  └── ZEMAX_IMPORT_QUICK_START.md    # This file
```

## Key Benefits

1. **Accurate Models**: Use manufacturer specs directly (no manual entry!)
2. **Standard Format**: Works with files from Thorlabs, Edmund Optics, Newport, etc.
3. **Multi-Element Support**: Handles complex systems (doublets, triplets, etc.)
4. **Correct Physics**: Automatic glass dispersion (Sellmeier equations)
5. **Seamless Integration**: Maps directly to existing `InterfaceDefinition` system

## Supported Features

### ✅ Currently Supported

- Sequential mode (MODE SEQ)
- Standard surfaces (TYPE STANDARD)
- Curvature (flat and curved surfaces)
- Glass materials (with Sellmeier dispersion)
- Surface spacing/thickness (DISZ)
- Diameters (DIAM)
- Multi-wavelength definitions
- Anti-reflection coatings (metadata only)

### 🔮 Future Enhancements

- Curved surface ray tracing (currently only flat interfaces)
- Aspheric surfaces
- Gradient index materials
- Non-sequential mode (NSC)
- CODE V and Oslo file formats
- Automatic lens catalog browser
- Tolerance analysis import
- Coating performance (beyond metadata)

## Glass Catalog

### Currently Included

- **Schott glasses**: N-BK7, N-LAK22, N-SF6HT, N-SF11, N-F2, SF11
- **Fused silica**: FUSED_SILICA, SILICA
- **Common materials**: WATER, SAPPHIRE

### Adding Custom Glasses

Edit `src/optiverse/services/glass_catalog.py`:

```python
self._catalog["MY-GLASS"] = {
    "formula": "Sellmeier",
    "manufacturer": "Custom",
    "coefficients": [B1, B2, B3, C1, C2, C3],
}
```

Sellmeier coefficients can be found in:
- Schott glass datasheets
- RefractiveIndex.INFO database
- Manufacturer catalogs

## Example Workflow

### Current (Command Line)

```bash
# 1. Download Zemax file from manufacturer website
# Example: Thorlabs AC254-100-B
wget https://www.thorlabs.com/.../AC254-100-B-Zemax.zmx

# 2. Parse and view mapping
python examples/zemax_parse_simple.py AC254-100-B-Zemax.zmx

# 3. Use programmatically (see code example above)
```

### Future (UI Integration)

```
1. Open Component Editor (Tools → Component Editor)
2. Click "Import Zemax…" button
3. Select ZMX file
4. Interfaces auto-populate
5. Optionally add component image
6. Save to library
7. Drag into main canvas and use in raytracing!
```

## Technical Details

### Coordinate System

- **Zemax**: Sequential along optical axis (z-axis)
- **OptiVerse**: Interfaces positioned in x-y plane
  - x-axis: Along optical axis (cumulative DISZ)
  - y-axis: Perpendicular (aperture height)
  
### Refractive Index Calculation

Uses Sellmeier equation:
```
n² - 1 = B₁λ²/(λ² - C₁) + B₂λ²/(λ² - C₂) + B₃λ²/(λ² - C₃)
```
where λ is wavelength in micrometers.

### Interface Positioning

```
Surface 1: x = 0.00 mm  (entry surface)
Surface 2: x = t₁       (t₁ = thickness of first element)
Surface 3: x = t₁ + t₂  (cumulative thickness)
...
```

## Testing

You can test the system with your own Zemax files:

```bash
# Test with the provided file
python examples/zemax_parse_simple.py ~/Downloads/AC254-100-B-Zemax\(ZMX\).zmx

# Expected output: 3 interfaces for achromatic doublet
# Interface 1: Air → N-LAK22
# Interface 2: N-LAK22 → N-SF6HT (cemented interface)
# Interface 3: N-SF6HT → Air
```

## Next Steps for Full Integration

To complete the UI integration:

1. **Add Import Button** to Component Editor toolbar
2. **File Dialog** for selecting ZMX files
3. **Auto-populate** interfaces in visual editor
4. **Preview** ray tracing through imported component
5. **Save to Library** with metadata
6. **Image Assignment** (optional, for visual reference)

See `docs/ZEMAX_INTEGRATION_STRATEGY.md` for complete implementation plan.

## References

- **Zemax File Format**: OpticStudio Programming Guide
- **Sellmeier Equation**: Born & Wolf, "Principles of Optics"
- **Schott Catalog**: https://www.schott.com/advanced_optics/
- **RefractiveIndex.INFO**: https://refractiveindex.info/

## Questions?

This integration demonstrates the power of OptiVerse's interface-based component model. The natural mapping from Zemax surfaces to `InterfaceDefinition` objects means you can leverage industry-standard lens prescriptions in your simulations without manual data entry!

