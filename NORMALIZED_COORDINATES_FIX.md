# Normalized 1000px Coordinate System - Enforced Limits ✅

## Problem

Users could enter line coordinates up to 1,000,000 pixels, violating the normalized 1000px system where all coordinates should be in the range [0, 1000].

## Solution

Implemented proper coordinate normalization and limits throughout the Component Editor:

### 1. Limited Spinbox Ranges

**Before:** Range 0 to 1,000,000 px
```python
self.p1_x.setRange(0, 1e6)  # ❌ Too large!
```

**After:** Range 0 to 1000 px
```python
self.p1_x.setRange(0, 1000)  # ✅ Normalized space
```

### 2. Coordinate Normalization

**Canvas → Spinboxes (Display):**
- Canvas returns actual image pixel coordinates
- Normalize to 1000px space for display in spinboxes

```python
# Normalize canvas clicks to 1000px space
_, h_px = self.canvas.image_pixel_size()
scale = 1000.0 / float(h_px)
self.p1_x.setValue(canvas_p1[0] * scale)  # Normalized
```

**Spinboxes → Canvas (User Edit):**
- Spinboxes contain normalized 1000px coordinates
- Denormalize to actual image space for canvas

```python
# Denormalize spinbox values to actual image space
scale = float(h_px) / 1000.0
canvas_p1 = (spinbox_p1[0] * scale, spinbox_p1[1] * scale)
self.canvas.set_points(canvas_p1, canvas_p2)
```

**Loading from Library:**
- Library stores normalized 1000px coordinates
- Denormalize to actual image space for canvas

```python
# rec.line_px is in normalized 1000px space
scale = float(h_px) / 1000.0
p1 = (float(rec.line_px[0]) * scale, float(rec.line_px[1]) * scale)
self.canvas.set_points(p1, p2)
```

### 3. Computation in Normalized Space

All calculations now use normalized coordinates:

```python
# Get normalized coordinates from spinboxes
p1_norm = (float(self.p1_x.value()), float(self.p1_y.value()))
p2_norm = (float(self.p2_x.value()), float(self.p2_y.value()))

# Compute in normalized space
dx = p2_norm[0] - p1_norm[0]
dy = p2_norm[1] - p1_norm[1]
px_len = (dx*dx + dy*dy)**0.5

# mm_per_pixel is computed from normalized coordinates
mm_per_px = object_height / px_len
```

## Coordinate Flow

```
User clicks on image
      ↓
Canvas returns actual pixels (e.g., 800x2000 image)
      ↓
Normalize to 1000px space → Spinboxes (0-1000 range)
      ↓
User can edit in spinboxes (limited to 0-1000)
      ↓
Denormalize to actual pixels → Canvas
      ↓
Save: Normalized coordinates → JSON
```

## Example

**Image:** 800x2000 pixels
**User clicks:** (400, 1000) in actual image space

**Displayed in spinboxes:**
- X: 400 × (1000/2000) = **200 px** (normalized)
- Y: 1000 × (1000/2000) = **500 px** (normalized)

**User edits to:** (250, 600) in spinboxes

**Sent to canvas:**
- X: 250 × (2000/1000) = **500 px** (actual)
- Y: 600 × (2000/1000) = **1200 px** (actual)

**Saved to JSON:**
- `"line_px": [250, 600, ...]` (normalized 1000px space)

## Benefits

✅ **Enforced limits**: Coordinates always ≤ 1000  
✅ **Consistent**: All saved coordinates in same normalized space  
✅ **Accurate**: Proper normalization in both directions  
✅ **Clear**: Spinboxes show actual stored values  

## Files Modified

- `src/optiverse/ui/views/component_editor_dialog.py`
  - Limited spinbox ranges to [0, 1000]
  - Added normalization when canvas → spinboxes
  - Added denormalization when spinboxes → canvas
  - Added denormalization when loading from library
  - Separated `_update_derived_labels()` and `_update_computed_values()`

## Testing Status

- ✅ No linter errors
- ✅ Spinbox maximum: 1000px
- ✅ Coordinates properly normalized/denormalized
- ✅ Loading from library works correctly

---

**Result:** All coordinates now properly constrained to normalized 1000px space! 🎯

