def test_library_dock_smoke(qtbot):
    from optiverse.ui.views.main_window import MainWindow

    from tests.helpers import safe_wait_exposed

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    safe_wait_exposed(qtbot, w)

    assert hasattr(w, "libraryDock")
    assert w.libraryDock.isVisible()
