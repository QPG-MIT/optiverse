"""Widget constants for Optiverse UI."""

from __future__ import annotations

# Z-Order
Z_ORDER_INITIAL_VALUE: float = 100.0
Z_ORDER_STEP: float = 1.0

# Ruler
RULER_SIZE: int = 25
RULER_TARGET_TICK_PIXELS: int = 75
RULER_DEFAULT_RANGE_MM: tuple[float, float] = (-50.0, 50.0)
RULER_INDICATOR_FILL: str = "#FF4444"
RULER_INDICATOR_STROKE: str = "#CC0000"
RULER_FONT_SIZE: int = 8
RULER_INDICATOR_TRIANGLE_SIZE: int = 5
RULER_INDICATOR_HEIGHT: int = 7
RULER_MAJOR_TICK_OFFSET: int = 5
RULER_MINOR_TICK_SIZE: int = 5
RULER_LABEL_WIDTH: int = 60
RULER_LABEL_HEIGHT: int = 12


class Icons:
    """Emoji icons used in the UI."""
    VISIBLE: str = "👁"
    HIDDEN: str = "○"
    LOCKED: str = "🔒"
    UNLOCKED: str = "🔓"
    FOLDER: str = "📁"
    FOLDER_ADD: str = "📁+"
    FOLDER_REMOVE: str = "📁-"
    N1_COLOR: str = "#FFD700"  # Gold
    N2_COLOR: str = "#9370DB"  # Purple


# Dropdown Options
PASS_TYPE_OPTIONS: list[str] = ["longpass", "shortpass"]
POLARIZER_SUBTYPE_OPTIONS: list[str] = ["waveplate", "linear_polarizer", "faraday_rotator"]

# Tree Widget
INTERFACE_TREE_INDENTATION: int = 10

# Layer Panel
TOGGLE_BUTTON_SIZE: int = 20
COLORED_CIRCLE_SIZE: int = 10
LAYER_ITEM_MARGIN: int = 2
LAYER_ITEM_SPACING: int = 4

# Property Forms
PROPERTY_FORM_VERTICAL_SPACING: int = 3
PROPERTY_FORM_HORIZONTAL_SPACING: int = 10
PROPERTY_FORM_LEFT_MARGIN: int = 15

# Interface Defaults
INTERFACE_DEFAULT_HALF_LENGTH_MM: float = 5.0
