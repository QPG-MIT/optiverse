"""Tests for ImageCanvas SVG support."""
import pytest

# Note: These tests require PyQt6 and PyQt6-SVG to be properly installed
# They may be skipped if dependencies are missing

try:
    from PyQt6 import QtCore, QtGui, QtWidgets, QtSvg
    HAVE_PYQT6 = True
    HAVE_SVG = True
except ImportError:
    HAVE_PYQT6 = False
    HAVE_SVG = False


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_imagecanvas_can_drop_svg_file(qtbot, tmp_path):
    """Test that ImageCanvas can handle SVG file drops."""
    from optiverse.widgets.image_canvas import ImageCanvas
    
    canvas = ImageCanvas()
    qtbot.addWidget(canvas)
    
    # Create a simple SVG file
    svg_content = '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>'''
    svg_file = tmp_path / "test.svg"
    svg_file.write_text(svg_content)
    
    # Simulate drop event
    mime_data = QtCore.QMimeData()
    url = QtCore.QUrl.fromLocalFile(str(svg_file))
    mime_data.setUrls([url])
    
    drop_event = QtGui.QDropEvent(
        QtCore.QPointF(50, 50),
        QtCore.Qt.DropAction.CopyAction,
        mime_data,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.NoModifier
    )
    
    # Test that canvas accepts and processes the drop
    # (Implementation should emit imageDropped signal)
    # Note: Actual testing would require more sophisticated event simulation


@pytest.mark.skipif(not HAVE_SVG, reason="QtSvg not available")
def test_render_svg_to_pixmap(tmp_path):
    """Test SVG rendering to pixmap."""
    from optiverse.widgets.image_canvas import ImageCanvas
    
    svg_content = '''<?xml version="1.0"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <circle cx="100" cy="100" r="50" fill="red"/>
</svg>'''
    svg_file = tmp_path / "circle.svg"
    svg_file.write_text(svg_content)
    
    # Test static method
    pix = ImageCanvas._render_svg_to_pixmap(str(svg_file))
    
    if HAVE_SVG:
        assert pix is not None
        assert not pix.isNull()
        assert pix.width() > 0
        assert pix.height() > 0


@pytest.mark.skipif(not HAVE_SVG, reason="QtSvg not available")
def test_render_svg_from_bytes():
    """Test SVG rendering from bytes."""
    from optiverse.widgets.image_canvas import ImageCanvas
    
    svg_bytes = b'''<?xml version="1.0"?>
<svg width="50" height="50" xmlns="http://www.w3.org/2000/svg">
    <rect width="50" height="50" fill="green"/>
</svg>'''
    
    pix = ImageCanvas._render_svg_to_pixmap(svg_bytes)
    
    if HAVE_SVG:
        assert pix is not None
        assert not pix.isNull()

