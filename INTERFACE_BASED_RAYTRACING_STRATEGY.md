# Interface-Based Raytracing Refactor Strategy

## Executive Summary

**Current Problem**: The raytracing algorithm does NOT properly interact with the optical interface architecture. While components can store multiple interfaces in the library (ComponentRecord with InterfaceDefinition), only RefractiveObjectItem exposes these interfaces to raytracing. Simple components (LensItem, MirrorItem, BeamsplitterItem, DichroicItem) only expose a single line segment, even if they have multiple interfaces stored in the library.

**Goal**: Refactor the system so that ALL components expose their optical interfaces, and the raytracing algorithm interacts exclusively with these interfaces.

---

## Current Architecture Analysis

### 1. Component Storage (✅ Already Interface-Based)

**Location**: `src/optiverse/core/interface_definition.py`, `src/optiverse/core/models.py`

- **ComponentRecord**: Components stored in library with multiple InterfaceDefinition objects
- **InterfaceDefinition**: Each interface has:
  - Geometry: `x1_mm, y1_mm, x2_mm, y2_mm`
  - Type: `element_type` (lens, mirror, beam_splitter, dichroic, refractive_interface)
  - Properties: Type-specific (efl_mm, reflectivity, split_T/R, n1/n2, etc.)
- **Status**: ✅ Well-designed, supports multiple interfaces per component

### 2. Component Loading (⚠️ Partially Interface-Based)

**Location**: `src/optiverse/ui/views/main_window.py::on_drop_component()`

**Current Behavior**:
- Multiple interfaces → Creates `RefractiveObjectItem` (preserves all interfaces)
- Single interface → Creates type-specific item (LensItem, MirrorItem, etc.)
  - ❌ **Problem**: Only extracts specific properties (efl_mm, split_T, etc.)
  - ❌ **Problem**: Loses interface structure

**Example**:
```python
# Component in library has 2 lens interfaces (Zemax doublet)
interfaces = [
    InterfaceDefinition(element_type="lens", efl_mm=100.0, ...),
    InterfaceDefinition(element_type="lens", efl_mm=-50.0, ...)
]

# But when dropped, becomes single LensItem with just efl_mm=100.0
# Second interface is LOST!
```

### 3. Scene Items (❌ NOT Interface-Based)

**Locations**: 
- `src/optiverse/objects/lenses/lens_item.py`
- `src/optiverse/objects/mirrors/mirror_item.py`
- `src/optiverse/objects/beamsplitters/beamsplitter_item.py`
- `src/optiverse/objects/dichroics/dichroic_item.py`

**Current Behavior**:
- Simple items (LensItem, MirrorItem, etc.):
  - ❌ Do NOT store interfaces
  - ❌ Only expose single line segment via `endpoints_scene()`
  - Store legacy params (LensParams with just efl_mm, BeamsplitterParams with split_T/R, etc.)

- RefractiveObjectItem:
  - ✅ Stores interfaces (RefractiveInterface list)
  - ✅ Exposes interfaces via `get_interfaces_scene()`

### 4. Raytracing (❌ NOT Interface-Based)

**Location**: 
- `src/optiverse/ui/views/main_window.py::retrace()`
- `src/optiverse/core/use_cases.py::trace_rays()`

**Current Behavior**:

```python
def retrace(self):
    # Collect by TYPE
    lenses: list[LensItem] = []
    mirrors: list[MirrorItem] = []
    # ... etc
    
    # Build elements - ONLY single line per simple component
    for L in lenses:
        p1, p2 = L.endpoints_scene()  # ❌ Single line only!
        elems.append(OpticalElement(kind="lens", p1=p1, p2=p2, efl_mm=L.params.efl_mm))
    
    # Only RefractiveObjectItem gets proper interface handling
    for R in refractive_objects:
        interfaces_scene = R.get_interfaces_scene()  # ✅ Multiple interfaces
        for p1, p2, iface in interfaces_scene:
            # ... proper interface handling
```

**Problems**:
1. ❌ Simple components limited to single line
2. ❌ Multi-interface components lost when using simple types
3. ❌ Raytracing separates by component KIND instead of iterating interfaces
4. ❌ No way for lens to have 2 curved surfaces, or mirror to have AR coating + reflective surface

