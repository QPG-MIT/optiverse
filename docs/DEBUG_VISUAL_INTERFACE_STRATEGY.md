# Debug Strategy: Visual Interface Not Showing

## Problem Report
User reports:
1. Not seeing multiple colored lines in component editor
2. Old "line points" interface still visible

## Root Causes Identified

### 1. Old Line Points UI Still Visible
**Location**: `src/optiverse/ui/views/component_editor_dialog.py` lines 247-260

The old UI section with:
- "─── Line Points (px) ───" header
- Point 1 (X, Y spinboxes)
- Point 2 (X, Y spinboxes)

These are still being displayed and are NOT hidden for any component type.

### 2. Lines Not Being Created on Image Load
When a simple component loads an image, no default line is being created automatically.

### 3. No Visual Feedback on Startup
When the component editor opens, no placeholder or instruction is shown about the visual line system.

## Solution Strategy

### Phase 1: Hide Old UI (Immediate)
1. Add labels/widgets to track old UI elements
2. Hide them by default or based on a flag
3. Keep them only for debugging/backward compatibility if needed

### Phase 2: Ensure Lines Are Created
1. When image is loaded for simple component → create default line
2. When image is loaded for refractive object → sync interfaces to canvas
3. Make sure `_sync_interfaces_to_canvas()` is called at the right times

### Phase 3: Visual Feedback
1. Show status message about dragging line endpoints
2. Add visual hint on canvas when no lines exist
3. Update tooltip/help text

### Phase 4: Testing Checklist
- [ ] Load simple component → see ONE colored line
- [ ] Change component kind → line color updates
- [ ] Load refractive object with preset → see MULTIPLE colored lines
- [ ] Drag endpoint → updates immediately
- [ ] Old line points UI is hidden
- [ ] Select interface from list → highlights on canvas
- [ ] Canvas line selection → highlights in list

## Implementation Plan

### Step 1: Remove/Hide Old Line Points UI
Options:
A. **Complete removal** (cleanest, recommended)
   - Remove the p1_x, p1_y, p2_x, p2_y widgets
   - Remove the "Line Points" section from form
   - Remove `_on_manual_point_changed` method

B. **Hide by default** (safer, allows rollback)
   - Keep widgets but hide them
   - Add a debug flag to show them if needed
   - `self.p1_x.setVisible(False)` etc.

**Recommendation**: Option B for now, transition to A later

### Step 2: Fix Line Creation Flow

```python
def _set_image(self, pix, source_path):
    # ... load image ...
    self._sync_interfaces_to_canvas()  # ✓ Already done
    
    # But _sync_interfaces_to_canvas needs to handle empty case
    # For simple components with no existing lines
```

Update `_sync_interfaces_to_canvas()` to ALWAYS create a default line for simple components.

### Step 3: Ensure Canvas Updates

Make sure:
1. `canvas.update()` is called after adding lines
2. Lines list is not empty when expected
3. Paint event is triggered

### Step 4: Add Debug Logging

Temporarily add print statements:
- When lines are added
- When paint event draws lines
- When sync is called

## Expected Behavior After Fix

### Simple Component (Lens)
1. Open component editor
2. Drop lens image
3. **See ONE cyan line** in center
4. Drag endpoints to align with lens
5. No "Line Points" UI visible

### Refractive Object (BS Cube)
1. Select "refractive_object"
2. Drop image
3. Click "BS Cube Preset"
4. **See FIVE colored lines**: 4 blue + 1 green diagonal
5. Drag any endpoint
6. Lines update immediately
7. Select in list → highlights on canvas

## Code Locations

1. **Old UI to hide**: Lines 247-260
2. **Sync function**: Lines 471-527
3. **Image load**: Lines 415-425
4. **Paint event**: `multi_line_canvas.py` line 233

## Next Actions

1. Hide old line points UI
2. Add debug print to see if lines are being created
3. Force canvas repaint after adding lines
4. Test with actual component editor

