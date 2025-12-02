from PyQt6 import QtWidgets


def test_beamsplitter_item_insert(qtbot):
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)

    # call insert beamsplitter via the window API once implemented
    assert hasattr(w, "_insert_beamsplitter")
    w._insert_beamsplitter()
    items = w.scene.items()
    assert any(isinstance(it, QtWidgets.QGraphicsObject) for it in items)
