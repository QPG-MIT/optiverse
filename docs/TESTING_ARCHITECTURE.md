---
layout: default
title: Testing Architecture
---

# Testing Architecture Analysis

## Overview

Optiverse uses **pytest** with **pytest-qt** for UI testing. The test suite covers:
- **Core logic** (physics, geometry, raytracing)
- **UI components** (windows, dialogs, widgets)
- **Integration** (save/load, undo/redo, copy/paste)
- **Services** (storage, settings, collaboration)

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures (qapp, qtbot, scene, view, mocks)
├── fixtures/
│   ├── factories.py         # Factory functions for creating test objects
│   └── mocks.py             # Mock services (storage, settings, collaboration)
├── core/                    # Physics and core logic tests
├── objects/                 # Qt graphics items tests
├── ui/                      # UI integration tests
├── raytracing/              # Raytracing engine tests
└── services/                # Service tests
```

## UI Testing Framework

### Key Components

1. **QApplication Fixture** (`conftest.py`)
   - Session-scoped QApplication instance
   - Required for all Qt tests
   - Automatically created before tests

2. **QtBot** (`pytest-qt`)
   - Simulates user interactions (clicks, keyboard, mouse)
   - Waits for signals and events
   - Handles Qt event loop

3. **Scene/View Fixtures**
   - `scene`: QGraphicsScene with proper size
   - `view`: GraphicsView attached to scene
   - Automatic cleanup after tests

4. **Mock Services**
   - `MockStorageService`: In-memory storage (no file I/O)
   - `MockSettingsService`: In-memory settings
   - `MockCollaborationManager`: No network calls
   - `MockLogService`: Captures log messages

### How UI Tests Work

#### 1. Widget Creation
```python
def test_example(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)  # Registers widget for cleanup
    window.show()
    qtbot.waitExposed(window)  # Wait for window to be visible
```

#### 2. Simulating User Interactions

**Mouse Clicks:**
```python
# Click a button
qtbot.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)

# Click at coordinates
qtbot.mouseClick(view, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(100, 100))
```

**Keyboard Events:**
```python
# Simulate Ctrl+C
qtbot.keyClick(window, QtCore.Qt.Key.Key_C, QtCore.Qt.KeyboardModifier.ControlModifier)

# Type text
qtbot.keyClicks(line_edit, "Hello World")
```

**Waiting for Signals:**
```python
# Wait for signal with timeout
with qtbot.waitSignal(widget.signal_name, timeout=1000):
    widget.do_action()
```

#### 3. Asserting UI State

**Check Widget Properties:**
```python
assert button.isEnabled()
assert line_edit.text() == "expected"
assert checkbox.isChecked()
```

**Check Scene Items:**
```python
items = scene.items()
sources = [item for item in items if isinstance(item, SourceItem)]
assert len(sources) == 1
```

**Check Component Properties:**
```python
source = sources[0]
assert abs(source.params.x_mm - 100.0) < 0.01
assert source.params.n_rays == 5
```

## Current Test Coverage

### ✅ Well-Tested Areas

1. **Save/Load** (`test_save_load_assembly.py`)
   - All component types saved/loaded correctly
   - Parameter preservation
   - Backward compatibility

2. **Copy/Paste** (`test_copy_paste.py`)
   - Single and multiple items
   - Property preservation
   - Keyboard shortcuts (Ctrl+C, Ctrl+V)
   - Undo/redo integration

3. **Component Editor** (`test_component_editor.py`)
   - Saving to library
   - Field visibility based on component type
   - Signal emission

4. **Undo/Redo** (`test_undo_redo_integration.py`)
   - Adding components
   - Moving components
   - Deleting components
   - Keyboard shortcuts

### ⚠️ Areas That May Need More Testing

1. **Visual Rendering**
   - Ray rendering correctness
   - Component visual appearance
   - Selection highlighting
   - Ghost preview during drag

2. **Mouse Interactions**
   - Drag and drop from library
   - Component dragging on canvas
   - Resizing components
   - Multi-select with Shift+Click

3. **Complex UI Flows**
   - Component editor workflow (image loading, interface editing)
   - Measurement tools (path, angle)
   - Library context menus
   - Dialog interactions

4. **Edge Cases**
   - Empty scene operations
   - Invalid input handling
   - Error dialogs
   - Large assemblies (performance)

## Recommendations for Ensuring Tests Test the Right Things

### 1. Test User-Facing Behavior, Not Implementation

**❌ Bad:**
```python
def test_internal_state():
    assert window._some_internal_flag == True
```

**✅ Good:**
```python
def test_user_can_save_assembly(qtbot, main_window, tmp_path):
    # Add component
    source = SourceItem(SourceParams())
    main_window.scene.addItem(source)
    
    # User saves
    with mock.patch.object(QFileDialog, "getSaveFileName", return_value=(str(tmp_path / "test.json"), "")):
        main_window.save_assembly()
    
    # Verify user can load it back
    main_window.scene.clear()
    with mock.patch.object(QFileDialog, "getOpenFileName", return_value=(str(tmp_path / "test.json"), "")):
        main_window.open_assembly()
    
    assert len([item for item in main_window.scene.items() if isinstance(item, SourceItem)]) == 1
```

### 2. Test Complete User Workflows

**Example: Component Creation Workflow**
```python
def test_component_creation_workflow(qtbot, main_window, tmp_path):
    """Test complete workflow: open editor -> create component -> use in scene"""
    # 1. Open component editor
    editor = main_window.open_component_editor()
    qtbot.addWidget(editor)
    
    # 2. Set component properties
    editor.name_edit.setText("TestLens")
    editor.kind_combo.setCurrentText("lens")
    editor.height_mm.setValue(50.0)
    
    # 3. Load image
    img = QImage(100, 100, QImage.Format.Format_ARGB32)
    editor.canvas.set_pixmap(QPixmap.fromImage(img))
    
    # 4. Save component
    with mock.patch.object(..., return_value=(str(tmp_path / "lib.json"), "")):
        editor.save_component()
    
    # 5. Use component in main window
    # Drag from library to scene
    # ... verify component appears correctly
