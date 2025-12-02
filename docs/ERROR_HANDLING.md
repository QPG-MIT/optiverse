---
layout: default
title: Error Handling
nav_order: 33
parent: Architecture & Development
---

# Global Error Handling System

## Overview

Optiverse now includes a comprehensive error handling system that prevents the application from crashing when errors occur. Instead of terminating, errors are caught, logged, and displayed in user-friendly error dialogs.

## Features

✅ **Global Exception Handler** - Catches all unhandled exceptions
✅ **Error Dialogs** - Shows user-friendly error messages with technical details
✅ **Logging Integration** - All errors are logged to the log service
✅ **Qt Message Handler** - Catches Qt warnings and errors
✅ **Context-Aware** - Error messages include context about what operation failed
✅ **Silent Mode** - Option to log errors without showing dialogs
✅ **Decorator Support** - Easy-to-use decorators for wrapping functions

## Architecture

### Components

1. **ErrorHandler** (`services/error_handler.py`)
   - Global singleton that manages error handling
   - Installs Python exception hook
   - Provides error dialog display
   - Integrates with log service

2. **ErrorContext** (context manager)
   - Wraps code blocks with error handling
   - Provides context information for errors
   - Optional dialog display

3. **@handle_errors** (decorator)
   - Wraps individual functions with error handling
   - Automatically catches and handles exceptions

### Installation

The error handler is automatically installed when the application starts in `app/main.py`:

```python
from ..services.error_handler import get_error_handler, install_qt_message_handler

# Install global error handler
error_handler = get_error_handler()

# Install Qt message handler
install_qt_message_handler()
```

## Usage

### Method 1: ErrorContext (Recommended)

Wrap code blocks that might fail:

```python
from optiverse.services.error_handler import ErrorContext

# With user-facing error dialog
with ErrorContext("while saving file"):
    save_to_disk(data)

# Silent mode (log only, no dialog)
with ErrorContext("during raytracing", show_dialog=False):
    trace_rays()
```

### Method 2: Decorator

Wrap entire functions:

```python
from optiverse.services.error_handler import handle_errors

@handle_errors
def load_assembly(self, path):
    with open(path) as f:
        data = json.load(f)
    return data
```

### Method 3: Manual Handling

For custom error handling:

```python
from optiverse.services.error_handler import get_error_handler

try:
    risky_operation()
except Exception as e:
    handler = get_error_handler()
    handler.handle_error(e, "while performing operation")
```

## What's Protected

The following critical areas are now wrapped with error handling:

### Main Window (`ui/views/main_window.py`)
- ✅ `save_assembly()` - File saving operations
- ✅ `save_assembly_as()` - Save As dialog
- ✅ `open_assembly()` - File loading operations
- ✅ `_do_retrace()` - Raytracing trigger
- ✅ `_retrace_legacy()` - Legacy raytracing engine
- ✅ `_retrace_polymorphic()` - New polymorphic raytracing engine

### Component Editor (`ui/views/component_editor_dialog.py`)
- ✅ `save_component()` - Component save operations
- ✅ `export_component()` - Component export
- ✅ `import_component()` - Component import (already had try/except)

### Graphics View (`objects/views/graphics_view.py`)
- ✅ `dropEvent()` - Drag-and-drop operations

### Application Startup (`app/main.py`)
- ✅ Main window creation
- ✅ OpenGL initialization

## Error Dialog Format

When an error occurs, users see a dialog with:

**Title:** Descriptive error title (e.g., "Error while saving assembly")

**Message:** User-friendly description of what went wrong

**Details:** (Expandable) Full Python traceback for debugging

Example:
```
┌─────────────────────────────────────┐
│ Error while saving assembly         │
├─────────────────────────────────────┤
│ An error occurred while saving      │
│ assembly:                            │
│                                      │
│ [Errno 13] Permission denied:       │
│ '/path/to/file.json'                │
│                                      │
│ [Show Details ▼]                    │
│                                      │
│              [ OK ]                  │
└─────────────────────────────────────┘
```

## Logging Integration

All errors are automatically logged with:
- **Category:** "Error Handler"
- **Level:** ERROR
- **Message:** Error description with context
- **Details:** Full traceback (DEBUG level)

View logs via **Help → Show Logs** in the application.

## Silent Mode

For non-critical errors (like raytracing failures), use silent mode to log without dialogs:

```python
with ErrorContext("during auto-retrace", show_dialog=False):
    self.retrace()
```

This prevents dialog spam during rapid operations while still logging issues.

## Qt Message Handler

The system also captures Qt-internal warnings and errors:

```python
install_qt_message_handler()
```

Qt messages are logged with category "Qt" at appropriate levels:
- QtDebugMsg → DEBUG
- QtInfoMsg → INFO  
- QtWarningMsg → WARNING
- QtCriticalMsg → ERROR
- QtFatalMsg → ERROR (also printed to stderr)

## Best Practices

### DO ✅
- Wrap all file I/O operations
- Wrap all network operations
- Wrap all complex computations
- Use silent mode for rapid/automatic operations
- Provide clear context strings
- Log errors even if you handle them

### DON'T ❌
- Show error dialogs during rapid auto-operations (use silent mode)
- Catch and ignore errors without logging
- Use generic context strings like "error"
- Suppress critical errors

## Testing

Test the error handling system:

```bash
python test_error_handling.py
```

This will verify:
- Error handler is installed
- ErrorContext works correctly
- Silent mode works
- Dialogs are displayed properly

## Future Enhancements

Potential improvements:
- [ ] Error reporting/telemetry (opt-in)
- [ ] Automatic crash reports
- [ ] Error recovery suggestions
- [ ] Known error database
- [ ] Performance monitoring

## Technical Details

### Exception Hook

The global exception hook is installed via:

```python
sys.excepthook = self._handle_exception
```

This catches ALL unhandled exceptions before they terminate the application.

### Thread Safety

The current implementation is designed for the main Qt thread. For background threads, use explicit error handling:

```python
try:
    # Background work
    result = compute_something()
except Exception as e:
    # Post error to main thread
    QtCore.QMetaObject.invokeMethod(
        main_window,
        lambda: get_error_handler().handle_error(e, "in background thread"),
        QtCore.Qt.ConnectionType.QueuedConnection
    )
```

### Performance Impact

Minimal - error handling only activates when exceptions occur. The try/except overhead is negligible (<1µs per context manager).

## Related Files

- `src/optiverse/services/error_handler.py` - Error handler implementation
- `src/optiverse/services/log_service.py` - Logging service
- `src/optiverse/app/main.py` - Installation point
- `test_error_handling.py` - Test script

## See Also

- [LOGGING_SYSTEM.md](LOGGING_SYSTEM.md) - Logging service documentation
- [DEBUG_COLLABORATION.md](DEBUG_COLLABORATION.md) - Debugging guide
