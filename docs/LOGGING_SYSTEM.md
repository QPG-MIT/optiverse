---
layout: default
title: Logging System
nav_order: 34
parent: Architecture & Development
---

# Logging System Documentation

## Overview
The application now has a centralized logging system that replaces console print statements with a proper log window that can be accessed via the menu bar.

## Features

### Log Service (`log_service.py`)
- **Centralized Logging**: All debug messages go through a single service
- **Timestamped**: Every message includes millisecond-precision timestamp
- **Categorized**: Messages are organized by category (e.g., "Copy/Paste", "Raytracing", "File I/O")
- **Severity Levels**: DEBUG, INFO, WARNING, ERROR
- **Memory Buffer**: Keeps last 1000 messages in memory
- **Listener Pattern**: Real-time updates to log window

### Log Window (`log_window.py`)
- **Accessible via Menu**: Tools → Show Log Window (or Ctrl+L)
- **Filtering**: Filter by severity level, category, or search text
- **Color Coding**: 
  - ERROR: Red
  - WARNING: Orange
  - INFO: Blue
  - DEBUG: Gray
- **Auto-scroll**: Optional auto-scroll to latest messages
- **Export**: Save log to text file
- **Clear**: Clear all messages

## Usage

### Accessing the Log Window
1. Open the application
2. Go to **Tools** → **Show Log Window**
3. Or press **Ctrl+L**

### Using the Log Service in Code

```python
# Get the log service
from ...services.log_service import get_log_service
log_service = get_log_service()

# Log messages
log_service.debug("Detailed debug information", "Category")
log_service.info("General information", "Category")
log_service.warning("Something unexpected", "Category")
log_service.error("An error occurred", "Category")
```

### Example Categories
- **"Copy/Paste"** - Copy/paste operations
- **"Raytracing"** - Ray tracing calculations
- **"File I/O"** - File open/save operations
- **"Collaboration"** - Collaboration network events
- **"General"** - Default category

## Copy/Paste Logging

The copy/paste functionality now logs:
- ✅ **Successful operations**: `"Copied 3 item(s) to clipboard"`
- ✅ **Paste details**: Item types being pasted
- ❌ **Errors**: Full stack traces when serialization/deserialization fails
- ⚠️ **Warnings**: Unknown item types, empty clipboard

### Example Log Messages

```
[14:23:15.432] INFO    | Copy/Paste   | Copied 2 item(s) to clipboard
[14:23:16.891] DEBUG   | Copy/Paste   | Pasting 2 item(s) from clipboard
[14:23:16.895] INFO    | Copy/Paste   | Successfully pasted 2 item(s)
```

If an error occurs:
```
[14:25:32.123] ERROR   | Copy/Paste   | Error pasting LensItem: TypeError: ...
[Full stack trace]
```

## UUID Behavior

✅ **Confirmed**: Copied elements receive **new UUIDs**
- Original `item_uuid` is excluded from paste data
- New items generate fresh UUIDs via `BaseObj.__init__()`
- Pasted items are independent copies, not references

## Benefits

### Before (Console Prints)
❌ Messages disappear when terminal scrolls
❌ No timestamps
❌ No filtering or search
❌ Can't save or export
❌ Mixed with other output

### After (Log Window)
✅ Persistent in-memory buffer
✅ Millisecond-precision timestamps
✅ Filter by level, category, or search
✅ Export to file
✅ Color-coded by severity
✅ Clean, organized interface

## Implementation Details

### Architecture
```
┌─────────────────┐
│   MainWindow    │
│  (logs events)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  LogService     │─────▶│  LogWindow   │
│  (singleton)    │      │  (listener)  │
└─────────────────┘      └──────────────┘
```

1. **LogService**: Singleton that stores messages and notifies listeners
2. **LogWindow**: Qt dialog that displays and filters messages
3. **MainWindow**: Uses log_service for all debug output

### Thread Safety
The log service is designed for future async operations but currently runs synchronously.

## File Locations

- **Service**: `src/optiverse/services/log_service.py`
- **Window**: `src/optiverse/ui/views/log_window.py`
- **Usage**: `src/optiverse/ui/views/main_window.py` (copy_selected, paste_items)

## Future Enhancements

Potential improvements:
- Log level configuration per category
- Persistent log file on disk
- Performance metrics (timing)
- Network activity logging
- Collaboration events logging
- Automatic error reporting

## Quick Reference

| Action | Method | Shortcut |
|--------|--------|----------|
| Open log window | Tools → Show Log Window | Ctrl+L |
| Filter by level | Use Level dropdown | - |
| Filter by category | Use Category dropdown | - |
| Search messages | Type in Search box | - |
| Clear log | Click "Clear Log" button | - |
| Export log | Click "Export..." button | - |
| Auto-scroll | Toggle "Auto-scroll" checkbox | - |

## Testing

After implementation, you should see log messages for:
1. Copy operations (Ctrl+C)
2. Paste operations (Ctrl+V)
3. Any errors during copy/paste
4. Warnings for unknown item types

Open the log window (Ctrl+L) and perform copy/paste operations to see the logging in action!

