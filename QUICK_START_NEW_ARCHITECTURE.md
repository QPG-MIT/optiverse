# Quick Start: Using the New Architecture

**Last Updated**: October 30, 2025  
**For**: Developers integrating the new raytracing system

---

## 🚀 30-Second Overview

The new architecture has **3 layers**:

1. **Data Layer** (`optiverse.data`) - Type-safe optical interfaces
2. **Behavior Layer** (`optiverse.raytracing`) - Polymorphic elements
3. **Integration Layer** (`optiverse.integration`) - Adapters

---

## 📦 Import Guide

```python
# Layer 1: Data (Phase 1)
from optiverse.data import (
    OpticalInterface, LineSegment,
    LensProperties, MirrorProperties, RefractiveProperties,
    BeamsplitterProperties, WaveplateProperties, DichroicProperties
)

# Layer 2: Raytracing (Phase 2)
from optiverse.raytracing import (
    Ray, RayPath, Polarization,
    IOpticalElement,  # Abstract base class
    Mirror, Lens, RefractiveInterfaceElement,
    Beamsplitter, Waveplate, Dichroic,
    trace_rays  # New engine (when implemented)
)

# Layer 3: Integration (Adapter)
from optiverse.integration import (
    create_polymorphic_element,       # OpticalInterface → IOpticalElement
    convert_legacy_interfaces,        # List conversion
    convert_scene_to_polymorphic     # Scene conversion
)
```

---

## 🎯 Common Use Cases

### Use Case 1: Create a Lens from Scratch

```python
import numpy as np
from optiverse.data import OpticalInterface, LineSegment, LensProperties

# Step 1: Define geometry
geometry = LineSegment(
    p1=np.array([10.0, -15.0]),  # Start point in mm
    p2=np.array([10.0, 15.0])    # End point in mm
)

# Step 2: Define optical properties
properties = LensProperties(
    efl_mm=100.0,  # Effective focal length
    name="My Lens"
)

# Step 3: Create optical interface
lens_interface = OpticalInterface(
    geometry=geometry,
    properties=properties,
    name="My Custom Lens"
)

# Step 4: Convert to polymorphic element
from optiverse.integration import create_polymorphic_element
lens_element = create_polymorphic_element(lens_interface)

# Step 5: Use in raytracing!
# lens_element.interact_with_ray(ray, intersection, epsilon, threshold)
```

---

### Use Case 2: Convert Legacy Interface

```python
from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.data import OpticalInterface
from optiverse.integration import create_polymorphic_element

# You have a legacy interface
legacy_lens = InterfaceDefinition(
    x1_mm=10.0, y1_mm=-15.0,
    x2_mm=10.0, y2_mm=15.0,
    element_type="lens",
    efl_mm=100.0
)

# Convert: Legacy → New Data Model
optical_iface = OpticalInterface.from_legacy_interface_definition(legacy_lens)

# Convert: Data → Behavior
lens_element = create_polymorphic_element(optical_iface)

# Ready to use!
```

---

### Use Case 3: Convert Entire Scene

```python
from optiverse.integration import convert_scene_to_polymorphic

# In MainWindow.retrace() or similar
def retrace_v2(self):
    """New raytracing using polymorphic elements."""
    
    # Step 1: Convert all items in scene to polymorphic elements
    elements = convert_scene_to_polymorphic(self.scene.items())
    
    # Step 2: Collect sources
    sources = [item.params for item in self.scene.items() 
               if isinstance(item, SourceItem)]
    
    # Step 3: Trace rays (when engine is implemented)
    from optiverse.raytracing import trace_rays
    paths = trace_rays(elements, sources, max_events=80)
    
    # Step 4: Render (same as before)
    self._render_ray_paths(paths)
```

---

### Use Case 4: Create All Element Types

