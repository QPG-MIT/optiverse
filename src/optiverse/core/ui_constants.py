"""
UI-specific constants for user interaction and visual feedback.

This module centralizes magic numbers used in UI interactions, hit testing,
and visual feedback across the application.
"""

# ========== Click/Hit Testing Tolerances (pixels) ==========

# Tolerance for inspect tool ray selection
INSPECT_TOOL_TOLERANCE_PX = 15.0

# Tolerance for path measure tool ray selection (more generous)
PATH_MEASURE_TOLERANCE_PX = 25.0

# Minimum scale factor to prevent division by zero
MIN_SCALE_FACTOR = 0.01

# ========== Ray/Path Detection Thresholds (millimeters) ==========

# Threshold for detecting beam splitter siblings (same starting point)
BEAM_SPLITTER_SIBLING_THRESHOLD_MM = 1.0

# Threshold for parallel bundle detection in path measure tool
PARALLEL_BUNDLE_THRESHOLD_MM = 15.0

# ========== Shape Geometry Padding (pixels) ==========

# Padding added to sprite shape for hit testing
SPRITE_SHAPE_PADDING_PX = 1.0

# Padding added to bounding rect for sprite
SPRITE_BOUNDS_PADDING_PX = 2.0

# ========== Clipboard/Clone Defaults ==========

# Default offset when cloning items (millimeters)
CLONE_OFFSET_X_MM = 20.0
CLONE_OFFSET_Y_MM = 20.0

# ========== Wheel Input Constants ==========

# Standard Qt wheel angle delta per "step" (120 = 15 degrees per step)
QT_WHEEL_ANGLE_DELTA_PER_STEP = 120.0

# ========== Zoom Constants ==========

# Zoom factor for zoom in/out actions
ZOOM_FACTOR = 1.15

# Minimum zoom level
MIN_ZOOM_LEVEL = 0.01

# Maximum zoom level
MAX_ZOOM_LEVEL = 100.0

# ========== Intensity/Alpha Constants ==========

# Maximum alpha value (8-bit)
MAX_ALPHA = 255.0

# ========== Snap Helper Constants ==========

# Default tolerance for magnetic snap (pixels)
MAGNETIC_SNAP_TOLERANCE_PX = 10.0

# ========== Ruler Constants ==========

# Ruler line dimensions
RULER_LINE_WIDTH = 2.0
RULER_LINE_WIDTH_SELECTED = 3.0  # 1.5x normal when selected

# Ruler bar dimensions (the end markers)
RULER_BAR_WIDTH = 1.0
RULER_BAR_HEIGHT = 12.0

# Hit testing tolerances
RULER_HIT_RADIUS_PX = 10.0
RULER_BOUNDING_PAD_PX = 90.0
RULER_MIN_STROKE_WIDTH_PX = 12.0

# Label positioning
RULER_LABEL_PADDING = 10.0
RULER_TOTAL_LABEL_PERP_OFFSET = 50.0  # Perpendicular offset from end point
RULER_TOTAL_LABEL_ALONG_OFFSET = 15.0  # Offset along segment direction
RULER_LABEL_CORNER_RADIUS = 4.0
RULER_LABEL_BG_ALPHA = 240
RULER_LABEL_BG_ALPHA_SELECTED = 250

# Change detection threshold for undo (in scene units)
RULER_POINT_CHANGE_THRESHOLD = 0.1

# ========== Angle Measure Constants ==========

# Line appearance
ANGLE_MEASURE_LINE_WIDTH = 2.0
ANGLE_MEASURE_ARC_WIDTH = 2.0
ANGLE_MEASURE_ARC_RADIUS = 30.0
ANGLE_MEASURE_ENDPOINT_RADIUS = 5.0

# Colors (RGBA tuples)
ANGLE_MEASURE_LINE_COLOR = (0, 150, 255, 200)  # Blue
ANGLE_MEASURE_ARC_COLOR = (0, 150, 255, 180)
ANGLE_MEASURE_LABEL_BG_COLOR = (0, 150, 255, 240)
ANGLE_MEASURE_LABEL_TEXT_COLOR = (255, 255, 255)
ANGLE_MEASURE_ENDPOINT_COLOR = (255, 255, 0, 200)  # Yellow
ANGLE_MEASURE_ENDPOINT_SELECTED_COLOR = (0, 150, 255, 255)

# ========== Path Measure Constants ==========

# Line appearance
PATH_MEASURE_LINE_WIDTH = 4.0
PATH_MEASURE_ENDPOINT_RADIUS = 6.0

# Colors (RGBA tuples)
PATH_MEASURE_HIGHLIGHT_COLOR = (0, 200, 100, 180)  # Green
PATH_MEASURE_LABEL_BG_COLOR = (0, 200, 100, 240)
PATH_MEASURE_LABEL_TEXT_COLOR = (255, 255, 255)
PATH_MEASURE_ENDPOINT_COLOR = (255, 255, 0, 200)  # Yellow

# ========== Shared Selection Indicator ==========

# Selection indicator color (shared across measurement items)
SELECTION_INDICATOR_COLOR = (255, 255, 0, 200)  # Yellow dashed outline



