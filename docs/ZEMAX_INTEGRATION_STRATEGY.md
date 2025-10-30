# Zemax File Integration Strategy

## Overview

This document outlines a comprehensive strategy for importing Zemax ZMX files into the Optiverse optical raytracing system, mapping Zemax surface definitions to the existing `InterfaceDefinition` concept.

## Zemax File Analysis

### Sample File: AC254-100-B (Achromatic Doublet)

The provided Zemax file defines a **Near-IR achromatic doublet lens** with these key elements:

```
SURF 0: Object surface (at infinity)
SURF 1: First refractive surface
  - CURV: 1.499700E-2 (R = 66.67 mm)
  - DISZ: 4.0 mm (thickness to next surface)
  - GLAS: N-LAK22 (glass material)
  - DIAM: 12.7 mm (clear aperture)
  - COAT: THORB (broadband coating)

SURF 2: Second refractive surface (cemented interface)
  - CURV: -1.862197E-2 (R = -53.70 mm)
  - DISZ: 1.5 mm
  - GLAS: N-SF6HT (second glass)

SURF 3: Third refractive surface (exit surface)
  - CURV: -3.854902E-3 (R = -259.48 mm)
  - DISZ: 97.09 mm (working distance to focal plane)
  - COAT: THORBSLAH64 (AR coating)

SURF 4: Image surface (focal plane)
```

### Key Zemax Concepts

1. **Sequential Mode**: Surfaces are defined in order along optical axis
2. **CURV (Curvature)**: 1/R where R is radius of curvature (mm)
3. **DISZ (Distance)**: Thickness/spacing to next surface (mm)
4. **GLAS (Glass)**: Material catalog reference (e.g., N-LAK22)
5. **DIAM (Diameter)**: Clear aperture diameter (mm)
6. **COAT (Coating)**: Anti-reflection or other optical coating

## Mapping to InterfaceDefinition System

### Current Interface System

Your `InterfaceDefinition` class supports:
- **Geometry**: (x1_mm, y1_mm) to (x2_mm, y2_mm) in local coordinates
- **Element types**: `lens`, `mirror`, `beam_splitter`, `dichroic`, `refractive_interface`
- **Refractive properties**: `n1`, `n2` (incident and transmitted indices)
- **Multi-interface components**: `ComponentRecord.interfaces_v2: List[InterfaceDefinition]`

### Zemax Surface → Interface Mapping

Each Zemax surface becomes a `refractive_interface` with these mappings:

| Zemax Property | InterfaceDefinition Field | Transformation |
|----------------|---------------------------|----------------|
| Surface position | (x1_mm, y1_mm, x2_mm, y2_mm) | Calculate from cumulative DISZ |
| GLAS (before) | n1 | Lookup from glass catalog |
| GLAS (after) | n2 | Lookup from glass catalog |
| CURV | *Computed property* | Store curvature for future curved surface support |
| DIAM | length_mm() | Convert diameter to interface line length |
| Surface name | name | e.g., "Surface 1: N-LAK22 Entry" |

### Example Mapping: AC254-100-B

```python
# Surface 1: Air → N-LAK22
InterfaceDefinition(
    x1_mm=0.0,
    y1_mm=-6.35,  # Half of 12.7mm diameter
    x2_mm=0.0,
    y2_mm=6.35,
    element_type="refractive_interface",
    name="S1: Air → N-LAK22",
    n1=1.0,      # Air
    n2=1.651,    # N-LAK22 @ 706.5nm
)

# Surface 2: N-LAK22 → N-SF6HT (cemented interface)
InterfaceDefinition(
    x1_mm=4.0,   # Cumulative thickness
    y1_mm=-6.35,
    x2_mm=4.0,
    y2_mm=6.35,
    element_type="refractive_interface",
    name="S2: N-LAK22 → N-SF6HT",
    n1=1.651,    # N-LAK22
    n2=1.805,    # N-SF6HT @ 706.5nm
)

# Surface 3: N-SF6HT → Air (exit surface)
InterfaceDefinition(
    x1_mm=5.5,   # 4.0 + 1.5mm
    y1_mm=-6.35,
    x2_mm=5.5,
    y2_mm=6.35,
    element_type="refractive_interface",
    name="S3: N-SF6HT → Air",
    n1=1.805,    # N-SF6HT
    n2=1.0,      # Air
)
```

### Component Record Structure

