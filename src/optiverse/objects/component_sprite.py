from __future__ import annotations

import hashlib
import logging
import math
import os
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtSvgWidgets import QGraphicsSvgItem

# Optional QtSvg for SVG support
try:
    from PyQt6 import QtSvg

    HAVE_QTSVG = True
except ImportError:
    HAVE_QTSVG = False

# Import cache directory function
try:
    from ..platform.paths import svg_cache_dir

    HAVE_CACHE = True
except Exception as e:
    HAVE_CACHE = False
    logging.warning(f"SVG caching disabled due to import error: {e}")


class ComponentSvgSprite(QGraphicsSvgItem):
    """
    Native SVG image underlay for an optical element.

    COORDINATE SYSTEM:
    - object_height_mm represents the physical size of the FULL IMAGE HEIGHT
    - mm_per_pixel is computed as: object_height_mm / actual_image_height
    - reference_line_mm is in mm coordinates (centered, Y-up): (x1, y1, x2, y2)
    - SVG is flipped in Y to convert from native Y-down to scene Y-up coordinates
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
        Initialize component SVG sprite.

        Args:
            image_path: Path to SVG file
            reference_line_mm: Reference line in mm coordinates (x1, y1, x2, y2)
                              Centered at image center (0,0), Y-up convention
                              (positive Y = up, negative Y = down)
            object_height_mm: Physical height of full image in mm
            parent_item: Parent graphics item
        """
        super().__init__(parent_item)

        # Store the actual reference line length in mm (for parent to use)
        self.picked_line_length_mm = 0.0

        if not (image_path and os.path.exists(image_path)):
            self.setVisible(False)
            return

        # Load SVG renderer
        renderer = QtSvg.QSvgRenderer(image_path)
        if not renderer.isValid():
            self.setVisible(False)
            return

        self.setSharedRenderer(renderer)

        # Get SVG's default size
        default_size = renderer.defaultSize()
        if default_size.height() <= 0:
            self.setVisible(False)
            return

        actual_width = default_size.width()
        actual_height = default_size.height()

        # Compute mm_per_pixel from object_height_mm
        # Scale image so that the FULL IMAGE HEIGHT is exactly object_height_mm
        mm_per_pixel = object_height_mm / actual_height

        # Convert reference line from mm (centered, Y-up) to image pixels (top-left origin, Y-up)
        x1_mm, y1_mm, x2_mm, y2_mm = reference_line_mm

        # Convert from centered mm to pixel coordinates
        # Storage: Y-up (positive = up, negative = down)
        # SVG: Y-down (native image format)
        # We negate Y when mapping mm to pixels, then flip the entire sprite to Y-up
        # Pixel coords: (0,0) at top-left
        # mm coords: (0,0) at center
        image_center_x_px = actual_width / 2.0
        image_center_y_px = actual_height / 2.0

        # Convert mm to pixels - negate Y to map Y-up mm to Y-down pixels
        x1_px = (x1_mm / mm_per_pixel) + image_center_x_px
        y1_px = (-y1_mm / mm_per_pixel) + image_center_y_px  # Negate Y
        x2_px = (x2_mm / mm_per_pixel) + image_center_x_px
        y2_px = (-y2_mm / mm_per_pixel) + image_center_y_px  # Negate Y

        # Calculate the actual length of the reference line in mm
        dx_mm = x2_mm - x1_mm
        dy_mm = y2_mm - y1_mm
        self.picked_line_length_mm = math.hypot(dx_mm, dy_mm)

        # Center point of reference line (in pixel coordinates)
        cx_px = 0.5 * (x1_px + x2_px)
        cy_px = 0.5 * (y1_px + y2_px)

        # Offset SVG so line center aligns with parent's origin
        self.setPos(-cx_px, -cy_px)

        # Scale uniformly from pixels to mm
        s_px_to_mm = float(mm_per_pixel) if mm_per_pixel > 0 else 1.0
        self.setScale(s_px_to_mm)

        # Flip sprite in Y to convert SVG from native Y-down to scene Y-up
        transform = self.transform()
        transform.scale(1.0, -1.0)
        self.setTransform(transform)

        # Render below the element geometry
        self.setZValue(-100)
        self.setOpacity(0.95)
        # Use device coordinate cache for better performance
        # Cache is invalidated when selection state changes
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.DeviceCoordinateCache)

        # Track parent selection state for cache invalidation
        self._parent_was_selected = False

    def paint(self, p: QtGui.QPainter, opt, widget=None):
        """
        Paint sprite with selection feedback.

        When parent item is selected, draw a translucent blue overlay
        to provide clear visual feedback.
        """
        # Check if parent selection state changed
        par = self.parentItem()
        is_selected = par is not None and par.isSelected()

        # Invalidate cache if selection state changed
        if is_selected != self._parent_was_selected:
            self._parent_was_selected = is_selected
            self.update()  # Force cache refresh

        # Draw the SVG
        super().paint(p, opt, widget)

        # Add blue tint if parent is selected
        if is_selected:
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(30, 144, 255, 70))  # Translucent blue
            p.drawRect(self.boundingRect())


