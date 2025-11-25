#!/usr/bin/env python3
"""
Setup script for creating macOS .app bundle for Optiverse.

This script creates an editable Optiverse.app bundle that uses symlinks,
so code changes are immediately reflected without rebuilding.

Features:
- Proper .icns icon (run scripts/create_icon.py first)
- Symlinks for editable development
- Works with conda or venv
- Shows as "Optiverse" in menu bar

Usage:
    python tools/setup_macos_app.py

Then launch with:
    open Optiverse.app
"""

import os
import sys
from pathlib import Path
import shutil
import subprocess


def get_conda_info():
    """Get conda base path and current environment."""
    try:
        # Get conda base
        result = subprocess.run(
            ["conda", "info", "--base"],
            capture_output=True,
            text=True,
            check=True
        )
        conda_base = result.stdout.strip()

        # Get current environment
        conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")

        return conda_base, conda_env
    except Exception:
        return None, None


def create_app_bundle(project_root: Path, editable: bool = True):
    """
    Create the macOS .app bundle structure.

    Args:
        project_root: Path to project root
        editable: If True, use symlinks for development mode
    """

    app_path = project_root / "Optiverse.app"
    contents_path = app_path / "Contents"
    macos_path = contents_path / "MacOS"
    resources_path = contents_path / "Resources"

    print(f"Creating {'editable' if editable else 'standalone'} app bundle at: {app_path}")

    # Create directories
    macos_path.mkdir(parents=True, exist_ok=True)
    resources_path.mkdir(parents=True, exist_ok=True)

    # Create Info.plist
    info_plist = contents_path / "Info.plist"
    plist_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>Optiverse</string>
    <key>CFBundleExecutable</key>
    <string>optiverse</string>
    <key>CFBundleIconFile</key>
    <string>optiverse</string>
    <key>CFBundleIdentifier</key>
    <string>app.optiverse</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Optiverse</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
'''

    info_plist.write_text(plist_content)
    print(f"✅ Created Info.plist")

    # Copy or create icon
    icon_icns = project_root / "resources" / "optiverse.icns"
    icon_png = project_root / "src" / "optiverse" / "ui" / "icons" / "optiverse.png"

    if icon_icns.exists():
        shutil.copy(icon_icns, resources_path / "optiverse.icns")
        print(f"✅ Copied .icns icon")
    elif icon_png.exists():
        # Try to create icns on the fly
        print(f"⚠️  .icns not found, attempting to create from PNG...")
        try:
            iconset_dir = resources_path / "optiverse.iconset"
            iconset_dir.mkdir(exist_ok=True)

            # Create a simple icon (just one size for now)
            sizes = [16, 32, 128, 256, 512]
            for size in sizes:
                output_file = iconset_dir / f"icon_{size}x{size}.png"
                subprocess.run([
                    'sips', '-z', str(size), str(size),
                    str(icon_png),
                    '--out', str(output_file)
                ], check=True, capture_output=True)

            # Convert to icns
            subprocess.run([
                'iconutil', '-c', 'icns',
                str(iconset_dir),
                '-o', str(resources_path / "optiverse.icns")
            ], check=True, capture_output=True)

            shutil.rmtree(iconset_dir)
            print(f"✅ Created .icns icon from PNG")
        except Exception as e:
            print(f"⚠️  Could not create icon: {e}")
            print(f"   Run: python scripts/create_icon.py")
    else:
        print(f"⚠️  No icon found. Run: python scripts/create_icon.py")

    # Create launcher script
    launcher = macos_path / "optiverse"
    conda_base, conda_env = get_conda_info()

    if conda_base and conda_env:
        # Using conda environment
        launcher_content = f'''#!/bin/bash
# Optiverse macOS launcher (conda environment: {conda_env})

# Get the project directory (3 levels up from this script)
APP_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
PROJECT_DIR="$(cd "$APP_DIR/.." && pwd)"

# Change to project directory
cd "$PROJECT_DIR"

# Source conda
source "{conda_base}/etc/profile.d/conda.sh"

# Activate environment
conda activate {conda_env}

# Launch application
exec python -m optiverse.app.main "$@"
'''
    else:
        # Using venv or system Python
        python_path = sys.executable
        site_packages = Path(python_path).parent.parent / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"

        launcher_content = f'''#!/bin/bash
# Optiverse macOS launcher (Python: {python_path})

# Get the project directory
APP_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
PROJECT_DIR="$(cd "$APP_DIR/.." && pwd)"

# Change to project directory
cd "$PROJECT_DIR"

# Launch with the Python that was used to create the bundle
exec "{python_path}" -m optiverse.app.main "$@"
'''

    launcher.write_text(launcher_content)
    launcher.chmod(0o755)
    print(f"✅ Created launcher script ({'conda' if conda_env else 'venv/system python'})")

    print(f"\n{'='*60}")
    print(f"✅ Optiverse.app bundle created successfully!")
    print(f"{'='*60}")
    print(f"\nMode: {'Editable (changes reflected immediately)' if editable else 'Standalone'}")
    print(f"\nTo launch Optiverse:")
    print(f"  open {app_path}")
    print(f"\nOr double-click Optiverse.app in Finder")
    print(f"\nThe app will show as 'Optiverse' in the menu bar.")

    if not icon_icns.exists():
        print(f"\n⚠️  For proper icon support, run: python scripts/create_icon.py")

    print()


def main():
    """Main entry point."""
    if sys.platform != "darwin":
        print("⚠️  This script is only needed on macOS.")
        print("On other platforms, run: python -m optiverse.app.main")
        print("Or use the entry point: optiverse")
        sys.exit(0)

    # Get project root (parent of tools/)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    print("Optiverse macOS App Bundle Setup")
    print("=" * 60)
    print()

    # Check if we're in editable mode
    editable = True  # Always use editable mode for development

    create_app_bundle(project_root, editable=editable)


if __name__ == "__main__":
    main()


