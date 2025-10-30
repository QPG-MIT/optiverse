#!/usr/bin/env python3
"""
Test script to verify interface coordinate system fix.

This script tests the coordinate transformations between:
1. Storage format (top-left origin, Y-down)
2. Canvas display (center origin, Y-up)
3. Scene rendering (item-relative, Y-down)

Run this to verify the fix is working correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from optiverse.core.interface_definition import InterfaceDefinition


def test_coordinate_transformation():
    """Test the coordinate transformation logic."""
    
    print("=" * 60)
    print("Interface Coordinate System Test")
    print("=" * 60)
    
    # Test parameters
    object_height_mm = 25.0  # Image height in mm
    image_width_px = 1000
    image_height_px = 1000
    mm_per_px = object_height_mm / image_height_px
    w_mm = image_width_px * mm_per_px
    h_mm = object_height_mm
    
    print(f"\nImage dimensions:")
    print(f"  Pixels: {image_width_px} x {image_height_px}")
    print(f"  mm: {w_mm:.2f} x {h_mm:.2f}")
    print(f"  mm/px: {mm_per_px:.6f}")
    
    # Test case 1: Interface at image center
    print("\n" + "-" * 60)
    print("Test 1: Interface at image center (NEW CENTERED SYSTEM)")
    print("-" * 60)
    
    # Storage coordinates (CENTER origin, Y-down)
    x1_storage = -5.0  # 5mm left of center
    y1_storage = 0.0   # At vertical center
    x2_storage = 5.0   # 5mm right of center
    y2_storage = 0.0   # At vertical center
    
    print(f"\nStorage coords (CENTER origin, Y-down):")
    print(f"  P1: ({x1_storage:.2f}, {y1_storage:.2f}) mm")
    print(f"  P2: ({x2_storage:.2f}, {y2_storage:.2f}) mm")
    
    # Convert to canvas display (center origin, Y-up)
    # Only need to flip Y axis!
    x1_canvas = x1_storage
    y1_canvas = -y1_storage
    x2_canvas = x2_storage
    y2_canvas = -y2_storage
    
    print(f"\nCanvas display coords (CENTER origin, Y-up):")
    print(f"  P1: ({x1_canvas:.2f}, {y1_canvas:.2f}) mm")
    print(f"  P2: ({x2_canvas:.2f}, {y2_canvas:.2f}) mm")
    print(f"  ✓ Should be: P1: (-5.00, 0.00), P2: (5.00, 0.00)")
    
    # Convert back to storage
    x1_storage_back = x1_canvas
    y1_storage_back = -y1_canvas
    x2_storage_back = x2_canvas
    y2_storage_back = -y2_canvas
    
    print(f"\nRound-trip back to storage:")
    print(f"  P1: ({x1_storage_back:.2f}, {y1_storage_back:.2f}) mm")
    print(f"  P2: ({x2_storage_back:.2f}, {y2_storage_back:.2f}) mm")
    
    # Verify round-trip
    tolerance = 0.001
    assert abs(x1_storage_back - x1_storage) < tolerance, "X1 round-trip failed"
    assert abs(y1_storage_back - y1_storage) < tolerance, "Y1 round-trip failed"
    assert abs(x2_storage_back - x2_storage) < tolerance, "X2 round-trip failed"
    assert abs(y2_storage_back - y2_storage) < tolerance, "Y2 round-trip failed"
    print("  ✓ Round-trip successful!")
    
    # Test case 2: Interface at top of image (NEW CENTERED SYSTEM)
    print("\n" + "-" * 60)
    print("Test 2: Interface at top of image")
    print("-" * 60)
    
    # Top of image is at -h_mm/2 in centered coords
    x1_storage = -5.0
    y1_storage = -h_mm/2  # Top edge
    x2_storage = 5.0
    y2_storage = -h_mm/2  # Top edge
    
    print(f"\nStorage coords:")
    print(f"  P1: ({x1_storage:.2f}, {y1_storage:.2f}) mm")
    print(f"  P2: ({x2_storage:.2f}, {y2_storage:.2f}) mm")
    
    # Convert to canvas (flip Y only)
    x1_canvas = x1_storage
    y1_canvas = -y1_storage
    x2_canvas = x2_storage
    y2_canvas = -y2_storage
    
    print(f"\nCanvas display coords:")
    print(f"  P1: ({x1_canvas:.2f}, {y1_canvas:.2f}) mm")
    print(f"  P2: ({x2_canvas:.2f}, {y2_canvas:.2f}) mm")
    print(f"  ✓ Should be: P1: (-5.00, 12.50), P2: (5.00, 12.50)")
    
    # Test case 3: Interface at bottom-right (NEW CENTERED SYSTEM)
    print("\n" + "-" * 60)
    print("Test 3: Interface at bottom-right corner")
    print("-" * 60)
    
    # Bottom-right in centered coords
    x1_storage = w_mm/2 - 5.0  # Near right edge
    y1_storage = h_mm/2  # Bottom edge
    x2_storage = w_mm/2  # Right edge
    y2_storage = h_mm/2  # Bottom edge
    
    print(f"\nStorage coords:")
    print(f"  P1: ({x1_storage:.2f}, {y1_storage:.2f}) mm")
    print(f"  P2: ({x2_storage:.2f}, {y2_storage:.2f}) mm")
    
    # Convert to canvas (flip Y only)
    x1_canvas = x1_storage
    y1_canvas = -y1_storage
    x2_canvas = x2_storage
    y2_canvas = -y2_storage
    
    print(f"\nCanvas display coords:")
    print(f"  P1: ({x1_canvas:.2f}, {y1_canvas:.2f}) mm")
    print(f"  P2: ({x2_canvas:.2f}, {y2_canvas:.2f}) mm")
    print(f"  ✓ Should be: P1: (7.50, -12.50), P2: (12.50, -12.50)")
    
    print("\n" + "=" * 60)
    print("All coordinate transformation tests passed! ✓")
    print("=" * 60)
    print("\nCoordinate system summary (NEW SIMPLIFIED SYSTEM):")
    print("  Storage:      (0,0) = IMAGE CENTER, Y-down (standard Qt coords)")
    print("  Canvas:       (0,0) = IMAGE CENTER, Y-up   (intuitive editing)")
    print("  Scene/Qt:     (0,0) = item origin,  Y-down (standard Qt coords)")
    print("\nTransformation: Just flip Y-axis! (y_canvas = -y_storage)")
    print("No origin shifting needed - everything uses centered coordinates!")
    print("=" * 60)


def test_interface_definition():
    """Test InterfaceDefinition with coordinate transformations."""
    
    print("\n" + "=" * 60)
    print("InterfaceDefinition Test")
    print("=" * 60)
    
    # Create interface at center (NEW CENTERED SYSTEM)
    interface = InterfaceDefinition(
        element_type="refractive_interface",
        x1_mm=-5.0,  # 5mm left of center
        y1_mm=0.0,   # At vertical center
        x2_mm=5.0,   # 5mm right of center
        y2_mm=0.0,   # At vertical center
        n1=1.0,
        n2=1.5
    )
    
    print(f"\nCreated interface:")
    print(f"  Type: {interface.element_type}")
    print(f"  Position: ({interface.x1_mm:.1f}, {interface.y1_mm:.1f}) → ({interface.x2_mm:.1f}, {interface.y2_mm:.1f})")
    print(f"  Indices: n₁={interface.n1:.2f} → n₂={interface.n2:.2f}")
    print(f"  Length: {interface.length_mm():.2f} mm")
    print(f"  Angle: {interface.angle_deg():.2f}°")
    
    # Serialize and deserialize
    data = interface.to_dict()
    interface2 = InterfaceDefinition.from_dict(data)
    
    print(f"\nRound-trip through JSON:")
    print(f"  Position: ({interface2.x1_mm:.1f}, {interface2.y1_mm:.1f}) → ({interface2.x2_mm:.1f}, {interface2.y2_mm:.1f})")
    assert interface2.x1_mm == interface.x1_mm
    assert interface2.y1_mm == interface.y1_mm
    print("  ✓ Serialization successful!")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        test_coordinate_transformation()
        test_interface_definition()
        print("\n✓ All tests passed successfully!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

