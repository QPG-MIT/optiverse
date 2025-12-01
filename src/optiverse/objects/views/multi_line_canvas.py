"""
Multi-line Image Canvas for Component Editor.

Extends ImageCanvas to support multiple optical interfaces with:
- Visual representation as colored lines
- Draggable endpoints
- Color coding by interface type
- Unified interface for simple (1 line) and complex (N lines) components
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from PyQt6 import QtCore, QtGui, QtWidgets

from .canvas_coordinates import CanvasCoordinateSystem
from .interface_renderer import InterfaceRenderer

# Optional QtSvg for SVG clipboard/loads
try:
    from PyQt6 import QtSvg

    HAVE_QTSVG = True
except ImportError:
    HAVE_QTSVG = False


@dataclass
class InterfaceLine:
    """
    A single optical interface line.

    COORDINATE SYSTEM:
    - Origin (0,0) is at the IMAGE CENTER
    - X-axis: positive right, negative left
    - Y-axis: positive UP, negative DOWN (Y-up, mathematical convention)
    - Units: millimeters

    Note: Y-up storage coordinates. MultiLineCanvas converts to Y-down for Qt display.
    """

    x1: float  # Start point X in mm (centered, Y-up)
    y1: float  # Start point Y in mm (centered, Y-up)
    x2: float  # End point X in mm (centered, Y-up)
    y2: float  # End point Y in mm (centered, Y-up)
    color: QtGui.QColor | None = None  # Line color
    label: str = ""  # Optional label
    properties: dict[str, Any] | None = None  # Additional properties (n1, n2, is_BS, etc.)

    def __post_init__(self):
        if self.color is None:
            self.color = QtGui.QColor(100, 100, 255)  # Default blue
        if self.properties is None:
            self.properties = {}


class MultiLineCanvas(QtWidgets.QLabel):
    """
    Image canvas with support for multiple draggable colored lines.

    COORDINATE SYSTEM:
    - Lines are stored in millimeter coordinates (InterfaceLine)
    - Origin (0,0) is at the IMAGE CENTER
    - Y-axis is UP (positive Y is up, negative Y is down) - mathematical convention
    - Canvas handles conversion to screen pixels (Y-down) automatically for display

    COORDINATE TRANSFORMATIONS:
    - Storage/Logic: Y-up (mathematical convention)
    - Qt Display: Y-down (screen coordinates)
    - Canvas converts Y-up storage ↔ Y-down display at the Qt boundary

    Signals:
        imageDropped: Emitted when image is dropped
        linesChanged: Emitted when any line changes
        lineSelected: Emitted when a line is selected (index)
    """

    imageDropped = QtCore.pyqtSignal(QtGui.QPixmap, str)
    linesChanged = QtCore.pyqtSignal()  # Any line changed
    lineSelected = QtCore.pyqtSignal(int)  # Line index selected (single)
    linesSelected = QtCore.pyqtSignal(list)  # Multiple line indices selected
    linesMoved = QtCore.pyqtSignal(
        list, list, list
    )  # (indices, old_positions, new_positions) for undo

    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._pix: QtGui.QPixmap | None = None
        self._svg_renderer: QtSvg.QSvgRenderer | None = None  # Native SVG renderer
        self._svg_cache_pixmap: QtGui.QPixmap | None = None  # Cached pre-rendered SVG
        self._svg_cache_size: QtCore.QSize = QtCore.QSize()  # Size of cached render
        self._scale_fit = 1.0
        self._src_path: str | None = None
        self.setAcceptDrops(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # Multiple lines support (all coordinates in millimeters)
        self._lines: list[InterfaceLine] = []
        self._selected_lines: set = set()  # Set of selected line indices (multi-selection)

        # Coordinate conversion factor
        self._mm_per_px: float = 1.0  # Millimeters per image pixel

        # Drag state
        self._dragging_line: int = -1  # Index of line being dragged (endpoint mode)
        self._dragging_point: int = 0  # 1 for start point, 2 for end point
        self._dragging_entire_lines: bool = False  # True when dragging whole line(s)
        self._drag_start_pos: QtCore.QPointF | None = None  # Initial drag position
        self._drag_initial_lines: list[tuple[float, float, float, float]] = (
            []
        )  # Initial line positions
        self._drag_moved_indices: list[int] = []  # Indices of lines that were moved (for undo)
        self._hover_line: int = -1  # Line being hovered
        self._hover_point: int = 0  # Point being hovered (1 or 2)

        # Rectangle selection
        self._rect_selecting: bool = False  # True when drawing selection rectangle
        self._rect_start: QtCore.QPoint | None = None  # Rectangle start position
        self._rect_end: QtCore.QPoint | None = None  # Rectangle end position

        # Drag lock (restrict dragging to specific line)
        self._drag_locked_line: int = (
            -1
        )  # -1 means no lock, otherwise only this line can be dragged

        # Coordinate system for transformations
        self._coord_system = CanvasCoordinateSystem()

        # Renderer for drawing interface lines
        self._renderer = InterfaceRenderer(self._coord_system)

        self.setMouseTracking(True)

    # ========== Image Management ==========

    def set_pixmap(self, pix: QtGui.QPixmap, source_path: str | None = None):
        """Set the background image."""
        # Normalize device pixel ratio
        if pix and not pix.isNull():
            img = pix.toImage()
            img.setDevicePixelRatio(1.0)
            pix = QtGui.QPixmap.fromImage(img)

        self._pix = pix
        self._src_path = source_path

        # If source is SVG, store renderer and pre-render cache
        self._svg_renderer = None
        self._svg_cache_pixmap = None
        self._svg_cache_size = QtCore.QSize()

        if source_path and source_path.lower().endswith(".svg") and HAVE_QTSVG:
            try:
                renderer = QtSvg.QSvgRenderer(source_path)
                if renderer.isValid():
                    self._svg_renderer = renderer
                    # Pre-render SVG to cache at high resolution
                    self._update_svg_cache()
            except (OSError, RuntimeError):
                pass  # SVG may be invalid or file inaccessible

        self.update()

    def source_path(self) -> str | None:
        return self._src_path

    def current_pixmap(self) -> QtGui.QPixmap | None:
        return self._pix

    def has_image(self) -> bool:
        return self._pix is not None and not self._pix.isNull()

    def image_pixel_size(self) -> tuple[int, int]:
        """Get image size in pixels."""
        if not self._pix:
            return (0, 0)
        return (self._pix.width(), self._pix.height())

    def set_mm_per_pixel(self, mm_per_px: float):
        """Set the millimeter per pixel conversion factor for coordinate system."""
        self._mm_per_px = mm_per_px
        self.update()

    def get_mm_per_pixel(self) -> float:
        """Get the millimeter per pixel conversion factor."""
        return self._mm_per_px

    # ========== Line Management ==========

    def add_line(self, line: InterfaceLine) -> int:
        """Add a line and return its index."""
        self._lines.append(line)
        self.update()
        self.linesChanged.emit()
        return len(self._lines) - 1

    def remove_line(self, index: int):
        """Remove line at index."""
        if 0 <= index < len(self._lines):
            del self._lines[index]
            # Update selected lines (remove deleted, adjust indices)
            new_selected = set()
            for sel_idx in self._selected_lines:
                if sel_idx < index:
                    new_selected.add(sel_idx)
                elif sel_idx > index:
                    new_selected.add(sel_idx - 1)
                # Skip if sel_idx == index (deleted line)
            self._selected_lines = new_selected
            self.update()
            self.linesChanged.emit()

    def get_line(self, index: int) -> InterfaceLine | None:
        """Get line at index."""
        if 0 <= index < len(self._lines):
            return self._lines[index]
        return None

    def update_line(self, index: int, line: InterfaceLine):
        """Update line at index."""
        if 0 <= index < len(self._lines):
            self._lines[index] = line
            self.update()
            self.linesChanged.emit()

    def get_all_lines(self) -> list[InterfaceLine]:
        """Get all lines."""
        return list(self._lines)

    def clear_lines(self):
        """Remove all lines."""
        self._lines.clear()
        self._selected_lines.clear()
        self.update()
        self.linesChanged.emit()

    def set_lines(self, lines: list[InterfaceLine]):
        """Set all lines at once."""
        self._lines = list(lines)
        self._selected_lines.clear()
        self.update()
        self.linesChanged.emit()

    def get_selected_line_index(self) -> int:
        """
        Get currently selected line index (-1 if none).

        Returns first selected for backward compatibility.
        """
        if len(self._selected_lines) > 0:
            return int(min(self._selected_lines))
        return -1

    def get_selected_line_indices(self) -> list[int]:
        """Get all selected line indices."""
        return sorted(list(self._selected_lines))

    def select_line(self, index: int, add_to_selection: bool = False):
        """
        Select a line by index.

        Args:
            index: Line index to select (-1 to clear selection)
            add_to_selection: If True, add to existing selection; if False, replace selection
        """
        if index == -1:
            self._selected_lines.clear()
        elif 0 <= index < len(self._lines):
            if not add_to_selection:
                self._selected_lines.clear()
            self._selected_lines.add(index)
            self.lineSelected.emit(index)

        self.update()
        self.linesSelected.emit(sorted(list(self._selected_lines)))

    def select_lines(self, indices: list[int]):
        """Select multiple lines by indices."""
        self._selected_lines.clear()
        for idx in indices:
            if 0 <= idx < len(self._lines):
                self._selected_lines.add(idx)
        self.update()
        self.linesSelected.emit(sorted(list(self._selected_lines)))

    def set_drag_lock(self, line_index: int):
        """Lock dragging to only the specified line."""
        self._drag_locked_line = line_index
        self.select_line(line_index, add_to_selection=False)
        self.update()

    def clear_drag_lock(self):
        """Clear drag lock, allow dragging all lines."""
        self._drag_locked_line = -1
        self.update()

    # ========== Backward Compatibility (for simple components) ==========

    def get_points(self) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
        """Get first line as point pair (backward compatibility)."""
        if len(self._lines) > 0:
            line = self._lines[0]
            return (line.x1, line.y1), (line.x2, line.y2)
        return None, None

    def set_points(self, p1: tuple[float, float] | None, p2: tuple[float, float] | None):
        """Set first line from point pair (backward compatibility)."""
        if p1 and p2:
            if len(self._lines) == 0:
                # Create new line
                line = InterfaceLine(
                    x1=p1[0], y1=p1[1], x2=p2[0], y2=p2[1], color=QtGui.QColor(100, 100, 255)
                )
                self._lines.append(line)
            else:
                # Update existing line
                self._lines[0].x1 = p1[0]
                self._lines[0].y1 = p1[1]
                self._lines[0].x2 = p2[0]
                self._lines[0].y2 = p2[1]
            self.update()
            self.linesChanged.emit()

    def clear_points(self):
        """Clear all lines (backward compatibility)."""
        self.clear_lines()

    # ========== Rendering ==========

    def _target_rect(self) -> QtCore.QRect:
        """Compute scaled image rectangle and update coordinate system."""
        if not self._pix:
            return QtCore.QRect()

        w_label = self.width()
        h_label = self.height()
        w_pix = self._pix.width()
        h_pix = self._pix.height()

        if w_pix == 0 or h_pix == 0:
            return QtCore.QRect()

        # Scale to fit
        scale_w = w_label / w_pix
        scale_h = h_label / h_pix
        self._scale_fit = min(scale_w, scale_h)

        scaled_w = int(w_pix * self._scale_fit)
        scaled_h = int(h_pix * self._scale_fit)

        # Center
        x0 = (w_label - scaled_w) // 2
        y0 = (h_label - scaled_h) // 2

        rect = QtCore.QRect(x0, y0, scaled_w, scaled_h)

        # Update coordinate system
        self._coord_system.update_params(rect, self._scale_fit, self._mm_per_px)

        return rect

    def paintEvent(self, e: QtGui.QPaintEvent | None):
        """Draw image and all lines."""
        super().paintEvent(e)

        if not self._pix or self._pix.isNull():
            return

        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        # Draw image
        target = self._target_rect()

        # Use cached SVG pixmap if available for better performance
        if self._svg_renderer is not None and self._svg_cache_pixmap is not None:
            # Check if we need to update cache due to significant resize
            if (
                target.width() > self._svg_cache_size.width() * 1.2
                or target.height() > self._svg_cache_size.height() * 1.2
            ):
                self._update_svg_cache()

            # Draw cached pixmap with smooth transformation
            p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
            p.drawPixmap(target, self._svg_cache_pixmap)
        else:
            p.drawPixmap(target, self._pix)

        # Draw all lines using the renderer
        for i, line in enumerate(self._lines):
            self._renderer.draw_line(
                p,
                target,
                line,
                i,
                self._selected_lines,
                self._hover_line,
                self._hover_point,
                self._drag_locked_line,
            )

        # Draw selection rectangle
        if self._rect_selecting and self._rect_start and self._rect_end:
            rect = QtCore.QRect(self._rect_start, self._rect_end).normalized()
            p.setPen(QtGui.QPen(QtGui.QColor(100, 150, 255), 2, QtCore.Qt.PenStyle.DashLine))
            p.setBrush(QtGui.QBrush(QtGui.QColor(100, 150, 255, 30)))
            p.drawRect(rect)

        # Draw bounding box around selected lines
        if len(self._selected_lines) > 1 and not self._rect_selecting:
            self._renderer.draw_bounding_box(
                p, target, self._lines, self._selected_lines, self._coord_system
            )

    # ========== Mouse Interaction ==========

    def _get_line_and_point_at(
        self, screen_pos: QtCore.QPoint, threshold: float = 10.0
    ) -> tuple[int, int]:
        """
        Find line and point at screen position.

        Returns:
            (line_index, point_number) where point_number is 1 or 2, or (-1, 0) if none
        """
        if not self._pix or not self._coord_system.is_valid:
            return (-1, 0)

        img_rect = self._target_rect()
        if not img_rect.contains(screen_pos):
            return (-1, 0)

        # Check all lines (prioritize selected lines)
        search_order = list(range(len(self._lines)))
        if self._selected_lines:
            # Check selected lines first (in order)
            selected_sorted = sorted(list(self._selected_lines), reverse=True)
            for sel_idx in selected_sorted:
                if sel_idx in search_order:
                    search_order.remove(sel_idx)
                    search_order.insert(0, sel_idx)

        for i in search_order:
            line = self._lines[i]

            # Convert to screen coordinates using coordinate system
            x1_screen, y1_screen = self._coord_system.mm_to_screen(line.x1, line.y1)
            x2_screen, y2_screen = self._coord_system.mm_to_screen(line.x2, line.y2)

            # Check point 2 first (so it takes priority if overlapping)
            dx = screen_pos.x() - x2_screen
            dy = screen_pos.y() - y2_screen
            if (dx * dx + dy * dy) <= threshold * threshold:
                return (i, 2)

            # Check point 1
            dx = screen_pos.x() - x1_screen
            dy = screen_pos.y() - y1_screen
            if (dx * dx + dy * dy) <= threshold * threshold:
                return (i, 1)

        return (-1, 0)

    def _get_line_at_position(self, screen_pos: QtCore.QPoint, threshold: float = 5.0) -> int:
        """
        Find line body at screen position (not just endpoints).

        Returns:
            Line index, or -1 if no line is near the position
        """
        if not self._pix or not self._coord_system.is_valid:
            return -1

        img_rect = self._target_rect()
        if not img_rect.contains(screen_pos):
            return -1

        # Check all lines in reverse order (prioritize top lines)
        for i in range(len(self._lines) - 1, -1, -1):
            line = self._lines[i]

            # Convert to screen coordinates using coordinate system
            x1_screen, y1_screen = self._coord_system.mm_to_screen(line.x1, line.y1)
            x2_screen, y2_screen = self._coord_system.mm_to_screen(line.x2, line.y2)

            # Calculate distance from point to line segment
            px, py = screen_pos.x(), screen_pos.y()

            # Vector from line start to end
            dx = x2_screen - x1_screen
            dy = y2_screen - y1_screen

            # Squared length of line
            len_sq = dx * dx + dy * dy

            if len_sq < 0.01:  # Degenerate line (too short)
                continue

            # Parameter t along line (clamped to [0, 1])
            t = max(0.0, min(1.0, ((px - x1_screen) * dx + (py - y1_screen) * dy) / len_sq))

            # Closest point on line segment
            closest_x = x1_screen + t * dx
            closest_y = y1_screen + t * dy

            # Distance to closest point
            dist_sq = (px - closest_x) ** 2 + (py - closest_y) ** 2

            if dist_sq <= threshold * threshold:
                return i

        return -1

    def _segments_intersect(
        self, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, x4: float, y4: float
    ) -> bool:
        """
        Check if two line segments intersect.

        Args:
            (x1, y1) - (x2, y2): First line segment
            (x3, y3) - (x4, y4): Second line segment

        Returns:
            True if segments intersect
        """
        # Calculate direction vectors
        dx1 = x2 - x1
        dy1 = y2 - y1
        dx2 = x4 - x3
        dy2 = y4 - y3

        # Calculate determinant
        det = dx1 * dy2 - dy1 * dx2

        if abs(det) < 1e-10:  # Lines are parallel
            return False

        # Calculate intersection parameters
        t1 = ((x3 - x1) * dy2 - (y3 - y1) * dx2) / det
        t2 = ((x3 - x1) * dy1 - (y3 - y1) * dx1) / det

        # Check if intersection is within both segments
        return 0 <= t1 <= 1 and 0 <= t2 <= 1

    def _line_intersects_rect(
        self, x1: float, y1: float, x2: float, y2: float, rect: QtCore.QRect
    ) -> bool:
        """
        Check if line segment intersects with rectangle.

        Args:
            (x1, y1) - (x2, y2): Line segment in screen coordinates
            rect: Rectangle to check

        Returns:
            True if line intersects or is inside rectangle
        """
        # Check if either endpoint is inside rectangle
        if rect.contains(QtCore.QPoint(int(x1), int(y1))):
            return True
        if rect.contains(QtCore.QPoint(int(x2), int(y2))):
            return True

        # Get rectangle edges
        left = float(rect.left())
        top = float(rect.top())
        right = float(rect.right())
        bottom = float(rect.bottom())

        # Check intersection with each rectangle edge
        # Top edge
        if self._segments_intersect(x1, y1, x2, y2, left, top, right, top):
            return True
        # Right edge
        if self._segments_intersect(x1, y1, x2, y2, right, top, right, bottom):
            return True
        # Bottom edge
        if self._segments_intersect(x1, y1, x2, y2, right, bottom, left, bottom):
            return True
        # Left edge
        if self._segments_intersect(x1, y1, x2, y2, left, bottom, left, top):
            return True

        return False

    def _get_lines_in_rect(self, rect: QtCore.QRect) -> list[int]:
        """
        Find all lines that intersect with the given rectangle.

        Returns:
            List of line indices
        """
        if not self._pix or not self._coord_system.is_valid:
            return []

        self._target_rect()  # Ensure coordinate system is updated

        result = []

        for i, line in enumerate(self._lines):
            # Convert to screen coordinates using coordinate system
            x1_screen, y1_screen = self._coord_system.mm_to_screen(line.x1, line.y1)
            x2_screen, y2_screen = self._coord_system.mm_to_screen(line.x2, line.y2)

            # Check if line intersects with rectangle
            if self._line_intersects_rect(x1_screen, y1_screen, x2_screen, y2_screen, rect):
                result.append(i)

        return result

    def mousePressEvent(self, e: QtGui.QMouseEvent | None):
        """Handle mouse press."""
        if e is None or not self._pix or e.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        # Check if clicking on an endpoint
        line_idx, point_num = self._get_line_and_point_at(e.pos())

        if line_idx >= 0:
            # Clicked on an endpoint

            # Check drag lock
            if self._drag_locked_line >= 0 and line_idx != self._drag_locked_line:
                return

            # Start dragging endpoint
            self._dragging_line = line_idx
            self._dragging_point = point_num
            self._dragging_entire_lines = False
            self.select_line(line_idx, add_to_selection=False)

            # Track initial position for undo
            line = self._lines[line_idx]
            self._drag_initial_lines = [(line.x1, line.y1, line.x2, line.y2)]
            self._drag_moved_indices = [line_idx]

            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            return

        # Check if clicking on a line body
        line_body_idx = self._get_line_at_position(e.pos())

        if line_body_idx >= 0:
            # Clicked on a line body - start translation drag

            # Check drag lock
            if self._drag_locked_line >= 0 and line_body_idx != self._drag_locked_line:
                return

            # If not already selected, select this line
            if line_body_idx not in self._selected_lines:
                self.select_line(line_body_idx, add_to_selection=False)

            # Start dragging entire line(s)
            self._dragging_entire_lines = True
            pos = e.pos()
            self._drag_start_pos = QtCore.QPointF(pos.x(), pos.y()).toPointF() if hasattr(e.pos(), 'toPointF') else QtCore.QPointF(e.pos())

            # Store initial positions of all selected lines for undo
            self._drag_initial_lines.clear()
            self._drag_moved_indices = []
            for idx in sorted(self._selected_lines):
                if 0 <= idx < len(self._lines):
                    line = self._lines[idx]
                    self._drag_initial_lines.append((line.x1, line.y1, line.x2, line.y2))
                    self._drag_moved_indices.append(idx)

            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            return

        # Click on empty space - start rectangle selection or clear selection
        img_rect = self._target_rect()
        if img_rect.contains(e.pos()):
            # If drag locked, clicking empty space clears the lock
            if self._drag_locked_line >= 0:
                self.clear_drag_lock()
            else:
                # Start rectangle selection
                self._rect_selecting = True
                self._rect_start = e.pos()
                self._rect_end = e.pos()
                self.update()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent | None):
        """Handle mouse move."""
        if e is None:
            return
        if self._rect_selecting:
            # Update rectangle selection
            self._rect_end = e.pos()
            self.update()
            return

        if self._dragging_entire_lines:
            # Dragging entire line(s) - translation mode
            if not self._drag_start_pos or not self._drag_initial_lines:
                return

            self._target_rect()  # Ensure coordinate system is updated
            if not self._coord_system.is_valid:
                return

            # Calculate drag delta in screen coordinates
            delta_x_screen = e.pos().x() - self._drag_start_pos.x()
            delta_y_screen = e.pos().y() - self._drag_start_pos.y()

            # Apply axis lock if Ctrl/Cmd is pressed
            modifiers = e.modifiers()
            if modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
                # Lock to primary axis
                if abs(delta_x_screen) > abs(delta_y_screen):
                    delta_y_screen = 0
                else:
                    delta_x_screen = 0

            # Convert delta to millimeters using coordinate system
            delta_x_mm, delta_y_mm = self._coord_system.screen_delta_to_mm(
                delta_x_screen, delta_y_screen
            )

            # Update all selected lines
            selected_indices = sorted(list(self._selected_lines))
            for i, idx in enumerate(selected_indices):
                if i < len(self._drag_initial_lines) and 0 <= idx < len(self._lines):
                    initial_x1, initial_y1, initial_x2, initial_y2 = self._drag_initial_lines[i]
                    line = self._lines[idx]

                    # Move both endpoints by the same delta (preserves angle)
                    line.x1 = initial_x1 + delta_x_mm
                    line.y1 = initial_y1 + delta_y_mm
                    line.x2 = initial_x2 + delta_x_mm
                    line.y2 = initial_y2 + delta_y_mm

            self.update()
            self.linesChanged.emit()
            return

        if self._dragging_line >= 0:
            # Dragging an endpoint
            self._target_rect()  # Ensure coordinate system is updated
            if not self._coord_system.is_valid:
                return

            # Convert screen coordinates to mm coordinates
            x_mm, y_mm = self._coord_system.screen_to_mm(e.pos().x(), e.pos().y())

            # Clamp to image bounds
            w, h = self.image_pixel_size()
            half_width_mm = (w / 2) * self._mm_per_px
            half_height_mm = (h / 2) * self._mm_per_px
            x_mm = max(-half_width_mm, min(half_width_mm, x_mm))
            y_mm = max(-half_height_mm, min(half_height_mm, y_mm))

            # Update line (stored in mm)
            line = self._lines[self._dragging_line]
            if self._dragging_point == 1:
                line.x1 = x_mm
                line.y1 = y_mm
            else:
                line.x2 = x_mm
                line.y2 = y_mm

            self.update()
            self.linesChanged.emit()
        else:
            # Hover detection
            line_idx, point_num = self._get_line_and_point_at(e.pos())

            # Check if we can interact with this line
            can_interact = True
            if self._drag_locked_line >= 0:
                # Drag lock active - only allow interaction with locked line
                can_interact = line_idx == self._drag_locked_line

            if line_idx >= 0 and can_interact:
                self._hover_line = line_idx
                self._hover_point = point_num
                self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            else:
                # Check if hovering over line body
                line_body_idx = self._get_line_at_position(e.pos())
                if line_body_idx >= 0:
                    self._hover_line = line_body_idx
                    self._hover_point = 0
                    self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
                else:
                    self._hover_line = -1
                    self._hover_point = 0
                    self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

            self.update()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent | None):
        """Handle mouse release."""
        if e is None:
            return
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            # Handle rectangle selection completion
            if self._rect_selecting:
                self._rect_selecting = False
                if self._rect_start and self._rect_end:
                    rect = QtCore.QRect(self._rect_start, self._rect_end).normalized()
                    selected_lines = self._get_lines_in_rect(rect)
                    if selected_lines:
                        self.select_lines(selected_lines)
                    else:
                        # Empty selection - clear selection
                        self.select_line(-1)
                self._rect_start = None
                self._rect_end = None
                self.update()
                return

            # Handle drag release
            # Check if anything was actually moved (for undo)
            if self._drag_initial_lines and self._drag_moved_indices:
                # Capture new positions
                new_positions = []
                for idx in self._drag_moved_indices:
                    if 0 <= idx < len(self._lines):
                        line = self._lines[idx]
                        new_positions.append((line.x1, line.y1, line.x2, line.y2))

                # Only emit if positions actually changed
                if new_positions != self._drag_initial_lines:
                    self.linesMoved.emit(
                        self._drag_moved_indices, self._drag_initial_lines, new_positions
                    )

            self._dragging_line = -1
            self._dragging_point = 0
            self._dragging_entire_lines = False
            self._drag_start_pos = None
            self._drag_initial_lines.clear()
            self._drag_moved_indices.clear()
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    # ========== Drag & Drop ==========

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent | None):
        """Accept image drops."""
        if e is None:
            return
        mime_data = e.mimeData()
        if mime_data is not None and (mime_data.hasImage() or mime_data.hasUrls()):
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e: QtGui.QDropEvent | None):
        """Handle dropped image."""
        if e is None:
            return
        md = e.mimeData()
        if md is None:
            return

        if md.hasImage():
            img_data = md.imageData()
            if img_data is not None:
                img = QtGui.QImage(img_data)
                if not img.isNull():
                    pix = QtGui.QPixmap.fromImage(img)
                    self.imageDropped.emit(pix, "")
        elif md.hasUrls():
            urls = md.urls()
            if urls:
                path = urls[0].toLocalFile()
                if path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".svg")):
                    if path.lower().endswith(".svg") and HAVE_QTSVG:
                        pix = self._render_svg_to_pixmap(path)
                        if pix is None:
                            continue
                    else:
                        pix = QtGui.QPixmap(path)

                    if pix and not pix.isNull():
                        self.imageDropped.emit(pix, path)

    def _update_svg_cache(self):
        """Update the cached SVG pixmap at optimal resolution."""
        if not self._svg_renderer or not self._pix:
            return

        # Calculate target size (2x current display size for quality)
        tgt = self._target_rect()
        target_width = max(tgt.width() * 2, 800)
        target_height = max(tgt.height() * 2, 600)

        # Get SVG aspect ratio
        default_size = self._svg_renderer.defaultSize()
        if default_size.width() > 0 and default_size.height() > 0:
            aspect = default_size.width() / default_size.height()
            # Maintain aspect ratio
            if target_width / target_height > aspect:
                target_width = int(target_height * aspect)
            else:
                target_height = int(target_width / aspect)

        cache_size = QtCore.QSize(int(target_width), int(target_height))

        # Render SVG to cache
        self._svg_cache_pixmap = QtGui.QPixmap(cache_size)
        self._svg_cache_pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(self._svg_cache_pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        self._svg_renderer.render(painter)
        painter.end()

        self._svg_cache_size = cache_size

    @staticmethod
    def _render_svg_to_pixmap(svg_path: str, size: int = 1000) -> QtGui.QPixmap | None:
        """Render SVG to pixmap at normalized height."""
        if not HAVE_QTSVG:
            return None

        renderer = QtSvg.QSvgRenderer(svg_path)
        if not renderer.isValid():
            return None

        default_size = renderer.defaultSize()
        aspect = default_size.width() / default_size.height() if default_size.height() > 0 else 1.0
        target_size = QtCore.QSize(int(size * aspect), size)

        pix = QtGui.QPixmap(target_size)
        pix.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(pix)
        renderer.render(painter)
        painter.end()

        return pix

    # ========== Ruler Support ==========

    def _screen_to_mm_coords(self, screen_pos: QtCore.QPoint) -> tuple[float, float]:
        """
        Convert screen coordinates to mm coordinates.

        Returns:
            (x_mm, y_mm) tuple
        """
        self._target_rect()  # Ensure coordinate system is updated
        result = self._coord_system.screen_to_mm_from_point(screen_pos)
        return cast(tuple[float, float], result)

    def _get_ruler_view_params(self) -> dict:
        """
        Get view parameters for rulers.

        Returns:
            Dictionary with ruler parameters:
            - h_scale: horizontal scale (screen pixels per mm)
            - h_offset: horizontal offset (where 0mm appears on screen)
            - h_range: tuple of (min_mm, max_mm) for horizontal axis
            - v_scale: vertical scale (screen pixels per mm)
            - v_offset: vertical offset (where 0mm appears on screen)
            - v_range: tuple of (min_mm, max_mm) for vertical axis
            - show_mm: whether to show mm units
        """
        self._target_rect()  # Ensure coordinate system is updated
        w, h = self.image_pixel_size()
        result = self._coord_system.get_ruler_params(w, h)
        return cast(dict[str, Any], result)