---

## Refactor Strategy

### Phase 1: Add Interface Storage to All Component Types

**Goal**: Make LensItem, MirrorItem, BeamsplitterItem, DichroicItem, WaveplateItem store interfaces like RefractiveObjectItem does.

#### 1.1 Update Parameter Classes

**File**: `src/optiverse/core/models.py`

Add `interfaces` field to all params classes:

```python
@dataclass
class LensParams:
    # Existing fields
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 90.0
    efl_mm: float = 100.0  # Keep for backward compatibility
    object_height_mm: float = 60.0
    image_path: Optional[str] = None
    name: Optional[str] = None
    
    # NEW: Interface-based storage
    interfaces: Optional[List['InterfaceDefinition']] = None
    
    def __post_init__(self):
        """Ensure interfaces list exists."""
        if self.interfaces is None:
            self.interfaces = []

# Repeat for MirrorParams, BeamsplitterParams, DichroicParams, WaveplateParams
```

#### 1.2 Add Interface Getter Methods

**Files**: 
- `src/optiverse/objects/lenses/lens_item.py`
- `src/optiverse/objects/mirrors/mirror_item.py`
- `src/optiverse/objects/beamsplitters/beamsplitter_item.py`
- `src/optiverse/objects/dichroics/dichroic_item.py`
- `src/optiverse/objects/waveplates/waveplate_item.py`

Add `get_interfaces_scene()` method to ALL component types (same as RefractiveObjectItem):

```python
def get_interfaces_scene(self) -> List[Tuple[np.ndarray, np.ndarray, InterfaceDefinition]]:
    """Get all interfaces in scene coordinates.
    
    Returns:
        List of (p1, p2, interface) tuples where p1 and p2 are scene coordinates
    """
    if not self.params.interfaces or len(self.params.interfaces) == 0:
        # Backward compatibility: if no interfaces, create default from legacy params
        return self._create_default_interface()
    
    # Get picked line offset for coordinate transformation
    offset_x, offset_y = getattr(self, '_picked_line_offset_mm', (0.0, 0.0))
    
    result = []
    for iface in self.params.interfaces:
        # Transform from image-center coords to item local coords
        p1_local = QtCore.QPointF(iface.x1_mm - offset_x, iface.y1_mm - offset_y)
        p2_local = QtCore.QPointF(iface.x2_mm - offset_x, iface.y2_mm - offset_y)
        
        # Transform to scene coordinates
        p1_scene = self.mapToScene(p1_local)
        p2_scene = self.mapToScene(p2_local)
        
        p1 = np.array([p1_scene.x(), p1_scene.y()])
        p2 = np.array([p2_scene.x(), p2_scene.y()])
        result.append((p1, p2, iface))
    
    return result

def _create_default_interface(self):
    """Create default interface from legacy params for backward compatibility."""
    # Example for LensItem:
    from ...core.interface_definition import InterfaceDefinition
    
    # Use current endpoints as interface geometry
    p1_local = self._p1  # Local coordinates
    p2_local = self._p2
    
    # Transform to scene
    p1_scene = self.mapToScene(p1_local)
    p2_scene = self.mapToScene(p2_local)
    p1 = np.array([p1_scene.x(), p1_scene.y()])
    p2 = np.array([p2_scene.x(), p2_scene.y()])
    
    # Create interface from legacy params
    iface = InterfaceDefinition(
        x1_mm=p1_local.x(), y1_mm=p1_local.y(),
        x2_mm=p2_local.x(), y2_mm=p2_local.y(),
        element_type="lens",
        efl_mm=self.params.efl_mm
    )
    
    return [(p1, p2, iface)]
```

#### 1.3 Update Component Loading

**File**: `src/optiverse/ui/views/main_window.py::on_drop_component()`

Always preserve interfaces, regardless of count:

