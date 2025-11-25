"""
Simple Zemax parser demonstration - no heavy dependencies.

This script demonstrates parsing a Zemax file and showing how it
maps to the OptiVerse interface concept.

Usage:
    python examples/zemax_parse_simple.py /path/to/file.zmx
"""

import sys
import os

# Simple inline parser (no imports)
def parse_zemax_simple(filepath):
    """Simple Zemax ZMX parser."""
    surfaces = []
    name = ""
    wavelengths = []
    primary_wl_idx = 1

    with open(filepath, 'r') as f:
        lines = f.readlines()

    current_surface = None
    surf_num = None

    for line in lines:
        line_stripped = line.strip()

        if line_stripped.startswith('NAME '):
            name = line_stripped[5:].strip()

        elif line_stripped.startswith('WAVM '):
            parts = line_stripped[5:].split()
            if len(parts) >= 2:
                wavelengths.append(float(parts[1]))

        elif line_stripped.startswith('PWAV '):
            primary_wl_idx = int(line_stripped[5:].strip())

        elif line_stripped.startswith('SURF '):
            if current_surface:
                surfaces.append(current_surface)
            surf_num = int(line_stripped[5:].strip())
            current_surface = {
                'number': surf_num,
                'curvature': 0.0,
                'thickness': 0.0,
                'glass': '',
                'diameter': 0.0,
                'coating': '',
                'comment': ''
            }

        elif current_surface and line.startswith('  '):  # Check indentation before stripping
            if line_stripped.startswith('CURV '):
                try:
                    current_surface['curvature'] = float(line_stripped[5:].split()[0])
                except:
                    pass
            elif line_stripped.startswith('DISZ '):
                val = line_stripped[5:].split()[0]
                if val.upper() != 'INFINITY':
                    try:
                        current_surface['thickness'] = float(val)
                    except:
                        pass
            elif line_stripped.startswith('GLAS '):
                try:
                    current_surface['glass'] = line_stripped[5:].split()[0]
                except:
                    pass
            elif line_stripped.startswith('DIAM '):
                try:
                    current_surface['diameter'] = float(line_stripped[5:].split()[0])
                except:
                    pass
            elif line_stripped.startswith('COAT '):
                try:
                    current_surface['coating'] = line_stripped[5:].split()[0]
                except:
                    pass
            elif line_stripped.startswith('COMM '):
                current_surface['comment'] = line_stripped[5:].strip()

    if current_surface:
        surfaces.append(current_surface)

    primary_wl_um = wavelengths[primary_wl_idx - 1] if wavelengths else 0.55

    return {
        'name': name,
        'surfaces': surfaces,
        'primary_wavelength_um': primary_wl_um
    }


# Minimal glass catalog
GLASS_INDICES = {
    'N-BK7': 1.517,
    'N-LAK22': 1.651,
    'N-SF6HT': 1.805,
    'N-SF11': 1.785,
    'N-F2': 1.620,
}


def get_index(material):
    """Get refractive index."""
    if not material or material.upper() in ['', 'AIR', 'VACUUM']:
        return 1.0
    return GLASS_INDICES.get(material.upper(), 1.5)


