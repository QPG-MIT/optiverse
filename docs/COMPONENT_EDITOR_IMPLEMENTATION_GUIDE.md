# Component Editor Generalization - Implementation Guide

## Quick Start

This guide provides step-by-step instructions for implementing the generalized component editor.

## Prerequisites

- Review `docs/COMPONENT_EDITOR_GENERALIZATION_STRATEGY.md` for overall strategy
- Review `docs/COMPONENT_EDITOR_UI_MOCKUP.md` for UI design
- Ensure existing tests pass before starting

## Phase 1: Data Model (Days 1-2)

### Step 1.1: Create InterfaceDefinition Class

**File**: `src/optiverse/core/interface_definition.py` (NEW)

```python
"""Interface definition data model for generalized component editor."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class InterfaceDefinition:
    """
    Definition of a single optical interface in a component.
    
    Each interface represents an optical element (lens, mirror, beam splitter, etc.)
    with specific geometry and optical properties.
    """
    
    # Geometry (in millimeters, local coordinate system)
    x1_mm: float = 0.0
    y1_mm: float = 0.0
    x2_mm: float = 10.0
    y2_mm: float = 0.0
    
    # Element type
    element_type: str = "refractive_interface"  # lens, mirror, beam_splitter, dichroic, refractive_interface
    
    # Common properties
    name: str = ""  # Optional user-defined name
    
    # Lens properties
    efl_mm: float = 100.0  # Effective focal length
    
    # Mirror properties
    reflectivity: float = 99.0  # Percentage
    
    # Beam splitter properties
    split_T: float = 50.0  # Transmission percentage
    split_R: float = 50.0  # Reflection percentage
    is_polarizing: bool = False
    pbs_transmission_axis_deg: float = 0.0
    
    # Dichroic properties
    cutoff_wavelength_nm: float = 550.0
    transition_width_nm: float = 50.0
    pass_type: str = "longpass"  # "longpass" | "shortpass"
    
    # Refractive interface properties
    n1: float = 1.0  # Incident refractive index
    n2: float = 1.5  # Transmitted refractive index
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'x1_mm': self.x1_mm,
            'y1_mm': self.y1_mm,
            'x2_mm': self.x2_mm,
            'y2_mm': self.y2_mm,
            'element_type': self.element_type,
            'name': self.name,
            'efl_mm': self.efl_mm,
            'reflectivity': self.reflectivity,
            'split_T': self.split_T,
            'split_R': self.split_R,
            'is_polarizing': self.is_polarizing,
            'pbs_transmission_axis_deg': self.pbs_transmission_axis_deg,
            'cutoff_wavelength_nm': self.cutoff_wavelength_nm,
            'transition_width_nm': self.transition_width_nm,
            'pass_type': self.pass_type,
            'n1': self.n1,
            'n2': self.n2,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterfaceDefinition':
        """Deserialize from dictionary."""
        return cls(
            x1_mm=data.get('x1_mm', 0.0),
            y1_mm=data.get('y1_mm', 0.0),
            x2_mm=data.get('x2_mm', 10.0),
            y2_mm=data.get('y2_mm', 0.0),
            element_type=data.get('element_type', 'refractive_interface'),
            name=data.get('name', ''),
            efl_mm=data.get('efl_mm', 100.0),
            reflectivity=data.get('reflectivity', 99.0),
            split_T=data.get('split_T', 50.0),
            split_R=data.get('split_R', 50.0),
            is_polarizing=data.get('is_polarizing', False),
            pbs_transmission_axis_deg=data.get('pbs_transmission_axis_deg', 0.0),
            cutoff_wavelength_nm=data.get('cutoff_wavelength_nm', 550.0),
            transition_width_nm=data.get('transition_width_nm', 50.0),
            pass_type=data.get('pass_type', 'longpass'),
            n1=data.get('n1', 1.0),
            n2=data.get('n2', 1.5),
        )
    
    def get_color(self) -> tuple[int, int, int]:
        """Get display color based on element type."""
        colors = {
            'lens': (0, 180, 180),           # Cyan
            'mirror': (255, 140, 0),         # Orange
            'beam_splitter': (0, 150, 120) if not self.is_polarizing else (150, 0, 150),  # Green or Purple
            'dichroic': (255, 0, 255),       # Magenta
            'refractive_interface': (100, 100, 255),  # Blue
        }
        return colors.get(self.element_type, (150, 150, 150))
    
    def get_label(self) -> str:
        """Get display label."""
        if self.name:
            return self.name
        
        type_labels = {
            'lens': f'Lens ({self.efl_mm:.1f}mm)',
            'mirror': 'Mirror',
            'beam_splitter': f'BS ({self.split_T:.0f}/{self.split_R:.0f})',
            'dichroic': f'Dichroic ({self.cutoff_wavelength_nm:.0f}nm)',
            'refractive_interface': f'n={self.n1:.3f}→{self.n2:.3f}',
        }
        return type_labels.get(self.element_type, 'Interface')
    
    def length_mm(self) -> float:
        """Calculate interface length in mm."""
        dx = self.x2_mm - self.x1_mm
        dy = self.y2_mm - self.y1_mm
        return (dx**2 + dy**2)**0.5
```