```

### 3. Use Visual Regression Testing (Optional)

For critical UI components, consider visual regression testing:

```python
def test_component_rendering(qtbot, scene):
    """Test that component renders correctly"""
    lens = create_lens_item()
    scene.addItem(lens)
    
    # Render to image
    view = GraphicsView(scene)
    qtbot.addWidget(view)
    pixmap = view.grab()
    
    # Compare with reference image
    expected = QPixmap("tests/fixtures/expected_lens.png")
    assert pixmap.toImage() == expected.toImage()
```

### 4. Test Error Handling

```python
def test_error_handling_invalid_file(qtbot, main_window):
    """Test that invalid file shows error dialog"""
    # Try to load invalid JSON
    with mock.patch.object(QFileDialog, "getOpenFileName", return_value=("invalid.json", "")):
        with qtbot.waitSignal(main_window.error_occurred, timeout=1000):
            main_window.open_assembly()
    
    # Verify error was logged
    assert mock_log_service.assert_message_logged("Error loading", level="error")
```

### 5. Test Keyboard Shortcuts

```python
def test_all_keyboard_shortcuts(qtbot, main_window):
    """Test that all documented shortcuts work"""
    # Test Ctrl+S (save)
    qtbot.keyClick(main_window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    # ... verify save dialog appears
    
    # Test Ctrl+Z (undo)
    qtbot.keyClick(main_window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    # ... verify undo happens
```

### 6. Test State Transitions

```python
def test_editor_mode_transitions(qtbot, main_window):
    """Test switching between editor modes"""
    # Start in default mode
    assert main_window.editor_state.mode == EditorMode.DEFAULT
    
    # Enter inspect mode
    main_window.act_inspect.trigger()
    assert main_window.editor_state.mode == EditorMode.INSPECT
    
    # Enter placement mode
    main_window.act_add_lens.trigger()
    assert main_window.editor_state.mode == EditorMode.PLACEMENT
    
    # Cancel (Esc)
    qtbot.keyClick(main_window, Qt.Key.Key_Escape)
    assert main_window.editor_state.mode == EditorMode.DEFAULT
```

### 7. Use Test Data Builders

Create complex test scenarios easily:

```python
def test_complex_optical_system(qtbot, main_window):
    """Test raytracing through complex system"""
    # Build complex setup
    setup = OpticalSetupBuilder() \
        .add_source(x=-200, angle=0) \
        .add_lens(x=-100, efl=50) \
        .add_mirror(x=0, angle=45) \
        .add_beamsplitter(x=100) \
        .build()
    
    for item in setup.items:
        main_window.scene.addItem(item)
    
    # Trace rays
    main_window.retrace()
    
    # Verify ray paths
    assert len(main_window.ray_paths) > 0
    # ... verify ray interactions
```

## Testing Checklist for New Features

When adding a new UI feature, ensure you test:

- [ ] **User can discover the feature** (menu item, button, shortcut exists)
- [ ] **Feature works with mouse interaction** (clicks, drags)
- [ ] **Feature works with keyboard shortcuts** (if applicable)
- [ ] **Feature integrates with undo/redo**
- [ ] **Feature saves/loads correctly** (if applicable)
- [ ] **Feature handles errors gracefully**
- [ ] **Feature updates UI state correctly**
- [ ] **Feature works with existing features** (no conflicts)

## Common Testing Patterns

### Pattern 1: Mock File Dialogs
```python
with mock.patch.object(
    QtWidgets.QFileDialog, 
    "getSaveFileName", 
    return_value=(str(tmp_path / "test.json"), "")
):
    main_window.save_assembly()
```

### Pattern 2: Wait for Async Operations
```python
with qtbot.waitSignal(widget.operation_complete, timeout=5000):
    widget.start_long_operation()
```

### Pattern 3: Test Signal Emission
```python
with qtbot.waitSignal(editor.saved, timeout=1000):
    editor.save_component()
```

### Pattern 4: Verify Scene State
```python
items = scene.items()
sources = [item for item in items if isinstance(item, SourceItem)]
assert len(sources) == expected_count
```

## Debugging Failed UI Tests

1. **Add Screenshots:**
```python
def test_with_screenshot(qtbot, main_window):
    main_window.show()
    qtbot.waitExposed(main_window)
    
    # Take screenshot on failure
    pixmap = main_window.grab()
    pixmap.save("test_failure.png")
    
    # ... rest of test
```

2. **Add Delays for Debugging:**
```python
qtbot.wait(1000)  # Wait 1 second to see what's happening
```

3. **Print Widget Tree:**
```python
def print_widget_tree(widget, indent=0):
    print(" " * indent + widget.__class__.__name__)
    for child in widget.findChildren(QWidget):
        print_widget_tree(child, indent + 2)
```

## Running Tests

```bash
# All tests
pytest

# UI tests only
pytest tests/ui/

# Specific test file
pytest tests/ui/test_main_window.py

# With coverage
pytest --cov=src/optiverse --cov-report=html

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

## CI Integration

Tests run automatically on:
- Push to main/develop/feature branches
- Pull requests
- All platforms (Linux, macOS, Windows)

See `.github/workflows/ci.yml` for CI configuration.

## Next Steps

1. **Add visual regression tests** for critical components
2. **Increase coverage** of mouse interaction tests
3. **Add performance tests** for large assemblies
4. **Test accessibility** features (keyboard navigation, screen readers)
5. **Add integration tests** for complete user workflows

