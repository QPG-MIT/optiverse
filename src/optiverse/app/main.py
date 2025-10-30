from __future__ import annotations

import sys
from PyQt6 import QtCore, QtGui, QtWidgets
from ..ui.views.main_window import MainWindow


def get_dark_stylesheet() -> str:
    """Get the dark mode stylesheet."""
    return """
    QMainWindow, QWidget {
        background-color: #1a1c21;
        color: white;
    }
    
    QGraphicsView {
        background-color: #1a1c21;
        border: none;
    }
    
    QMenu {
        background-color: #1a1c21;
        color: white;
        border: 1px solid #3d3f46;
    }
    
    QMenu::item:selected {
        background-color: #2d2f36;
    }
    
    QToolBar {
        background-color: #1a1c21;
        border: none;
        spacing: 3px;
    }
    
    QToolBar QToolButton {
        background-color: transparent;
        border: none;
        padding: 3px;
    }
    
    QToolBar QToolButton:hover {
        background-color: #2d2f36;
        border-radius: 3px;
    }
    
    QToolBar QToolButton:pressed {
        background-color: #23252b;
        border-radius: 3px;
    }
    
    QStatusBar {
        background-color: #1a1c21;
        color: white;
    }
    
    QDockWidget {
        background-color: #1a1c21;
        color: white;
        titlebar-close-icon: url(close.png);
        titlebar-normal-icon: url(float.png);
    }
    
    QDockWidget::title {
        background-color: #2d2f36;
        padding: 4px;
    }
    
    QTreeWidget {
        background-color: #1a1c21;
        color: white;
        border: 1px solid #3d3f46;
        alternate-background-color: #23252b;
    }
    
    QTreeWidget::item:selected {
        background-color: #2d2f36;
    }
    
    QTreeWidget::item:hover {
        background-color: #26282e;
    }
    
    QPushButton {
        background-color: #2d2f36;
        color: white;
        border: 1px solid #3d3f46;
        padding: 5px 15px;
        border-radius: 3px;
    }
    
    QPushButton:hover {
        background-color: #3d3f46;
    }
    
    QPushButton:pressed {
        background-color: #23252b;
    }
    
    QLineEdit, QComboBox {
        background-color: #2d2f36;
        color: white;
        border: 1px solid #3d3f46;
        padding: 3px;
        border-radius: 3px;
    }
    
    QLineEdit:focus, QComboBox:focus {
        border: 1px solid #5d5f66;
    }
    
    QLabel {
        color: white;
    }
    
    QCheckBox {
        color: white;
    }
    
    QRadioButton {
        color: white;
    }
    
    QGroupBox {
        color: white;
        border: 1px solid #3d3f46;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        color: white;
    }
    
    QScrollBar:vertical {
        background-color: #1a1c21;
        width: 12px;
        border: none;
    }
    
    QScrollBar::handle:vertical {
        background-color: #3d3f46;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #4d4f56;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        background-color: #1a1c21;
        height: 12px;
        border: none;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #3d3f46;
        border-radius: 6px;
        min-width: 20px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #4d4f56;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    QTabWidget::pane {
        border: 1px solid #3d3f46;
        background-color: #1a1c21;
    }
    
    QTabBar::tab {
        background-color: #2d2f36;
        color: white;
        padding: 8px 16px;
        border: 1px solid #3d3f46;
    }
    
    QTabBar::tab:selected {
        background-color: #1a1c21;
        border-bottom: none;
    }
    
    QTabBar::tab:hover {
        background-color: #3d3f46;
    }
    
    QDialog {
        background-color: #1a1c21;
        color: white;
    }
    
    QTextEdit, QPlainTextEdit {
        background-color: #2d2f36;
        color: white;
        border: 1px solid #3d3f46;
        border-radius: 3px;
    }
    """


