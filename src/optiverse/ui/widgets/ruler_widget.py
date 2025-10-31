"""
Photoshop-style ruler widgets for the component editor canvas.

Provides horizontal and vertical rulers with:
- Measurement markings (in mm or pixels)
- Triangular cursor position indicators
- Synchronized with canvas coordinate system
"""

from __future__ import annotations

from typing import Optional
from PyQt6 import QtCore, QtGui, QtWidgets


class RulerWidget(QtWidgets.QWidget):
    """Base class for ruler widgets with position indicator."""
    
    # Ruler orientation
    HORIZONTAL = 0
    VERTICAL = 1
    
    def __init__(self, orientation: int = HORIZONTAL, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.orientation = orientation
        self._cursor_pos: Optional[float] = None  # Position in mm
        self._scale: float = 1.0  # Screen pixels per mm
        self._offset: float = 0.0  # Offset in screen pixels
        self._range_mm: tuple[float, float] = (-50.0, 50.0)  # Visible range in mm
        self._show_mm: bool = True  # Show mm units (else show pixels)
        
        # Ruler dimensions
        self.ruler_size = 25  # Height for horizontal, width for vertical
        
        # Set size policy
        if orientation == self.HORIZONTAL:
            self.setFixedHeight(self.ruler_size)
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed
            )
        else:
            self.setFixedWidth(self.ruler_size)
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Expanding
            )
        
        # Styling
        self.setStyleSheet("""
            RulerWidget {
                background-color: #E8E8E8;
                border: 1px solid #999;
            }
        """)
    
    def set_cursor_position(self, pos_mm: Optional[float]):
        """Set cursor position in mm (or None to hide indicator)."""
        self._cursor_pos = pos_mm
        self.update()
    
    def set_view_parameters(self, scale: float, offset: float, range_mm: tuple[float, float]):
        """
        Set view parameters for coordinate conversion.
        
        Args:
            scale: Screen pixels per mm
            offset: Offset in screen pixels (where 0mm appears on screen)
            range_mm: Tuple of (min_mm, max_mm) visible range
        """
        self._scale = scale
        self._offset = offset
        self._range_mm = range_mm
        self.update()
    
    def set_show_mm(self, show_mm: bool):
        """Set whether to show mm units (True) or pixels (False)."""
        self._show_mm = show_mm
        self.update()
    
    def paintEvent(self, event: QtGui.QPaintEvent):
        """Draw the ruler."""
        super().paintEvent(event)
        
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        # Draw background (already styled, but ensure it's filled)
        painter.fillRect(self.rect(), QtGui.QColor("#E8E8E8"))
        
        if self.orientation == self.HORIZONTAL:
            self._draw_horizontal_ruler(painter)
        else:
            self._draw_vertical_ruler(painter)
        
        # Draw cursor indicator
        if self._cursor_pos is not None:
            self._draw_indicator(painter, self._cursor_pos)
    
    def _draw_horizontal_ruler(self, painter: QtGui.QPainter):
        """Draw horizontal ruler markings."""
        width = self.width()
        height = self.height()
        
        # Determine tick spacing based on scale
        major_interval_mm = self._calculate_tick_interval()
        minor_interval_mm = major_interval_mm / 5
        
        # Calculate range of values to draw
        min_mm, max_mm = self._range_mm
        
        # Draw ticks and labels
        painter.setPen(QtGui.QPen(QtGui.QColor("#333"), 1))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Start from first major tick before min_mm
        start_major = (int(min_mm / major_interval_mm) - 1) * major_interval_mm
        
        # Draw minor ticks
        pos_mm = start_major
        while pos_mm <= max_mm:
            screen_x = self._mm_to_screen_x(pos_mm)
            if 0 <= screen_x <= width:
                is_major = abs(pos_mm % major_interval_mm) < 1e-6
                
                if is_major:
                    # Major tick (full height)
                    tick_height = height - 5
                    painter.drawLine(int(screen_x), height - tick_height, int(screen_x), height)
                    
                    # Draw label
                    if self._show_mm:
                        label = f"{pos_mm:.1f}" if abs(pos_mm) < 1000 else f"{pos_mm:.0f}"
                    else:
                        # Convert mm to pixels for display
                        pixels = pos_mm / (self._scale / self._get_canvas_scale())
                        label = f"{pixels:.0f}"
                    
                    painter.drawText(
                        QtCore.QRectF(screen_x - 30, 2, 60, 12),
                        QtCore.Qt.AlignmentFlag.AlignCenter,
                        label
                    )
                else:
                    # Minor tick
                    tick_height = 5
                    painter.drawLine(int(screen_x), height - tick_height, int(screen_x), height)
            
            pos_mm += minor_interval_mm
    
    def _draw_vertical_ruler(self, painter: QtGui.QPainter):
        """Draw vertical ruler markings."""
        width = self.width()
        height = self.height()
        
        # Determine tick spacing based on scale
        major_interval_mm = self._calculate_tick_interval()
        minor_interval_mm = major_interval_mm / 5
        
        # Calculate range of values to draw
        min_mm, max_mm = self._range_mm
        
        # Draw ticks and labels
        painter.setPen(QtGui.QPen(QtGui.QColor("#333"), 1))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Start from first major tick before min_mm
        start_major = (int(min_mm / major_interval_mm) - 1) * major_interval_mm
        
        # Draw minor ticks
        pos_mm = start_major
        while pos_mm <= max_mm:
            screen_y = self._mm_to_screen_y(pos_mm)
            if 0 <= screen_y <= height:
                is_major = abs(pos_mm % major_interval_mm) < 1e-6
                
                if is_major:
                    # Major tick (full width)
                    tick_width = width - 5
                    painter.drawLine(width - tick_width, int(screen_y), width, int(screen_y))
                    
                    # Draw label (rotated for vertical ruler)
                    if self._show_mm:
                        label = f"{pos_mm:.1f}" if abs(pos_mm) < 1000 else f"{pos_mm:.0f}"
                    else:
                        # Convert mm to pixels for display
                        pixels = pos_mm / (self._scale / self._get_canvas_scale())
                        label = f"{pixels:.0f}"
                    
                    painter.save()
                    painter.translate(width - 2, screen_y)
                    painter.rotate(-90)
                    painter.drawText(
                        QtCore.QRectF(-30, -10, 60, 12),
                        QtCore.Qt.AlignmentFlag.AlignCenter,
                        label
                    )
                    painter.restore()
                else:
                    # Minor tick
                    tick_width = 5
                    painter.drawLine(width - tick_width, int(screen_y), width, int(screen_y))
            
            pos_mm += minor_interval_mm
    
    def _draw_indicator(self, painter: QtGui.QPainter, pos_mm: float):
        """Draw triangular cursor position indicator."""
        if self.orientation == self.HORIZONTAL:
            screen_x = self._mm_to_screen_x(pos_mm)
            
            # Check if indicator is within visible range
            if screen_x < 0 or screen_x > self.width():
                return
            
            # Draw triangle pointing down
            points = [
                QtCore.QPointF(screen_x, 0),
                QtCore.QPointF(screen_x - 5, 7),
                QtCore.QPointF(screen_x + 5, 7)
            ]
            
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#FF4444")))
            painter.setPen(QtGui.QPen(QtGui.QColor("#CC0000"), 1))
            painter.drawPolygon(points)
            
        else:  # VERTICAL
            screen_y = self._mm_to_screen_y(pos_mm)
            
            # Check if indicator is within visible range
            if screen_y < 0 or screen_y > self.height():
                return
            
            # Draw triangle pointing right
            points = [
                QtCore.QPointF(0, screen_y),
                QtCore.QPointF(7, screen_y - 5),
                QtCore.QPointF(7, screen_y + 5)
            ]
            
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#FF4444")))
            painter.setPen(QtGui.QPen(QtGui.QColor("#CC0000"), 1))
            painter.drawPolygon(points)
    
    def _mm_to_screen_x(self, mm: float) -> float:
        """Convert mm coordinate to screen X coordinate."""
        # For horizontal ruler, map mm position to screen position
        # Assuming 0mm is at center (offset)
        return self._offset + mm * self._scale
    
    def _mm_to_screen_y(self, mm: float) -> float:
        """Convert mm (Y-up) to screen Y (pixels down)."""
        # Vertical ruler maps math Y-up to screen coordinates by inverting sign
        return self._offset - mm * self._scale
    
    def _calculate_tick_interval(self) -> float:
        """Calculate appropriate tick interval based on scale."""
        # Aim for major ticks every 50-100 pixels
        target_pixels = 75
        interval_mm = target_pixels / self._scale if self._scale > 0 else 10.0
        
        # Round to nice values (1, 2, 5, 10, 20, 50, 100, etc.)
        magnitude = 10 ** int(math.log10(interval_mm))
        normalized = interval_mm / magnitude
        
        if normalized < 1.5:
            nice_interval = magnitude
        elif normalized < 3.5:
            nice_interval = 2 * magnitude
        elif normalized < 7.5:
            nice_interval = 5 * magnitude
        else:
            nice_interval = 10 * magnitude
        
        return nice_interval
    
    def _get_canvas_scale(self) -> float:
        """Get the canvas scale factor (for pixel conversion)."""
        # This is a placeholder - actual value should be provided by canvas
        return 1.0


