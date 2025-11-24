"""Ray path rendering for the UI.

This module handles the visual rendering of traced ray paths to the scene,
using either OpenGL hardware acceleration or software fallback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from PyQt6 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from ..raytracing import RayPath
    from ..objects import GraphicsView


class RayRenderer:
    """
    Renderer for ray paths in the graphics scene.
    
    Handles both hardware-accelerated OpenGL rendering and software fallback
    using QGraphicsPathItem.
    """
    
    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        view: "GraphicsView",
    ):
        """
        Initialize the ray renderer.
        
        Args:
            scene: The graphics scene to render rays into
            view: The graphics view (for OpenGL overlay access)
        """
        self.scene = scene
        self.view = view
        
        # Track rendered ray items for software rendering
        self.ray_items: List[QtWidgets.QGraphicsPathItem] = []
        
        # Ray width in pixels
        self._ray_width_px: float = 2.0
    
    @property
    def ray_width_px(self) -> float:
        """Get the ray width in pixels."""
        return self._ray_width_px
    
    @ray_width_px.setter
    def ray_width_px(self, value: float):
        """Set the ray width in pixels."""
        self._ray_width_px = float(value)
    
    def clear(self) -> None:
        """Remove all ray graphics from scene."""
        # Clear OpenGL overlay if available
        if self.view.has_ray_overlay():
            self.view.clear_ray_overlay()
        
        # Clear software-rendered rays
        for it in self.ray_items:
            try:
                # Check if item is still in scene before removing
                if it.scene() is not None:
                    self.scene.removeItem(it)
            except RuntimeError:
                # Item was already deleted (e.g., during scene clear)
                pass
        self.ray_items.clear()
    
    def render(self, paths: List["RayPath"]) -> None:
        """
        Render ray paths to the scene.
        
        Uses OpenGL hardware acceleration if available, otherwise falls back
        to software rendering with QGraphicsPathItem.
        
        Args:
            paths: List of RayPath objects to render
        """
        # Try OpenGL rendering first (100x+ faster)
        if self.view.has_ray_overlay():
            # Use hardware-accelerated OpenGL rendering
            self.view.update_ray_overlay(paths, self._ray_width_px)
            # No need to create QGraphicsPathItem objects
            self._update_path_measures(paths)
            return
        
        # Fallback to software rendering if OpenGL not available
        self._render_software(paths)
        self._update_path_measures(paths)
    
    def _render_software(self, paths: List["RayPath"]) -> None:
        """
        Software fallback rendering using QGraphicsPathItem.
        
        Args:
            paths: List of RayPath objects to render
        """
        # Constants for rendering adjustments
        SATURATION_BOOST_FACTOR = 1.3
        VALUE_BOOST_FACTOR = 1.2
        HSV_MAX = 255
        RAY_WIDTH_OPENGL_SCALE = 2.0
        
        for p in paths:
            if len(p.points) < 2:
                continue
            
            # Build QPainterPath from points
            path = QtGui.QPainterPath(QtCore.QPointF(p.points[0][0], p.points[0][1]))
            for q in p.points[1:]:
                path.lineTo(q[0], q[1])
            
            item = QtWidgets.QGraphicsPathItem(path)
            r, g, b, a = p.rgba
            
            # Boost saturation and brightness for OpenGL viewport (colors appear darker in OpenGL)
            # Convert to HSV, increase saturation and value significantly, convert back
            color = QtGui.QColor(r, g, b, a)
            h, s, v, alpha = color.getHsv()
            
            # Only boost HSV if OpenGL is used
            if self.view.has_ray_overlay():
                s = min(HSV_MAX, int(s * SATURATION_BOOST_FACTOR))
                v = min(HSV_MAX, int(v * VALUE_BOOST_FACTOR))
                color.setHsv(h, s, v, alpha)
            
            pen = QtGui.QPen(color)
            # OpenGL viewport makes lines appear thinner, so increase width
            # Use a scale factor to compensate (RAY_WIDTH_OPENGL_SCALE)
            pen.setWidthF(self._ray_width_px * RAY_WIDTH_OPENGL_SCALE)
            pen.setCosmetic(True)
            item.setPen(pen)
            item.setZValue(10)
            
            self.scene.addItem(item)
            self.ray_items.append(item)
    
    def _update_path_measures(self, paths: List["RayPath"]) -> None:
        """
        Update any PathMeasureItem objects after retrace.
        
        Args:
            paths: List of RayPath objects
        """
        from optiverse.objects.annotations.path_measure_item import PathMeasureItem
        
        for item in self.scene.items():
            if isinstance(item, PathMeasureItem):
                ray_index = item.get_ray_index()
                if 0 <= ray_index < len(paths):
                    item.update_path(paths[ray_index].points)

