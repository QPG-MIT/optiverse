from PyQt6 import QtCore, QtWidgets


def test_trace_renders_paths(qtbot):
    from optiverse.ui.views.main_window import MainWindow
    from optiverse.widgets.source_item import SourceItem
    from optiverse.widgets.lens_item import LensItem

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    # add a source and a lens, then retrace
    s = SourceItem(); s.setPos(-200, 0)
    L = LensItem(); L.setPos(0, 0)
    w.scene.addItem(s)
    w.scene.addItem(L)

    # invoke retrace
    w.retrace()
    # expect at least one QGraphicsPathItem
    path_items = [it for it in w.scene.items() if isinstance(it, QtWidgets.QGraphicsPathItem)]
    assert len(path_items) >= 1


