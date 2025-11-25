from PyQt6 import QtWidgets


def test_beamsplitter_renders_two_paths(qtbot):
    from optiverse.ui.views.main_window import MainWindow
    from optiverse.objects import SourceItem
    from optiverse.core.models import SourceParams, BeamsplitterParams
    from optiverse.objects import ComponentItem

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    s = SourceItem(SourceParams(x_mm=-200, y_mm=0))
    params = BeamsplitterParams(x_mm=0, y_mm=0, angle_deg=45.0, object_height_mm=50.0, split_T=50.0, split_R=50.0)
    bs = ComponentItem(params)
    w.scene.addItem(s)
    w.scene.addItem(bs)

    w.retrace()
    path_items = [it for it in w.scene.items() if isinstance(it, QtWidgets.QGraphicsPathItem)]
    assert len(path_items) >= 2




