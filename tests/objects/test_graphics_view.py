from PyQt6 import QtCore, QtGui, QtWidgets


def test_graphics_view_scale_bar_smoke(qtbot):
    from optiverse.objects.views.graphics_view import GraphicsView

    sc = QtWidgets.QGraphicsScene()
    v = GraphicsView(sc)
    qtbot.addWidget(v)
    v.resize(300, 200)
    v.show()
    qtbot.waitExposed(v)
    # trigger a redraw
    v.viewport().update()
    assert v.isVisible()


def test_graphics_view_mac_gestures_initialization(qtbot):
    """Test that Mac-specific gesture support initializes correctly."""
    from optiverse.objects.views.graphics_view import GraphicsView
    from optiverse.platform.paths import is_macos

    sc = QtWidgets.QGraphicsScene()
    v = GraphicsView(sc)
    qtbot.addWidget(v)

    # Verify viewport update mode is set correctly based on platform
    if is_macos():
        assert (
            v.viewportUpdateMode()
            == QtWidgets.QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate
        )
    else:
        assert (
            v.viewportUpdateMode() == QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

    # Verify gesture state variables exist
    assert hasattr(v, "_pinch_start_scale")
    assert hasattr(v, "_is_panning_gesture")


def test_graphics_view_wheel_event_handles_pixel_delta(qtbot):
    """Test that wheel events with pixel deltas (Mac trackpad) are handled."""
    from optiverse.objects.views.graphics_view import GraphicsView

    sc = QtWidgets.QGraphicsScene()
    v = GraphicsView(sc)
    qtbot.addWidget(v)
    v.show()

    # Simulate trackpad scroll event with pixel delta
    pos = QtCore.QPointF(150, 100)
    pixel_delta = QtCore.QPoint(10, 20)  # Simulate trackpad scroll
    angle_delta = QtCore.QPoint(0, 0)  # No angle delta (trackpad, not wheel)

    event = QtGui.QWheelEvent(
        pos,  # position
        v.mapToGlobal(pos.toPoint()),  # globalPosition
        pixel_delta,  # pixelDelta
        angle_delta,  # angleDelta
        QtCore.Qt.MouseButton.NoButton,  # buttons
        QtCore.Qt.KeyboardModifier.NoModifier,  # modifiers
        QtCore.Qt.ScrollPhase.ScrollUpdate,  # phase
        False,  # inverted
    )

    # On Mac, this should be handled; on other platforms, it will be ignored
    v.wheelEvent(event)

    # Test passes if no exception is raised
    assert True


def test_graphics_view_pinch_gesture_handler(qtbot):
    """Test that pinch gesture handler exists and can be called."""
    from optiverse.objects.views.graphics_view import GraphicsView

    sc = QtWidgets.QGraphicsScene()
    v = GraphicsView(sc)
    qtbot.addWidget(v)

    # Verify the method exists
    assert hasattr(v, "_handle_pinch_gesture")
    assert callable(v._handle_pinch_gesture)

    # Verify gesture event handler exists
    assert hasattr(v, "_handle_gesture_event")
    assert callable(v._handle_gesture_event)
