from PyQt6 import QtWidgets

from tests.helpers import safe_wait_exposed


def test_beamsplitter_item_insert(qtbot):
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    safe_wait_exposed(qtbot, w)

    # call insert beamsplitter via the window API once implemented
    assert hasattr(w, "_insert_beamsplitter")
    w._insert_beamsplitter()
    items = w.scene.items()
    assert any(isinstance(it, QtWidgets.QGraphicsObject) for it in items)
