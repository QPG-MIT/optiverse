from PyQt6 import QtWidgets


def test_graphics_view_scale_bar_smoke(qtbot):
    from optiverse.widgets.graphics_view import GraphicsView

    sc = QtWidgets.QGraphicsScene()
    v = GraphicsView(sc)
    qtbot.addWidget(v)
    v.resize(300, 200)
    v.show()
    qtbot.waitExposed(v)
    # trigger a redraw
    v.viewport().update()
    assert v.isVisible()


