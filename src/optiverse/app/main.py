from __future__ import annotations

import os
import sys
from PyQt6 import QtCore, QtGui, QtWidgets
from ..ui.views.main_window import MainWindow


def get_dark_stylesheet() -> str:
    """Get the dark mode stylesheet."""
    return """
    QMainWindow {
        background-color: #1a1c21;
        color: white;
    }
    
    QGraphicsView {
        background-color: #1a1c21;
        border: none;
    }
    

    QMenuBar {
        background-color: #1a1c21;
        color: white;
        border: none;
    }
    QMenuBar::item {
        background: transparent;
        padding: 4px 8px;
        color: white;
    }
    QMenuBar::item:selected {
        background-color: #2d2f36;
        border-radius: 3px;
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
    QMainWindow {
        background-color: white;
        color: black;
    }
    
    QGraphicsView {
        background-color: white;
        border: none;
    }
    

    QMenuBar {
        background-color: #f0f0f0;
        color: black;
        border: none;
    }
    QMenuBar::item {
        background: transparent;
        padding: 4px 8px;
        color: black;
    }
    QMenuBar::item:selected {
        background-color: #e0e0e0;
        border-radius: 3px;
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
        
        # More efficient style refresh - only update top-level windows
        # Setting the palette and stylesheet will cascade to child widgets automatically
        # We only need to explicitly update top-level windows
        for widget in app.topLevelWidgets():
            # Force each top-level widget to recompute its style
            # This will cascade to all child widgets automatically
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()


def main() -> int:
    # Increase Qt's image allocation limit to support large SVG cache files
    # Default is 256MB, we set to 1GB to allow high-resolution cached PNGs
    # This must be set BEFORE creating QApplication
    os.environ['QT_IMAGEIO_MAXALLOC'] = '1024'  # In MB
    
    # Configure OpenGL surface format BEFORE creating QApplication
    # This ensures all OpenGL widgets use the same format with antialiasing
    try:
        fmt = QtGui.QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        fmt.setStencilBufferSize(8)
        fmt.setSamples(4)  # 4x MSAA for antialiasing
        fmt.setVersion(2, 1)  # OpenGL 2.1 for macOS compatibility
        fmt.setProfile(QtGui.QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        fmt.setAlphaBufferSize(8)  # Enable alpha channel for transparency
        QtGui.QSurfaceFormat.setDefaultFormat(fmt)
        print("✅ OpenGL surface format configured: 4x MSAA, OpenGL 2.1")
    except Exception as e:
        print(f"⚠️  Failed to configure OpenGL format: {e}")
    
    # On macOS, set the app name in the menu bar
    # Multiple approaches are needed because macOS is finicky about this
    
    # Method 1: Change sys.argv[0] BEFORE creating QApplication
    original_argv0 = sys.argv[0]
    sys.argv[0] = 'Optiverse'
    
    # Method 2: Use pyobjc to set process name (macOS only)
    try:
        from Foundation import NSProcessInfo
        processInfo = NSProcessInfo.processInfo()
        processInfo.setProcessName_('Optiverse')
        print("✅ macOS process name set to 'Optiverse' via pyobjc")
    except ImportError:
        print("⚠️  pyobjc not available - app name in menu bar may show as 'Python'")
    except Exception as e:
        print(f"⚠️  Failed to set macOS process name: {e}")
    
    # Minimal app that opens the main window (Qt6 enables high DPI by default)
    app = QtWidgets.QApplication(sys.argv)
    
    # Restore original argv[0] after QApplication creation
    sys.argv[0] = original_argv0
    
    # Method 3: Set Qt application metadata
    app.setApplicationName("Optiverse")
    app.setApplicationDisplayName("Optiverse")
    app.setOrganizationName("Optiverse")
    app.setOrganizationDomain("optiverse.app")
    
    # Method 4: Try to set macOS NSApp activation policy after QApplication is created
    try:
        from AppKit import NSRunningApplication
        NSRunningApplication.currentApplication().activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
        print("✅ macOS NSApp activation configured")
    except Exception as e:
        print(f"⚠️  Failed to configure NSApp: {e}")
    
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


