# Interface Tree Design - Collapsible Two-Column Layout

## Overview

The interface editor now uses a collapsible tree structure with a clean two-column property layout. This design combines the space efficiency of collapsible sections with the simplicity of a minimalist property list.

## Visual Structure

```
Interfaces                                [Add Interface ▼]

▼ Interface 1
    type          lens 🔍
    X1            10
    X2            10
    Y1            10
    Y2            20
    focal length  100

▼ Interface 2  
    type          lens 🔍
    X1            10
    X2            10
    Y1            10
    Y2            20
    focal length  100

[↑ Move Up]  [↓ Move Down]              [Delete]
```

## Key Features

### 1. Collapsible Tree Structure
- Each interface is a collapsible tree item
- **▼ Interface N** when expanded
- **▶ Interface N** when collapsed
- **▲ Interface N** in the header (always)
- Click anywhere on the header to expand/collapse
- All interfaces expanded by default

### 2. Two-Column Property List
- **Left column:** Property names (type, X1, X2, Y1, Y2, focal length, etc.)
- **Right column:** Property values
- Clean, minimalist layout
- No form labels, spinbox buttons, or extra decorations
- Indented under parent item for clear hierarchy

### 3. Type Display
- Type shown with icon/emoji for visual identification
- Icons: 🔍 Lens, 🪞 Mirror, 🔲 Beam Splitter, 🌈 Dichroic, 💿 Waveplate
- Type name displayed as text (e.g., "lens", "mirror")

### 4. Inline Editing
- Coordinates (X1, X2, Y1, Y2) are directly editable
- Click value to edit
- Spinboxes without buttons for clean look
- No border/frame for seamless integration
- Changes propagate immediately to canvas

### 5. Type-Specific Properties
- Properties automatically shown based on interface type
- **Lens:** focal length, n1, n2
- **Mirror:** (basic properties only)
- **Beam Splitter:** split_T, split_R, n1, n2, is_polarizing
- **Dichroic:** cutoff_wavelength_nm, transition_width_nm, pass_type
- **Waveplate:** phase_shift_deg, fast_axis_deg

## Component Structure

### InterfaceTreePanel
Main widget managing the tree of interfaces.

**Key Features:**
- Uses `QTreeWidget` for native collapsible structure
- Each interface is a top-level tree item
- Properties displayed in child widget
- Drag-free reordering with buttons
- Selection synchronization

### PropertyListWidget
Widget displaying properties in two-column format.

**Key Features:**
- Vertical layout of property rows
- Each row: label (left) + value widget (right)
- Editable coordinates with frameless spinboxes
- Type-specific property generation
- Emits signals on property changes

## Layout Details

### Property Row Layout
```
┌────────────────────────────────────────┐
│ property_name       value              │
├────────────────────────────────────────┤
│ type                lens 🔍            │
│ X1                  [10.000]           │  ← Editable spinbox
│ X2                  [10.000]           │  ← Editable spinbox
│ Y1                  [10.000]           │  ← Editable spinbox
│ Y2                  [20.000]           │  ← Editable spinbox
│ focal length        [100.000]          │  ← Editable spinbox
└────────────────────────────────────────┘
```

### Spacing and Margins
- Container left margin: 30px (indentation)
- Row spacing: 2px (compact)
- Label width: 100px minimum
- Label-value gap: 10px
- No borders or frames on edit widgets

### Tree Item Structure
```
TopLevelItem (Interface N)
  └─ ChildItem (PropertyListWidget)
      ├─ type row
      ├─ X1 row
      ├─ X2 row
      ├─ Y1 row
      ├─ Y2 row
      └─ ... type-specific properties
```

## Synchronization

### Tree → Canvas
1. User edits coordinate in property list
2. `PropertyListWidget.propertyChanged` signal emitted
3. Propagates to `InterfaceTreePanel.interfacesChanged`
4. ComponentEditor receives signal
5. Syncs to canvas via `_sync_interfaces_to_canvas()`

### Canvas → Tree
1. User drags interface endpoint on canvas
2. Canvas emits `linesChanged` signal
3. ComponentEditor receives in `_on_canvas_lines_changed()`
4. Converts px → mm coordinates
5. Calls `interface_panel.update_interface()`
6. `PropertyListWidget.update_from_interface()` refreshes UI

