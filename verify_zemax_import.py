#!/usr/bin/env python3
"""
Simple verification script for Zemax import fix.
This script verifies that the parser extracts data correctly.
"""

import sys
sys.path.insert(0, 'src')

from optiverse.services.zemax_parser import ZemaxParser

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}ℹ️  {text}{RESET}")

ZEMAX_FILE = "/Users/benny/Downloads/AC254-100-B-Zemax(ZMX).zmx"

print_header("ZEMAX IMPORT VERIFICATION")

# Parse the file
print("Parsing Zemax file...")
parser = ZemaxParser()
data = parser.parse(ZEMAX_FILE)

if not data:
    print_error("Failed to parse Zemax file!")
    sys.exit(1)

print_success(f"Parsed file: {data.name}")
print_success(f"Found {len(data.surfaces)} surfaces")
print_success(f"Primary wavelength: {data.primary_wavelength_um*1000:.1f} nm")
print()

# Check each surface
print_header("SURFACE DATA VERIFICATION")

expected = {
    0: {"name": "Object", "curv": 0.0, "thick": float('inf'), "glass": "", "diam": 0.0},
    1: {"name": "Entry", "curv": 0.014997, "thick": 4.0, "glass": "N-LAK22", "diam": 12.7},
    2: {"name": "Cemented", "curv": -0.018622, "thick": 1.5, "glass": "N-SF6HT", "diam": 12.7},
    3: {"name": "Exit", "curv": -0.003854, "thick": 97.09, "glass": "", "diam": 12.7},
    4: {"name": "Image", "curv": 0.0, "thick": 0.0, "glass": "", "diam": 0.005},
}

all_passed = True

for surf in data.surfaces:
    exp = expected.get(surf.number)
    if not exp:
        continue
    
    print(f"Surface {surf.number} ({exp['name']}):")
    
    # Check curvature
    if abs(surf.curvature - exp["curv"]) < 0.00001:
        print_success(f"  Curvature: {surf.curvature:.6f} (1/mm)")
        if not surf.is_flat:
            print_success(f"  Radius: {surf.radius_mm:.2f} mm")
    else:
        print_error(f"  Curvature: got {surf.curvature:.6f}, expected {exp['curv']:.6f}")
        all_passed = False
    
    # Check thickness
    if surf.number < 4:  # Skip image surface
        if abs(surf.thickness - exp["thick"]) < 0.01 or (surf.thickness == float('inf') and exp["thick"] == float('inf')):
            print_success(f"  Thickness: {surf.thickness:.2f} mm" if surf.thickness != float('inf') else "  Thickness: ∞")
        else:
            print_error(f"  Thickness: got {surf.thickness:.2f}, expected {exp['thick']:.2f}")
            all_passed = False
    
    # Check glass
    if surf.glass == exp["glass"]:
        if surf.glass:
            print_success(f"  Glass: {surf.glass}")
        else:
            print_success(f"  Glass: Air")
    else:
        print_error(f"  Glass: got '{surf.glass}', expected '{exp['glass']}'")
        all_passed = False
    
    # Check diameter
    if abs(surf.diameter - exp["diam"]) < 0.1:
        print_success(f"  Diameter: {surf.diameter:.2f} mm")
    else:
        print_error(f"  Diameter: got {surf.diameter:.2f}, expected {exp['diam']:.2f}")
        all_passed = False
    
    print()

# Summary
print_header("VERIFICATION SUMMARY")

if all_passed:
    print_success("ALL CHECKS PASSED!")
    print()
    print_info("The Zemax parser is working correctly.")
    print_info("Next steps:")
    print_info("  1. Run: python src/optiverse/app/main.py")
    print_info("  2. Open Component Editor")
    print_info("  3. Click 'Import Zemax...' button")
    print_info("  4. Select the .zmx file")
    print_info("  5. Check the interface panel (right side) for:")
    print_info("     - 3 interfaces listed")
    print_info("     - Curvature values (R=+66.68, R=-53.70, R=-259.41)")
    print_info("     - Refractive indices (n1, n2)")
    print_info("  6. Load an image (File → Open Image) to see interfaces on canvas")
    print()
else:
    print_error("SOME CHECKS FAILED!")
    print_info("Please review the errors above.")

sys.exit(0 if all_passed else 1)

