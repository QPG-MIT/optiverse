#!/usr/bin/env python3
"""
Generate dark mode (inverted) versions of toolbar icons.

This script creates inverted versions of all toolbar icons for dark mode.
The inverted icons are saved to the icons/dark/ subfolder.
"""

from pathlib import Path

from PIL import Image, ImageOps


def invert_icon(input_path: Path, output_path: Path) -> None:
    """Invert RGB values of an icon while preserving alpha channel."""
    # Open image with alpha
    img = Image.open(input_path).convert("RGBA")
    r, g, b, a = img.split()
    
    # Invert RGB channels using PIL (preserves alpha)
    rgb = Image.merge("RGB", (r, g, b))
    rgb_inverted = ImageOps.invert(rgb)
    
    # Recombine with original alpha
    r_inv, g_inv, b_inv = rgb_inverted.split()
    inverted = Image.merge("RGBA", (r_inv, g_inv, b_inv, a))
    
    inverted.save(output_path)
    print(f"  Created: {output_path.name}")


def main():
    # Paths
    icons_dir = Path(__file__).parent.parent / "src" / "optiverse" / "ui" / "icons"
    light_dir = icons_dir / "light"
    dark_dir = icons_dir / "dark"
    
    # Toolbar icons to invert
    toolbar_icons = [
        "angle_measure.png",
        "beamsplitter.png",
        "inspect.png",
        "lens.png",
        "mirror.png",
        "ruler.png",
        "source.png",
        "text.png",
    ]
    
    # Create dark folder
    dark_dir.mkdir(exist_ok=True)
    print(f"Creating dark icons in: {dark_dir}")
    print(f"Reading light icons from: {light_dir}")
    
    # Generate inverted icons from light theme
    for icon_name in toolbar_icons:
        input_path = light_dir / icon_name
        output_path = dark_dir / icon_name
        
        if input_path.exists():
            invert_icon(input_path, output_path)
        else:
            print(f"  Warning: {icon_name} not found in light/, skipping")
    
    print("\nDone! Dark mode icons created.")


if __name__ == "__main__":
    main()

