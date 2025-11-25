from __future__ import annotations

import os
from functools import partial
from pathlib import Path

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.constants import (
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    SCENE_MIN_COORD,
    SCENE_SIZE_MM,
)
from ...core.editor_state import EditorState
from ...core.protocols import Editable
from ...core.snap_helper import SnapHelper
from ...core.ui_constants import (
    MAGNETIC_SNAP_TOLERANCE_PX,
    ZOOM_FACTOR,
)
from ...core.undo_stack import UndoStack
from ...objects import (
    GraphicsView,
)
from ...services.collaboration_manager import CollaborationManager
from ...services.log_service import get_log_service
from ...services.settings_service import SettingsService
from ...services.storage_service import StorageService
from ..builders import ActionBuilder
from ..controllers import (
    CollaborationController,
    FileController,
    RaytracingController,
    ToolModeController,
)
from ..controllers.component_operations import ComponentOperationsHandler
from ..controllers.item_drag_handler import ItemDragHandler
from ..controllers.library_manager import LibraryManager
from ..controllers.ray_renderer import RayRenderer
from ..widgets.library_tree import LibraryTree
from .log_window import LogWindow
from .placement_handler import PlacementHandler
from .ruler_placement_handler import RulerPlacementHandler
from .scene_event_handler import SceneEventHandler
from .tool_handlers import AngleMeasureToolHandler, InspectToolHandler, PathMeasureToolHandler


def _get_icon_path(icon_name: str) -> str:
    """Get the full path to an icon file."""
    icons_dir = Path(__file__).parent.parent / "icons"
    return str(icons_dir / icon_name)