**Test**: `tests/core/test_interface_definition.py` (NEW)

```python
"""Tests for InterfaceDefinition."""

import pytest
from optiverse.core.interface_definition import InterfaceDefinition


def test_interface_definition_default():
    """Test default interface creation."""
    iface = InterfaceDefinition()
    assert iface.element_type == "refractive_interface"
    assert iface.x1_mm == 0.0
    assert iface.n1 == 1.0


def test_interface_definition_serialization():
    """Test serialization round-trip."""
    iface = InterfaceDefinition(
        x1_mm=-10.0, y1_mm=5.0,
        x2_mm=10.0, y2_mm=5.0,
        element_type="lens",
        efl_mm=50.0
    )
    
    data = iface.to_dict()
    iface2 = InterfaceDefinition.from_dict(data)
    
    assert iface2.x1_mm == iface.x1_mm
    assert iface2.element_type == "lens"
    assert iface2.efl_mm == 50.0


def test_interface_colors():
    """Test color coding."""
    lens = InterfaceDefinition(element_type="lens")
    assert lens.get_color() == (0, 180, 180)  # Cyan
    
    mirror = InterfaceDefinition(element_type="mirror")
    assert mirror.get_color() == (255, 140, 0)  # Orange
    
    bs = InterfaceDefinition(element_type="beam_splitter")
    assert bs.get_color() == (0, 150, 120)  # Green
    
    pbs = InterfaceDefinition(element_type="beam_splitter", is_polarizing=True)
    assert pbs.get_color() == (150, 0, 150)  # Purple


def test_interface_length():
    """Test length calculation."""
    iface = InterfaceDefinition(
        x1_mm=0.0, y1_mm=0.0,
        x2_mm=3.0, y2_mm=4.0
    )
    assert iface.length_mm() == pytest.approx(5.0)
```

### Step 1.2: Create Interface Type Registry

**File**: `src/optiverse/core/interface_types.py` (NEW)

