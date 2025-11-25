def test_library_dock_smoke(qtbot):
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    assert hasattr(w, "libraryDock")
    assert w.libraryDock.isVisible()




