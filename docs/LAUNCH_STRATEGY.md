# Cross-Platform Launch Strategy

## Overview

We need a clean solution that works across platforms and keeps the code editable during development.

## Current Issues

1. ❌ **macOS**: Shows "Python" in menu bar without app bundle
2. ❌ **App Bundle**: Not editable (points to specific Python path)
3. ❌ **Icon**: Not showing in app bundle
4. ❌ **Windows**: No clean launch mechanism
5. ❌ **Inconsistency**: Different launch methods per platform

## Proposed Solution

### Strategy: Entry Point Scripts + Platform-Specific Launchers

```
optiverse/
├── pyproject.toml           # Defines `optiverse` entry point
├── setup.py                 # Optional, for editable installs
├── scripts/
│   ├── build_macos_app.py   # Build Optiverse.app (development/release)
│   └── create_icon.py       # Convert PNG to .icns for macOS
└── Optiverse.app/           # Generated (gitignored)
```

### Platform Workflows

#### **macOS (Development)**
```bash
# Install in editable mode
pip install -e .

# Build app bundle (one-time or after updates)
python scripts/build_macos_app.py

# Launch
open Optiverse.app
```

**How it works:**
- App bundle contains symlinks to Python and project
- Changes to source code are immediately reflected
- Icon properly embedded as `.icns` file

#### **macOS (Distribution)**
```bash
# Create standalone app with py2app
python setup.py py2app
```

#### **Windows**
```bash
# Install in editable mode
pip install -e .

# Launch via entry point
optiverse

# Or create shortcut to:
pythonw -m optiverse.app.main
```

#### **Linux**
```bash
# Install in editable mode
pip install -e .

# Launch via entry point
optiverse

# Or create .desktop file
```

## Implementation Plan

### 1. Update pyproject.toml
- ✅ Already has entry point: `optiverse = "optiverse.app.main:main"`
- Add py2app configuration for release builds

### 2. Create Icon in Correct Format
- macOS needs `.icns` (multiple resolutions)
- Windows needs `.ico`
- Convert `optiverse.png` to both formats

### 3. Smart App Bundle Builder
- Detect if using conda or venv
- Create symlinks for editable mode
- Embed icon correctly
- Add to macOS Dock if desired

### 4. Entry Point Optimization
- Make `optiverse` command work everywhere
- Add `--version`, `--help` flags
- Platform detection for best UX

## File Structure

```
Optiverse.app/
├── Contents/
    ├── Info.plist              # App metadata
    ├── MacOS/
    │   └── optiverse           # Launcher (symlink to wrapper script)
    ├── Resources/
    │   ├── optiverse.icns      # macOS icon (proper format)
    │   └── Python.framework/   # Symlink to Python (editable mode)
    └── PythonApp/              # Symlink to src/ (editable mode)
```

## Advantages

✅ **Editable**: Changes to source immediately reflected  
✅ **Clean**: Single command to launch (`open Optiverse.app` or `optiverse`)  
✅ **Cross-platform**: Works on macOS, Windows, Linux  
✅ **Icon**: Proper icon in Dock/Taskbar  
✅ **Professional**: App shows as "Optiverse" not "Python"  
✅ **Developer-friendly**: No rebuild after code changes (dev mode)  
✅ **Distribution-ready**: Can create standalone app (py2app/pyinstaller)

## Icon Requirements

### macOS (.icns)
Required resolutions:
- 16x16, 32x32, 64x64, 128x128, 256x256, 512x512, 1024x1024
- Both standard and @2x retina versions

### Windows (.ico)
Required resolutions:
- 16x16, 32x32, 48x48, 256x256

### Linux
- Use PNG directly in .desktop file
- Typically 512x512 or larger

## Next Steps

1. Create `scripts/create_icon.py` - Convert PNG to .icns/.ico
2. Update `scripts/build_macos_app.py` - Smart app builder with symlinks
3. Add Windows launcher script
4. Add Linux .desktop file generator
5. Update README with unified instructions
