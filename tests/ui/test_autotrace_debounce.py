"""Tests for autotrace debouncing to prevent framerate issues."""
import time
from PyQt6 import QtCore


def test_autotrace_debouncing_prevents_multiple_retraces(qtbot):
    """Test that multiple rapid schedule_retrace calls only trigger one actual retrace."""
    from optiverse.ui.views.main_window import MainWindow
    from optiverse.objects import SourceItem
    from optiverse.core.models import LensParams
    from optiverse.objects import ComponentItem

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    # Add items to scene
    from optiverse.core.models import SourceParams
    s = SourceItem(SourceParams(x_mm=-200, y_mm=0))
    params = LensParams(x_mm=0, y_mm=0, object_height_mm=50.0, efl_mm=100.0)
    L = ComponentItem(params)
    w.scene.addItem(s)
    w.scene.addItem(L)

    # Track retrace calls
    retrace_count = {"n": 0}
    _orig = w.retrace
    
    def _wrap():
        retrace_count["n"] += 1
        _orig()
    
    w.retrace = _wrap  # type: ignore[assignment]

    # Schedule multiple retraces rapidly (simulating rapid changes)
    initial_count = retrace_count["n"]
    for _ in range(10):
        w._schedule_retrace()
    
    # Wait for debounce timer to fire (50ms + buffer)
    qtbot.wait(100)
    
    # Should only have triggered ONE actual retrace due to debouncing
    assert retrace_count["n"] == initial_count + 1, \
        f"Expected 1 retrace, got {retrace_count['n'] - initial_count}"
    
    # Restore to avoid callbacks after teardown
    w.retrace = _orig  # type: ignore[assignment]


def test_schedule_retrace_respects_autotrace_flag(qtbot):
    """Test that _schedule_retrace respects the autotrace flag."""
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    # Track retrace calls
    retrace_count = {"n": 0}
    _orig = w.retrace
    
    def _wrap():
        retrace_count["n"] += 1
        _orig()
    
    w.retrace = _wrap  # type: ignore[assignment]

    # Disable autotrace
    w.autotrace = False
    initial_count = retrace_count["n"]
    
    # Try to schedule retrace
    w._schedule_retrace()
    qtbot.wait(100)
    
    # Should NOT have triggered retrace
    assert retrace_count["n"] == initial_count, \
        "Retrace should not fire when autotrace is disabled"
    
    # Enable autotrace
    w.autotrace = True
    w._schedule_retrace()
    qtbot.wait(100)
    
    # Should have triggered retrace
    assert retrace_count["n"] == initial_count + 1, \
        "Retrace should fire when autotrace is enabled"
    
    # Restore to avoid callbacks after teardown
    w.retrace = _orig  # type: ignore[assignment]


def test_retrace_pending_flag_prevents_duplicate_scheduling(qtbot):
    """Test that _retrace_pending flag prevents duplicate timer scheduling."""
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    # Schedule retrace
    assert not w._retrace_pending, "Should start with no pending retrace"
    w._schedule_retrace()
    assert w._retrace_pending, "Flag should be set after scheduling"
    
    # Try to schedule again while pending
    w._schedule_retrace()
    assert w._retrace_pending, "Flag should still be set"
    
    # Wait for timer to fire
    qtbot.wait(100)
    
    # Flag should be cleared after execution
    assert not w._retrace_pending, "Flag should be cleared after retrace executes"