```python
def on_drop_component(self, rec: dict, scene_pos: QtCore.QPointF):
    # ... existing code ...
    
    # Extract interfaces
    interfaces_data = rec.get("interfaces", [])
    
    # Convert to InterfaceDefinition objects
    from ...core.interface_definition import InterfaceDefinition
    interfaces = [
        InterfaceDefinition.from_dict(iface_data) if isinstance(iface_data, dict) else iface_data
        for iface_data in interfaces_data
    ]
    
    # Get first interface type to determine component category
    if interfaces:
        first_interface = interfaces[0]
        element_type = first_interface.element_type
    else:
        # No interfaces - create default based on legacy "kind"
        element_type = rec.get("kind", "lens")
    
    # Create appropriate item type based on FIRST interface type
    # (This maintains UI/editing behavior while preserving all interfaces)
    
    if element_type == "lens":
        params = LensParams(
            x_mm=scene_pos.x(),
            y_mm=scene_pos.y(),
            angle_deg=angle_deg,
            efl_mm=first_interface.efl_mm if interfaces else 100.0,
            object_height_mm=object_height_mm,
            image_path=img,
            name=name,
            interfaces=interfaces,  # ✅ PRESERVE ALL INTERFACES
        )
        item = LensItem(params)
    
    elif element_type in ["beam_splitter", "beamsplitter"]:
        params = BeamsplitterParams(
            x_mm=scene_pos.x(),
            y_mm=scene_pos.y(),
            angle_deg=angle_deg,
            object_height_mm=object_height_mm,
            split_T=first_interface.split_T if interfaces else 50.0,
            split_R=first_interface.split_R if interfaces else 50.0,
            image_path=img,
            name=name,
            is_polarizing=first_interface.is_polarizing if interfaces else False,
            pbs_transmission_axis_deg=first_interface.pbs_transmission_axis_deg if interfaces else 0.0,
            interfaces=interfaces,  # ✅ PRESERVE ALL INTERFACES
        )
        item = BeamsplitterItem(params)
    
    # ... similar for mirror, dichroic, waveplate ...
```

### Phase 2: Refactor Raytracing to Use Interfaces

**Goal**: Make raytracing iterate through ALL interfaces from ALL components, not separate by component type.

#### 2.1 Update retrace() Method

**File**: `src/optiverse/ui/views/main_window.py::retrace()`

```python
def retrace(self):
    """Trace all rays from sources through optical elements."""
    self.clear_rays()
    
    # Collect sources
    sources: list[SourceItem] = []
    for it in self.scene.items():
        if isinstance(it, SourceItem):
            sources.append(it)
    
    if not sources:
        return
    
    # NEW APPROACH: Collect ALL interfaces from ALL components
    # This is the unified interface-based approach
    
    elems: list[OpticalElement] = []
    
    for item in self.scene.items():
        # Check if item has interfaces
        if hasattr(item, 'get_interfaces_scene') and callable(item.get_interfaces_scene):
            try:
                interfaces_scene = item.get_interfaces_scene()
                
                for p1, p2, iface in interfaces_scene:
                    # Create OpticalElement based on interface type
                    elem = self._create_element_from_interface(p1, p2, iface)
                    if elem:
                        elems.append(elem)
                        
            except Exception as e:
                print(f"Warning: Error getting interfaces from {type(item).__name__}: {e}")
                continue
    
    # Build source params
    srcs: list[SourceParams] = []
    for S in sources:
        srcs.append(S.params)
    
    # Trace
    paths = trace_rays(elems, srcs, max_events=80)
    
    # Display rays
    self._display_ray_paths(paths)

def _create_element_from_interface(self, p1: np.ndarray, p2: np.ndarray, 
                                   iface: InterfaceDefinition) -> Optional[OpticalElement]:
    """Create OpticalElement from InterfaceDefinition.
    
    This centralizes the conversion logic and handles all interface types.
    """
    element_type = iface.element_type
    
    if element_type == "lens":
        return OpticalElement(
            kind="lens",
            p1=p1,
            p2=p2,
            efl_mm=iface.efl_mm
        )
    
    elif element_type == "mirror":
        return OpticalElement(
            kind="mirror",
            p1=p1,
            p2=p2
        )
    
    elif element_type in ["beam_splitter", "beamsplitter"]:
        return OpticalElement(
            kind="bs",
            p1=p1,
            p2=p2,
            split_T=iface.split_T,
            split_R=iface.split_R,
            is_polarizing=iface.is_polarizing,
            pbs_transmission_axis_deg=iface.pbs_transmission_axis_deg
        )
    
    elif element_type == "dichroic":
        return OpticalElement(
            kind="dichroic",
            p1=p1,
            p2=p2,
            cutoff_wavelength_nm=iface.cutoff_wavelength_nm,
            transition_width_nm=iface.transition_width_nm,
            pass_type=iface.pass_type
        )
    
    elif element_type == "waveplate":
        return OpticalElement(
            kind="waveplate",
            p1=p1,
            p2=p2,
            phase_shift_deg=iface.phase_shift_deg,
            fast_axis_deg=iface.fast_axis_deg,
            angle_deg=0.0  # Interface already in scene coords
        )
    
    elif element_type == "refractive_interface":
        elem = OpticalElement(
            kind="refractive_interface",
            p1=p1,
            p2=p2
        )
        # Store refractive properties
        elem.n1 = iface.n1
        elem.n2 = iface.n2
        elem.is_beam_splitter = False
        return elem
    
    else:
        print(f"Warning: Unknown interface type: {element_type}")
        return None
```

