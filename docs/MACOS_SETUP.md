# macOS Installation Guide

This guide explains how to set up Optiverse on macOS so it appears correctly in the menu bar.

## Quick Setup

After cloning the repository:

```bash
# 1. Create conda environment (recommended)
conda create -n optiverse python=3.11
conda activate optiverse

# 2. Install dependencies
pip install -e .
pip install pyobjc-framework-Cocoa

# 3. Create the macOS app bundle
python tools/setup_macos_app.py

# 4. Launch Optiverse
open Optiverse.app
```

## Why the App Bundle?

On macOS, Python scripts show up as "Python" or "Python 3.x" in the menu bar. To have the app show as **"Optiverse"** in the menu bar, we need to create a proper macOS application bundle (.app).

The `tools/setup_macos_app.py` script automatically creates this bundle structure:

```
Optiverse.app/
├── Contents/
    ├── Info.plist          # Defines app name, bundle ID, etc.
    ├── MacOS/
    │   └── optiverse       # Launcher script
    └── Resources/
        └── optiverse.png   # App icon
```

## How It Works

### Info.plist
The `Info.plist` file tells macOS about the application:
- `CFBundleName`: "Optiverse" (what appears in the menu bar)
- `CFBundleExecutable`: Points to the launcher script
- `CFBundleIdentifier`: Unique app identifier

### Launcher Script
The launcher script (`Contents/MacOS/optiverse`):
1. Finds the project directory
2. Activates the conda environment (if using conda)
3. Runs `python -m optiverse.app.main`

### Preferences Menu
With `pyobjc-framework-Cocoa` installed, the code in `src/optiverse/app/main.py` and `src/optiverse/ui/views/main_window.py` sets:
- Process name to "Optiverse" (via `NSProcessInfo`)
- Preferences menu role (automatically moves to app menu on macOS)

## Fresh Clone Setup

When someone else clones the repo:

```bash
git clone https://github.com/QPG-MIT/optiverse.git
cd optiverse

# Setup conda environment
conda create -n optiverse python=3.11
conda activate optiverse
pip install -e .
pip install pyobjc-framework-Cocoa

# Create app bundle
python tools/setup_macos_app.py

# Launch
open Optiverse.app
```

The `Optiverse.app` directory is in `.gitignore`, so it won't be committed to git. Each user generates it on their machine with the correct paths.

## Alternative: Command Line Launch

If you don't want to use the app bundle, you can still launch from the terminal:

```bash
conda activate optiverse
python -m optiverse.app.main
```

However, this will show as "Python" in the menu bar.

## Troubleshooting

**App doesn't launch:**
- Make sure conda environment is activated when running `setup_macos_app.py`
- Check that the launcher script is executable: `chmod +x Optiverse.app/Contents/MacOS/optiverse`

**Still shows "Python" in menu bar:**
- Make sure you're launching with `open Optiverse.app` (not `python -m optiverse.app.main`)
- Verify `pyobjc-framework-Cocoa` is installed
- Quit and relaunch the app

**Preferences not in app menu:**
- Install `pyobjc-framework-Cocoa`
- The preferences will be under "Optiverse → Preferences..." in the menu bar
