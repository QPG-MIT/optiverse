# Save and Save As Implementation Summary

## Overview
Replaced the single "Save Assembly…" menu item with proper "Save" and "Save As…" actions following standard application behavior.

## Changes Made

### 1. Actions Created (lines 303-311)
- **Save Action**: Label "Save", shortcut Ctrl+S
- **Save As Action**: Label "Save As…", shortcut Ctrl+Shift+S

### 2. Menu Bar Updated (lines 545-546)
Both actions added to the File menu:
- File → Open Assembly…
- File → Save (Ctrl+S)
- File → Save As… (Ctrl+Shift+S)

### 3. Shortcuts Registered (lines 619-621)
Both Save actions registered globally in `_register_shortcuts()` to ensure keyboard shortcuts work even when child widgets have focus.

### 4. Methods Refactored (lines 1253-1304)

#### `save_assembly()` - Quick Save
- Checks if `_saved_file_path` exists
- If yes: saves directly using `_save_to_file(path)`
- If no: calls `save_assembly_as()` to prompt for location

#### `save_assembly_as()` - Save As Dialog
- Always shows file dialog for new location
- Saves to selected path using `_save_to_file(path)`
- Updates `_saved_file_path` with new location

#### `_save_to_file(path)` - Helper Method
- Contains the actual save logic
- Serializes all scene items to JSON
- Updates `_saved_file_path` and marks canvas as clean
- Shows error dialog if save fails

## Integration Points

### Prompt Save Changes
The `_prompt_save_changes()` method (line 287) calls `save_assembly()`:
- For files previously saved: saves directly without prompting
- For new files: shows save dialog
- If user cancels dialog: correctly returns Cancel to abort the operation

### Open Assembly
The `open_assembly()` method tracks the file path and marks as clean after loading, enabling direct saves.

## Behavior

### New File Workflow
1. User creates content
2. Presses Ctrl+S or File → Save
3. Save dialog appears (first time only)
4. File is saved and path is remembered
5. Future Ctrl+S saves directly without dialog

### Existing File Workflow
1. User opens an existing file
2. Makes changes
3. Presses Ctrl+S
4. File is saved directly without dialog

### Save As Workflow
1. User presses Ctrl+Shift+S or File → Save As…
2. Save dialog always appears
3. User selects new location
4. File is saved to new location
5. New path becomes the current file

## Keyboard Shortcuts
- **Ctrl+S**: Quick save (prompts only if new file)
- **Ctrl+Shift+S**: Save as (always prompts for location)

## Files Modified
- `src/optiverse/ui/views/main_window.py`: All implementation