#### 2.2 Simplify trace_rays (Optional)

**File**: `src/optiverse/core/use_cases.py`

The current `trace_rays` function already works with the unified approach since it just needs OpticalElements. However, we can add better comments:

```python
def trace_rays(
    elements: List[OpticalElement],
    sources: List[SourceParams],
    max_events: int = 80,
    parallel: bool = None,
    parallel_threshold: int = 20,
) -> List[RayPath]:
    """
    Trace rays from sources through optical elements.
    
    This function is interface-agnostic - it works with OpticalElement objects
    that are created from InterfaceDefinition objects by the caller.
    
    Each OpticalElement represents a single optical interface, not a physical component.
    Complex components (like doublets, beam splitter cubes, etc.) will have multiple
    elements in the list, one per interface.
    
    Args:
        elements: List of optical elements (one per interface)
        sources: List of light sources
        max_events: Maximum number of interactions per ray
        parallel: If True, use parallel processing
        parallel_threshold: Minimum rays to trigger parallelization
    
    Returns:
        List of RayPath objects representing traced rays
    """
    # ... existing implementation ...
```

### Phase 3: Backward Compatibility & Migration

#### 3.1 Handle Legacy Components

Components without interfaces should auto-generate them:

```python
def _ensure_interfaces(self):
    """Ensure component has at least one interface (for backward compatibility)."""
    if not self.params.interfaces or len(self.params.interfaces) == 0:
        # Create default interface from current geometry and params
        from ...core.interface_definition import InterfaceDefinition
        
        # For LensItem example:
        p1 = self._p1
        p2 = self._p2
        
        default_interface = InterfaceDefinition(
            x1_mm=p1.x(),
            y1_mm=p1.y(),
            x2_mm=p2.x(),
            y2_mm=p2.y(),
            element_type="lens",
            efl_mm=self.params.efl_mm
        )
        self.params.interfaces = [default_interface]
```

#### 3.2 Update Serialization

**File**: All `*_item.py` files

Update `to_dict()` and `from_dict()` to handle interfaces:

```python
def to_dict(self) -> Dict[str, Any]:
    """Serialize to dictionary."""
    d = {
        "x_mm": float(self.pos().x()),
        "y_mm": float(self.pos().y()),
        "angle_deg": float(self.rotation()),
        "efl_mm": self.params.efl_mm,  # Legacy field
        "object_height_mm": self.params.object_height_mm,
        "image_path": to_relative_path(self.params.image_path),
        "name": self.params.name,
        # NEW: Serialize interfaces
        "interfaces": [iface.to_dict() for iface in self.params.interfaces] if self.params.interfaces else []
    }
    return d

@classmethod
def from_dict(cls, d: Dict[str, Any]) -> 'LensItem':
    """Deserialize from dictionary."""
    from ...core.interface_definition import InterfaceDefinition
    
    # Load interfaces if available
    interfaces_data = d.get("interfaces", [])
    interfaces = [InterfaceDefinition.from_dict(iface) for iface in interfaces_data] if interfaces_data else None
    
    params = LensParams(
        x_mm=d.get("x_mm", 0.0),
        y_mm=d.get("y_mm", 0.0),
        angle_deg=d.get("angle_deg", 90.0),
        efl_mm=d.get("efl_mm", 100.0),
        object_height_mm=d.get("object_height_mm", 60.0),
        image_path=to_absolute_path(d.get("image_path", "")),
        name=d.get("name", ""),
        interfaces=interfaces
    )
    
    return cls(params, d.get("item_uuid"))
```

