"""
Ray rendering layer for high-performance visualization.

Uses direct vector rendering (NoCache) because Qt's caching mechanisms were
causing constant invalidation overhead. Ray path building is fast (3ms for 5000+ segments),
so uncached rendering provides better performance than fighting cache invalidation.
"""

from __future__ import annotations

import logging
import time

from PyQt6 import QtCore, QtGui, QtWidgets

_logger = logging.getLogger(__name__)


class DebugRayPathItem(QtWidgets.QGraphicsPathItem):
    """Custom QGraphicsPathItem that tracks paint performance."""

    paint_count = 0
    total_paint_time = 0.0
    paint_times = []

    def __init__(self, path):
        super().__init__(path)
        self._segment_count = 0

    def set_segment_count(self, count):
        """Track how many segments this item has."""
        self._segment_count = count

    def paint(self, painter, option, widget=None):
        """Paint with performance tracking."""
        start = time.perf_counter()
        super().paint(painter, option, widget)
        elapsed = (time.perf_counter() - start) * 1000

        DebugRayPathItem.paint_count += 1
        DebugRayPathItem.total_paint_time += elapsed
        DebugRayPathItem.paint_times.append(elapsed)

        # Keep only last 100 times
        if len(DebugRayPathItem.paint_times) > 100:
            DebugRayPathItem.paint_times.pop(0)

        # Report every 100 paint calls
        if DebugRayPathItem.paint_count % 100 == 0:
            avg = sum(DebugRayPathItem.paint_times) / len(DebugRayPathItem.paint_times)
            max_time = max(DebugRayPathItem.paint_times)
            _logger.debug(
                "Ray path item paints: %d total, avg=%.3fms, max=%.3fms, segments=%d",
                DebugRayPathItem.paint_count,
                avg,
                max_time,
                self._segment_count,
            )


