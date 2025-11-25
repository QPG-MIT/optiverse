def test_autotrace_triggers_on_scene_change(qtbot):
    from optiverse.core.models import LensParams, SourceParams
    from optiverse.objects import ComponentItem, SourceItem
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    s = SourceItem(SourceParams(x_mm=-200, y_mm=0))
    params = LensParams(x_mm=0, y_mm=0, object_height_mm=50.0, efl_mm=100.0)
    L = ComponentItem(params)
    w.scene.addItem(s)
    w.scene.addItem(L)

    called = {"n": 0}
    _orig = w.retrace

    def _wrap():
        called["n"] += 1
        _orig()

    w.retrace = _wrap  # type: ignore[assignment]

    # move lens → scene.changed should fire and schedule retrace
    L.setPos(10, 0)
    qtbot.waitUntil(lambda: called["n"] > 0, timeout=1000)
    # restore to avoid callbacks after teardown
    w.retrace = _orig  # type: ignore[assignment]


def test_snap_selected_to_grid(qtbot):
    from optiverse.core.models import LensParams
    from optiverse.objects import ComponentItem
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    params = LensParams(x_mm=10.7, y_mm=9.3, object_height_mm=50.0, efl_mm=100.0)
    L = ComponentItem(params)
    w.scene.addItem(L)
    L.setSelected(True)

    # call snap helper directly
    w._snap_selected_to_grid()
    p = L.pos()
    assert int(p.x()) == round(10.7)
    assert int(p.y()) == round(9.3)