```python
"""Interface type registry and metadata."""

from typing import Dict, List, Any


INTERFACE_TYPES = {
    'lens': {
        'name': 'Lens',
        'description': 'Thin lens with specified focal length',
        'color': (0, 180, 180),
        'emoji': '🔵',
        'properties': ['efl_mm'],
        'property_labels': {
            'efl_mm': 'Effective Focal Length',
        },
        'property_units': {
            'efl_mm': 'mm',
        },
        'property_ranges': {
            'efl_mm': (-10000, 10000),
        },
    },
    'mirror': {
        'name': 'Mirror',
        'description': 'Reflective surface',
        'color': (255, 140, 0),
        'emoji': '🟠',
        'properties': ['reflectivity'],
        'property_labels': {
            'reflectivity': 'Reflectivity',
        },
        'property_units': {
            'reflectivity': '%',
        },
        'property_ranges': {
            'reflectivity': (0, 100),
        },
    },
    'beam_splitter': {
        'name': 'Beam Splitter',
        'description': 'Partially transmitting/reflecting coating',
        'color': (0, 150, 120),
        'emoji': '🟢',
        'properties': ['split_T', 'split_R', 'is_polarizing', 'pbs_transmission_axis_deg'],
        'property_labels': {
            'split_T': 'Transmission',
            'split_R': 'Reflection',
            'is_polarizing': 'Polarizing (PBS)',
            'pbs_transmission_axis_deg': 'PBS Transmission Axis',
        },
        'property_units': {
            'split_T': '%',
            'split_R': '%',
            'pbs_transmission_axis_deg': '°',
        },
        'property_ranges': {
            'split_T': (0, 100),
            'split_R': (0, 100),
            'pbs_transmission_axis_deg': (-180, 180),
        },
    },
    'dichroic': {
        'name': 'Dichroic',
        'description': 'Wavelength-selective filter',
        'color': (255, 0, 255),
        'emoji': '🟣',
        'properties': ['cutoff_wavelength_nm', 'transition_width_nm', 'pass_type'],
        'property_labels': {
            'cutoff_wavelength_nm': 'Cutoff Wavelength',
            'transition_width_nm': 'Transition Width',
            'pass_type': 'Pass Type',
        },
        'property_units': {
            'cutoff_wavelength_nm': 'nm',
            'transition_width_nm': 'nm',
        },
        'property_ranges': {
            'cutoff_wavelength_nm': (200, 2000),
            'transition_width_nm': (1, 200),
        },
    },
    'refractive_interface': {
        'name': 'Refractive Interface',
        'description': 'Boundary between two media',
        'color': (100, 100, 255),
        'emoji': '🔵',
        'properties': ['n1', 'n2'],
        'property_labels': {
            'n1': 'Incident Index (n₁)',
            'n2': 'Transmitted Index (n₂)',
        },
        'property_units': {
            'n1': '',
            'n2': '',
        },
        'property_ranges': {
            'n1': (1.0, 3.0),
            'n2': (1.0, 3.0),
        },
    },
}


def get_type_info(element_type: str) -> Dict[str, Any]:
    """Get metadata for an interface type."""
    return INTERFACE_TYPES.get(element_type, {})


def get_property_label(element_type: str, prop_name: str) -> str:
    """Get human-readable label for a property."""
    type_info = get_type_info(element_type)
    return type_info.get('property_labels', {}).get(prop_name, prop_name)


def get_property_unit(element_type: str, prop_name: str) -> str:
    """Get unit for a property."""
    type_info = get_type_info(element_type)
    return type_info.get('property_units', {}).get(prop_name, '')


def get_property_range(element_type: str, prop_name: str) -> tuple[float, float]:
    """Get valid range for a property."""
    type_info = get_type_info(element_type)
    return type_info.get('property_ranges', {}).get(prop_name, (-1e10, 1e10))


def get_type_color(element_type: str) -> tuple[int, int, int]:
    """Get color for an interface type."""
    return get_type_info(element_type).get('color', (150, 150, 150))
```

### Step 1.3: Update ComponentRecord

**File**: `src/optiverse/core/models.py` (MODIFY)

```python
# Add at top:
from .interface_definition import InterfaceDefinition

# Update ComponentRecord:
@dataclass
class ComponentRecord:
    """
    Persistent component data for library storage.
    
    GENERALIZED INTERFACE-BASED DESIGN:
    - Component is a container for named interfaces
    - Each interface has its own element type and properties
    - Backward compatibility maintained via migration
    """
    name: str
    object_height_mm: float
    interfaces: List[InterfaceDefinition] = field(default_factory=list)
    notes: str = ""
    
    # DEPRECATED: Legacy fields kept for backward compatibility
    kind: str = ""  # Auto-computed from interfaces
    image_path: str = ""
    line_px: Tuple[float, float, float, float] = (0, 0, 0, 0)
    efl_mm: float = 0.0
    split_TR: Tuple[float, float] = (50.0, 50.0)
    # ... other legacy fields ...
    
    def __post_init__(self):
        """Initialize and migrate legacy data if needed."""
        if not self.interfaces and self.kind:
            # Legacy component - migrate to interface format
            self._migrate_from_legacy()
        
        # Auto-compute kind from interfaces
        if self.interfaces:
            self.kind = self._compute_kind()
    
    def _migrate_from_legacy(self):
        """Convert legacy component to interface-based format."""
        # Implementation in Step 1.4
        pass
    
    def _compute_kind(self) -> str:
        """Compute component kind from interfaces."""
        if len(self.interfaces) == 0:
            return "empty"
        elif len(self.interfaces) == 1:
            return self.interfaces[0].element_type
        else:
            return "multi_element"
```

