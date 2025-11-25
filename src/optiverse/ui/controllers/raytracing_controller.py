"""
Raytracing Controller - Manages ray tracing operations.

Encapsulates all raytracing logic including:
- Ray tracing execution
- Debouncing for performance
- Ray data management
- Ray rendering coordination
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from PyQt6 import QtCore

from ...services.error_handler import ErrorContext
from ...core.log_categories import LogCategory
from ...core.constants import MAX_RAYTRACING_EVENTS

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QGraphicsScene
    from ...services.log_service import LogService
    from .ray_renderer import RayRenderer


class RaytracingController(QtCore.QObject):
    """
    Controller for raytracing operations.

    Handles:
    - Ray tracing through optical elements
    - Debounced retrace scheduling
    - Ray data storage for tools (inspect, path measure)
    - Ray rendering coordination

    Signals:
        rays_changed: Emitted when ray data is updated (after retrace)
    """

    rays_changed = QtCore.pyqtSignal()

    def __init__(
        self,
        scene: "QGraphicsScene",
        ray_renderer: "RayRenderer",
        log_service: "LogService",
        parent: Optional[QtCore.QObject] = None,
    ):
        """
        Initialize the raytracing controller.

        Args:
            scene: The graphics scene containing optical elements
            ray_renderer: The renderer for drawing rays
            log_service: Service for logging messages
            parent: Optional parent QObject
        """
        super().__init__(parent)

        self._scene = scene
        self._ray_renderer = ray_renderer
        self._log_service = log_service

        # State
        self._ray_data: list = []
        self._ray_width_px: float = 2.0
        self._autotrace: bool = True

        # Debouncing for autotrace
        self._retrace_pending = False
        self._retrace_timer = QtCore.QTimer()
        self._retrace_timer.setSingleShot(True)
        self._retrace_timer.setInterval(1)  # 1ms debounce delay
        self._retrace_timer.timeout.connect(self._do_retrace)

    @property
    def ray_data(self) -> list:
        """Get the current ray data (list of RayPath objects)."""
        return self._ray_data

    @property
    def autotrace(self) -> bool:
        """Get autotrace enabled state."""
        return self._autotrace

    @autotrace.setter
    def autotrace(self, value: bool) -> None:
        """Set autotrace enabled state."""
        self._autotrace = value

    @property
    def ray_width_px(self) -> float:
        """Get ray width in pixels."""
        return self._ray_width_px

    @ray_width_px.setter
    def ray_width_px(self, value: float) -> None:
        """Set ray width in pixels and trigger retrace."""
        self._ray_width_px = float(value)
        self.schedule_retrace()

    def clear_rays(self) -> None:
        """Remove all ray graphics from scene."""
        self._ray_renderer.clear()
        self._ray_data.clear()

    def schedule_retrace(self) -> None:
        """
        Schedule a retrace with debouncing to prevent excessive calls.

        This method prevents framerate issues by:
        - Only scheduling one retrace at a time (prevents queue buildup)
        - Adding a small delay to batch rapid changes together
        - Checking if autotrace is enabled before scheduling
        """
        if not self._autotrace:
            return
        if not self._retrace_pending:
            self._retrace_pending = True
            self._retrace_timer.start()

    def _do_retrace(self) -> None:
        """Execute the actual retrace (called by timer after debounce delay)."""
        self._retrace_pending = False
        with ErrorContext("while raytracing", show_dialog=False, suppress=True):
            self.retrace()

    def retrace(self) -> None:
        """
        Trace all rays from sources through optical elements.

        Uses polymorphic raytracing engine with interface-based approach where
        all components expose their optical interfaces via get_interfaces_scene().
        """
        with ErrorContext("while raytracing", show_dialog=False, suppress=True):
            self.clear_rays()

            # Import here to avoid circular imports
            from ...objects import SourceItem
            from ...core.models import SourceParams

            # Collect sources
            sources: list[SourceItem] = []
            for it in self._scene.items():
                if isinstance(it, SourceItem):
                    sources.append(it)

            if not sources:
                return

            # Convert scene to polymorphic elements using the integration adapter
            try:
                from ...integration import convert_scene_to_polymorphic
                elements = convert_scene_to_polymorphic(self._scene.items())
            except Exception as e:
                self._log_service.error(f"Error converting scene: {e}", LogCategory.RAYTRACING)
                return

            # Build source params (use actual params from items)
            srcs: list[SourceParams] = []
            for S in sources:
                srcs.append(S.params)

            # Trace using polymorphic engine
            try:
                from ...raytracing import trace_rays_polymorphic
                paths = trace_rays_polymorphic(elements, srcs, max_events=MAX_RAYTRACING_EVENTS)
            except Exception as e:
                self._log_service.error(f"Error in raytracing: {e}", LogCategory.RAYTRACING)
                return

            # Render paths
            self._render_ray_paths(paths)

    def _render_ray_paths(self, paths) -> None:
        """
        Render ray paths to the scene.

        Delegates to RayRenderer for actual rendering.

        Args:
            paths: List of RayPath objects
        """
        # Store ray data for inspect tool and path measure tool
        self._ray_data = list(paths)

        # Sync ray width with renderer
        self._ray_renderer.ray_width_px = self._ray_width_px

        # Delegate rendering to RayRenderer
        self._ray_renderer.render(paths)

        # Notify that rays have changed
        self.rays_changed.emit()