```python
ComponentRecord(
    name="AC254-100-B Achromatic Doublet",
    interfaces_v2=[surface1, surface2, surface3],
    object_height_mm=12.7,  # From DIAM
    kind="multi_element",   # Auto-computed from interfaces_v2
    notes="Imported from Zemax: AC254-100-B NEAR IR ACHROMATS: 100mm EFL",
)
```

## Implementation Strategy

### Phase 1: Zemax Parser Module

Create `src/optiverse/services/zemax_parser.py`:

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
import re

@dataclass
class ZemaxSurface:
    """Parsed Zemax surface data."""
    number: int
    type: str = "STANDARD"
    curvature: float = 0.0  # 1/mm
    thickness: float = 0.0  # mm to next surface
    glass: str = ""
    diameter: float = 0.0  # mm
    coating: str = ""
    comment: str = ""
    is_stop: bool = False
    
    @property
    def radius_mm(self) -> float:
        """Radius of curvature (mm)."""
        return 1.0 / self.curvature if abs(self.curvature) > 1e-10 else float('inf')

@dataclass
class ZemaxFile:
    """Parsed Zemax file data."""
    name: str
    mode: str  # SEQ or NSC
    wavelengths_um: List[float]
    primary_wavelength_um: float
    surfaces: List[ZemaxSurface]
    notes: List[str]
    
class ZemaxParser:
    """Parser for Zemax ZMX files."""
    
    def parse(self, filepath: str) -> Optional[ZemaxFile]:
        """Parse a Zemax ZMX file."""
        # Implementation: Parse line by line
        # Extract SURF blocks, WAVM, NAME, NOTE, etc.
        pass
    
    def _parse_surface_block(self, lines: List[str]) -> ZemaxSurface:
        """Parse a SURF block."""
        # Extract CURV, DISZ, GLAS, DIAM, COAT, COMM, STOP
        pass
```

### Phase 2: Glass Catalog Database

Create `src/optiverse/services/glass_catalog.py`:

```python
from typing import Optional
import json

class GlassCatalog:
    """
    Refractive index database for optical materials.
    
    Supports:
    - Schott glass catalog
    - Infrared materials
    - Custom materials
    """
    
    def __init__(self):
        self._catalog: Dict[str, Dict] = {}
        self._load_builtin_catalog()
    
    def get_refractive_index(
        self, 
        glass_name: str, 
        wavelength_um: float = 0.7065
    ) -> Optional[float]:
        """
        Get refractive index for glass at specified wavelength.
        
        Args:
            glass_name: Material name (e.g., "N-LAK22", "N-SF6HT")
            wavelength_um: Wavelength in micrometers
            
        Returns:
            Refractive index, or None if not found
        """
        glass_name = glass_name.upper().strip()
        
        if glass_name not in self._catalog:
            return None
        
        glass_data = self._catalog[glass_name]
        
        # Use Sellmeier equation or interpolation
        return self._calculate_index(glass_data, wavelength_um)
    
    def _calculate_index(self, glass_data: Dict, wavelength_um: float) -> float:
        """Calculate index using Sellmeier or Cauchy formula."""
        # Implementation: Sellmeier coefficients
        # n² - 1 = Σ(Bi * λ² / (λ² - Ci))
        pass
    
    def _load_builtin_catalog(self):
        """Load built-in glass catalog from JSON."""
        # Start with common glasses
        self._catalog = {
            "N-LAK22": {
                "type": "Schott",
                "formula": "Sellmeier",
                "coefficients": [1.14229781, 0.535138441, 1.04088385,
                                0.00585778594, 0.0198546147, 100.834017],
            },
            "N-SF6HT": {
                "type": "Schott",
                "formula": "Sellmeier",
                "coefficients": [1.77931763, 0.338149866, 2.08734474,
                                0.0133714182, 0.0617533621, 174.01759],
            },
            "BK7": {
                "type": "Schott",
                "formula": "Sellmeier",
                "coefficients": [1.03961212, 0.231792344, 1.01046945,
                                0.00600069867, 0.0200179144, 103.560653],
            },
            # Add more as needed
        }
```

### Phase 3: Zemax to Interface Converter

Create `src/optiverse/services/zemax_converter.py`:

```python
from typing import List
from ..core.interface_definition import InterfaceDefinition
from ..core.models import ComponentRecord
from .zemax_parser import ZemaxFile, ZemaxSurface
from .glass_catalog import GlassCatalog

