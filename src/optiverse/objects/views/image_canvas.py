from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

# Optional QtSvg for SVG clipboard/loads
try:
    from PyQt6 import QtSvg

    HAVE_QTSVG = True
except ImportError:
    HAVE_QTSVG = False


class ImageCanvas(QtWidgets.QLabel):
    clickedPoint = QtCore.pyqtSignal(float, float)
    imageDropped = QtCore.pyqtSignal(QtGui.QPixmap, str)
    pointsChanged = QtCore.pyqtSignal()  # Emitted when points change

    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._pix: QtGui.QPixmap | None = None
        self._svg_renderer: QtSvg.QSvgRenderer | None = None  # Native SVG renderer
        self._svg_cache_pixmap: QtGui.QPixmap | None = None  # Cached pre-rendered SVG
        self._svg_cache_size: QtCore.QSize = QtCore.QSize()  # Size of cached render
        self._scale_fit = 1.0
        self._pt1: tuple[float, float] | None = None
        self._pt2: tuple[float, float] | None = None
        self._src_path: str | None = None
        self.setAcceptDrops(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        # Drag state
        self._dragging_point: int | None = None  # 1 or 2 when dragging
        self._hover_point: int | None = None  # 1 or 2 when hovering
        self.setMouseTracking(True)

    def set_pixmap(self, pix: QtGui.QPixmap, source_path: str | None = None):
        # Normalize device pixel ratio to 1.0 for consistent size reporting
        if pix and not pix.isNull():
            img = pix.toImage()
            img.setDevicePixelRatio(1.0)
            pix = QtGui.QPixmap.fromImage(img)

        self._pix = pix
        self._src_path = source_path
        self._pt1 = None
        self._pt2 = None

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

    def get_points(self):
        return self._pt1, self._pt2

    def set_points(self, p1: tuple[float, float] | None, p2: tuple[float, float] | None):
        self._pt1 = p1
        self._pt2 = p2
        self.update()

    def clear_points(self):
        self._pt1 = None
        self._pt2 = None
        self.update()

    def image_pixel_size(self) -> tuple[int, int]:
        if not self._pix:
            return (0, 0)
        return (self._pix.width(), self._pix.height())

    def _get_point_at_screen_pos(
        self, screen_pos: QtCore.QPoint, threshold: float = 8.0
    ) -> int | None:
        """Check if screen position is near point 1 or 2. Returns 1, 2, or None."""
        if not self._pix:
            return None
        pixrect = self._target_rect()
        if not pixrect.contains(screen_pos):
            return None

        # Check point 2 first (so it takes priority if overlapping)
        if self._pt2:
            x2, y2 = self._pt2
            X2 = pixrect.x() + x2 * self._scale_fit
            Y2 = pixrect.y() + y2 * self._scale_fit
            dx = screen_pos.x() - X2
            dy = screen_pos.y() - Y2
            if (dx * dx + dy * dy) <= threshold * threshold:
                return 2

        # Check point 1
        if self._pt1:
            x1, y1 = self._pt1
            X1 = pixrect.x() + x1 * self._scale_fit
            Y1 = pixrect.y() + y1 * self._scale_fit
            dx = screen_pos.x() - X1
            dy = screen_pos.y() - Y1
            if (dx * dx + dy * dy) <= threshold * threshold:
                return 1

        return None

    def _screen_to_image_coords(self, screen_pos: QtCore.QPoint) -> tuple[float, float] | None:
        """Convert screen position to image pixel coordinates."""
        if not self._pix:
            return None
        pixrect = self._target_rect()
        if not pixrect.contains(screen_pos):
            return None
        x = (screen_pos.x() - pixrect.x()) / self._scale_fit
        y = (screen_pos.y() - pixrect.y()) / self._scale_fit
        # Clamp to image bounds
        x = max(0, min(x, self._pix.width()))
        y = max(0, min(y, self._pix.height()))
        return (x, y)

    def mousePressEvent(self, e: QtGui.QMouseEvent | None):
        if e is None or not self._pix:
            return
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            # Check if clicking on existing point to drag
            point_idx = self._get_point_at_screen_pos(e.pos())
            if point_idx is not None:
                self._dragging_point = point_idx
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                return

            # Otherwise, place new point
            coords = self._screen_to_image_coords(e.pos())
            if coords is None:
                return
            px, py = coords
            if self._pt1 is None:
                self._pt1 = (px, py)
            else:
                self._pt2 = (px, py)
            self.clickedPoint.emit(px, py)
            self.pointsChanged.emit()
            self.update()
        elif e.button() == QtCore.Qt.MouseButton.RightButton:
            self.clear_points()
            self.pointsChanged.emit()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent | None):
        if e is None or not self._pix:
            return

        # Handle dragging
        if self._dragging_point is not None:
            coords = self._screen_to_image_coords(e.pos())
            if coords is not None:
                if self._dragging_point == 1:
                    self._pt1 = coords
                elif self._dragging_point == 2:
                    self._pt2 = coords
                self.pointsChanged.emit()
                self.update()
            return

        # Handle hover cursor
        point_idx = self._get_point_at_screen_pos(e.pos())
        if point_idx != self._hover_point:
            self._hover_point = point_idx
            if point_idx is not None:
                self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent | None):
        if e is None:
            return
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            if self._dragging_point is not None:
                self._dragging_point = None
                # Update cursor based on current position
                point_idx = self._get_point_at_screen_pos(e.pos())
                if point_idx is not None:
                    self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
                else:
                    self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent | None):
        if e is None:
            return
        md = e.mimeData()
        if md is not None and (md.hasImage() or md.hasUrls()):
            e.acceptProposedAction()

    def dropEvent(self, e: QtGui.QDropEvent | None):
        if e is None:
            return
        md = e.mimeData()
        if md is None:
            return
        # Direct bitmap drop
        if md.hasImage():
            img_data = md.imageData()
            if img_data is None:
                return
            img = img_data
            if isinstance(img, QtGui.QImage):
                pix = QtGui.QPixmap.fromImage(img)
            elif isinstance(img, QtGui.QPixmap):
                pix = img
            else:
                pix = QtGui.QPixmap()
            if not pix.isNull():
                self.imageDropped.emit(pix, "")
                e.acceptProposedAction()
                return

        # File URL(s)
        if md.hasUrls():
            for url in md.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    low = path.lower()
                    if low.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg")):
                        pix_file: QtGui.QPixmap | None
                        if low.endswith(".svg") and HAVE_QTSVG:
                            pix_file = self._render_svg_to_pixmap(path)
                            if pix_file is not None:
                                self.imageDropped.emit(pix_file, path)
                                e.acceptProposedAction()
                                return
                        else:
                            pix_file = QtGui.QPixmap(path)
                            if not pix_file.isNull():
                                self.imageDropped.emit(pix_file, path)
                                e.acceptProposedAction()
                                return
        e.ignore()

    def _target_rect(self) -> QtCore.QRect:
        if not self._pix:
            return QtCore.QRect(0, 0, self.width(), self.height())
        pw = self._pix.width()
        ph = self._pix.height()
        ww, wh = self.width(), self.height()
        s = min(ww / pw, wh / ph) if pw > 0 and ph > 0 else 1.0
        self._scale_fit = s
        tw, th = int(pw * s), int(ph * s)
        x = int((ww - tw) / 2)
        y = int((wh - th) / 2)
        return QtCore.QRect(x, y, tw, th)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        if self._pix:
            tgt = self._target_rect()

            # Use cached SVG pixmap if available for better performance
            if self._svg_renderer is not None and self._svg_cache_pixmap is not None:
                # Check if we need to update cache due to significant resize
                if (
                    tgt.width() > self._svg_cache_size.width() * 1.2
                    or tgt.height() > self._svg_cache_size.height() * 1.2
                ):
                    self._update_svg_cache()

                # Draw cached pixmap with smooth transformation
                p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
                p.drawPixmap(tgt, self._svg_cache_pixmap)
            else:
                p.drawPixmap(tgt, self._pix)
            if self._pt1:
                x1, y1 = self._pt1
                X1 = tgt.x() + x1 * self._scale_fit
                Y1 = tgt.y() + y1 * self._scale_fit
                # Highlight if hovering or dragging
                is_active = self._hover_point == 1 or self._dragging_point == 1
                radius = 6 if is_active else 5
                pen_width = 3 if is_active else 2
                pen = QtGui.QPen(QtGui.QColor(0, 180, 255), pen_width)
                p.setPen(pen)
                alpha = 150 if is_active else 100
                p.setBrush(QtGui.QBrush(QtGui.QColor(0, 180, 255, alpha)))
                p.drawEllipse(QtCore.QPointF(X1, Y1), radius, radius)
            if self._pt2:
                x2, y2 = self._pt2
                X2 = tgt.x() + x2 * self._scale_fit
                Y2 = tgt.y() + y2 * self._scale_fit
                # Highlight if hovering or dragging
                is_active = self._hover_point == 2 or self._dragging_point == 2
                radius = 6 if is_active else 5
                pen_width = 3 if is_active else 2
                pen = QtGui.QPen(QtGui.QColor(255, 80, 0), pen_width)
                p.setPen(pen)
                alpha = 150 if is_active else 100
                p.setBrush(QtGui.QBrush(QtGui.QColor(255, 80, 0, alpha)))
                p.drawEllipse(QtCore.QPointF(X2, Y2), radius, radius)
            if self._pt1 and self._pt2:
                pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 2, QtCore.Qt.PenStyle.DashLine)
                p.setPen(pen)
                p.drawLine(
                    QtCore.QLineF(
                        tgt.x() + self._pt1[0] * self._scale_fit,
                        tgt.y() + self._pt1[1] * self._scale_fit,
                        tgt.x() + self._pt2[0] * self._scale_fit,
                        tgt.y() + self._pt2[1] * self._scale_fit,
                    )
                )

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
    def _render_svg_to_pixmap(path_or_bytes) -> QtGui.QPixmap | None:
        """Render SVG file or bytes to QPixmap."""
        if not HAVE_QTSVG:
            return None
        try:
            if isinstance(path_or_bytes, (bytes, bytearray)):
                renderer = QtSvg.QSvgRenderer(path_or_bytes)
            else:
                renderer = QtSvg.QSvgRenderer(str(path_or_bytes))
            if not renderer.isValid():
                return None
            size = renderer.defaultSize()
            if not size.isValid() or size.isEmpty():
                size = QtCore.QSize(1200, 800)
            img = QtGui.QImage(size, QtGui.QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(0)
            painter = QtGui.QPainter(img)
            renderer.render(painter)
            painter.end()
            return QtGui.QPixmap.fromImage(img)
        except (OSError, RuntimeError):
            return None