class CachedRayLayer(QtWidgets.QGraphicsItemGroup):
    """
    Ray rendering layer using uncached vector graphics.

    Despite the name "Cached", this now uses NoCache because Qt was invalidating
    the cache on every pan/zoom anyway, causing worse performance than direct rendering.

    Performance:
    - Ray grouping by color (1-5 items for typical scenes)
    - Fast vector rendering (3ms for 5000+ segments)
    - No cache invalidation overhead
    - Smooth 60fps panning and zooming
    - Only re-builds paths when rays actually change

    Example:
        layer = CachedRayLayer()
        scene.addItem(layer)
        layer.update_rays(ray_paths, width_px=2.0)
    """

    def __init__(self):
        super().__init__()

        # PERFORMANCE: No caching - Qt keeps invalidating cache anyway on pan/zoom
        # Ray rendering is fast enough (3ms for 5000+ segments) that caching overhead hurts more than helps
        # Uncached vector rendering = smooth 60fps, cached = constant invalidation = stuttering
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)

        # Set z-value to draw rays above components but below annotations
        self.setZValue(10)

        # Disable selection/focus (rays are visual only)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)

        # Debug tracking
        self._paint_count = 0
        self._last_paint_time = time.perf_counter()
        self._paint_times = []

    def update_rays(self, ray_paths: list, width_px: float):
        """
        Update ray rendering with new paths.

        PERFORMANCE: Uses path simplification to reduce segment count.
        On high-DPI displays, Qt's software rasterizer is very slow (90ms for 2500 segments).
        We simplify paths by removing collinear points, which reduces segments by 50-80%
        with no visual difference.

        Args:
            ray_paths: List of RayPath objects
            width_px: Width of ray lines in pixels
        """
        # Clear existing ray items
        for child in self.childItems():
            self.removeFromGroup(child)
            if child.scene():
                child.scene().removeItem(child)

        if not ray_paths:
            return

        # Group rays by visual style (color + width)
        style_groups = {}
        for ray_path in ray_paths:
            if len(ray_path.points) < 2:
                continue

            r, g, b, a = ray_path.rgba
            style_key = (r, g, b, a, width_px)

            if style_key not in style_groups:
                style_groups[style_key] = []
            style_groups[style_key].append(ray_path)

        # Create one batched item per style group
        for style_key, rays in style_groups.items():
            r, g, b, a, width = style_key

            # Build combined path for all rays with this style
            combined_path = QtGui.QPainterPath()
            segment_count = 0
            original_segment_count = 0

            for ray in rays:
                # Simplify the path by removing unnecessary points
                simplified_points = self._simplify_path(ray.points, tolerance=0.5)
                original_segment_count += len(ray.points) - 1

                if len(simplified_points) < 2:
                    continue

                # Start new subpath for each ray
                combined_path.moveTo(
                    QtCore.QPointF(float(simplified_points[0][0]), float(simplified_points[0][1]))
                )
                for point in simplified_points[1:]:
                    combined_path.lineTo(float(point[0]), float(point[1]))
                    segment_count += 1

            if segment_count == 0:
                continue

            _logger.debug(
                "Simplified %d segments -> %d (%.1f%% reduction)",
                original_segment_count,
                segment_count,
                100 * (1 - segment_count / original_segment_count),
            )

            # Create graphics item for this style group (with debug tracking)
            item = DebugRayPathItem(combined_path)
            item.set_segment_count(segment_count)

            # Set pen style
            pen = QtGui.QPen(QtGui.QColor(r, g, b, a))
            pen.setWidthF(width)
            pen.setCosmetic(True)  # Width in screen pixels, not scene units
            item.setPen(pen)

            # PERFORMANCE: No caching - let Qt render vectors directly
            # Caching was causing constant invalidation overhead on pan/zoom
            item.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)

            # Disable interaction (rays are visual only)
            item.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

            # Add to group
            self.addToGroup(item)

    def _simplify_path(self, points, tolerance=0.5):
        """
        Simplify a path by removing collinear points.

        Uses Ramer-Douglas-Peucker algorithm to remove unnecessary points
        while preserving the visual shape within tolerance.

        Args:
            points: List of [x, y] points
            tolerance: Maximum distance from simplified line (in scene units)

        Returns:
            Simplified list of points
        """
        if len(points) < 3:
            return points

        # Ramer-Douglas-Peucker algorithm
        def perpendicular_distance(point, line_start, line_end):
            """Calculate perpendicular distance from point to line."""
            x0, y0 = point[0], point[1]
            x1, y1 = line_start[0], line_start[1]
            x2, y2 = line_end[0], line_end[1]

            dx = x2 - x1
            dy = y2 - y1

            if dx == 0 and dy == 0:
                return ((x0 - x1) ** 2 + (y0 - y1) ** 2) ** 0.5

            # Distance = |cross product| / |line segment|
            return abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / (dx**2 + dy**2) ** 0.5

        def rdp(points, start, end, tolerance):
            """Recursive Ramer-Douglas-Peucker."""
            if end - start < 2:
                return []

            # Find point with maximum distance
            max_dist = 0
            max_index = start

            for i in range(start + 1, end):
                dist = perpendicular_distance(points[i], points[start], points[end])
                if dist > max_dist:
                    max_dist = dist
                    max_index = i

            # If max distance is greater than tolerance, recursively simplify
            if max_dist > tolerance:
                # Recursively simplify both sides
                left = rdp(points, start, max_index, tolerance)
                right = rdp(points, max_index, end, tolerance)
                return left + [max_index] + right
            else:
                # All points between start and end can be removed
                return []

        # Apply RDP algorithm
        indices_to_keep = [0] + rdp(points, 0, len(points) - 1, tolerance) + [len(points) - 1]
        indices_to_keep = sorted(set(indices_to_keep))

        return [points[i] for i in indices_to_keep]

    def clear(self):
        """Clear all rays from the layer."""
        for child in self.childItems():
            self.removeFromGroup(child)
            if child.scene():
                child.scene().removeItem(child)

    def paint(self, painter, option, widget=None):
        """Paint the ray layer - track rendering performance."""
        paint_start = time.perf_counter()

        # Call parent to paint child items
        super().paint(painter, option, widget)

        paint_time = (time.perf_counter() - paint_start) * 1000
        self._paint_count += 1
        self._paint_times.append(paint_time)

        # Keep only last 60 paint times
        if len(self._paint_times) > 60:
            self._paint_times.pop(0)

        # Print every 30 frames
        if self._paint_count % 30 == 0:
            avg_time = sum(self._paint_times) / len(self._paint_times)
            max_time = max(self._paint_times)
            min_time = min(self._paint_times)
            time_since_last = (paint_start - self._last_paint_time) * 1000
            self._last_paint_time = paint_start

            _logger.debug(
                "PAINT #%d: avg=%.2fms, min=%.2fms, max=%.2fms, 30 frames took %.0fms. Children: %d ray items",
                self._paint_count,
                avg_time,
                min_time,
                max_time,
                time_since_last,
                len(self.childItems()),
            )
