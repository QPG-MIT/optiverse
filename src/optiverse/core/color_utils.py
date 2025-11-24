from __future__ import annotations

import numpy as np
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
    except (TypeError, ValueError):
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


def wavelength_to_rgb(wavelength_nm: float) -> tuple[int, int, int]:
    """
    Convert wavelength in nanometers to RGB color.
    
    Uses a physically-inspired approximation of the visible spectrum.
    Based on the CIE color matching functions approximation.
    
    Args:
        wavelength_nm: Wavelength in nanometers (typically 380-750 nm)
        
    Returns:
        RGB tuple with values 0-255
        
    References:
        Approximation based on Dan Bruton's algorithm with improvements
    """
    # Clamp to visible range
    wl = float(wavelength_nm)
    
    # Define the visible spectrum boundaries
    if wl < 380:
        # UV -> violet
        return (138, 43, 226)  # Blue-violet
    elif wl >= 380 and wl < 440:
        # Violet to Blue
        attenuation = 0.3 + 0.7 * (wl - 380) / (440 - 380)
        r = ((-(wl - 440) / (440 - 380)) * attenuation) ** 0.8
        g = 0.0
        b = (1.0 * attenuation) ** 0.8
    elif wl >= 440 and wl < 490:
        # Blue to Cyan
        r = 0.0
        g = ((wl - 440) / (490 - 440)) ** 0.8
        b = 1.0
    elif wl >= 490 and wl < 510:
        # Cyan to Green
        r = 0.0
        g = 1.0
        b = (-(wl - 510) / (510 - 490)) ** 0.8
    elif wl >= 510 and wl < 580:
        # Green to Yellow
        r = ((wl - 510) / (580 - 510)) ** 0.8
        g = 1.0
        b = 0.0
    elif wl >= 580 and wl < 645:
        # Yellow to Orange to Red
        r = 1.0
        g = (-(wl - 645) / (645 - 580)) ** 0.8
        b = 0.0
    elif wl >= 645 and wl <= 750:
        # Red
        attenuation = 0.3 + 0.7 * (750 - wl) / (750 - 645)
        r = (1.0 * attenuation) ** 0.8
        g = 0.0
        b = 0.0
    else:
        # IR -> deep red
        return (139, 0, 0)  # Dark red
    
    # Convert to 0-255 range
    R = int(np.clip(r * 255, 0, 255))
    G = int(np.clip(g * 255, 0, 255))
    B = int(np.clip(b * 255, 0, 255))
    
    return (R, G, B)


def wavelength_to_hex(wavelength_nm: float) -> str:
    """
    Convert wavelength to hex color string.
    
    Args:
        wavelength_nm: Wavelength in nanometers
        
    Returns:
        Hex color string in format "#RRGGBB"
    """
    r, g, b = wavelength_to_rgb(wavelength_nm)
    return f"#{r:02x}{g:02x}{b:02x}"


def wavelength_to_qcolor(wavelength_nm: float) -> QtGui.QColor:
    """
    Convert wavelength to QColor.
    
    Args:
        wavelength_nm: Wavelength in nanometers
        
    Returns:
        QColor instance
    """
    r, g, b = wavelength_to_rgb(wavelength_nm)
    return QtGui.QColor(r, g, b)


# Common laser wavelengths (in nm) for reference
LASER_WAVELENGTHS = {
    "UV (355nm Nd:YAG 3rd)": 355.0,
    "Violet (405nm diode)": 405.0,
    "Blue (450nm diode)": 450.0,
    "Cyan (488nm Ar-ion)": 488.0,
    "Green (532nm Nd:YAG 2nd)": 532.0,
    "Yellow (589nm Na)": 589.0,
    "Red (633nm HeNe)": 632.8,
    "Deep Red (650nm diode)": 650.0,
    "IR (808nm diode)": 808.0,
    "IR (1064nm Nd:YAG)": 1064.0,
}

