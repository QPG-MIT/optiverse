from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets


class GraphicsView(QtWidgets.QGraphicsView):
    zoomChanged = QtCore.pyqtSignal()

    def __init__(self, scene: QtWidgets.QGraphicsScene | None = None):
        super().__init__(scene)
        self.setRenderHints(
            QtGui.QPainter.RenderHint.Antialiasing | QtGui.QPainter.RenderHint.TextAntialiasing
        )
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
        self.setAcceptDrops(True)

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

    def wheelEvent(self, e: QtGui.QWheelEvent):
        delta_y = e.angleDelta().y()
        factor = 1.15 if delta_y > 0 else 1 / 1.15
        self.scale(factor, factor)
        e.accept()
        self.zoomChanged.emit()
        self.viewport().update()

    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        self.zoomChanged.emit()
        self.viewport().update()

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
        from ...core.models import BeamsplitterParams, LensParams, MirrorParams
        from ..beamsplitter_item import BeamsplitterItem
        from ..lens_item import LensItem
        from ..mirror_item import MirrorItem

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
            elif kind == "mirror":
                angle = 0.0
            else:
                angle = 0.0

        # Extract common parameters
        name = rec.get("name")
        img = rec.get("image_path")
        mm_per_px = float(rec.get("mm_per_pixel", 0.1))
        line_px = tuple(rec.get("line_px", (0, 0, 1, 0)))
        length_mm = float(rec.get("length_mm", 60.0))

        # Create the appropriate item type
        if kind == "lens":
            efl_mm = float(rec.get("efl_mm", 100.0))
            params = LensParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle,
                efl_mm=efl_mm,
                length_mm=length_mm,
                image_path=img,
                mm_per_pixel=mm_per_px,
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
                length_mm=length_mm,
                split_T=T,
                split_R=R,
                image_path=img,
                mm_per_pixel=mm_per_px,
                line_px=line_px,
                name=name
            )
            item = BeamsplitterItem(params)
        else:  # mirror (default)
            params = MirrorParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle,
                length_mm=length_mm,
                image_path=img,
                mm_per_pixel=mm_per_px,
                line_px=line_px,
                name=name
            )
            item = MirrorItem(params)

        # Make it a non-interactive "ghost"
        item.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        item.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        item.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        item.setOpacity(0.7)  # Semi-transparent
        item.setZValue(9999)  # Render on top

        # Ensure the decorative sprite is visible on the ghost
        try:
            item._maybe_attach_sprite()
        except Exception:
            pass

        # Add to scene
        self.scene().addItem(item)
        self._ghost_item = item
        self._ghost_rec = dict(rec)  # Keep a copy for later use

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
            except Exception:
                pass
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
            except Exception:
                pass
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
        """Handle key press for pan mode (Space key)."""
        if e.key() in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal):
            # Zoom in
            self.scale(1.15, 1.15)
            self.zoomChanged.emit()
            self.viewport().update()
            return
        if e.key() in (QtCore.Qt.Key.Key_Minus, QtCore.Qt.Key.Key_Underscore):
            # Zoom out
            self.scale(1 / 1.15, 1 / 1.15)
            self.zoomChanged.emit()
            self.viewport().update()
            return
        if e.key() == QtCore.Qt.Key.Key_Space:
            # Hold space → drag to pan
            self._hand = True
            self.setDragMode(self.DragMode.ScrollHandDrag)
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QtGui.QKeyEvent):
        """Handle key release to exit pan mode."""
        if e.key() == QtCore.Qt.Key.Key_Space and self._hand:
            # Release space → back to select mode
            self._hand = False
            self.setDragMode(self.DragMode.RubberBandDrag)
            return
        super().keyReleaseEvent(e)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        """Handle middle button press for pan mode."""
        if e.button() == QtCore.Qt.MouseButton.MiddleButton:
            # Middle button → drag to pan
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
        else:
            super().mouseReleaseEvent(e)