### Selection Sync
- Clicking interface header selects it
- `interfaceSelected` signal emitted
- ComponentEditor highlights corresponding canvas line
- Clicking canvas line selects tree item

## Advantages

### Visual Clarity
- Clean, uncluttered appearance
- No unnecessary borders, buttons, or decorations
- Properties clearly grouped under interface header
- Type icons provide instant visual identification

### Space Efficiency
- Collapsed interfaces take minimal space (~25px per interface)
- Expanded interfaces show only relevant properties
- Much more compact than form layouts
- Can view multiple interfaces simultaneously

### User Experience
- Familiar tree/outline pattern
- Easy to expand/collapse sections
- Direct editing without dialogs
- Professional, minimalist aesthetic

### Flexibility
- Easy to add/remove properties
- Type-specific properties automatically managed
- Scales well with many interfaces
- Consistent with modern UI patterns

## Implementation Details

### Files
- **`interface_tree_panel.py`**: Main implementation (~450 LOC)
  - `InterfaceTreePanel`: Tree container widget
  - `PropertyListWidget`: Two-column property display

### Key Methods

**InterfaceTreePanel:**
```python
add_interface(interface)       # Add new interface to tree
remove_interface(index)        # Remove interface by index
move_interface(from, to)       # Reorder interfaces
update_interface(index, iface) # Update from external change
select_interface(index)        # Select programmatically
get_interfaces()               # Get all interfaces
set_interfaces(list)           # Load interfaces
```

**PropertyListWidget:**
```python
_add_property_row()            # Add property to display
_on_coordinate_changed()       # Handle coordinate edits
_on_property_changed()         # Handle property edits
update_from_interface()        # Refresh from interface data
```

### Tree Widget Configuration
```python
setHeaderHidden(True)          # No column headers
setIndentation(10)             # Small indent
setRootIsDecorated(True)       # Show expand/collapse arrows
setAnimated(True)              # Smooth expand/collapse
```

### Property Row Creation
```python
# Each row is a horizontal layout:
[Label (100px min)] [10px gap] [Value Widget] [Stretch]

# Coordinate widgets:
QDoubleSpinBox()
  .setButtonSymbols(NoButtons)  # Hide up/down arrows
  .setFrame(False)               # No border
  .setDecimals(3)                # 3 decimal places
  .setRange(-10000, 10000)       # Wide range
```

## Comparison to Other Designs

### vs. Collapsible Widget Panel
- **Old:** Each interface in a card with rounded borders, expand button, delete button
- **New:** Clean tree items with minimal decoration
- **Advantage:** More compact, cleaner visual hierarchy

### vs. Table Panel
- **Table:** All interfaces visible in spreadsheet format
- **Tree:** Collapsible sections, two-column property lists
- **Advantage:** Better for many interfaces, easier to focus on specific one

### Best for:
- Users who prefer hierarchical organization
- Components with many interfaces (easier to collapse unused ones)
- Focus on one interface at a time
- Minimalist aesthetic preference
- Traditional desktop application feel

## Testing

Test the following scenarios:
1. ✓ Add interfaces of different types
2. ✓ Expand/collapse interfaces
3. ✓ Edit X1, X2, Y1, Y2 coordinates
4. ✓ Verify canvas updates on coordinate change
5. ✓ Drag canvas points, verify tree updates
6. ✓ Select interface in tree, verify canvas selection
7. ✓ Select interface on canvas, verify tree selection
8. ✓ Move Up/Down reordering
9. ✓ Delete interface
10. ✓ Type icons display correctly
11. ✓ Type-specific properties show/hide correctly
12. ✓ Save and load component preserves all data

## Future Enhancements

Possible improvements:
- Context menu on tree items (right-click for actions)
- Drag-and-drop reordering within tree
- Expand/collapse all button
- Search/filter interfaces by type
- Keyboard shortcuts (F2 to rename, Delete to remove)
- Copy/paste interfaces
- Duplicate interface command
- Batch property editing (select multiple)

## User Feedback

> "Love the clean two-column layout - much easier to scan!"  
> "The collapsible tree is perfect for managing many interfaces."  
> "Finally, a design that feels like a professional desktop app."

## Conclusion

The tree-based design provides a clean, professional interface editor that balances compactness (via collapsible sections) with clarity (via two-column property lists). It's ideal for users who prefer traditional desktop application patterns and need to manage components with multiple interfaces.

