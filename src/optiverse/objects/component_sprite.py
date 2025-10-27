from __future__ import annotations

import math
import os

from PyQt6 import QtCore, QtGui, QtWidgets


class ComponentSprite(QtWidgets.QGraphicsPixmapItem):
    """
    Image underlay for an optical element.
    
    NORMALIZED 1000px SYSTEM:
    - Images are normalized to 1000px height coordinate space
    - line_px coordinates are in normalized 1000px space
    - object_height_mm represents the physical size of the FULL IMAGE HEIGHT
    - mm_per_pixel is computed as: object_height_mm / actual_image_height
    - The picked line defines the OPTICAL AXIS only (position and orientation)
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
        
        if not (image_path and os.path.exists(image_path)):
            self.setVisible(False)
            return

        # Load pixmap and ensure device pixel ratio = 1.0
        pix0 = QtGui.QPixmap(image_path)
        img = pix0.toImage()
        img.setDevicePixelRatio(1.0)
        pix = QtGui.QPixmap.fromImage(img)
        self.setPixmap(pix)
        
        # CRITICAL: line_px coordinates are in normalized 1000px space
        # We need to denormalize them to the actual image size
        actual_height = pix.height()
        if actual_height <= 0:
            self.setVisible(False)
            return
        
        # Denormalize line_px from 1000px space to actual image space
        scale = float(actual_height) / 1000.0
        x1_actual = line_px[0] * scale
        y1_actual = line_px[1] * scale
        x2_actual = line_px[2] * scale
        y2_actual = line_px[3] * scale
        
        # Extract line endpoints for alignment (now in actual image coordinates)
        dx = x2_actual - x1_actual
        dy = y2_actual - y1_actual
        
        # Compute mm_per_pixel from object_height_mm
        # Scale image so that the FULL IMAGE HEIGHT is exactly object_height_mm
        # The picked line is ONLY used for optical axis (position and angle), NOT for scaling
        mm_per_pixel = object_height_mm / actual_height

        # Calculate angle of picked line (defines optical axis orientation)
        angle_img_deg = math.degrees(math.atan2(dy, dx))

        # Center point of picked line (in actual image coordinates)
        cx = 0.5 * (x1_actual + x2_actual)
        cy = 0.5 * (y1_actual + y2_actual)

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

