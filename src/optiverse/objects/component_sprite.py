from __future__ import annotations

import math
import os

from PyQt6 import QtCore, QtGui, QtWidgets


class ComponentSprite(QtWidgets.QGraphicsPixmapItem):
    """
    Image underlay for an optical element.
    
    COORDINATE SYSTEM:
    - object_height_mm represents the physical size of the FULL IMAGE HEIGHT
    - mm_per_pixel is computed as: object_height_mm / actual_image_height
    - reference_line_mm is in mm coordinates (centered, Y-down): (x1, y1, x2, y2)
    - The reference line defines the OPTICAL AXIS (position and orientation)
    - Reference line's midpoint is aligned to the parent's local origin using setOffset
    - Pre-rotated so reference line lies on +X in local coords
    """

    def __init__(
        self,
        image_path: str,
        reference_line_mm: tuple[float, float, float, float],
        object_height_mm: float,
        parent_item: QtWidgets.QGraphicsItem,
    ):
        """
        Initialize component sprite.
        
        Args:
            image_path: Path to image file
            reference_line_mm: Reference line in mm coordinates (x1, y1, x2, y2)
                              Centered at image center (0,0), Y-down
            object_height_mm: Physical height of full image in mm
            parent_item: Parent graphics item
        """
        super().__init__(parent_item)
        
        # Store the actual reference line length in mm (for parent to use)
        self.picked_line_length_mm = 0.0
        
        if not (image_path and os.path.exists(image_path)):
            self.setVisible(False)
            return

        # Load pixmap and ensure device pixel ratio = 1.0
        pix0 = QtGui.QPixmap(image_path)
        img = pix0.toImage()
        img.setDevicePixelRatio(1.0)
        pix = QtGui.QPixmap.fromImage(img)
        self.setPixmap(pix)
        
        actual_width = pix.width()
        actual_height = pix.height()
        if actual_height <= 0:
            self.setVisible(False)
            return
        
        # Compute mm_per_pixel from object_height_mm
        # Scale image so that the FULL IMAGE HEIGHT is exactly object_height_mm
        mm_per_pixel = object_height_mm / actual_height
        
        # Convert reference line from mm (centered, Y-down) to image pixels (top-left origin, Y-down)
        x1_mm, y1_mm, x2_mm, y2_mm = reference_line_mm
        
        # Convert from centered mm to pixel coordinates
        # Pixel coords: (0,0) at top-left
        # mm coords: (0,0) at center
        image_center_x_px = actual_width / 2.0
        image_center_y_px = actual_height / 2.0
        
        x1_px = (x1_mm / mm_per_pixel) + image_center_x_px
        y1_px = (y1_mm / mm_per_pixel) + image_center_y_px
        x2_px = (x2_mm / mm_per_pixel) + image_center_x_px
        y2_px = (y2_mm / mm_per_pixel) + image_center_y_px
        
        # Extract line vector for alignment
        dx_px = x2_px - x1_px
        dy_px = y2_px - y1_px
        
        # Calculate the actual length of the reference line in mm
        dx_mm = x2_mm - x1_mm
        dy_mm = y2_mm - y1_mm
        self.picked_line_length_mm = math.hypot(dx_mm, dy_mm)

        # Center point of reference line (in pixel coordinates)
        cx_px = 0.5 * (x1_px + x2_px)
        cy_px = 0.5 * (y1_px + y2_px)

        # Offset pixmap so line center aligns with parent's origin
        self.setOffset(-cx_px, -cy_px)

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

