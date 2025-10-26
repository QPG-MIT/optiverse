from PyQt6 import QtWidgets


def test_beamsplitter_renders_two_paths(qtbot):
    from optiverse.ui.views.main_window import MainWindow
    from optiverse.widgets.source_item import SourceItem
    from optiverse.widgets.beamsplitter_item import BeamsplitterItem

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    s = SourceItem(); s.setPos(-200, 0)
    bs = BeamsplitterItem(); bs.setPos(0, 0); bs.setRotation(45.0)
    w.scene.addItem(s)
    w.scene.addItem(bs)

    w.retrace()
    path_items = [it for it in w.scene.items() if isinstance(it, QtWidgets.QGraphicsPathItem)]
    assert len(path_items) >= 2


