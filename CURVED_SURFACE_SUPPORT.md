# Curved Surface Support Implementation

**Date**: October 30, 2025  
**Status**: ⚠️ **PARTIALLY IMPLEMENTED - NEEDS INTEGRATION**  
**Priority**: 🔴 **CRITICAL** for proper lens raytracing

---

## 🎯 Problem

**Current Issue**: All optical interfaces are treated as straight lines, which doesn't work correctly for curved lens surfaces. Lenses need proper curved geometry for accurate raytracing.

**Impact**: 
- ❌ Lenses don't focus correctly
- ❌ Curved surfaces treated as flat
- ❌ Incorrect ray bending at curved interfaces
- ❌ Wrong optical behavior

---

## ✅ What Was Implemented

### 1. CurvedSegment Class ✅

**File**: `src/optiverse/data/geometry.py`

**New Classes**:
- `CurvedSegment` - Represents a circular arc (curved interface)
- `GeometrySegment` - Type alias for `LineSegment | CurvedSegment`

**Key Features**:
```python
@dataclass
class CurvedSegment:
    p1: np.ndarray  # Start point
    p2: np.ndarray  # End point
    radius_of_curvature_mm: float  # + or - radius
    is_curved: bool = True
    
    # Methods:
    def normal_at_point(point) -> np.ndarray  # Normal at specific point!
    def tangent_at_point(point) -> np.ndarray  # Tangent at specific point!
    def get_center() -> np.ndarray  # Center of curvature
    def get_radius() -> float  # Absolute radius
```

**Why This Matters**:
- ✅ Proper normal vectors at intersection points
- ✅ Correct Snell's law calculations
- ✅ Accurate lens focusing

### 2. Updated LineSegment ✅

**Added fields** for compatibility:
```python
@dataclass
class LineSegment:
    p1: np.ndarray
    p2: np.ndarray
    is_curved: bool = False  # NEW!
    radius_of_curvature_mm: float = 0.0  # NEW!
```

### 3. Updated Exports ✅

**File**: `src/optiverse/data/__init__.py`

Now exports:
- `LineSegment`
- `CurvedSegment` ⬅️ NEW!
- `GeometrySegment` ⬅️ NEW!

---

## ⚠️ What Still Needs To Be Done

### 1. Ray-Circle Intersection Algorithm ⚡ CRITICAL

**Need to add** to `src/optiverse/core/geometry.py`:

```python
def ray_hit_curved_element(
    P: np.ndarray,  # Ray position
    V: np.ndarray,  # Ray direction
    segment: CurvedSegment
) -> Optional[Tuple[float, np.ndarray, np.ndarray, np.ndarray]]:
    """
    Calculate ray intersection with a curved surface (circular arc).
    
    Returns:
        Tuple of (t, hit_point, tangent, normal) or None
    """
    center = segment.get_center()
    radius = segment.get_radius()
    
    # Ray-circle intersection
    # Ray: R(t) = P + t*V
    # Circle: |R - center|² = radius²
    
    # Quadratic equation: a*t² + b*t + c = 0
    PC = P - center
    a = np.dot(V, V)
    b = 2.0 * np.dot(V, PC)
    c = np.dot(PC, PC) - radius**2
    
    discriminant = b**2 - 4*a*c
    
    if discriminant < 0:
        return None  # No intersection
    
    sqrt_disc = math.sqrt(discriminant)
    t1 = (-b - sqrt_disc) / (2*a)
    t2 = (-b + sqrt_disc) / (2*a)
    
    # Find valid intersection (positive t, within arc bounds)
    for t in [t1, t2]:
        if t <= 0:
            continue
        
        hit_point = P + t * V
        
        # Check if hit_point is within arc bounds (between p1 and p2)
        if _point_on_arc(hit_point, segment):
            # Calculate normal and tangent at hit point
            normal = segment.normal_at_point(hit_point)
            tangent = segment.tangent_at_point(hit_point)
            
            return (t, hit_point, tangent, normal)
    
    return None


def _point_on_arc(point: np.ndarray, segment: CurvedSegment) -> bool:
    """
    Check if a point lies within the arc bounds.
    
    The point must be:
    1. On the circle (approximately)
    2. Between the angular extents defined by p1 and p2
    """
    center = segment.get_center()
    
    # Angles from center to p1, p2, and point
    v_p1 = segment.p1 - center
    v_p2 = segment.p2 - center
    v_point = point - center
    
    # Calculate angles
    angle_p1 = math.atan2(v_p1[1], v_p1[0])
    angle_p2 = math.atan2(v_p2[1], v_p2[0])
    angle_point = math.atan2(v_point[1], v_point[0])
    
    # Normalize angles to [0, 2π]
    angle_p1 = angle_p1 % (2 * math.pi)
    angle_p2 = angle_p2 % (2 * math.pi)
    angle_point = angle_point % (2 * math.pi)
    
    # Check if angle_point is between angle_p1 and angle_p2
    # Handle wraparound
    if angle_p1 < angle_p2:
        return angle_p1 <= angle_point <= angle_p2
    else:
        return angle_point >= angle_p1 or angle_point <= angle_p2
```

