# Quick Test: Curved Surface Visualization

## What Was Fixed

1. **✅ Curved surfaces now display as arcs** (not straight lines)
2. **✅ Coordinate system centered** ((0,0) at center of canvas)

## 2-Minute Visual Test

### Step 1: Launch and Import

```bash
cd /Users/benny/Desktop/MIT/git/optiverse
python src/optiverse/app/main.py
```

1. Click "Component Editor"
2. Click "Import Zemax…" button
3. Select `/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx`
4. Click OK on success dialog

### Step 2: Load Background Image

1. File → Open Image
2. Select **any image** (just need a background)
3. Click Open

### Step 3: Visual Verification

You should now see **THREE CURVED LINES** on the canvas:

```
Expected visualization (side view of doublet lens):

        Interface 1 (Convex)
              │
              ▼
         ╱────)
        (      ╲
         ╲    (╲
          ────) ╲────
              ▲   ▲
              │   │
              │   Interface 3
              │   (Gentle concave)
              │
        Interface 2 (Concave)
```

**✅ Checklist:**
- [ ] Interface 1 curves to the RIGHT ) - convex
- [ ] Interface 2 curves to the LEFT ( - concave  
- [ ] Interface 3 curves to the LEFT ( - gentle concave
- [ ] Interfaces are centered on canvas
- [ ] Can drag interface endpoints
- [ ] Curves maintain shape when dragged

### What You Should See

**Interface 1** (Entry surface):
- Position: X ≈ center-left
- Shape: **Convex )** curving to the right
- Radius: +66.68mm (positive = convex)

**Interface 2** (Cemented surface):
- Position: X ≈ 4mm from Interface 1
- Shape: **Concave (** curving to the left
- Radius: -53.70mm (negative = concave)

**Interface 3** (Exit surface):
- Position: X ≈ 1.5mm from Interface 2
- Shape: **Gently concave (** curving to the left
- Radius: -259.41mm (negative = concave, large radius = gentle curve)

### Coordinate System Test

The coordinate system is now centered:

```
        Y (positive up)
        ▲
        │
        │
◄───────0───────► X (positive right)
        │
        │
        ▼ Y (negative down)
```

**To verify:**
1. Expand Interface 1 in right panel
2. Check coordinates:
   - X₁: 0.000 mm (on optical axis at start)
   - Y₁: -6.350 mm (bottom edge)
   - X₂: 0.000 mm (same X)
   - Y₂: +6.350 mm (top edge)

This means:
- ✅ Y=0 is at center (optical axis)
- ✅ Y>0 is above center
- ✅ Y<0 is below center

## What If It Doesn't Work?

### No Curves Visible?

**Possible causes:**
1. **No background image loaded**
   - Solution: File → Open Image
   - The canvas requires an image to establish coordinates

2. **Interfaces collapsed in panel**
   - Solution: Click ▶ arrows to expand each interface
   - Verify `is_curved: True` and `radius_of_curvature_mm` has values

3. **Wrong Zemax file**
   - Solution: Make sure you imported `AC254-100-B-Zemax(ZMX).zmx`
   - Check success dialog shows 3 interfaces

### Still Seeing Straight Lines?

Run verification:
```bash
cd /Users/benny/Desktop/MIT/git/optiverse
python verify_zemax_import.py
```

If this passes, the data is correct. The issue would be visual.

Check the code changes were applied:
```bash
grep -n "_draw_curved_line" src/optiverse/objects/views/multi_line_canvas.py
```

Should show: `442:    def _draw_curved_line(...`

## Expected Appearance

### Before Fix
```
All straight lines:

  |     |     |
  |     |     |
  |     |     |
  |     |     |
  
(No curvature visible)
```

### After Fix
```
Curved surfaces:

   )    (    (
  /      \    \
 |        |    |
  \      /    /
   )    (    (
   
✓ Convex  ✓ Concave  ✓ Concave
  (+R)      (-R)       (-R)
```

## Properties Panel Verification

Expand Interface 1 in the right panel. You should see:

```yaml
Type: 🔵 Refractive Interface

Position:
  X₁ (mm): 0.000
  Y₁ (mm): -6.350
  X₂ (mm): 0.000
  Y₂ (mm): 6.350

Optics:
  Incident Index (n₁): 1.000
  Transmitted Index (n₂): 1.641
  Curved Surface: ☑ (checked)        ← Should be checked
  Radius of Curvature (mm): 66.680   ← Should be positive
```

For Interface 2, the radius should be **negative** (-53.70).

## Summary

If you see **three curved lines** (not straight lines) with:
- First curve bulging **right** )
- Second curve bulging **left** (
- Third curve bulging **left** (

**Then it works! ✅**

The curvature data is now being visualized correctly, and the coordinate system is centered as requested.

## Next Steps

Try:
1. **Dragging endpoints**: Curves should maintain their shape
2. **Different Zemax files**: Import other .zmx files
3. **Creating interfaces**: Add Interface → Refractive Interface
4. **Editing curvature**: Change `radius_of_curvature_mm` to see curve change

---

**Files Changed:**
- `src/optiverse/objects/views/multi_line_canvas.py`
  - Added curved line drawing
  - Centered coordinate system

**Status:** ✅ **READY TO TEST**