class ZemaxToInterfaceConverter:
    """Convert Zemax surfaces to InterfaceDefinition objects."""
    
    def __init__(self, glass_catalog: GlassCatalog):
        self.catalog = glass_catalog
    
    def convert(self, zemax_file: ZemaxFile) -> ComponentRecord:
        """
        Convert Zemax file to ComponentRecord with interfaces.
        
        Returns:
            ComponentRecord with interfaces_v2 populated
        """
        interfaces: List[InterfaceDefinition] = []
        cumulative_thickness = 0.0
        current_material = ""  # Start in air
        
        for i, surf in enumerate(zemax_file.surfaces):
            if surf.type == "STANDARD" and surf.number > 0:
                # Skip object surface (surf 0) and image surface
                if i == len(zemax_file.surfaces) - 1:
                    break
                
                # Get refractive indices
                n1 = self._get_index(current_material, zemax_file.primary_wavelength_um)
                n2 = self._get_index(surf.glass, zemax_file.primary_wavelength_um)
                
                # Create interface
                interface = self._create_interface(
                    surf, 
                    cumulative_thickness, 
                    n1, 
                    n2,
                    zemax_file.primary_wavelength_um
                )
                interfaces.append(interface)
                
                # Update for next surface
                cumulative_thickness += surf.thickness
                current_material = surf.glass if surf.glass else ""
        
        # Create component record
        # Use first surface diameter for object_height_mm
        diameter_mm = zemax_file.surfaces[1].diameter if len(zemax_file.surfaces) > 1 else 25.4
        
        return ComponentRecord(
            name=zemax_file.name,
            interfaces_v2=interfaces,
            object_height_mm=diameter_mm,
            kind="multi_element",
            notes=f"Imported from Zemax\n" + "\n".join(zemax_file.notes[:2])
        )
    
    def _create_interface(
        self,
        surf: ZemaxSurface,
        x_pos: float,
        n1: float,
        n2: float,
        wavelength_um: float
    ) -> InterfaceDefinition:
        """Create InterfaceDefinition from Zemax surface."""
        half_diameter = surf.diameter / 2.0
        
        # For now, create flat interfaces (vertical lines)
        # Future: Support curved surfaces using curvature
        return InterfaceDefinition(
            x1_mm=x_pos,
            y1_mm=-half_diameter,
            x2_mm=x_pos,
            y2_mm=half_diameter,
            element_type="refractive_interface",
            name=f"S{surf.number}: {self._material_name(n1)} → {self._material_name(n2)}",
            n1=n1,
            n2=n2,
        )
    
    def _get_index(self, material: str, wavelength_um: float) -> float:
        """Get refractive index, defaulting to air if empty."""
        if not material or material.upper() in ["", "AIR", "VACUUM"]:
            return 1.0
        
        index = self.catalog.get_refractive_index(material, wavelength_um)
        if index is None:
            # Fallback: assume common glass
            return 1.5
        return index
    
    def _material_name(self, n: float) -> str:
        """Generate readable material name from index."""
        if abs(n - 1.0) < 0.01:
            return "Air"
        return f"n={n:.3f}"
```

### Phase 4: UI Integration

Add to `ComponentEditor` in `component_editor_dialog.py`:

```python
class ComponentEditor(QtWidgets.QMainWindow):
    # ... existing code ...
    
    def _build_toolbar(self):
        # ... existing actions ...
        
        tb.addSeparator()
        
        # Add Zemax import action
        act_import_zemax = QtGui.QAction("Import Zemax…", self)
        act_import_zemax.triggered.connect(self._import_zemax)
        tb.addAction(act_import_zemax)
    
    def _import_zemax(self):
        """Import Zemax ZMX file."""
        from ...services.zemax_parser import ZemaxParser
        from ...services.zemax_converter import ZemaxToInterfaceConverter
        from ...services.glass_catalog import GlassCatalog
        
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import Zemax File",
            "",
            "Zemax Files (*.zmx *.ZMX);;All Files (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            # Parse Zemax file
            parser = ZemaxParser()
            zemax_data = parser.parse(filepath)
            
            if not zemax_data:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Import Error",
                    "Failed to parse Zemax file."
                )
                return
            
            # Convert to interfaces
            catalog = GlassCatalog()
            converter = ZemaxToInterfaceConverter(catalog)
            component = converter.convert(zemax_data)
            
            # Load into editor
            self._load_component_record(component)
            
            self.statusBar().showMessage(
                f"Imported {len(component.interfaces_v2)} interfaces from Zemax"
            )
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Import Error",
                f"Error importing Zemax file:\n{str(e)}"
            )
    
    def _load_component_record(self, component: ComponentRecord):
        """Load a ComponentRecord into the editor."""
        # Clear existing
        self.canvas.clear_points()
        
        # Set component properties
        self.name_edit.setText(component.name)
        self.length_edit.setValue(component.object_height_mm)
        
        # Load interfaces
        if component.interfaces_v2:
            self._interfaces = component.interfaces_v2.copy()
            self._sync_interfaces_to_canvas()
            self._refresh_interface_tree()