### Step 1.4: Implement Migration Utilities

**File**: `src/optiverse/core/component_migration.py` (NEW)

```python
"""Migration utilities for legacy component format."""

from typing import Dict, Any
from .models import ComponentRecord
from .interface_definition import InterfaceDefinition


def migrate_legacy_component(data: Dict[str, Any]) -> ComponentRecord:
    """
    Migrate legacy component format to new interface-based format.
    
    Legacy formats:
    1. Simple component (lens, mirror, beamsplitter, dichroic)
       - Has 'kind' field
       - Has 'line_px' for calibration
       - Type-specific properties at top level
    
    2. Refractive object
       - Has 'kind' = 'refractive_object'
       - Has 'interfaces' list with old schema
    """
    kind = data.get('kind', '')
    
    if kind == 'refractive_object':
        return _migrate_refractive_object(data)
    elif kind in ('lens', 'mirror', 'beamsplitter', 'dichroic'):
        return _migrate_simple_component(data)
    else:
        # Unknown format - create empty
        return ComponentRecord(
            name=data.get('name', 'Unknown'),
            object_height_mm=data.get('object_height_mm', 25.4),
            interfaces=[],
        )


def _migrate_simple_component(data: Dict[str, Any]) -> ComponentRecord:
    """Migrate simple component to single interface."""
    kind = data['kind']
    
    # Create single interface from component properties
    if kind == 'lens':
        interface = InterfaceDefinition(
            element_type='lens',
            efl_mm=data.get('efl_mm', 100.0),
        )
    elif kind == 'mirror':
        interface = InterfaceDefinition(
            element_type='mirror',
        )
    elif kind == 'beamsplitter':
        interface = InterfaceDefinition(
            element_type='beam_splitter',
            split_T=data.get('split_TR', (50, 50))[0],
            split_R=data.get('split_TR', (50, 50))[1],
        )
    elif kind == 'dichroic':
        interface = InterfaceDefinition(
            element_type='dichroic',
            cutoff_wavelength_nm=data.get('cutoff_wavelength_nm', 550.0),
            transition_width_nm=data.get('transition_width_nm', 50.0),
            pass_type=data.get('pass_type', 'longpass'),
        )
    else:
        interface = InterfaceDefinition()
    
    # Convert line_px to mm coordinates
    # (This requires knowing mm_per_px, which we'll compute from object_height)
    line_px = data.get('line_px', (0, 0, 100, 100))
    object_height_mm = data.get('object_height_mm', 25.4)
    
    # Compute line length in pixels (normalized 1000px space)
    dx = line_px[2] - line_px[0]
    dy = line_px[3] - line_px[1]
    line_length_px = (dx**2 + dy**2)**0.5
    
    if line_length_px > 0:
        mm_per_px = object_height_mm / line_length_px
        
        # Convert to mm (origin at image center)
        interface.x1_mm = (line_px[0] - 500) * mm_per_px
        interface.y1_mm = (line_px[1] - 500) * mm_per_px
        interface.x2_mm = (line_px[2] - 500) * mm_per_px
        interface.y2_mm = (line_px[3] - 500) * mm_per_px
    
    return ComponentRecord(
        name=data.get('name', ''),
        object_height_mm=object_height_mm,
        interfaces=[interface],
        notes=data.get('notes', ''),
    )


def _migrate_refractive_object(data: Dict[str, Any]) -> ComponentRecord:
    """Migrate refractive object to interface list."""
    legacy_interfaces = data.get('interfaces', [])
    object_height_mm = data.get('object_height_mm', 25.4)
    
    # Legacy interfaces have pixel coordinates - need to convert to mm
    # Use first interface as calibration reference
    interfaces = []
    
    for i, old_iface in enumerate(legacy_interfaces):
        # Determine element type from properties
        if old_iface.get('is_beam_splitter', False):
            element_type = 'beam_splitter'
        else:
            element_type = 'refractive_interface'
        
        interface = InterfaceDefinition(
            element_type=element_type,
            n1=old_iface.get('n1', 1.0),
            n2=old_iface.get('n2', 1.5),
            split_T=old_iface.get('split_T', 50.0),
            split_R=old_iface.get('split_R', 50.0),
            is_polarizing=old_iface.get('is_polarizing', False),
            pbs_transmission_axis_deg=old_iface.get('pbs_transmission_axis_deg', 0.0),
        )
        
        # Convert pixel coords to mm
        # (Similar to above, but may need different reference)
        x1_px = old_iface.get('x1_px', 0)
        y1_px = old_iface.get('y1_px', 0)
        x2_px = old_iface.get('x2_px', 100)
        y2_px = old_iface.get('y2_px', 100)
        
        # For now, store as-is and convert during render
        # TODO: Implement proper coordinate conversion
        interface.x1_mm = x1_px
        interface.y1_mm = y1_px
        interface.x2_mm = x2_px
        interface.y2_mm = y2_px
        
        interfaces.append(interface)
    
    return ComponentRecord(
        name=data.get('name', ''),
        object_height_mm=object_height_mm,
        interfaces=interfaces,
        notes=data.get('notes', ''),
    )
```

