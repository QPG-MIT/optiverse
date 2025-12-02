"""
Application-wide constants.

This module centralizes magic numbers and default values used throughout
the application for maintainability and consistency.
"""

# ========== Scene Constants ==========

# Scene bounds in millimeters (1 km x 1 km centered at origin)
# Provides effectively "infinite" scrollable area
SCENE_SIZE_MM = 1_000_000  # Total width/height
SCENE_MIN_COORD = -500_000  # Minimum X/Y coordinate
SCENE_MAX_COORD = 500_000  # Maximum X/Y coordinate

# ========== Timing Constants (milliseconds) ==========

# Autosave debounce delay - wait for this long after changes before autosaving
AUTOSAVE_DEBOUNCE_MS = 1000

# Wheel rotation undo delay - batch wheel events within this window
WHEEL_ROTATION_FINALIZE_DELAY_MS = 300

# Collaboration heartbeat interval
COLLABORATION_HEARTBEAT_MS = 30_000

# ========== Default Measurements ==========

# Default object height in millimeters (1 inch)
DEFAULT_OBJECT_HEIGHT_MM = 25.4

# Default component sizes
DEFAULT_RECTANGLE_WIDTH_MM = 60.0
DEFAULT_RECTANGLE_HEIGHT_MM = 40.0

# ========== Rotation Constants ==========

# Wheel rotation sensitivity (degrees per scroll step)
WHEEL_ROTATION_DEGREES_PER_STEP = 2.0

# Snap angle for Shift+Ctrl rotation (degrees)
ROTATION_SNAP_ANGLE_DEG = 45.0

# ========== UI Constants ==========

# Default window size
DEFAULT_WINDOW_WIDTH = 1450
DEFAULT_WINDOW_HEIGHT = 860

# Ray rendering
DEFAULT_RAY_WIDTH_PX = 1.5

# Hit testing thresholds (pixels)
LINE_ENDPOINT_HIT_THRESHOLD_PX = 10.0
LINE_BODY_HIT_THRESHOLD_PX = 5.0

# Ghost item opacity for placement preview
PLACEMENT_GHOST_OPACITY = 0.5

# ========== Serialization Constants ==========

# Current file format version
FILE_FORMAT_VERSION = "2.0"

# ========== MIME Type Constants ==========

# Custom MIME type for optics components (used in drag-and-drop)
MIME_OPTICS_COMPONENT = "application/x-optics-component"

# ========== Physical Constants ==========

# Speed of light in vacuum (mm/ns for internal calculations)
SPEED_OF_LIGHT_MM_PER_NS = 299.792458

# Air refractive index (standard conditions)
AIR_REFRACTIVE_INDEX = 1.0

# Common glass refractive index (BK7-like)
GLASS_REFRACTIVE_INDEX = 1.52

# ========== Raytracing Constants ==========

# Maximum number of raytracing events (reflections/refractions) per ray
MAX_RAYTRACING_EVENTS = 80
