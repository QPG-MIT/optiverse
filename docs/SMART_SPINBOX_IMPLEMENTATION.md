# Smart SpinBox Implementation - Live Updates & Cursor-Aware Increments

## Overview

Enhanced all component editor dialogs with two major improvements:
1. **Live Updates**: Changes to x, y, and angle fields update the component in real-time (not just when clicking OK)
2. **Cursor-Aware Increments**: The up/down arrow buttons increment the digit at the cursor position, not a fixed ±0.1

## Implementation Details

### New Component: SmartDoubleSpinBox

Created `src/optiverse/ui/smart_spinbox.py` with two new spinbox classes:

#### `SmartDoubleSpinBox`
- Extends `QDoubleSpinBox` with intelligent increment behavior
- Increments the digit to the **left** of the cursor (the digit you just typed/are looking at)
- Examples of behavior:
  - Value: `123.456`, cursor at `12|3.456` → Up arrow → `133.456` (increments the '2' in tens place)
  - Value: `123.456`, cursor at `123|.456` → Up arrow → `124.456` (increments the '3' in ones place)
  - Value: `123.456`, cursor at `123.4|56` → Up arrow → `123.556` (increments the '4' in tenths place)
  - Value: `123.456`, cursor at `123.45|6` → Up arrow → `123.466` (increments the '5' in hundredths place)

#### `SmartSpinBox`
- Similar functionality for integer values
- Useful for future enhancements to integer fields

### Updated Components

All optical component editors now use `SmartDoubleSpinBox` for x, y, and angle fields:

1. **Lens Editor** (`src/optiverse/objects/lenses/lens_item.py`)
   - Live updates for: X Position, Y Position, Optical Axis Angle, EFL, Clear Length
   
2. **Mirror Editor** (`src/optiverse/objects/mirrors/mirror_item.py`)
   - Live updates for: X Position, Y Position, Optical Axis Angle, Length

3. **Beamsplitter Editor** (`src/optiverse/objects/beamsplitters/beamsplitter_item.py`)
   - Live updates for: X Position, Y Position, Optical Axis Angle, Length
   - T/R ratios and PBS settings still apply on OK (as they involve more complex interdependencies)

4. **Dichroic Mirror Editor** (`src/optiverse/objects/dichroics/dichroic_item.py`)
   - Live updates for: X Position, Y Position, Optical Axis Angle, Length
   - Wavelength parameters apply on OK

5. **Waveplate Editor** (`src/optiverse/objects/waveplates/waveplate_item.py`)
   - Live updates for: X Position, Y Position, Element Angle, Clear Length
   - Phase shift and fast axis parameters apply on OK

6. **SLM Editor** (`src/optiverse/objects/misc/slm_item.py`)
   - Live updates for: X Position, Y Position, Optical Axis Angle, Length

7. **Source Editor** (`src/optiverse/objects/sources/source_item.py`)
   - Live updates for: X Position, Y Position, Optical Axis Angle
   - Other source parameters (rays, color, polarization) apply on OK

## Technical Implementation

### Live Update Pattern

Each editor creates lambda functions connected to `valueChanged` signals:

```python
def update_position():
    self.setPos(x.value(), y.value())
    self.params.x_mm = x.value()
    self.params.y_mm = y.value()
    self.edited.emit()

x.valueChanged.connect(update_position)
y.valueChanged.connect(update_position)
```

This pattern ensures:
- Component position updates immediately in the scene
- Parameters are kept in sync
- The `edited` signal notifies the system of changes
- Undo/redo system tracks changes appropriately

### Cursor-Aware Step Algorithm

The implementation uses **two key mechanisms**:

#### 1. Event Filter - Intercept Keyboard Events
The `eventFilter()` method intercepts Up/Down arrow key presses from the line edit **before** Qt's default handling:
- Installs an event filter on the line edit in `__init__()`
- When Up/Down keys are pressed while editing, captures the current cursor position
- Calls our custom `stepBy()` with the correct cursor position
- Returns `True` to prevent Qt's default behavior from running
- **This is critical**: Without this, Qt's default spinbox behavior would take over and ignore cursor position

#### 2. Position-Aware Stepping
The `stepBy()` override calculates step size based on cursor position:
1. **Uses saved cursor position** (from eventFilter or position tracking)
2. **Strips prefix/suffix correctly**: Accounts for " mm", " °" suffixes and spaces
3. **Finds decimal point position** in the cleaned number text
4. **Calculates appropriate step size**:
   - Before decimal: `10^(distance_from_decimal)` (e.g., cursor at hundreds → step by 100)
   - After decimal: `10^(-distance_from_decimal-1)` (e.g., cursor at hundredths → step by 0.01)
5. **Applies the step** while respecting min/max bounds
6. **Restores cursor position** accounting for any text reformatting

#### Why Both Mechanisms?
- **Event filter**: Catches keyboard Up/Down in the text field (most common use case)
- **Position tracking**: Handles spinner button clicks and scroll wheel
- Together they provide comprehensive cursor-aware behavior for all input methods

## Benefits

1. **Improved Workflow**: Users can see changes immediately without constantly clicking OK
2. **Precise Adjustments**: Can increment specific decimal places by positioning cursor
3. **Natural Behavior**: Matches expectations from other professional software (CAD, graphics tools)
4. **Reduced Friction**: Eliminates the "change value → OK → not quite right → open again" cycle

## Cancel/Rollback Behavior

When the user clicks "Cancel" in the editor dialog:
- All live changes to x, y, and angle are **reverted** to their initial values
- The component returns to its original position and orientation
- Other parameters (that don't update live) are automatically discarded
- This provides the expected "preview then confirm/cancel" workflow

Example workflow:
1. User opens editor, component at (100, 100)
2. User adjusts x to 200 → component moves immediately to (200, 100)
3. User clicks Cancel → component returns to (100, 100)

## Backward Compatibility

- OK and Cancel buttons work as expected with proper rollback
- Cancel will revert any live changes made during the editing session
- All existing keyboard shortcuts and workflows remain functional
- No breaking changes to serialization or parameter storage
- The edited signal is emitted for both OK (final confirm) and Cancel (rollback) to ensure proper update

## Future Enhancements

Potential improvements for future iterations:
- Add smart increment to other numeric fields (EFL, lengths, etc.)
- Visual feedback showing which digit will be affected
- Keyboard shortcut to cycle through decimal places
- History/undo within the dialog itself

