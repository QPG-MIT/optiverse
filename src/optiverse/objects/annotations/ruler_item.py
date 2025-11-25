from __future__ import annotations

import math
import uuid
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.ui_constants import (
    RULER_BAR_HEIGHT,
    RULER_BAR_WIDTH,
    RULER_BOUNDING_PAD_PX,
    RULER_HIT_RADIUS_PX,
    RULER_LABEL_BG_ALPHA,
    RULER_LABEL_BG_ALPHA_SELECTED,
    RULER_LABEL_CORNER_RADIUS,
    RULER_LABEL_PADDING,
    RULER_LINE_WIDTH,
    RULER_LINE_WIDTH_SELECTED,
    RULER_MIN_STROKE_WIDTH_PX,
    RULER_POINT_CHANGE_THRESHOLD,
    RULER_TOTAL_LABEL_ALONG_OFFSET,
    RULER_TOTAL_LABEL_PERP_OFFSET,
)
from ...core.zorder_utils import handle_z_order_from_menu


class RulerItem(QtWidgets.QGraphicsObject):
    """
    Draggable multi-segment ruler that shows the distance in mm.

    Features:
    - Drag endpoint bars to measure; drag elsewhere to move as a whole.
    - Right-click → Delete, Add Bend, or Delete Point (for bends).
    - Supports multiple segments with bends.
    - Undo/redo support via commandCreated signal.

    Public API for point manipulation:
    - get_points(): Get a copy of all points
    - set_point(index, pos): Set a specific point's position
    - set_preview_point(pos): Update the last point (during placement)
    - finalize_segment(pos): Finalize current segment and add preview point
    - remove_preview_point(): Remove the last (preview) point
    - point_count(): Get number of points
    """

    # Signal emitted when an undo command is created
    commandCreated = QtCore.pyqtSignal(object)

    # Signal emitted when item requests deletion (for undoable delete)
    requestDelete = QtCore.pyqtSignal(object)  # Emits self

    def __init__(
        self,
        p1: QtCore.QPointF = QtCore.QPointF(-50, 0),
        p2: QtCore.QPointF = QtCore.QPointF(50, 0),
        item_uuid: str | None = None,
        points: list[QtCore.QPointF] | None = None,
    ):
        super().__init__()
        # Generate or use provided UUID for collaboration
        self.item_uuid = item_uuid if item_uuid else str(uuid.uuid4())

        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)
        self.setZValue(10_000)  # keep ruler + label on top

        # Support both old (p1/p2) and new (points) initialization for backward compatibility
        if points is not None:
            self._points = [QtCore.QPointF(p) for p in points]
        else:
            self._points = [QtCore.QPointF(p1), QtCore.QPointF(p2)]

        # Ensure at least 2 points
        if len(self._points) < 2:
            self._points = [QtCore.QPointF(-50, 0), QtCore.QPointF(50, 0)]

        # Interaction state
        self._grab: int | None = None  # index of grabbed point, or None
        self._initial_points: list[QtCore.QPointF] | None = None  # Track for undo

    # ========== Public API for Point Manipulation ==========

    def get_points(self) -> list[QtCore.QPointF]:
        """Return a copy of all points."""
        return [QtCore.QPointF(p) for p in self._points]

    def set_point(self, index: int, pos: QtCore.QPointF) -> None:
        """Set a specific point's position."""
        if 0 <= index < len(self._points):
            self.prepareGeometryChange()
            self._points[index] = QtCore.QPointF(pos)
            self.update()

    def set_preview_point(self, pos: QtCore.QPointF) -> None:
        """Update the last point (preview during placement)."""
        if len(self._points) >= 2:
            self.prepareGeometryChange()
            self._points[-1] = QtCore.QPointF(pos)
            self.update()

    def finalize_segment(self, pos: QtCore.QPointF) -> None:
        """Finalize current segment and add new preview point."""
        if len(self._points) >= 2:
            self.prepareGeometryChange()
            self._points[-1] = QtCore.QPointF(pos)
            self._points.append(QtCore.QPointF(pos))
            self.update()

    def remove_preview_point(self) -> bool:
        """
        Remove the last (preview) point.

        Returns:
            True if ruler still valid (has >= 2 points after removal)
        """
        if len(self._points) > 2:
            self.prepareGeometryChange()
            self._points.pop()
            self.update()
        return len(self._points) >= 2

    def point_count(self) -> int:
        """Return number of points."""
        return len(self._points)

    def add_point(self, pos: QtCore.QPointF, insert_after_index: int | None = None) -> None:
        """Add a new point. If insert_after_index is None, append at end."""
        self.prepareGeometryChange()
        if insert_after_index is None:
            self._points.append(QtCore.QPointF(pos))
        else:
            self._points.insert(insert_after_index + 1, QtCore.QPointF(pos))
        self.update()

    # ========== Geometry Calculation Helpers ==========

    def _compute_segment_data(self) -> tuple[list[float], float]:
        """
        Compute segment lengths and total length.

        Returns:
            Tuple of (segment_lengths list, total_length)
        """
        segment_lengths = []
        total_length = 0.0
        for i in range(len(self._points) - 1):
            dx = self._points[i + 1].x() - self._points[i].x()
            dy = self._points[i + 1].y() - self._points[i].y()
            seg_len = math.hypot(dx, dy)
            segment_lengths.append(seg_len)
            total_length += seg_len
        return segment_lengths, total_length

    def _compute_total_label_position(self) -> QtCore.QPointF:
        """Compute position for total length label (multi-segment rulers)."""
        last_start = self._points[-2]
        last_end = self._points[-1]
        dx = last_end.x() - last_start.x()
        dy = last_end.y() - last_start.y()
        length = math.hypot(dx, dy) or 1.0

        # Perpendicular and along-segment unit vectors
        perp_x, perp_y = -dy / length, dx / length
        along_x, along_y = dx / length, dy / length

        return QtCore.QPointF(
            last_end.x()
            + perp_x * RULER_TOTAL_LABEL_PERP_OFFSET
            + along_x * RULER_TOTAL_LABEL_ALONG_OFFSET,
            last_end.y()
            + perp_y * RULER_TOTAL_LABEL_PERP_OFFSET
            + along_y * RULER_TOTAL_LABEL_ALONG_OFFSET,
        )

    def _get_label_bounding_rect(self, pos: QtCore.QPointF, text: str) -> QtCore.QRectF:
        """Calculate bounding rectangle for a label (for hit testing)."""
        fm = QtGui.QFontMetrics(QtGui.QFont())
        w = fm.horizontalAdvance(text) + 12
        h = fm.height() + 6

        # Use larger box to account for rotation
        padding = RULER_BAR_HEIGHT / 2.0 + RULER_LABEL_PADDING
        max_dim = max(w, h) + padding
        return QtCore.QRectF(
            pos.x() - max_dim / 2.0, pos.y() - max_dim / 2.0 - padding, max_dim, max_dim
        )

    # ========== Qt Graphics Item Methods ==========

    def boundingRect(self) -> QtCore.QRectF:
        if not self._points:
            return QtCore.QRectF()

        min_x = min(p.x() for p in self._points)
        max_x = max(p.x() for p in self._points)
        min_y = min(p.y() for p in self._points)
        max_y = max(p.y() for p in self._points)
        rect = QtCore.QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        pad = max(RULER_BOUNDING_PAD_PX, RULER_BAR_HEIGHT * 1.5)
        return rect.adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        if len(self._points) < 2:
            return path

        # Add the line path with stroke width for hit testing
        line_path = QtGui.QPainterPath()
        line_path.moveTo(self._points[0])
        for i in range(1, len(self._points)):
            line_path.lineTo(self._points[i])
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(max(RULER_MIN_STROKE_WIDTH_PX, RULER_BAR_HEIGHT))
        path.addPath(stroker.createStroke(line_path))

        # Add label areas for hit testing
        segment_lengths, total_length = self._compute_segment_data()

        if len(self._points) > 2:
            # Multi-segment: add per-segment labels
            for i in range(len(self._points) - 1):
                seg_mid = (self._points[i] + self._points[i + 1]) * 0.5
                seg_txt = f"{segment_lengths[i]:.1f} mm"
                path.addRect(self._get_label_bounding_rect(seg_mid, seg_txt))

            # Add total label
            total_pos = self._compute_total_label_position()
            total_txt = f"Total: {total_length:.1f} mm"
            path.addRect(self._get_label_bounding_rect(total_pos, total_txt))
        else:
            # Single segment: add centered label
            mid = (self._points[0] + self._points[1]) * 0.5
            total_txt = f"{total_length:.1f} mm"
            path.addRect(self._get_label_bounding_rect(mid, total_txt))

        return path

    # ========== Paint Helpers ==========

    def _draw_bar(
        self,
        painter: QtGui.QPainter,
        center: QtCore.QPointF,
        dir_x: float,
        dir_y: float,
        perp_x: float,
        perp_y: float,
        color: QtGui.QColor,
    ) -> None:
        """Draw a bar perpendicular to the line at center point."""
        cx, cy = center.x(), center.y()
        hw = RULER_BAR_WIDTH / 2.0  # half-width along direction
        hh = RULER_BAR_HEIGHT / 2.0  # half-height along perpendicular

        pts = [
            QtCore.QPointF(cx + (-hw * dir_x + -hh * perp_x), cy + (-hw * dir_y + -hh * perp_y)),
            QtCore.QPointF(cx + (hw * dir_x + -hh * perp_x), cy + (hw * dir_y + -hh * perp_y)),
            QtCore.QPointF(cx + (hw * dir_x + hh * perp_x), cy + (hw * dir_y + hh * perp_y)),
            QtCore.QPointF(cx + (-hw * dir_x + hh * perp_x), cy + (-hw * dir_y + hh * perp_y)),
        ]

        painter.save()
        painter.setPen(QtGui.QPen(color, 1))
        painter.setBrush(color)
        painter.drawPolygon(QtGui.QPolygonF(pts))
        painter.restore()

    def _draw_label(
        self,
        painter: QtGui.QPainter,
        pos: QtCore.QPointF,
        text: str,
        seg_dx: float,
        seg_dy: float,
        is_selected: bool,
    ) -> None:
        """Draw a text label at the given position with proper rotation."""
        # Ensure text is always readable (flip direction if needed)
        dx_calc, dy_calc = seg_dx, seg_dy
        if seg_dx < 0:
            dx_calc, dy_calc = -seg_dx, -seg_dy
        angle = math.degrees(math.atan2(dy_calc, dx_calc))

        painter.save()
        painter.translate(pos)
        painter.rotate(angle)
        # Compensate for view's Y-axis inversion
        painter.scale(1.0, -1.0)

        fm = QtGui.QFontMetrics(painter.font())
        w = fm.horizontalAdvance(text) + 12
        h = fm.height() + 6
        y_off = -(RULER_BAR_HEIGHT / 2.0 + RULER_LABEL_PADDING + h)

        # Background and text colors
        if is_selected:
            bg_color = QtGui.QColor(255, 255, 255, RULER_LABEL_BG_ALPHA_SELECTED)
            text_color = QtGui.QColor(0, 120, 215)  # Selection blue
        else:
            bg_color = QtGui.QColor(255, 255, 255, RULER_LABEL_BG_ALPHA)
            text_color = QtGui.QColor(20, 20, 20)

        # Draw background
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        label_rect = QtCore.QRectF(-w / 2.0, y_off, float(w), float(h))
        painter.drawRoundedRect(label_rect, RULER_LABEL_CORNER_RADIUS, RULER_LABEL_CORNER_RADIUS)

        # Draw text
        painter.setPen(QtGui.QPen(text_color))
        painter.drawText(label_rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()

    def paint(self, painter: QtGui.QPainter, opt, widget=None):
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

        if len(self._points) < 2:
            return

        is_selected = self.isSelected()

        # Line appearance based on selection
        if is_selected:
            base_color = QtGui.QColor(0, 120, 215)  # Blue for selection
            line_width = RULER_LINE_WIDTH_SELECTED
        else:
            base_color = QtGui.QColor(30, 30, 30)
            line_width = RULER_LINE_WIDTH

        base_pen = QtGui.QPen(base_color, line_width)
        base_pen.setCosmetic(True)
        base_pen.setCapStyle(QtCore.Qt.PenCapStyle.FlatCap)
        base_pen.setJoinStyle(QtCore.Qt.PenJoinStyle.MiterJoin)
        painter.setPen(base_pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        # Calculate segment data once
        segment_lengths, total_length = self._compute_segment_data()

        # Draw lines between consecutive points
        for i in range(len(self._points) - 1):
            painter.drawLine(self._points[i], self._points[i + 1])

        # Draw bars at all points
        for i in range(len(self._points)):
            # Determine direction for bar orientation
            if i == 0:
                dx = self._points[1].x() - self._points[0].x()
                dy = self._points[1].y() - self._points[0].y()
            elif i == len(self._points) - 1:
                dx = self._points[-1].x() - self._points[-2].x()
                dy = self._points[-1].y() - self._points[-2].y()
            else:
                # Middle point: average direction of adjacent segments
                dx1 = self._points[i].x() - self._points[i - 1].x()
                dy1 = self._points[i].y() - self._points[i - 1].y()
                dx2 = self._points[i + 1].x() - self._points[i].x()
                dy2 = self._points[i + 1].y() - self._points[i].y()
                dx = (dx1 + dx2) / 2.0
                dy = (dy1 + dy2) / 2.0

            length = math.hypot(dx, dy) or 1.0
            dir_x, dir_y = dx / length, dy / length
            perp_x, perp_y = -dir_y, dir_x

            bar_color = base_color if is_selected else QtGui.QColor(QtCore.Qt.GlobalColor.black)
            self._draw_bar(painter, self._points[i], dir_x, dir_y, perp_x, perp_y, bar_color)

        # Draw labels
        if len(self._points) > 2:
            # Multi-segment: show label for each segment
            for i in range(len(self._points) - 1):
                seg_mid = (self._points[i] + self._points[i + 1]) * 0.5
                seg_dx = self._points[i + 1].x() - self._points[i].x()
                seg_dy = self._points[i + 1].y() - self._points[i].y()
                seg_txt = f"{segment_lengths[i]:.1f} mm"
                self._draw_label(painter, seg_mid, seg_txt, seg_dx, seg_dy, is_selected)

            # Total length label
            total_pos = self._compute_total_label_position()
            total_txt = f"Total: {total_length:.1f} mm"
            self._draw_label(painter, total_pos, total_txt, 1.0, 0.0, is_selected)
        else:
            # Single segment: show total distance label
            mid = (self._points[0] + self._points[1]) * 0.5
            total_txt = f"{total_length:.1f} mm"
            seg_dx = self._points[1].x() - self._points[0].x()
            seg_dy = self._points[1].y() - self._points[0].y()
            self._draw_label(painter, mid, total_txt, seg_dx, seg_dy, is_selected)

    # ========== Mouse Event Handling ==========

    def _nearest_point(self, pos: QtCore.QPointF) -> int | None:
        """Check if pos is near any point, return index if found."""
        min_dist = float("inf")
        nearest_idx = None
        for i, point in enumerate(self._points):
            dist = QtCore.QLineF(pos, point).length()
            if dist <= RULER_HIT_RADIUS_PX and dist < min_dist:
                min_dist = dist
                nearest_idx = i
        return nearest_idx

    def _emit_property_change_command(
        self, before_state: dict[str, Any], after_state: dict[str, Any]
    ) -> None:
        """Create and emit a property change command for undo/redo."""
        from ...core.undo_commands import PropertyChangeCommand

        cmd = PropertyChangeCommand(self, before_state, after_state)
        self.commandCreated.emit(cmd)

    def mousePressEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        if ev.button() == QtCore.Qt.MouseButton.RightButton:
            self._handle_context_menu(ev)
            ev.accept()
            return

        which = self._nearest_point(ev.pos())
        if ev.button() == QtCore.Qt.MouseButton.LeftButton and which is not None:
            self._grab = which
            # Store initial point positions for undo
            self._initial_points = [QtCore.QPointF(p) for p in self._points]
            ev.accept()
            return

        self._grab = None
        self._initial_points = None
        super().mousePressEvent(ev)

    def _handle_context_menu(self, ev: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle right-click context menu."""
        nearest_idx = self._nearest_point(ev.pos())
        is_bend_point = nearest_idx is not None and 0 < nearest_idx < len(self._points) - 1

        m = QtWidgets.QMenu()
        act_del = m.addAction("Delete")

        # Add "Delete Point" option for bend points
        act_del_point = None
        if is_bend_point:
            act_del_point = m.addAction("Delete Point")
            m.addSeparator()

        act_add_bend = m.addAction("Add Bend")

        # Z-order options
        m.addSeparator()
        act_bring_to_front = m.addAction("Bring to Front")
        act_bring_forward = m.addAction("Bring Forward")
        act_send_backward = m.addAction("Send Backward")
        act_send_to_back = m.addAction("Send to Back")

        action = m.exec(ev.screenPos())

        if action == act_del:
            # Emit signal for undoable deletion
            self.requestDelete.emit(self)
        elif action == act_del_point and is_bend_point and nearest_idx is not None:
            self._delete_bend_point(nearest_idx)
        elif action == act_add_bend:
            self._add_bend_at_nearest_segment(ev.pos())
        else:
            # Handle z-order actions
            handle_z_order_from_menu(
                self,
                action,
                {
                    act_bring_to_front: "bring_to_front",
                    act_bring_forward: "bring_forward",
                    act_send_backward: "send_backward",
                    act_send_to_back: "send_to_back",
                },
            )

    def _delete_bend_point(self, index: int) -> None:
        """Delete a bend point with undo support."""
        if len(self._points) <= 2:
            return

        before_state = self.capture_state()
        self.prepareGeometryChange()
        self._points.pop(index)
        self.update()
        after_state = self.capture_state()

        self._emit_property_change_command(before_state, after_state)

    def _add_bend_at_nearest_segment(self, click_pos: QtCore.QPointF) -> None:
        """Add a bend point at the midpoint of the nearest segment."""
        if len(self._points) < 2:
            return

        # Find nearest segment
        min_dist = float("inf")
        insert_idx = 0

        for i in range(len(self._points) - 1):
            seg_start = self._points[i]
            seg_end = self._points[i + 1]
            seg_len = QtCore.QLineF(seg_start, seg_end).length()

            if seg_len > 0:
                # Project click point onto segment
                seg_vec = seg_end - seg_start
                click_vec = click_pos - seg_start
                t = max(
                    0,
                    min(
                        1,
                        (click_vec.x() * seg_vec.x() + click_vec.y() * seg_vec.y())
                        / (seg_len * seg_len),
                    ),
                )
                proj_point = seg_start + t * seg_vec
                dist = QtCore.QLineF(click_pos, proj_point).length()

                if dist < min_dist:
                    min_dist = dist
                    insert_idx = i

        # Insert point at midpoint of nearest segment
        midpoint = (self._points[insert_idx] + self._points[insert_idx + 1]) * 0.5

        before_state = self.capture_state()
        self.add_point(midpoint, insert_idx)
        after_state = self.capture_state()

        self._emit_property_change_command(before_state, after_state)

    def mouseMoveEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        if self._grab is not None and 0 <= self._grab < len(self._points):
            self.prepareGeometryChange()
            self._points[self._grab] = ev.pos()
            self.update()
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        # Create undo command if points were changed
        if self._grab is not None and self._initial_points is not None:
            points_changed = self._check_points_changed()

            if points_changed:
                before_state = {
                    "points": [[float(p.x()), float(p.y())] for p in self._initial_points],
                    "pos": {"x": float(self.pos().x()), "y": float(self.pos().y())},
                }
                after_state = self.capture_state()
                self._emit_property_change_command(before_state, after_state)

        self._grab = None
        self._initial_points = None
        super().mouseReleaseEvent(ev)

    def _check_points_changed(self) -> bool:
        """Check if points have changed from initial state."""
        if self._initial_points is None:
            return False
        if len(self._points) != len(self._initial_points):
            return True

        for old_pt, new_pt in zip(self._initial_points, self._points):
            if QtCore.QLineF(old_pt, new_pt).length() > RULER_POINT_CHANGE_THRESHOLD:
                return True
        return False

    # ========== State Management (Undo/Redo) ==========

    def capture_state(self) -> dict[str, Any]:
        """Capture current state for undo/redo."""
        return {
            "points": [[float(p.x()), float(p.y())] for p in self._points],
            "pos": {"x": float(self.pos().x()), "y": float(self.pos().y())},
        }

    def apply_state(self, state: dict[str, Any]) -> None:
        """Apply a previously captured state."""
        if "points" in state:
            self.prepareGeometryChange()
            self._points = [QtCore.QPointF(float(p[0]), float(p[1])) for p in state["points"]]
            self.update()
        if "pos" in state:
            self.setPos(QtCore.QPointF(float(state["pos"]["x"]), float(state["pos"]["y"])))

    # ========== Serialization ==========

    def clone(self, offset_mm: tuple[float, float] = (20.0, 20.0)) -> RulerItem:
        """Create a deep copy of this ruler with optional position offset."""
        # Get scene coordinates of all points
        points_scene = [self.mapToScene(p) for p in self._points]

        # Create new ruler with offset positions
        new_points = [
            QtCore.QPointF(p.x() + offset_mm[0], p.y() + offset_mm[1]) for p in points_scene
        ]
        new_ruler = RulerItem(points=new_points, item_uuid=str(uuid.uuid4()))
        new_ruler.setZValue(self.zValue())

        return new_ruler

    def to_dict(self) -> dict[str, Any]:
        """Serialize ruler to dictionary."""
        # Save absolute points in scene space so reopening is exact
        points_scene = [self.mapToScene(p) for p in self._points]
        return {
            "type": "ruler",
            "points": [[float(p.x()), float(p.y())] for p in points_scene],
            "item_uuid": self.item_uuid,
            "z_value": float(self.zValue()),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> RulerItem:
        """Deserialize ruler from dictionary."""
        item_uuid = d.get("item_uuid")

        # Support both old format (p1/p2) and new format (points)
        if "points" in d:
            points = [QtCore.QPointF(float(p[0]), float(p[1])) for p in d["points"]]
            item = RulerItem(points=points, item_uuid=item_uuid)
        else:
            # Old format: backward compatibility
            p1 = QtCore.QPointF(float(d["p1"][0]), float(d["p1"][1]))
            p2 = QtCore.QPointF(float(d["p2"][0]), float(d["p2"][1]))
            item = RulerItem(p1, p2, item_uuid)

        if "z_value" in d:
            item.setZValue(float(d["z_value"]))

        return item
