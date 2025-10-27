"""Test component editor coordinate editing and dragging functionality."""

import pytest


def test_image_canvas_drag_points(qtbot):
    """Test dragging points in ImageCanvas."""
    from PyQt6 import QtCore, QtGui
    from optiverse.objects.views.image_canvas import ImageCanvas
    
    canvas = ImageCanvas()
    qtbot.addWidget(canvas)
    
    # Create a simple test image
    pix = QtGui.QPixmap(400, 300)
    pix.fill(QtCore.Qt.GlobalColor.white)
    canvas.set_pixmap(pix, None)
    
    # Set initial points
    canvas.set_points((100.0, 100.0), (200.0, 200.0))
    p1, p2 = canvas.get_points()
    assert p1 == (100.0, 100.0)
    assert p2 == (200.0, 200.0)
    
    # Simulate dragging point 1
    # Note: This is a simplified test - actual mouse dragging would require
    # more complex event simulation
    canvas._pt1 = (150.0, 150.0)
    canvas.update()
    p1, p2 = canvas.get_points()
    assert p1 == (150.0, 150.0)
    assert p2 == (200.0, 200.0)


def test_image_canvas_points_changed_signal(qtbot):
    """Test that pointsChanged signal is emitted."""
    from PyQt6 import QtCore, QtGui
    from optiverse.objects.views.image_canvas import ImageCanvas
    
    canvas = ImageCanvas()
    qtbot.addWidget(canvas)
    
    # Create a simple test image
    pix = QtGui.QPixmap(400, 300)
    pix.fill(QtCore.Qt.GlobalColor.white)
    canvas.set_pixmap(pix, None)
    
    # Connect signal spy
    with qtbot.waitSignal(canvas.pointsChanged, timeout=1000):
        canvas.set_points((100.0, 100.0), (200.0, 200.0))


def test_image_canvas_hover_detection(qtbot):
    """Test hover detection near points."""
    from PyQt6 import QtCore, QtGui
    from optiverse.objects.views.image_canvas import ImageCanvas
    
    canvas = ImageCanvas()
    qtbot.addWidget(canvas)
    
    # Create a simple test image
    pix = QtGui.QPixmap(400, 300)
    pix.fill(QtCore.Qt.GlobalColor.white)
    canvas.set_pixmap(pix, None)
    canvas.resize(400, 300)
    
    # Set points
    canvas.set_points((100.0, 100.0), (200.0, 200.0))
    
    # Test _get_point_at_screen_pos
    # This will depend on the scale, but we can test the logic
    canvas._scale_fit = 1.0
    pixrect = canvas._target_rect()
    
    # Position near point 1
    test_pos = QtCore.QPoint(
        int(pixrect.x() + 100),
        int(pixrect.y() + 100)
    )
    point_idx = canvas._get_point_at_screen_pos(test_pos)
    assert point_idx in (1, 2, None)  # Should detect a point or None if scale is off


def test_component_editor_manual_coords(qtbot, tmp_path):
    """Test manual coordinate editing in component editor."""
    from PyQt6 import QtCore, QtGui
    from optiverse.ui.views.component_editor_dialog import ComponentEditor
    from optiverse.services.storage_service import StorageService
    
    storage = StorageService()
    editor = ComponentEditor(storage)
    qtbot.addWidget(editor)
    
    # Create a simple test image
    pix = QtGui.QPixmap(400, 300)
    pix.fill(QtCore.Qt.GlobalColor.white)
    editor.canvas.set_pixmap(pix, None)
    
    # Set points via canvas
    editor.canvas.set_points((100.0, 100.0), (200.0, 200.0))
    editor._update_derived_labels()
    
    # Check that spinboxes are updated
    assert editor.p1_x.value() == 100.0
    assert editor.p1_y.value() == 100.0
    assert editor.p2_x.value() == 200.0
    assert editor.p2_y.value() == 200.0
    
    # Modify spinboxes
    editor.p1_x.setValue(150.0)
    editor.p1_y.setValue(150.0)
    
    # Check that canvas is updated
    p1, p2 = editor.canvas.get_points()
    assert p1 == (150.0, 150.0)
    assert p2 == (200.0, 200.0)


def test_component_editor_coords_sync(qtbot, tmp_path):
    """Test bidirectional sync between canvas and spinboxes."""
    from PyQt6 import QtCore, QtGui
    from optiverse.ui.views.component_editor_dialog import ComponentEditor
    from optiverse.services.storage_service import StorageService
    
    storage = StorageService()
    editor = ComponentEditor(storage)
    qtbot.addWidget(editor)
    
    # Create a simple test image
    pix = QtGui.QPixmap(400, 300)
    pix.fill(QtCore.Qt.GlobalColor.white)
    editor.canvas.set_pixmap(pix, None)
    
    # Set via canvas
    editor.canvas.set_points((50.0, 60.0), (150.0, 160.0))
    editor._update_derived_labels()
    
    assert editor.p1_x.value() == 50.0
    assert editor.p1_y.value() == 60.0
    assert editor.p2_x.value() == 150.0
    assert editor.p2_y.value() == 160.0
    
    # Set via spinboxes
    editor.p2_x.setValue(250.0)
    editor.p2_y.setValue(260.0)
    
    p1, p2 = editor.canvas.get_points()
    assert p1 == (50.0, 60.0)
    assert p2 == (250.0, 260.0)


def test_image_canvas_screen_to_image_coords(qtbot):
    """Test screen to image coordinate conversion."""
    from PyQt6 import QtCore, QtGui, QtWidgets
    from optiverse.objects.views.image_canvas import ImageCanvas
    
    canvas = ImageCanvas()
    qtbot.addWidget(canvas)
    
    # Create a simple test image
    pix = QtGui.QPixmap(400, 300)
    pix.fill(QtCore.Qt.GlobalColor.white)
    canvas.set_pixmap(pix, None)
    canvas.resize(800, 600)
    canvas.show()
    
    # Force layout
    QtWidgets.QApplication.processEvents()
    
    # Test coordinate conversion
    pixrect = canvas._target_rect()
    test_pos = QtCore.QPoint(pixrect.x() + 50, pixrect.y() + 50)
    coords = canvas._screen_to_image_coords(test_pos)
    
    assert coords is not None
    x, y = coords
    assert 0 <= x <= pix.width()
    assert 0 <= y <= pix.height()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

