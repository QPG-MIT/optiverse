#!/usr/bin/env python3
"""
Test script to verify line_px computation from interface coordinates.

This script tests that interface mm coordinates are correctly converted to line_px
for sprite positioning.
"""


def compute_line_px(x1_mm, y1_mm, x2_mm, y2_mm, object_height_mm):
    """
    Compute line_px from interface coordinates.
    
    Converts from:
    - Interface: mm coordinates, centered (0,0 at image center), Y-down
    To:
    - line_px: pixel coordinates, normalized 1000px space (0,0 at top-left), Y-down
    """
    mm_per_px = object_height_mm / 1000.0
    
    x1_px = (x1_mm / mm_per_px) + 500.0
    y1_px = (y1_mm / mm_per_px) + 500.0
    x2_px = (x2_mm / mm_per_px) + 500.0
    y2_px = (y2_mm / mm_per_px) + 500.0
    
    return (x1_px, y1_px, x2_px, y2_px)


def test_line_px_computation():
    """Test line_px computation with various interface configurations."""
    
    print("=" * 70)
    print("LINE_PX COMPUTATION TEST")
    print("=" * 70)
    print()
    
    # Test 1: Vertical line at center (typical lens)
    print("Test 1: Vertical line at center (lens)")
    print("-" * 70)
    object_height_mm = 30.5
    x1_mm, y1_mm, x2_mm, y2_mm = 0.0, -15.25, 0.0, 15.25
    
    line_px = compute_line_px(x1_mm, y1_mm, x2_mm, y2_mm, object_height_mm)
    
    print(f"Interface (mm, centered):")
    print(f"  Point 1: ({x1_mm:.2f}, {y1_mm:.2f}) mm")
    print(f"  Point 2: ({x2_mm:.2f}, {y2_mm:.2f}) mm")
    print()
    print(f"line_px (1000px space, top-left origin):")
    print(f"  Point 1: ({line_px[0]:.1f}, {line_px[1]:.1f}) px")
    print(f"  Point 2: ({line_px[2]:.1f}, {line_px[3]:.1f}) px")
    
    # Verify expectations
    assert abs(line_px[0] - 500.0) < 0.1, "X1 should be at horizontal center"
    assert abs(line_px[2] - 500.0) < 0.1, "X2 should be at horizontal center"
    assert abs(line_px[1] - 0.0) < 0.1, "Y1 should be at top"
    assert abs(line_px[3] - 1000.0) < 0.1, "Y2 should be at bottom"
    
    print(f"  ✓ Verification: Vertical line from top to bottom, horizontally centered")
    print()
    
    # Test 2: Diagonal line (typical beamsplitter)
    print("Test 2: Diagonal line (beamsplitter at 45°)")
    print("-" * 70)
    object_height_mm = 25.4
    x1_mm, y1_mm, x2_mm, y2_mm = -12.7, -12.7, 12.7, 12.7
    
    line_px = compute_line_px(x1_mm, y1_mm, x2_mm, y2_mm, object_height_mm)
    
    print(f"Interface (mm, centered):")
    print(f"  Point 1: ({x1_mm:.2f}, {y1_mm:.2f}) mm")
    print(f"  Point 2: ({x2_mm:.2f}, {y2_mm:.2f}) mm")
    print()
    print(f"line_px (1000px space, top-left origin):")
    print(f"  Point 1: ({line_px[0]:.1f}, {line_px[1]:.1f}) px")
    print(f"  Point 2: ({line_px[2]:.1f}, {line_px[3]:.1f}) px")
    
    # Verify expectations (diagonal from top-left to bottom-right)
    assert line_px[0] < 500.0, "X1 should be left of center"
    assert line_px[2] > 500.0, "X2 should be right of center"
    assert line_px[1] < 500.0, "Y1 should be above center"
    assert line_px[3] > 500.0, "Y2 should be below center"
    
    print(f"  ✓ Verification: Diagonal line from top-left to bottom-right quadrant")
    print()
    
    # Test 3: Off-center horizontal line
    print("Test 3: Off-center horizontal line")
    print("-" * 70)
    object_height_mm = 40.0
    x1_mm, y1_mm, x2_mm, y2_mm = -10.0, 5.0, 10.0, 5.0
    
    line_px = compute_line_px(x1_mm, y1_mm, x2_mm, y2_mm, object_height_mm)
    
    print(f"Interface (mm, centered):")
    print(f"  Point 1: ({x1_mm:.2f}, {y1_mm:.2f}) mm")
    print(f"  Point 2: ({x2_mm:.2f}, {y2_mm:.2f}) mm")
    print()
    print(f"line_px (1000px space, top-left origin):")
    print(f"  Point 1: ({line_px[0]:.1f}, {line_px[1]:.1f}) px")
    print(f"  Point 2: ({line_px[2]:.1f}, {line_px[3]:.1f}) px")
    
    # Verify expectations (horizontal line below center)
    assert line_px[0] < 500.0, "X1 should be left of center"
    assert line_px[2] > 500.0, "X2 should be right of center"
    assert abs(line_px[1] - line_px[3]) < 0.1, "Y should be same (horizontal line)"
    assert line_px[1] > 500.0, "Y should be below center (positive y in mm = down)"
    
    print(f"  ✓ Verification: Horizontal line below center")
    print()
    
    # Test 4: Verify round-trip (line_px back to mm)
    print("Test 4: Round-trip verification")
    print("-" * 70)
    object_height_mm = 30.5
    x1_mm_orig, y1_mm_orig = 0.0, -15.25
    x2_mm_orig, y2_mm_orig = 0.0, 15.25
    
    # Forward: mm → px
    line_px = compute_line_px(x1_mm_orig, y1_mm_orig, x2_mm_orig, y2_mm_orig, object_height_mm)
    
    # Reverse: px → mm
    mm_per_px = object_height_mm / 1000.0
    x1_mm_back = (line_px[0] - 500.0) * mm_per_px
    y1_mm_back = (line_px[1] - 500.0) * mm_per_px
    x2_mm_back = (line_px[2] - 500.0) * mm_per_px
    y2_mm_back = (line_px[3] - 500.0) * mm_per_px
    
    print(f"Original mm coords: ({x1_mm_orig:.2f}, {y1_mm_orig:.2f}) to ({x2_mm_orig:.2f}, {y2_mm_orig:.2f})")
    print(f"After round-trip:   ({x1_mm_back:.2f}, {y1_mm_back:.2f}) to ({x2_mm_back:.2f}, {y2_mm_back:.2f})")
    
    # Verify round-trip accuracy
    assert abs(x1_mm_orig - x1_mm_back) < 0.01, "X1 round-trip failed"
    assert abs(y1_mm_orig - y1_mm_back) < 0.01, "Y1 round-trip failed"
    assert abs(x2_mm_orig - x2_mm_back) < 0.01, "X2 round-trip failed"
    assert abs(y2_mm_orig - y2_mm_back) < 0.01, "Y2 round-trip failed"
    
    print(f"  ✓ Verification: Round-trip accurate to < 0.01mm")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY - ALL TESTS PASSED ✓")
    print("=" * 70)
    print()
    print("line_px computation verified:")
    print("  1. Vertical line (lens) → correct ✓")
    print("  2. Diagonal line (beamsplitter) → correct ✓")
    print("  3. Off-center horizontal line → correct ✓")
    print("  4. Round-trip accuracy → correct ✓")
    print()
    print("The line_px computation correctly converts interface mm coordinates")
    print("to normalized 1000px space for sprite positioning.")
    print()
    
    return True


if __name__ == "__main__":
    success = test_line_px_computation()
    exit(0 if success else 1)

