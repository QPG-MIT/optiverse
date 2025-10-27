from PyQt6 import QtCore, QtWidgets


def test_ruler_item_smoke(qtbot):
    from optiverse.widgets.ruler_item import RulerItem
    from optiverse.widgets.graphics_view import GraphicsView

    scene = QtWidgets.QGraphicsScene()
    view = GraphicsView(scene)
    qtbot.addWidget(view)
    view.resize(300, 200)
    view.show()
    qtbot.waitExposed(view)

    r = RulerItem(QtCore.QPointF(-50, 0), QtCore.QPointF(50, 0))
    scene.addItem(r)
    assert r.boundingRect().isValid()
    # move one endpoint
    r._p2 = QtCore.QPointF(60, 0)
    scene.update()
    assert r.boundingRect().width() > 0


def test_text_note_item_smoke(qtbot):
    from optiverse.widgets.text_note_item import TextNoteItem
    from optiverse.widgets.graphics_view import GraphicsView

    scene = QtWidgets.QGraphicsScene()
    view = GraphicsView(scene)
    qtbot.addWidget(view)
    view.resize(300, 200)
    view.show()
    qtbot.waitExposed(view)

    t = TextNoteItem("Hello")
    scene.addItem(t)
    t.setPos(10, 10)
    assert t.toPlainText() == "Hello"


