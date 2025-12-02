"""Test beamsplitter ray tracing."""

import gc
import sys

import pytest
from PyQt6 import QtWidgets


# Skip this test for now - needs further investigation for pytest compatibility
@pytest.mark.skip(reason="Test hangs in pytest - passes when run standalone")
def test_beamsplitter_renders_two_paths():
    """Test that beamsplitter creates split ray paths."""
    from optiverse.core.models import BeamsplitterParams, SourceParams
    from optiverse.objects import ComponentItem, SourceItem
    from optiverse.ui.views.main_window import MainWindow

    # Ensure QApplication exists
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    # Setup
    window = MainWindow()
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    window.file_controller._autosave_timer.stop()
    app.processEvents()

    try:
        # Create and add items
        s = SourceItem(SourceParams(x_mm=-200, y_mm=0))
        params = BeamsplitterParams(
            x_mm=0, y_mm=0, angle_deg=45.0, object_height_mm=50.0, split_T=50.0, split_R=50.0
        )
        bs = ComponentItem(params)
        window.scene.addItem(s)
        window.scene.addItem(bs)
        app.processEvents()

        # Retrace
        window.retrace()
        app.processEvents()

        # Check results
        path_items = [
            it for it in window.scene.items() if isinstance(it, QtWidgets.QGraphicsPathItem)
        ]
        assert len(path_items) >= 2
    finally:
        # Cleanup
        window.autotrace = False
        window.raytracing_controller._retrace_timer.stop()
        window.file_controller._autosave_timer.stop()
        window.file_controller.mark_clean()
        window.raytracing_controller.clear_rays()
        for item in list(window.scene.items()):
            window.scene.removeItem(item)
        app.processEvents()
        window.close()
        app.processEvents()
        gc.collect()
        app.processEvents()
