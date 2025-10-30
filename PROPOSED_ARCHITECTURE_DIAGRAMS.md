# Proposed Architecture - Visual Diagrams

## Current vs Proposed: High-Level Comparison

### Current Architecture (Problematic)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                             │
│  MainWindow, ComponentEditor, GraphicsView                               │
│                                                                           │
│  ❌ Contains: Raytracing coordination, Component creation logic,         │
│              Serialization logic, Coordinate transformations             │
│                                                                           │
│  Problems:                                                               │
│  • 2000+ line files with multiple responsibilities                       │
│  • Can't test raytracing without PyQt                                    │
│  • Tight coupling to everything                                          │
└─────────────────────────────────────────────────────────────────────────┘
                              │        ▲
                              ▼        │
┌─────────────────────────────────────────────────────────────────────────┐
│                        COMPONENT LAYER (UI + Data)                       │
│  LensItem, MirrorItem, BeamsplitterItem, etc.                            │
│                                                                           │
│  ❌ Mixed responsibilities:                                              │
│     • Qt graphics (boundingRect, paint, mousePressEvent)                 │
│     • Data storage (params, interfaces)                                  │
│     • Coordinate transformations                                         │
│     • Serialization (to_dict/from_dict)                                  │
│                                                                           │
│  Problems:                                                               │
│  • Can't reuse logic without importing PyQt                              │
│  • Each component duplicates similar code                                │
│  • Tight coupling between rendering and data                             │
└─────────────────────────────────────────────────────────────────────────┘
                              │        ▲
                              ▼        │
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA MODELS LAYER                               │
│  ComponentRecord, *Params classes, InterfaceDefinition, RefractiveInterface
│                                                                           │
│  ❌ Problems:                                                            │
│     • Two interface models (InterfaceDefinition vs RefractiveInterface)  │
│     • Params classes inconsistent (some have interfaces, some don't)    │
│     • Properties duplicated (LensParams.efl AND interface.efl)           │
│     • No clear hierarchy or abstraction                                  │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    RAYTRACING LAYER (use_cases.py)                       │
│                                                                           │
│  OpticalElement (God Object) ──→ trace_rays() ──→ _trace_single_ray_worker()
│                                                         (358 lines!)      │
│                                                                           │
│  ❌ Problems:                                                            │
│     • String-based type dispatch (if kind == "mirror"...)                │
│     • O(6n) element filtering before tracing                             │
│     • Giant monolithic worker function                                   │
│     • OpticalElement has fields for ALL element types                    │
│     • Hard to extend, test, or optimize                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Proposed Architecture (Clean)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                             │
│  MainWindow, ComponentEditor, GraphicsView                               │
│                                                                           │
│  ✅ Responsibilities:                                                    │
│     • User interaction                                                   │
│     • Visualization only                                                 │
│     • Delegates to lower layers                                          │
│                                                                           │
│  Benefits:                                                               │
│  • Thin layer, easy to understand                                        │
│  • Can swap UI framework (PyQt → PySide → Web)                           │
│  • Testable via mocks                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GRAPHICS COMPONENTS LAYER                             │
│  ComponentItem(BaseObj)                                                  │
│                                                                           │
│  ✅ Responsibilities:                                                    │
│     • Qt graphics rendering ONLY                                         │
│     • Delegates data to ComponentRecord                                  │
│     • Converts ComponentRecord → IOpticalElement for raytracing          │
│                                                                           │
│  Benefits:                                                               │
│  • Single responsibility                                                 │
│  • Data model is separate and reusable                                   │
│  • Clean separation of concerns                                          │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     OPTICAL DATA LAYER (Pure Python)                     │
│  ComponentRecord                                                         │
│      └─ List[OpticalInterface]                                           │
│            └─ OpticalProperties (Union type)                             │
│                                                                           │
│  ✅ Responsibilities:                                                    │
│     • Data storage only                                                  │
│     • Serialization/deserialization                                      │
│     • Immutable data structures                                          │
│                                                                           │
│  Benefits:                                                               │
│  • No PyQt dependency                                                    │
│  • Testable in pure Python                                               │
│  • Serialization in ONE place                                            │
│  • Can use in CLI tools, web backends, etc.                              │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  RAYTRACING LAYER (Pure Python + NumPy)                  │
│                                                                           │
│  IOpticalElement (Interface)                                             │
│      ├─ MirrorElement                                                    │
│      ├─ LensElement                                                      │
│      ├─ RefractiveElement                                                │
│      ├─ BeamsplitterElement                                              │
│      ├─ DichroicElement                                                  │
│      └─ WaveplateElement                                                 │
│                                                                           │
│  RaytracingEngine:                                                       │
│      • trace_rays(elements: List[IOpticalElement]) → List[RayPath]      │
│      • Uses BVH spatial index for O(log n) queries                       │
│                                                                           │
│  ✅ Benefits:                                                            │
│     • Polymorphic dispatch (no type checking!)                           │
│     • Each element independently testable                                │
│     • Easy to extend (add new IOpticalElement)                           │
│     • Can run in separate process/thread                                 │
│     • Industry-standard architecture                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Current vs Proposed

### Current: Too Many Transformations

```
ComponentRecord (Library)
    ↓ [Transform 1: Extract data]
LensParams
    ↓ [Transform 2: Create UI item]
LensItem
    ↓ [Transform 3: endpoints_scene() or get_interfaces_scene()]
(p1, p2, interface)
    ↓ [Transform 4: _create_element_from_interface()]
OpticalElement(kind="lens", efl_mm=..., split_T=0, split_R=0, ...)
    ↓ [Transform 5: Partition by type]
6× Separate lists (mirrors, lenses, bss, waveplates, dichroics, refractive)
    ↓ [Transform 6: Check each list]
if kind == "lens": apply_lens_physics()
```

**Problems**:
- 6 transformations before raytracing even starts!
- Information loss at each step
- Hard to debug (which transformation failed?)

### Proposed: Minimal Transformations

```
ComponentRecord (Library)
    ↓ [ONE transformation: to_optical_elements()]
List[IOpticalElement]
    ↓ [Spatial indexing for optimization]
BVHTree(elements)
    ↓ [Polymorphic dispatch]
element.interact(ray) → List[Ray]
```

**Benefits**:
- 1 transformation instead of 6
- No information loss
- Easy to debug
- Fast and efficient

---

## Component Structure: Current vs Proposed

### Current Component (LensItem)

```python
class LensItem(BaseObj):
    """
    Lines of code: 300+
    Responsibilities: 5+
    Dependencies: PyQt, numpy, models, services
    """
    
    def __init__(self, params: LensParams):
        # Responsibility 1: Qt graphics setup
        super().__init__()
        self.setFlags(...)
        
        # Responsibility 2: Data storage
        self.params = params
        self._sprite = None
        
        # Responsibility 3: Geometry calculations
        self._update_geom()
        
        # Responsibility 4: Coordinate transformations
        self._picked_line_offset_mm = (0, 0)
    
    # Responsibility 5: Qt event handling
    def mousePressEvent(self, event): ...
    def paint(self, painter, option, widget): ...
    
    # Responsibility 6: Coordinate transformations
    def endpoints_scene(self): ...
    def get_interfaces_scene(self): ...
    
    # Responsibility 7: Serialization
    def to_dict(self): ...
    def from_dict(self, d): ...
    
    # Responsibility 8: UI interaction
    def open_editor(self): ...
```

**Violations**:
- ❌ Single Responsibility Principle (8 responsibilities!)
- ❌ Separation of Concerns
- ❌ Dependency Inversion Principle (depends on concrete types)

### Proposed Component (Separated)

```python
# 1. Pure data (no dependencies)
@dataclass
class ComponentRecord:
    """
    Lines: 20
    Responsibilities: 1 (data storage)
    Dependencies: None (pure Python)
    """
    name: str
    interfaces: List[OpticalInterface]
    visualization: VisualizationData
    metadata: Dict[str, Any]
    
    def to_optical_elements(self) -> List[IOpticalElement]:
        """Convert to raytracing elements"""
        return [create_element(iface) for iface in self.interfaces]

# 2. Qt graphics (depends on ComponentRecord)
class ComponentItem(QGraphicsObject):
    """
    Lines: 100
    Responsibilities: 1 (Qt rendering)
    Dependencies: PyQt, ComponentRecord
    """
    def __init__(self, record: ComponentRecord):
        super().__init__()
        self.record = record  # Single source of truth
    
    def paint(self, painter, option, widget):
        """Render from self.record data"""
        pass
    
    def boundingRect(self):
        """Compute from self.record.interfaces"""
        pass

# 3. Raytracing element (no dependencies)
class LensElement(IOpticalElement):
    """
    Lines: 50
    Responsibilities: 1 (ray-lens interaction)
    Dependencies: numpy only
    """
    def __init__(self, p1, p2, efl_mm):
        self.p1 = p1
        self.p2 = p2
        self.efl_mm = efl_mm
    
    def interact(self, ray: RayState) -> List[RayState]:
        """Thin lens equation"""
        pass
```

**Benefits**:
- ✅ Each class has ONE responsibility
- ✅ Can test each independently
- ✅ Can reuse in different contexts
- ✅ Clear dependencies (data → UI → raytracing)

---

## Raytracing: Current vs Proposed

### Current Raytracing Flow

```
trace_rays(elements, sources)
    │
    ├─ Partition elements by type (O(6n))
    │   └─ if e.kind == "mirror": mirrors.append(...)
    │
    ├─ Build ray jobs (O(n_sources × n_rays))
    │
    └─ For each ray:
         │
         ├─ Intersection testing (O(6n) per ray)
         │   ├─ for obj, A, B in mirrors:
         │   │     ray_hit_element(...)  # O(n)
         │   ├─ for obj, A, B in lenses:
         │   │     ray_hit_element(...)  # O(n)
         │   ├─ for obj, A, B in bss: ...
         │   ├─ for obj, A, B in waveplates: ...
         │   ├─ for obj, A, B in dichroics: ...
         │   └─ for p1, p2, iface in refractive: ...
         │
         └─ Type-based physics (if-elif chain)
             ├─ if kind == "mirror": reflect(...)
             ├─ elif kind == "lens": refract_lens(...)
             ├─ elif kind == "bs": split(...)
             ├─ elif kind == "waveplate": transform_pol(...)
             ├─ elif kind == "dichroic": wavelength_split(...)
             └─ elif kind == "refractive": snell_fresnel(...)
```

**Complexity**: O(n_rays × n_elements × 6)

### Proposed Raytracing Flow

```
trace_rays(elements: List[IOpticalElement], sources)
    │
    ├─ Build spatial index (O(n log n), done once)
    │   └─ bvh_tree = BVHTree(elements)
    │
    └─ For each ray:
         │
         ├─ Find nearest intersection (O(log n))
         │   └─ element, point = bvh_tree.query(ray)
         │
         └─ Polymorphic physics (no type checking!)
             └─ new_rays = element.interact(ray)
```

**Complexity**: O(n_rays × log n_elements)

**Speedup**: 
- 100 elements: 6×100 = 600 checks → log(100) ≈ 7 checks = **85× faster**
- 1000 elements: 6×1000 = 6000 checks → log(1000) ≈ 10 checks = **600× faster**

---

## Interface Model: Current vs Proposed

### Current: Two Models + Translation

```
InterfaceDefinition              RefractiveInterface
    ├─ element_type: str             ├─ n1: float
    ├─ x1_mm, y1_mm, x2_mm, y2_mm    ├─ n2: float
    ├─ efl_mm                        ├─ is_beam_splitter
    ├─ reflectivity                  ├─ split_T
    ├─ split_T, split_R              ├─ split_R
    ├─ is_polarizing                 ├─ is_polarizing
    ├─ pbs_transmission_axis_deg     └─ pbs_transmission_axis_deg
    ├─ cutoff_wavelength_nm
    ├─ transition_width_nm
    ├─ pass_type
    ├─ n1, n2
    ├─ is_curved
    └─ radius_of_curvature_mm

         ↓ Translation layer (error-prone!)

OpticalElement (God Object)
    ├─ kind: str  # ← String typing!
    ├─ p1, p2
    ├─ ALL properties from both models above
    └─ 15+ optional fields (most unused)
```

### Proposed: Single Unified Model

```python
@dataclass
class OpticalInterface:
    """Single unified interface model"""
    # Geometry (always needed)
    geometry: LineSegment
    
    # Type-safe properties (Union type)
    properties: OpticalProperties
    
    # Coordinate metadata
    frame: CoordinateFrame

# Type-safe property unions
OpticalProperties = Union[
    RefractiveProperties,
    LensProperties,
    MirrorProperties,
    BeamsplitterProperties,
    WaveplateProperties,
    DichroicProperties,
]

@dataclass
class RefractiveProperties:
    n1: float
    n2: float
    curvature_radius_mm: Optional[float] = None

@dataclass
class LensProperties:
    efl_mm: float

# etc...
```

**Benefits**:
- ✅ One model (not two or three)
- ✅ Type safety (Union types catch errors)
- ✅ No translation layers
- ✅ Clear which properties apply to which elements
- ✅ Can't accidentally use wrong properties

---

## Dependency Graph: Current vs Proposed

### Current (Circular Dependencies)

```
     ┌─────────────┐
     │ MainWindow  │◄─────────────┐
     └──────┬──────┘              │
            │                     │
            ▼                     │
     ┌─────────────┐              │
     │  LensItem   │              │
     └──────┬──────┘              │
            │                     │
            ▼                     │
     ┌─────────────┐              │
     │ LensParams  │              │
     └──────┬──────┘              │
            │                     │
            ▼                     │
     ┌─────────────┐              │
     │   models    │              │
     └──────┬──────┘              │
            │                     │
            ▼                     │
     ┌─────────────┐              │
     │ use_cases   │──────────────┘
     │ (raytracing)│
     └─────────────┘
```
**Problem**: Circular dependencies make testing impossible

### Proposed (Clean Layered Architecture)

```
     ┌─────────────┐
     │ MainWindow  │  (UI Layer)
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │ComponentItem│  (Graphics Layer)
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │ComponentRec │  (Data Layer)
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │Raytracing   │  (Engine Layer)
     │  Engine     │
     └─────────────┘
```

**Benefits**:
- ✅ No circular dependencies
- ✅ Each layer testable independently
- ✅ Can swap implementations
- ✅ Clear architectural boundaries

---

## File Organization: Proposed

```
optiverse/
├── data/                        # Pure data models (no dependencies)
│   ├── __init__.py
│   ├── optical_interface.py     # OpticalInterface, OpticalProperties
│   ├── component_record.py      # ComponentRecord
│   ├── ray.py                   # Ray, RayPath, Polarization
│   └── geometry.py              # LineSegment, BoundingBox
│
├── raytracing/                  # Pure raytracing engine (numpy only)
│   ├── __init__.py
│   ├── engine.py                # trace_rays() - main entry point
│   ├── elements/                # Optical element implementations
│   │   ├── __init__.py
│   │   ├── base.py              # IOpticalElement interface
│   │   ├── mirror.py            # MirrorElement
│   │   ├── lens.py              # LensElement
│   │   ├── refractive.py        # RefractiveElement
│   │   ├── beamsplitter.py      # BeamsplitterElement
│   │   ├── waveplate.py         # WaveplateElement
│   │   └── dichroic.py          # DichroicElement
│   ├── spatial/                 # Spatial indexing
│   │   ├── __init__.py
│   │   ├── bvh.py               # Bounding Volume Hierarchy
│   │   └── intersection.py      # Ray-line intersection
│   └── optics/                  # Optical physics
│       ├── __init__.py
│       ├── snell.py             # Snell's law, refraction
│       ├── fresnel.py           # Fresnel equations
│       └── jones.py             # Jones calculus for polarization
│
├── ui/                          # PyQt UI layer
│   ├── components/              # Graphics items
│   │   ├── __init__.py
│   │   ├── base_item.py         # BaseObj
│   │   └── component_item.py    # ComponentItem (generic)
│   ├── views/
│   │   ├── __init__.py
│   │   ├── main_window.py       # Main application window
│   │   └── component_editor.py  # Component editor dialog
│   └── widgets/
│       └── ...
│
├── services/                    # Application services
│   ├── __init__.py
│   ├── storage_service.py       # Load/save components and scenes
│   ├── zemax_importer.py        # Import from Zemax
│   └── glass_catalog.py         # Material database
│
└── platform/                    # Platform-specific code
    ├── __init__.py
    └── paths.py                 # Path utilities
```

**Key Principles**:
1. **Dependencies flow down only** (ui → data → raytracing)
2. **Pure Python in data/ and raytracing/** (no PyQt)
3. **One file per class** (easier to find and test)
4. **Clear separation of concerns**

---

Would you like me to provide implementation examples for any of these diagrams?

