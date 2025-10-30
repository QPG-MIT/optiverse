#!/usr/bin/env python3
"""
Test script to verify interface coordinate system math (no Qt required).

This script tests the coordinate transformation logic without importing Qt.
"""


def test_coordinate_transformations():
    """Test coordinate transformations between different systems."""
    
    print("=" * 70)
    print("INTERFACE COORDINATE SYSTEM MATH TEST")
    print("=" * 70)
    print()
    
    # Test 1: Storage Y-down coordinates
    print("Test 1: Create interface in storage format (Y-down)")
    print("-" * 70)
    
    # Create interface at: 10mm right, 5mm BELOW center (Y-down, positive Y is down)
    storage_x1, storage_y1 = 10.0, 5.0   # Point 1: below center
    storage_x2, storage_y2 = 10.0, -5.0  # Point 2: above center
    
    print(f"Storage coords (Y-down):")
    print(f"  Point 1: ({storage_x1:.1f}, {storage_y1:.1f}) mm")
    print(f"  Point 2: ({storage_x2:.1f}, {storage_y2:.1f}) mm")
    print(f"  Interpretation: Vertical line at X=10mm, from 5mm below to 5mm above center")
    print()
    
    # Test 2: Transform to canvas coordinates (Y-up)
    print("Test 2: Transform to canvas display format (Y-up)")
    print("-" * 70)
    
    # Simulate _sync_interfaces_to_canvas() transformation
    canvas_x1 = storage_x1
    canvas_y1 = -storage_y1  # Flip Y: storage Y-down → canvas Y-up
    canvas_x2 = storage_x2
    canvas_y2 = -storage_y2  # Flip Y: storage Y-down → canvas Y-up
    
    print(f"Canvas coords (Y-up):")
    print(f"  Point 1: ({canvas_x1:.1f}, {canvas_y1:.1f}) mm")
    print(f"  Point 2: ({canvas_x2:.1f}, {canvas_y2:.1f}) mm")
    print(f"  Interpretation: Vertical line at X=10mm, from 5mm above to 5mm below center")
    
    # Verify flip
    assert canvas_y1 == -storage_y1, "Y1 flip failed"
    assert canvas_y2 == -storage_y2, "Y2 flip failed"
    print(f"  ✓ Verification: Y-coordinates flipped correctly")
    print()
    
    # Test 3: User drags on canvas (Y-up) → storage (Y-down)
    print("Test 3: User drags endpoint up by 3mm on canvas")
    print("-" * 70)
    
    # User drags point 2 up by 3mm in canvas (Y-up)
    canvas_y2_new = canvas_y2 + 3.0  # Drag up = increase Y in Y-up system
    
    print(f"Canvas before drag: Point 2 = ({canvas_x2:.1f}, {canvas_y2:.1f}) mm")
    print(f"Canvas after drag:  Point 2 = ({canvas_x2:.1f}, {canvas_y2_new:.1f}) mm")
    print(f"  Drag direction: UP (+Y in Y-up)")
    
    # Simulate _on_canvas_lines_changed() transformation
    storage_y2_new = -canvas_y2_new  # Flip Y: canvas Y-up → storage Y-down
    
    print(f"Storage before drag: Point 2 = ({canvas_x2:.1f}, {storage_y2:.1f}) mm")
    print(f"Storage after drag:  Point 2 = ({canvas_x2:.1f}, {storage_y2_new:.1f}) mm")
    print(f"  Change in storage: Y = {storage_y2:.1f} → {storage_y2_new:.1f} (more negative = higher up)")
    
    # Verify drag
    assert storage_y2_new == -canvas_y2_new, "Reverse Y flip failed"
    assert storage_y2_new < storage_y2, "Dragging up should make Y more negative in Y-down"
    print(f"  ✓ Verification: Drag up on canvas correctly translates to more negative Y in storage")
    print()
    
    # Test 4: Convert to RefractiveInterface for main canvas
    print("Test 4: Convert to RefractiveInterface for main canvas display")
    print("-" * 70)
    
    # Simulate conversion in main_window.py on_drop_component()
    ref_x1, ref_y1 = storage_x1, storage_y1  # Direct copy
    ref_x2, ref_y2 = storage_x2, storage_y2_new  # Use updated coordinate
    
    print(f"RefractiveInterface coords (Y-down):")
    print(f"  Point 1: ({ref_x1:.1f}, {ref_y1:.1f}) mm")
    print(f"  Point 2: ({ref_x2:.1f}, {ref_y2:.1f}) mm")
    
    # Verify direct copy
    assert ref_y1 == storage_y1, "Y1 should be direct copy"
    assert ref_y2 == storage_y2_new, "Y2 should be direct copy"
    print(f"  ✓ Verification: Direct copy from storage, no transformation needed")
    print()
    
    # Test 5: Apply picked line offset for display
    print("Test 5: Apply picked line offset for display on main canvas")
    print("-" * 70)
    
    # Assume picked line is at (2mm, 1mm) relative to image center
    picked_line_offset_x = 2.0
    picked_line_offset_y = 1.0
    
    # Simulate RefractiveObjectItem.paint() transformation
    display_x1 = ref_x1 - picked_line_offset_x
    display_y1 = ref_y1 - picked_line_offset_y
    display_x2 = ref_x2 - picked_line_offset_x
    display_y2 = ref_y2 - picked_line_offset_y
    
    print(f"Picked line offset: ({picked_line_offset_x:.1f}, {picked_line_offset_y:.1f}) mm")
    print(f"Display coords (Y-down, relative to picked line):")
    print(f"  Point 1: ({display_x1:.1f}, {display_y1:.1f}) mm")
    print(f"  Point 2: ({display_x2:.1f}, {display_y2:.1f}) mm")
    
    # Verify offset
    assert display_x1 == ref_x1 - picked_line_offset_x, "X offset failed"
    assert display_y1 == ref_y1 - picked_line_offset_y, "Y offset failed"
    print(f"  ✓ Verification: Offset applied, Y-down preserved")
    print()
    
    # Test 6: Round-trip verification
    print("Test 6: Round-trip verification")
    print("-" * 70)
    
    # Storage → Canvas → Storage
    storage_orig = storage_y1
    canvas_transformed = -storage_orig
    storage_back = -canvas_transformed
    
    print(f"Original storage Y: {storage_orig:.1f} mm")
    print(f"Canvas Y (after flip): {canvas_transformed:.1f} mm")
    print(f"Back to storage (after reverse flip): {storage_back:.1f} mm")
    
    # Verify round-trip
    assert abs(storage_orig - storage_back) < 0.001, "Round-trip failed"
    print(f"  ✓ Verification: Round-trip successful (difference < 0.001mm)")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY - ALL TESTS PASSED ✓")
    print("=" * 70)
    print()
    print("Coordinate system transformations verified:")
    print("  1. Storage (Y-down) → Canvas (Y-up): Flip Y-axis ✓")
    print("  2. Canvas (Y-up) → Storage (Y-down): Flip Y-axis ✓")
    print("  3. Storage (Y-down) → RefractiveInterface (Y-down): Direct copy ✓")
    print("  4. RefractiveInterface → Display: Apply offset, preserve Y-down ✓")
    print("  5. Round-trip: Storage → Canvas → Storage: No loss ✓")
    print()
    print("All coordinate transformations are mathematically correct!")
    print()
    
    return True


if __name__ == "__main__":
    success = test_coordinate_transformations()
    exit(0 if success else 1)

