from __future__ import annotations

from typing import Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets


class ImageCanvas(QtWidgets.QLabel):
    clickedPoint = QtCore.pyqtSignal(float, float)
    imageDropped = QtCore.pyqtSignal(QtGui.QPixmap, str)

    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self._pix: Optional[QtGui.QPixmap] = None
        self._scale_fit = 1.0
        self._pt1: Optional[Tuple[float, float]] = None
        self._pt2: Optional[Tuple[float, float]] = None
        self._src_path: Optional[str] = None
        self.setAcceptDrops(True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def set_pixmap(self, pix: QtGui.QPixmap, source_path: str | None = None):
        self._pix = pix
        self._src_path = source_path
        self._pt1 = None
        self._pt2 = None
        self.update()

    def source_path(self) -> Optional[str]:
        return self._src_path

    def current_pixmap(self) -> Optional[QtGui.QPixmap]:
        return self._pix

    def has_image(self) -> bool:
        return self._pix is not None and not self._pix.isNull()

    def get_points(self):
        return self._pt1, self._pt2

    def set_points(self, p1: Optional[Tuple[float, float]], p2: Optional[Tuple[float, float]]):
        self._pt1 = p1
        self._pt2 = p2
        self.update()

    def clear_points(self):
        self._pt1 = None
        self._pt2 = None
        self.update()

    def image_pixel_size(self) -> Tuple[int, int]:
        if not self._pix:
            return (0, 0)
        return (self._pix.width(), self._pix.height())

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if not self._pix:
            return
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            pos = e.pos()
            pixrect = self._target_rect()
            if not pixrect.contains(pos):
                return
            x = (pos.x() - pixrect.x())
            y = (pos.y() - pixrect.y())
            px = x / self._scale_fit
            py = y / self._scale_fit
            if self._pt1 is None:
                self._pt1 = (px, py)
            else:
                self._pt2 = (px, py)
            self.clickedPoint.emit(px, py)
            self.update()
        elif e.button() == QtCore.Qt.MouseButton.RightButton:
            self.clear_points()

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        md = e.mimeData()
        if md.hasImage() or md.hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QtGui.QDropEvent):
        md = e.mimeData()
        if md.hasImage():
            img = md.imageData()
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
        if md.hasUrls():
            for url in md.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    low = path.lower()
                    if low.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
                        pix = QtGui.QPixmap(path)
                        if not pix.isNull():
                            self.imageDropped.emit(pix, path)
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
            p.drawPixmap(tgt, self._pix)
            if self._pt1:
                x1, y1 = self._pt1
                X1 = tgt.x() + x1 * self._scale_fit
                Y1 = tgt.y() + y1 * self._scale_fit
                pen = QtGui.QPen(QtGui.QColor(0, 180, 255), 2)
                p.setPen(pen)
                p.setBrush(QtGui.QBrush(QtGui.QColor(0, 180, 255, 100)))
                p.drawEllipse(QtCore.QPointF(X1, Y1), 4, 4)
            if self._pt2:
                x2, y2 = self._pt2
                X2 = tgt.x() + x2 * self._scale_fit
                Y2 = tgt.y() + y2 * self._scale_fit
                pen = QtGui.QPen(QtGui.QColor(255, 80, 0), 2)
                p.setPen(pen)
                p.setBrush(QtGui.QBrush(QtGui.QColor(255, 80, 0, 100)))
                p.drawEllipse(QtCore.QPointF(X2, Y2), 4, 4)
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


