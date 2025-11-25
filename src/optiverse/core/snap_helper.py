"""
Magnetic snap helper for aligning components.

Provides PowerPoint-style snap-to-align functionality with visual guides.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6 import QtCore

if TYPE_CHECKING:
    from PyQt6 import QtWidgets


@dataclass
class SnapResult:
    """Result of a snap calculation.

    Attributes:
        position: The final position (snapped or original)
        snapped: Whether snapping occurred
        guide_lines: List of guide lines to display (type, coordinate)
                    e.g., [("horizontal", 100.0), ("vertical", 200.0)]
    """

    position: QtCore.QPointF
    snapped: bool
    guide_lines: list[tuple[str, float]]


class SnapHelper:
    """Helper class for calculating magnetic snap positions.

    Implements PowerPoint-style snap-to-align functionality:
    - Center-to-center alignment
    - Edge-to-edge alignment (future)
    - Visual alignment guides

    Args:
        tolerance_px: Snap tolerance in view pixels (default 10.0)
    """

    def __init__(self, tolerance_px: float = 10.0):
        """Initialize snap helper with tolerance."""
        self.tolerance_px = tolerance_px

    def calculate_snap(
        self,
        target_pos: QtCore.QPointF,
        moving_item: QtWidgets.QGraphicsItem,
        scene: QtWidgets.QGraphicsScene,
        view: QtWidgets.QGraphicsView | None = None,
    ) -> SnapResult:
        """Calculate snap position for a moving item.

        Args:
            target_pos: The desired position in scene coordinates
            moving_item: The item being moved
            scene: The graphics scene
            view: Optional view for transform calculations

        Returns:
            SnapResult with final position and guide lines
        """
        # Import here to avoid circular imports
        from ..objects import BaseObj

        # Calculate tolerance in scene coordinates
        tolerance_scene = self._view_to_scene_distance(self.tolerance_px, view)

        # Find all potential snap targets (other BaseObj items)
        targets = []
        for item in scene.items():
            if isinstance(item, BaseObj) and item is not moving_item:
                targets.append(item)

        if not targets:
            # No targets to snap to
            return SnapResult(target_pos, False, [])

        # Get moving item center in scene coordinates
        moving_center = target_pos

        # Find closest snap points for X and Y axes
        best_x_snap = None
        best_x_dist = tolerance_scene
        best_y_snap = None
        best_y_dist = tolerance_scene

        for target in targets:
            # Get target center position
            target_center = target.pos()

            # Check horizontal alignment (Y coordinate)
            y_dist = abs(moving_center.y() - target_center.y())
            if y_dist < best_y_dist:
                best_y_dist = y_dist
                best_y_snap = target_center.y()

            # Check vertical alignment (X coordinate)
            x_dist = abs(moving_center.x() - target_center.x())
            if x_dist < best_x_dist:
                best_x_dist = x_dist
                best_x_snap = target_center.x()

        # Build result
        snapped_x = best_x_snap if best_x_snap is not None else target_pos.x()
        snapped_y = best_y_snap if best_y_snap is not None else target_pos.y()
        final_pos = QtCore.QPointF(snapped_x, snapped_y)

        guide_lines = []
        snapped = False

        if best_x_snap is not None:
            guide_lines.append(("vertical", best_x_snap))
            snapped = True

        if best_y_snap is not None:
            guide_lines.append(("horizontal", best_y_snap))
            snapped = True

        return SnapResult(final_pos, snapped, guide_lines)

    def _view_to_scene_distance(
        self, distance_px: float, view: QtWidgets.QGraphicsView | None
    ) -> float:
        """Convert a distance in view pixels to scene coordinates.

        Args:
            distance_px: Distance in view pixels
            view: The graphics view (optional)

        Returns:
            Distance in scene coordinates
        """
        if view is None:
            # No view transform, assume 1:1 mapping
            return distance_px

        # Get the view's transform matrix
        transform = view.transform()

        # Use the average scale factor (m11 and m22 for x and y)
        scale_x = transform.m11()
        scale_y = transform.m22()
        avg_scale = (abs(scale_x) + abs(scale_y)) / 2.0

        if avg_scale < 1e-6:
            # Degenerate transform
            return distance_px

        # Convert view pixels to scene units
        return distance_px / avg_scale
