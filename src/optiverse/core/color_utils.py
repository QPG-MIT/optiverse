from __future__ import annotations

from PyQt6 import QtGui


def qcolor_from_hex(h: str, fallback: str = "#DC143C") -> QtGui.QColor:
    """
    Convert hex color string to QColor.
    
    Args:
        h: Hex color string (e.g., "#DC143C")
        fallback: Fallback hex string if h is invalid
        
    Returns:
        QColor instance
    """
    try:
        c = QtGui.QColor(h)
        return c if c.isValid() else QtGui.QColor(fallback)
    except Exception:
        return QtGui.QColor(fallback)


def hex_from_qcolor(c: QtGui.QColor) -> str:
    """
    Convert QColor to hex color string.
    
    Args:
        c: QColor instance
        
    Returns:
        Hex color string in format "#RRGGBB"
    """
    return c.name()  # Returns #RRGGBB format

