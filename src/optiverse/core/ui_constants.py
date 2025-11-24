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

