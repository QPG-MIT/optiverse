"""
Coordinate transformation system for canvas views.

Handles conversion between:
- Millimeter coordinates (centered, Y-up, mathematical convention)
- Image pixel coordinates (centered, Y-up)
- Screen coordinates (Qt, Y-down)
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6 import QtCore


@dataclass
class CoordinateParams:
    """Parameters for coordinate transformations."""

    img_rect: QtCore.QRect  # Image rectangle in screen coordinates
    scale_fit: float  # Scale factor from image to screen
    mm_per_px: float  # Millimeters per image pixel

    @property
    def img_center_x_px(self) -> float:
        """X coordinate of image center in image pixels."""
        if self.scale_fit == 0:
            return 0.0
        return self.img_rect.width() / (2 * self.scale_fit)

    @property
    def img_center_y_px(self) -> float:
        """Y coordinate of image center in image pixels."""
        if self.scale_fit == 0:
            return 0.0
        return self.img_rect.height() / (2 * self.scale_fit)


class CanvasCoordinateSystem:
    """
    Manages coordinate transformations for the canvas.

    COORDINATE SYSTEMS:
    - Storage (mm): Origin at image center, Y-up (positive is up)
    - Image pixels: Origin at image center, Y-up
    - Screen pixels: Origin at top-left, Y-down (Qt convention)

    Transformations:
        mm → image_px: divide by mm_per_px
        image_px → screen: translate by img_rect origin, scale by scale_fit, flip Y
        screen → image_px: reverse of above
        image_px → mm: multiply by mm_per_px
    """

    def __init__(self):
        """Initialize coordinate system."""
        self._params: CoordinateParams | None = None

    def update_params(self, img_rect: QtCore.QRect, scale_fit: float, mm_per_px: float):
        """
        Update coordinate transformation parameters.

        Args:
            img_rect: Image rectangle in screen coordinates
            scale_fit: Scale factor from image to screen
            mm_per_px: Millimeters per image pixel
        """
        self._params = CoordinateParams(img_rect=img_rect, scale_fit=scale_fit, mm_per_px=mm_per_px)

    @property
    def is_valid(self) -> bool:
        """Check if coordinate system has valid parameters."""
        return (
            self._params is not None
            and self._params.img_rect.isValid()
            and self._params.scale_fit > 0
            and self._params.mm_per_px > 0
        )

    @property
    def params(self) -> CoordinateParams | None:
        """Get current coordinate parameters."""
        return self._params

    # ========== MM to Screen ==========

    def mm_to_screen(self, x_mm: float, y_mm: float) -> tuple[float, float]:
        """
        Convert millimeter coordinates to screen coordinates.

        Args:
            x_mm: X position in millimeters (centered, Y-up)
            y_mm: Y position in millimeters (centered, Y-up)

        Returns:
            (x_screen, y_screen) tuple in Qt screen coordinates
        """
        if not self.is_valid:
            return (0.0, 0.0)

        p = self._params
        if p is None:
            return (0.0, 0.0)

        # mm → image pixels
        x_img_px = x_mm / p.mm_per_px
        y_img_px = y_mm / p.mm_per_px

        # image pixels (centered, Y-up) → screen (Y-down)
        x_screen = p.img_rect.x() + (x_img_px + p.img_center_x_px) * p.scale_fit
        y_screen = p.img_rect.y() + (p.img_center_y_px - y_img_px) * p.scale_fit

        return (x_screen, y_screen)

    def mm_to_screen_point(self, x_mm: float, y_mm: float) -> QtCore.QPointF:
        """Convert mm coordinates to QPointF in screen coordinates."""
        x, y = self.mm_to_screen(x_mm, y_mm)
        return QtCore.QPointF(x, y)

    # ========== Screen to MM ==========

    def screen_to_mm(self, x_screen: float, y_screen: float) -> tuple[float, float]:
        """
        Convert screen coordinates to millimeter coordinates.

        Args:
            x_screen: X position in screen coordinates
            y_screen: Y position in screen coordinates

        Returns:
            (x_mm, y_mm) tuple in mm (centered, Y-up)
        """
        if not self.is_valid:
            return (0.0, 0.0)

        p = self._params
        if p is None:
            return (0.0, 0.0)

        # screen → image pixels (centered, Y-up)
        x_img_px = (x_screen - p.img_rect.x()) / p.scale_fit - p.img_center_x_px
        y_img_px = p.img_center_y_px - (y_screen - p.img_rect.y()) / p.scale_fit

        # image pixels → mm
        x_mm = x_img_px * p.mm_per_px
        y_mm = y_img_px * p.mm_per_px

        return (x_mm, y_mm)

    def screen_to_mm_from_point(self, pos: QtCore.QPoint) -> tuple[float, float]:
        """Convert QPoint screen position to mm coordinates."""
        return self.screen_to_mm(pos.x(), pos.y())

    # ========== Screen to Image Pixels ==========

    def screen_to_img_px(self, x_screen: float, y_screen: float) -> tuple[float, float]:
        """
        Convert screen coordinates to image pixel coordinates (centered, Y-up).

        Args:
            x_screen: X position in screen coordinates
            y_screen: Y position in screen coordinates

        Returns:
            (x_img_px, y_img_px) tuple (centered, Y-up)
        """
        if not self.is_valid:
            return (0.0, 0.0)

        p = self._params
        if p is None:
            return (0.0, 0.0)

        x_img_px = (x_screen - p.img_rect.x()) / p.scale_fit - p.img_center_x_px
        y_img_px = p.img_center_y_px - (y_screen - p.img_rect.y()) / p.scale_fit

        return (x_img_px, y_img_px)

    # ========== Screen Delta to MM Delta ==========

    def screen_delta_to_mm(self, dx_screen: float, dy_screen: float) -> tuple[float, float]:
        """
        Convert screen coordinate delta to mm delta.

        Note: Y is inverted (screen +y is down, mm +y is up)

        Args:
            dx_screen: X delta in screen coordinates
            dy_screen: Y delta in screen coordinates

        Returns:
            (dx_mm, dy_mm) tuple
        """
        if not self.is_valid:
            return (0.0, 0.0)

        p = self._params
        if p is None:
            return (0.0, 0.0)

        dx_mm = (dx_screen / p.scale_fit) * p.mm_per_px
        dy_mm = (-dy_screen / p.scale_fit) * p.mm_per_px  # Y inverted

        return (dx_mm, dy_mm)

    # ========== MM to Radius Pixels ==========

    def mm_to_screen_radius(self, radius_mm: float) -> float:
        """
        Convert a radius/distance from mm to screen pixels.

        Args:
            radius_mm: Radius in millimeters

        Returns:
            Radius in screen pixels
        """
        if not self.is_valid:
            return 0.0

        p = self._params
        if p is None:
            return 0.0
        return abs(radius_mm) / p.mm_per_px * p.scale_fit

    # ========== Clamping ==========

    def clamp_img_px(
        self, x_img_px: float, y_img_px: float, img_width: int, img_height: int
    ) -> tuple[float, float]:
        """
        Clamp image pixel coordinates to image bounds.

        Args:
            x_img_px: X in image pixels (centered)
            y_img_px: Y in image pixels (centered)
            img_width: Image width in pixels
            img_height: Image height in pixels

        Returns:
            Clamped (x_img_px, y_img_px)
        """
        max_x = img_width / 2
        max_y = img_height / 2

        x_clamped = max(-max_x, min(max_x, x_img_px))
        y_clamped = max(-max_y, min(max_y, y_img_px))

        return (x_clamped, y_clamped)

    # ========== Ruler Parameters ==========

    def get_ruler_params(self, img_width: int, img_height: int) -> dict:
        """
        Get parameters for ruler widgets.

        Args:
            img_width: Image width in pixels
            img_height: Image height in pixels

        Returns:
            Dictionary with ruler parameters
        """
        if not self.is_valid:
            return {
                "h_scale": 1.0,
                "h_offset": 0.0,
                "h_range": (-50.0, 50.0),
                "v_scale": 1.0,
                "v_offset": 0.0,
                "v_range": (-50.0, 50.0),
                "show_mm": True,
            }

        p = self._params
        if p is None:
            return {
                "scale": 1.0,
                "h_offset": 0.0,
                "v_offset": 0.0,
                "h_range": (-50.0, 50.0),
                "v_range": (-50.0, 50.0),
                "show_mm": True,
            }

        # Scale: screen pixels per mm
        scale = p.scale_fit / p.mm_per_px

        # Offset: where 0mm appears on screen (center of image)
        h_offset = p.img_rect.x() + p.img_rect.width() / 2
        v_offset = p.img_rect.y() + p.img_rect.height() / 2

        # Range: visible range in mm
        half_width_mm = (img_width / 2) * p.mm_per_px
        half_height_mm = (img_height / 2) * p.mm_per_px

        return {
            "h_scale": scale,
            "h_offset": h_offset,
            "h_range": (-half_width_mm, half_width_mm),
            "v_scale": scale,
            "v_offset": v_offset,
            "v_range": (-half_height_mm, half_height_mm),
            "show_mm": True,
        }
