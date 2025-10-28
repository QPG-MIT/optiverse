from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from ...platform.paths import is_macos


class GraphicsView(QtWidgets.QGraphicsView):
    zoomChanged = QtCore.pyqtSignal()

    def __init__(self, scene: QtWidgets.QGraphicsScene | None = None):
        super().__init__(scene)
        self.setRenderHints(
            QtGui.QPainter.RenderHint.Antialiasing | QtGui.QPainter.RenderHint.TextAntialiasing
        )
        
        # Dark mode state (detect system preference by default)
        self._dark_mode = self._detect_system_dark_mode()
        
        # Mac-specific optimizations for performance
        if is_macos():
            # On Mac, use MinimalViewportUpdate for better performance with Retina displays
            # This significantly reduces lag while avoiding grid artifacts
            # MinimalViewportUpdate: only updates bounding rect of changed items
            # but still properly redraws background (grid) during pan/zoom
            self.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        else:
            # Use FullViewportUpdate to properly render drawForeground (scale bar)
            # BoundingRectViewportUpdate causes scale bar artifacts during panning
            self.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
        self.setAcceptDrops(True)
        
        # Enable scrollbars to support panning (visible when scene larger than viewport)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Enable gesture support for Mac trackpad
        if is_macos():
            self.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
            self.viewport().grabGesture(QtCore.Qt.GestureType.PinchGesture)
            self.viewport().grabGesture(QtCore.Qt.GestureType.PanGesture)

        # scale bar prefs
        self._sb_len_px = 120
        self._sb_height_px = 10
        self._sb_margin_px = 10
        self._sb_font = QtGui.QFont()
        self._sb_font.setPointSize(9)

        # Ghost preview during drag (Phase 1.1: Ghost Preview System)
        self._ghost_item: QtWidgets.QGraphicsItem | None = None
        self._ghost_rec: dict | None = None

        # Pan control state (Phase 3.1: Pan Controls)
        self._hand = False  # Track space key state for pan mode

        # Magnetic snap alignment guides
        self._snap_guides: list[tuple[str, float]] = []  # [("horizontal", y), ("vertical", x)]
        
        # Mac trackpad gesture state
        self._pinch_start_scale = 1.0
        self._is_panning_gesture = False
        
        # Dark mode state
        self._dark_mode = self._detect_system_dark_mode() if is_macos() else False
    
    def _detect_system_dark_mode(self) -> bool:
        """Detect if macOS is in dark mode."""
        if not is_macos():
            return False
        try:
            # Use Qt's palette to detect dark mode
            palette = QtWidgets.QApplication.palette()
            bg_color = palette.color(QtGui.QPalette.ColorRole.Window)
            # If background is dark (low lightness), we're in dark mode
            return bg_color.lightness() < 128
        except Exception:
            return False
    
    def set_dark_mode(self, enabled: bool):
        """Set dark mode on/off."""
        self._dark_mode = enabled
        self.viewport().update()
    
    def is_dark_mode(self) -> bool:
        """Check if dark mode is enabled."""
        return self._dark_mode

    def wheelEvent(self, e: QtGui.QWheelEvent):
        """Handle wheel events including Mac trackpad scrolling.
        
        Mac trackpads send:
        - pixelDelta() for smooth scrolling gestures (two-finger scroll)
        - angleDelta() for traditional wheel events
        """
        # Check for pixel-based scrolling (Mac trackpad two-finger scroll)
        pixel_delta = e.pixelDelta()
        angle_delta = e.angleDelta()
        
        # On Mac, use pixel deltas if available (smoother for trackpad)
        if is_macos() and not pixel_delta.isNull():
            # Two-finger scroll on trackpad
            # Check if this is primarily vertical scrolling with Command key (for zoom)
            if e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                # Cmd+scroll = zoom (like in most Mac apps)
                delta_y = pixel_delta.y()
                if abs(delta_y) > 0:
                    # Smoother zoom for trackpad
                    factor = 1.0 + (delta_y * 0.01)  # More gradual than mouse wheel
                    factor = max(0.5, min(2.0, factor))  # Limit zoom per event
                    self.scale(factor, factor)
                    self.zoomChanged.emit()
                    # Force viewport update for clean grid rendering
                    self.viewport().update()
                    e.accept()
                    return
            else:
                # Regular two-finger scroll = pan
                # Use scrollbars for smooth panning
                h_bar = self.horizontalScrollBar()
                v_bar = self.verticalScrollBar()
                h_bar.setValue(h_bar.value() - pixel_delta.x())
                v_bar.setValue(v_bar.value() - pixel_delta.y())
                # Force full viewport update to ensure grid redraws cleanly
                self.viewport().update()
                e.accept()
                return
        
        # Traditional mouse wheel or fallback behavior
        if not angle_delta.isNull():
            delta_y = angle_delta.y()
            if delta_y != 0:
                factor = 1.15 if delta_y > 0 else 1 / 1.15
                self.scale(factor, factor)
                self.zoomChanged.emit()
                self.viewport().update()
                e.accept()
                return
        
        e.ignore()

    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        self.zoomChanged.emit()
        self.viewport().update()
    
    def viewportEvent(self, event: QtCore.QEvent) -> bool:
        """Handle gesture events for Mac trackpad support."""
        if event.type() == QtCore.QEvent.Type.Gesture:
            return self._handle_gesture_event(event)
        return super().viewportEvent(event)
    
    def _handle_gesture_event(self, event: QtGui.QGestureEvent) -> bool:
        """Process pinch and pan gestures from Mac trackpad."""
        pinch = event.gesture(QtCore.Qt.GestureType.PinchGesture)
        if pinch:
            return self._handle_pinch_gesture(pinch)
        
        # Note: PanGesture is handled via wheelEvent pixelDelta for better control
        return True
    
    def _handle_pinch_gesture(self, gesture: QtWidgets.QGesture) -> bool:
        """Handle pinch-to-zoom gesture from Mac trackpad.
        
        This provides natural two-finger pinch zooming like in Safari, Preview, etc.
        """
        if not isinstance(gesture, QtWidgets.QPinchGesture):
            return False
        
        state = gesture.state()
        
        if state == QtCore.Qt.GestureState.GestureStarted:
            # Store initial scale
            self._pinch_start_scale = self.transform().m11()
        
        elif state == QtCore.Qt.GestureState.GestureUpdated:
            # Apply incremental scaling
            scale_factor = gesture.scaleFactor()
            
            # Apply the scaling relative to the gesture center point
            # Get the center point in viewport coordinates
            center_point = gesture.centerPoint().toPoint()
            
            # Map to scene coordinates for proper anchor
            old_pos = self.mapToScene(center_point)
            
            # Apply scale
            self.scale(scale_factor, scale_factor)
            
            # Adjust to keep the point under the gesture center
            new_pos = self.mapToScene(center_point)
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
            
            self.zoomChanged.emit()
            # Force viewport update for clean grid rendering
            self.viewport().update()
        
        elif state == QtCore.Qt.GestureState.GestureFinished:
            # Final update
            self.viewport().update()
        
        return True

    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF):
        """Draw grid in background (MUCH faster than QGraphicsItems!)."""
        super().drawBackground(painter, rect)
        
        # Draw background color
        if self._dark_mode:
            painter.fillRect(rect, QtGui.QColor(25, 25, 28))  # Dark background
        else:
            painter.fillRect(rect, QtGui.QColor(255, 255, 255))  # White background
        
        # Get visible area in scene coordinates
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        
        # Add small margin
        margin = 500  # Reduced margin for better performance
        xmin = int(visible_rect.left()) - margin
        xmax = int(visible_rect.right()) + margin
        ymin = int(visible_rect.top()) - margin
        ymax = int(visible_rect.bottom()) + margin
        
        # Adaptive grid density based on zoom
        zoom_scale = self.transform().m11()
        
        # More aggressive step increases to prevent lag when zoomed out
        if zoom_scale > 0.5:
            step = 1  # 1mm grid
        elif zoom_scale > 0.1:
            step = 10  # 1cm grid
        elif zoom_scale > 0.05:
            step = 100  # 10cm grid
        elif zoom_scale > 0.01:
            step = 1000  # 1m grid
        elif zoom_scale > 0.005:
            step = 5000  # 5m grid
        else:
            step = 10000  # 10m grid - very zoomed out
        
        # Performance optimization: limit number of lines drawn
        # Calculate how many lines would be drawn
        x_range = xmax - xmin
        y_range = ymax - ymin
        max_lines_per_axis = 500  # Maximum lines to draw in each direction
        
        # If we would draw too many lines, increase step size
        potential_x_lines = int(x_range / step)
        potential_y_lines = int(y_range / step)
        
        if potential_x_lines > max_lines_per_axis:
            # Calculate required step, ensuring proper rounding
            required_step = x_range / max_lines_per_axis
            # Round up to nearest multiple of 10 to get nice numbers
            new_step = int((required_step + 9) / 10) * 10
            step = max(step, new_step)
        
        if potential_y_lines > max_lines_per_axis:
            # Calculate required step, ensuring proper rounding
            required_step = y_range / max_lines_per_axis
            # Round up to nearest multiple of 10 to get nice numbers
            new_step = int((required_step + 9) / 10) * 10
            step = max(step, new_step)
        
        # Skip grid entirely if step is too large (too zoomed out)
        if step > 50000:
            painter.save()
            # Just draw axes
            if self._dark_mode:
                axis_pen = QtGui.QPen(QtGui.QColor(80, 82, 87))
            else:
                axis_pen = QtGui.QPen(QtGui.QColor(170, 170, 170))
            axis_pen.setStyle(QtCore.Qt.PenStyle.DashLine)
            axis_pen.setCosmetic(True)
            axis_pen.setWidth(1)
            painter.setPen(axis_pen)
            if ymin <= 0 <= ymax:
                painter.drawLine(QtCore.QPointF(xmin, 0), QtCore.QPointF(xmax, 0))
            if xmin <= 0 <= xmax:
                painter.drawLine(QtCore.QPointF(0, ymin), QtCore.QPointF(0, ymax))
            painter.restore()
            return
        
        # Setup pens based on dark mode
        if self._dark_mode:
            minor_pen = QtGui.QPen(QtGui.QColor(40, 42, 47))  # Subtle dark grid
            major_pen = QtGui.QPen(QtGui.QColor(60, 62, 67))  # More visible dark grid
            axis_pen = QtGui.QPen(QtGui.QColor(80, 82, 87))   # Axis lines
        else:
            minor_pen = QtGui.QPen(QtGui.QColor(242, 242, 242))  # Light gray grid
            major_pen = QtGui.QPen(QtGui.QColor(215, 215, 215))  # Darker gray grid
            axis_pen = QtGui.QPen(QtGui.QColor(170, 170, 170))   # Axis lines
        
        axis_pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        
        for pen in (minor_pen, major_pen, axis_pen):
            pen.setCosmetic(True)
            pen.setWidth(1)
        
        painter.save()
        
        # Draw vertical lines with line count limit
        x = xmin - (xmin % step)  # Align to grid
        line_count = 0
        while x <= xmax and line_count < max_lines_per_axis:
            if x % (step * 10) == 0:
                painter.setPen(major_pen)
            else:
                painter.setPen(minor_pen)
            painter.drawLine(QtCore.QPointF(x, ymin), QtCore.QPointF(x, ymax))
            x += step
            line_count += 1
        
        # Draw horizontal lines with line count limit
        y = ymin - (ymin % step)  # Align to grid
        line_count = 0
        while y <= ymax and line_count < max_lines_per_axis:
            if y % (step * 10) == 0:
                painter.setPen(major_pen)
            else:
                painter.setPen(minor_pen)
            painter.drawLine(QtCore.QPointF(xmin, y), QtCore.QPointF(xmax, y))
            y += step
            line_count += 1
        
        # Draw axes
        painter.setPen(axis_pen)
        if ymin <= 0 <= ymax:
            painter.drawLine(QtCore.QPointF(xmin, 0), QtCore.QPointF(xmax, 0))
        if xmin <= 0 <= xmax:
            painter.drawLine(QtCore.QPointF(0, ymin), QtCore.QPointF(0, ymax))
        
        painter.restore()
    
    def drawForeground(self, painter: QtGui.QPainter, rect: QtCore.QRectF):
        # Draw snap alignment guides first (in scene coordinates)
        if self._snap_guides:
            painter.save()
            # Stay in scene coordinates for guides
            pen = QtGui.QPen(QtGui.QColor(255, 0, 255, 180))  # Magenta guides
            pen.setWidth(2)
            pen.setCosmetic(True)
            pen.setStyle(QtCore.Qt.PenStyle.DashLine)
            painter.setPen(pen)
            
            visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
            
            for guide_type, coord in self._snap_guides:
                if guide_type == "horizontal":
                    # Draw horizontal line at Y coordinate
                    painter.drawLine(
                        QtCore.QPointF(visible_rect.left(), coord),
                        QtCore.QPointF(visible_rect.right(), coord)
                    )
                elif guide_type == "vertical":
                    # Draw vertical line at X coordinate
                    painter.drawLine(
                        QtCore.QPointF(coord, visible_rect.top()),
                        QtCore.QPointF(coord, visible_rect.bottom())
                    )
            
            painter.restore()
        
        # Draw scale bar in viewport coordinates
        painter.save()
        painter.resetTransform()

        vsize = self.viewport().size()
        box_w = self._sb_len_px + 70
        box_h = self._sb_height_px + 22
        x0 = self._sb_margin_px
        y0 = vsize.height() - box_h - self._sb_margin_px

        # pixels per unit (assume mm world for now) = m11
        px_per_mm = max(1e-12, self.transform().m11())
        mm_value = self._sb_len_px / px_per_mm

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        
        # Scale bar colors based on dark mode
        if self._dark_mode:
            painter.setPen(QtGui.QPen(QtGui.QColor(100, 100, 100, 90)))
            painter.setBrush(QtGui.QColor(40, 40, 45, 200))
            painter.drawRoundedRect(x0, y0, box_w, box_h, 6, 6)
            
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(200, 200, 200))
            painter.drawRect(x0 + 12, y0 + 11, self._sb_len_px, self._sb_height_px)
            
            painter.setPen(QtGui.QColor(220, 220, 220))
        else:
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 90)))
            painter.setBrush(QtGui.QColor(255, 255, 255, 200))
            painter.drawRoundedRect(x0, y0, box_w, box_h, 6, 6)
            
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(30, 30, 30))
            painter.drawRect(x0 + 12, y0 + 11, self._sb_len_px, self._sb_height_px)
            
            painter.setPen(QtGui.QColor(20, 20, 20))
        
        painter.setFont(self._sb_font)
        label = f"{mm_value:.1f} mm"
        painter.drawText(x0 + 12 + self._sb_len_px + 8, y0 + 11 + self._sb_height_px, label)

        painter.restore()

    # ----- Magnetic Snap Guide Methods -----
    def set_snap_guides(self, guide_lines: list[tuple[str, float]]):
        """Set alignment guide lines for magnetic snap feedback.
        
        Args:
            guide_lines: List of (type, coordinate) tuples.
                        e.g., [("horizontal", 100.0), ("vertical", 200.0)]
        """
        self._snap_guides = guide_lines
        self.viewport().update()
    
    def clear_snap_guides(self):
        """Clear all alignment guide lines."""
        if self._snap_guides:
            self._snap_guides = []
            self.viewport().update()
    
    # ----- Ghost Preview Methods (Phase 1.1) -----
    def _clear_ghost(self):
        """Remove ghost preview item from scene."""
        if self._ghost_item is not None:
            try:
                # The ghost is owned by the scene; remove it safely
                if self._ghost_item.scene() is not None:
                    self.scene().removeItem(self._ghost_item)
            except Exception:
                pass
        self._ghost_item = None
        self._ghost_rec = None

    def _make_ghost(self, rec: dict, scene_pos: QtCore.QPointF):
        """
        Build a semi-transparent ghost preview item for drag operation.
        
        The ghost shows exactly what will be dropped and where.
        """
        # Clear any existing ghost first
        if self._ghost_item is not None:
            self._clear_ghost()

        # Import here to avoid circular imports
        from ...core.models import BeamsplitterParams, LensParams, MirrorParams, SLMParams, WaveplateParams
        from ..beamsplitters import BeamsplitterItem
        from ..lenses import LensItem
        from ..mirrors import MirrorItem
        from ..misc import SLMItem
        from ..waveplates import WaveplateItem

        # Determine default angle for this component type
        kind = (rec.get("kind") or "lens").lower()
        if "angle_deg" in rec:
            angle = float(rec["angle_deg"])
        else:
            # Default angles per component type
            if kind == "lens":
                angle = 90.0
            elif kind == "beamsplitter":
                angle = 45.0
            elif kind == "waveplate":
                angle = 90.0
            elif kind == "mirror":
                angle = 0.0
            else:
                angle = 0.0

        # Extract common parameters (normalized 1000px system)
        name = rec.get("name")
        img = rec.get("image_path")
        line_px = tuple(rec.get("line_px", (0, 0, 1, 0)))
        # Support new object_height_mm and legacy object_height/length_mm
        object_height_mm = float(rec.get("object_height_mm", rec.get("object_height", rec.get("length_mm", 60.0))))
        # mm_per_pixel computed from object_height_mm in normalized 1000px system

        # Create the appropriate item type with images for visual feedback
        if kind == "lens":
            efl_mm = float(rec.get("efl_mm", 100.0))
            params = LensParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle,
                efl_mm=efl_mm,
                object_height_mm=object_height_mm,
                image_path=img,
                line_px=line_px,
                name=name
            )
            item = LensItem(params)
        elif kind == "beamsplitter":
            if "split_TR" in rec and isinstance(rec["split_TR"], (list, tuple)) and len(rec["split_TR"]) == 2:
                T, R = float(rec["split_TR"][0]), float(rec["split_TR"][1])
            else:
                T, R = float(rec.get("split_T", 50.0)), float(rec.get("split_R", 50.0))
            params = BeamsplitterParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle,
                object_height_mm=object_height_mm,
                split_T=T,
                split_R=R,
                image_path=img,
                line_px=line_px,
                name=name,
                is_polarizing=bool(rec.get("is_polarizing", False)),
                pbs_transmission_axis_deg=float(rec.get("pbs_transmission_axis_deg", 0.0)),
            )
            item = BeamsplitterItem(params)
        elif kind == "waveplate":
            phase_shift_deg = float(rec.get("phase_shift_deg", 90.0))
            fast_axis_deg = float(rec.get("fast_axis_deg", 0.0))
            params = WaveplateParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle,
                object_height_mm=object_height_mm,
                phase_shift_deg=phase_shift_deg,
                fast_axis_deg=fast_axis_deg,
                image_path=img,
                line_px=line_px,
                name=name
            )
            item = WaveplateItem(params)
        elif kind == "slm":
            params = SLMParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle,
                object_height_mm=object_height_mm,
                image_path=img,
                line_px=line_px,
                name=name
            )
            item = SLMItem(params)
        else:  # mirror (default)
            params = MirrorParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle,
                object_height_mm=object_height_mm,
                image_path=img,
                line_px=line_px,
                name=name
            )
            item = MirrorItem(params)

        # Make it a non-interactive "ghost"
        item.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        item.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        item.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        item.setOpacity(0.7)  # Semi-transparent ghost (increased for better visibility)
        item.setZValue(9999)  # Render on top

        # Add to scene
        self.scene().addItem(item)
        self._ghost_item = item
        self._ghost_rec = dict(rec)  # Keep a copy for later use
        
        # Force viewport update to ensure ghost is visible
        self.viewport().update()

    # ----- drag & drop (images and components) -----
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        md = e.mimeData()
        if md.hasFormat("application/x-optics-component"):
            # Build ghost right away so the moment you cross into the canvas you see it
            try:
                import json
                rec = json.loads(bytes(md.data("application/x-optics-component")).decode("utf-8"))
                self._clear_ghost()
                self._make_ghost(rec, self.mapToScene(e.position().toPoint()))
            except Exception as ex:
                # Log error for debugging
                import traceback
                print(f"Ghost preview error: {ex}")
                traceback.print_exc()
            e.acceptProposedAction()
        elif md.hasImage() or md.hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        md = e.mimeData()
        if md.hasFormat("application/x-optics-component"):
            # Move the ghost with the pointer; if it doesn't exist yet, (re)create it
            try:
                if self._ghost_item is None:
                    import json
                    rec = json.loads(bytes(md.data("application/x-optics-component")).decode("utf-8"))
                    self._make_ghost(rec, self.mapToScene(e.position().toPoint()))
                else:
                    self._ghost_item.setPos(self.mapToScene(e.position().toPoint()))
                    self.viewport().update()  # Force redraw as ghost moves
            except Exception as ex:
                print(f"Ghost move error: {ex}")
            e.acceptProposedAction()
        elif md.hasImage() or md.hasUrls():
            e.acceptProposedAction()

    def dragLeaveEvent(self, e: QtGui.QDragLeaveEvent):
        """Clear ghost when drag leaves the view."""
        self._clear_ghost()
        e.accept()

    def dropEvent(self, e: QtGui.QDropEvent):
        scene = self.scene()
        if scene is None:
            e.ignore()
            return
        md = e.mimeData()
        pos_view = e.position().toPoint()
        scene_pos = self.mapToScene(pos_view)

        # Component from library
        if md.hasFormat("application/x-optics-component"):
            import json
            data = md.data("application/x-optics-component")
            try:
                rec = json.loads(bytes(data).decode("utf-8"))
            except Exception:
                e.ignore()
                return

            # Finalize: remove ghost and create the real object
            self._clear_ghost()

            # Ensure we drop with the same default angle we previewed
            if "angle_deg" not in rec:
                kind = (rec.get("kind") or "lens").lower()
                if kind == "lens":
                    rec["angle_deg"] = 90.0
                elif kind == "beamsplitter":
                    rec["angle_deg"] = 45.0
                elif kind == "mirror":
                    rec["angle_deg"] = 0.0
                else:
                    rec["angle_deg"] = 0.0

            self.parent().on_drop_component(rec, scene_pos)
            e.acceptProposedAction()
            return

        # Direct image
        if md.hasImage():
            img = md.imageData()
            if isinstance(img, QtGui.QImage):
                pix = QtGui.QPixmap.fromImage(img)
            elif isinstance(img, QtGui.QPixmap):
                pix = img
            else:
                pix = QtGui.QPixmap()
            if not pix.isNull():
                item = QtWidgets.QGraphicsPixmapItem(pix)
                item.setPos(scene_pos - QtCore.QPointF(pix.width() / 2, pix.height() / 2))
                scene.addItem(item)
                e.acceptProposedAction()
                return

        # File URLs
        if md.hasUrls():
            for url in md.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if path.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
                        pix = QtGui.QPixmap(path)
                        if not pix.isNull():
                            item = QtWidgets.QGraphicsPixmapItem(pix)
                            item.setPos(scene_pos - QtCore.QPointF(pix.width() / 2, pix.height() / 2))
                            scene.addItem(item)
                            e.acceptProposedAction()
                            return
        e.ignore()

    # ----- Pan Controls (Phase 3.1: Space + Middle Button) -----
    def keyPressEvent(self, e: QtGui.QKeyEvent):
        """Handle key press for pan mode (Space key).
        
        Note: We must check for modifier keys (Ctrl, Shift, etc.) to avoid
        intercepting keyboard shortcuts like Ctrl+C, Ctrl+V, etc.
        """
        # Don't handle key events with modifiers - let them propagate for shortcuts
        if e.modifiers() not in (QtCore.Qt.KeyboardModifier.NoModifier, 
                                  QtCore.Qt.KeyboardModifier.KeypadModifier):
            super().keyPressEvent(e)
            return
            
        if e.key() in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal):
            # Zoom in
            self.scale(1.15, 1.15)
            self.zoomChanged.emit()
            self.viewport().update()
            e.accept()
            return
        if e.key() in (QtCore.Qt.Key.Key_Minus, QtCore.Qt.Key.Key_Underscore):
            # Zoom out
            self.scale(1 / 1.15, 1 / 1.15)
            self.zoomChanged.emit()
            self.viewport().update()
            e.accept()
            return
        
        # Note: Space key is handled by MainWindow action for retrace
        # Pan mode is still available via middle mouse button
        
        # Let parent handle all other keys (including shortcuts)
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QtGui.QKeyEvent):
        """Handle key release events."""
        # Note: Space key pan mode removed to avoid conflict with retrace shortcut
        super().keyReleaseEvent(e)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        """Handle middle button press for pan mode."""
        if e.button() == QtCore.Qt.MouseButton.MiddleButton:
            # Middle button → drag to pan
            # Switch to NoAnchor for better panning (AnchorUnderMouse causes issues at low zoom)
            self.setTransformationAnchor(self.ViewportAnchor.NoAnchor)
            self.setDragMode(self.DragMode.ScrollHandDrag)
            # Create fake left button event for pan mode
            fake = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseButtonPress,
                e.position(),
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.MouseButton.LeftButton,
                e.modifiers()
            )
            super().mousePressEvent(fake)
        else:
            super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        """Handle middle button release to exit pan mode."""
        if e.button() == QtCore.Qt.MouseButton.MiddleButton:
            # Create fake left button release
            fake = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseButtonRelease,
                e.position(),
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.MouseButton.NoButton,
                e.modifiers()
            )
            super().mouseReleaseEvent(fake)
            # Back to select mode
            self.setDragMode(self.DragMode.RubberBandDrag)
            # Restore anchor for zooming
            self.setTransformationAnchor(self.ViewportAnchor.AnchorUnderMouse)
        else:
            super().mouseReleaseEvent(e)


