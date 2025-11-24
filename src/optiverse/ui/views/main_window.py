from __future__ import annotations

import json
import os
from functools import partial
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.constants import (
    SCENE_SIZE_MM,
    SCENE_MIN_COORD,
    AUTOSAVE_DEBOUNCE_MS,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
)
from ...core.ui_constants import (
    ZOOM_FACTOR,
    MAGNETIC_SNAP_TOLERANCE_PX,
)
from ...core.component_types import ComponentType
from ...core.editor_state import EditorMode, EditorState
from ...core.models import SourceParams
from ...core.snap_helper import SnapHelper
from ...core.undo_commands import AddItemCommand
from ...core.undo_stack import UndoStack
from ...services.settings_service import SettingsService
from ...services.storage_service import StorageService
from ...services.collaboration_manager import CollaborationManager
from ...services.log_service import get_log_service
from ...services.error_handler import get_error_handler, ErrorContext
from ..controllers import RaytracingController
from ..controllers.library_manager import LibraryManager
from ..controllers.item_drag_handler import ItemDragHandler
from ..controllers.component_operations import ComponentOperationsHandler
from ..controllers.ray_renderer import RayRenderer
from ..widgets.library_tree import LibraryTree
from .collaboration_dialog import CollaborationDialog
from .log_window import LogWindow
from .tool_handlers import InspectToolHandler, PathMeasureToolHandler, point_to_segment_distance
from .placement_handler import PlacementHandler
from ..builders import ActionBuilder
from ...services.scene_file_manager import SceneFileManager
from ...objects import (
    GraphicsView,
    RulerItem,
    SourceItem,
    TextNoteItem,
)


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
        self.scene.setSceneRect(
            SCENE_MIN_COORD, SCENE_MIN_COORD, SCENE_SIZE_MM, SCENE_SIZE_MM
        )
        self.view = GraphicsView(self.scene)
        self.view.main_window = self  # Reference for dropEvent callback
        self.setCentralWidget(self.view)
        
        # Initialize OpenGL ray overlay for hardware-accelerated rendering
        self.view._create_ray_overlay()

        # State variables
        self.snap_to_grid = False
        self.ray_items: list[QtWidgets.QGraphicsPathItem] = []
        
        # Centralized editor state (replaces scattered boolean flags)
        self._editor_state = EditorState()
        
        # Path measure tool state (managed by handler, kept here for compatibility)
        self._path_measure_state = None  # 'waiting_first_click' or 'waiting_second_click'
        self._path_measure_ray_index = None
        self._path_measure_start_param = None
        self._path_measure_temp_item = None  # Temporary visual feedback item
        
        # Autosave timer with debouncing (triggered by significant changes)
        self._autosave_timer = QtCore.QTimer()
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DEBOUNCE_MS)
        self._autosave_timer.timeout.connect(self._do_autosave)
        
        # Placement ghost item (managed by PlacementHandler)
        self._placement_ghost = None
        
        # Cache standard component templates for toolbar placement
        # Maps toolbar type strings to library component data
        self._component_templates = {}
        
        # Grid now drawn in GraphicsView.drawBackground() for better performance
        
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
        self.collab_server_process = None  # Track hosted server process
        
        # Track unsaved changes (synced from file_manager via _on_modified_changed)
        self._is_modified = False
        
        # Load saved preferences
        self.magnetic_snap = self.settings_service.get_value("magnetic_snap", True, bool)
        
        # Load dark mode preference and apply theme to match
        dark_mode_saved = self.settings_service.get_value("dark_mode", self.view.is_dark_mode(), bool)
        self.view.set_dark_mode(dark_mode_saved)
        # Apply theme to ensure app-wide styling matches the saved preference
        from ..theme_manager import apply_theme
        apply_theme(dark_mode_saved)
        
        # Connect collaboration signals
        # Note: remote_item_added is handled internally by CollaborationManager._apply_add_item()
        # We only need to update UI status here
        self.collaboration_manager.status_changed.connect(self._on_collaboration_status_changed)
        
        # Initialize extracted handlers
        self._init_handlers()

        # Build library dock first (needed before menus reference libDock)
        self._build_library_dock()
        
        # Build UI using ActionBuilder
        action_builder = ActionBuilder(self)
        action_builder.build_all()
        
        # Mark canvas as modified when commands are pushed
        self._connect_modification_tracking()

        # Install event filter for snap and ruler placement
        self.scene.installEventFilter(self)
        # Grid is now drawn automatically in GraphicsView.drawBackground()
        
        # Check for autosave recovery on startup
        QtCore.QTimer.singleShot(100, self._check_autosave_recovery)
        
        # Set initial window title
        self._update_window_title()
    
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
        
        # Scene file manager - handles save/load/autosave
        self.file_manager = SceneFileManager(
            scene=self.scene,
            log_service=self.log_service,
            get_ray_data=self._get_ray_data,
            on_modified=self._on_modified_changed,
            parent_widget=self,
        )
        
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

    def _connect_modification_tracking(self):
        """Connect signals to track when canvas is modified."""
        # Connect to commandPushed signal instead of monkey-patching
        self.undo_stack.commandPushed.connect(self._on_command_pushed)
    
    def _on_command_pushed(self):
        """Handle command pushed - mark modified and schedule autosave."""
        self._mark_modified()
        # Schedule autosave after significant changes (not during drag)
        self._schedule_autosave()

    def _mark_modified(self):
        """Mark the canvas as having unsaved changes."""
        self.file_manager.mark_modified()
        # NOTE: _is_modified is synced via _on_modified_changed callback

    def _mark_clean(self):
        """Mark the canvas as saved (no unsaved changes)."""
        self.file_manager.mark_clean()
        # NOTE: _is_modified is synced via _on_modified_changed callback

    def _update_window_title(self):
        """Update window title to show file name and modified state."""
        if self._saved_file_path:
            import os
            filename = os.path.basename(self._saved_file_path)
            # Remove extension for cleaner look
            filename_no_ext = os.path.splitext(filename)[0]
            title = filename_no_ext
        else:
            title = "Untitled"
        
        # Add modified indicator (asterisk before title on macOS, standard convention)
        if self._is_modified:
            title = f"{title} — Edited"
        
        self.setWindowTitle(title)
    
    def _schedule_autosave(self):
        """Schedule autosave with debouncing."""
        if self._autosave_timer:
            self._autosave_timer.stop()
            self._autosave_timer.start()
    
    # ----- File management delegated to SceneFileManager -----
    def _do_autosave(self):
        """Perform autosave (delegated to file manager)."""
        self.file_manager.do_autosave()
    
    def _check_autosave_recovery(self):
        """Check for autosave on startup (delegated to file manager)."""
        if self.file_manager.check_autosave_recovery():
            self._schedule_retrace()
    
    def _prompt_save_changes(self):
        """Prompt user to save unsaved changes."""
        reply = self.file_manager.prompt_save_changes()
        if reply == QtWidgets.QMessageBox.StandardButton.Save:
            self.save_assembly()
            if self._is_modified:
                return QtWidgets.QMessageBox.StandardButton.Cancel
        return reply
    
    def _on_modified_changed(self, is_modified: bool):
        """Callback when file manager's modified state changes."""
        self._is_modified = is_modified
        self._update_window_title()
    
    @property
    def _saved_file_path(self) -> Optional[str]:
        """Get saved file path from file manager."""
        return self.file_manager.saved_file_path
    
    @_saved_file_path.setter
    def _saved_file_path(self, value: Optional[str]):
        """Set saved file path on file manager."""
        self.file_manager.saved_file_path = value

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

    def populate_library(self):
        """Load and populate component library (delegated to library manager)."""
        self._component_templates = self.library_manager.populate()
        # Update placement handler with new templates
        if hasattr(self, 'placement_handler'):
            self.placement_handler.component_templates = self._component_templates
    
    def _connect_item_signals(self, item):
        """Connect standard signals for a new item (edited, commandCreated)."""
        from ...objects import BaseObj
        
        # Connect edited signal for retrace and collaboration
        if hasattr(item, 'edited'):
            item.edited.connect(self._maybe_retrace)
            item.edited.connect(partial(self.collaboration_manager.broadcast_update_item, item))
        
        # Connect commandCreated signal for undo/redo
        if isinstance(item, BaseObj) and hasattr(item, 'commandCreated'):
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

    def start_place_ruler(self):
        """Enter ruler placement mode (two-click)."""
        # Cancel any other active mode
        if self._editor_state.is_inspect:
            self.act_inspect.setChecked(False)
        if self._editor_state.is_path_measure:
            self.act_measure_path.setChecked(False)
        if self._editor_state.is_placement:
            self._cancel_placement_mode()
        
        self._editor_state.enter_ruler_placement()
        self._prev_cursor = self.view.cursor()
        self.view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), "Click start point, then end point")

    def _finish_place_ruler(self):
        """Exit ruler placement mode."""
        self._editor_state.enter_default()
        if self._prev_cursor is not None:
            self.view.setCursor(self._prev_cursor)
            self._prev_cursor = None

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

    # ----- Save / Load (delegated to SceneFileManager) -----
    def save_assembly(self):
        """Quick save: save to current file or prompt if new."""
        with ErrorContext("while saving assembly", suppress=True):
            if self._saved_file_path:
                self.file_manager.save_to_file(self._saved_file_path)
            else:
                self.save_assembly_as()
    
    def save_assembly_as(self):
        """Save As: always prompt for new file location."""
        with ErrorContext("while saving assembly", suppress=True):
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Assembly As", "", "Optics Assembly (*.json)"
            )
            if path:
                self.file_manager.save_to_file(path)

    def open_assembly(self):
        """Load all elements from JSON file."""
        with ErrorContext("while opening assembly", suppress=True):
            if self._is_modified:
                reply = self._prompt_save_changes()
                if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return
            
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open Assembly", "", "Optics Assembly (*.json)"
            )
            if not path:
                return
            
            if not self.file_manager.open_file(path):
                return
        
        # Connect edited signal for optical components
        from ...objects import BaseObj
        for item in self.scene.items():
            if isinstance(item, BaseObj) and hasattr(item, 'edited'):
                item.edited.connect(self._maybe_retrace)
        
        # Clear undo history after loading
        self.undo_stack.clear()
        self._schedule_retrace()

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
            self.scene.itemsBoundingRect(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio
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
        """Toggle inspect tool mode."""
        if on:
            # Cancel any other active mode
            if self._editor_state.is_placement:
                self._cancel_placement_mode()
            if self._editor_state.is_path_measure:
                self.act_measure_path.setChecked(False)
            if self._editor_state.is_ruler_placement:
                self._finish_place_ruler()
            
            self._editor_state.enter_inspect()
            # Change cursor to indicate inspect mode is active
            self.view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), "Click on a ray to view its properties")
        else:
            self._editor_state.enter_default()
            # Restore default cursor (unset to use widget default)
            self.view.unsetCursor()
    
    def _toggle_path_measure(self, on: bool):
        """Toggle path measure tool mode."""
        if on:
            # Cancel any other active mode
            if self._editor_state.is_placement:
                self._cancel_placement_mode()
            if self._editor_state.is_inspect:
                self.act_inspect.setChecked(False)
            if self._editor_state.is_ruler_placement:
                self._finish_place_ruler()
            
            self._editor_state.enter_path_measure()
            # Activate handler
            self.path_measure_handler.activate()
            # Change cursor to indicate path measure mode is active
            self.view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            QtWidgets.QToolTip.showText(
                QtGui.QCursor.pos(),
                "Click on a ray to set start point.\n\n"
                "💡 Tip: At beam splitters, transmitted and reflected are separate rays.\n"
                "Create one measurement for each path."
            )
        else:
            self._editor_state.enter_default()
            # Deactivate handler
            self.path_measure_handler.deactivate()
            # Restore default cursor
            self.view.unsetCursor()
    
    def _toggle_placement_mode(self, component_type: str, on: bool):
        """Toggle component placement mode."""
        if on:
            # Cancel any other active mode
            if self._editor_state.is_inspect:
                self.act_inspect.setChecked(False)
            if self._editor_state.is_path_measure:
                self.act_measure_path.setChecked(False)
            if self._editor_state.is_ruler_placement:
                self._finish_place_ruler()
            
            # Disable any other placement mode buttons
            self._cancel_placement_mode(except_type=component_type)
            
            # Enter placement mode
            self._editor_state.enter_placement(component_type)
            
            # Activate handler
            self.placement_handler.activate(component_type)
        else:
            # Exit placement mode
            self._cancel_placement_mode()
    
    def _cancel_placement_mode(self, except_type: str | None = None):
        """Cancel placement mode and clean up."""
        # Get previous type before deactivating
        prev_type = self.placement_handler.component_type if self.placement_handler.is_active else self._editor_state.placement_type
        
        # Deactivate handler (handles ghost cleanup, cursor, mouse tracking)
        self.placement_handler.deactivate()
        
        # Reset state
        self._editor_state.enter_default()
        self._placement_ghost = None  # Handler manages this now
        
        # Uncheck toolbar buttons (except the one we're toggling to)
        if prev_type != except_type:
            # Map component types to their actions
            type_to_action = {
                ComponentType.SOURCE: self.act_add_source,
                ComponentType.LENS: self.act_add_lens,
                ComponentType.MIRROR: self.act_add_mirror,
                ComponentType.BEAMSPLITTER: self.act_add_bs,
                ComponentType.TEXT: self.act_add_text,
                ComponentType.RECTANGLE: self.act_add_rectangle,
            }
            # Handle both enum and string types for backward compatibility
            if isinstance(prev_type, str):
                try:
                    prev_type = ComponentType(prev_type)
                except ValueError:
                    prev_type = None
            if prev_type in type_to_action:
                type_to_action[prev_type].setChecked(False)

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

    def open_component_editor(self):
        """Open component editor dialog."""
        try:
            from .component_editor_dialog import ComponentEditorDialog
        except ImportError as e:
            QtWidgets.QMessageBox.critical(self, "Import error", str(e))
            return
        self._comp_editor = ComponentEditorDialog(self.storage_service, self)
        self._comp_editor.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        # Connect saved signal to reload library
        if hasattr(self._comp_editor, "saved"):
            self._comp_editor.saved.connect(self.populate_library)
        self._comp_editor.show()
    
    def open_component_editor_with_data(self, component_data: dict):
        """Open component editor dialog with a specific component loaded."""
        try:
            from .component_editor_dialog import ComponentEditorDialog
        except ImportError as e:
            QtWidgets.QMessageBox.critical(self, "Import error", str(e))
            return
        self._comp_editor = ComponentEditorDialog(self.storage_service, self)
        self._comp_editor.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        # Connect saved signal to reload library
        if hasattr(self._comp_editor, "saved"):
            self._comp_editor.saved.connect(self.populate_library)
        # Load the component data into the editor
        self._comp_editor._load_from_dict(component_data)
        self._comp_editor.show()
    
    def open_user_library_folder(self):
        """Open the user library folder in the system file explorer."""
        from ...platform.paths import get_user_library_root
        import subprocess
        import sys
        
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
                f"(Could not open folder automatically: {str(e)})"
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

    # ----- Event filter for snap, ruler placement, inspect, and placement mode -----
    def eventFilter(self, obj, ev):
        """Handle scene events for snap, ruler placement, inspect tool, and component placement."""
        et = ev.type()

        # --- Component placement mode ---
        if self.placement_handler.is_active:
            # Mouse move - update ghost position
            if et == QtCore.QEvent.Type.GraphicsSceneMouseMove:
                mev = ev  # QGraphicsSceneMouseEvent
                scene_pt = mev.scenePos()
                self.placement_handler.handle_mouse_move(scene_pt)
                return True  # consume event
            
            # Mouse press - place component or cancel
            elif et == QtCore.QEvent.Type.GraphicsSceneMousePress:
                mev = ev  # QGraphicsSceneMouseEvent
                scene_pt = mev.scenePos()
                
                if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                    self.placement_handler.handle_click(scene_pt, mev.button())
                    return True  # consume event
                
                elif mev.button() == QtCore.Qt.MouseButton.RightButton:
                    # Cancel placement
                    self._cancel_placement_mode()
                    return True  # consume event
        
        # --- Inspect tool ---
        if self._editor_state.is_inspect and et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            mev = ev  # QGraphicsSceneMouseEvent
            if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                scene_pt = mev.scenePos()
                self.inspect_handler.handle_click(scene_pt)
                return True  # consume event
        
        # --- Path Measure tool ---
        if self._editor_state.is_path_measure and et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            mev = ev  # QGraphicsSceneMouseEvent
            if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                scene_pt = mev.scenePos()
                self.path_measure_handler.handle_click(scene_pt)
                return True  # consume event

        # --- Ruler 2-click placement ---
        if self._editor_state.is_ruler_placement and et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            mev = ev  # QGraphicsSceneMouseEvent
            if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                scene_pt = mev.scenePos()
                if self._editor_state.ruler_first_point is None:
                    # first click
                    self._editor_state.ruler_first_point = QtCore.QPointF(scene_pt)
                    return True  # consume
                else:
                    # second click -> create ruler in item coords
                    p1 = QtCore.QPointF(self._editor_state.ruler_first_point)
                    p2 = QtCore.QPointF(scene_pt)
                    R = RulerItem(p1, p2)
                    R.setPos(0, 0)
                    cmd = AddItemCommand(self.scene, R)
                    self.undo_stack.push(cmd)
                    R.setSelected(True)
                    self._finish_place_ruler()
                    return True  # consume
            elif mev.button() == QtCore.Qt.MouseButton.RightButton:
                # cancel placement on right-click
                self._finish_place_ruler()
                return True

        # --- Track item positions and rotations on mouse press ---
        if et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            self.drag_handler.handle_mouse_press(ev)

        # --- Snap to grid and create move/rotate commands on mouse release ---
        if et == QtCore.QEvent.Type.GraphicsSceneMouseRelease:
            self.drag_handler.handle_mouse_release()

        return super().eventFilter(obj, ev)
    
    def keyPressEvent(self, ev):
        """Handle key press events for mode cancellation and deletion."""
        # Check if Escape is pressed and any special mode is active
        if ev.key() == QtCore.Qt.Key.Key_Escape:
            if self._editor_state.is_placement:
                self._cancel_placement_mode()
                ev.accept()
                return
            elif self._editor_state.is_ruler_placement:
                self._finish_place_ruler()
                ev.accept()
                return
            elif self._editor_state.is_inspect:
                self.act_inspect.setChecked(False)
                ev.accept()
                return
            elif self._editor_state.is_path_measure:
                self.act_measure_path.setChecked(False)
                ev.accept()
                return
        
        # Pass to parent for normal handling (Delete/Backspace handled by act_delete action)
        super().keyPressEvent(ev)

    def show_log_window(self):
        """Show the application log window."""
        log_window = LogWindow(self)
        log_window.show()
    
    # ----- Collaboration -----
    def open_collaboration_dialog(self):
        """Open dialog to connect to or host a collaboration session."""
        dialog = CollaborationDialog(self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            info = dialog.get_connection_info()
            
            mode = info.get("mode", "connect")
            
            if mode == "host":
                # Host creating a new session
                session_id = info.get("session_id", "default")
                user_id = info.get("user_id", "host")
                use_current_canvas = info.get("use_current_canvas", True)
                
                # Store server process if hosted locally
                if dialog.server_process:
                    self.collab_server_process = dialog.server_process
                
                # Create session as host
                self.collaboration_manager.create_session(
                    session_id=session_id,
                    user_id=user_id,
                    use_current_canvas=use_current_canvas
                )
                
                # Connect to local server
                server_url = f"ws://localhost:{info.get('port', 8765)}"
                self.collaboration_manager.connect_to_session(server_url, session_id, user_id)
                
                self.log_service.info(
                    f"Created session '{session_id}' as host (current_canvas={use_current_canvas})",
                    "Collaboration"
                )
            
            else:
                # Client joining existing session
                server_url = info.get("server_url", "ws://localhost:8765")
                session_id = info.get("session_id", "default")
                user_id = info.get("user_id", "user")
                
                # Join session as client
                self.collaboration_manager.join_session(server_url, session_id, user_id)
                
                self.log_service.info(
                    f"Joining session '{session_id}' as client",
                    "Collaboration"
                )
            
            self.act_disconnect.setEnabled(True)
            self.act_collaborate.setEnabled(False)
    
    def disconnect_collaboration(self):
        """Disconnect from collaboration session."""
        self.collaboration_manager.disconnect()
        self.act_disconnect.setEnabled(False)
        self.act_collaborate.setEnabled(True)
        self.collab_status_label.setText("Not connected")
        
        # Stop server if we're hosting one
        if self.collab_server_process:
            try:
                self.collab_server_process.terminate()
                try:
                    self.collab_server_process.wait(timeout=3)
                except TimeoutError:
                    self.collab_server_process.kill()
                self.log_service.info("Stopped collaboration server", "Collaboration")
            except OSError as e:
                self.log_service.warning(f"Error stopping server: {e}", "Collaboration")
            finally:
                self.collab_server_process = None
    
    def _on_collaboration_status_changed(self, status: str):
        """Update collaboration status indicator."""
        self.collab_status_label.setText(f"Collaboration: {status}")
    
    # ensure clean shutdown
    def closeEvent(self, e: QtGui.QCloseEvent):
        # Check for unsaved changes
        if self._is_modified:
            reply = self._prompt_save_changes()
            if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                e.ignore()  # Don't close the window
                return
        
        try:
            # Stop autosave timer
            if hasattr(self, '_autosave_timer'):
                self._autosave_timer.stop()
            
            # Clear autosave on clean exit
            self.file_manager.clear_autosave()
            
            if hasattr(self, "_comp_editor") and self._comp_editor:
                self._comp_editor.close()
            # Disconnect from collaboration and stop server if running
            if hasattr(self, "collaboration_manager"):
                self.disconnect_collaboration()
        except (OSError, RuntimeError):
            # Ignore cleanup errors during shutdown
            pass
        super().closeEvent(e)
