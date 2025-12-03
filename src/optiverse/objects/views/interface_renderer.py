"""
Interface Renderer - Draws optical interface lines on a canvas.

Extracted from MultiLineCanvas to reduce file size and improve separation
of concerns. Handles all visual rendering of interface lines including:
- Straight and curved surfaces
- Refractive index indicators
- Selection highlighting
- Endpoint markers
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui

if TYPE_CHECKING:
    from .multi_line_canvas import InterfaceLine


class InterfaceRenderer:
    """
    Renders optical interface lines to a QPainter.

    This class encapsulates all the drawing logic for interface lines,
    including special handling for curved surfaces and refractive indices.
    """

    def __init__(self, coord_system):
        """
        Initialize the renderer.

        Args:
            coord_system: CanvasCoordinateSystem for mm <-> screen conversion
        """
        self._coord_system = coord_system

    def draw_line(
        self,
        p: QtGui.QPainter,
        img_rect: QtCore.QRect,
        line: InterfaceLine,
        index: int,
        selected_lines: set,
        hover_line: int,
        hover_point: int,
        drag_locked_line: int,
    ) -> None:
        """
        Draw a single interface line with all visual effects.

        Args:
            p: QPainter to draw on
            img_rect: Image rectangle for bounds
            line: The InterfaceLine to draw
            index: Line index in the collection
            selected_lines: Set of selected line indices
            hover_line: Index of line being hovered (-1 if none)
            hover_point: Which point is being hovered (1 or 2)
            drag_locked_line: Index of drag-locked line (-1 if none)
        """
        # Use coordinate system for conversions
        x1_screen, y1_screen = self._coord_system.mm_to_screen(line.x1, line.y1)
        x2_screen, y2_screen = self._coord_system.mm_to_screen(line.x2, line.y2)

        # Determine appearance
        is_selected = index in selected_lines
        is_hovering = index == hover_line
        is_locked = drag_locked_line >= 0 and index == drag_locked_line
        is_dimmed = drag_locked_line >= 0 and index != drag_locked_line

        # Line color and width
        color = line.color
        if color is None:
            color = QtGui.QColor(100, 100, 255)  # Default blue
        if is_dimmed:
            # Dim non-locked lines
            color = QtGui.QColor(color.red(), color.green(), color.blue(), 80)
            pen = QtGui.QPen(color, 1.5)
        elif is_selected or is_locked:
            pen = QtGui.QPen(color, 3)
        elif is_hovering:
            pen = QtGui.QPen(color, 2.5)
        else:
            pen = QtGui.QPen(color, 2)

        p.setPen(pen)

        # Check if this is a curved surface
        interface = line.properties.get("interface") if line.properties else None
        is_curved = interface and hasattr(interface, "is_curved") and interface.is_curved

        if is_curved and interface and abs(interface.radius_of_curvature_mm) > 0.1:
            # Draw curved surface as an arc
            self._draw_curved_line(
                p,
                x1_screen,
                y1_screen,
                x2_screen,
                y2_screen,
                interface.radius_of_curvature_mm,
                img_rect,
            )
        else:
            # Draw straight line
            p.drawLine(QtCore.QPointF(x1_screen, y1_screen), QtCore.QPointF(x2_screen, y2_screen))

        # Draw refractive index indicator
        if not is_dimmed and line.properties:
            interface = line.properties.get("interface")
            if interface and interface.element_type == "refractive_interface":
                if abs(interface.n1 - interface.n2) > 0.01:
                    self._draw_refractive_index_indicator(
                        p, x1_screen, y1_screen, x2_screen, y2_screen, interface, img_rect
                    )

        # Draw endpoints
        if not is_dimmed:
            base_color = line.color
            if base_color is None:
                base_color = QtGui.QColor(100, 100, 255)  # Default blue
            point_color = base_color.lighter(120) if (is_selected or is_locked) else base_color
            p.setPen(QtGui.QPen(point_color, 1))
            p.setBrush(QtGui.QBrush(point_color))

            # Point 1
            pt1_size = 6 if (is_selected or is_locked or (is_hovering and hover_point == 1)) else 5
            p.drawEllipse(QtCore.QPointF(x1_screen, y1_screen), pt1_size, pt1_size)

            # Point 2
            pt2_size = 6 if (is_selected or is_locked or (is_hovering and hover_point == 2)) else 5
            p.drawEllipse(QtCore.QPointF(x2_screen, y2_screen), pt2_size, pt2_size)

        # Draw refractive index labels
        if not is_dimmed and line.properties:
            interface = line.properties.get("interface")
            if interface and interface.element_type == "refractive_interface":
                if abs(interface.n1 - interface.n2) > 0.01:
                    # Ensure color is not None before passing
                    label_color = color if color is not None else QtGui.QColor(100, 100, 255)
                    self._draw_refractive_index_labels(
                        p,
                        x1_screen,
                        y1_screen,
                        x2_screen,
                        y2_screen,
                        interface.n1,
                        interface.n2,
                        label_color,
                    )

        # Draw label if exists
        if line.label and is_selected:
            p.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black))
            mid_x = (x1_screen + x2_screen) / 2
            mid_y = (y1_screen + y2_screen) / 2
            p.drawText(QtCore.QPointF(mid_x + 10, mid_y - 10), line.label)

    def _draw_refractive_index_labels(
        self,
        p: QtGui.QPainter,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        n1: float,
        n2: float,
        line_color: QtGui.QColor,
    ) -> None:
        """
        Draw refractive index labels near the endpoints.

        Args:
            p: QPainter instance
            x1, y1: First endpoint (screen coordinates)
            x2, y2: Second endpoint (screen coordinates)
            n1, n2: Refractive indices at each side
            line_color: Color of the interface line
        """
        # Calculate line direction and perpendicular
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-6:
            return

        # Normal vector (perpendicular to line, pointing "left" from p1 to p2)
        nx = -dy / length
        ny = dx / length

        # Position labels at fixed offsets from line center
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Offset from line center
        label_offset = 25

        # n1 label (left side)
        n1_x = mid_x + nx * label_offset
        n1_y = mid_y + ny * label_offset

        # n2 label (right side)
        n2_x = mid_x - nx * label_offset
        n2_y = mid_y - ny * label_offset

        # Use a contrasting background
        font = p.font()
        font.setPointSize(9)
        p.setFont(font)

        # Draw background rectangles for readability
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        bg_color = QtGui.QColor(255, 255, 255, 200)
        p.setBrush(QtGui.QBrush(bg_color))

        # n1 label
        n1_text = f"n={n1:.3f}"
        metrics = p.fontMetrics()
        rect1 = metrics.boundingRect(n1_text)
        rect1.moveCenter(QtCore.QPoint(int(n1_x), int(n1_y)))
        rect1.adjust(-3, -2, 3, 2)
        p.drawRoundedRect(rect1, 3, 3)

        # n2 label
        n2_text = f"n={n2:.3f}"
        rect2 = metrics.boundingRect(n2_text)
        rect2.moveCenter(QtCore.QPoint(int(n2_x), int(n2_y)))
        rect2.adjust(-3, -2, 3, 2)
        p.drawRoundedRect(rect2, 3, 3)

        # Draw text
        p.setPen(QtGui.QPen(line_color.darker(150)))
        p.drawText(rect1, QtCore.Qt.AlignmentFlag.AlignCenter, n1_text)
        p.drawText(rect2, QtCore.Qt.AlignmentFlag.AlignCenter, n2_text)

    def _draw_refractive_index_indicator(
        self,
        p: QtGui.QPainter,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        interface,
        img_rect: QtCore.QRect,
    ) -> None:
        """
        Draw a half-and-half colored circle at the midpoint of a refractive interface.

        The circle is split perpendicular to the line direction (or tangent for curved lines):
        - Left half (toward n1 endpoint): Yellow
        - Right half (toward n2 endpoint): Purple

        Args:
            p: QPainter instance
            x1, y1: First endpoint (screen coordinates) - n1 side
            x2, y2: Second endpoint (screen coordinates) - n2 side
            interface: InterfaceDefinition object with curvature info
            img_rect: Image rectangle for coordinate conversion
        """
        # Check if this is a curved interface
        is_curved = interface and hasattr(interface, "is_curved") and interface.is_curved
        has_curvature = (
            is_curved
            and hasattr(interface, "radius_of_curvature_mm")
            and abs(interface.radius_of_curvature_mm) > 0.1
        )

        # Calculate chord properties
        dx = x2 - x1
        dy = y2 - y1
        chord_length = math.sqrt(dx * dx + dy * dy)

        if chord_length < 1:
            return  # Line too short, skip indicator

        # Default to chord midpoint and direction
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        tangent_angle_rad = math.atan2(dy, dx)

        # For curved lines, calculate arc midpoint and tangent
        if has_curvature:
            radius_mm = interface.radius_of_curvature_mm
            radius_px = self._coord_system.mm_to_screen_radius(radius_mm)

            # Only adjust for curves if radius is reasonable relative to chord
            if radius_px >= chord_length / 2:
                # Calculate arc center (SAME logic as _draw_curved_line)
                half_chord = chord_length / 2
                h = math.sqrt(radius_px * radius_px - half_chord * half_chord)

                # Normal to chord (perpendicular direction)
                nx = -dy / chord_length
                ny = dx / chord_length

                # Chord midpoint
                chord_mid_x = (x1 + x2) / 2
                chord_mid_y = (y1 + y2) / 2

                # Arc center (same signs as _draw_curved_line)
                if radius_mm > 0:
                    center_x = chord_mid_x - nx * h
                    center_y = chord_mid_y - ny * h
                else:
                    center_x = chord_mid_x + nx * h
                    center_y = chord_mid_y + ny * h

                # Calculate angles from center to endpoints
                angle1 = math.atan2(y1 - center_y, x1 - center_x)
                angle2 = math.atan2(y2 - center_y, x2 - center_x)

                # Arc midpoint angle (average of endpoint angles)
                # Need to handle wraparound correctly
                angle_diff = angle2 - angle1
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi

                mid_angle = angle1 + angle_diff / 2

                # Arc midpoint position (point on circle at mid_angle)
                mid_x = center_x + radius_px * math.cos(mid_angle)
                mid_y = center_y + radius_px * math.sin(mid_angle)

                # Tangent at arc midpoint is perpendicular to radial direction
                tangent_angle_rad = mid_angle + math.pi / 2

        # Circle properties
        circle_radius = 8  # pixels

        # Define colors (matching the property panel indicators)
        yellow_n1 = QtGui.QColor(255, 215, 0)  # Yellow for n1 side (#FFD700)
        purple_n2 = QtGui.QColor(147, 112, 219)  # Purple for n2 side (#9370DB)

        # Save painter state
        p.save()

        # Draw the circle split ALONG the line direction
        # The split line runs parallel to the interface
        # Yellow on the n1 side (toward point 1), Purple on the n2 side (toward point 2)

        p.setPen(QtCore.Qt.PenStyle.NoPen)

        # The split should align with the line direction
        # For a vertical line (90deg), split should be vertical
        # For a horizontal line (0deg), split should be horizontal
        # To split ALONG the line (not perpendicular), we rotate by 90deg and negate to fix direction

        # Draw n1 half (Yellow) - the half toward point 1
        p.setBrush(QtGui.QBrush(yellow_n1))
        start_angle_deg = -math.degrees(tangent_angle_rad)
        span_angle_deg = 180

        rect = QtCore.QRectF(
            mid_x - circle_radius,
            mid_y - circle_radius,
            circle_radius * 2,
            circle_radius * 2,
        )
        p.drawPie(rect, int(start_angle_deg * 16), int(span_angle_deg * 16))

        # Draw n2 half (Purple) - the half toward point 2
        p.setBrush(QtGui.QBrush(purple_n2))
        start_angle_deg = 180 - math.degrees(tangent_angle_rad)
        p.drawPie(rect, int(start_angle_deg * 16), int(span_angle_deg * 16))

        # Draw outline for better visibility
        p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 180), 1))
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect)

        # Restore painter state
        p.restore()

    def _draw_curved_line(
        self,
        p: QtGui.QPainter,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius_mm: float,
        img_rect: QtCore.QRect,
    ) -> None:
        """
        Draw a curved surface as an arc.

        Args:
            p: QPainter instance
            x1, y1: First endpoint (screen coordinates)
            x2, y2: Second endpoint (screen coordinates)
            radius_mm: Radius of curvature in mm (positive = convex left)
            img_rect: Image rectangle for bounds
        """
        # Convert radius to screen pixels
        radius_px = self._coord_system.mm_to_screen_radius(radius_mm)

        # Calculate chord properties
        dx = x2 - x1
        dy = y2 - y1
        chord = math.sqrt(dx * dx + dy * dy)

        if chord < 1e-6 or radius_px < chord / 2:
            # Degenerate case: draw straight line
            p.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2))
            return

        # Midpoint of the chord
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Distance from midpoint to arc center
        half_chord = chord / 2
        h = math.sqrt(radius_px * radius_px - half_chord * half_chord)

        # Normal to chord (perpendicular direction)
        nx = -dy / chord
        ny = dx / chord

        # Arc center (on one side of the chord based on radius sign)
        # Note: radius_mm sign is defined in mm (Y-up) coords, but (nx, ny) is in screen (Y-down)
        # The Y-flip reverses the perpendicular direction, so we use opposite signs
        if radius_mm > 0:
            cx = mid_x - nx * h
            cy = mid_y - ny * h
        else:
            cx = mid_x + nx * h
            cy = mid_y + ny * h

        # Calculate start and end angles
        # Note: Qt's arcTo uses Y-up angle convention (90° = up), but we're in screen coords (Y-down)
        # Negate Y differences to convert from screen to Qt's angle convention
        angle1 = math.degrees(math.atan2(cy - y1, x1 - cx))
        angle2 = math.degrees(math.atan2(cy - y2, x2 - cx))

        # Ensure we draw the correct arc (shorter one)
        span = angle2 - angle1
        if span > 180:
            span -= 360
        elif span < -180:
            span += 360

        # Create arc rectangle
        rect = QtCore.QRectF(cx - radius_px, cy - radius_px, radius_px * 2, radius_px * 2)

        # Draw the arc (stroke only, no fill)
        path = QtGui.QPainterPath()
        path.arcMoveTo(rect, angle1)
        path.arcTo(rect, angle1, span)
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def draw_bounding_box(
        self,
        p: QtGui.QPainter,
        img_rect: QtCore.QRect,
        lines: list,
        selected_lines: set,
        coord_system,
    ) -> None:
        """
        Draw a bounding box around selected lines.

        Args:
            p: QPainter instance
            img_rect: Image rectangle for bounds
            lines: List of all InterfaceLines
            selected_lines: Set of selected line indices
            coord_system: Coordinate system for conversion
        """
        if len(selected_lines) < 2:
            return

        # Calculate bounding box of all selected lines
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        for idx in selected_lines:
            if 0 <= idx < len(lines):
                line = lines[idx]
                x1_s, y1_s = coord_system.mm_to_screen(line.x1, line.y1)
                x2_s, y2_s = coord_system.mm_to_screen(line.x2, line.y2)
                min_x = min(min_x, x1_s, x2_s)
                min_y = min(min_y, y1_s, y2_s)
                max_x = max(max_x, x1_s, x2_s)
                max_y = max(max_y, y1_s, y2_s)

        if min_x == float("inf"):
            return

        # Add padding
        padding = 10
        min_x -= padding
        min_y -= padding
        max_x += padding
        max_y += padding

        # Draw dashed rectangle
        pen = QtGui.QPen(QtGui.QColor(100, 100, 255, 150))
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.drawRect(QtCore.QRectF(min_x, min_y, max_x - min_x, max_y - min_y))
