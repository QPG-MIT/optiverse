from PyQt6 import QtCore, QtGui


def test_image_canvas_click_and_line(qtbot):
    from optiverse.objects import ImageCanvas

    w = ImageCanvas()
    qtbot.addWidget(w)

    # load a small pixmap
    img = QtGui.QImage(100, 80, QtGui.QImage.Format.Format_ARGB32)
    img.fill(0)
    pix = QtGui.QPixmap.fromImage(img)
    w.set_pixmap(pix)

    assert w.has_image()
    assert w.image_pixel_size() == (100, 80)

    # Simulate clicks roughly in the center: use widget coords (scaled to fit)
    w.resize(200, 200)
    w.show()
    qtbot.waitExposed(w)

    # Click twice near center of the target rect
    pos = w.rect().center()
    qtbot.mouseClick(w, QtCore.Qt.MouseButton.LeftButton, pos=pos)
    qtbot.mouseClick(w, QtCore.Qt.MouseButton.LeftButton, pos=pos + QtCore.QPoint(10, 0))

    p1, p2 = w.get_points()
    assert p1 is not None and p2 is not None


