def test_main_window_smoke(qtbot):
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    try:
        w.raytracing_controller._retrace_timer.stop()
        w.file_controller._autosave_timer.stop()
        w.show()
        assert w.windowTitle().startswith("Optiverse v")
        assert "Untitled" in w.windowTitle()
    finally:
        w.raytracing_controller._retrace_timer.stop()
        w.file_controller._autosave_timer.stop()
        w.close()
