"""
Multi-line Image Canvas for Component Editor.

Extends ImageCanvas to support multiple optical interfaces with:
- Visual representation as colored lines
- Draggable endpoints
- Color coding by interface type
- Unified interface for simple (1 line) and complex (N lines) components
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

from PyQt6 import QtCore, QtGui, QtWidgets

# Optional QtSvg for SVG clipboard/loads
try:
    from PyQt6 import QtSvg
    HAVE_QTSVG = True
except Exception:
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
    color: QtGui.QColor = None  # Line color
    label: str = ""  # Optional label
    properties: Dict[str, Any] = None  # Additional properties (n1, n2, is_BS, etc.)
    
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
    linesMoved = QtCore.pyqtSignal(list, list, list)  # (indices, old_positions, new_positions) for undo
    
    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._pix: Optional[QtGui.QPixmap] = None
        self._scale_fit = 1.0
        self._src_path: Optional[str] = None
        self.setAcceptDrops(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        
        # Multiple lines support (all coordinates in millimeters)
        self._lines: List[InterfaceLine] = []
        self._selected_lines: set = set()  # Set of selected line indices (multi-selection)
        
        # Coordinate conversion factor
        self._mm_per_px: float = 1.0  # Millimeters per image pixel
        
        # Drag state
        self._dragging_line: int = -1  # Index of line being dragged (endpoint mode)
        self._dragging_point: int = 0  # 1 for start point, 2 for end point
        self._dragging_entire_lines: bool = False  # True when dragging whole line(s)
        self._drag_start_pos: Optional[QtCore.QPointF] = None  # Initial drag position
        self._drag_initial_lines: List[Tuple[float, float, float, float]] = []  # Initial line positions
        self._drag_moved_indices: List[int] = []  # Indices of lines that were moved (for undo)
        self._hover_line: int = -1  # Line being hovered
        self._hover_point: int = 0  # Point being hovered (1 or 2)
        
        # Rectangle selection
        self._rect_selecting: bool = False  # True when drawing selection rectangle
        self._rect_start: Optional[QtCore.QPoint] = None  # Rectangle start position
        self._rect_end: Optional[QtCore.QPoint] = None  # Rectangle end position
        
        # Drag lock (restrict dragging to specific line)
        self._drag_locked_line: int = -1  # -1 means no lock, otherwise only this line can be dragged
        
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
        self.update()
    
    def source_path(self) -> Optional[str]:
        return self._src_path
    
    def current_pixmap(self) -> Optional[QtGui.QPixmap]:
        return self._pix
    
    def has_image(self) -> bool:
        return self._pix is not None and not self._pix.isNull()
    
    def image_pixel_size(self) -> Tuple[int, int]:
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
    
    def get_line(self, index: int) -> Optional[InterfaceLine]:
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
    
    def get_all_lines(self) -> List[InterfaceLine]:
        """Get all lines."""
        return list(self._lines)
    
    def clear_lines(self):
        """Remove all lines."""
        self._lines.clear()
        self._selected_lines.clear()
        self.update()
        self.linesChanged.emit()
    
    def set_lines(self, lines: List[InterfaceLine]):
        """Set all lines at once."""
        self._lines = list(lines)
        self._selected_lines.clear()
        self.update()
        self.linesChanged.emit()
    
    def get_selected_line_index(self) -> int:
        """Get currently selected line index (-1 if none). Returns first selected for backward compatibility."""
        if len(self._selected_lines) > 0:
            return min(self._selected_lines)
        return -1
    
    def get_selected_line_indices(self) -> List[int]:
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
    
    def select_lines(self, indices: List[int]):
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
    
    def get_points(self) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        """Get first line as point pair (backward compatibility)."""
        if len(self._lines) > 0:
            line = self._lines[0]
            return (line.x1, line.y1), (line.x2, line.y2)
        return None, None
    
    def set_points(self, p1: Optional[Tuple[float, float]], p2: Optional[Tuple[float, float]]):
        """Set first line from point pair (backward compatibility)."""
        if p1 and p2:
            if len(self._lines) == 0:
                # Create new line
                line = InterfaceLine(
                    x1=p1[0], y1=p1[1],
                    x2=p2[0], y2=p2[1],
                    color=QtGui.QColor(100, 100, 255)
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
        """Compute scaled image rectangle."""
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
        
        return QtCore.QRect(x0, y0, scaled_w, scaled_h)
    
    def paintEvent(self, e: QtGui.QPaintEvent):
        """Draw image and all lines."""
        super().paintEvent(e)
        
        if not self._pix or self._pix.isNull():
            return
        
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        
        # Draw image
        target = self._target_rect()
        p.drawPixmap(target, self._pix)
        
        # Draw all lines
        for i, line in enumerate(self._lines):
            self._draw_line(p, target, line, i)
        
        # Draw selection rectangle
        if self._rect_selecting and self._rect_start and self._rect_end:
            rect = QtCore.QRect(self._rect_start, self._rect_end).normalized()
            p.setPen(QtGui.QPen(QtGui.QColor(100, 150, 255), 2, QtCore.Qt.PenStyle.DashLine))
            p.setBrush(QtGui.QBrush(QtGui.QColor(100, 150, 255, 30)))
            p.drawRect(rect)
        
        # Draw bounding box around selected lines
        if len(self._selected_lines) > 1 and not self._rect_selecting:
            self._draw_bounding_box(p, target)
    
    def _draw_line(self, p: QtGui.QPainter, img_rect: QtCore.QRect, line: InterfaceLine, index: int):
        """Draw a single interface line."""
        # Convert mm coordinates to image pixel coordinates, then to screen coordinates
        x1_img_px = line.x1 / self._mm_per_px
        y1_img_px = line.y1 / self._mm_per_px
        x2_img_px = line.x2 / self._mm_per_px
        y2_img_px = line.y2 / self._mm_per_px
        
        # Center the coordinate system: (0,0) should be at the center of the canvas
        # instead of at the top-left corner
        img_center_x_px = img_rect.width() / (2 * self._scale_fit)
        img_center_y_px = img_rect.height() / (2 * self._scale_fit)
        
        # Convert image pixel coordinates to screen coordinates (centered origin, Y-up)
        x1_screen = img_rect.x() + (x1_img_px + img_center_x_px) * self._scale_fit
        y1_screen = img_rect.y() + (img_center_y_px - y1_img_px) * self._scale_fit
        x2_screen = img_rect.x() + (x2_img_px + img_center_x_px) * self._scale_fit
        y2_screen = img_rect.y() + (img_center_y_px - y2_img_px) * self._scale_fit
        
        # Determine appearance
        is_selected = (index in self._selected_lines)
        is_hovering = (index == self._hover_line)
        is_locked = (self._drag_locked_line >= 0 and index == self._drag_locked_line)
        is_dimmed = (self._drag_locked_line >= 0 and index != self._drag_locked_line)
        
        # Line color and width
        color = line.color
        if is_dimmed:
            # Dim non-locked lines
            color = QtGui.QColor(color.red(), color.green(), color.blue(), 80)  # Semi-transparent
            pen = QtGui.QPen(color, 1.5)
        elif is_selected or is_locked:
            pen = QtGui.QPen(color, 3)
        elif is_hovering:
            pen = QtGui.QPen(color, 2.5)
        else:
            pen = QtGui.QPen(color, 2)
        
        p.setPen(pen)
        
        # Check if this is a curved surface
        interface = line.properties.get('interface') if line.properties else None
        is_curved = interface and hasattr(interface, 'is_curved') and interface.is_curved
        
        if is_curved and interface and abs(interface.radius_of_curvature_mm) > 0.1:
            # Draw curved surface as an arc
            self._draw_curved_line(p, x1_screen, y1_screen, x2_screen, y2_screen, 
                                  interface.radius_of_curvature_mm, img_rect)
        else:
            # Draw straight line
            p.drawLine(QtCore.QPointF(x1_screen, y1_screen), 
                       QtCore.QPointF(x2_screen, y2_screen))
        
        # Draw refractive index indicator (half-circle) for refractive interfaces
        if not is_dimmed and line.properties:
            interface = line.properties.get('interface')
            if interface and interface.element_type == 'refractive_interface':
                # Only show indicator if indices are different (meaningful refraction)
                if abs(interface.n1 - interface.n2) > 0.01:
                    self._draw_refractive_index_indicator(
                        p, x1_screen, y1_screen, x2_screen, y2_screen,
                        interface, img_rect
                    )
        
        # Draw endpoints (skip if dimmed)
        if not is_dimmed:
            point_color = line.color.lighter(120) if (is_selected or is_locked) else line.color
            p.setPen(QtGui.QPen(point_color, 1))
            p.setBrush(QtGui.QBrush(point_color))
            
            # Point 1
            point_size = 6 if (is_selected or is_locked or (is_hovering and self._hover_point == 1)) else 5
            p.drawEllipse(QtCore.QPointF(x1_screen, y1_screen), point_size, point_size)
            
            # Point 2
            point_size = 6 if (is_selected or is_locked or (is_hovering and self._hover_point == 2)) else 5
            p.drawEllipse(QtCore.QPointF(x2_screen, y2_screen), point_size, point_size)
        
        # Draw refractive index labels for refractive interfaces
        if not is_dimmed and line.properties:
            interface = line.properties.get('interface')
            if interface and interface.element_type == 'refractive_interface':
                # Only show labels if indices are different (meaningful refraction)
                if abs(interface.n1 - interface.n2) > 0.01:
                    self._draw_refractive_index_labels(
                        p, x1_screen, y1_screen, x2_screen, y2_screen,
                        interface.n1, interface.n2, color
                    )
        
        # Draw label if exists
        if line.label and is_selected:
            p.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black))
            mid_x = (x1_screen + x2_screen) / 2
            mid_y = (y1_screen + y2_screen) / 2
            p.drawText(QtCore.QPointF(mid_x + 10, mid_y - 10), line.label)
    
    def _draw_refractive_index_labels(self, p: QtGui.QPainter, 
                                      x1: float, y1: float, 
                                      x2: float, y2: float,
                                      n1: float, n2: float,
                                      line_color: QtGui.QColor):
        """
        Draw refractive index labels near the endpoints of a refractive interface.
        
        Args:
            p: QPainter instance
            x1, y1: First endpoint (screen coordinates) - n1 side
            x2, y2: Second endpoint (screen coordinates) - n2 side
            n1: Refractive index at first endpoint
            n2: Refractive index at second endpoint
            line_color: Color of the interface line
        """
        # Calculate line vector and perpendicular
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        
        if length < 1:
            return  # Line too short, skip labels
        
        # Normalized perpendicular vector (rotate 90 degrees)
        perp_x = -dy / length
        perp_y = dx / length
        
        # Offset distance from line endpoints
        offset_dist = 15  # pixels from endpoint
        
        # Label positions (offset perpendicular to line)
        label1_x = x1 + perp_x * offset_dist
        label1_y = y1 + perp_y * offset_dist
        label2_x = x2 + perp_x * offset_dist
        label2_y = y2 + perp_y * offset_dist
        
        # Format labels with subscripts using Unicode
        label1_text = f"n₁={n1:.3f}"
        label2_text = f"n₂={n2:.3f}"
        
        # Font settings
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        p.setFont(font)
        
        # Get text bounding boxes for background
        fm = p.fontMetrics()
        rect1 = fm.boundingRect(label1_text)
        rect2 = fm.boundingRect(label2_text)
        
        # Add padding
        padding = 3
        rect1.adjust(-padding, -padding, padding, padding)
        rect2.adjust(-padding, -padding, padding, padding)
        
        # Position rectangles
        rect1.moveCenter(QtCore.QPoint(int(label1_x), int(label1_y)))
        rect2.moveCenter(QtCore.QPoint(int(label2_x), int(label2_y)))
        
        # Draw semi-transparent background for readability
        bg_color = QtGui.QColor(255, 255, 255, 220)  # White with alpha
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QBrush(bg_color))
        p.drawRoundedRect(rect1, 3, 3)
        p.drawRoundedRect(rect2, 3, 3)
        
        # Draw border around labels
        border_color = line_color.darker(120)
        p.setPen(QtGui.QPen(border_color, 1))
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect1, 3, 3)
        p.drawRoundedRect(rect2, 3, 3)
        
        # Draw text
        text_color = QtGui.QColor(0, 0, 0)  # Black text
        p.setPen(QtGui.QPen(text_color))
        p.drawText(rect1, QtCore.Qt.AlignmentFlag.AlignCenter, label1_text)
        p.drawText(rect2, QtCore.Qt.AlignmentFlag.AlignCenter, label2_text)
    
    def _draw_refractive_index_indicator(self, p: QtGui.QPainter,
                                         x1: float, y1: float,
                                         x2: float, y2: float,
                                         interface, img_rect: QtCore.QRect):
        """
        Draw a half-and-half colored circle at the midpoint of a refractive interface.
        
        The circle is split perpendicular to the line direction (or tangent for curved lines):
        - Left half (toward n₁ endpoint): Yellow
        - Right half (toward n₂ endpoint): Purple
        
        Args:
            p: QPainter instance
            x1, y1: First endpoint (screen coordinates) - n₁ side
            x2, y2: Second endpoint (screen coordinates) - n₂ side
            interface: InterfaceDefinition object with curvature info
            img_rect: Image rectangle for coordinate conversion
        """
        # Check if this is a curved interface
        is_curved = interface and hasattr(interface, 'is_curved') and interface.is_curved
        has_curvature = is_curved and hasattr(interface, 'radius_of_curvature_mm') and abs(interface.radius_of_curvature_mm) > 0.1
        
        # Calculate chord properties
        dx = x2 - x1
        dy = y2 - y1
        chord_length = math.sqrt(dx*dx + dy*dy)
        
        if chord_length < 1:
            return  # Line too short, skip indicator
        
        # Default to chord midpoint and direction
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        tangent_angle_rad = math.atan2(dy, dx)
        
        # For curved lines, calculate arc midpoint and tangent
        if has_curvature:
            radius_mm = interface.radius_of_curvature_mm
            radius_px = abs(radius_mm) / self._mm_per_px * self._scale_fit
            
            # Only adjust for curves if radius is reasonable relative to chord
            if radius_px >= chord_length / 2:
                # Calculate arc center (using SAME logic as _draw_curved_line)
                half_chord = chord_length / 2
                sag = radius_px - math.sqrt(radius_px**2 - half_chord**2)
                
                # Perpendicular direction to chord (normalized)
                perp_x = -dy / chord_length
                perp_y = dx / chord_length
                
                # Chord midpoint
                chord_mid_x = (x1 + x2) / 2
                chord_mid_y = (y1 + y2) / 2
                
                # Arc center position (same calculation as _draw_curved_line)
                if radius_mm > 0:
                    center_x = chord_mid_x + perp_x * (radius_px - sag)
                    center_y = chord_mid_y + perp_y * (radius_px - sag)
                else:
                    center_x = chord_mid_x - perp_x * (radius_px - sag)
                    center_y = chord_mid_y - perp_y * (radius_px - sag)
                
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
        
        # Define colors (matching plan specification)
        yellow_n1 = QtGui.QColor(255, 215, 0)  # Yellow for n₁ side
        purple_n2 = QtGui.QColor(147, 112, 219)  # Purple for n₂ side
        
        # Save painter state
        p.save()
        
        # Draw the circle split ALONG the line direction
        # The split line runs parallel to the interface
        # Yellow on the n₁ side (toward point 1), Purple on the n₂ side (toward point 2)
        
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        
        # The split should align with the line direction
        # For a vertical line (90°), split should be vertical
        # For a horizontal line (0°), split should be horizontal
        # To split ALONG the line (not perpendicular), we rotate by 90° and negate to fix direction
        
        # Draw n₁ half (Yellow) - the half toward point 1
        p.setBrush(QtGui.QBrush(yellow_n1))
        start_angle_deg = 180 - math.degrees(tangent_angle_rad)
        span_angle_deg = 180
        
        rect = QtCore.QRectF(mid_x - circle_radius, mid_y - circle_radius, 
                             circle_radius * 2, circle_radius * 2)
        p.drawPie(rect, int(start_angle_deg * 16), int(span_angle_deg * 16))
        
        # Draw n₂ half (Purple) - the half toward point 2  
        p.setBrush(QtGui.QBrush(purple_n2))
        start_angle_deg = 360 - math.degrees(tangent_angle_rad)
        p.drawPie(rect, int(start_angle_deg * 16), int(span_angle_deg * 16))
        
        # Draw outline for better visibility
        p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 180), 1))
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.drawEllipse(QtCore.QPointF(mid_x, mid_y), circle_radius, circle_radius)
        
        # Restore painter state
        p.restore()
    
    def _draw_curved_line(self, p: QtGui.QPainter, x1_screen: float, y1_screen: float, 
                          x2_screen: float, y2_screen: float, 
                          radius_mm: float, img_rect: QtCore.QRect):
        """
        Draw a curved line representing a spherical optical surface.
        
        Args:
            p: QPainter instance
            x1_screen, y1_screen: First endpoint in screen coordinates
            x2_screen, y2_screen: Second endpoint in screen coordinates
            radius_mm: Radius of curvature in millimeters
            img_rect: Image rectangle for coordinate conversion
        """
        # Convert radius from mm to screen pixels
        radius_px = abs(radius_mm) / self._mm_per_px * self._scale_fit
        
        # Midpoint of the chord
        mid_x = (x1_screen + x2_screen) / 2
        mid_y = (y1_screen + y2_screen) / 2
        
        # Chord length
        chord_length = math.sqrt((x2_screen - x1_screen)**2 + (y2_screen - y1_screen)**2)
        
        # If radius is too small relative to chord, draw straight line
        if radius_px < chord_length / 2:
            p.drawLine(QtCore.QPointF(x1_screen, y1_screen), 
                      QtCore.QPointF(x2_screen, y2_screen))
            return
        
        # Calculate sag (height of arc from chord)
        # sag = R - sqrt(R² - (chord/2)²)
        half_chord = chord_length / 2
        if radius_px < half_chord:
            # Degenerate case - draw straight line
            p.drawLine(QtCore.QPointF(x1_screen, y1_screen), 
                      QtCore.QPointF(x2_screen, y2_screen))
            return
        
        sag = radius_px - math.sqrt(radius_px**2 - half_chord**2)
        
        # Direction perpendicular to chord (normalized)
        dx = x2_screen - x1_screen
        dy = y2_screen - y1_screen
        chord_len = math.sqrt(dx**2 + dy**2)
        if chord_len < 0.1:
            # Degenerate case - endpoints too close
            return
        
        # Perpendicular vector (rotated 90° CCW)
        perp_x = -dy / chord_len
        perp_y = dx / chord_len
        
        # Determine arc direction based on sign of radius
        if radius_mm > 0:
            # Positive radius: center in positive perpendicular direction
            center_x = mid_x + perp_x * (radius_px - sag)
            center_y = mid_y + perp_y * (radius_px - sag)
        else:
            # Negative radius: center in negative perpendicular direction
            center_x = mid_x - perp_x * (radius_px - sag)
            center_y = mid_y - perp_y * (radius_px - sag)
        
        # Calculate angles for arc
        angle1 = math.atan2(y1_screen - center_y, x1_screen - center_x)
        angle2 = math.atan2(y2_screen - center_y, x2_screen - center_x)
        
        # Convert to degrees
        angle1_deg = math.degrees(angle1)
        angle2_deg = math.degrees(angle2)
        
        # Calculate span angle (ensure correct direction)
        span_angle = angle2_deg - angle1_deg
        
        # Normalize span to [-180, 180]
        while span_angle > 180:
            span_angle -= 360
        while span_angle < -180:
            span_angle += 360
        
        # For concave surfaces, we want the shorter arc on the other side
        if radius_mm < 0:
            if abs(span_angle) > 180:
                span_angle = span_angle - 360 if span_angle > 0 else span_angle + 360
        
        # Draw the arc
        # QPainter.drawArc uses a bounding rectangle and angles in 1/16th degrees
        rect = QtCore.QRectF(
            center_x - radius_px, 
            center_y - radius_px, 
            radius_px * 2, 
            radius_px * 2
        )
        
        # Convert angles to 1/16th degrees for Qt
        start_angle_16th = int(angle1_deg * 16)
        span_angle_16th = int(span_angle * 16)
        
        p.drawArc(rect, start_angle_16th, span_angle_16th)
    
    def _draw_bounding_box(self, p: QtGui.QPainter, img_rect: QtCore.QRect):
        """Draw a bounding box around all selected lines."""
        if not self._selected_lines:
            return
        
        # Calculate bounds in screen coordinates
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        img_center_x_px = img_rect.width() / (2 * self._scale_fit)
        img_center_y_px = img_rect.height() / (2 * self._scale_fit)
        
        for idx in self._selected_lines:
            if 0 <= idx < len(self._lines):
                line = self._lines[idx]
                
                # Convert to screen coordinates
                x1_img_px = line.x1 / self._mm_per_px
                y1_img_px = line.y1 / self._mm_per_px
                x2_img_px = line.x2 / self._mm_per_px
                y2_img_px = line.y2 / self._mm_per_px
                
                x1_screen = img_rect.x() + (x1_img_px + img_center_x_px) * self._scale_fit
                y1_screen = img_rect.y() + (y1_img_px + img_center_y_px) * self._scale_fit
                x2_screen = img_rect.x() + (x2_img_px + img_center_x_px) * self._scale_fit
                y2_screen = img_rect.y() + (y2_img_px + img_center_y_px) * self._scale_fit
                
                min_x = min(min_x, x1_screen, x2_screen)
                max_x = max(max_x, x1_screen, x2_screen)
                min_y = min(min_y, y1_screen, y2_screen)
                max_y = max(max_y, y1_screen, y2_screen)
        
        if min_x < float('inf'):
            # Add padding
            padding = 10
            bbox = QtCore.QRectF(
                min_x - padding, min_y - padding,
                max_x - min_x + 2 * padding, max_y - min_y + 2 * padding
            )
            
            # Draw bounding box
            p.setPen(QtGui.QPen(QtGui.QColor(100, 150, 255), 2, QtCore.Qt.PenStyle.DashLine))
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawRect(bbox)
    
    # ========== Mouse Interaction ==========
    
    def _get_line_and_point_at(self, screen_pos: QtCore.QPoint, threshold: float = 10.0) -> Tuple[int, int]:
        """
        Find line and point at screen position.
        
        Returns:
            (line_index, point_number) where point_number is 1 or 2, or (-1, 0) if none
        """
        if not self._pix:
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
        
        # Calculate centered coordinate system parameters
        img_center_x_px = img_rect.width() / (2 * self._scale_fit)
        img_center_y_px = img_rect.height() / (2 * self._scale_fit)
        
        for i in search_order:
            line = self._lines[i]
            
            # Convert mm to image pixels
            x1_img_px = line.x1 / self._mm_per_px
            y1_img_px = line.y1 / self._mm_per_px
            x2_img_px = line.x2 / self._mm_per_px
            y2_img_px = line.y2 / self._mm_per_px
            
            # Convert to screen coordinates (with centered origin)
            x1_screen = img_rect.x() + (x1_img_px + img_center_x_px) * self._scale_fit
            y1_screen = img_rect.y() + (img_center_y_px - y1_img_px) * self._scale_fit
            x2_screen = img_rect.x() + (x2_img_px + img_center_x_px) * self._scale_fit
            y2_screen = img_rect.y() + (img_center_y_px - y2_img_px) * self._scale_fit
            
            # Check point 2 first (so it takes priority if overlapping)
            dx = screen_pos.x() - x2_screen
            dy = screen_pos.y() - y2_screen
            if (dx*dx + dy*dy) <= threshold*threshold:
                return (i, 2)
            
            # Check point 1
            dx = screen_pos.x() - x1_screen
            dy = screen_pos.y() - y1_screen
            if (dx*dx + dy*dy) <= threshold*threshold:
                return (i, 1)
        
        return (-1, 0)
    
    def _get_line_at_position(self, screen_pos: QtCore.QPoint, threshold: float = 5.0) -> int:
        """
        Find line body at screen position (not just endpoints).
        
        Returns:
            Line index, or -1 if no line is near the position
        """
        if not self._pix:
            return -1
        
        img_rect = self._target_rect()
        if not img_rect.contains(screen_pos):
            return -1
        
        img_center_x_px = img_rect.width() / (2 * self._scale_fit)
        img_center_y_px = img_rect.height() / (2 * self._scale_fit)
        
        # Check all lines in reverse order (prioritize top lines)
        for i in range(len(self._lines) - 1, -1, -1):
            line = self._lines[i]
            
            # Convert to screen coordinates
            x1_img_px = line.x1 / self._mm_per_px
            y1_img_px = line.y1 / self._mm_per_px
            x2_img_px = line.x2 / self._mm_per_px
            y2_img_px = line.y2 / self._mm_per_px
            
            x1_screen = img_rect.x() + (x1_img_px + img_center_x_px) * self._scale_fit
            y1_screen = img_rect.y() + (img_center_y_px - y1_img_px) * self._scale_fit
            x2_screen = img_rect.x() + (x2_img_px + img_center_x_px) * self._scale_fit
            y2_screen = img_rect.y() + (img_center_y_px - y2_img_px) * self._scale_fit
            
            # Calculate distance from point to line segment
            px, py = screen_pos.x(), screen_pos.y()
            
            # Vector from line start to end
            dx = x2_screen - x1_screen
            dy = y2_screen - y1_screen
            
            # Squared length of line
            len_sq = dx*dx + dy*dy
            
            if len_sq < 0.01:  # Degenerate line (too short)
                continue
            
            # Parameter t along line (clamped to [0, 1])
            t = max(0.0, min(1.0, ((px - x1_screen) * dx + (py - y1_screen) * dy) / len_sq))
            
            # Closest point on line segment
            closest_x = x1_screen + t * dx
            closest_y = y1_screen + t * dy
            
            # Distance to closest point
            dist_sq = (px - closest_x)**2 + (py - closest_y)**2
            
            if dist_sq <= threshold * threshold:
                return i
        
        return -1
    
    def _segments_intersect(self, x1: float, y1: float, x2: float, y2: float,
                           x3: float, y3: float, x4: float, y4: float) -> bool:
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
    
    def _line_intersects_rect(self, x1: float, y1: float, x2: float, y2: float,
                              rect: QtCore.QRect) -> bool:
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
    
    def _get_lines_in_rect(self, rect: QtCore.QRect) -> List[int]:
        """
        Find all lines that intersect with the given rectangle.
        
        Returns:
            List of line indices
        """
        if not self._pix:
            return []
        
        img_rect = self._target_rect()
        img_center_x_px = img_rect.width() / (2 * self._scale_fit)
        img_center_y_px = img_rect.height() / (2 * self._scale_fit)
        
        result = []
        
        for i, line in enumerate(self._lines):
            # Convert to screen coordinates
            x1_img_px = line.x1 / self._mm_per_px
            y1_img_px = line.y1 / self._mm_per_px
            x2_img_px = line.x2 / self._mm_per_px
            y2_img_px = line.y2 / self._mm_per_px
            
            x1_screen = img_rect.x() + (x1_img_px + img_center_x_px) * self._scale_fit
            y1_screen = img_rect.y() + (img_center_y_px - y1_img_px) * self._scale_fit
            x2_screen = img_rect.x() + (x2_img_px + img_center_x_px) * self._scale_fit
            y2_screen = img_rect.y() + (img_center_y_px - y2_img_px) * self._scale_fit
            
            # Check if line intersects with rectangle
            if self._line_intersects_rect(x1_screen, y1_screen, x2_screen, y2_screen, rect):
                result.append(i)
        
        return result
    
    def mousePressEvent(self, e: QtMouseEvent):
        """Handle mouse press."""
        if not self._pix or e.button() != QtCore.Qt.MouseButton.LeftButton:
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
            self._drag_start_pos = e.pos()
            
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
    
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        """Handle mouse move."""
        if self._rect_selecting:
            # Update rectangle selection
            self._rect_end = e.pos()
            self.update()
            return
        
        if self._dragging_entire_lines:
            # Dragging entire line(s) - translation mode
            if not self._drag_start_pos or not self._drag_initial_lines:
                return
            
            img_rect = self._target_rect()
            if not img_rect.isValid():
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
            
            # Convert delta to millimeters (Y-up: screen +y is down → invert sign)
            delta_x_mm = (delta_x_screen / self._scale_fit) * self._mm_per_px
            delta_y_mm = (-(delta_y_screen) / self._scale_fit) * self._mm_per_px
            
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
            img_rect = self._target_rect()
            if not img_rect.isValid():
                return
            
            # Calculate centered coordinate system parameters
            img_center_x_px = img_rect.width() / (2 * self._scale_fit)
            img_center_y_px = img_rect.height() / (2 * self._scale_fit)
            
            # Convert screen coordinates to image pixel coordinates (centered, Y-up)
            x_img_px = (e.pos().x() - img_rect.x()) / self._scale_fit - img_center_x_px
            y_img_px = img_center_y_px - (e.pos().y() - img_rect.y()) / self._scale_fit
            
            # Clamp to image bounds (in centered coordinates)
            w, h = self.image_pixel_size()
            max_x = w / 2
            max_y = h / 2
            x_img_px = max(-max_x, min(max_x, x_img_px))
            y_img_px = max(-max_y, min(max_y, y_img_px))
            
            # Convert image pixel coordinates to millimeters
            x_mm = x_img_px * self._mm_per_px
            y_mm = y_img_px * self._mm_per_px
            
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
                can_interact = (line_idx == self._drag_locked_line)
            
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
    
    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        """Handle mouse release."""
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
                        self._drag_moved_indices,
                        self._drag_initial_lines,
                        new_positions
                    )
            
            self._dragging_line = -1
            self._dragging_point = 0
            self._dragging_entire_lines = False
            self._drag_start_pos = None
            self._drag_initial_lines.clear()
            self._drag_moved_indices.clear()
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
    
    # ========== Drag & Drop ==========
    
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        """Accept image drops."""
        if e.mimeData().hasImage() or e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()
    
    def dropEvent(self, e: QtGui.QDropEvent):
        """Handle dropped image."""
        md = e.mimeData()
        
        if md.hasImage():
            img = QtGui.QImage(md.imageData())
            if not img.isNull():
                pix = QtGui.QPixmap.fromImage(img)
                self.imageDropped.emit(pix, "")
        elif md.hasUrls():
            urls = md.urls()
            if urls:
                path = urls[0].toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.svg')):
                    if path.lower().endswith('.svg') and HAVE_QTSVG:
                        pix = self._render_svg_to_pixmap(path)
                    else:
                        pix = QtGui.QPixmap(path)
                    
                    if pix and not pix.isNull():
                        self.imageDropped.emit(pix, path)
    
    @staticmethod
    def _render_svg_to_pixmap(svg_path: str, size: int = 1000) -> Optional[QtGui.QPixmap]:
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
    
    def _screen_to_mm_coords(self, screen_pos: QtCore.QPoint) -> Tuple[float, float]:
        """
        Convert screen coordinates to mm coordinates.
        
        Returns:
            (x_mm, y_mm) tuple
        """
        if not self._pix:
            return (0.0, 0.0)
        
        img_rect = self._target_rect()
        if not img_rect.isValid():
            return (0.0, 0.0)
        
        # Calculate centered coordinate system parameters
        img_center_x_px = img_rect.width() / (2 * self._scale_fit)
        img_center_y_px = img_rect.height() / (2 * self._scale_fit)
        
        # Convert screen coordinates to image pixel coordinates (centered, Y-up)
        x_img_px = (screen_pos.x() - img_rect.x()) / self._scale_fit - img_center_x_px
        y_img_px = img_center_y_px - (screen_pos.y() - img_rect.y()) / self._scale_fit
        
        # Convert image pixel coordinates to millimeters
        x_mm = x_img_px * self._mm_per_px
        y_mm = y_img_px * self._mm_per_px
        
        return (x_mm, y_mm)
    
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
        if not self._pix or self._mm_per_px <= 0:
            return {
                'h_scale': 1.0,
                'h_offset': 0.0,
                'h_range': (-50.0, 50.0),
                'v_scale': 1.0,
                'v_offset': 0.0,
                'v_range': (-50.0, 50.0),
                'show_mm': True
            }
        
        img_rect = self._target_rect()
        if not img_rect.isValid():
            return {
                'h_scale': 1.0,
                'h_offset': 0.0,
                'h_range': (-50.0, 50.0),
                'v_scale': 1.0,
                'v_offset': 0.0,
                'v_range': (-50.0, 50.0),
                'show_mm': True
            }
        
        # Scale: screen pixels per mm
        scale = self._scale_fit / self._mm_per_px
        
        # Offset: where 0mm appears on screen
        # For centered coordinates, 0mm is at the center of the image
        h_offset = img_rect.x() + img_rect.width() / 2
        v_offset = img_rect.y() + img_rect.height() / 2
        
        # Range: visible range in mm
        w, h = self.image_pixel_size()
        half_width_mm = (w / 2) * self._mm_per_px
        half_height_mm = (h / 2) * self._mm_per_px
        
        return {
            'h_scale': scale,
            'h_offset': h_offset,
            'h_range': (-half_width_mm, half_width_mm),
            'v_scale': scale,
            'v_offset': v_offset,
            'v_range': (-half_height_mm, half_height_mm),
            'show_mm': True
        }