```python
import numpy as np
from optiverse.data import OpticalInterface, LineSegment
from optiverse.data import (
    LensProperties, MirrorProperties, RefractiveProperties,
    BeamsplitterProperties, WaveplateProperties, DichroicProperties, PassType
)
from optiverse.integration import create_polymorphic_element

# Helper function
def create_element(x_mm, props, name=""):
    geom = LineSegment(np.array([x_mm, -10]), np.array([x_mm, 10]))
    iface = OpticalInterface(geometry=geom, properties=props, name=name)
    return create_polymorphic_element(iface)

# 1. Lens
lens = create_element(10, LensProperties(efl_mm=100.0), "Lens")

# 2. Mirror
mirror = create_element(20, MirrorProperties(reflectivity=99.0), "Mirror")

# 3. Refractive Interface
refractive = create_element(30, RefractiveProperties(n1=1.0, n2=1.5), "Glass")

# 4. Beamsplitter
beamsplitter = create_element(40, BeamsplitterProperties(
    split_T=70.0, split_R=30.0,
    is_polarizing=False
), "BS")

# 5. Polarizing Beamsplitter (PBS)
pbs = create_element(50, BeamsplitterProperties(
    split_T=95.0, split_R=5.0,
    is_polarizing=True,
    pbs_transmission_axis_deg=0.0
), "PBS")

# 6. Quarter-Wave Plate
qwp = create_element(60, WaveplateProperties(
    phase_shift_deg=90.0,
    fast_axis_deg=45.0
), "QWP")

# 7. Half-Wave Plate
hwp = create_element(70, WaveplateProperties(
    phase_shift_deg=180.0,
    fast_axis_deg=22.5
), "HWP")

# 8. Dichroic (Longpass)
dichroic = create_element(80, DichroicProperties(
    cutoff_wavelength_nm=550.0,
    transition_width_nm=20.0,
    pass_type=PassType.LONGPASS
), "Dichroic")

# All elements implement IOpticalElement!
elements = [lens, mirror, refractive, beamsplitter, pbs, qwp, hwp, dichroic]
```

---

### Use Case 5: Create and Use Rays

```python
import numpy as np
from optiverse.raytracing import Ray, Polarization

# Create a ray
ray = Ray(
    position=np.array([0.0, 5.0]),      # Starting position in mm
    direction=np.array([1.0, 0.0]),     # Normalized direction
    remaining_length=100.0,              # Max propagation distance
    polarization=Polarization.horizontal(),  # Horizontal polarization
    wavelength_nm=633.0,                 # HeNe laser wavelength
    base_rgb=(255, 0, 0)                 # Red color
)

# Create other polarization states
h_pol = Polarization.horizontal()         # [1, 0]
v_pol = Polarization.vertical()           # [0, 1]
d_pol = Polarization.diagonal_plus_45()   # [1/√2, 1/√2]
r_pol = Polarization.circular_right()     # [1/√2, i/√2]
l_pol = Polarization.circular_left()      # [1/√2, -i/√2]
custom_pol = Polarization.linear(30.0)    # 30° from horizontal

# Advanced ray with circular polarization
circular_ray = Ray(
    position=np.array([0.0, 0.0]),
    direction=np.array([1.0, 0.0]),
    remaining_length=100.0,
    polarization=Polarization.circular_right(),
    wavelength_nm=532.0,  # Green laser
    base_rgb=(0, 255, 0)
)
```

---

### Use Case 6: Manual Ray-Element Interaction

```python
import numpy as np
from optiverse.raytracing import Ray, Polarization
from optiverse.data import OpticalInterface, LineSegment, MirrorProperties
from optiverse.integration import create_polymorphic_element
from optiverse.raytracing.elements import RayIntersection

# Create a mirror
geom = LineSegment(np.array([10, -10]), np.array([10, 10]))
props = MirrorProperties(reflectivity=99.0)
iface = OpticalInterface(geometry=geom, properties=props)
mirror = create_polymorphic_element(iface)

# Create a ray heading towards the mirror
ray = Ray(
    position=np.array([0.0, 0.0]),
    direction=np.array([1.0, 0.0]),
    remaining_length=100.0,
    polarization=Polarization.horizontal(),
    wavelength_nm=633.0,
    base_rgb=(255, 0, 0)
)

# Calculate intersection (you'd normally use the engine for this)
# For this example, we'll create a mock intersection
from optiverse.core.geometry import ray_hit_element
hit_result = ray_hit_element(
    ray.position, ray.direction,
    geom.p1, geom.p2
)

if hit_result:
    t, X, t_hat, n_hat, C, L = hit_result
    intersection = RayIntersection(
        distance=t,
        point=X,
        tangent=t_hat,
        normal=n_hat,
        center=C,
        length=L,
        interface=iface
    )
    
    # Interact!
    output_rays = mirror.interact_with_ray(ray, intersection, epsilon=1e-3, intensity_threshold=0.02)
    
    print(f"Mirror produced {len(output_rays)} output rays")
    for i, r in enumerate(output_rays):
        print(f"  Ray {i}: direction={r.direction}, intensity={r.intensity}")
```

---

## 🛠️ Integration with Existing Code

### Modify MainWindow to Use New System

