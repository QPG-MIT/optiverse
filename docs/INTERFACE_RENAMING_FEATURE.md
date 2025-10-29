# Interface Renaming Feature

## Overview

Interfaces in the Component Editor can now be renamed with a simple double-click. This allows users to give meaningful names to interfaces instead of the default "Interface 1", "Interface 2", etc.

## How to Use

### Renaming an Interface

1. Open the Component Editor
2. Locate the interface you want to rename in the Interfaces panel
3. **Double-click** on the interface name (e.g., "Interface 1")
4. The name becomes editable
5. Type the new name (e.g., "Front Surface", "Beam Splitter Coating", "Exit Face")
6. Press **Enter** to confirm, or **Escape** to cancel

### Where Names Appear

Custom interface names are displayed in:
- **Interface Tree Panel**: Header of each collapsible interface section
- **Canvas Labels**: When interface is selected (if labels are enabled)
- **Component Properties**: Saved with the component definition

### Name Persistence

- Interface names are **saved with the component**
- Names are **preserved** when saving/loading components
- Names are **migrated** from old component formats
- Empty names automatically revert to "Interface N" format

## Examples

### Use Case: Beam Splitter Cube

Default names:
```
Interface 1
Interface 2  
Interface 3
Interface 4
Interface 5
```

Renamed for clarity:
```
Left Edge (Entry)
Bottom Edge
BS Coating (Diagonal)
Right Edge (Transmitted)
Top Edge (Reflected)
```

### Use Case: Lens System

Default names:
```
Interface 1
```

Renamed:
```
f=100mm Achromat
```

### Use Case: Complex Refractive Object

Default names:
```
Interface 1
Interface 2
Interface 3
Interface 4
```

Renamed:
```
AR Coating (Front)
Glass-Air (Back)
Prism Entry
Prism Exit
```

## Technical Details

### Implementation

**File Modified**: `src/optiverse/ui/widgets/interface_tree_panel.py`

**Key Changes**:
1. Added `ItemIsEditable` flag to tree items
2. Connected `itemChanged` signal to `_on_item_renamed` handler
3. Updated display name logic to show custom name if set
4. Interface name updates trigger `interfacesChanged` signal

**Storage**: Names are stored in `InterfaceDefinition.name` field (string)

### Code Snippet

```python
def _on_item_renamed(self, item: QtWidgets.QTreeWidgetItem, column: int):
    """Handle item name changes (user edited the text)."""
    # Only handle top-level items (interface headers)
    if item.parent() is not None:
        return
    
    # Get the index and update interface name
    index = self._tree.indexOfTopLevelItem(item)
    if 0 <= index < len(self._interfaces):
        new_name = item.text(0).strip()
        self._interfaces[index].name = new_name
        self.interfacesChanged.emit()
```

### Display Logic

```python
# Use custom name if set, otherwise default to "Interface N"
display_name = interface.name if interface.name else f"Interface {index + 1}"
item.setText(0, display_name)
```

## Benefits

### Organization
- Quickly identify specific interfaces in complex components
- No more counting "which interface is #3 again?"

### Documentation  
- Self-documenting component structure
- Names explain purpose/function of each interface

### Collaboration
- Easier communication about specific interfaces
- "Adjust the BS Coating" vs "Adjust Interface 3"

### Workflow
- No extra dialogs or menus needed
- Standard double-click-to-rename interaction
- Instant visual feedback

## Tips

### Good Naming Practices

**Descriptive**:
- ✅ "Front AR Coating"
- ❌ "Interface A"

**Concise**:
- ✅ "Entry Face"  
- ❌ "The front entry face where the beam enters the component"

**Consistent**:
- ✅ "L1 Front", "L1 Back", "L2 Front", "L2 Back"
- ❌ "First Lens Entry", "1st lens exit", "Second Surface"

**Functional**:
- ✅ "PBS Coating (45°)"
- ✅ "Dichroic (550nm)"
- ✅ "Mirror (R=99%)"

### When to Rename

**Always rename** for:
- Multi-surface components (lenses, cubes, prisms)
- Beam splitter coatings vs. refractive surfaces
- Components you'll share with others
- Components with >3 interfaces

**Optional** for:
- Simple single-interface components
- Quick prototypes
- Personal use components

## Keyboard Shortcuts

- **F2**: Start editing selected interface name (alternative to double-click)
- **Enter**: Confirm name change
- **Escape**: Cancel editing, revert to original name
- **Tab**: Confirm and move to next interface (if implemented)

## Future Enhancements

Potential improvements:
1. **Batch Rename**: Rename multiple interfaces at once
2. **Name Templates**: Common naming schemes (Surface 1, Surface 2, etc.)
3. **Auto-naming**: Suggest names based on interface type
4. **Search/Filter**: Find interfaces by name
5. **Name Validation**: Prevent duplicate or invalid names
6. **Undo/Redo**: Undo name changes

## Related Features

- **Interface Selection**: Click interface in tree to highlight on canvas
- **Interface Reordering**: Use Move Up/Down buttons
- **Interface Properties**: Expand to edit optical properties
- **Interface Colors**: Visual coding by interface type

---

**Status**: ✅ Implemented and Ready to Use  
**Version**: Component Editor v2.0+