**Priority**: 🔴 **CRITICAL** - Without this, rays can't hit curved surfaces!

---

### 2. Update OpticalInterface ⚡ HIGH PRIORITY

**File**: `src/optiverse/data/optical_interface.py`

**Change geometry type**:
```python
from .geometry import LineSegment, CurvedSegment, GeometrySegment

@dataclass
class OpticalInterface:
    geometry: GeometrySegment  # Was: LineSegment, Now: LineSegment | CurvedSegment
    properties: OpticalPropertyType
    interface_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

**Add helper method**:
```python
def create_geometry(p1: np.ndarray, p2: np.ndarray, 
                   is_curved: bool = False, 
                   radius_of_curvature_mm: float = 0.0) -> GeometrySegment:
    """
    Create appropriate geometry (Line or Curved) based on parameters.
    
    Args:
        p1, p2: Endpoints
        is_curved: Whether the surface is curved
        radius_of_curvature_mm: Radius (if curved)
    
    Returns:
        LineSegment or CurvedSegment
    """
    if is_curved and abs(radius_of_curvature_mm) > 1e-6:
        return CurvedSegment(p1, p2, radius_of_curvature_mm)
    else:
        return LineSegment(p1, p2)
```

---

### 3. Update Adapter ⚡ HIGH PRIORITY

**File**: `src/optiverse/integration/adapter.py`

**Update `from_legacy_interface_definition`**:
```python
@classmethod
def from_legacy_interface_definition(cls, old_iface: OldInterfaceDefinition) -> OpticalInterface:
    # Extract geometry with curvature support
    p1 = np.array([old_iface.x1_mm, old_iface.y1_mm])
    p2 = np.array([old_iface.x2_mm, old_iface.y2_mm])
    
    # Check if curved
    is_curved = getattr(old_iface, 'is_curved', False)
    radius = getattr(old_iface, 'radius_of_curvature_mm', 0.0)
    
    # Create appropriate geometry
    if is_curved and abs(radius) > 1e-6:
        geometry = CurvedSegment(p1, p2, radius)
    else:
        geometry = LineSegment(p1, p2)
    
    # ... rest of conversion ...
    
    return cls(geometry=geometry, properties=properties)
```

---

### 4. Update Elements to Use Curved Intersection ⚡ CRITICAL

**Files**: All element implementations in `src/optiverse/raytracing/elements/`

**For each element** (Mirror, Lens, Refractive, etc.):

```python
def intersect(self, ray_position: np.ndarray, ray_direction: np.ndarray):
    """Calculate intersection with this element's surface."""
    geometry = self._geometry
    
    if geometry.is_curved:
        # Use curved intersection
        from optiverse.core.geometry import ray_hit_curved_element
        return ray_hit_curved_element(ray_position, ray_direction, geometry)
    else:
        # Use straight line intersection
        from optiverse.core.geometry import ray_hit_element
        return ray_hit_element(ray_position, ray_direction, geometry.p1, geometry.p2)
```

---

### 5. Update Legacy System (Optional)

**File**: `src/optiverse/core/use_cases.py`

The legacy system also needs curved surface support if you want backward compatibility:

```python
# In _trace_single_ray_worker:

# For each element, check if curved
for obj, A, B in lenses:
    if hasattr(obj, 'is_curved') and obj.is_curved:
        result = ray_hit_curved_element(P, V, obj)
    else:
        result = ray_hit_element(P, V, A, B)
