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
- Overrides `stepBy()` to detect cursor position and adjust step size accordingly
- Examples of behavior:
  - Value: `123.456`, cursor at position 2 (`12|3.456`) → Up arrow → `133.456` (increments tens place)
  - Value: `123.456`, cursor at position 5 (`123.4|56`) → Up arrow → `123.556` (increments hundredths place)
  - Value: `123.456`, cursor at position 0 (`|123.456`) → Up arrow → `223.456` (increments hundreds place)

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

The `stepBy()` override in `SmartDoubleSpinBox`:
1. Gets current cursor position in the line edit
2. Strips prefix/suffix to get clean number text
3. Finds decimal point position
4. Calculates appropriate step size based on cursor position relative to decimal point
5. Applies the step while respecting min/max bounds
6. Preserves cursor position after update

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

