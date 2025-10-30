# Pipet Tool Waveplate Fix

## Problem

The pipet tool was showing the **same Jones vector** before and after a waveplate, even though waveplates should transform the polarization state.

**Example:**
- Source: Horizontal polarization `[1, 0]`
- QWP at 45°: Should convert to circular `[0.707, 0.707i]`
- **Bug**: Pipet showed the SAME polarization (circular) both before and after the QWP!

## Root Cause

The raytracing system stores ray paths as `RayPath` objects, where each `RayPath` has:
- A list of points (the ray's trajectory)
- A single polarization state for all those points

When a ray passed through a waveplate, the code:
1. Calculated the transformed polarization (`pol2`)
2. Continued the ray with `pts + [P2]` - adding the new point to the existing points list
3. All points (including those before the waveplate) were stored in one `RayPath` with the **transformed** polarization

This meant clicking on the ray before the waveplate showed the **output** polarization, not the input polarization!

## Solution

Modified `src/optiverse/core/use_cases.py` in the waveplate handling (around line 212):

### Before:
```python
if kind == "waveplate":
    # ... calculate pol2 ...
    
    V2 = normalize(V)
    P2 = P + V2 * EPS_ADV
    # Continue with same points list - ALL points get pol2!
    stack.append((pts + [P2.copy()], P2.copy(), V2, remaining - EPS_ADV, obj, events + 1, I, pol2, wl))
    continue
```

### After:
```python
if kind == "waveplate":
    # ... calculate pol2 ...
    
    # Create a RayPath for the segment UP TO the waveplate with OLD polarization
    # This ensures the pipette tool shows correct polarization before the waveplate
    if len(pts) >= 2:
        a = int(255 * max(0.0, min(1.0, I)))
        paths.append(RayPath(pts, (base_rgb[0], base_rgb[1], base_rgb[2], a), pol, wl))
    
    # Start a NEW ray segment with the NEW polarization after the waveplate
    V2 = normalize(V)
    P2 = P + V2 * EPS_ADV
    # Start new segment with just P2 (not all previous points)
    stack.append(([P2.copy()], P2.copy(), V2, remaining - EPS_ADV, obj, events + 1, I, pol2, wl))
    continue
```

## Key Changes

1. **Create RayPath before waveplate**: Finalize the current ray segment with the OLD polarization
2. **Start fresh segment**: Begin a new segment with only the post-waveplate position and NEW polarization
3. **Separate polarization states**: Now there are distinct segments with different Jones vectors

## Impact

- ✅ Pipet tool now shows correct polarization **before** the waveplate
- ✅ Pipet tool now shows correct polarization **after** the waveplate  
- ✅ No change to visual rendering (rays look the same)
- ✅ No impact on beamsplitters, mirrors, or lenses (they already create separate segments)

## Similar Elements

**Elements that change polarization and already create separate segments:**
- Mirrors: Create new segment due to reflection (direction change)
- Beamsplitters: Create separate transmitted/reflected segments
- PBS: Create separate H/V components

**Elements that DON'T need this fix:**
- Lenses: Don't change polarization (`transform_polarization_lens` returns input unchanged)
- Dichroics: Don't change polarization (preserve input state)
- Refractive interfaces: Simplified model preserves polarization

**Elements that might need similar fix in future:**
- Faraday rotators (if added)
- Polarization rotators (if added)
- Any other elements that transform polarization without splitting the beam

## Testing

To verify the fix works:

1. Create a scene with a polarized source and waveplate:
   ```python
   - Source at (0, 0) with horizontal polarization
   - QWP at x=100mm with 45° fast axis, 90° phase shift
   ```

2. Enable auto-trace and activate pipet tool

3. Click on ray **before** QWP (e.g., x=50mm):
   - Should show: Jones `[1, 0]`, horizontal linear (Q≈1, V≈0)

4. Click on ray **after** QWP (e.g., x=150mm):
   - Should show: Jones `[0.707, 0.707i]`, circular (Q≈0, V≈1)

5. Verify the Jones vectors are **different** before and after

## Additional Notes

- The fix is minimal and only affects waveplate interactions
- Ray segments may now be slightly shorter (split at waveplates)
- This is the correct physical representation: polarization changes at the waveplate boundary
- The pipet tool can now be used to verify waveplate transformations
- Useful for debugging QWP/HWP configurations and polarization optics

## Files Modified

- `src/optiverse/core/use_cases.py`: Waveplate handling in `_trace_single_ray_worker()`
  - Lines ~212-248: Split ray path at waveplate boundary

## Related Issues

- Original report: "Pipet tool shows same Jones vector before and after waveplate"
- Affects all waveplate types (QWP, HWP, custom phase shifts)
- Does not affect other optical elements