```

---

## 📋 Implementation Checklist

### Phase 1: Core Geometry (DONE ✅)
- [x] Create `CurvedSegment` class
- [x] Add `is_curved` to `LineSegment`
- [x] Update exports

### Phase 2: Ray-Curve Intersection (TODO ⚠️)
- [ ] Implement `ray_hit_curved_element()`
- [ ] Implement `_point_on_arc()`  
- [ ] Add tests for ray-circle intersection

### Phase 3: Data Layer Integration (TODO ⚠️)
- [ ] Update `OpticalInterface.geometry` type
- [ ] Add `create_geometry()` helper
- [ ] Update `from_legacy_*` converters

### Phase 4: Adapter Integration (TODO ⚠️)
- [ ] Update `convert_legacy_interface_to_optical()`
- [ ] Handle curved geometry in adapter

### Phase 5: Element Integration (TODO ⚠️)
- [ ] Update `Mirror.intersect()`
- [ ] Update `Lens.intersect()`
- [ ] Update `RefractiveElement.intersect()`
- [ ] Update other elements

### Phase 6: Testing (TODO ⚠️)
- [ ] Test ray-circle intersection
- [ ] Test curved lens focusing
- [ ] Test curved mirror reflection
- [ ] Verify Zemax import with curved surfaces

---

## 🧪 Test Cases Needed

```python
def test_ray_hits_curved_lens():
    """Test ray intersection with curved lens surface."""
    # Create curved segment
    p1 = np.array([50.0, -10.0])
    p2 = np.array([50.0, 10.0])
    radius = 50.0  # 50mm radius of curvature
    
    segment = CurvedSegment(p1, p2, radius)
    
    # Ray heading straight toward lens
    ray_pos = np.array([0.0, 0.0])
    ray_dir = np.array([1.0, 0.0])
    
    # Should hit the curved surface
    result = ray_hit_curved_element(ray_pos, ray_dir, segment)
    
    assert result is not None
    t, hit_point, tangent, normal = result
    
    # Should hit around x=50
    assert abs(hit_point[0] - 50.0) < 1.0
    
    # Normal should point radially
    assert np.dot(normal, hit_point - segment.get_center()) > 0


def test_curved_lens_focusing():
    """Test that curved lens properly focuses rays."""
    # Create converging lens with curved surfaces
    # ... (similar to above but full lens system)
    
    # Parallel rays should converge to focal point
    assert rays_converge_to_focus()
```

---

## 🚀 Quick Start for Integration

**Immediate steps to get curved surfaces working**:

1. **Add ray-circle intersection** (5 min):
   - Copy the `ray_hit_curved_element()` function above
   - Add to `src/optiverse/core/geometry.py`

2. **Update adapter** (3 min):
   - Modify `from_legacy_interface_definition()` to create `CurvedSegment`

3. **Update elements** (2 min per element):
   - Add curved intersection check in each element's `intersect()` method

4. **Test** (10 min):
   - Create a simple curved lens
   - Trace rays through it
   - Verify proper focusing

**Total time**: ~30-45 minutes

---

## 💡 Why This Matters

### Before (Incorrect ❌):
```
Curved lens treated as flat line:

    |  ← Flat interface (wrong!)
    |
    |
```

Rays don't focus properly because the normal is the same everywhere.

### After (Correct ✅):
```
Curved lens with proper geometry:

    )  ← Curved interface (correct!)
   ( 
    )
```

Rays focus properly because normal varies along the curve.

---

## 🎯 Expected Behavior

### Converging Lens (Positive Curvature)
```
Parallel rays → → → )(  → \ | / → Focus point
                          \|/
                           *
```

### Diverging Lens (Negative Curvature)
```
Parallel rays → → → () → \  |  / → Diverging
                          \ | /
```

### Curved Mirror
```
Rays → → → (  ← ← ← Reflected rays
            \ | /
             \|/
              * Focus
```

---

## ⚠️ Current Workaround

Until full integration is complete, the **thin lens approximation** in the current system provides approximate behavior:
- Lenses use effective focal length (efl_mm)
- Rays are bent at the lens plane
- Not geometrically accurate but optically close

**However**: For accurate Zemax imports and complex lens systems, proper curved surface support is **essential**.

---

## 📚 References

**Files to modify**:
1. `src/optiverse/core/geometry.py` - Add ray-circle intersection
2. `src/optiverse/data/optical_interface.py` - Update geometry type
3. `src/optiverse/integration/adapter.py` - Handle curved conversion
4. `src/optiverse/raytracing/elements/*.py` - Use curved intersection

**New files created**:
1. `src/optiverse/data/geometry.py` - CurvedSegment class ✅

---

## 🎉 Benefits Once Complete

- ✅ Accurate lens raytracing
- ✅ Proper curved mirror reflection
- ✅ Correct Zemax import behavior
- ✅ Realistic optical simulations
- ✅ Physical accuracy

---

**Status**: Geometry classes created, integration pending  
**Priority**: Critical for lens raytracing  
**Effort**: ~1-2 hours for full integration  
**Impact**: Correct optical behavior

**Next step**: Implement `ray_hit_curved_element()` function!

