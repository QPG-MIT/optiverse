# Component Placement Mode Implementation

## Overview
Successfully reworked the component placement system to use an active placement mode with ghost preview, similar to the pipet tool. Components are no longer randomly placed on the canvas when clicking toolbar buttons.

## What Changed

### Before
- Clicking a toolbar button (Source, Lens, Mirror, Beamsplitter, Text) would immediately create the component at position (0, 0) or center
- User had to manually move the component to the desired location
- Could only place one component at a time
- Poor UX for precise placement

### After
- Clicking a toolbar button enters **placement mode**
- A **ghost preview** appears that follows the cursor
- Component is placed only when the user **clicks on the canvas**
- **Placement mode stays active** - place multiple components without re-clicking the button
- User can **cancel** placement by right-clicking or pressing Escape
- Much better UX for precise component placement and batch operations

## How It Works

### 1. Entering Placement Mode
When you click any component button in the toolbar (or menu):
- The button becomes visually highlighted (checked state)
- The cursor changes to a crosshair
- A tooltip appears: "Click to place {component}. Right-click or Escape to cancel."
- The system enters placement mode

### 2. Ghost Preview
- As you move the mouse over the canvas, a semi-transparent **ghost preview** appears
- The ghost shows exactly what will be placed and where
- Opacity is set to 0.5 for the ghost effect
- The ghost respects snap-to-grid settings if enabled

### 3. Placing the Component
- **Left-click** on the canvas to place the component at the cursor position
- The component is created with default parameters
- The component is automatically selected after placement
- **The placement mode stays active** so you can place more components
- Just keep clicking to place additional components
- The ghost reappears as you move the cursor after each placement
- Autotrace is triggered if enabled (for optical components)

### 4. Canceling Placement
You can cancel placement in two ways:
- **Right-click** anywhere on the canvas
- Press **Escape** key

Both methods will:
- Remove the ghost preview
- Exit placement mode
- Restore the normal cursor
- Uncheck the toolbar button

## Technical Details

### State Management
New state variables added to MainWindow:
```python
self._placement_mode = False       # Is placement mode active?
self._placement_type = None        # "source", "lens", "mirror", "beamsplitter", or "text"
self._placement_ghost = None       # The ghost preview item
```

### Toolbar Actions
All component toolbar actions are now **checkable**:
- `act_add_source`
- `act_add_lens`
- `act_add_mirror`
- `act_add_bs`
- `act_add_text`

They toggle placement mode instead of directly creating components.

### Key Methods

#### `_toggle_placement_mode(component_type: str, on: bool)`
- Handles entering/exiting placement mode
- Disables other conflicting modes (pipet, other placements)
- Changes cursor and shows tooltip

#### `_create_placement_ghost(component_type: str, scene_pos: QPointF)`
- Creates a semi-transparent ghost preview of the component
- Uses the same default parameters as the final component
- Adds the ghost to the scene

#### `_update_placement_ghost(scene_pos: QPointF)`
- Updates the ghost position as the mouse moves
- Applies snap-to-grid if enabled

#### `_place_component_at(component_type: str, scene_pos: QPointF)`
- Creates the actual component at the specified position
- Connects all necessary signals
- Adds to undo stack
- Broadcasts to collaboration if active

#### `_cancel_placement_mode(except_type: str | None)`
- Cleans up ghost preview
- Resets state variables
- Unchecks toolbar buttons
- Restores cursor

### Event Handling
Enhanced the `eventFilter` method to handle placement mode events:

**Mouse Tracking**:
- Enabled on both the view and viewport when entering placement mode
- This allows mouse move events to be received even without button press
- Disabled when exiting placement mode to avoid performance impact

**Mouse Move** (`GraphicsSceneMouseMove`):
- Creates ghost on first move if it doesn't exist
- Updates ghost position on subsequent moves

**Mouse Press** (`GraphicsSceneMousePress`):
- Left-click: Places component and **keeps placement mode active**
- Ghost is cleared and recreated on next mouse move for the next placement
- Right-click: Cancels placement and exits mode

**Key Press** (new `keyPressEvent` method):
- Escape: Cancels placement mode

### Integration with Existing Features
- **Snap to grid**: Ghost and final placement respect snap-to-grid setting
- **Undo/Redo**: Component placement is added to undo stack
- **Collaboration**: Component creation is broadcast to collaborators
- **Autotrace**: Triggered automatically after placement if enabled
- **Pipet tool**: Placement mode and pipet mode are mutually exclusive

## User Experience Benefits

### Before (Single Component)
1. Click "Lens" button
2. Lens appears at (0,0)
3. Scroll to find the lens
4. Drag lens to desired location
5. Fine-tune position

### After (Single Component)
1. Click "Lens" button
2. See ghost preview immediately
3. Move mouse to desired location
4. Click to place
5. Done! ✓

### After (Multiple Components)
1. Click "Lens" button once
2. Click at position 1 - lens placed
3. Click at position 2 - lens placed
4. Click at position 3 - lens placed
5. Right-click or Escape to finish

**Much more efficient for placing multiple components!** No need to go back to the toolbar repeatedly.

## Consistency
This implementation matches the interaction pattern of:
- Pipet tool (active mode with cursor change)
- Ruler tool (2-click placement with ghost)
- Drag-and-drop from library (ghost preview during drag)

All placement operations now follow similar UX patterns for consistency.

## Code Cleanup
Removed the old component creation methods that are no longer used:
- `add_source()`
- `add_lens()`
- `add_mirror()`
- `add_bs()`
- `add_text()`

These are replaced by the unified `_place_component_at()` method that handles all component types.

## Testing Checklist

To test the new placement mode:

1. **Basic Placement**
   - [ ] Click Source button - ghost appears and follows cursor
   - [ ] Click on canvas - source is placed at cursor
   - [ ] Repeat for Lens, Mirror, Beamsplitter, Text

2. **Multiple Placement**
   - [ ] Click Lens button once
   - [ ] Click multiple times on canvas - lens is placed each time
   - [ ] Ghost reappears after each placement
   - [ ] Button stays checked during multiple placements

3. **Ghost Preview**
   - [ ] Ghost is semi-transparent (50% opacity)
   - [ ] Ghost shows correct component type and orientation
   - [ ] Ghost follows cursor smoothly

4. **Snap to Grid**
   - [ ] Enable snap to grid
   - [ ] Ghost snaps to integer coordinates
   - [ ] Final placement is snapped

5. **Cancellation**
   - [ ] Right-click cancels placement
   - [ ] Escape key cancels placement
   - [ ] Ghost is removed on cancel
   - [ ] Button is unchecked on cancel

6. **Mode Switching**
   - [ ] Clicking different component button switches mode
   - [ ] Only one button is checked at a time
   - [ ] Pipet and placement modes are mutually exclusive

7. **Menu Integration**
   - [ ] Insert menu items work with placement mode
   - [ ] Menu items show same behavior as toolbar

8. **Undo/Redo**
   - [ ] Placed component can be undone
   - [ ] Undone component can be redone

9. **Collaboration**
   - [ ] Placed components are broadcast to other users
   - [ ] Remote users see the component appear

## Future Enhancements

Possible improvements for later:
- [ ] Add keyboard shortcut to cycle through component types
- [ ] Allow rotation of ghost with mouse wheel before placement
- [ ] Add numeric input dialog for precise coordinate entry
- [ ] Remember last placement mode and restore on next session
- ✅ ~~Add "place another" option to keep mode active after placement~~ **DONE - stays active by default!**

