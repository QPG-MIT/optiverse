from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

from optiverse import __version__

from ...core.constants import (
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    SCENE_MIN_COORD,
    SCENE_SIZE_MM,
)
from ...core.editor_state import EditorState
from ...core.layer_tree_state import LayerTreeState
from ...core.layer_zorder_applier import LayerZOrderApplier
from ...core.protocols import Editable
from ...core.snap_helper import SnapHelper
from ...core.ui_constants import (
    MAGNETIC_SNAP_TOLERANCE_PX,
    ZOOM_FACTOR,
)
from ...core.undo_stack import UndoStack
from ...objects import GraphicsView
from ...services.collaboration_manager import CollaborationManager
from ...services.linked_assembly_service import LinkedAssemblyService
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
from ..widgets.layer_panel import LayerPanel
from ..widgets.library_tree import LibraryTree
from .component_canvas_sync import apply_record_to_component_item, normalized_component_name
from .log_window import LogWindow
from .placement_handler import PlacementHandler
from .ruler_placement_handler import RulerPlacementHandler
from .scene_event_handler import SceneEventHandler
from .tool_handlers import AngleMeasureToolHandler, InspectToolHandler, PathMeasureToolHandler


def _get_icon_path(icon_name: str) -> str:
    """Get the full path to an icon file."""
    icons_dir = Path(__file__).parent.parent / "icons"
    return str(icons_dir / icon_name)


