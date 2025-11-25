from PyQt6 import QtCore, QtWidgets


def test_trace_renders_paths(qtbot):
    from optiverse.ui.views.main_window import MainWindow
    from optiverse.objects import SourceItem
    from optiverse.core.models import SourceParams, LensParams
    from optiverse.objects import ComponentItem

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    # add a source and a lens, then retrace
    s = SourceItem(SourceParams(x_mm=-200, y_mm=0))
    params = LensParams(x_mm=0, y_mm=0, object_height_mm=50.0, efl_mm=100.0)
    L = ComponentItem(params)
    w.scene.addItem(s)
    w.scene.addItem(L)

    # invoke retrace
    w.retrace()
    # expect at least one QGraphicsPathItem
    path_items = [it for it in w.scene.items() if isinstance(it, QtWidgets.QGraphicsPathItem)]
    assert len(path_items) >= 1