import math


class CanvasWithRulers(QtWidgets.QWidget):
    """Container widget that wraps a canvas with rulers."""
    
    def __init__(self, canvas_widget: QtWidgets.QWidget, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        
        self.canvas = canvas_widget
        
        # Create rulers
        self.h_ruler = RulerWidget(RulerWidget.HORIZONTAL, self)
        self.v_ruler = RulerWidget(RulerWidget.VERTICAL, self)
        
        # Create corner widget (just a blank space)
        self.corner = QtWidgets.QWidget(self)
        self.corner.setFixedSize(self.v_ruler.ruler_size, self.h_ruler.ruler_size)
        self.corner.setStyleSheet("background-color: #D0D0D0; border: 1px solid #999;")
        
        # Layout: corner, h_ruler, v_ruler, canvas
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        layout.addWidget(self.corner, 0, 0)
        layout.addWidget(self.h_ruler, 0, 1)
        layout.addWidget(self.v_ruler, 1, 0)
        layout.addWidget(self.canvas, 1, 1)
        
        # Set stretch factors so canvas takes all available space
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(1, 1)
        
        # Install event filter on canvas to track mouse movement
        self.canvas.installEventFilter(self)
        
        # Timer to periodically update ruler view parameters
        self._update_timer = QtCore.QTimer(self)
        self._update_timer.timeout.connect(self._update_ruler_parameters)
        self._update_timer.start(100)  # Update every 100ms
    
    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Filter canvas events to update ruler indicators."""
        if obj == self.canvas:
            if event.type() == QtCore.QEvent.Type.MouseMove:
                # Update ruler cursor position
                mouse_event = event
                self._update_cursor_position(mouse_event.pos())
            elif event.type() == QtCore.QEvent.Type.Leave:
                # Hide cursor indicators when mouse leaves canvas
                self.h_ruler.set_cursor_position(None)
                self.v_ruler.set_cursor_position(None)
        
        # IMPORTANT: Return False to allow events to pass through to the canvas
        # This ensures mouse dragging and other canvas interactions work normally
        return False
    
    def _update_cursor_position(self, canvas_pos: QtCore.QPoint):
        """Update ruler cursor position based on canvas mouse position."""
        # Try to get coordinate information from canvas
        if hasattr(self.canvas, '_screen_to_mm_coords'):
            # Canvas has method to convert screen to mm coords
            x_mm, y_mm = self.canvas._screen_to_mm_coords(canvas_pos)
            self.h_ruler.set_cursor_position(x_mm)
            self.v_ruler.set_cursor_position(y_mm)
        else:
            # Fallback: just hide indicators
            self.h_ruler.set_cursor_position(None)
            self.v_ruler.set_cursor_position(None)
    
    def _update_ruler_parameters(self):
        """Update ruler view parameters based on canvas state."""
        # Try to get view parameters from canvas
        if hasattr(self.canvas, '_get_ruler_view_params'):
            try:
                params = self.canvas._get_ruler_view_params()
                
                # Horizontal ruler parameters
                h_scale = params['h_scale']
                h_offset = params['h_offset']
                h_range = params['h_range']
                
                # Vertical ruler parameters
                v_scale = params['v_scale']
                v_offset = params['v_offset']
                v_range = params['v_range']
                
                self.h_ruler.set_view_parameters(h_scale, h_offset, h_range)
                self.v_ruler.set_view_parameters(v_scale, v_offset, v_range)
                
                # Set unit display
                show_mm = params.get('show_mm', True)
                self.h_ruler.set_show_mm(show_mm)
                self.v_ruler.set_show_mm(show_mm)
            except Exception:
                pass

