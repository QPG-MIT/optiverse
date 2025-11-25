"""
Angle Measure Item - Measures angles between two lines.

Displays an angle arc with the angle value in degrees.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.ui_constants import (
    ANGLE_MEASURE_ARC_COLOR,
    ANGLE_MEASURE_ARC_RADIUS,
    ANGLE_MEASURE_ARC_WIDTH,
    ANGLE_MEASURE_ENDPOINT_COLOR,
    ANGLE_MEASURE_ENDPOINT_RADIUS,
    ANGLE_MEASURE_ENDPOINT_SELECTED_COLOR,
    ANGLE_MEASURE_LABEL_BG_COLOR,
    ANGLE_MEASURE_LABEL_TEXT_COLOR,
    ANGLE_MEASURE_LINE_COLOR,
    ANGLE_MEASURE_LINE_WIDTH,
    SELECTION_INDICATOR_COLOR,
)
from ...core.zorder_utils import handle_z_order_from_menu


class AngleMeasureItem(QtWidgets.QGraphicsObject):
    """
    Visual representation of an angle measurement.

    Features:
    - Three points: vertex, first point, second point
    - Arc showing the angle
    - Label displaying angle in degrees
    - Draggable endpoints
    - Undo/redo support via commandCreated signal
    """

    # Signal emitted when an undo command is created
    commandCreated = QtCore.pyqtSignal(object)

    # Signal emitted when item requests deletion (for undoable delete)
    requestDelete = QtCore.pyqtSignal(object)  # Emits self

    def __init__(
        self,
        vertex: QtCore.QPointF,
        point1: QtCore.QPointF,
        point2: QtCore.QPointF,
        item_uuid: str | None = None,
    ):
        """
        Initialize angle measure item.

        Args:
            vertex: Vertex point (corner of the angle)
            point1: First point defining one side of the angle
            point2: Second point defining the other side of the angle
            item_uuid: Unique identifier for collaboration
        """
        super().__init__()

        # Generate or use provided UUID
        self.item_uuid = item_uuid if item_uuid else str(uuid.uuid4())

        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)
        self.setZValue(9_999)  # Below rulers (10,000) but above rays

        # Store points in scene coordinates
        # Position item at vertex for easier manipulation
        self.setPos(vertex)

        # Store points relative to vertex (in item coordinates)
        self._vertex = QtCore.QPointF(0, 0)  # Always at origin in item coords
        self._point1 = QtCore.QPointF(point1 - vertex)
        self._point2 = QtCore.QPointF(point2 - vertex)

        # Dragging state
        self._dragging_point: str | None = None  # 'vertex', 'point1', 'point2', or None
        self._initial_points: dict[str, QtCore.QPointF] | None = None

        # Appearance (from constants)
        self._line_color = QtGui.QColor(*ANGLE_MEASURE_LINE_COLOR)
        self._arc_color = QtGui.QColor(*ANGLE_MEASURE_ARC_COLOR)
        self._line_width = ANGLE_MEASURE_LINE_WIDTH
        self._arc_width = ANGLE_MEASURE_ARC_WIDTH
        self._arc_radius = ANGLE_MEASURE_ARC_RADIUS
        self._endpoint_radius = ANGLE_MEASURE_ENDPOINT_RADIUS
        self._label_bg_color = QtGui.QColor(*ANGLE_MEASURE_LABEL_BG_COLOR)
        self._label_text_color = QtGui.QColor(*ANGLE_MEASURE_LABEL_TEXT_COLOR)

    @property
    def vertex(self) -> QtCore.QPointF:
        """Get vertex point in scene coordinates."""
        return self.pos()

    @property
    def point1(self) -> QtCore.QPointF:
        """Get first point in scene coordinates."""
        return self.mapToScene(self._point1)

    @property
    def point2(self) -> QtCore.QPointF:
        """Get second point in scene coordinates."""
        return self.mapToScene(self._point2)

    @property
    def angle(self) -> float:
        """Get the measured angle in degrees."""
        return self._calculate_angle()

    def _calculate_angle(self) -> float:
        """Calculate inner angle in degrees between the two lines (always < 180°)."""
        # Vectors from vertex to each point
        v1 = self._point1 - self._vertex
        v2 = self._point2 - self._vertex

        # Calculate angle using dot product
        dot = v1.x() * v2.x() + v1.y() * v2.y()
        len1 = math.hypot(v1.x(), v1.y())
        len2 = math.hypot(v2.x(), v2.y())

        if len1 < 1e-6 or len2 < 1e-6:
            return 0.0

        # Clamp to avoid numerical errors
        cos_angle = max(-1.0, min(1.0, dot / (len1 * len2)))
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)

        # Always return the inner angle (smaller angle, 0-180°)
        # If the calculated angle is > 180, use the complement
        if angle_deg > 180:
            angle_deg = 360.0 - angle_deg

        return angle_deg

    def _get_angle_arc_angles(self) -> tuple[float, float]:
        """
        Get start and span angles for the arc.

        Returns:
            (start_angle_deg, span_angle_deg) in Qt's coordinate system
        """
        v1 = self._point1 - self._vertex
        v2 = self._point2 - self._vertex

        # Calculate angles in Qt's coordinate system (0° = right, 90° = down)
        angle1_deg = math.degrees(math.atan2(-v1.y(), v1.x()))  # Negate y for Qt coords
        angle2_deg = math.degrees(math.atan2(-v2.y(), v2.x()))

        # Normalize to [0, 360)
        angle1_deg = angle1_deg % 360
        angle2_deg = angle2_deg % 360

        # Calculate the measured angle (always inner angle < 180°)
        self._calculate_angle()

        # Calculate span going counterclockwise from angle2 to angle1
        span_ccw = (angle1_deg - angle2_deg) % 360
        if span_ccw == 0:
            span_ccw = 360

        # Calculate span going clockwise from angle2 to angle1
        span_cw = 360 - span_ccw if span_ccw != 360 else 360

        # Start from angle2 (third point)
        start_angle = angle2_deg

        # Always draw the inner angle (smaller arc)
        # Use whichever direction gives the smaller span
        if span_ccw < span_cw:
            span = span_ccw
        else:
            # Go clockwise (negative span in Qt)
            span = -span_cw

        return start_angle, span

    def boundingRect(self) -> QtCore.QRectF:
        """Calculate bounding rectangle."""
        # Include all three points plus arc and label
        points = [self._vertex, self._point1, self._point2]
        xs = [p.x() for p in points]
        ys = [p.y() for p in points]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # Add padding for arc and label
        pad = max(80.0, self._arc_radius + 30.0)

        return QtCore.QRectF(
            min_x - pad, min_y - pad, (max_x - min_x) + 2 * pad, (max_y - min_y) + 2 * pad
        )

    def shape(self) -> QtGui.QPainterPath:
        """Define interactive shape for selection."""
        path = QtGui.QPainterPath()

        # Add lines
        path.moveTo(self._vertex)
        path.lineTo(self._point1)
        path.moveTo(self._vertex)
        path.lineTo(self._point2)

        # Add arc
        start_angle, span = self._get_angle_arc_angles()
        arc_rect = QtCore.QRectF(
            self._vertex.x() - self._arc_radius,
            self._vertex.y() - self._arc_radius,
            self._arc_radius * 2,
            self._arc_radius * 2,
        )
        arc_path = QtGui.QPainterPath()
        arc_path.arcMoveTo(arc_rect, start_angle)
        arc_path.arcTo(arc_rect, start_angle, span)
        path.addPath(arc_path)

        # Add endpoint circles
        for point in [self._point1, self._point2]:
            circle = QtGui.QPainterPath()
            circle.addEllipse(point, self._endpoint_radius * 2, self._endpoint_radius * 2)
            path.addPath(circle)

        # Stroke for easier clicking
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(10.0)
        return stroker.createStroke(path)

    def paint(self, painter: QtGui.QPainter, option, widget=None):
        """Render the angle measurement."""
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

        is_selected = self.isSelected()

        # Draw lines from vertex to each point
        pen = QtGui.QPen(self._line_color, self._line_width)
        pen.setCosmetic(True)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        painter.drawLine(self._vertex, self._point1)
        painter.drawLine(self._vertex, self._point2)

        # Draw arc
        start_angle, span = self._get_angle_arc_angles()
        arc_rect = QtCore.QRectF(
            self._vertex.x() - self._arc_radius,
            self._vertex.y() - self._arc_radius,
            self._arc_radius * 2,
            self._arc_radius * 2,
        )

        arc_pen = QtGui.QPen(self._arc_color, self._arc_width)
        arc_pen.setCosmetic(True)
        painter.setPen(arc_pen)
        painter.drawArc(
            arc_rect, int(start_angle * 16), int(span * 16)
        )  # Qt uses 1/16th degree units

        # Draw endpoint markers
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        endpoint_color = (
            QtGui.QColor(*ANGLE_MEASURE_ENDPOINT_SELECTED_COLOR)
            if is_selected
            else QtGui.QColor(*ANGLE_MEASURE_ENDPOINT_COLOR)
        )
        painter.setBrush(QtGui.QBrush(endpoint_color))
        painter.drawEllipse(self._point1, self._endpoint_radius, self._endpoint_radius)
        painter.drawEllipse(self._point2, self._endpoint_radius, self._endpoint_radius)

        # Draw angle label
        self._draw_angle_label(painter)

        # Draw selection indicator if selected
        if is_selected:
            self._draw_selection_indicator(painter)

    def _draw_angle_label(self, painter: QtGui.QPainter):
        """Draw the angle value label."""
        angle = self._calculate_angle()
        txt = f"{angle:.1f}°"

        # Position label along arc (at midpoint)
        start_angle, span = self._get_angle_arc_angles()
        mid_angle = start_angle + span / 2.0

        # Calculate label position
        label_dist = self._arc_radius + 20.0
        mid_angle_rad = math.radians(mid_angle)
        # Qt coordinates: 0° = right, 90° = down, so we need to adjust
        label_x = self._vertex.x() + label_dist * math.cos(mid_angle_rad)
        label_y = self._vertex.y() - label_dist * math.sin(mid_angle_rad)  # Negate for Qt coords

        label_pos = QtCore.QPointF(label_x, label_y)

        # Draw label background
        painter.save()
        painter.translate(label_pos)

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

    def _draw_selection_indicator(self, painter: QtGui.QPainter):
        """Draw dashed outline when selected."""
        pen = QtGui.QPen(QtGui.QColor(*SELECTION_INDICATOR_COLOR), 2.0)
        pen.setCosmetic(True)
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        painter.drawLine(self._vertex, self._point1)
        painter.drawLine(self._vertex, self._point2)

    def set_point2(self, scene_pos: QtCore.QPointF) -> None:
        """Set point2 in scene coordinates."""
        item_pos = self.mapFromScene(scene_pos)
        self._point2 = item_pos
        self.prepareGeometryChange()
        self.update()

    def _point_at_pos(self, scene_pos: QtCore.QPointF) -> str | None:
        """
        Check if position is near a point.

        Args:
            scene_pos: Position in scene coordinates

        Returns:
            'vertex', 'point1', or 'point2' if near respective point, None otherwise
        """
        item_pos = self.mapFromScene(scene_pos)
        tolerance = 10.0

        # Vertex is always at origin in item coordinates
        if item_pos.manhattanLength() < tolerance:
            return "vertex"
        if (item_pos - self._point1).manhattanLength() < tolerance:
            return "point1"
        if (item_pos - self._point2).manhattanLength() < tolerance:
            return "point2"

        return None

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        """Handle mouse press for dragging points or context menu."""
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            # Show context menu
            menu = QtWidgets.QMenu()
            act_delete = menu.addAction("Delete")

            # Add z-order options
            menu.addSeparator()
            act_bring_to_front = menu.addAction("Bring to Front")
            act_bring_forward = menu.addAction("Bring Forward")
            act_send_backward = menu.addAction("Send Backward")
            act_send_to_back = menu.addAction("Send to Back")

            action = menu.exec(event.screenPos())

            if action == act_delete:
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
            # Check if clicking on a point
            self._dragging_point = self._point_at_pos(event.scenePos())
            if self._dragging_point:
                # Store initial points in scene coordinates for undo
                self._initial_points = {
                    "vertex": self.pos(),
                    "point1": self.mapToScene(self._point1),
                    "point2": self.mapToScene(self._point2),
                }
                event.accept()
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        """Handle dragging points."""
        if self._dragging_point:
            item_pos = self.mapFromScene(event.scenePos())

            if self._dragging_point == "vertex":
                # Move the item position (vertex)
                self.setPos(event.scenePos())
            elif self._dragging_point == "point1":
                self._point1 = item_pos
            elif self._dragging_point == "point2":
                self._point2 = item_pos

            self.prepareGeometryChange()
            self.update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        """Handle end of dragging and create undo command."""
        if self._dragging_point and self._initial_points:
            # Check if points actually changed (compare scene coordinates)
            points_changed = False
            if self._dragging_point == "vertex":
                # self.pos() is the vertex in scene coordinates
                points_changed = (
                    self.pos() - self._initial_points["vertex"]
                ).manhattanLength() > 0.1
            elif self._dragging_point == "point1":
                # Convert current item coords to scene coords for comparison
                current_point1_scene = self.mapToScene(self._point1)
                points_changed = (
                    current_point1_scene - self._initial_points["point1"]
                ).manhattanLength() > 0.1
            elif self._dragging_point == "point2":
                # Convert current item coords to scene coords for comparison
                current_point2_scene = self.mapToScene(self._point2)
                points_changed = (
                    current_point2_scene - self._initial_points["point2"]
                ).manhattanLength() > 0.1

            if points_changed:
                # Create undo command for point changes
                from ...core.undo_commands import PropertyChangeCommand

                # Create before state from initial points (already in scene coordinates)
                before_state = {
                    "vertex": [
                        float(self._initial_points["vertex"].x()),
                        float(self._initial_points["vertex"].y()),
                    ],
                    "point1": [
                        float(self._initial_points["point1"].x()),
                        float(self._initial_points["point1"].y()),
                    ],
                    "point2": [
                        float(self._initial_points["point2"].x()),
                        float(self._initial_points["point2"].y()),
                    ],
                }
                # Create after state from current points
                after_state = self.capture_state()

                cmd = PropertyChangeCommand(self, before_state, after_state)
                self.commandCreated.emit(cmd)

        self._dragging_point = None
        self._initial_points = None
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def capture_state(self) -> dict[str, Any]:
        """Capture current state for undo/redo."""
        # Return points in scene coordinates
        vertex_scene = self.pos()
        point1_scene = self.mapToScene(self._point1)
        point2_scene = self.mapToScene(self._point2)

        return {
            "vertex": [float(vertex_scene.x()), float(vertex_scene.y())],
            "point1": [float(point1_scene.x()), float(point1_scene.y())],
            "point2": [float(point2_scene.x()), float(point2_scene.y())],
        }

    def apply_state(self, state: dict[str, Any]) -> None:
        """Apply a previously captured state."""
        if "vertex" in state:
            vertex_scene = QtCore.QPointF(float(state["vertex"][0]), float(state["vertex"][1]))
            self.setPos(vertex_scene)
        if "point1" in state:
            point1_scene = QtCore.QPointF(float(state["point1"][0]), float(state["point1"][1]))
            self._point1 = self.mapFromScene(point1_scene)
        if "point2" in state:
            point2_scene = QtCore.QPointF(float(state["point2"][0]), float(state["point2"][1]))
            self._point2 = self.mapFromScene(point2_scene)

        self.prepareGeometryChange()
        self.update()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for save/load."""
        # Save absolute points in scene space
        vertex_scene = self.mapToScene(self._vertex)
        point1_scene = self.mapToScene(self._point1)
        point2_scene = self.mapToScene(self._point2)

        return {
            "type": "angle_measure",
            "vertex": [float(vertex_scene.x()), float(vertex_scene.y())],
            "point1": [float(point1_scene.x()), float(point1_scene.y())],
            "point2": [float(point2_scene.x()), float(point2_scene.y())],
            "item_uuid": self.item_uuid,
            "z_value": float(self.zValue()),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> AngleMeasureItem:
        """Deserialize from dictionary."""
        item_uuid = d.get("item_uuid")

        vertex = QtCore.QPointF(float(d["vertex"][0]), float(d["vertex"][1]))
        point1 = QtCore.QPointF(float(d["point1"][0]), float(d["point1"][1]))
        point2 = QtCore.QPointF(float(d["point2"][0]), float(d["point2"][1]))

        item = AngleMeasureItem(vertex, point1, point2, item_uuid)

        # Restore z-value if present
        if "z_value" in d:
            item.setZValue(float(d["z_value"]))

        return item