def main():
    if len(sys.argv) < 2:
        print("Usage: python zemax_parse_simple.py <path_to_zmx_file>")
        return

    filepath = sys.argv[1]

    print("="*70)
    print("ZEMAX FILE PARSER - Simple Demonstration")
    print("="*70)
    print()

    # Parse
    data = parse_zemax_simple(filepath)

    print(f"Name: {data['name']}")
    print(f"Primary wavelength: {data['primary_wavelength_um'] * 1000:.1f} nm")
    print(f"Number of surfaces: {len(data['surfaces'])}")
    print()

    print("-"*70)
    print("SURFACES:")
    print("-"*70)

    cumulative_x = 0.0
    current_material = ""

    for surf in data['surfaces']:
        num = surf['number']
        curv = surf['curvature']
        thick = surf['thickness']
        glass = surf['glass']
        diam = surf['diameter']

        radius = 1.0 / curv if abs(curv) > 1e-10 else float('inf')
        radius_str = f"{radius:.2f}" if radius != float('inf') else "∞"

        print(f"\nSurface {num}:")
        if num == 0:
            print(f"  Type: Object surface (at infinity)")
        else:
            print(f"  Radius: {radius_str} mm")
            print(f"  Thickness to next: {thick:.2f} mm")
            print(f"  Material: {glass if glass else 'Air'}")
            print(f"  Diameter: {diam:.2f} mm")

            # Show as interface
            if num > 0 and num < len(data['surfaces']) - 1:
                n1 = get_index(current_material)
                n2 = get_index(glass)
                mat1 = current_material if current_material else "Air"
                mat2 = glass if glass else "Air"

                # Calculate sag for curved surfaces
                is_curved = radius != float('inf')
                sag = 0.0
                if is_curved and diam > 0:
                    R_abs = abs(radius)
                    h = diam / 2.0
                    if h**2 < R_abs**2:
                        sag = R_abs - (R_abs**2 - h**2)**0.5
                        if radius < 0:
                            sag = -sag

                print(f"\n  → OptiVerse Interface:")
                print(f"     Position: x={cumulative_x:.2f} mm (vertex)")
                print(f"     Height: {diam:.2f} mm (±{diam/2:.2f} mm from axis)")
                print(f"     Indices: n₁={n1:.3f} ({mat1}) → n₂={n2:.3f} ({mat2})")
                if is_curved:
                    print(f"     Curvature: R={radius_str} mm")
                    print(f"     Sag (edge): {abs(sag):.3f} mm {'(convex)' if radius > 0 else '(concave)'}")
                    print(f"     Type: curved refractive_interface")
                else:
                    print(f"     Type: flat refractive_interface")

                cumulative_x += thick
                current_material = glass

    print()
    print("="*70)
    print("MAPPING TO OPTIVERSE")
    print("="*70)
    print()

    print("This Zemax file defines a multi-element lens system that maps to")
    print("OptiVerse's interface-based component model as follows:")
    print()

    # Count real interfaces (exclude object and image)
    real_surfaces = [s for s in data['surfaces'] if 0 < s['number'] < len(data['surfaces']) - 1]

    print(f"ComponentRecord(")
    print(f"  name=\"{data['name']}\",")
    print(f"  kind=\"multi_element\",")
    print(f"  object_height_mm={real_surfaces[0]['diameter'] if real_surfaces else 25.4:.2f},")
    print(f"  interfaces_v2=[")

    cumulative_x = 0.0
    current_material = ""

    for surf in data['surfaces']:
        if surf['number'] == 0 or surf['number'] >= len(data['surfaces']) - 1:
            continue

        n1 = get_index(current_material)
        n2 = get_index(surf['glass'])
        half_diam = surf['diameter'] / 2.0

        mat1 = current_material if current_material else "Air"
        mat2 = surf['glass'] if surf['glass'] else "Air"

        # Get radius info
        radius = 1.0 / surf['curvature'] if abs(surf['curvature']) > 1e-10 else float('inf')
        is_curved = radius != float('inf')

        print(f"    InterfaceDefinition(")
        print(f"      x1_mm={cumulative_x:.2f}, y1_mm={-half_diam:.2f},")
        print(f"      x2_mm={cumulative_x:.2f}, y2_mm={half_diam:.2f},")
        print(f"      element_type='refractive_interface',")
        print(f"      name='S{surf['number']}: {mat1} → {mat2}',")
        print(f"      n1={n1:.4f}, n2={n2:.4f},")
        if is_curved:
            print(f"      is_curved=True,")
            print(f"      radius_of_curvature_mm={radius:.2f}")
        else:
            print(f"      is_curved=False")
        print(f"    ),")

        cumulative_x += surf['thickness']
        current_material = surf['glass']

    print(f"  ]")
    print(f")")
    print()

    print("="*70)
    print("NEXT STEPS")
    print("="*70)
    print()
    print("To use this in OptiVerse:")
    print("  1. Implement Zemax import in Component Editor")
    print("  2. Parse ZMX file using zemax_parser.py")
    print("  3. Convert to InterfaceDefinition objects")
    print("  4. Create ComponentRecord with interfaces_v2")
    print("  5. Save to library or use directly in raytracing")
    print()


if __name__ == "__main__":
    main()



