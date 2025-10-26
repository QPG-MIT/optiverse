def test_main_window_smoke(qtbot):
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    assert w.windowTitle().startswith("Photonic Sandbox")

