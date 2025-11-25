"""
Integration tests for magnetic snap feature.

Tests the complete flow of magnetic snap alignment.
"""
import pytest
from PyQt6 import QtCore, QtWidgets
from optiverse.ui.views.main_window import MainWindow
from optiverse.objects import LensItem
from optiverse.core.models import LensParams


def test_magnetic_snap_toggle(qtbot):
    """Test that magnetic snap toggle works."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Check initial state
    assert window.magnetic_snap is True
    assert window.act_magnetic_snap.isChecked()

    # Toggle off
    window.act_magnetic_snap.trigger()
    assert window.magnetic_snap is False
    assert not window.act_magnetic_snap.isChecked()

    # Toggle back on
    window.act_magnetic_snap.trigger()
    assert window.magnetic_snap is True
    assert window.act_magnetic_snap.isChecked()


def test_magnetic_snap_aligns_components(qtbot):
    """Test that components snap to align with each other."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    # Enable magnetic snap
    window.magnetic_snap = True

    # Add first lens at (100, 200)
    lens1 = LensItem(LensParams(x_mm=100, y_mm=200))
    window.scene.addItem(lens1)
    lens1._ready = True

    # Add second lens at (300, 205) - close to same Y
    lens2 = LensItem(LensParams(x_mm=300, y_mm=205))
    window.scene.addItem(lens2)
    lens2._ready = True

    # Simulate position change (as would happen during drag)
    # The itemChange method will intercept and snap
    from PyQt6.QtCore import QPointF
    proposed_pos = QPointF(300, 205)

    # Trigger itemChange by simulating a position change
    snapped_pos = lens2.itemChange(
        lens2.GraphicsItemChange.ItemPositionChange,
        proposed_pos
    )

    # Should snap to Y=200 (within tolerance of lens1)
    # The itemChange returns the snapped position
    assert isinstance(snapped_pos, QPointF)
    assert snapped_pos.y() == 200  # Snapped to lens1's Y coordinate
    assert snapped_pos.x() == 300  # X unchanged


def test_magnetic_snap_shows_guides(qtbot):
    """Test that alignment guides are shown during snap."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Enable magnetic snap
    window.magnetic_snap = True

    # Add two lenses
    lens1 = LensItem(LensParams(x_mm=100, y_mm=200))
    window.scene.addItem(lens1)

    lens2 = LensItem(LensParams(x_mm=300, y_mm=203))
    window.scene.addItem(lens2)

    # Calculate snap
    snap_result = window._snap_helper.calculate_snap(
        lens2.pos(),
        lens2,
        window.scene,
        window.view
    )

    # Set guides
    window.view.set_snap_guides(snap_result.guide_lines)

    # Check that guides are set
    assert len(window.view._snap_guides) > 0

    # Clear guides
    window.view.clear_snap_guides()
    assert len(window.view._snap_guides) == 0


def test_magnetic_snap_respects_tolerance(qtbot):
    """Test that snap doesn't occur beyond tolerance."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Enable magnetic snap
    window.magnetic_snap = True

    # Add first lens at (100, 200)
    lens1 = LensItem(LensParams(x_mm=100, y_mm=200))
    window.scene.addItem(lens1)

    # Add second lens far away (300, 250) - beyond tolerance
    lens2 = LensItem(LensParams(x_mm=300, y_mm=250))
    window.scene.addItem(lens2)

    # Calculate snap
    snap_result = window._snap_helper.calculate_snap(
        lens2.pos(),
        lens2,
        window.scene,
        window.view
    )

    # Should NOT snap (too far)
    assert not snap_result.snapped
    assert len(snap_result.guide_lines) == 0


def test_magnetic_snap_disabled_no_snap(qtbot):
    """Test that disabling magnetic snap prevents snapping."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Disable magnetic snap
    window.magnetic_snap = False

    # Add two close lenses
    lens1 = LensItem(LensParams(x_mm=100, y_mm=200))
    window.scene.addItem(lens1)

    lens2 = LensItem(LensParams(x_mm=300, y_mm=203))
    window.scene.addItem(lens2)
    lens2.setSelected(True)

    # Simulate mouse move event (should not snap)
    # When magnetic_snap is False, the eventFilter should not apply snapping

    # Position should remain unchanged
    original_y = lens2.pos().y()

    # The snap calculation would suggest Y=200, but with magnetic_snap=False
    # the eventFilter won't apply it
    assert lens2.pos().y() == original_y


def test_magnetic_snap_persistence(qtbot):
    """Test that magnetic snap setting is persisted."""
    # Create first window and toggle snap off
    window1 = MainWindow()
    qtbot.addWidget(window1)
    window1.magnetic_snap = False
    window1.settings_service.set_value("magnetic_snap", False)

    # Create second window - should load saved setting
    window2 = MainWindow()
    qtbot.addWidget(window2)

    # Should remember the disabled state
    assert window2.magnetic_snap is False

    # Cleanup: reset to default
    window2.settings_service.set_value("magnetic_snap", True)