def to_np(p: QtCore.QPointF) -> np.ndarray:
    """Convert QPointF to numpy array."""
    return np.array([p.x(), p.y()], float)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D Ray Optics Sandbox — Top View (mm/cm grid)")
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        # Set window icon
        icon_path = _get_icon_path("optiverse.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        # Scene and view
        self.scene = QtWidgets.QGraphicsScene(self)
        # Effectively "infinite" scene (see constants.py for details)
        # Centered at origin for optical bench convention
        self.scene.setSceneRect(SCENE_MIN_COORD, SCENE_MIN_COORD, SCENE_SIZE_MM, SCENE_SIZE_MM)
        self.view = GraphicsView(self.scene)
        # Connect drop signal instead of circular reference
        self.view.componentDropped.connect(self.on_drop_component)
        self.setCentralWidget(self.view)

        # Initialize OpenGL ray overlay for hardware-accelerated rendering
        self.view._create_ray_overlay()

        # State variables
        self.snap_to_grid = False
        self.ray_items: list[QtWidgets.QGraphicsPathItem] = []

        # Centralized editor state (replaces scattered boolean flags)
        self._editor_state = EditorState()

        # Cache standard component templates for toolbar placement
        self._component_templates = {}

        # Snap helper for magnetic alignment
        self._snap_helper = SnapHelper(tolerance_px=MAGNETIC_SNAP_TOLERANCE_PX)

        # Ruler placement cursor backup
        self._prev_cursor = None

        # Services
        self.settings_service = SettingsService()
        self.storage_service = StorageService(settings_service=self.settings_service)
        self.undo_stack = UndoStack()
        self.collaboration_manager = CollaborationManager(self)
        self.log_service = get_log_service()
        self.log_service.debug("MainWindow.__init__ called", "Init")

        # Load saved preferences
        self.magnetic_snap = self.settings_service.get_value("magnetic_snap", True, bool)

        # Load dark mode preference and apply theme to match
        dark_mode_saved = self.settings_service.get_value(
            "dark_mode", self.view.is_dark_mode(), bool
        )
        self.view.set_dark_mode(dark_mode_saved)
        # Apply theme to ensure app-wide styling matches the saved preference
        from ..theme_manager import apply_theme

        apply_theme(dark_mode_saved)

        # Initialize extracted handlers
        self._init_handlers()

        # Build library dock first (needed before menus reference libDock)
        self._build_library_dock()

        # Tool mode controller - manages inspect, path measure, angle measure, placement modes
        self.tool_controller = ToolModeController(
            editor_state=self._editor_state,
            view=self.view,
            path_measure_handler=self.path_measure_handler,
            angle_measure_handler=self.angle_measure_handler,
            placement_handler=self.placement_handler,
            parent=self,
        )

        # Build UI using ActionBuilder
        action_builder = ActionBuilder(self)
        action_builder.build_all()

        # Initialize handlers that need actions (after action_builder creates them)
        self._init_event_handlers()

        # Install event filter for snap and ruler placement
        self.scene.installEventFilter(self)

        # Check for autosave recovery on startup
        QtCore.QTimer.singleShot(100, self.file_controller.check_autosave_recovery)

    def _init_handlers(self):
        """Initialize extracted handler classes."""
        # Ray renderer for rendering traced paths
        self.ray_renderer = RayRenderer(self.scene, self.view)

        # Raytracing controller - manages ray tracing, debouncing, and ray data
        self.raytracing_controller = RaytracingController(
            scene=self.scene,
            ray_renderer=self.ray_renderer,
            log_service=self.log_service,
            parent=self,
        )

        # File controller - handles save/load/autosave with UI
        self.file_controller = FileController(
            scene=self.scene,
            undo_stack=self.undo_stack,
            log_service=self.log_service,
            get_ray_data=self._get_ray_data,
            parent_widget=self,
            connect_item_signals=self._connect_item_signals,
        )
        # Connect file controller signals
        self.file_controller.traceRequested.connect(self._schedule_retrace)
        self.file_controller.windowTitleChanged.connect(self.setWindowTitle)

        # Collaboration controller - handles hosting/joining sessions
        self.collab_controller = CollaborationController(
            collaboration_manager=self.collaboration_manager,
            log_service=self.log_service,
            parent_widget=self,
        )
        # Status updates are connected via ActionBuilder to status label

        # Inspect tool handler
        self.inspect_handler = InspectToolHandler(
            view=self.view,
            get_ray_data=self._get_ray_data,
            parent_widget=self,
        )

        # Path measure tool handler
        self.path_measure_handler = PathMeasureToolHandler(
            scene=self.scene,
            view=self.view,
            undo_stack=self.undo_stack,
            get_ray_data=self._get_ray_data,
            parent_widget=self,
            on_complete=self._on_path_measure_complete,
        )

        # Angle measure tool handler
        self.angle_measure_handler = AngleMeasureToolHandler(
            scene=self.scene,
            view=self.view,
            undo_stack=self.undo_stack,
            parent_widget=self,
            on_complete=self._on_angle_measure_complete,
        )

        # Item drag handler - tracks positions/rotations for undo/redo
        self.drag_handler = ItemDragHandler(
            scene=self.scene,
            view=self.view,
            undo_stack=self.undo_stack,
            snap_to_grid_getter=self._get_snap_to_grid,
            schedule_retrace=self._schedule_retrace,
        )

        # Component operations handler - copy, paste, delete, drop
        self.component_ops = ComponentOperationsHandler(
            scene=self.scene,
            undo_stack=self.undo_stack,
            collaboration_manager=self.collaboration_manager,
            log_service=self.log_service,
            snap_to_grid_getter=self._get_snap_to_grid,
            connect_item_signals=self._connect_item_signals,
            schedule_retrace=self._schedule_retrace,
            set_paste_enabled=self._set_paste_enabled,
            parent_widget=self,
        )

        # Note: PlacementHandler is initialized after _build_library_dock()
        # because it needs _component_templates which is populated by populate_library()

    # Grid is now drawn in GraphicsView.drawBackground() for much better performance
    # No need for _draw_grid() method anymore!

    def _build_library_dock(self):
        """Build component library dock with categorized tree view."""
        self.libDock = QtWidgets.QDockWidget("Component Library", self)
        self.libDock.setObjectName("libDock")
        self.libraryTree = LibraryTree(self)
        self.libDock.setWidget(self.libraryTree)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.libDock)

        # Initialize library manager
        self.library_manager = LibraryManager(
            library_tree=self.libraryTree,
            storage_service=self.storage_service,
            log_service=self.log_service,
            get_dark_mode=self.view.is_dark_mode,
            get_style=self.style,
            parent_widget=self,
        )
        self._component_templates = self.library_manager.populate()

        # Initialize PlacementHandler now that component_templates is populated
        self.placement_handler = PlacementHandler(
            scene=self.scene,
            view=self.view,
            undo_stack=self.undo_stack,
            log_service=self.log_service,
            component_templates=self._component_templates,
            snap_to_grid_getter=self._get_snap_to_grid,
            connect_item_signals=self._connect_item_signals,
            schedule_retrace=self._schedule_retrace,
            broadcast_add_item=self.collaboration_manager.broadcast_add_item,
        )

    def _init_event_handlers(self):
        """Initialize handlers that require actions to be created first."""
        # Ruler placement handler
        self.ruler_handler = RulerPlacementHandler(
            scene=self.scene,
            view=self.view,
            editor_state=self._editor_state,
            undo_stack=self.undo_stack,
            get_ruler_action=lambda: self.act_add_ruler,
            finish_ruler_mode=self.tool_controller.finish_ruler_placement,
        )

        # Scene event handler - routes events to appropriate handlers
        self.scene_event_handler = SceneEventHandler(
            editor_state=self._editor_state,
            placement_handler=self.placement_handler,
            inspect_handler=self.inspect_handler,
            path_measure_handler=self.path_measure_handler,
            angle_measure_handler=self.angle_measure_handler,
            ruler_handler=self.ruler_handler,
            drag_handler=self.drag_handler,
            cancel_placement_mode=self._cancel_placement_mode,
            get_inspect_action=lambda: self.act_inspect,
            get_path_measure_action=lambda: self.act_measure_path,
            get_angle_measure_action=lambda: self.act_measure_angle,
            parent=self,
        )

    def populate_library(self):
        """Load and populate component library (delegated to library manager)."""
        self._component_templates = self.library_manager.populate()
        # Update placement handler with new templates (always exists after _build_library_dock)
        self.placement_handler.component_templates = self._component_templates

    def _connect_item_signals(self, item):
        """Connect standard signals for a new item (edited, commandCreated)."""
        from ...objects import BaseObj

        # Connect edited signal for retrace and collaboration
        if isinstance(item, Editable):
            item.edited.connect(self._maybe_retrace)
            item.edited.connect(partial(self.collaboration_manager.broadcast_update_item, item))

        # Connect commandCreated signal for undo/redo
        # BaseObj and RulerItem both have commandCreated signal
        if isinstance(item, BaseObj):
            item.commandCreated.connect(self.undo_stack.push)
        elif isinstance(item, RulerItem):
            item.commandCreated.connect(self.undo_stack.push)

    def on_drop_component(self, rec: dict, scene_pos: QtCore.QPointF):
        """Handle component drop from library (delegated to component_ops)."""
        self.component_ops.on_drop_component(rec, scene_pos)

    def delete_selected(self):
        """Delete selected items (delegated to component_ops)."""
        self.component_ops.delete_selected()

    def copy_selected(self):
        """Copy selected items to clipboard (delegated to component_ops)."""
        self.component_ops.copy_selected()

    def paste_items(self):
        """Paste items from clipboard at current cursor position (delegated to component_ops)."""
        # Get cursor position in scene coordinates
        cursor_global = QtGui.QCursor.pos()
        cursor_view = self.view.mapFromGlobal(cursor_global)
        cursor_scene = self.view.mapToScene(cursor_view)

        self.component_ops.paste_items(cursor_scene)

    def _do_undo(self):
        """Undo last action and retrace rays."""
        self.undo_stack.undo()
        self._schedule_retrace()

    def _do_redo(self):
        """Redo last undone action and retrace rays."""
        self.undo_stack.redo()
        self._schedule_retrace()

    def _toggle_ruler_placement(self, on: bool):
        """Toggle ruler placement mode (delegated to RulerPlacementHandler)."""
        self.ruler_handler.toggle(on, self.tool_controller._cancel_other_modes)

    def start_place_ruler(self):
        """Enter ruler placement mode (delegated to RulerPlacementHandler)."""
        self.ruler_handler.start(self.tool_controller._cancel_other_modes)

    def _finish_place_ruler(self):
        """Exit ruler placement mode (delegated to RulerPlacementHandler)."""
        self.ruler_handler.finish()

    # ----- Ray tracing (delegated to RaytracingController) -----
    def clear_rays(self):
        """Remove all ray graphics from scene."""
        self.raytracing_controller.clear_rays()

    def _schedule_retrace(self):
        """Schedule a retrace with debouncing."""
        self.raytracing_controller.schedule_retrace()

    def retrace(self):
        """Trace all rays from sources through optical elements."""
        self.raytracing_controller.retrace()

    def _maybe_retrace(self):
        """Retrace if autotrace is enabled (with debouncing)."""
        self._schedule_retrace()

    # Properties to maintain backward compatibility
    @property
    def ray_data(self) -> list:
        """Get ray data from controller."""
        return self.raytracing_controller.ray_data

    @property
    def autotrace(self) -> bool:
        """Get autotrace enabled state from controller."""
        return self.raytracing_controller.autotrace

    @autotrace.setter
    def autotrace(self, value: bool) -> None:
        """Set autotrace enabled state on controller."""
        self.raytracing_controller.autotrace = value

    @property
    def _ray_width_px(self) -> float:
        """Get ray width from controller."""
        return self.raytracing_controller.ray_width_px

    @_ray_width_px.setter
    def _ray_width_px(self, value: float) -> None:
        """Set ray width on controller."""
        self.raytracing_controller.ray_width_px = value

    # ----- Getter methods for handlers (replaces lambda callbacks) -----
    def _get_ray_data(self) -> list:
        """Get ray data - used by handlers instead of lambda."""
        return self.raytracing_controller.ray_data

    def _get_snap_to_grid(self) -> bool:
        """Get snap to grid state - used by handlers instead of lambda."""
        return self.snap_to_grid

    def _set_paste_enabled(self, enabled: bool) -> None:
        """Set paste action enabled state - used by handlers instead of lambda."""
        self.act_paste.setEnabled(enabled)

    def _on_path_measure_complete(self) -> None:
        """Called when path measure tool completes - used instead of lambda."""
        self.act_measure_path.setChecked(False)

    def _on_angle_measure_complete(self) -> None:
        """Called when angle measure tool completes - used instead of lambda."""
        self.act_measure_angle.setChecked(False)

    # ----- Save / Load (delegated to FileController) -----
    def save_assembly(self):
        """Quick save (delegated to file controller)."""
        self.file_controller.save_assembly()

    def save_assembly_as(self):
        """Save As (delegated to file controller)."""
        self.file_controller.save_assembly_as()

    def open_assembly(self):
        """Open assembly (delegated to file controller)."""
        if self.file_controller.open_assembly():
            # Connect edited signal for optical components
            for item in self.scene.items():
                if isinstance(item, Editable):
                    item.edited.connect(self._maybe_retrace)

    # ----- Settings -----
    def _toggle_autotrace(self, on: bool):
        """Toggle auto-trace."""
        self.autotrace = on
        if on:
            self._schedule_retrace()

    def _toggle_snap(self, on: bool):
        """Toggle snap to grid."""
        self.snap_to_grid = on

    def _toggle_magnetic_snap(self, on: bool):
        """Toggle magnetic snap."""
        self.magnetic_snap = on
        self.settings_service.set_value("magnetic_snap", on)
        # Clear guides if turning off
        if not on:
            self.view.clear_snap_guides()

    def _toggle_dark_mode(self, on: bool):
        """Toggle dark mode."""
        self.view.set_dark_mode(on)
        self.settings_service.set_value("dark_mode", on)
        # Apply the theme to the entire application
        from ..theme_manager import apply_theme

        apply_theme(on)
        # Refresh library to update category colors
        self.populate_library()

    def _zoom_in(self):
        """Zoom in by ZOOM_FACTOR."""
        self.view.scale(ZOOM_FACTOR, ZOOM_FACTOR)
        self.view.zoomChanged.emit()

    def _zoom_out(self):
        """Zoom out by ZOOM_FACTOR."""
        self.view.scale(1 / ZOOM_FACTOR, 1 / ZOOM_FACTOR)
        self.view.zoomChanged.emit()

    def _fit_scene(self):
        """Fit scene contents in view."""
        self.view.fitInView(
            self.scene.itemsBoundingRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio
        )
        self.view.zoomChanged.emit()

    def _recenter_view(self):
        """Reset view to default position (centered at origin) and zoom level (1:1)."""
        # Reset transform to identity (removes any zoom/pan/rotation)
        self.view.resetTransform()
        # Re-apply Y-flip for coordinate system (Y-up world coordinates)
        self.view.scale(1.0, -1.0)
        # Center view on origin (0, 0)
        self.view.centerOn(0, 0)
        # Emit zoom changed signal to update UI
        self.view.zoomChanged.emit()

    def _toggle_inspect(self, on: bool):
        """Toggle inspect tool mode (delegated to ToolModeController)."""
        self.tool_controller.toggle_inspect(on)

    def _toggle_path_measure(self, on: bool):
        """Toggle path measure tool mode (delegated to ToolModeController)."""
        self.tool_controller.toggle_path_measure(on)

    def _toggle_angle_measure(self, on: bool):
        """Toggle angle measure tool mode (delegated to ToolModeController)."""
        self.tool_controller.toggle_angle_measure(on)

    def _toggle_placement_mode(self, component_type: str, on: bool):
        """Toggle component placement mode (delegated to ToolModeController)."""
        self.tool_controller.toggle_placement(component_type, on)

    def _cancel_placement_mode(self, except_type: str | None = None):
        """Cancel placement mode (delegated to ToolModeController)."""
        self.tool_controller.cancel_placement(except_type=except_type)

    def _set_ray_width(self, v: float):
        """Set ray width and retrace."""
        self._ray_width_px = float(v)
        self._schedule_retrace()

    def _choose_ray_width(self):
        """Show custom ray width dialog."""
        v, ok = QtWidgets.QInputDialog.getDouble(
            self, "Ray width", "Width (px):", float(self._ray_width_px), 0.5, 20.0, 1
        )
        if ok:
            self._set_ray_width(v)
            # update checked state in presets if it matches one
            for act in self._raywidth_group.actions():
                act.setChecked(abs(float(act.text().split()[0]) - v) < 1e-9)

    def open_component_editor(self, component_data: dict = None):
        """
        Open component editor dialog, optionally with pre-loaded data.

        Args:
            component_data: Optional dict to load into the editor
        """
        try:
            from .component_editor_dialog import ComponentEditorDialog
        except ImportError as e:
            QtWidgets.QMessageBox.critical(self, "Import error", str(e))
            return
        self._comp_editor = ComponentEditorDialog(self.storage_service, self)
        self._comp_editor.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        # Connect saved signal to reload library (saved is always a signal on ComponentEditorDialog)
        self._comp_editor.saved.connect(self.populate_library)
        # Load component data if provided
        if component_data is not None:
            self._comp_editor._load_from_dict(component_data)
        self._comp_editor.show()

    def open_user_library_folder(self):
        """Open the user library folder in the system file explorer."""
        import subprocess
        import sys

        from ...platform.paths import get_user_library_root

        library_path = get_user_library_root()

        try:
            if sys.platform == "win32":
                os.startfile(str(library_path))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(library_path)])
            else:  # linux
                subprocess.run(["xdg-open", str(library_path)])
        except (OSError, subprocess.SubprocessError) as e:
            QtWidgets.QMessageBox.information(
                self,
                "User Library Location",
                f"User library location:\n{library_path}\n\n"
                f"(Could not open folder automatically: {str(e)})",
            )

    def open_preferences(self):
        """Open preferences/settings dialog."""
        from .settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.settings_service, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self):
        """Handle settings changes."""
        # Reload library to pick up new library paths
        self.populate_library()

        # Log the change
        self.log_service.info("Settings updated - library reloaded", "Settings")

    def import_component_library(self):
        """Import components from another library folder (delegated to library manager)."""
        if self.library_manager.import_library():
            self.populate_library()

    # ----- Event filter (delegated to SceneEventHandler) -----
    def eventFilter(self, obj, ev):
        """Handle scene events (delegated to SceneEventHandler)."""
        result = self.scene_event_handler.handle_event(obj, ev)
        if result is not None:
            return result
        return super().eventFilter(obj, ev)

    def keyPressEvent(self, ev):
        """Handle key press events (delegated to SceneEventHandler)."""
        if self.scene_event_handler.handle_key_press(ev):
            ev.accept()
            return
        # Pass to parent for normal handling (Delete/Backspace handled by act_delete action)
        super().keyPressEvent(ev)

    def show_log_window(self):
        """Show the application log window."""
        log_window = LogWindow(self)
        log_window.show()

    # ----- Collaboration (delegated to CollaborationController) -----
    def open_collaboration_dialog(self):
        """Open dialog to connect to or host a collaboration session."""
        self.collab_controller.open_dialog()
        if self.collab_controller.is_connected:
            self.act_disconnect.setEnabled(True)
            self.act_collaborate.setEnabled(False)

    def disconnect_collaboration(self):
        """Disconnect from collaboration session."""
        self.collab_controller.disconnect()
        self.act_disconnect.setEnabled(False)
        self.act_collaborate.setEnabled(True)

    # ensure clean shutdown
    def closeEvent(self, e: QtGui.QCloseEvent):
        # Check for unsaved changes
        if self.file_controller.is_modified:
            reply = self.file_controller.prompt_save_changes()
            if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                e.ignore()  # Don't close the window
                return

        try:
            # Clear autosave on clean exit
            self.file_controller.file_manager.clear_autosave()

            # Close component editor if it was opened
            if getattr(self, "_comp_editor", None) is not None:
                self._comp_editor.close()
            # Disconnect from collaboration (collab_controller always exists after __init__)
            self.collab_controller.cleanup()
        except (OSError, RuntimeError):
            # Ignore cleanup errors during shutdown
            pass
        super().closeEvent(e)
