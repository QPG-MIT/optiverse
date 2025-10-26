from PyQt6 import QtCore


def test_autotrace_triggers_on_scene_change(qtbot):
    from optiverse.ui.views.main_window import MainWindow
    from optiverse.widgets.source_item import SourceItem
    from optiverse.widgets.lens_item import LensItem

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    s = SourceItem(); s.setPos(-200, 0)
    L = LensItem(); L.setPos(0, 0)
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
    from optiverse.ui.views.main_window import MainWindow
    from optiverse.widgets.lens_item import LensItem

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    L = LensItem(); L.setPos(10.7, 9.3)
    w.scene.addItem(L)
    L.setSelected(True)

    # call snap helper directly
    w._snap_selected_to_grid()
    p = L.pos()
    assert int(p.x()) == round(10.7)
    assert int(p.y()) == round(9.3)