def get_light_stylesheet() -> str:
    """Get the light mode stylesheet."""
    return """
    QMainWindow, QWidget {
        background-color: white;
        color: black;
    }
    
    QGraphicsView {
        background-color: white;
        border: none;
    }
    
    QMenu {
        background-color: white;
        color: black;
        border: 1px solid #c0c0c0;
    }
    
    QMenu::item:selected {
        background-color: #e0e0e0;
    }
    
    QToolBar {
        background-color: #f0f0f0;
        border: none;
        spacing: 3px;
    }
    
    QToolBar QToolButton {
        background-color: transparent;
        color: black;
        border: none;
        padding: 3px;
    }
    
    QToolBar QToolButton:hover {
        background-color: #e0e0e0;
        color: black;
        border-radius: 3px;
    }
    
    QToolBar QToolButton:pressed {
        background-color: #d0d0d0;
        color: black;
        border-radius: 3px;
    }
    
    QStatusBar {
        background-color: #f0f0f0;
        color: black;
    }
    
    QDockWidget {
        background-color: white;
        color: black;
    }
    
    QDockWidget::title {
        background-color: #e0e0e0;
        padding: 4px;
    }
    
    QTreeWidget {
        background-color: white;
        color: black;
        border: 1px solid #c0c0c0;
        alternate-background-color: #f8f8f8;
    }
    
    QTreeWidget::item:selected {
        background-color: #cce8ff;
    }
    
    QTreeWidget::item:hover {
        background-color: #e6f2ff;
    }
    
    QPushButton {
        background-color: #f0f0f0;
        color: black;
        border: 1px solid #c0c0c0;
        padding: 5px 15px;
        border-radius: 3px;
    }
    
    QPushButton:hover {
        background-color: #e0e0e0;
    }
    
    QPushButton:pressed {
        background-color: #d0d0d0;
    }
    
    QLineEdit, QComboBox {
        background-color: white;
        color: black;
        border: 1px solid #c0c0c0;
        padding: 3px;
        border-radius: 3px;
    }
    
    QLineEdit:focus, QComboBox:focus {
        border: 1px solid #4a90e2;
    }
    
    QLabel {
        color: black;
    }
    
    QCheckBox {
        color: black;
    }
    
    QRadioButton {
        color: black;
    }
    
    QGroupBox {
        color: black;
        border: 1px solid #c0c0c0;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        color: black;
    }
    
    QScrollBar:vertical {
        background-color: #f0f0f0;
        width: 12px;
        border: none;
    }
    
    QScrollBar::handle:vertical {
        background-color: #c0c0c0;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #a0a0a0;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        background-color: #f0f0f0;
        height: 12px;
        border: none;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #c0c0c0;
        border-radius: 6px;
        min-width: 20px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #a0a0a0;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    QTabWidget::pane {
        border: 1px solid #c0c0c0;
        background-color: white;
    }
    
    QTabBar::tab {
        background-color: #e0e0e0;
        color: black;
        padding: 8px 16px;
        border: 1px solid #c0c0c0;
    }
    
    QTabBar::tab:selected {
        background-color: white;
        border-bottom: none;
    }
    
    QTabBar::tab:hover {
        background-color: #f0f0f0;
    }
    
    QDialog {
        background-color: white;
        color: black;
    }
    
    QTextEdit, QPlainTextEdit {
        background-color: white;
        color: black;
        border: 1px solid #c0c0c0;
        border-radius: 3px;
    }
    """


def detect_system_dark_mode() -> bool:
    """Detect if the system is in dark mode."""
    try:
        # Use Qt's palette to detect dark mode
        palette = QtWidgets.QApplication.palette()
        bg_color = palette.color(QtGui.QPalette.ColorRole.Window)
        # If background is dark (low lightness), we're in dark mode
        return bg_color.lightness() < 128
    except Exception:
        return False


def apply_theme(dark_mode: bool):
    """Apply the appropriate stylesheet based on dark mode setting."""
    app = QtWidgets.QApplication.instance()
    if app:
        # Create a palette to override system colors
        palette = QtGui.QPalette()
        
        if dark_mode:
            # Dark mode colors
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
            app.setStyleSheet(get_dark_stylesheet())
        else:
            # Light mode colors
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
            app.setStyleSheet(get_light_stylesheet())
        
        # Apply the palette to override system colors
        app.setPalette(palette)
        
        # Force complete style refresh to override macOS system styling
        # This is critical on Mac where system dark mode can conflict with app theme
        for widget in app.allWidgets():
            # Force each widget to recompute its style
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()


def main() -> int:
    # On macOS, change sys.argv[0] to set the app name in the menu bar
    # This must be done BEFORE creating QApplication
    original_argv0 = sys.argv[0]
    sys.argv[0] = 'Optiverse'
    
    # Also try to set process name via pyobjc if available
    try:
        from Foundation import NSProcessInfo
        processInfo = NSProcessInfo.processInfo()
        processInfo.setProcessName_('Optiverse')
    except ImportError:
        pass
    
    # Minimal app that opens the main window (Qt6 enables high DPI by default)
    app = QtWidgets.QApplication(sys.argv)
    
    # Restore original argv[0] after QApplication creation in case something needs it
    sys.argv[0] = original_argv0
    
    # Set application name (for Qt internals and other purposes)
    app.setApplicationName("Optiverse")
    app.setApplicationDisplayName("Optiverse")
    app.setOrganizationName("Optiverse")
    
    # Set application icon
    from pathlib import Path
    icon_path = Path(__file__).parent.parent / "ui" / "icons" / "optiverse.png"
    if icon_path.exists():
        app.setWindowIcon(QtGui.QIcon(str(icon_path)))
    
    # Detect system dark mode and apply initial stylesheet
    # Note: MainWindow will load user preference and override if needed
    system_dark_mode = detect_system_dark_mode()
    apply_theme(system_dark_mode)
    
    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


