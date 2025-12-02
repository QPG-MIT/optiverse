"""
Demo: Import Zemax ZMX file and convert to OptiVerse component.

This demonstrates how to:
1. Parse a Zemax ZMX file
2. Convert surfaces to InterfaceDefinition objects
3. Create a multi-element ComponentRecord
4. Visualize the component in the component editor

Usage:
    python examples/zemax_import_demo.py /path/to/file.zmx
"""

import os
import sys

# Add src to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(project_root, "src"))

try:
    from optiverse.services.glass_catalog import GlassCatalog
    from optiverse.services.zemax_converter import ZemaxToInterfaceConverter
    from optiverse.services.zemax_parser import ZemaxParser
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you run this from the project root.")
    sys.exit(1)


def print_separator(char="=", length=70):
    """Print a separator line."""
    print(char * length)


def demo_zemax_import(zmx_filepath: str):
    """
    Demonstrate Zemax file import process.

    Args:
        zmx_filepath: Path to .zmx file
    """
    print_separator()
    print("ZEMAX IMPORT DEMONSTRATION")
    print_separator()
    print()

    # Step 1: Parse Zemax file
    print("STEP 1: Parsing Zemax file...")
    print(f"File: {zmx_filepath}")
    print()

    parser = ZemaxParser()
    zemax_data = parser.parse(zmx_filepath)

    if not zemax_data:
        print("ERROR: Failed to parse Zemax file")
        return

    print("✓ Successfully parsed Zemax file")
    print()
    print(parser.format_summary(zemax_data))
    print()

    # Step 2: Show glass catalog capabilities
    print_separator("-")
    print("STEP 2: Glass Catalog Lookup")
    print_separator("-")
    print()

    catalog = GlassCatalog()
    print(f"Available glasses: {len(catalog.list_glasses())}")
    print()

    # Show refractive indices for materials in this lens
    unique_materials = set()
    for surf in zemax_data.surfaces:
        if surf.glass:
            unique_materials.add(surf.glass)

    print("Materials used in this lens:")
    wavelength_um = zemax_data.primary_wavelength_um
    for material in sorted(unique_materials):
        n = catalog.get_refractive_index(material, wavelength_um)
        if n:
            print(f"  {material:20s} @ {wavelength_um * 1000:.1f}nm: n = {n:.5f}")
        else:
            print(f"  {material:20s} @ {wavelength_um * 1000:.1f}nm: NOT FOUND")
    print()

    # Step 3: Convert to InterfaceDefinition objects
    print_separator("-")
    print("STEP 3: Converting to OptiVerse Interfaces")
    print_separator("-")
    print()

    converter = ZemaxToInterfaceConverter(catalog)
    component = converter.convert(zemax_data)

    print(f"Component Name: {component.name}")
    print(f"Component Type: {component.kind}")
    print(f"Object Height: {component.object_height_mm:.2f} mm")
    print(f"Number of Interfaces: {len(component.interfaces_v2) if component.interfaces_v2 else 0}")
    print()

    # Step 4: Show detailed interface information
    print_separator("-")
    print("STEP 4: Interface Details")
    print_separator("-")
    print()

    if component.interfaces_v2:
        for i, iface in enumerate(component.interfaces_v2):
            print(f"Interface {i + 1}:")
            print(f"  Name:     {iface.name}")
            print(f"  Type:     {iface.element_type}")
            print(f"  Position: x={iface.x1_mm:.3f} mm, y=±{abs(iface.y1_mm):.3f} mm")
            print(f"  Height:   {iface.length_mm():.3f} mm")
            print(f"  Indices:  n₁={iface.n1:.5f} → n₂={iface.n2:.5f}")
            print(f"  Δn:       {abs(iface.n2 - iface.n1):.5f}")
            print()

    # Step 5: Show how this would be used in OptiVerse
    print_separator("-")
    print("STEP 5: Usage in OptiVerse")
    print_separator("-")
    print()

    print("This component can now be used in OptiVerse:")
    print()
    print("1. SAVE TO LIBRARY:")
    print("   from optiverse.services.storage_service import StorageService")
    print("   storage = StorageService()")
    print("   storage.save_component(component)")
    print()
    print("2. LOAD IN COMPONENT EDITOR:")
    print("   editor = ComponentEditor(storage)")
    print("   editor.load_component(component)")
    print("   # Visual editor with all interfaces shown")
    print()
    print("3. USE IN RAY TRACING:")
    print("   # Drag component from library to canvas")
    print("   # Rays will automatically refract through all interfaces")
    print("   # Snell's law applied at each n₁→n₂ boundary")
    print()

    # Step 6: Show component JSON representation
    print_separator("-")
    print("STEP 6: JSON Representation (Excerpt)")
    print_separator("-")
    print()

    import json

    from optiverse.core.models import serialize_component

    component_dict = serialize_component(component)

    # Show excerpt of JSON (first interface only)
    excerpt = {
        "name": component_dict["name"],
        "format_version": component_dict["format_version"],
        "kind": component_dict["kind"],
        "object_height_mm": component_dict["object_height_mm"],
        "num_interfaces": len(component_dict.get("interfaces_v2", [])),
        "first_interface": (
            component_dict.get("interfaces_v2", [{}])[0]
            if component_dict.get("interfaces_v2")
            else {}
        ),
    }

    print(json.dumps(excerpt, indent=2))
    print()

    print_separator()
    print("IMPORT COMPLETE ✓")
    print_separator()
    print()
    print("Next steps:")
    print("  1. Open OptiVerse Component Editor")
    print("  2. Click 'Import Zemax…' in toolbar")
    print("  3. Select this ZMX file")
    print("  4. Interfaces will auto-populate")
    print("  5. Optionally add component image")
    print("  6. Save to library")
    print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python zemax_import_demo.py <path_to_zmx_file>")
        print()
        print("Example:")
        print("  python examples/zemax_import_demo.py ~/Downloads/AC254-100-B-Zemax.zmx")
        sys.exit(1)

    zmx_filepath = sys.argv[1]

    if not os.path.exists(zmx_filepath):
        print(f"ERROR: File not found: {zmx_filepath}")
        sys.exit(1)

    demo_zemax_import(zmx_filepath)


if __name__ == "__main__":
    main()
