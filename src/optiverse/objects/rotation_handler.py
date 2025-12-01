"""
Rotation handlers for optical elements.

Encapsulates rotation logic to keep BaseObj focused on core functionality.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable

from PyQt6 import QtCore

from ..core.constants import WHEEL_ROTATION_FINALIZE_DELAY_MS
from ..core.undo_stack import UndoStack

if TYPE_CHECKING:
    from .base_obj import BaseObj


class SingleItemRotationHandler:
    """
    Handles rotation of a single item via Ctrl+drag.

    Usage:
        handler = SingleItemRotationHandler(item)
        # In mouse events:
        handler.start_rotation(mouse_scene_pos, item.rotation())
        handler.update_rotation(mouse_scene_pos, snap_to_45=False)
        handler.finish_rotation()
    """

    def __init__(self, item: BaseObj):
        """
        Initialize handler.

        Args:
            item: The item to rotate
        """
        self._item = item
        self._rotating = False
        self._rotation_start_angle = 0.0
        self._rotation_initial = 0.0

    @property
    def is_rotating(self) -> bool:
        """Check if currently in rotation mode."""
        return self._rotating

    def start_rotation(self, mouse_scene_pos: QtCore.QPointF, initial_rotation: float) -> None:
        """
        Start rotation mode.

        Args:
            mouse_scene_pos: Mouse position in scene coordinates
            initial_rotation: Item's current rotation in degrees
        """
        self._rotating = True
        self._rotation_initial = initial_rotation

        # Get rotation center (item's transform origin)
        center = self._item.mapToScene(self._item.transformOriginPoint())

        # Calculate initial angle from center to mouse position
        dx = mouse_scene_pos.x() - center.x()
        dy = mouse_scene_pos.y() - center.y()
        self._rotation_start_angle = math.degrees(math.atan2(dy, dx))

    def update_rotation(self, mouse_scene_pos: QtCore.QPointF, snap_to_45: bool = False) -> float:
        """
        Update rotation based on mouse position.

        Args:
            mouse_scene_pos: Current mouse position in scene coordinates
            snap_to_45: If True, snap to 45-degree increments

        Returns:
            New rotation angle in degrees
        """
        if not self._rotating:
            return self._item.rotation()

        center = self._item.mapToScene(self._item.transformOriginPoint())

        # Calculate current angle
        dx = mouse_scene_pos.x() - center.x()
        dy = mouse_scene_pos.y() - center.y()
        current_angle = math.degrees(math.atan2(dy, dx))

        # Calculate rotation delta
        angle_delta = current_angle - self._rotation_start_angle
        new_rotation = self._rotation_initial + angle_delta

        # Apply 45-degree snap if requested
        if snap_to_45:
            new_rotation = round(new_rotation / 45.0) * 45.0

        return new_rotation

    def finish_rotation(self) -> None:
        """End rotation mode."""
        self._rotating = False


class GroupRotationHandler:
    """
    Handles rotation of multiple selected items around their common center.

    Features:
    - Calculates group center automatically
    - Rotates all items around common center
    - Updates both position and rotation of each item
    - Supports 45-degree snap
    """

    def __init__(self, items: list[BaseObj]):
        """
        Initialize handler.

        Args:
            items: List of items to rotate together
        """
        self._items = items
        self._rotating = False
        self._rotation_start_angle = 0.0
        self._initial_positions: dict[BaseObj, QtCore.QPointF] = {}
        self._initial_rotations: dict[BaseObj, float] = {}
        self._center = QtCore.QPointF(0, 0)

    @property
    def is_rotating(self) -> bool:
        """Check if currently in rotation mode."""
        return self._rotating

    @property
    def items(self) -> list[BaseObj]:
        """Get the items being rotated."""
        return self._items

    @property
    def initial_positions(self) -> dict[BaseObj, QtCore.QPointF]:
        """Get the initial positions of items."""
        return self._initial_positions

    @property
    def initial_rotations(self) -> dict[BaseObj, float]:
        """Get the initial rotations of items."""
        return self._initial_rotations

    def start_rotation(self, mouse_scene_pos: QtCore.QPointF) -> None:
        """
        Start group rotation mode.

        Args:
            mouse_scene_pos: Mouse position in scene coordinates
        """
        if not self._items:
            return

        self._rotating = True

        # Store initial state for all items
        self._initial_positions = {item: QtCore.QPointF(item.pos()) for item in self._items}
        self._initial_rotations = {item: item.rotation() for item in self._items}

        # Calculate group center
        center_x = sum(item.pos().x() for item in self._items) / len(self._items)
        center_y = sum(item.pos().y() for item in self._items) / len(self._items)
        self._center = QtCore.QPointF(center_x, center_y)

        # Calculate initial angle from center to mouse position
        dx = mouse_scene_pos.x() - self._center.x()
        dy = mouse_scene_pos.y() - self._center.y()
        self._rotation_start_angle = math.degrees(math.atan2(dy, dx))

    @property
    def center(self) -> QtCore.QPointF:
        """Get the rotation center."""
        return self._center

    def update_rotation(self, mouse_scene_pos: QtCore.QPointF, snap_to_45: bool = False) -> float:
        """
        Update all items based on mouse position.

        Args:
            mouse_scene_pos: Current mouse position in scene coordinates
            snap_to_45: If True, snap to 45-degree increments

        Returns:
            Rotation delta in degrees
        """
        if not self._rotating:
            return 0.0

        # Calculate current angle
        dx = mouse_scene_pos.x() - self._center.x()
        dy = mouse_scene_pos.y() - self._center.y()
        current_angle = math.degrees(math.atan2(dy, dx))

        # Calculate rotation delta
        angle_delta = current_angle - self._rotation_start_angle

        # Apply 45-degree snap if requested
        if snap_to_45:
            angle_delta = round(angle_delta / 45.0) * 45.0

        # Apply rotation to all items
        angle_rad = math.radians(angle_delta)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        for item in self._items:
            # Rotate position around group center
            initial_pos = self._initial_positions[item]
            rel_pos = initial_pos - self._center
            new_x = rel_pos.x() * cos_a - rel_pos.y() * sin_a
            new_y = rel_pos.x() * sin_a + rel_pos.y() * cos_a
            item.setPos(self._center.x() + new_x, self._center.y() + new_y)

            # Rotate the item itself
            initial_rotation = self._initial_rotations[item]
            item.setRotation(initial_rotation + angle_delta)
            item.edited.emit()

        return angle_delta

    def finish_rotation(self) -> None:
        """End group rotation mode and emit edited signals."""
        if self._rotating:
            for item in self._items:
                item.edited.emit()

        self._rotating = False
        self._items = []
        self._initial_positions = {}
        self._initial_rotations = {}


class WheelRotationTracker:
    """
    Tracks wheel rotation events and creates undo commands after a delay.

    Batches multiple wheel events into a single undo command.
    """

    def __init__(self, get_undo_stack: Callable[[], UndoStack | None]):
        """
        Initialize tracker.

        Args:
            get_undo_stack: Callable that returns the undo stack (or None if unavailable)
        """
        self._get_undo_stack = get_undo_stack
        self._timer: QtCore.QTimer | None = None
        self._start_rotations: dict[BaseObj, float] | None = None
        self._start_positions: dict[BaseObj, QtCore.QPointF] | None = None
        self._items: list[BaseObj] | None = None

    def track(self, items: list[BaseObj]) -> None:
        """
        Start tracking rotation for the given items (if not already tracking).

        Args:
            items: Items being rotated
        """
        if self._start_rotations is None:
            self._start_rotations = {item: item.rotation() for item in items}
            self._start_positions = {item: QtCore.QPointF(item.pos()) for item in items}
            self._items = items

        # Reset/start timer
        if self._timer:
            self._timer.stop()
        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._finalize)
        self._timer.start(WHEEL_ROTATION_FINALIZE_DELAY_MS)

    def _finalize(self) -> None:
        """Create undo command for the completed rotation sequence."""
        if self._start_rotations is None or self._items is None:
            return

        undo_stack = self._get_undo_stack()
        if undo_stack is None:
            self._clear()
            return

        # Import here to avoid circular imports
        from .core_imports import get_rotate_commands

        RotateItemCommand, RotateItemsCommand = get_rotate_commands()

        items = self._items
        old_rotations = self._start_rotations
        old_positions = self._start_positions
        new_rotations = {item: item.rotation() for item in items}
        new_positions = {item: item.pos() for item in items}

        # Check if anything actually changed
        rotation_changed = any(
            abs(old_rotations.get(item, 0) - new_rotations.get(item, 0)) > 0.01 for item in items
        )
        position_changed = any(
            old_positions.get(item) != new_positions.get(item)
            for item in items
            if old_positions and item in old_positions
        )

        if rotation_changed or position_changed:
            if len(items) == 1 and not position_changed:
                # Single item rotation only
                cmd = RotateItemCommand(items[0], old_rotations[items[0]], new_rotations[items[0]])
                undo_stack.push(cmd)
            elif len(items) > 1 or position_changed:
                # Group rotation or single item with position change
                cmd = RotateItemsCommand(
                    items, old_positions, new_positions, old_rotations, new_rotations
                )
                undo_stack.push(cmd)

        self._clear()

    def _clear(self) -> None:
        """Clear tracking state."""
        self._start_rotations = None
        self._start_positions = None
        self._items = None


def rotate_group_instant(items: list[BaseObj], rotation_delta: float) -> None:
    """
    Instantly rotate a group of items around their common center.

    This is a simple helper for wheel rotation. For drag rotation,
    use GroupRotationHandler instead.

    Args:
        items: Items to rotate
        rotation_delta: Rotation amount in degrees
    """
    if not items:
        return

    # Calculate center of all items
    center_x = sum(item.pos().x() for item in items) / len(items)
    center_y = sum(item.pos().y() for item in items) / len(items)
    center = QtCore.QPointF(center_x, center_y)

    # Rotate each item around the common center
    angle_rad = math.radians(rotation_delta)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    for item in items:
        # Get current position relative to center
        rel_pos = item.pos() - center

        # Rotate the relative position
        new_x = rel_pos.x() * cos_a - rel_pos.y() * sin_a
        new_y = rel_pos.x() * sin_a + rel_pos.y() * cos_a

        # Set new position
        item.setPos(center.x() + new_x, center.y() + new_y)

        # Also rotate the item itself
        item.setRotation(item.rotation() + rotation_delta)
        item.edited.emit()