```python
# In src/optiverse/ui/views/main_window.py

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing init code ...
        
        # ADD: Feature flag for new raytracing
        self.use_new_raytracing = False  # Set to True to use new system
    
    def retrace(self):
        """Trace all rays (dispatches to old or new system)."""
        if self.use_new_raytracing:
            self._retrace_new()
        else:
            self._retrace_legacy()
    
    def _retrace_legacy(self):
        """Original raytracing system (current implementation)."""
        # ... existing code (unchanged) ...
        from ...core.use_cases import trace_rays
        paths = trace_rays(elems, srcs, max_events=80)
        # ... render ...
    
    def _retrace_new(self):
        """New polymorphic raytracing system."""
        self.clear_rays()
        
        # Convert scene to polymorphic elements
        from ...integration import convert_scene_to_polymorphic
        elements = convert_scene_to_polymorphic(self.scene.items())
        
        # Collect sources (same as before)
        sources = [item.params for item in self.scene.items() 
                   if isinstance(item, SourceItem)]
        
        if not sources:
            return
        
        # Use new raytracing engine
        from ...raytracing import trace_rays  # When implemented
        paths = trace_rays(elements, sources, max_events=80)
        
        # Render paths (same as before)
        for p in paths:
            if len(p.points) < 2:
                continue
            path = QtGui.QPainterPath(QtCore.QPointF(p.points[0][0], p.points[0][1]))
            for q in p.points[1:]:
                path.lineTo(q[0], q[1])
            item = QtWidgets.QGraphicsPathItem(path)
            r, g, b, a = p.rgba
            pen = QtGui.QPen(QtGui.QColor(r, g, b, a))
            pen.setWidthF(self._ray_width_px)
            pen.setCosmetic(True)
            item.setPen(pen)
            item.setZValue(10)
            self.scene.addItem(item)
            self.ray_items.append(item)
            self.ray_data.append(p)
```

---

## 🧪 Testing Your Code

### Test a Custom Element

```python
import pytest
import numpy as np
from optiverse.raytracing import Ray, Polarization
from optiverse.data import OpticalInterface, LineSegment, LensProperties
from optiverse.integration import create_polymorphic_element
from optiverse.raytracing.elements import RayIntersection

def test_custom_lens():
    """Test that a lens refracts rays correctly."""
    # Create lens
    geom = LineSegment(np.array([10, -10]), np.array([10, 10]))
    props = LensProperties(efl_mm=50.0)
    iface = OpticalInterface(geometry=geom, properties=props)
    lens = create_polymorphic_element(iface)
    
    # Create ray hitting lens at y=5
    ray = Ray(
        position=np.array([0.0, 5.0]),
        direction=np.array([1.0, 0.0]),
        remaining_length=100.0,
        polarization=Polarization.horizontal(),
        wavelength_nm=633.0,
        base_rgb=(255, 0, 0)
    )
    
    # Create intersection (simplified)
    intersection = RayIntersection(
        distance=10.0,
        point=np.array([10.0, 5.0]),
        tangent=np.array([0.0, 1.0]),
        normal=np.array([1.0, 0.0]),
        center=np.array([10.0, 0.0]),
        length=20.0,
        interface=iface
    )
    
    # Test interaction
    output_rays = lens.interact_with_ray(ray, intersection, epsilon=1e-3, intensity_threshold=0.02)
    
    assert len(output_rays) == 1
    refracted_ray = output_rays[0]
    
    # Ray should bend towards focal point at (60, 0)
    # Expected direction: from (10, 5) to (60, 0) → (50, -5) → normalized
    expected_direction = np.array([50.0, -5.0])
    expected_direction = expected_direction / np.linalg.norm(expected_direction)
    
    assert np.allclose(refracted_ray.direction, expected_direction, atol=1e-6)
```

---

## 📚 API Reference

### Key Classes

#### `OpticalInterface` (Phase 1)
```python
class OpticalInterface:
    geometry: LineSegment          # Geometric representation
    properties: OpticalPropertyType # Optical properties (Lens, Mirror, etc.)
    name: str                      # Optional name
    
    def get_element_type() -> str
    def to_dict() -> dict
    @classmethod from_dict(data: dict)
    @classmethod from_legacy_interface_definition(legacy)
    @classmethod from_legacy_refractive_interface(legacy)
```

#### `IOpticalElement` (Phase 2)
```python
class IOpticalElement(ABC):
    @abstractmethod
    def interact_with_ray(
        self, ray: Ray,
        intersection: RayIntersection,
        epsilon: float,
        intensity_threshold: float
    ) -> List[Ray]:
        """Return list of output rays (can be 0, 1, or 2+)"""
        pass
    
    @abstractmethod
    def get_geometry() -> Tuple[np.ndarray, np.ndarray]:
        """Return (p1, p2) endpoints"""
        pass
    
    @abstractmethod
    def get_bounding_box() -> Tuple[np.ndarray, np.ndarray]:
        """Return (min_point, max_point) for BVH"""
        pass
```

