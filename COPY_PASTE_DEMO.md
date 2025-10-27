# Copy/Paste Feature Implementation

## Overview

I've successfully added copy and paste functionality to the Optiverse application. Users can now copy and paste objects on the board using **Ctrl+C** and **Ctrl+V** keyboard shortcuts.

## Changes Made

### 1. **New Command: `PasteItemsCommand`** (`src/optiverse/core/undo_commands.py`)
   - Added a new undo command to support pasting multiple items at once
   - Integrates with the existing undo/redo system
   - Supports both execute and undo operations

### 2. **Main Window Updates** (`src/optiverse/ui/views/main_window.py`)
   - Added `_clipboard` list to store copied object data
   - Created `act_copy` action with Ctrl+C shortcut
   - Created `act_paste` action with Ctrl+V shortcut
   - Added both actions to the Edit menu
   - Implemented `copy_selected()` method to serialize selected objects
   - Implemented `paste_items()` method to deserialize and create new objects

### 3. **Test Suite** (`tests/ui/test_copy_paste.py`)
   - Comprehensive test coverage for copy/paste functionality
   - Tests for single and multiple item operations
   - Tests for undo/redo integration
   - Tests for property preservation
   - Tests for keyboard shortcuts

## How It Works

### Copying Objects
1. Select one or more objects on the canvas (sources, lenses, mirrors, beamsplitters, rulers, or text notes)
2. Press **Ctrl+C** or use **Edit > Copy** from the menu
3. The objects are serialized to an internal clipboard

### Pasting Objects
1. After copying objects, press **Ctrl+V** or use **Edit > Paste** from the menu
2. New objects are created with a 20mm offset (both X and Y) from the original positions
3. The pasted objects are automatically selected
4. The operation is added to the undo stack

### Supported Object Types
- ✅ Source Items (optical sources)
- ✅ Lens Items
- ✅ Mirror Items
- ✅ Beamsplitter Items
- ✅ Ruler Items (annotations)
- ✅ Text Note Items (annotations)

### Properties Preserved
When copying and pasting, all properties are preserved:
- For optical elements: position (offset), angle, optical properties (EFL, split ratios, etc.), images, calibration data
- For sources: ray count, spread angle, color, polarization settings
- For rulers: length and endpoints (offset)
- For text notes: content and formatting

### Undo/Redo Support
- Paste operations are fully integrated with the undo/redo system
- Press Ctrl+Z to undo a paste operation
- Press Ctrl+Y to redo a paste operation
- All pasted items are removed/restored as a group

## Usage Examples

### Example 1: Duplicate a Single Mirror
1. Click on a mirror to select it
2. Press Ctrl+C
3. Press Ctrl+V
4. The new mirror appears 20mm away from the original
5. Move it to the desired position

### Example 2: Copy Multiple Components
1. Click and drag to select multiple components (or Ctrl+Click to select individually)
2. Press Ctrl+C
3. Press Ctrl+V multiple times to create multiple copies
4. Each paste creates a new set of components with a 20mm offset

### Example 3: Copy a Complex Setup
1. Select a source, lens, and mirror that form a working optical setup
2. Press Ctrl+C
3. Press Ctrl+V
4. Adjust the pasted components to create a parallel optical path

## Implementation Details

### Data Serialization
- Objects are serialized using their existing `to_dict()` method
- An `_item_type` field is added to identify the object type during reconstruction
- All object parameters are preserved in the dictionary format

### Object Reconstruction
- During paste, objects are reconstructed from their parameter dictionaries
- The appropriate constructor (SourceParams, LensParams, etc.) is called
- Position offsets are applied before creating the object
- Sprites are reattached for optical components
- Signal connections are restored (`edited` signal for ray tracing)

### UI Feedback
- The Paste action is disabled when the clipboard is empty
- The Paste action is enabled after a successful copy operation
- Pasted objects are automatically selected for easy manipulation

## Code Quality
- ✅ No linter errors
- ✅ Follows existing code patterns and style
- ✅ Integrates seamlessly with existing undo/redo system
- ✅ Comprehensive test coverage
- ✅ Proper error handling (gracefully skips items that can't be serialized)

## Future Enhancements (Optional)
- Cross-session clipboard using system clipboard or JSON
- Copy/paste with keyboard position offset (e.g., paste at mouse position)
- Visual feedback during copy operation
- Copy/paste entire assemblies with preserved relationships