```

## Phase 5: Advanced Features

### 5.1 Curved Surface Support

Future enhancement: Support curved interfaces with radius of curvature

```python
@dataclass
class InterfaceDefinition:
    # ... existing fields ...
    
    # Curved surface properties (optional)
    radius_of_curvature_mm: Optional[float] = None  # None = flat
    is_curved: bool = False
    center_of_curvature_x: float = 0.0
    center_of_curvature_y: float = 0.0
```

### 5.2 Lens Group Recognition

Automatically detect and classify lens groups:
- Singlets (1 interface)
- Doublets (2 elements, 3 interfaces)
- Triplets (3 elements, 4 interfaces)
- Zoom groups

### 5.3 Ray Tracing Through Curved Surfaces

Extend ray tracing engine to handle curved surfaces:
1. Calculate ray-sphere intersection
2. Apply Snell's law at curved interface
3. Handle total internal reflection

### 5.4 Zemax Export

Allow exporting OptiVerse components back to Zemax format:
- Reverse mapping: InterfaceDefinition → SURF blocks
- Generate proper prescription file
- Include glass materials and coatings

## Usage Workflow

### For Users

1. **Open Component Editor**: Menu → Tools → Component Editor
2. **Import Zemax File**: Toolbar → "Import Zemax…"
3. **Select ZMX file**: Navigate to downloaded Thorlabs/Edmund/etc. Zemax files
4. **Review Interfaces**: Interfaces automatically populate
5. **Adjust if needed**: Edit positions, refractive indices
6. **Add Image** (optional): Drag product image for visual reference
7. **Save to Library**: Saves as multi-element component

### Example: Achromatic Doublet

```python
# User workflow (automated by UI):
editor = ComponentEditor(storage_service)
editor.show()

# Import button clicked
zemax_file = parse_zemax("AC254-100-B.zmx")
# → 3 interfaces created automatically
# → Interface 1: Air → N-LAK22 (n=1.0 → 1.651)
# → Interface 2: N-LAK22 → N-SF6HT (n=1.651 → 1.805)
# → Interface 3: N-SF6HT → Air (n=1.805 → 1.0)

# Visual editor shows:
# - Drag endpoints to adjust positions
# - Click interface to edit n1, n2
# - Real-time ray tracing preview

# Save to library
# → Can now use in main canvas like any other component
```

## Benefits

1. **Accurate Models**: Use manufacturer-provided Zemax files
2. **No Manual Entry**: Automatic extraction of all parameters
3. **Glass Database**: Correct refractive indices at any wavelength
4. **Complex Optics**: Support multi-element systems (doublets, triplets, etc.)
5. **Standard Format**: Compatible with Thorlabs, Edmund Optics, Newport, etc.
6. **Full Integration**: Works seamlessly with existing interface system

## File Structure

```
src/optiverse/
  services/
    zemax_parser.py          # Parse ZMX files
    zemax_converter.py       # Convert to InterfaceDefinition
    glass_catalog.py         # Refractive index database
    glass_data/              # JSON files with glass data
      schott_catalog.json
      infrared_catalog.json
      custom_glasses.json
```

## Testing Strategy

1. **Unit Tests**: Parse known Zemax files
2. **Conversion Tests**: Verify interface generation
3. **Index Tests**: Check glass catalog lookups
4. **Integration Tests**: Import → Edit → Raytrace workflow
5. **Sample Files**: Include test ZMX files from various vendors

## Future Enhancements

1. **CODE V Support**: Parse .seq files
2. **Oslo Support**: Parse .osd files
3. **Lens Catalog Browser**: Browse built-in lens library
4. **Automatic Lens Selection**: Suggest lenses for desired focal length
5. **Aberration Display**: Show chromatic/spherical aberration
6. **Tolerance Analysis**: Import tolerance data from Zemax

## Conclusion

This strategy provides a complete pathway from industry-standard Zemax files to your existing `InterfaceDefinition` system. The mapping is natural:
- **Zemax surfaces** → **refractive interfaces**
- **Sequential thickness** → **x-position in local coordinates**
- **Glass materials** → **n1, n2 refractive indices**
- **Multi-surface systems** → **multi_element components**

The implementation can be done incrementally, with Phase 1-3 providing basic import capability, and later phases adding advanced features like curved surfaces and bidirectional export.