class MainWindow(QtWidgets.QMainWindow):
    # Action attributes (initialized by ActionBuilder)
    act_new: QtGui.QAction
    act_open: QtGui.QAction
    act_save: QtGui.QAction
    act_save_as: QtGui.QAction
    act_close: QtGui.QAction
    act_export_image: QtGui.QAction
    act_export_pdf: QtGui.QAction
    act_export_pyopticl: QtGui.QAction
    act_quit: QtGui.QAction
    act_link_assembly: QtGui.QAction
    menu_recent: QtWidgets.QMenu
    open_library_menu: QtWidgets.QMenu
    act_undo: QtGui.QAction
    act_redo: QtGui.QAction
    act_delete: QtGui.QAction
    act_copy: QtGui.QAction
    act_paste: QtGui.QAction
    act_preferences: QtGui.QAction
    act_add_source: QtGui.QAction
    act_add_lens: QtGui.QAction
    act_add_mirror: QtGui.QAction
    act_add_bs: QtGui.QAction
    act_add_ruler: QtGui.QAction
    act_add_text: QtGui.QAction
    act_add_rectangle: QtGui.QAction
    act_inspect: QtGui.QAction
    act_measure_path: QtGui.QAction
    _tool_action_group: QtGui.QActionGroup  # type: ignore[misc]
    act_measure_angle: QtGui.QAction
    act_zoom_in: QtGui.QAction
    act_zoom_out: QtGui.QAction
    act_fit: QtGui.QAction
    act_recenter: QtGui.QAction
    act_autotrace: QtGui.QAction
    act_snap: QtGui.QAction
    act_magnetic_snap: QtGui.QAction
    act_dark_mode: QtGui.QAction
    menu_raywidth: QtWidgets.QMenu
    _raywidth_group: QtGui.QActionGroup
    act_retrace: QtGui.QAction
    act_clear: QtGui.QAction
    act_editor: QtGui.QAction
    act_reload: QtGui.QAction
    act_open_library_folder: QtGui.QAction
    act_import_library: QtGui.QAction
    act_show_log: QtGui.QAction
    act_collaborate: QtGui.QAction
    act_disconnect: QtGui.QAction
    act_import_as_layer: QtGui.QAction
    collab_status_label: QtWidgets.QLabel
    coord_label: QtWidgets.QLabel

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self._format_window_title("Untitled"))
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
        self.view.cursorScenePosChanged.connect(self._update_coord_label)
        self.view.nudgeRequested.connect(self._nudge_selected)
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

        from ...services.library_service import LibraryService

        self.library_service = LibraryService(self.settings_service, parent=self)

        self.undo_stack = UndoStack()
        self.collaboration_manager = CollaborationManager(self)
        self.log_service = get_log_service()
        self.log_service.debug("MainWindow.__init__ called", "Init")

        # Layer tree state for layer hierarchy and grouping
        self.layer_state = LayerTreeState()

        # Z-order applier keeps scene z-values in sync with layer tree order
        self._zorder_applier = LayerZOrderApplier(self.layer_state, self.scene, parent=self)
        self._zorder_applier.zValuesApplied.connect(self._schedule_retrace)

        # Load all preferences from QSettings into the runtime preferences module
        from ...core import preferences
        from ...core.preferences import load_from_settings

        load_from_settings(self.settings_service)

        # Apply persisted toggles
        self.magnetic_snap = self.settings_service.get_value("magnetic_snap", True, bool)
        self.snap_to_grid = self.settings_service.get_value("canvas/snap_to_grid", False, bool)

        dark_mode_saved = self.settings_service.get_value(
            "dark_mode", self.view.is_dark_mode(), bool
        )
        self.view.set_dark_mode(dark_mode_saved)
        self.view.show_scale_bar = preferences.show_scale_bar
        from ..theme_manager import apply_theme

        apply_theme(dark_mode_saved)

        # Initialize extracted handlers
        self._init_handlers()

        # Build library dock first (needed before menus reference libDock)
        self._build_library_dock()

        # Auto-refresh library dock when library paths change
        self.library_service.libraries_changed.connect(self.populate_library)

        # Build layer panel dock (for z-order and grouping)
        self._build_layer_dock()

        # Tool mode controller - manages inspect, path measure, angle measure, placement modes
        self.tool_controller = ToolModeController(
            editor_state=self._editor_state,
            view=self.view,
            path_measure_handler=self.path_measure_handler,
            angle_measure_handler=self.angle_measure_handler,
            placement_handler=self.placement_handler,
            parent=self,
        )

        # Build UI using ActionBuilder (stored for theme switching)
        self.action_builder = ActionBuilder(self)
        self.action_builder.build_all()

        # Initialize handlers that need actions (after action_builder creates them)
        self._init_event_handlers()

        # Re-evaluate paste action whenever system clipboard changes
        QtWidgets.QApplication.clipboard().dataChanged.connect(self._on_clipboard_changed)

        # Apply startup-only preferences (autotrace, ray width, autosave, max events)
        self.autotrace = self.settings_service.get_value("canvas/autotrace", True, bool)
        self._ray_width_px = self.settings_service.get_value(
            "canvas/default_ray_width_px", 2.0, float
        )
        self.raytracing_controller.max_events = preferences.max_raytracing_events
        if preferences.autosave_enabled:
            self.file_controller.set_autosave_interval(preferences.autosave_interval_ms)
        else:
            self.file_controller.disable_autosave()

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
            layer_state=self.layer_state,
            settings_service=self.settings_service,
            library_service=self.library_service,
        )
        # Connect file controller signals
        self.file_controller.traceRequested.connect(self._schedule_retrace)
        self.file_controller.windowTitleChanged.connect(self._on_window_title_changed)

        # Linked assembly service - manages external assembly references
        self.linked_assembly_service = LinkedAssemblyService(
            scene=self.scene,
            layer_state=self.layer_state,
            log_service=self.log_service,
            library_service=self.library_service,
            parent=self,
        )
        self.file_controller.set_linked_assembly_service(self.linked_assembly_service)
        self._linked_update_dialog_open = False
        self.linked_assembly_service.sourceFileChanged.connect(
            self._on_linked_source_changed
        )

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
            layer_state=self.layer_state,
        )

        # Angle measure tool handler
        self.angle_measure_handler = AngleMeasureToolHandler(
            scene=self.scene,
            view=self.view,
            undo_stack=self.undo_stack,
            parent_widget=self,
            on_complete=self._on_angle_measure_complete,
            layer_state=self.layer_state,
        )

        # Item drag handler - tracks positions/rotations for undo/redo
        self.drag_handler = ItemDragHandler(
            scene=self.scene,
            view=self.view,
            undo_stack=self.undo_stack,
            snap_to_grid_getter=self._get_snap_to_grid,
            schedule_retrace=self._schedule_retrace,
            layer_state=self.layer_state,
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

    def _format_window_title(self, subtitle: str) -> str:
        """Format window title with version and subtitle."""
        return f"Optiverse v{__version__} — {subtitle}"

    def _on_window_title_changed(self, subtitle: str) -> None:
        """Handle window title change from file controller."""
        self.setWindowTitle(self._format_window_title(subtitle))

    def _on_linked_source_changed(self, link_uuid: str, path: str) -> None:
        """Handle notification that a linked assembly's source file changed on disk."""
        if self._linked_update_dialog_open:
            return

        import os

        node = self.layer_state.get_node(link_uuid)
        name = node.name if node else os.path.basename(path)

        from ..theme_manager import question as theme_aware_question

        self._linked_update_dialog_open = True
        try:
            reply = theme_aware_question(
                self,
                "Linked Assembly Changed",
                f"{name} has changed on disk.\n\nUpdate now?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.Yes,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.file_controller.refresh_linked_assembly(link_uuid)
                self.layer_panel.refresh()
        finally:
            self._linked_update_dialog_open = False

    def _build_library_dock(self):
        """Build component library dock with categorized tree view and search bar."""
        self.libDock = QtWidgets.QDockWidget("Component Library", self)
        self.libDock.setObjectName("libDock")

        # Container with search bar + tree
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        search_bar = QtWidgets.QLineEdit()
        search_bar.setPlaceholderText("Search components...")
        search_bar.setClearButtonEnabled(True)
        layout.addWidget(search_bar)

        self.libraryTree = LibraryTree(self)
        layout.addWidget(self.libraryTree)

        search_bar.textChanged.connect(self.libraryTree.filter_items)

        self.libDock.setWidget(container)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.libDock)

        # Initialize library manager
        self.library_manager = LibraryManager(
            library_tree=self.libraryTree,
            storage_service=self.storage_service,
            log_service=self.log_service,
            get_dark_mode=self.view.is_dark_mode,
            get_style=self.style,
            parent_widget=self,
            library_service=self.library_service,
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
            layer_state=self.layer_state,
        )

    def _build_layer_dock(self):
        """Build layer panel dock for z-order management and grouping."""
        self.layerDock = QtWidgets.QDockWidget("Layers", self)
        self.layerDock.setObjectName("layerDock")
        self.layer_panel = LayerPanel(self)
        self.layer_panel.set_scene(self.scene)
        self.layer_panel.set_layer_state(self.layer_state)
        self.layerDock.setWidget(self.layer_panel)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.layerDock)

        # Connect layer panel selection to scene selection sync
        self.scene.selectionChanged.connect(self._sync_layer_panel_selection)

        # Connect z-order changes to retrace (so rays update their z-values)
        self.layer_panel.zOrderChanged.connect(self._schedule_retrace)

        # Connect visibility changes to retrace (so hidden sources stop emitting rays)
        self.layer_panel.visibilityChanged.connect(self._schedule_retrace)

        # Set layer state on component ops for delete operations
        self.component_ops.set_layer_state(self.layer_state)

        # Initial refresh to show any existing items
        QtCore.QTimer.singleShot(100, self.layer_panel.refresh)

    def _sync_layer_panel_selection(self):
        """Sync layer panel selection when scene selection changes."""
        self.layer_panel.sync_from_scene_selection()

    def _refresh_layer_panel(self):
        """Refresh the layer panel to reflect scene changes."""
        if hasattr(self, "layer_panel"):
            self.layer_panel.refresh()

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
            layer_state=self.layer_state,
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
        """Connect standard signals for a new item (edited, commandCreated, requestDelete)."""
        # Connect edited signal for retrace and collaboration
        if isinstance(item, Editable):
            item.edited.connect(self._maybe_retrace)  # type: ignore[attr-defined]
            item.edited.connect(partial(self.collaboration_manager.broadcast_update_item, item))  # type: ignore[attr-defined]

        # Connect commandCreated signal for undo/redo (duck-type for all item types)
        if hasattr(item, "commandCreated"):
            item.commandCreated.connect(self.undo_stack.push)
        # Connect requestDelete for undoable context-menu deletion with retrace
        if hasattr(item, "requestDelete"):
            item.requestDelete.connect(self._handle_item_delete)

        # Refresh layer panel when item is added
        self._refresh_layer_panel()

    def on_drop_component(self, rec: dict, scene_pos: QtCore.QPointF):
        """Handle component drop from library (delegated to component_ops)."""
        self.component_ops.on_drop_component(rec, scene_pos)
        self._refresh_layer_panel()

    def _handle_item_delete(self, item):
        """Handle requestDelete signal from an item's context menu (undoable + retrace)."""
        from ...core.undo_commands import RemoveItemCommand

        scene = item.scene() if item else None
        if scene is None:
            return
        cmd = RemoveItemCommand(scene, item, self.component_ops._layer_state)
        self.undo_stack.push(cmd)
        self._schedule_retrace()
        self._refresh_layer_panel()

    def delete_selected(self):
        """Delete selected items — routes to layer panel when it has focus."""
        if self.layer_panel.has_tree_focus():
            self.layer_panel._delete_selected()
        else:
            self.component_ops.delete_selected()
        self._refresh_layer_panel()

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
        self._refresh_layer_panel()

    def _do_undo(self):
        """Undo last action and retrace rays."""
        self.undo_stack.undo()
        self._schedule_retrace()
        self._refresh_layer_panel()

    def _do_redo(self):
        """Redo last undone action and retrace rays."""
        self.undo_stack.redo()
        self._schedule_retrace()
        self._refresh_layer_panel()

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
    def ray_data(self) -> list[Any]:
        """Get ray data from controller."""
        return self.raytracing_controller.ray_data  # type: ignore[no-any-return]

    @property
    def autotrace(self) -> bool:
        """Get autotrace enabled state from controller."""
        return self.raytracing_controller.autotrace  # type: ignore[no-any-return]

    @autotrace.setter
    def autotrace(self, value: bool) -> None:
        """Set autotrace enabled state on controller."""
        self.raytracing_controller.autotrace = value

    @property
    def _ray_width_px(self) -> float:
        """Get ray width from controller."""
        return self.raytracing_controller.ray_width_px  # type: ignore[no-any-return]

    @_ray_width_px.setter
    def _ray_width_px(self, value: float) -> None:
        """Set ray width on controller."""
        self.raytracing_controller.ray_width_px = value

    # ----- Getter methods for handlers (replaces lambda callbacks) -----
    def _get_ray_data(self) -> list[Any]:
        """Get ray data - used by handlers instead of lambda."""
        return self.raytracing_controller.ray_data  # type: ignore[no-any-return]

    def _get_snap_to_grid(self) -> bool:
        """Get snap to grid state - used by handlers instead of lambda."""
        return self.snap_to_grid  # type: ignore[no-any-return]

    def _set_paste_enabled(self, enabled: bool) -> None:
        """Set paste action enabled state - used by handlers instead of lambda."""
        self.act_paste.setEnabled(enabled)

    def _on_clipboard_changed(self) -> None:
        """Re-evaluate paste action when the system clipboard changes."""
        self.act_paste.setEnabled(self.component_ops.has_clipboard_items)

    def _on_path_measure_complete(self) -> None:
        """Called when path measure tool completes - used instead of lambda."""
        self.act_measure_path.setChecked(False)

    def _on_angle_measure_complete(self) -> None:
        """Called when angle measure tool completes - used instead of lambda."""
        self.act_measure_angle.setChecked(False)

    # ----- Save / Load (delegated to FileController) -----
    def new_assembly(self):
        """Create new assembly (delegated to file controller)."""
        if self.file_controller.new_assembly():
            # Refresh layer panel
            self.layer_panel.refresh()

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
                    item.edited.connect(self._maybe_retrace)  # type: ignore[attr-defined]
            # Refresh layer panel
            self.layer_panel.refresh()

    def open_recent_file(self, path: str):
        """Open a recent file (delegated to file controller)."""
        if self.file_controller.open_recent_file(path):
            # Connect edited signal for optical components
            for item in self.scene.items():
                if isinstance(item, Editable):
                    item.edited.connect(self._maybe_retrace)  # type: ignore[attr-defined]
            # Refresh layer panel
            self.layer_panel.refresh()

    def close_assembly(self):
        """Close current assembly (delegated to file controller)."""
        if self.file_controller.close_assembly():
            # Refresh layer panel
            self.layer_panel.refresh()

    def export_image(self):
        """Export scene to image (delegated to file controller)."""
        self.file_controller.export_image()

    def export_pdf(self):
        """Export scene to PDF (delegated to file controller)."""
        self.file_controller.export_pdf()

    def export_pyopticl(self):
        """Export scene to PyOpticL script (delegated to file controller)."""
        self.file_controller.export_pyopticl()

    def quit_application(self):
        """Quit the application (triggers close event which handles unsaved changes)."""
        self.close()

    def link_assembly(self):
        """Link an external assembly file (reference, not copy)."""
        if self.file_controller.link_assembly():
            for item in self.scene.items():
                if isinstance(item, Editable):
                    try:
                        item.edited.disconnect(self._maybe_retrace)  # type: ignore[attr-defined]
                    except TypeError:
                        pass
                    item.edited.connect(self._maybe_retrace)  # type: ignore[attr-defined]
            self.layer_panel.refresh()

    def import_assembly_as_layer(self):
        """Import an assembly file as a new layer (grouped items)."""
        if self.file_controller.import_as_layer():
            # Connect edited signal for newly imported optical components
            for item in self.scene.items():
                if isinstance(item, Editable):
                    # Only connect if not already connected
                    try:
                        item.edited.disconnect(self._maybe_retrace)  # type: ignore[attr-defined]
                    except TypeError:
                        pass
                    item.edited.connect(self._maybe_retrace)  # type: ignore[attr-defined]
            # Refresh layer panel
            self.layer_panel.refresh()

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
        # Refresh toolbar icons for new theme
        self.action_builder.refresh_toolbar_icons(on)
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

    def open_component_editor(self, component_data: dict | None = None):
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
        self._comp_editor = ComponentEditorDialog(
            self.storage_service, parent=None, library_service=self.library_service,
        )
        self._comp_editor._main_window = self
        self._comp_editor.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        # Connect saved signal to reload library (saved is always a signal on ComponentEditorDialog)
        self._comp_editor.saved.connect(self.populate_library)
        # Load component data if provided
        if component_data is not None:
            self._comp_editor._load_from_dict(component_data)
        self._comp_editor.show()

    def open_component_editor_for_item(self, item):
        """Open the Component Editor pre-loaded with *item*'s data.

        When the user saves inside the editor the library is updated (normal
        behaviour) **and** the placed scene instance is updated in-place so
        the canvas reflects the changes immediately.
        """
        from ...core.undo_commands import PropertyChangeCommand
        from ...objects.generic.component_item import ComponentItem

        if not isinstance(item, ComponentItem):
            return

        component_data = item.to_component_dict()
        baseline_state = item.capture_state()

        self.open_component_editor(component_data)

        if self._comp_editor is None:
            return

        def _apply_back():
            """Read the editor's current record and push changes to the placed item."""
            nonlocal baseline_state
            editor = self._comp_editor
            if editor is None:
                return
            rec = editor._build_record_from_ui()
            if rec is None:
                return

            apply_record_to_component_item(
                item, rec, self.storage_service.settings_service
            )

            final_state = item.capture_state()
            if baseline_state != final_state:
                cmd = PropertyChangeCommand(item, baseline_state, final_state)
                self.undo_stack.push(cmd)
                baseline_state = final_state
            self._schedule_retrace()

        self._comp_editor.saved.connect(_apply_back)

    def update_canvas_instances_from_component_editor(self, editor) -> None:
        """Update every placed ComponentItem whose name matches the editor's current record.

        Shows a confirmation dialog first. Uses one batch undo command for all changes.
        """
        from ...core.undo_commands import BatchPropertyChangeCommand
        from ...objects.generic.component_item import ComponentItem

        rec = editor._build_record_from_ui()
        if rec is None:
            return

        key = normalized_component_name(rec.name)
        if not key:
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Update canvas instances",
            (
                f"This will change the main canvas.\n\n"
                f'All placed components named "{rec.name}" will be updated to match '
                "the definition in this editor (interfaces, image, size, notes, "
                "and related fields).\n\n"
                "Each instance keeps its position, rotation, z-order, and lock state.\n\n"
                "Do you want to continue?"
            ),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        targets = [
            it
            for it in self.scene.items()
            if isinstance(it, ComponentItem)
            and normalized_component_name(it.params.name) == key
        ]
        if not targets:
            QtWidgets.QMessageBox.information(
                self,
                "Update canvas instances",
                f'No placed components named "{rec.name}" were found on the canvas.',
            )
            return

        entries: list = []
        for item in targets:
            old_state = item.capture_state()
            apply_record_to_component_item(
                item, rec, self.storage_service.settings_service
            )
            new_state = item.capture_state()
            if old_state != new_state:
                entries.append((item, old_state, new_state))

        if entries:
            cmd = BatchPropertyChangeCommand(entries)
            self.undo_stack.push(cmd)
        self._schedule_retrace()

    def apply_component_properties_to_all(self, source_item):
        """Open the Apply-Properties-to-All dialog for *source_item*."""
        from ...core.undo_commands import BatchPropertyChangeCommand
        from ...objects.generic.component_item import ComponentItem
        from .apply_properties_dialog import ApplyPropertiesToAllDialog

        all_components = [
            item
            for item in self.scene.items()
            if isinstance(item, ComponentItem)
        ]

        if len(all_components) < 2:
            QtWidgets.QMessageBox.information(
                self,
                "Apply Properties",
                "There are no other components on the canvas to apply to.",
            )
            return

        dlg = ApplyPropertiesToAllDialog(source_item, all_components, self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        targets = dlg.get_targets()
        checked = dlg.get_checked_properties()
        if not targets:
            return

        active_keys = [k for k, v in checked.items() if v]
        if not active_keys:
            return

        entries: list[tuple] = []
        for target in targets:
            old_state = target.capture_state()
            self._apply_properties(source_item, target, active_keys)
            new_state = target.capture_state()
            if old_state != new_state:
                entries.append((target, old_state, new_state))

        if entries:
            cmd = BatchPropertyChangeCommand(entries)
            self.undo_stack.push(cmd)
            self._schedule_retrace()

    @staticmethod
    def _apply_properties(source, target, active_keys: list[str]):
        """Copy checked properties from *source* to *target* ComponentItem."""
        if "object_height_mm" in active_keys:
            target.params.object_height_mm = source.params.object_height_mm

        if not source.params.interfaces or not target.params.interfaces:
            target._update_geom()
            target._maybe_attach_sprite()
            target.edited.emit()
            return

        iface_keys = [k for k in active_keys if ":" in k]
        for src_iface, tgt_iface in zip(
            source.params.interfaces, target.params.interfaces, strict=True
        ):
            for key in iface_keys:
                et, prop = key.split(":", 1)
                if src_iface.element_type == et and tgt_iface.element_type == et:
                    if hasattr(tgt_iface, prop):
                        setattr(tgt_iface, prop, getattr(src_iface, prop))

        target._update_geom()
        target._maybe_attach_sprite()
        target.edited.emit()

    def open_user_library_folder(self):
        """Open the user library folder in the system file explorer."""
        from ...platform.paths import get_user_library_root

        self._open_folder(str(get_user_library_root()))

    def _open_folder(self, path: str):
        """Open *path* in the platform's file manager."""
        import subprocess
        import sys

        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except (OSError, subprocess.SubprocessError) as e:
            QtWidgets.QMessageBox.information(
                self,
                "Library Location",
                f"Location:\n{path}\n\n"
                f"(Could not open folder automatically: {e})",
            )

    def _populate_open_library_menu(self):
        """Rebuild the 'Open Library Folder' submenu with all known libraries."""
        menu = self.open_library_menu  # type: ignore[attr-defined]
        menu.clear()
        for lib in self.library_service.get_all():
            if not lib.exists:
                continue
            label = f"{lib.name}  ({lib.source_type})"
            if not lib.enabled:
                label += "  [disabled]"
            action = menu.addAction(label)
            action.setEnabled(lib.enabled)
            path_str = str(lib.path)
            action.triggered.connect(lambda checked, p=path_str: self._open_folder(p))

    def open_preferences(self):
        """Open preferences/settings dialog."""
        from .settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.settings_service, self, library_service=self.library_service)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self):
        """Handle settings changes from the Preferences dialog."""
        from ...core import preferences
        from ...core.preferences import load_from_settings

        load_from_settings(self.settings_service)

        # -- Library --
        self.library_service.refresh()

        # -- Appearance --
        new_dark = self.settings_service.get_value(
            "dark_mode", self.view.is_dark_mode(), bool
        )
        if new_dark != self.view.is_dark_mode():
            self._toggle_dark_mode(new_dark)
            self.act_dark_mode.setChecked(new_dark)
        self.view.show_scale_bar = preferences.show_scale_bar
        self.view.viewport().update()

        # -- Canvas & Editing --
        self.snap_to_grid = self.settings_service.get_value(
            "canvas/snap_to_grid", False, bool
        )
        self.act_snap.setChecked(self.snap_to_grid)

        self.magnetic_snap = self.settings_service.get_value("magnetic_snap", True, bool)
        self.act_magnetic_snap.setChecked(self.magnetic_snap)
        self._snap_helper.tolerance_px = preferences.magnetic_snap_tolerance_px

        autotrace_pref = self.settings_service.get_value("canvas/autotrace", True, bool)
        self.autotrace = autotrace_pref
        self.act_autotrace.setChecked(autotrace_pref)

        ray_width_pref = self.settings_service.get_value(
            "canvas/default_ray_width_px", 2.0, float
        )
        self._ray_width_px = ray_width_pref
        for act in self._raywidth_group.actions():
            act.setChecked(abs(float(act.text().split()[0]) - ray_width_pref) < 1e-9)

        self.raytracing_controller.max_events = preferences.max_raytracing_events

        # -- Autosave --
        if preferences.autosave_enabled:
            self.file_controller.set_autosave_interval(preferences.autosave_interval_ms)
        else:
            self.file_controller.disable_autosave()

        self._schedule_retrace()
        self.log_service.info("Settings updated", "Settings")

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

        super().keyPressEvent(ev)

    def _nudge_selected(self, key: int, shift: bool) -> None:
        """Move selected items by arrow key (connected to GraphicsView.nudgeRequested)."""
        from ...core import preferences
        from ...core.undo_commands import MoveItemCommand
        from ...objects import BaseObj
        from ...objects.annotations import RulerItem
        from ...objects.annotations.rectangle_item import RectangleItem
        from ...objects.annotations.text_note_item import TextNoteItem

        selected = [
            it for it in self.scene.selectedItems()
            if isinstance(it, (BaseObj, RulerItem, TextNoteItem, RectangleItem))
        ]
        if not selected:
            return

        step = preferences.nudge_large_mm if shift else preferences.nudge_small_mm

        dx, dy = 0.0, 0.0
        if key == QtCore.Qt.Key.Key_Left:
            dx = -step
        elif key == QtCore.Qt.Key.Key_Right:
            dx = step
        elif key == QtCore.Qt.Key.Key_Up:
            dy = step
        elif key == QtCore.Qt.Key.Key_Down:
            dy = -step

        for item in selected:
            old_pos = item.pos()
            new_pos = QtCore.QPointF(old_pos.x() + dx, old_pos.y() + dy)
            cmd = MoveItemCommand(item, old_pos, new_pos)
            self.undo_stack.push(cmd)

        self._schedule_retrace()

    @staticmethod
    def _format_coord(mm_val: float, px_per_mm: float) -> str:
        """Format a coordinate value with zoom-appropriate units."""
        mm_per_px = 1.0 / max(px_per_mm, 1e-12)
        if mm_per_px < 0.001:
            return f"{mm_val * 1e6:.1f}"
        elif mm_per_px < 1.0:
            return f"{mm_val * 1e3:.2f}"
        else:
            return f"{mm_val:.2f}"

    @staticmethod
    def _coord_unit(px_per_mm: float) -> str:
        mm_per_px = 1.0 / max(px_per_mm, 1e-12)
        if mm_per_px < 0.001:
            return "nm"
        elif mm_per_px < 1.0:
            return "\u00b5m"
        return "mm"

    def _update_coord_label(self, pos: QtCore.QPointF) -> None:
        """Update the status bar coordinate display with zoom-aware units."""
        label = getattr(self, "coord_label", None)
        if label is None:
            return
        px_per_mm = abs(self.view.transform().m11())
        unit = self._coord_unit(px_per_mm)
        x_str = self._format_coord(pos.x(), px_per_mm)
        y_str = self._format_coord(pos.y(), px_per_mm)
        label.setText(f"X: {x_str}  Y: {y_str} {unit}")

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
    def closeEvent(self, e: QtGui.QCloseEvent | None):
        # Check for unsaved changes (skip dialog in offscreen/test mode)
        import os

        if self.file_controller.is_modified and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            reply = self.file_controller.prompt_save_changes()
            if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                if e is not None:
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

            # Clean up layer panel to prevent accessing deleted items
            if hasattr(self, "layer_panel"):
                self.layer_panel.cleanup()
        except (OSError, RuntimeError):
            # Ignore cleanup errors during shutdown
            pass
        super().closeEvent(e)
