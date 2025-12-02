"""
Theme Manager - Centralized theme and stylesheet management.

This module handles:
- Loading QSS stylesheets from files (with embedded fallback)
- Detecting system dark mode
- Applying themes application-wide
- Palette configuration for consistent colors
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

_logger = logging.getLogger(__name__)

# Path to styles directory
_STYLES_DIR = Path(__file__).parent / "styles"


# ============================================================================
# Embedded Stylesheets (fallback if files don't exist)
# ============================================================================

_DARK_STYLESHEET_FALLBACK = """
QMainWindow { background-color: #1a1c21; color: white; }
QGraphicsView { background-color: #1a1c21; border: none; }
QMenuBar { background-color: #1a1c21; color: white; border: none; }
QToolBar { background-color: #1a1c21; border: none; }
QStatusBar { background-color: #1a1c21; color: white; }
QDockWidget { background-color: #1a1c21; color: white; }
QTreeWidget { background-color: #1a1c21; color: white; border: 1px solid #3d3f46; }
QPushButton {
    background-color: #2d2f36; color: white; border: 1px solid #3d3f46;
    padding: 5px 15px; border-radius: 3px;
}
QLineEdit, QComboBox {
    background-color: #2d2f36; color: white; border: 1px solid #3d3f46;
    padding: 3px; border-radius: 3px;
}
QLabel { color: white; }
QDialog { background-color: #1a1c21; color: white; }
"""

_LIGHT_STYLESHEET_FALLBACK = """
QMainWindow { background-color: white; color: black; }
QGraphicsView { background-color: white; border: none; }
QMenuBar { background-color: #f0f0f0; color: black; border: none; }
QToolBar { background-color: #f0f0f0; border: none; }
QStatusBar { background-color: #f0f0f0; color: black; }
QDockWidget { background-color: white; color: black; }
QTreeWidget { background-color: white; color: black; border: 1px solid #c0c0c0; }
QPushButton {
    background-color: #f0f0f0; color: black; border: 1px solid #c0c0c0;
    padding: 5px 15px; border-radius: 3px;
}
QLineEdit, QComboBox {
    background-color: white; color: black; border: 1px solid #c0c0c0;
    padding: 3px; border-radius: 3px;
}
QLabel { color: black; }
QDialog { background-color: white; color: black; }
"""


# ============================================================================
# Stylesheet Loading
# ============================================================================


def _load_stylesheet_from_file(filename: str) -> str | None:
    """
    Load a stylesheet from the styles directory.

    Args:
        filename: Name of the QSS file (e.g., "dark_theme.qss")

    Returns:
        Stylesheet content if file exists, None otherwise
    """
    filepath = _STYLES_DIR / filename
    if filepath.exists():
        try:
            return filepath.read_text(encoding="utf-8")
        except OSError as e:
            _logger.warning("Failed to read stylesheet %s: %s", filepath, e)
    return None


def get_dark_stylesheet() -> str:
    """
    Get the dark mode stylesheet.

    Tries to load from file first, falls back to embedded version.

    Returns:
        Dark theme stylesheet string
    """
    stylesheet = _load_stylesheet_from_file("dark_theme.qss")
    if stylesheet:
        _logger.debug("Loaded dark theme from file")
        return stylesheet
    _logger.debug("Using embedded dark theme fallback")
    return _DARK_STYLESHEET_FALLBACK


def get_light_stylesheet() -> str:
    """
    Get the light mode stylesheet.

    Tries to load from file first, falls back to embedded version.

    Returns:
        Light theme stylesheet string
    """
    stylesheet = _load_stylesheet_from_file("light_theme.qss")
    if stylesheet:
        _logger.debug("Loaded light theme from file")
        return stylesheet
    _logger.debug("Using embedded light theme fallback")
    return _LIGHT_STYLESHEET_FALLBACK


# ============================================================================
# System Theme Detection
# ============================================================================


def detect_system_dark_mode() -> bool:
    """
    Detect if the system is in dark mode.

    Uses Qt's palette to determine if the system theme is dark.

    Returns:
        True if system is in dark mode, False otherwise
    """
    try:
        palette = QtWidgets.QApplication.palette()
        bg_color = palette.color(QtGui.QPalette.ColorRole.Window)
        # If background is dark (low lightness), we're in dark mode
        return bg_color.lightness() < 128
    except (AttributeError, RuntimeError):
        return False


# ============================================================================
# Theme Application
# ============================================================================


def _create_dark_palette() -> QtGui.QPalette:
    """Create a QPalette configured for dark mode."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#1a1c21"))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("white"))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#2d2f36"))
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#23252b"))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("white"))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#2d2f36"))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("white"))
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor("white"))
    palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor("#6495ff"))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#2d2f36"))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("white"))
    return palette


def _create_light_palette() -> QtGui.QPalette:
    """Create a QPalette configured for light mode."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("white"))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("black"))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("white"))
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#f8f8f8"))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("black"))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#f0f0f0"))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("black"))
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor("black"))
    palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor("#4a90e2"))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#cce8ff"))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("black"))
    return palette


def apply_theme(dark_mode: bool) -> None:
    """
    Apply the appropriate theme (stylesheet + palette) based on dark mode setting.

    This function:
    1. Sets the appropriate stylesheet
    2. Configures the application palette
    3. Forces a complete style refresh on all widgets

    Args:
        dark_mode: True for dark theme, False for light theme
    """
    app = QtWidgets.QApplication.instance()
    if not app or not isinstance(app, QtWidgets.QApplication):
        _logger.warning("No QApplication instance - cannot apply theme")
        return

    # Apply stylesheet and palette
    if dark_mode:
        app.setStyleSheet(get_dark_stylesheet())
        app.setPalette(_create_dark_palette())
        _logger.info("Applied dark theme")
    else:
        app.setStyleSheet(get_light_stylesheet())
        app.setPalette(_create_light_palette())
        _logger.info("Applied light theme")

    # Force complete style refresh to override macOS system styling
    # This is critical on Mac where system dark mode can conflict with app theme
    for widget in app.allWidgets():
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)
        widget.update()


def is_dark_mode() -> bool:
    """
    Check if the application is currently in dark mode.

    Returns:
        True if dark mode is active, False otherwise
    """
    try:
        app = QtWidgets.QApplication.instance()
        if not app or not isinstance(app, QtWidgets.QApplication):
            return False
        palette = app.palette()
        bg_color = palette.color(QtGui.QPalette.ColorRole.Window)
        lightness: int = bg_color.lightness()
        return lightness < 128
    except (AttributeError, RuntimeError):
        return False


def question(
    parent: QtWidgets.QWidget | None,
    title: str,
    text: str,
    buttons: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.StandardButton.Yes
    | QtWidgets.QMessageBox.StandardButton.No,
    default_button: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.StandardButton.No,
) -> QtWidgets.QMessageBox.StandardButton:
    """
    Show a question dialog with theme-aware icon colors.

    This is a drop-in replacement for QMessageBox.question that ensures
    the question mark icon is visible in dark mode.

    Args:
        parent: Parent widget
        title: Dialog title
        text: Message text
        buttons: Standard buttons to show
        default_button: Default button

    Returns:
        The button that was pressed
    """
    msg_box = QtWidgets.QMessageBox(parent)
    msg_box.setIcon(QtWidgets.QMessageBox.Icon.Question)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStandardButtons(buttons)
    msg_box.setDefaultButton(default_button)

    # Center align the text label
    text_label = msg_box.findChild(QtWidgets.QLabel, "qt_msgbox_label")
    if text_label is not None:
        text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    # In dark mode, invert the icon to make it visible
    if is_dark_mode():
        # Get the standard icon from QStyle
        style = msg_box.style()
        if style is not None:
            # Get the standard pixmap for Question icon
            standard_pixmap = style.standardPixmap(
                QtWidgets.QStyle.StandardPixmap.SP_MessageBoxQuestion, None, msg_box
            )
            if standard_pixmap is not None and not standard_pixmap.isNull():
                # Create inverted pixmap using QImage transformation
                img = standard_pixmap.toImage()
                img.invertPixels(QtGui.QImage.InvertMode.InvertRgb)  # Invert RGB, preserve alpha
                inverted_pixmap = QtGui.QPixmap.fromImage(img)
                msg_box.setIconPixmap(inverted_pixmap)

    result: int = msg_box.exec()
    return QtWidgets.QMessageBox.StandardButton(result)
