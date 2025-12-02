#!/usr/bin/env python3
"""
Test script to verify Mac trackpad optimizations are working.

Run this script to verify:
1. Platform detection works correctly
2. Graphics view initializes with correct settings
3. Gesture handlers are properly configured
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PyQt6 import QtCore, QtGui, QtWidgets

from optiverse.objects.views.graphics_view import GraphicsView
from optiverse.platform.paths import is_linux, is_macos, is_windows


def test_platform_detection():
    """Test platform detection functions."""
    print("=" * 60)
    print("PLATFORM DETECTION TEST")
    print("=" * 60)
    print(f"Running on: {sys.platform}")
    print(f"is_macos():  {is_macos()}")
    print(f"is_windows(): {is_windows()}")
    print(f"is_linux():  {is_linux()}")
    print()

    # Verify only one is True
    platform_count = sum([is_macos(), is_windows(), is_linux()])
    assert platform_count == 1, "Exactly one platform should be detected"
    print("✓ Platform detection working correctly")
    print()


def test_graphics_view_configuration(app):
    """Test that GraphicsView is configured correctly for the platform."""
    print("=" * 60)
    print("GRAPHICS VIEW CONFIGURATION TEST")
    print("=" * 60)

    scene = QtWidgets.QGraphicsScene()
    view = GraphicsView(scene)

    # Test viewport update mode
    update_mode = view.viewportUpdateMode()
    print(f"Viewport update mode: {update_mode.name}")

    if is_macos():
        expected_mode = QtWidgets.QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate
        assert (
            update_mode == expected_mode
        ), f"Expected MinimalViewportUpdate on Mac, got {update_mode.name}"
        print("✓ Mac-optimized viewport update mode (MinimalViewportUpdate)")
        print("  (Updates only changed items, avoids grid artifacts)")
    else:
        expected_mode = QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        assert (
            update_mode == expected_mode
        ), f"Expected FullViewportUpdate on non-Mac, got {update_mode.name}"
        print("✓ Standard viewport update mode (FullViewportUpdate)")

    print()

    # Test gesture state variables
    print("Gesture state variables:")
    assert hasattr(view, "_pinch_start_scale"), "Missing _pinch_start_scale"
    print("✓ _pinch_start_scale exists")

    assert hasattr(view, "_is_panning_gesture"), "Missing _is_panning_gesture"
    print("✓ _is_panning_gesture exists")

    print()

    # Test gesture handlers
    print("Gesture handlers:")
    assert hasattr(view, "viewportEvent"), "Missing viewportEvent"
    print("✓ viewportEvent method exists")

    assert hasattr(view, "_handle_gesture_event"), "Missing _handle_gesture_event"
    print("✓ _handle_gesture_event method exists")

    assert hasattr(view, "_handle_pinch_gesture"), "Missing _handle_pinch_gesture"
    print("✓ _handle_pinch_gesture method exists")

    print()


def test_wheel_event_handling(app):
    """Test that wheel events are handled correctly."""
    print("=" * 60)
    print("WHEEL EVENT HANDLING TEST")
    print("=" * 60)

    scene = QtWidgets.QGraphicsScene()
    scene.setSceneRect(-1000, -1000, 2000, 2000)
    view = GraphicsView(scene)
    view.show()

    # Test pixel delta (Mac trackpad scroll)
    print("Testing pixel delta handling (Mac trackpad)...")
    pos = QtCore.QPointF(200, 150)
    pixel_delta = QtCore.QPoint(10, 20)
    angle_delta = QtCore.QPoint(0, 0)

    wheel_event = QtGui.QWheelEvent(
        pos,
        view.mapToGlobal(pos.toPoint()),
        pixel_delta,
        angle_delta,
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        QtCore.Qt.ScrollPhase.ScrollUpdate,
        False,
    )

    try:
        view.wheelEvent(wheel_event)
        print("✓ Pixel delta event handled without error")
    except Exception as e:
        print(f"✗ Error handling pixel delta: {e}")
        raise

    # Test angle delta (mouse wheel)
    print("Testing angle delta handling (mouse wheel)...")
    angle_delta = QtCore.QPoint(0, 120)  # Standard mouse wheel tick
    pixel_delta = QtCore.QPoint(0, 0)

    wheel_event = QtGui.QWheelEvent(
        pos,
        view.mapToGlobal(pos.toPoint()),
        pixel_delta,
        angle_delta,
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,
        QtCore.Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    try:
        view.wheelEvent(wheel_event)
        print("✓ Angle delta event handled without error")
    except Exception as e:
        print(f"✗ Error handling angle delta: {e}")
        raise

    print()


def print_summary():
    """Print summary of Mac optimizations."""
    print("=" * 60)
    print("MAC TRACKPAD OPTIMIZATIONS SUMMARY")
    print("=" * 60)
    print()

    if is_macos():
        print("🎉 Running on macOS - All optimizations active!")
        print()
        print("Performance Optimizations:")
        print("  • MinimalViewportUpdate mode (faster rendering, no artifacts)")
        print("  • Explicit viewport updates (clean grid rendering)")
        print("  • Retina-optimized rendering")
        print()
        print("Trackpad Gestures Enabled:")
        print("  • Two-finger scroll → Pan canvas")
        print("  • Pinch (two fingers) → Zoom in/out")
        print("  • Cmd + scroll → Alternative zoom")
        print("  • Middle mouse → Pan (still works)")
        print("  • Mouse wheel → Zoom (still works)")
        print()
    else:
        print("Running on non-Mac platform")
        print("  • Standard rendering mode (FullViewportUpdate)")
        print("  • Mouse wheel zoom and middle-button pan available")
        print()

    print("✓ All tests passed!")
    print()
    print("To test in the actual app:")
    print("  1. Run: optiverse")
    print("  2. Try two-finger scroll to pan")
    print("  3. Try pinch gesture to zoom")
    print("  4. Verify smooth, lag-free operation")
    print()


def main():
    """Run all tests."""
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Mac Trackpad Optimization Verification".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # Platform detection doesn't need Qt app
    test_platform_detection()

    # Create Qt application for view tests
    app = QtWidgets.QApplication(sys.argv)

    try:
        test_graphics_view_configuration(app)
        test_wheel_event_handling(app)
        print_summary()
        return 0
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        # Don't call app.exec() - we don't need the event loop
        pass


if __name__ == "__main__":
    sys.exit(main())