---

## Implementation Checklist

### Phase 1: Interface Storage
- [ ] 1.1: Add `interfaces` field to all Params classes (LensParams, MirrorParams, BeamsplitterParams, DichroicParams, WaveplateParams)
- [ ] 1.2: Add `get_interfaces_scene()` method to LensItem
- [ ] 1.3: Add `get_interfaces_scene()` method to MirrorItem
- [ ] 1.4: Add `get_interfaces_scene()` method to BeamsplitterItem
- [ ] 1.5: Add `get_interfaces_scene()` method to DichroicItem
- [ ] 1.6: Add `get_interfaces_scene()` method to WaveplateItem
- [ ] 1.7: Update `on_drop_component()` to preserve all interfaces
- [ ] 1.8: Add `_ensure_interfaces()` for backward compatibility
- [ ] 1.9: Update all `to_dict()` methods to serialize interfaces
- [ ] 1.10: Update all `from_dict()` methods to deserialize interfaces

### Phase 2: Raytracing Refactor
- [ ] 2.1: Add `_create_element_from_interface()` helper to MainWindow
- [ ] 2.2: Refactor `retrace()` to use unified interface iteration
- [ ] 2.3: Test raytracing with simple components (single interface)
- [ ] 2.4: Test raytracing with complex components (multiple interfaces)
- [ ] 2.5: Update `trace_rays()` documentation

### Phase 3: Testing & Validation
- [ ] 3.1: Test loading legacy save files (backward compatibility)
- [ ] 3.2: Test Zemax import with multiple interfaces
- [ ] 3.3: Test component editor with multiple interfaces
- [ ] 3.4: Verify performance (should be similar or better)
- [ ] 3.5: Test save/load with interface-based components
- [ ] 3.6: Verify all component types work with raytracing

---

## Benefits of This Refactor

1. **Unified Architecture**: All components work the same way (interface-based)
2. **Zemax Support**: Properly handles doublets, triplets, compound lenses
3. **Physical Accuracy**: Can model AR coatings, multi-layer dichroics, etc.
4. **Extensibility**: Easy to add new interface types
5. **Backward Compatible**: Legacy components auto-generate interfaces
6. **Cleaner Code**: Single path through raytracing instead of type-specific branches

---

## Example Use Cases Enabled

### 1. Achromatic Doublet from Zemax
```python
# Component stored with 4 interfaces:
# 1. First lens front surface (convex)
# 2. First lens back surface / second lens front (flat, n1=1.517, n2=1.620)
# 3. Second lens back surface (concave)
# Total: Proper modeling of glass path and multiple refractions
```

### 2. AR-Coated Mirror
```python
# Component with 2 interfaces:
# 1. AR coating (refractive, n1=1.0, n2=1.38, reduces Fresnel reflection)
# 2. Reflective coating (mirror, reflectivity=99.9%)
```

### 3. Dichroic Filter Stack
```python
# Component with 3 interfaces:
# 1. Entrance surface (refractive, n1=1.0, n2=1.5)
# 2. Dichroic coating (dichroic, cutoff=550nm)
# 3. Exit surface (refractive, n1=1.5, n2=1.0)
```

---

## Migration Notes

- **No breaking changes** for users (backward compatible)
- **No changes** to file format (interfaces already in ComponentRecord)
- **Raytracing API unchanged** (still uses OpticalElement)
- **Component editor already supports** multiple interfaces

The refactor is mostly internal plumbing to properly connect existing pieces!