class ComponentSprite(QtWidgets.QGraphicsPixmapItem):
    """
    Image underlay for an optical element.

    COORDINATE SYSTEM:
    - object_height_mm represents the physical size of the FULL IMAGE HEIGHT
    - mm_per_pixel is computed as: object_height_mm / actual_image_height
    - reference_line_mm is in mm coordinates (centered, Y-up): (x1, y1, x2, y2)
    - Pixmap is flipped in Y to convert from native Y-down to scene Y-up coordinates
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
                              Centered at image center (0,0), Y-up convention
                              (positive Y = up, negative Y = down)
            object_height_mm: Physical height of full image in mm
            parent_item: Parent graphics item
        """
        super().__init__(parent_item)

        # Store the actual reference line length in mm (for parent to use)
        self.picked_line_length_mm = 0.0

        if not (image_path and os.path.exists(image_path)):
            self.setVisible(False)
            return

        # Load pixmap - handle SVG or raster images
        if image_path.lower().endswith(".svg") and HAVE_QTSVG:
            # Render SVG to high-resolution pixmap once
            # High resolution ensures sharpness at all zoom levels
            pix = self._render_svg_to_pixmap(image_path, object_height_mm)
            if not pix or pix.isNull():
                self.setVisible(False)
                return
        else:
            # Load raster image and ensure device pixel ratio = 1.0
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

        # Convert reference line from mm (centered, Y-up) to image pixels (top-left origin, Y-up)
        x1_mm, y1_mm, x2_mm, y2_mm = reference_line_mm

        # Convert from centered mm to pixel coordinates
        # Storage: Y-up (positive = up, negative = down)
        # Pixmap: Y-down (native image format)
        # We negate Y when mapping mm to pixels, then flip the entire sprite to Y-up
        # Pixel coords: (0,0) at top-left
        # mm coords: (0,0) at center
        image_center_x_px = actual_width / 2.0
        image_center_y_px = actual_height / 2.0

        # Convert mm to pixels - negate Y to map Y-up mm to Y-down pixels
        x1_px = (x1_mm / mm_per_pixel) + image_center_x_px
        y1_px = (-y1_mm / mm_per_pixel) + image_center_y_px  # Negate Y
        x2_px = (x2_mm / mm_per_pixel) + image_center_x_px
        y2_px = (-y2_mm / mm_per_pixel) + image_center_y_px  # Negate Y

        # Extract line vector for alignment
        x2_px - x1_px
        y2_px - y1_px

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

        # Flip sprite in Y to convert pixmap from native Y-down to scene Y-up
        transform = self.transform()
        transform.scale(1.0, -1.0)
        self.setTransform(transform)

        # Render below the element geometry
        self.setZValue(-100)
        self.setOpacity(0.95)
        self.setTransformationMode(QtCore.Qt.TransformationMode.SmoothTransformation)
        # Use device coordinate cache for better performance
        # Cache is invalidated when selection state changes
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.DeviceCoordinateCache)

        # Track parent selection state for cache invalidation
        self._parent_was_selected = False

    def paint(self, p: QtGui.QPainter, opt, widget=None):
        """
        Paint sprite with selection feedback.

        When parent item is selected, draw a translucent blue overlay
        to provide clear visual feedback.
        """
        # Check if parent selection state changed
        par = self.parentItem()
        is_selected = par is not None and par.isSelected()

        # Invalidate cache if selection state changed
        if is_selected != self._parent_was_selected:
            self._parent_was_selected = is_selected
            self.update()  # Force cache refresh

        # Draw the pixmap
        super().paint(p, opt, widget)

        # Add blue tint if parent is selected
        if is_selected:
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(30, 144, 255, 70))  # Translucent blue
            p.drawRect(self.boundingRect())

    @staticmethod
    def _render_svg_to_pixmap(svg_path: str, object_height_mm: float) -> QtGui.QPixmap | None:
        """
        Render SVG to high-resolution pixmap with caching.

        Renders at high resolution (4000-8000px) to ensure sharpness at all zoom levels.
        Qt's image allocation limit is increased to 1GB to support large PNG cache files.
        Qt's GPU-accelerated smooth transformation handles scaling efficiently.

        Uses disk cache (PNG format - lossless) to avoid re-rendering the same SVG.
        Shows busy cursor during rendering. Cache persists between app sessions.

        Args:
            svg_path: Path to SVG file
            object_height_mm: Physical height of object in mm (used to calculate target pixel size)

        Returns:
            QPixmap with rendered SVG, or None if rendering fails
        """
        if not HAVE_QTSVG:
            return None

        # Calculate target resolution based on physical size
        # Larger objects need higher resolution for zoom detail
        # Use ~100 pixels per mm as a base (0.01mm per pixel at 1:1 zoom)
        # Clamp between 4000px (small) and 8000px (large) to stay under Qt's 256MB limit
        # 8000x8000 RGBA = 256MB uncompressed, so 8000px is the safe maximum
        target_height = max(4000, min(8000, int(object_height_mm * 100)))

        logging.debug(
            f"Rendering SVG: {Path(svg_path).name} at {target_height}px (HAVE_CACHE={HAVE_CACHE})"
        )

        # Try to load from cache first
        cached_pix = ComponentSprite._load_from_cache(svg_path, target_height)
        if cached_pix and not cached_pix.isNull():
            return cached_pix

        # Cache miss - show loading indicator and render
        logging.debug("Rendering SVG from scratch...")
        app = QtWidgets.QApplication.instance()
        if app:
            app.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)

        try:
            renderer = QtSvg.QSvgRenderer(svg_path)
            if not renderer.isValid():
                return None

            # Get SVG's default size and aspect ratio
            default_size = renderer.defaultSize()
            if default_size.height() <= 0:
                return None

            aspect = default_size.width() / default_size.height()

            # Calculate width maintaining aspect ratio
            target_width = int(target_height * aspect)
            target_size = QtCore.QSize(target_width, target_height)

            # Create pixmap and render SVG
            pix = QtGui.QPixmap(target_size)
            pix.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QtGui.QPainter(pix)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
            renderer.render(painter)
            painter.end()

            # Save to cache for future use
            ComponentSprite._save_to_cache(svg_path, target_height, pix)

            return pix

        finally:
            # Always restore cursor
            if app:
                app.restoreOverrideCursor()

    @staticmethod
    def _get_cache_key(svg_path: str, target_height: int) -> str:
        """
        Generate cache key for an SVG rendering.

        Args:
            svg_path: Path to SVG file
            target_height: Target render height in pixels

        Returns:
            Cache key (hash string)
        """
        # Include file modification time to invalidate cache when SVG changes
        try:
            mtime = os.path.getmtime(svg_path)
        except OSError:
            mtime = 0

        # Create hash from path, height, and modification time
        key_str = f"{svg_path}:{target_height}:{mtime}"
        hash_obj = hashlib.sha256(key_str.encode("utf-8"))
        return hash_obj.hexdigest()[:16]  # Use first 16 chars for shorter filename

    @staticmethod
    def _load_from_cache(svg_path: str, target_height: int) -> QtGui.QPixmap | None:
        """
        Load rendered SVG from cache.

        Args:
            svg_path: Path to SVG file
            target_height: Target render height in pixels

        Returns:
            Cached pixmap if found, None otherwise
        """
        if not HAVE_CACHE:
            return None

        try:
            cache_dir = svg_cache_dir()
            cache_key = ComponentSprite._get_cache_key(svg_path, target_height)
            cache_file = Path(cache_dir) / f"{cache_key}.png"  # Use PNG for lossless quality

            if cache_file.exists():
                pix = QtGui.QPixmap(str(cache_file))
                if not pix.isNull():
                    file_size_mb = cache_file.stat().st_size / (1024 * 1024)
                    logging.debug(
                        f"SVG cache hit: {cache_file.name} ({pix.width()}x{pix.height()}, {file_size_mb:.1f}MB)"
                    )
                    return pix
                else:
                    logging.warning(
                        f"SVG cache file corrupted or exceeds Qt limit: {cache_file.name}"
                    )
                    # Delete corrupted file
                    try:
                        cache_file.unlink()
                    except OSError:
                        pass  # File may be locked or already deleted
            else:
                logging.debug(f"SVG cache miss: {cache_key}.png not found in {cache_dir}")
        except OSError as e:
            logging.error(f"Error loading from SVG cache: {e}")

        return None

    @staticmethod
    def _save_to_cache(svg_path: str, target_height: int, pixmap: QtGui.QPixmap) -> None:
        """
        Save rendered SVG to cache.

        Args:
            svg_path: Path to SVG file
            target_height: Target render height in pixels
            pixmap: Rendered pixmap to cache
        """
        if not HAVE_CACHE:
            logging.debug("SVG caching disabled (HAVE_CACHE=False)")
            return

        if pixmap.isNull():
            logging.warning("Cannot save null pixmap to cache")
            return

        try:
            cache_dir = svg_cache_dir()
            cache_key = ComponentSprite._get_cache_key(svg_path, target_height)
            cache_file = Path(cache_dir) / f"{cache_key}.png"

            # Save as PNG for lossless quality
            # Qt's image allocation limit has been increased to 1GB to support large cached files
            # PNG provides perfect quality for technical drawings
            success = pixmap.save(str(cache_file), "PNG")
            if success:
                file_size_mb = cache_file.stat().st_size / (1024 * 1024)
                logging.debug(
                    f"SVG cached successfully: {cache_file.name} ({pixmap.width()}x{pixmap.height()}, {file_size_mb:.1f}MB)"
                )
            else:
                logging.error(f"Failed to save SVG cache file: {cache_file}")
        except OSError as e:
            logging.error(f"Error saving to SVG cache: {e}")


def create_component_sprite(
    image_path: str,
    reference_line_mm: tuple[float, float, float, float],
    object_height_mm: float,
    parent_item: QtWidgets.QGraphicsItem,
) -> ComponentSprite | ComponentSvgSprite:
    """
    Factory function to create appropriate sprite based on image type.

    Always creates ComponentSprite which pre-renders SVG to pixmap for better
    zoom performance. ComponentSvgSprite (native vector rendering) is disabled
    because it re-renders on every zoom level change, causing poor performance.

    Args:
        image_path: Path to image file
        reference_line_mm: Reference line in mm coordinates (x1, y1, x2, y2)
        object_height_mm: Physical height of full image in mm
        parent_item: Parent graphics item

    Returns:
        ComponentSprite for all image types (SVG pre-rendered to pixmap)
    """
    # Always use ComponentSprite - it pre-renders SVG to high-res pixmap
    # This gives excellent performance when zooming (pixmap scaling is fast)
    # Native vector rendering (ComponentSvgSprite) re-renders on every zoom = slow
    return ComponentSprite(image_path, reference_line_mm, object_height_mm, parent_item)
