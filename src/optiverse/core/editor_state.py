"""
Editor state management.

Provides a clean state machine for editor modes, replacing scattered boolean flags.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..objects.annotations.ruler_item import RulerItem


class EditorMode(Enum):
    """
    Editor mode states.

    Only one mode can be active at a time. This replaces the scattered boolean
    flags like _inspect_mode, _placement_mode, _path_measure_mode, _placing_ruler.
    """
    DEFAULT = auto()        # Normal selection/editing mode
    INSPECT = auto()        # Inspect tool active
    PATH_MEASURE = auto()   # Path measure tool active
    ANGLE_MEASURE = auto()  # Angle measure tool active
    PLACEMENT = auto()      # Component placement mode
    RULER_PLACEMENT = auto()  # Ruler two-click placement


class EditorState:
    """
    Centralized editor state management.

    Manages the current editor mode and associated state, ensuring only one
    mode is active at a time and providing clean transitions.
    """

    def __init__(self):
        self._mode = EditorMode.DEFAULT

        # Placement-specific state (only valid when mode == PLACEMENT)
        self._placement_type: Optional[str] = None

        # Ruler placement state (only valid when mode == RULER_PLACEMENT)
        self._ruler_in_progress: Optional['RulerItem'] = None  # RulerItem being placed

    @property
    def mode(self) -> EditorMode:
        """Get the current editor mode."""
        return self._mode

    @property
    def is_default(self) -> bool:
        """Check if in default mode."""
        return self._mode == EditorMode.DEFAULT

    @property
    def is_inspect(self) -> bool:
        """Check if inspect mode is active."""
        return self._mode == EditorMode.INSPECT

    @property
    def is_path_measure(self) -> bool:
        """Check if path measure mode is active."""
        return self._mode == EditorMode.PATH_MEASURE

    @property
    def is_angle_measure(self) -> bool:
        """Check if angle measure mode is active."""
        return self._mode == EditorMode.ANGLE_MEASURE

    @property
    def is_placement(self) -> bool:
        """Check if placement mode is active."""
        return self._mode == EditorMode.PLACEMENT

    @property
    def is_ruler_placement(self) -> bool:
        """Check if ruler placement mode is active."""
        return self._mode == EditorMode.RULER_PLACEMENT

    @property
    def placement_type(self) -> Optional[str]:
        """Get the current placement type (only valid in PLACEMENT mode)."""
        return self._placement_type if self._mode == EditorMode.PLACEMENT else None

    @property
    def ruler_in_progress(self) -> Optional['RulerItem']:
        """Get the ruler currently being placed (only valid in RULER_PLACEMENT mode)."""
        return self._ruler_in_progress if self._mode == EditorMode.RULER_PLACEMENT else None

    @ruler_in_progress.setter
    def ruler_in_progress(self, value: Optional['RulerItem']):
        """Set the ruler currently being placed."""
        if self._mode == EditorMode.RULER_PLACEMENT:
            self._ruler_in_progress = value

    def enter_default(self) -> EditorMode:
        """
        Enter default mode.

        Returns:
            Previous mode for cleanup purposes
        """
        prev = self._mode
        self._mode = EditorMode.DEFAULT
        self._placement_type = None
        self._ruler_in_progress = None
        return prev

    def enter_inspect(self) -> EditorMode:
        """
        Enter inspect mode.

        Returns:
            Previous mode for cleanup purposes
        """
        prev = self._mode
        self._mode = EditorMode.INSPECT
        self._placement_type = None
        self._ruler_in_progress = None
        return prev

    def enter_path_measure(self) -> EditorMode:
        """
        Enter path measure mode.

        Returns:
            Previous mode for cleanup purposes
        """
        prev = self._mode
        self._mode = EditorMode.PATH_MEASURE
        self._placement_type = None
        self._ruler_in_progress = None
        return prev

    def enter_angle_measure(self) -> EditorMode:
        """
        Enter angle measure mode.

        Returns:
            Previous mode for cleanup purposes
        """
        prev = self._mode
        self._mode = EditorMode.ANGLE_MEASURE
        self._placement_type = None
        self._ruler_in_progress = None
        return prev

    def enter_placement(self, component_type: str) -> EditorMode:
        """
        Enter placement mode for a specific component type.

        Args:
            component_type: Type of component to place

        Returns:
            Previous mode for cleanup purposes
        """
        prev = self._mode
        self._mode = EditorMode.PLACEMENT
        self._placement_type = component_type
        self._ruler_in_progress = None
        return prev

    def enter_ruler_placement(self) -> EditorMode:
        """
        Enter ruler placement mode.

        Returns:
            Previous mode for cleanup purposes
        """
        prev = self._mode
        self._mode = EditorMode.RULER_PLACEMENT
        self._placement_type = None
        self._ruler_in_progress = None
        return prev

    def exit_ruler_placement(self) -> EditorMode:
        """
        Exit ruler placement mode and return to default mode.

        Returns:
            Previous mode for cleanup purposes
        """
        return self.enter_default()



