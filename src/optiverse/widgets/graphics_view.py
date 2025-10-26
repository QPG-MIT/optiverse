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

    # ----- drag & drop (images and components) -----
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        md = e.mimeData()
        if md.hasFormat("application/x-optics-component") or md.hasImage() or md.hasUrls():
            e.acceptProposedAction()
    
    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        md = e.mimeData()
        if md.hasFormat("application/x-optics-component") or md.hasImage() or md.hasUrls():
            e.acceptProposedAction()

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


