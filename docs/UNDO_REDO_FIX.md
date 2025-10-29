# Undo/Redo Fix - Multiple Item Deletion Bug

## Problem Description

Users reported that when deleting multiple objects together, the undo operation would cause objects to "disappear in the wrong order." Specifically:

1. User selects 3 objects (A, B, C)
2. User presses Delete
3. All 3 objects disappear (as expected)
4. User presses Undo (Ctrl+Z)
5. **BUG**: Only 1 object (C) reappears
6. User has to press Undo 2 more times to restore all objects

**Expected behavior**: All 3 objects should reappear with a single Undo operation, since they were deleted together in a single Delete operation.

## Root Cause

The bug was in the `delete_selected()` method in `main_window.py`. When multiple items were selected and deleted:

```python
# OLD (BUGGY) CODE
def delete_selected(self):
    selected = self.scene.selectedItems()
    for item in selected:
        if isinstance(item, (BaseObj, RulerItem, TextNoteItem)):
            cmd = RemoveItemCommand(self.scene, item)
            self.undo_stack.push(cmd)  # ❌ Pushes SEPARATE command for each item
```

This created **one `RemoveItemCommand` per item**, resulting in:
- Deleting 3 items = 3 separate commands on the undo stack
- First undo only undoes the last command (restores 1 item)
- User needs 3 undos to restore all 3 items

## Solution

Created a new `RemoveMultipleItemsCommand` class that batches multiple deletions into a single undoable operation:

```python
class RemoveMultipleItemsCommand(Command):
    """Command to remove multiple items from the scene in a single operation."""
    
    def __init__(self, scene, items):
        self.scene = scene
        self.items = items
        self._executed = False
    
    def execute(self):
        """Remove all items from the scene."""
        if not self._executed:
            for item in self.items:
                self.scene.removeItem(item)
            self._executed = True
    
    def undo(self):
        """Add all items back to the scene."""
        if self._executed:
            for item in self.items:
                self.scene.addItem(item)
            self._executed = False
```

Updated `delete_selected()` to batch deletions:

```python
# NEW (FIXED) CODE
def delete_selected(self):
    selected = self.scene.selectedItems()
    items_to_delete = []
    
    for item in selected:
        if isinstance(item, (BaseObj, RulerItem, TextNoteItem)):
            items_to_delete.append(item)
            self.collaboration_manager.broadcast_remove_item(item)
    
    # ✅ Use a single command for all deletions
    if items_to_delete:
        if len(items_to_delete) == 1:
            cmd = RemoveItemCommand(self.scene, items_to_delete[0])
        else:
            cmd = RemoveMultipleItemsCommand(self.scene, items_to_delete)
        self.undo_stack.push(cmd)
```

## Changes Made

### 1. New Command Class
**File**: `src/optiverse/core/undo_commands.py`
- Added `RemoveMultipleItemsCommand` class
- Handles removal and restoration of multiple items as a single operation

### 2. Updated Delete Logic
**File**: `src/optiverse/ui/views/main_window.py`
- Modified `delete_selected()` to collect all items to delete
- Uses `RemoveMultipleItemsCommand` when deleting 2+ items
- Uses `RemoveItemCommand` for single item (backwards compatibility)
- Updated imports to include new command

### 3. Comprehensive Tests
**File**: `tests/core/test_undo_multiple_deletions.py`
- Test multiple item deletion with single undo
- Test item state preservation after undo
- Test edge cases (empty list, single item)
- Test comparison between old and new behavior

## Testing

Run the new test suite:
```bash
python -m pytest tests/core/test_undo_multiple_deletions.py -v
```

### Manual Testing
1. Launch the application
2. Add 3-4 optical components to the canvas
3. Select all of them (Ctrl+A or click-drag selection)
4. Press Delete
5. Press Ctrl+Z (Undo)
6. **Expected**: All objects reappear together
7. Press Ctrl+Shift+Z (Redo)
8. **Expected**: All objects disappear together

## Backward Compatibility

- Single item deletions continue to use `RemoveItemCommand`
- Existing saved undo/redo state is not affected
- No changes to the undo stack interface
- Collaboration sync still broadcasts individual item removals

## Benefits

1. **User Experience**: Undo/redo now works intuitively for batch operations
2. **Undo Stack Efficiency**: Fewer commands on the stack for multiple selections
3. **Consistency**: Matches user expectations (one action = one undo)
4. **Extensibility**: Pattern can be applied to other batch operations (e.g., property changes)

## Future Considerations

This pattern could be extended to:
- Batch property changes (e.g., changing color of multiple selected items)
- Batch moves (moving multiple items together)
- Batch rotations
- Copy/paste operations (already uses `PasteItemsCommand`)

## Related Files

- `src/optiverse/core/undo_commands.py` - Command implementations
- `src/optiverse/core/undo_stack.py` - Undo stack manager
- `src/optiverse/ui/views/main_window.py` - Main window with delete logic
- `tests/core/test_undo_stack.py` - Undo stack tests
- `tests/core/test_undo_commands.py` - Command tests
- `tests/core/test_undo_multiple_deletions.py` - New test for this fix

