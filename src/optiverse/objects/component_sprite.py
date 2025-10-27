from __future__ import annotations

import math
import os

from PyQt6 import QtCore, QtGui, QtWidgets


class ComponentSprite(QtWidgets.QGraphicsPixmapItem):
    """
    Image underlay for an optical element.
    
    NORMALIZED 1000px SYSTEM:
    - Images are normalized to 1000px height
    - line_px coordinates are in normalized 1000px space
    - object_height_mm represents the physical size of the full 1000px height
    - mm_per_pixel is computed as: object_height_mm / 1000.0
    - Picked line's midpoint is aligned to the parent's local origin using setOffset
    - Pre-rotated so picked line lies on +X in local coords
    """

    def __init__(
        self,
        image_path: str,
        line_px: tuple[float, float, float, float],
        object_height_mm: float,
        parent_item: QtWidgets.QGraphicsItem,
    ):
        super().__init__(parent_item)
        
        # Compute mm_per_pixel from object_height_mm (normalized 1000px system)
        # object_height_mm represents the physical size corresponding to the full 1000px normalized image height
        mm_per_pixel = object_height_mm / 1000.0
        
        # Extract line endpoints for alignment
        x1, y1, x2, y2 = line_px
        dx, dy = (x2 - x1), (y2 - y1)

        if not (image_path and os.path.exists(image_path)):
            self.setVisible(False)
            return

        # Load pixmap and ensure device pixel ratio = 1.0
        pix0 = QtGui.QPixmap(image_path)
        img = pix0.toImage()
        img.setDevicePixelRatio(1.0)
        pix = QtGui.QPixmap.fromImage(img)
        self.setPixmap(pix)

        # Calculate angle of picked line
        angle_img_deg = math.degrees(math.atan2(dy, dx))

        # Center point of picked line
        cx = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)

        # Offset pixmap so line center aligns with parent's origin
        self.setOffset(-cx, -cy)

        # Rotate to align picked line with +X axis in parent coords
        self.setRotation(-angle_img_deg)

        # Scale uniformly from pixels to mm
        s_px_to_mm = float(mm_per_pixel) if mm_per_pixel > 0 else 1.0
        self.setScale(s_px_to_mm)

        # Render below the element geometry
        self.setZValue(-100)
        self.setOpacity(0.95)
        self.setTransformationMode(QtCore.Qt.TransformationMode.SmoothTransformation)
        # Don't use caching because paint() depends on parent selection state
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)

    def paint(self, p: QtGui.QPainter, opt, widget=None):
        """
        Paint sprite with selection feedback.
        
        Phase 2.1: When parent item is selected, draw a translucent blue overlay
        to provide clear visual feedback.
        """
        # Draw the pixmap
        super().paint(p, opt, widget)

        # Add blue tint if parent is selected
        par = self.parentItem()
        if par is not None and par.isSelected():
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(30, 144, 255, 70))  # Translucent blue
            p.drawRect(self.boundingRect())

