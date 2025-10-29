# Interface Properties - Table Format

## Overview

The interface properties are now displayed in a clean, aligned table format instead of individual text boxes. This provides better visual organization and eliminates alignment issues.

## Visual Structure

```
┌────────────────────────────────────────┐
│  Interface 1                        ▼  │
├────────────────────────────────────────┤
│ ┌────────────┬─────────────────────┐  │
│ │ Parameter  │ Value               │  │
│ ├────────────┼─────────────────────┤  │
│ │ type       │ lens  🔍            │  │
│ │ X1         │ 10.0                │  │
│ │ X2         │ 10.0                │  │
│ │ Y1         │ 10.0                │  │
│ │ Y2         │ 20.0                │  │
│ │ focal leng │ 100.0               │  │
│ └────────────┴─────────────────────┘  │
└────────────────────────────────────────┘
```

## Key Features

### 1. Proper Table Structure
- Uses `QTableWidget` for native table display
- Two columns: "Parameter" and "Value"
- Grid lines visible for clear separation
- Consistent row heights
- No alternating colors (clean look)

### 2. Perfect Alignment
- All parameter names aligned in left column
- All values aligned in right column
- No misaligned text boxes
- Professional spreadsheet-like appearance

### 3. Inline Editing
- Coordinates (X1, X2, Y1, Y2) editable via frameless spinboxes
- Spinboxes appear seamlessly in table cells
- No visible borders on edit widgets
- 1 decimal place for clean numbers

### 4. Read-Only Cells
- Type row is read-only (displays "lens  🔍")
- Non-editable cells use `QTableWidgetItem`
- Proper flags set to prevent editing

### 5. Auto-Sizing
- Table height automatically adjusts to content
- No scrollbars within interface sections
- Compact display - only shows necessary rows
- Fixed height calculation based on row count

## Technical Implementation

### Table Configuration
```python
table.setColumnCount(2)
table.setHorizontalHeaderLabels(["Parameter", "Value"])
table.horizontalHeader().setStretchLastSection(True)
table.verticalHeader().setVisible(False)
table.setShowGrid(True)
table.setSelectionMode(NoSelection)
table.setFocusPolicy(NoFocus)
table.setColumnWidth(0, 100)  # Parameter column
```

### Row Types

**Read-only row (type):**
```python
item = QTableWidgetItem("lens  🔍")
item.setFlags(item.flags() & ~ItemIsEditable)
table.setItem(row, col, item)
```

**Editable spinbox (coordinates):**
```python
spin = QDoubleSpinBox()
spin.setRange(-10000, 10000)
spin.setDecimals(1)
spin.setButtonSymbols(NoButtons)
spin.setFrame(False)
table.setCellWidget(row, col, spin)
```

**Type-specific properties:**
- Numbers: Frameless spinboxes
- Booleans: Checkboxes
- Strings: ComboBoxes or LineEdits

### Height Calculation
```python
# Calculate exact height needed
total_height = sum(table.rowHeight(i) for i in range(rowCount))
header_height = table.horizontalHeader().height()
table.setFixedHeight(total_height + header_height + 5)
```

## Advantages

### Before (Loose Layout with Text Boxes)
❌ Misaligned text boxes  
❌ Uneven spacing  
❌ Boxes not in line  
❌ Hard to scan  
❌ Inconsistent appearance

### After (Clean Table Format)
✅ Perfect alignment  
✅ Consistent spacing  
✅ Grid structure  
✅ Easy to scan  
✅ Professional appearance

## Example Layouts

### Simple Interface (Lens)
| Parameter    | Value       |
|--------------|-------------|
| type         | lens  🔍    |
| X1           | -10.0       |
| X2           | 10.0        |
| Y1           | 0.0         |
| Y2           | 0.0         |
| focal length | 100.0       |
| n1           | 1.0         |
| n2           | 1.517       |

### Complex Interface (Beam Splitter)
| Parameter      | Value       |
|----------------|-------------|
| type           | beam split  |
| X1             | 0.0         |
| X2             | 0.0         |
| Y1             | -10.0       |
| Y2             | 10.0        |
| split_T        | 50.0        |
| split_R        | 50.0        |
| is_polarizing  | ☐           |
| n1             | 1.0         |
| n2             | 1.517       |

### Dichroic Filter
| Parameter           | Value       |
|---------------------|-------------|
| type                | dichroic 🌈 |
| X1                  | -5.0        |
| X2                  | 5.0         |
| Y1                  | 0.0         |
| Y2                  | 0.0         |
| cutoff_wavelength   | 550.0       |
| transition_width    | 50.0        |
| pass_type           | longpass ▼  |

## Synchronization

### Table → Canvas
1. User edits value in table cell (spinbox)
2. `valueChanged` signal emitted
3. `_on_coordinate_changed()` or `_on_property_changed()` called
4. Interface data updated
5. `propertyChanged` signal emitted
6. ComponentEditor syncs to canvas

### Canvas → Table
1. User drags point on canvas
2. Canvas emits `linesChanged`
3. ComponentEditor calculates new mm coordinates
4. Calls `interface_panel.update_interface()`
5. `PropertyListWidget.update_from_interface()` updates spinbox values
6. Table displays new coordinates

## Styling Notes

- **No borders on widgets**: Spinboxes and line edits have `setFrame(False)`
- **No spinbox buttons**: `setButtonSymbols(NoButtons)` for clean look
- **Grid visible**: Shows clear cell boundaries
- **Header visible**: "Parameter" and "Value" labels at top
- **Fixed first column**: 100px width for parameter names
- **Stretched second column**: Takes remaining space

## Testing Checklist

- [x] Table displays with proper alignment
- [x] Grid lines visible
- [x] Headers show "Parameter" and "Value"
- [x] Type row displays with icon
- [x] X1, X2, Y1, Y2 editable via spinboxes
- [x] Spinboxes have no visible borders
- [x] Spinboxes have no up/down buttons
- [x] 1 decimal place on all numbers
- [x] Type-specific properties appear correctly
- [x] Table height fits content exactly
- [x] No scrollbars within table
- [x] Edits propagate to canvas
- [x] Canvas drags update table values
- [x] No alignment issues

## Conclusion

The table format provides a clean, professional interface for editing properties. All values are perfectly aligned, easy to scan, and the grid structure makes it clear which parameter corresponds to which value. The frameless widgets integrate seamlessly into the table cells for a polished appearance.

