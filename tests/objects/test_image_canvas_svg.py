"""Tests for ImageCanvas and ComponentSprite SVG support."""
import pytest
import os

# Note: These tests require PyQt6 and PyQt6-SVG to be properly installed
# They may be skipped if dependencies are missing

try:
    from PyQt6 import QtCore, QtGui, QtWidgets, QtSvg
    from PyQt6.QtSvgWidgets import QGraphicsSvgItem
    HAVE_PYQT6 = True
    HAVE_SVG = True
except ImportError:
    HAVE_PYQT6 = False
    HAVE_SVG = False


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_imagecanvas_native_svg_rendering(qtbot, tmp_path):
    """Test that ImageCanvas uses native SVG renderer when available."""
    from optiverse.objects.views.image_canvas import ImageCanvas

    canvas = ImageCanvas()
    qtbot.addWidget(canvas)

    # Create a simple SVG file
    svg_content = '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>'''
    svg_file = tmp_path / "test.svg"
    svg_file.write_text(svg_content)

    # Load SVG as pixmap (for backward compatibility)
    from PyQt6.QtSvg import QSvgRenderer
    renderer = QSvgRenderer(str(svg_file))
    pix = QtGui.QPixmap(100, 100)
    pix.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pix)
    renderer.render(painter)
    painter.end()

    # Set pixmap with SVG source path
    canvas.set_pixmap(pix, str(svg_file))

    # Verify that native SVG renderer is stored
    if HAVE_SVG:
        assert canvas._svg_renderer is not None
        assert canvas._svg_renderer.isValid()

    # Verify pixmap is still available for export
    assert canvas.current_pixmap() is not None


@pytest.mark.skipif(not HAVE_SVG, reason="QtSvg not available")
def test_component_sprite_factory(qtbot, tmp_path):
    """Test that create_component_sprite factory chooses correct sprite type."""
    from optiverse.objects.component_sprite import create_component_sprite, ComponentSprite, ComponentSvgSprite

    # Create test SVG file
    svg_content = '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="50" r="40" fill="red"/>
</svg>'''
    svg_file = tmp_path / "test_sprite.svg"
    svg_file.write_text(svg_content)

    # Create PNG file for comparison
    png_file = tmp_path / "test_sprite.png"
    pix = QtGui.QPixmap(100, 100)
    pix.fill(QtCore.Qt.GlobalColor.white)
    pix.save(str(png_file), "PNG")

    # Create parent item
    scene = QtWidgets.QGraphicsScene()
    parent = QtWidgets.QGraphicsRectItem(0, 0, 10, 10)
    scene.addItem(parent)

    # Test SVG sprite creation
    svg_sprite = create_component_sprite(
        str(svg_file),
        (-5.0, 0.0, 5.0, 0.0),  # reference line
        10.0,  # object height
        parent
    )

    # Verify SVG sprite type
    assert isinstance(svg_sprite, ComponentSvgSprite)
    assert svg_sprite.picked_line_length_mm > 0

    # Test PNG sprite creation
    png_sprite = create_component_sprite(
        str(png_file),
        (-5.0, 0.0, 5.0, 0.0),
        10.0,
        parent
    )

    # Verify PNG sprite type
    assert isinstance(png_sprite, ComponentSprite)
    assert not isinstance(png_sprite, ComponentSvgSprite)


@pytest.mark.skipif(not HAVE_SVG, reason="QtSvg not available")
def test_component_svg_sprite_coordinate_transform(qtbot, tmp_path):
    """Test that ComponentSvgSprite applies same coordinate transforms as ComponentSprite."""
    from optiverse.objects.component_sprite import ComponentSvgSprite

    # Create test SVG
    svg_content = '''<?xml version="1.0"?>
<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect width="200" height="100" fill="green"/>
</svg>'''
    svg_file = tmp_path / "test_coords.svg"
    svg_file.write_text(svg_content)

    # Create parent item
    scene = QtWidgets.QGraphicsScene()
    parent = QtWidgets.QGraphicsRectItem(0, 0, 10, 10)
    scene.addItem(parent)

    # Create sprite with specific reference line
    reference_line = (-10.0, -5.0, 10.0, 5.0)  # Diagonal line
    sprite = ComponentSvgSprite(
        str(svg_file),
        reference_line,
        100.0,  # object height
        parent
    )

    # Verify sprite is created and visible
    assert sprite.isVisible()
    assert sprite.picked_line_length_mm > 0

    # Verify coordinate transforms are applied (Y-flip)
    transform = sprite.transform()
    # Check that Y is flipped (m22 should be negative)
    assert transform.m22() < 0


@pytest.mark.skipif(not HAVE_SVG, reason="QtSvg not available")
def test_multiline_canvas_svg_rendering(qtbot, tmp_path):
    """Test that MultiLineCanvas uses native SVG renderer."""
    from optiverse.objects.views.multi_line_canvas import MultiLineCanvas

    canvas = MultiLineCanvas()
    qtbot.addWidget(canvas)

    # Create SVG file
    svg_content = '''<?xml version="1.0"?>
<svg width="150" height="150" xmlns="http://www.w3.org/2000/svg">
    <polygon points="75,0 150,150 0,150" fill="yellow"/>
</svg>'''
    svg_file = tmp_path / "test_multi.svg"
    svg_file.write_text(svg_content)

    # Load as pixmap
    from PyQt6.QtSvg import QSvgRenderer
    renderer = QSvgRenderer(str(svg_file))
    pix = QtGui.QPixmap(150, 150)
    pix.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pix)
    renderer.render(painter)
    painter.end()

    # Set pixmap with SVG source
    canvas.set_pixmap(pix, str(svg_file))

    # Verify SVG renderer is stored
    if HAVE_SVG:
        assert canvas._svg_renderer is not None
        assert canvas._svg_renderer.isValid()


@pytest.mark.skipif(not HAVE_SVG, reason="QtSvg not available")
def test_render_svg_to_pixmap_fallback(tmp_path):
    """Test SVG rendering to pixmap fallback (for backward compatibility)."""
    from optiverse.objects.views.image_canvas import ImageCanvas

    svg_content = '''<?xml version="1.0"?>
<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <circle cx="100" cy="100" r="50" fill="red"/>
</svg>'''
    svg_file = tmp_path / "circle.svg"
    svg_file.write_text(svg_content)

    # Test static method (fallback for export/save operations)
    pix = ImageCanvas._render_svg_to_pixmap(str(svg_file))

    if HAVE_SVG:
        assert pix is not None
        assert not pix.isNull()
        assert pix.width() > 0
        assert pix.height() > 0


@pytest.mark.skipif(not HAVE_SVG, reason="QtSvg not available")
def test_render_svg_from_bytes():
    """Test SVG rendering from bytes."""
    from optiverse.objects.views.image_canvas import ImageCanvas

    svg_bytes = b'''<?xml version="1.0"?>
<svg width="50" height="50" xmlns="http://www.w3.org/2000/svg">
    <rect width="50" height="50" fill="green"/>
</svg>'''

    pix = ImageCanvas._render_svg_to_pixmap(svg_bytes)

    if HAVE_SVG:
        assert pix is not None
        assert not pix.isNull()



