"""
Multi-line Image Canvas for Component Editor.

Extends ImageCanvas to support multiple optical interfaces with:
- Visual representation as colored lines
- Draggable endpoints
- Color coding by interface type
- Unified interface for simple (1 line) and complex (N lines) components
"""

from __future__ import annotations

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
    """A single optical interface line."""
    x1: float  # Start point X (in image pixels)
    y1: float  # Start point Y
    x2: float  # End point X
    y2: float  # End point Y
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
    
    Signals:
        imageDropped: Emitted when image is dropped
        linesChanged: Emitted when any line changes
        lineSelected: Emitted when a line is selected (index)
    """
    imageDropped = QtCore.pyqtSignal(QtGui.QPixmap, str)
    linesChanged = QtCore.pyqtSignal()  # Any line changed
    lineSelected = QtCore.pyqtSignal(int)  # Line index selected
    
    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._pix: Optional[QtGui.QPixmap] = None
        self._scale_fit = 1.0
        self._src_path: Optional[str] = None
        self.setAcceptDrops(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        
        # Multiple lines support
        self._lines: List[InterfaceLine] = []
        self._selected_line: int = -1  # Currently selected line index
        
        # Drag state
        self._dragging_line: int = -1  # Index of line being dragged
        self._dragging_point: int = 0  # 1 for start point, 2 for end point
        self._hover_line: int = -1  # Line being hovered
        self._hover_point: int = 0  # Point being hovered (1 or 2)
        
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
            if self._selected_line == index:
                self._selected_line = -1
            elif self._selected_line > index:
                self._selected_line -= 1
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
        self._selected_line = -1
        self.update()
        self.linesChanged.emit()
    
    def set_lines(self, lines: List[InterfaceLine]):
        """Set all lines at once."""
        self._lines = list(lines)
        self._selected_line = -1
        self.update()
        self.linesChanged.emit()
    
    def get_selected_line_index(self) -> int:
        """Get currently selected line index (-1 if none)."""
        return self._selected_line
    
    def select_line(self, index: int):
        """Select a line by index."""
        if -1 <= index < len(self._lines):
            self._selected_line = index
            self.update()
            if index >= 0:
                self.lineSelected.emit(index)
    
    def set_drag_lock(self, line_index: int):
        """Lock dragging to only the specified line."""
        self._drag_locked_line = line_index
        self._selected_line = line_index
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
    
    def _draw_line(self, p: QtGui.QPainter, img_rect: QtCore.QRect, line: InterfaceLine, index: int):
        """Draw a single interface line."""
        # Convert image coordinates to screen coordinates
        x1_screen = img_rect.x() + line.x1 * self._scale_fit
        y1_screen = img_rect.y() + line.y1 * self._scale_fit
        x2_screen = img_rect.x() + line.x2 * self._scale_fit
        y2_screen = img_rect.y() + line.y2 * self._scale_fit
        
        # Determine appearance
        is_selected = (index == self._selected_line)
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
        p.drawLine(QtCore.QPointF(x1_screen, y1_screen), 
                   QtCore.QPointF(x2_screen, y2_screen))
        
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
        
        # Draw label if exists
        if line.label and is_selected:
            p.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black))
            mid_x = (x1_screen + x2_screen) / 2
            mid_y = (y1_screen + y2_screen) / 2
            p.drawText(QtCore.QPointF(mid_x + 10, mid_y - 10), line.label)
    
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
        
        # Check all lines (prioritize selected line)
        search_order = list(range(len(self._lines)))
        if self._selected_line >= 0:
            # Check selected line first
            search_order.remove(self._selected_line)
            search_order.insert(0, self._selected_line)
        
        for i in search_order:
            line = self._lines[i]
            
            # Check point 2 first (so it takes priority if overlapping)
            x2_screen = img_rect.x() + line.x2 * self._scale_fit
            y2_screen = img_rect.y() + line.y2 * self._scale_fit
            dx = screen_pos.x() - x2_screen
            dy = screen_pos.y() - y2_screen
            if (dx*dx + dy*dy) <= threshold*threshold:
                return (i, 2)
            
            # Check point 1
            x1_screen = img_rect.x() + line.x1 * self._scale_fit
            y1_screen = img_rect.y() + line.y1 * self._scale_fit
            dx = screen_pos.x() - x1_screen
            dy = screen_pos.y() - y1_screen
            if (dx*dx + dy*dy) <= threshold*threshold:
                return (i, 1)
        
        return (-1, 0)
    
    def mousePressEvent(self, e: QtMouseEvent):
        """Handle mouse press."""
        if not self._pix or e.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        
        line_idx, point_num = self._get_line_and_point_at(e.pos())
        
        if line_idx >= 0:
            # Check drag lock
            if self._drag_locked_line >= 0 and line_idx != self._drag_locked_line:
                # Trying to drag a different line than the locked one - ignore
                return
            
            # Start dragging
            self._dragging_line = line_idx
            self._dragging_point = point_num
            self.select_line(line_idx)
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
        else:
            # Click on empty space - add new point or select line
            img_rect = self._target_rect()
            if img_rect.contains(e.pos()):
                # Convert to image coordinates
                x_img = (e.pos().x() - img_rect.x()) / self._scale_fit
                y_img = (e.pos().y() - img_rect.y()) / self._scale_fit
                
                # If drag locked, clicking empty space clears the lock
                if self._drag_locked_line >= 0:
                    self.clear_drag_lock()
                else:
                    # For now, just deselect
                    self.select_line(-1)
    
    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        """Handle mouse move."""
        if self._dragging_line >= 0:
            # Dragging a point
            img_rect = self._target_rect()
            if not img_rect.isValid():
                return
            
            # Convert to image coordinates
            x_img = (e.pos().x() - img_rect.x()) / self._scale_fit
            y_img = (e.pos().y() - img_rect.y()) / self._scale_fit
            
            # Clamp to image bounds
            w, h = self.image_pixel_size()
            x_img = max(0, min(w, x_img))
            y_img = max(0, min(h, y_img))
            
            # Update line
            line = self._lines[self._dragging_line]
            if self._dragging_point == 1:
                line.x1 = x_img
                line.y1 = y_img
            else:
                line.x2 = x_img
                line.y2 = y_img
            
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
                self._hover_line = -1
                self._hover_point = 0
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            
            self.update()
    
    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        """Handle mouse release."""
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            self._dragging_line = -1
            self._dragging_point = 0
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