#### `Ray` (Phase 2)
```python
@dataclass
class Ray:
    position: np.ndarray
    direction: np.ndarray
    remaining_length: float
    polarization: Polarization
    wavelength_nm: float
    base_rgb: Tuple[int, int, int]
    intensity: float = 1.0
    events: int = 0
    path_points: List[np.ndarray] = field(default_factory=list)
    
    def advance(new_position, distance)
    def split(new_direction, new_polarization, intensity_factor) -> Ray
```

---

## 🎯 Best Practices

### DO ✅

1. **Use type hints** - The whole system is type-safe
2. **Test your elements** - Each element is independently testable
3. **Use feature flags** - Gradual migration is safer
4. **Follow SOLID** - Keep elements focused and simple
5. **Document physics** - Explain optical equations in comments

### DON'T ❌

1. **Don't modify IOpticalElement** - Extend, don't modify
2. **Don't bypass adapters** - Use the integration layer
3. **Don't mix old/new** - Choose one system per raytrace
4. **Don't skip tests** - High coverage = high confidence
5. **Don't hardcode** - Use configuration/parameters

---

## 🐛 Troubleshooting

### "No module named 'optiverse.data'"

**Solution**: Install package in development mode
```bash
cd /path/to/optiverse
pip install -e .
```

### "numpy segfault on import"

**Solution**: macOS/conda issue. Try:
```bash
conda install numpy -c conda-forge --force-reinstall
```

### "Element not producing expected output"

**Solution**: Check your intersection calculation
```python
# Make sure you're computing intersection correctly
from optiverse.core.geometry import ray_hit_element
hit = ray_hit_element(ray.position, ray.direction, elem.p1, elem.p2)
if hit is None:
    print("Ray doesn't hit element!")
```

### "Rays disappearing"

**Solution**: Check intensity threshold
```python
# Lower threshold if rays are too dim
output_rays = element.interact_with_ray(ray, intersection, epsilon=1e-3, intensity_threshold=0.001)  # Lower from 0.02
```

---

## 📖 Further Reading

- **ARCHITECTURE_TRANSFORMATION_COMPLETE.md** - Complete overview
- **PHASE1_TDD_IMPLEMENTATION_COMPLETE.md** - Data layer details
- **PHASE2_POLYMORPHIC_ELEMENTS_COMPLETE.md** - Raytracing details
- **INTEGRATION_COMPLETE.md** - Integration guide
- **ARCHITECTURE_CRITIQUE_AND_STRATEGY.md** - Why this architecture

---

## 🤝 Contributing

### Adding a New Element Type

1. Create dataclass in `data/optical_properties.py`
2. Add case in `OpticalInterface.from_legacy_*`
3. Create element class in `raytracing/elements/`
4. Add case in `integration/adapter.py`
5. Write tests!

Example: Adding a diffraction grating (50 lines total)

```python
# 1. In data/optical_properties.py
@dataclass
class GratingProperties(OpticalProperties):
    lines_per_mm: float = 600.0
    order: int = 1
    
    def get_element_type(self) -> str:
        return "grating"

# 2. In raytracing/elements/grating.py
class Grating(IOpticalElement):
    def __init__(self, optical_iface: OpticalInterface):
        self.interface = optical_iface
        assert isinstance(optical_iface.properties, GratingProperties)
        self.lines_per_mm = optical_iface.properties.lines_per_mm
        self.order = optical_iface.properties.order
    
    def interact_with_ray(self, ray, intersection, epsilon, threshold):
        """Grating equation: m*λ = d*(sin(θ_out) - sin(θ_in))"""
        # ... implement diffraction physics ...
        return [diffracted_ray]
    
    def get_geometry(self):
        return self.interface.geometry.p1, self.interface.geometry.p2
    
    def get_bounding_box(self):
        p1, p2 = self.get_geometry()
        return np.minimum(p1, p2), np.maximum(p1, p2)

# 3. In integration/adapter.py - add case
elif element_type == "grating":
    return Grating(optical_iface)

# Done! Now you can use gratings in your optical system.
```

---

## 🎉 You're Ready!

You now know how to:
- ✅ Create optical elements
- ✅ Convert legacy interfaces
- ✅ Use the new raytracing system
- ✅ Test your code
- ✅ Integrate with existing UI
- ✅ Add new element types

**Happy raytracing!** 🚀

---

**Questions?** See the comprehensive guides or examine the test files for more examples.