## Phase 2: UI Widgets (Days 3-5)

### Step 2.1: Create CollapsibleInterfaceWidget

**File**: `src/optiverse/ui/widgets/collapsible_interface_widget.py` (NEW)

See full implementation in strategy document. Key points:

- Header with expand/collapse toggle
- Element type dropdown
- Coordinate spinboxes (x1, y1, x2, y2 in mm)
- Dynamic property panel based on element type
- Color indicator matching canvas

### Step 2.2: Create InterfacePropertiesPanel

**File**: `src/optiverse/ui/widgets/interface_properties_panel.py` (NEW)

Manages stack of CollapsibleInterfaceWidget instances.

### Step 2.3: Update ComponentEditor

**File**: `src/optiverse/ui/views/component_editor_dialog.py` (MAJOR REFACTOR)

- Remove `kind_combo`
- Remove type-specific property fields
- Add `InterfacePropertiesPanel`
- Update synchronization logic

## Phase 3: Testing (Day 6)

### Unit Tests
```bash
pytest tests/core/test_interface_definition.py
pytest tests/core/test_component_migration.py
```

### Integration Tests
```bash
pytest tests/ui/test_component_editor.py
```

### Manual Testing
- Load existing library components
- Create new components
- Test all interface types
- Verify coordinate conversion

## Phase 4: Documentation (Day 7)

- Update user documentation
- Create migration guide
- Update API documentation
- Create video tutorial

## Rollout Plan

### Stage 1: Alpha (Internal Testing)
- Deploy to test environment
- Load production library
- Verify all components work

### Stage 2: Beta (Limited Release)
- Release to beta testers
- Gather feedback
- Fix issues

### Stage 3: Production
- Full release
- Announce new features
- Provide migration support

## Troubleshooting

### Issue: Coordinates don't match after migration
**Solution**: Check mm_per_px calculation, verify calibration line

### Issue: Canvas lines not syncing
**Solution**: Check signal blocking, verify coordinate conversion

### Issue: Old components won't load
**Solution**: Check migration logic, add fallbacks

## Success Metrics

- [ ] All existing components load correctly
- [ ] No visual regressions
- [ ] Performance acceptable (<100ms for 50 interfaces)
- [ ] User feedback positive
- [ ] No critical bugs in first week

## Resources

- Strategy: `docs/COMPONENT_EDITOR_GENERALIZATION_STRATEGY.md`
- UI Mockups: `docs/COMPONENT_EDITOR_UI_MOCKUP.md`
- Current Implementation: `src/optiverse/ui/views/component_editor_dialog.py`
- Data Model: `src/optiverse/core/models.py`

