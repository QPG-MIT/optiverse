#!/usr/bin/env python3
"""
Create platform-specific application icons from PNG source.

This script converts the source PNG to:
- .icns for macOS (multiple resolutions)
- .ico for Windows (multiple resolutions)

Requirements:
    pip install Pillow

macOS only (for .icns):
    brew install libicns  # or use sips (built-in)

Usage:
    python scripts/create_icon.py
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image


def create_icns_macos(png_path: Path, output_path: Path):
    """
    Create .icns file for macOS using sips (built-in on macOS).

    Args:
        png_path: Path to source PNG (should be at least 1024x1024)
        output_path: Path for output .icns file
    """
    if sys.platform != "darwin":
        print("⚠️  .icns creation only supported on macOS")
        return False

    try:
        # Create iconset directory
        iconset_dir = output_path.parent / f"{output_path.stem}.iconset"
        iconset_dir.mkdir(exist_ok=True)

        # Required sizes for macOS
        sizes = [16, 32, 64, 128, 256, 512, 1024]

        print(f"Creating icon set in {iconset_dir}")

        for size in sizes:
            # Standard resolution
            output_file = iconset_dir / f"icon_{size}x{size}.png"
            subprocess.run(
                ["sips", "-z", str(size), str(size), str(png_path), "--out", str(output_file)],
                check=True,
                capture_output=True,
            )

            # Retina resolution (@2x) - except for 1024
            if size < 1024:
                output_file_2x = iconset_dir / f"icon_{size}x{size}@2x.png"
                subprocess.run(
                    [
                        "sips",
                        "-z",
                        str(size * 2),
                        str(size * 2),
                        str(png_path),
                        "--out",
                        str(output_file_2x),
                    ],
                    check=True,
                    capture_output=True,
                )

        # Convert iconset to icns
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_path)], check=True
        )

        # Clean up iconset directory
        import shutil

        shutil.rmtree(iconset_dir)

        print(f"✅ Created {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create .icns: {e}")
        return False


def create_ico_windows(png_path: Path, output_path: Path):
    """
    Create .ico file for Windows using Pillow.

    Args:
        png_path: Path to source PNG
        output_path: Path for output .ico file
    """
    try:
        img = Image.open(png_path)

        # Windows icon sizes
        sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]

        # Create resized versions
        icons = []
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            icons.append(resized)

        # Save as .ico with all sizes
        icons[0].save(output_path, format="ICO", sizes=sizes, append_images=icons[1:])

        print(f"✅ Created {output_path}")
        return True

    except Exception as e:
        print(f"❌ Failed to create .ico: {e}")
        return False


def main():
    """Main entry point."""
    # Find project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    # Source PNG
    source_png = project_root / "src" / "optiverse" / "ui" / "icons" / "optiverse.png"

    if not source_png.exists():
        print(f"❌ Source icon not found: {source_png}")
        return 1

    # Check size
    img = Image.open(source_png)
    print(f"Source icon: {source_png} ({img.width}x{img.height})")

    if img.width < 1024 or img.height < 1024:
        print("⚠️  Warning: Source PNG should be at least 1024x1024 for best quality")

    # Output paths
    resources_dir = project_root / "resources"
    resources_dir.mkdir(exist_ok=True)

    icns_path = resources_dir / "optiverse.icns"
    ico_path = resources_dir / "optiverse.ico"

    print("\nCreating platform-specific icons...")
    print("=" * 60)

    # Create macOS icon
    if sys.platform == "darwin":
        create_icns_macos(source_png, icns_path)
    else:
        print("ℹ️  Skipping .icns (macOS only)")

    # Create Windows icon
    create_ico_windows(source_png, ico_path)

    print("=" * 60)
    print("✅ Icon creation complete!")
    print(f"\nIcons saved to: {resources_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
