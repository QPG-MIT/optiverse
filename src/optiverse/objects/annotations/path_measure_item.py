"""
Path Measure Item - Measures optical path length along traced rays.

Highlights a selected ray path and displays cumulative distance traveled,
including reflections, refractions, and beam splitter paths.
"""

from __future__ import annotations

import math
import uuid
from typing import Any, cast

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.ui_constants import (
    PATH_MEASURE_ENDPOINT_COLOR,
    PATH_MEASURE_ENDPOINT_RADIUS,
    PATH_MEASURE_HIGHLIGHT_COLOR,
    PATH_MEASURE_LABEL_BG_COLOR,
    PATH_MEASURE_LABEL_TEXT_COLOR,
    PATH_MEASURE_LINE_WIDTH,
    SELECTION_INDICATOR_COLOR,
)
from ...core.zorder_utils import handle_z_order_from_menu


class PathMeasureItem(QtWidgets.QGraphicsObject):
    """
    Highlights and measures a traced ray path.

    Features:
    - Automatic path following along ray segments
    - Distance calculation including reflections/refractions
    - Visual highlighting with segment markers
    - Displays total optical path length
    - Undo/redo support via commandCreated signal
    """

    # Signal emitted when an undo command is created
    commandCreated = QtCore.pyqtSignal(object)

    # Signal emitted when item requests deletion (for undoable delete)
    requestDelete = QtCore.pyqtSignal(object)  # Emits self

    def __init__(
        self,
        ray_path_points: list[np.ndarray],
        start_param: float = 0.0,
        end_param: float = 1.0,
        ray_index: int = -1,
        item_uuid: str | None = None,
        label_prefix: str = "",
    ):
        """
        Initialize path measure for a segment of a ray path.

        Args:
            ray_path_points: List of [x, y] positions along the full ray path
            start_param: Parameter [0, 1] for segment start position along path
            end_param: Parameter [0, 1] for segment end position along path
            ray_index: Index in main_window.ray_data (for tracking across retraces)
            item_uuid: Unique identifier for collaboration
            label_prefix: Optional text prefix rendered before the distance label
        """
        super().__init__()

        # Generate or use provided UUID
        self.item_uuid = item_uuid if item_uuid else str(uuid.uuid4())

        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)
        self.setZValue(9_999)  # Below rulers (10,000) but above rays

        # Accept keyboard input
        self.setAcceptHoverEvents(True)

        # Ray path data
        self._full_path_points = [np.array(p, dtype=float) for p in ray_path_points]
        self._ray_index = ray_index

        # Calculate total path length FIRST (needed by _position_at_parameter)
        self._total_path_length = self._calculate_path_length(self._full_path_points)

        # Segment parameters
        self.start_param = float(np.clip(start_param, 0.0, 1.0))
        self.end_param = float(np.clip(end_param, 0.0, 1.0))

        # Ensure start < end
        if self.start_param > self.end_param:
            self.start_param, self.end_param = self.end_param, self.start_param

        # Calculate segment length
        segment_points = self._get_segment_points()
        self._segment_length = self._calculate_path_length(segment_points)

        # Optional label prefix (e.g., "Transmitted: ") for beam splitter pairs
        self._label_prefix = label_prefix

        # Dragging state
        self._dragging_endpoint: str | None = None  # 'start' or 'end' when dragging
        self._initial_params: dict[str, float] | None = None  # For undo tracking

        # Appearance (from constants)
        self._highlight_color = QtGui.QColor(*PATH_MEASURE_HIGHLIGHT_COLOR)
        self._line_width = PATH_MEASURE_LINE_WIDTH
        self._endpoint_radius = PATH_MEASURE_ENDPOINT_RADIUS
        self._label_bg_color = QtGui.QColor(*PATH_MEASURE_LABEL_BG_COLOR)
        self._label_text_color = QtGui.QColor(*PATH_MEASURE_LABEL_TEXT_COLOR)

    @staticmethod
    def _calculate_path_length(points: list[np.ndarray]) -> float:
        """Calculate cumulative distance along path segments."""
        total = 0.0
        for i in range(len(points) - 1):
            dx = points[i + 1][0] - points[i][0]
            dy = points[i + 1][1] - points[i][1]
            total += math.sqrt(dx * dx + dy * dy)
        return total

    def _calculate_segment_length(self) -> float:
        """Calculate length of the measured segment between start and end parameters."""
        if len(self._full_path_points) < 2:
            return 0.0

        segment_points = self._get_segment_points()
        return self._calculate_path_length(segment_points)

    def _get_segment_points(self) -> list[np.ndarray]:
        """Get the list of points between start_param and end_param."""
        if len(self._full_path_points) < 2:
            return []

        start_pos = self._position_at_parameter(self.start_param)
        end_pos = self._position_at_parameter(self.end_param)

        if start_pos is None or end_pos is None:
            return []

        start_dist = self.start_param * self._total_path_length
        end_dist = self.end_param * self._total_path_length

        segment_points = [start_pos]

        # Add intermediate points that fall within the range
        accumulated = 0.0
        for i in range(len(self._full_path_points) - 1):
            p1 = self._full_path_points[i]
            p2 = self._full_path_points[i + 1]
            segment_len = np.linalg.norm(p2 - p1)

            # Check if this segment's endpoint is in our range
            if accumulated + segment_len > start_dist and accumulated + segment_len <= end_dist:
                segment_points.append(p2.copy())

            accumulated += float(segment_len)

        segment_points.append(end_pos)
        return segment_points

    def _position_at_parameter(self, param: float) -> np.ndarray | None:
        """
        Find position along path at given parameter [0,1].

        Args:
            param: Position parameter (0=start of path, 1=end of path)

        Returns:
            [x, y] position, or None if path is empty
        """
        if len(self._full_path_points) < 2:
            return None

        target_dist = param * self._total_path_length
        accumulated = 0.0

        for i in range(len(self._full_path_points) - 1):
            p1 = self._full_path_points[i]
            p2 = self._full_path_points[i + 1]

            segment_vec = p2 - p1
            segment_len = np.linalg.norm(segment_vec)

            if accumulated + segment_len >= target_dist:
                remaining = target_dist - accumulated
                t = remaining / segment_len if segment_len > 0 else 0
                return cast(np.ndarray, p1 + t * segment_vec)

            accumulated += float(segment_len)

        return self._full_path_points[-1].copy()

    def update_path(self, new_points: list[np.ndarray]):
        """
        Update the path points (e.g., after retrace).

        Args:
            new_points: New list of path points
        """
        self.prepareGeometryChange()
        self._full_path_points = [np.array(p, dtype=float) for p in new_points]
        self._total_path_length = self._calculate_path_length(self._full_path_points)
        self._segment_length = self._calculate_segment_length()
        self.update()

    def set_target_length(self, target_mm: float):
        """
        Adjust end_param to achieve target length.

        Args:
            target_mm: Desired segment length in mm
        """
        if len(self._full_path_points) < 2:
            return

        start_dist = self.start_param * self._total_path_length
        target_total_dist = start_dist + target_mm

        if target_total_dist > self._total_path_length:
            target_total_dist = self._total_path_length

        self.end_param = (
            target_total_dist / self._total_path_length if self._total_path_length > 0 else 1.0
        )
        self.end_param = max(0.0, min(1.0, self.end_param))

        if self.end_param < self.start_param:
            self.end_param = self.start_param

        self.prepareGeometryChange()
        self._segment_length = self._calculate_segment_length()
        self.update()

    def boundingRect(self) -> QtCore.QRectF:
        """Calculate bounding rectangle encompassing measured segment."""
        segment_points = self._get_segment_points()

        if len(segment_points) < 2:
            return QtCore.QRectF()

        xs = [p[0] for p in segment_points]
        ys = [p[1] for p in segment_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        pad = max(100.0, self._line_width * 2, self._endpoint_radius * 2)

        return QtCore.QRectF(
            min_x - pad, min_y - pad, (max_x - min_x) + 2 * pad, (max_y - min_y) + 2 * pad
        )

    def shape(self) -> QtGui.QPainterPath:
        """Define interactive shape for selection."""
        path = QtGui.QPainterPath()

        segment_points = self._get_segment_points()
        if len(segment_points) < 2:
            return path

        path.moveTo(segment_points[0][0], segment_points[0][1])
        for i in range(1, len(segment_points)):
            path.lineTo(segment_points[i][0], segment_points[i][1])

        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(max(15.0, self._line_width * 2))
        return stroker.createStroke(path)

    def paint(self, painter: QtGui.QPainter | None, option, widget=None):
        """Render the highlighted path segment with measurements."""
        if painter is None:
            return
        segment_points = self._get_segment_points()

        if len(segment_points) < 2:
            return

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

        # Draw highlighted path segment
        pen = QtGui.QPen(self._highlight_color, self._line_width)
        pen.setCosmetic(True)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        # Draw path segments
        for i in range(len(segment_points) - 1):
            p1 = segment_points[i]
            p2 = segment_points[i + 1]
            painter.drawLine(QtCore.QPointF(p1[0], p1[1]), QtCore.QPointF(p2[0], p2[1]))

        # Draw yellow endpoint markers
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(*PATH_MEASURE_ENDPOINT_COLOR)))

        start_pos = segment_points[0]
        end_pos = segment_points[-1]

        painter.drawEllipse(
            QtCore.QPointF(start_pos[0], start_pos[1]), self._endpoint_radius, self._endpoint_radius
        )
        painter.drawEllipse(
            QtCore.QPointF(end_pos[0], end_pos[1]), self._endpoint_radius, self._endpoint_radius
        )

        # Draw distance label at midpoint
        self._draw_distance_label(painter, segment_points)

        # Draw selection indicator if selected
        if self.isSelected():
            self._draw_selection_indicator(painter, segment_points)

    def _draw_distance_label(self, painter: QtGui.QPainter, segment_points: list[np.ndarray]):
        """Draw the distance label."""
        if len(segment_points) < 2:
            return

        # Find position at actual path length midpoint
        mid_param = (self.start_param + self.end_param) / 2.0
        label_pos = self._position_at_parameter(mid_param)

        if label_pos is None:
            # Fallback to geometric midpoint
            mid_idx = len(segment_points) // 2
            label_pos = segment_points[mid_idx]

        # Format distance text
        if self._label_prefix:
            txt = f"{self._label_prefix}{self._segment_length:.2f} mm"
        else:
            txt = f"{self._segment_length:.2f} mm"

        # Prepare label background
        painter.save()
        painter.translate(label_pos[0], label_pos[1])

        # Compensate for Y-axis inversion
        painter.scale(1.0, -1.0)

        # Calculate label size
        fm = QtGui.QFontMetrics(painter.font())
        text_width = fm.horizontalAdvance(txt) + 16
        text_height = fm.height() + 8

        # Draw background
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QBrush(self._label_bg_color))
        painter.drawRoundedRect(
            QtCore.QRectF(-text_width / 2, -text_height / 2, text_width, text_height), 5.0, 5.0
        )

        # Draw text
        painter.setPen(QtGui.QPen(self._label_text_color))
        painter.drawText(
            QtCore.QRectF(-text_width / 2, -text_height / 2, text_width, text_height),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            txt,
        )

        painter.restore()

    def _endpoint_at_pos(self, scene_pos: QtCore.QPointF) -> str | None:
        """
        Check if position is near an endpoint.

        Args:
            scene_pos: Position in scene coordinates

        Returns:
            'start' or 'end' if near respective endpoint, None otherwise
        """
        segment_points = self._get_segment_points()
        if len(segment_points) < 2:
            return None

        start_pos = QtCore.QPointF(segment_points[0][0], segment_points[0][1])
        end_pos = QtCore.QPointF(segment_points[-1][0], segment_points[-1][1])

        # Check proximity (10 mm tolerance)
        if (scene_pos - start_pos).manhattanLength() < 10:
            return "start"
        if (scene_pos - end_pos).manhattanLength() < 10:
            return "end"

        return None

    def _find_closest_parameter(self, scene_pos: QtCore.QPointF) -> float:
        """
        Find parameter value [0, 1] for closest point on full path to given position.

        Args:
            scene_pos: Position in scene coordinates

        Returns:
            Parameter value [0.0, 1.0]
        """
        if len(self._full_path_points) < 2:
            return 0.0

        min_dist = float("inf")
        best_param = 0.0

        pos = np.array([scene_pos.x(), scene_pos.y()])

        # Calculate total path length
        total_length = self._calculate_path_length(self._full_path_points)
        if total_length < 1e-6:
            return 0.0

        accumulated = 0.0

        for i in range(len(self._full_path_points) - 1):
            p1 = self._full_path_points[i]
            p2 = self._full_path_points[i + 1]

            segment_vec = p2 - p1
            segment_len = np.linalg.norm(segment_vec)

            if segment_len < 1e-6:
                continue

            # Find closest point on this segment
            to_pos = pos - p1
            t = np.clip(np.dot(to_pos, segment_vec) / (segment_len**2), 0.0, 1.0)
            closest_on_segment = p1 + t * segment_vec

            dist = np.linalg.norm(pos - closest_on_segment)

            if dist < min_dist:
                min_dist = float(dist)
                # Calculate parameter for this position
                best_param = float((accumulated + float(t) * float(segment_len)) / total_length)

            accumulated += float(segment_len)

        return cast(float, np.clip(best_param, 0.0, 1.0))

    def _draw_selection_indicator(self, painter: QtGui.QPainter, segment_points: list[np.ndarray]):
        """Draw dashed outline when selected."""
        pen = QtGui.QPen(QtGui.QColor(*SELECTION_INDICATOR_COLOR), 2.0)
        pen.setCosmetic(True)
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        # Draw dashed segment path
        for i in range(len(segment_points) - 1):
            p1 = segment_points[i]
            p2 = segment_points[i + 1]
            painter.drawLine(QtCore.QPointF(p1[0], p1[1]), QtCore.QPointF(p2[0], p2[1]))

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent | None):
        """Handle mouse press for dragging endpoints or context menu."""
        if event is None:
            return
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            # Show context menu
            menu = QtWidgets.QMenu()
            act_edit_length = menu.addAction("Edit Length...")
            act_delete = menu.addAction("Delete")

            # Add z-order options
            menu.addSeparator()
            act_bring_to_front = menu.addAction("Bring to Front")
            act_bring_forward = menu.addAction("Bring Forward")
            act_send_backward = menu.addAction("Send Backward")
            act_send_to_back = menu.addAction("Send to Back")

            action = menu.exec(event.screenPos())

            if action == act_edit_length:
                self._show_edit_length_dialog()
            elif action == act_delete:
                # Emit signal for undoable deletion
                self.requestDelete.emit(self)
            else:
                # Handle z-order actions via utility
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

            event.accept()
            return

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            # Check if clicking on endpoint
            endpoint = self._endpoint_at_pos(event.scenePos())
            self._dragging_endpoint = endpoint if endpoint else None
            if self._dragging_endpoint:
                # Store initial params for undo
                self._initial_params = {
                    "start_param": self.start_param,
                    "end_param": self.end_param,
                }
                event.accept()
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent | None):
        """Handle dragging endpoints along path."""
        if event is None:
            return
        if self._dragging_endpoint:
            # Find parameter for current position
            new_param = self._find_closest_parameter(event.scenePos())

            if self._dragging_endpoint == "start":
                # Ensure start < end
                self.start_param = min(new_param, self.end_param - 0.01)
            else:  # 'end'
                # Ensure end > start
                self.end_param = max(new_param, self.start_param + 0.01)

            # Recalculate segment length
            segment_points = self._get_segment_points()
            self._segment_length = self._calculate_path_length(segment_points)

            self.prepareGeometryChange()
            self.update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent | None):
        """Handle end of dragging and create undo command if changed."""
        if event is None:
            return
        if self._dragging_endpoint and self._initial_params:
            # Check if params actually changed
            params_changed = (
                abs(self.start_param - self._initial_params["start_param"]) > 0.001
                or abs(self.end_param - self._initial_params["end_param"]) > 0.001
            )

            if params_changed:
                # Create undo command
                from ...core.undo_commands import PropertyChangeCommand

                before_state = {
                    "start_param": self._initial_params["start_param"],
                    "end_param": self._initial_params["end_param"],
                }
                after_state = self.capture_state()
                cmd = PropertyChangeCommand(self, before_state, after_state)
                self.commandCreated.emit(cmd)

            self._dragging_endpoint = None
            self._initial_params = None
            self.unsetCursor()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent | None):
        """Handle double-click to edit length."""
        if event is None:
            return
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._show_edit_length_dialog()
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        """Handle item changes."""
        return super().itemChange(change, value)

    def _show_edit_length_dialog(self):
        """Show dialog to edit target length."""
        if not self.scene() or not self.scene().views():
            return

        main_window = self.scene().views()[0].window()

        current_length = self._segment_length

        value, ok = QtWidgets.QInputDialog.getDouble(
            main_window,
            "Edit Path Length",
            "Target length (mm):",
            value=current_length,
            min=0.1,
            decimals=2,
        )

        if ok and abs(value - current_length) > 0.01:
            self.set_target_length(value)
            self.update()

    def get_ray_index(self) -> int:
        """Get the ray index for tracking across retraces."""
        return self._ray_index

    @property
    def segment_length(self) -> float:
        """Expose current segment length in mm."""
        return self._segment_length

    @property
    def label_prefix(self) -> str:
        """Expose current label prefix (if any)."""
        return self._label_prefix

    def set_label_prefix(self, prefix: str):
        """Update label prefix and refresh rendering."""
        self._label_prefix = prefix
        self.update()

    def capture_state(self) -> dict[str, Any]:
        """Capture current state for undo/redo."""
        return {
            "start_param": float(self.start_param),
            "end_param": float(self.end_param),
        }

    def apply_state(self, state: dict[str, Any]) -> None:
        """Apply a previously captured state."""
        if "start_param" in state:
            self.start_param = float(state["start_param"])
        if "end_param" in state:
            self.end_param = float(state["end_param"])

        # Recalculate segment length
        segment_points = self._get_segment_points()
        self._segment_length = self._calculate_path_length(segment_points)

        self.prepareGeometryChange()
        self.update()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for save/load."""
        return {
            "type": "path_measure",
            "ray_index": self._ray_index,
            "start_param": float(self.start_param),
            "end_param": float(self.end_param),
            "item_uuid": self.item_uuid,
            "z_value": float(self.zValue()),
            "label_prefix": self._label_prefix,
            # Note: We store ray_index and parameters, not the full path
            # The path is reconstructed from ray_data on load
        }

    @staticmethod
    def from_dict(d: dict[str, Any], ray_data: list[Any] | None = None) -> PathMeasureItem | None:
        """
        Deserialize from dictionary.

        Args:
            d: Serialized data
            ray_data: List of RayPath objects from main window

        Returns:
            PathMeasureItem instance, or None if ray_index invalid
        """
        ray_index = d.get("ray_index", -1)

        # Try to get ray path from ray_data
        if ray_data and 0 <= ray_index < len(ray_data):
            ray_path = ray_data[ray_index]
            points = ray_path.points
        else:
            # Fallback: create dummy path (will be updated on next retrace)
            points = [np.array([0, 0]), np.array([10, 10])]

        item = PathMeasureItem(
            ray_path_points=points,
            start_param=d.get("start_param", 0.0),
            end_param=d.get("end_param", 1.0),
            ray_index=ray_index,
            item_uuid=d.get("item_uuid"),
            label_prefix=d.get("label_prefix", ""),
        )

        # Restore z-value
        if "z_value" in d:
            item.setZValue(float(d["z_value"]))

        return item
