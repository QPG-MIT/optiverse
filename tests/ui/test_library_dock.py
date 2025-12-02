import gc

import pytest
from PyQt6 import QtWidgets


@pytest.fixture
def main_window(qapp, qtbot):
    """Create a MainWindow instance for testing with proper cleanup."""
    from optiverse.ui.views.main_window import MainWindow
    from tests.helpers import safe_wait_exposed

    window = MainWindow()
    # Disable autotrace and stop timers to prevent hangs in CI
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    window.file_controller._autosave_timer.stop()
    QtWidgets.QApplication.processEvents()
    qtbot.addWidget(window)
    window.show()
    safe_wait_exposed(qtbot, window)
    yield window
    # Clean up
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    window.file_controller._autosave_timer.stop()
    window.file_controller.mark_clean()
    window.raytracing_controller.clear_rays()
    for item in list(window.scene.items()):
        window.scene.removeItem(item)
    QtWidgets.QApplication.processEvents()
    window.close()
    QtWidgets.QApplication.processEvents()
    gc.collect()
    QtWidgets.QApplication.processEvents()


def test_library_dock_smoke(main_window):
    """Test that library dock is visible on startup."""
    assert hasattr(main_window, "libDock")
    assert main_window.libDock.isVisible()
