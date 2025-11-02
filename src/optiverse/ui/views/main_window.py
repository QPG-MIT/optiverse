from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import (
    BeamsplitterParams,
    DichroicParams,
    LensParams,
    MirrorParams,
    SLMParams,
    WaveplateParams,
    RefractiveObjectParams,
    OpticalElement,
    SourceParams,
)
from ...core.snap_helper import SnapHelper
from ...core.undo_commands import AddItemCommand, MoveItemCommand, RemoveItemCommand, RemoveMultipleItemsCommand, PasteItemsCommand, RotateItemCommand, RotateItemsCommand
from ...core.undo_stack import UndoStack
from ...core.use_cases import trace_rays
from ...services.settings_service import SettingsService
from ...services.storage_service import StorageService
from ...services.collaboration_manager import CollaborationManager
from ...services.log_service import get_log_service
from .collaboration_dialog import CollaborationDialog
from .log_window import LogWindow
from ...objects import (
    BeamsplitterItem,
    DichroicItem,
    GraphicsView,
    LensItem,
    MirrorItem,
    RefractiveObjectItem,
    SLMItem,
    WaveplateItem,
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


class LibraryTree(QtWidgets.QTreeWidget):
    """Drag-enabled library tree for component templates organized by category."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIconSize(QtCore.QSize(64, 64))
        self.setDragEnabled(True)
        self.setSelectionMode(QtWidgets.QTreeWidget.SelectionMode.SingleSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(QtCore.Qt.DropAction.CopyAction)
        self.setIndentation(20)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Expand all categories by default
        self.expandAll()
    
    def _show_context_menu(self, position):
        """Show context menu for component items."""
        item = self.itemAt(position)
        if not item:
            return
        
        # Only show context menu for leaf items (components), not category headers
        if item.childCount() > 0:
            return
        
        payload = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not payload:
            return
        
        # Create context menu
        menu = QtWidgets.QMenu(self)
        edit_action = menu.addAction("Edit Component")
        edit_action.triggered.connect(lambda: self._edit_component(payload))
        
        # Show menu at cursor position
        menu.exec(self.viewport().mapToGlobal(position))
    
    def _edit_component(self, component_data: dict):
        """Open component editor with the selected component loaded."""
        # Get the main window parent
        main_window = self.window()
        if hasattr(main_window, 'open_component_editor_with_data'):
            main_window.open_component_editor_with_data(component_data)

    def startDrag(self, actions):
        it = self.currentItem()
        if not it:
            return
        
        # Only allow dragging leaf items (components), not category headers
        if it.childCount() > 0:
            return
            
        payload = it.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not payload:
            return
            
        md = QtCore.QMimeData()
        md.setData("application/x-optics-component", json.dumps(payload).encode("utf-8"))
        drag = QtGui.QDrag(self)
        drag.setMimeData(md)
        
        # Set an empty 1x1 transparent pixmap to prevent Qt from creating a default drag cursor
        # The ghost preview in GraphicsView provides the visual feedback
        empty_pixmap = QtGui.QPixmap(1, 1)
        empty_pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        drag.setPixmap(empty_pixmap)
        drag.setHotSpot(QtCore.QPoint(0, 0))
        
        # Execute drag and clear selection afterwards
        result = drag.exec(QtCore.Qt.DropAction.CopyAction)
        if result == QtCore.Qt.DropAction.CopyAction:
            self.clearSelection()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D Ray Optics Sandbox — Top View (mm/cm grid)")
        self.resize(1450, 860)
        
        # Set window icon
        icon_path = _get_icon_path("optiverse.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        # Scene and view
        self.scene = QtWidgets.QGraphicsScene(self)
        # Effectively "infinite" scene: 1 million x 1 million mm (1 km x 1 km)
        # This provides unlimited scrollable area for panning at any zoom level
        # Centered at origin for optical bench convention
        self.scene.setSceneRect(-500000, -500000, 1000000, 1000000)
        self.view = GraphicsView(self.scene)
        self.view.parent = lambda: self  # For dropEvent callback
        self.setCentralWidget(self.view)

        # State variables
        self.snap_to_grid = True
        self._ray_width_px = 2.0
        self.ray_items: list[QtWidgets.QGraphicsPathItem] = []
        self.ray_data: list = []  # Store RayPath data for each ray item
        self.autotrace = True
        self._pipet_mode = False  # Track if pipet tool is active
        
        # Component placement mode
        self._placement_mode = False  # Track if component placement mode is active
        self._placement_type = None  # Type of component being placed ("source", "lens", "mirror", "beamsplitter", "waveplate", "text")
        self._placement_ghost = None  # Ghost item for preview
        
        # NEW: Feature flag for polymorphic raytracing engine
        # Set to True to use new polymorphic system (Phase 1-3 complete)
        # Set to False to use legacy system (backward compatibility)
        self._use_polymorphic_raytracing = False  # Default: False for safety
        
        # Grid now drawn in GraphicsView.drawBackground() for better performance
        
        # Snap helper for magnetic alignment
        self._snap_helper = SnapHelper(tolerance_px=10.0)

        # Ruler placement mode
        self._placing_ruler = False
        self._ruler_p1_scene: QtCore.QPointF | None = None
        self._prev_cursor = None

        # Undo/Redo tracking
        self._item_positions: dict[QtWidgets.QGraphicsItem, QtCore.QPointF] = {}
        self._item_rotations: dict[QtWidgets.QGraphicsItem, float] = {}
        self._item_group_states: dict = {}  # For group rotation tracking

        # Services
        self.storage_service = StorageService()
        self.settings_service = SettingsService()
        self.undo_stack = UndoStack()
        self.collaboration_manager = CollaborationManager(self)
        self.log_service = get_log_service()
        self.log_service.debug("MainWindow.__init__ called", "Init")
        self.collab_server_process = None  # Track hosted server process
        
        # Initialize clipboard for copy/paste
        self._clipboard = []
        self.log_service.debug("Clipboard initialized", "Copy/Paste")
        
        # Track unsaved changes
        self._is_modified = False
        self._saved_file_path = None  # Track current file for save vs save-as
        
        # Load saved preferences
        self.magnetic_snap = self.settings_service.get_value("magnetic_snap", True, bool)
        
        # Load dark mode preference and apply theme to match
        dark_mode_saved = self.settings_service.get_value("dark_mode", self.view.is_dark_mode(), bool)
        self.view.set_dark_mode(dark_mode_saved)
        # Apply theme to ensure app-wide styling matches the saved preference
        from ...app.main import apply_theme
        apply_theme(dark_mode_saved)
        
        # Connect collaboration signals
        self.collaboration_manager.remote_item_added.connect(self._on_remote_item_added)
        self.collaboration_manager.status_changed.connect(self._on_collaboration_status_changed)

        # Build UI
        self._build_actions()
        self._build_toolbar()
        self._build_menubar()
        self._build_library_dock()
        
        # Add actions with shortcuts to main window so they work globally
        self._register_shortcuts()

        # Install event filter for snap and ruler placement
        self.scene.installEventFilter(self)
        # Grid is now drawn automatically in GraphicsView.drawBackground()

    # Grid is now drawn in GraphicsView.drawBackground() for much better performance
    # No need for _draw_grid() method anymore!

    def _connect_modification_tracking(self):
        """Connect signals to track when canvas is modified."""
        # Use a custom signal handler to mark modified on push
        original_push = self.undo_stack.push
        def tracked_push(command):
            original_push(command)
            self._mark_modified()
        self.undo_stack.push = tracked_push

    def _mark_modified(self):
        """Mark the canvas as having unsaved changes."""
        if not self._is_modified:
            self._is_modified = True
            self._update_window_title()

    def _mark_clean(self):
        """Mark the canvas as saved (no unsaved changes)."""
        if self._is_modified:
            self._is_modified = False
            self._update_window_title()

    def _update_window_title(self):
        """Update window title to show file name and modified state."""
        title = "2D Ray Optics Sandbox — Top View (mm/cm grid)"
        if self._saved_file_path:
            import os
            filename = os.path.basename(self._saved_file_path)
            title = f"{filename} - {title}"
        if self._is_modified:
            title = f"*{title}"
        self.setWindowTitle(title)

    def _prompt_save_changes(self):
        """
        Prompt user to save unsaved changes.
        
        Returns:
            QMessageBox.StandardButton: The user's choice (Save, Discard, or Cancel)
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            "Unsaved Changes",
            "Do you want to save your changes before closing?",
            QtWidgets.QMessageBox.StandardButton.Save |
            QtWidgets.QMessageBox.StandardButton.Discard |
            QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Save
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Save:
            # Save the file
            self.save_assembly()
            # Check if save was successful (user didn't cancel the save dialog)
            if self._is_modified:
                # User cancelled the save dialog, treat as cancel
                return QtWidgets.QMessageBox.StandardButton.Cancel
        
        return reply

    def _build_actions(self):
        """Build all menu actions."""
        # --- File ---
        self.act_open = QtGui.QAction("Open Assembly…", self)
        self.act_open.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self.act_open.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_open.triggered.connect(self.open_assembly)

        self.act_save = QtGui.QAction("Save Assembly…", self)
        self.act_save.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        self.act_save.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_save.triggered.connect(self.save_assembly)

        # --- Edit ---
        self.act_undo = QtGui.QAction("Undo", self)
        self.act_undo.setShortcut(QtGui.QKeySequence("Ctrl+Z"))
        self.act_undo.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_undo.triggered.connect(self._do_undo)
        self.act_undo.setEnabled(False)

        self.act_redo = QtGui.QAction("Redo", self)
        self.act_redo.setShortcut(QtGui.QKeySequence("Ctrl+Y"))
        self.act_redo.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_redo.triggered.connect(self._do_redo)
        self.act_redo.setEnabled(False)

        self.act_delete = QtGui.QAction("Delete", self)
        self.act_delete.setShortcuts([QtGui.QKeySequence.StandardKey.Delete, QtGui.QKeySequence(QtCore.Qt.Key.Key_Backspace)])
        self.act_delete.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_delete.triggered.connect(self.delete_selected)

        self.act_copy = QtGui.QAction("Copy", self)
        self.act_copy.setShortcut(QtGui.QKeySequence("Ctrl+C"))
        self.act_copy.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_copy.triggered.connect(self.copy_selected)

        self.act_paste = QtGui.QAction("Paste", self)
        self.act_paste.setShortcut(QtGui.QKeySequence("Ctrl+V"))
        self.act_paste.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_paste.triggered.connect(self.paste_items)
        self.act_paste.setEnabled(False)

        # Connect undo stack signals to update action states
        self.undo_stack.canUndoChanged.connect(self.act_undo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.act_redo.setEnabled)
        
        # Mark canvas as modified when commands are pushed
        # Note: We'll connect this after initialization
        self._connect_modification_tracking()

        # --- Insert ---
        # Component placement actions - now checkable to enter placement mode
        self.act_add_source = QtGui.QAction("Source", self, checkable=True)
        self.act_add_source.toggled.connect(lambda on: self._toggle_placement_mode("source", on))

        self.act_add_lens = QtGui.QAction("Lens", self, checkable=True)
        self.act_add_lens.toggled.connect(lambda on: self._toggle_placement_mode("lens", on))

        self.act_add_mirror = QtGui.QAction("Mirror", self, checkable=True)
        self.act_add_mirror.toggled.connect(lambda on: self._toggle_placement_mode("mirror", on))

        self.act_add_bs = QtGui.QAction("Beamsplitter", self, checkable=True)
        self.act_add_bs.toggled.connect(lambda on: self._toggle_placement_mode("beamsplitter", on))

        self.act_add_ruler = QtGui.QAction("Ruler", self)
        self.act_add_ruler.triggered.connect(self.start_place_ruler)

        self.act_add_text = QtGui.QAction("Text", self, checkable=True)
        self.act_add_text.toggled.connect(lambda on: self._toggle_placement_mode("text", on))
        
        self.act_add_rectangle = QtGui.QAction("Rectangle", self, checkable=True)
        self.act_add_rectangle.toggled.connect(lambda on: self._toggle_placement_mode("rectangle", on))

        # --- Tools ---
        self.act_pipet = QtGui.QAction("Pipet", self, checkable=True)
        self.act_pipet.setChecked(False)
        self.act_pipet.toggled.connect(self._toggle_pipet)

        # --- View ---
        self.act_zoom_in = QtGui.QAction("Zoom In", self)
        self.act_zoom_in.setShortcut(QtGui.QKeySequence.StandardKey.ZoomIn)
        self.act_zoom_in.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_zoom_in.triggered.connect(lambda: (self.view.scale(1.15, 1.15), self.view.zoomChanged.emit()))

        self.act_zoom_out = QtGui.QAction("Zoom Out", self)
        self.act_zoom_out.setShortcut(QtGui.QKeySequence.StandardKey.ZoomOut)
        self.act_zoom_out.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_zoom_out.triggered.connect(lambda: (self.view.scale(1 / 1.15, 1 / 1.15), self.view.zoomChanged.emit()))

        self.act_fit = QtGui.QAction("Fit Scene", self)
        self.act_fit.setShortcut("Ctrl+0")
        self.act_fit.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_fit.triggered.connect(
            lambda: (
                self.view.fitInView(
                    self.scene.itemsBoundingRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio
                ),
                self.view.zoomChanged.emit(),
            )
        )

        # Checkable options
        self.act_autotrace = QtGui.QAction("Auto-trace", self, checkable=True)
        self.act_autotrace.setChecked(True)
        self.act_autotrace.toggled.connect(self._toggle_autotrace)

        self.act_snap = QtGui.QAction("Snap to mm grid", self, checkable=True)
        self.act_snap.setChecked(True)
        self.act_snap.toggled.connect(self._toggle_snap)

        self.act_magnetic_snap = QtGui.QAction("Magnetic snap", self, checkable=True)
        self.act_magnetic_snap.setChecked(self.magnetic_snap)
        self.act_magnetic_snap.toggled.connect(self._toggle_magnetic_snap)
        
        # Dark mode toggle
        self.act_dark_mode = QtGui.QAction("Dark mode", self, checkable=True)
        self.act_dark_mode.setChecked(self.view.is_dark_mode())
        self.act_dark_mode.toggled.connect(self._toggle_dark_mode)

        # Ray width submenu with presets + Custom…
        self.menu_raywidth = QtWidgets.QMenu("Ray width", self)
        self._raywidth_group = QtGui.QActionGroup(self)
        self._raywidth_group.setExclusive(True)
        for v in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]:
            a = self.menu_raywidth.addAction(f"{v:.1f} px")
            a.setCheckable(True)
            if abs(v - self._ray_width_px) < 1e-9:
                a.setChecked(True)
            a.triggered.connect(lambda _, vv=v: self._set_ray_width(vv))
            self._raywidth_group.addAction(a)
        self.menu_raywidth.addSeparator()
        a_custom = self.menu_raywidth.addAction("Custom…")
        a_custom.triggered.connect(self._choose_ray_width)

        # --- Tools ---
        self.act_retrace = QtGui.QAction("Retrace", self)
        self.act_retrace.setShortcut("Space")
        self.act_retrace.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_retrace.triggered.connect(self.retrace)

        self.act_clear = QtGui.QAction("Clear Rays", self)
        self.act_clear.triggered.connect(self.clear_rays)

        self.act_editor = QtGui.QAction("Component Editor…", self)
        self.act_editor.setShortcut("Ctrl+E")
        self.act_editor.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_editor.triggered.connect(self.open_component_editor)

        self.act_reload = QtGui.QAction("Reload Library", self)
        self.act_reload.triggered.connect(self.populate_library)
        
        self.act_show_log = QtGui.QAction("Show Log Window...", self)
        self.act_show_log.setShortcut("Ctrl+L")
        self.act_show_log.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_show_log.triggered.connect(self.show_log_window)
        
        # --- Collaboration ---
        self.act_collaborate = QtGui.QAction("Connect/Host Session…", self)
        self.act_collaborate.setShortcut("Ctrl+Shift+C")
        self.act_collaborate.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_collaborate.triggered.connect(self.open_collaboration_dialog)
        
        self.act_disconnect = QtGui.QAction("Disconnect", self)
        self.act_disconnect.setEnabled(False)
        self.act_disconnect.triggered.connect(self.disconnect_collaboration)

    def _build_toolbar(self):
        """Build component toolbar with custom PNG icons."""
        toolbar = QtWidgets.QToolBar("Components")
        toolbar.setObjectName("component_toolbar")
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        toolbar.setIconSize(QtCore.QSize(32, 32))
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, toolbar)
        
        # Add styling for checked/active tool buttons to make them visually distinct
        # Using box-shadow instead of border to avoid resizing the toolbar
        toolbar.setStyleSheet("""
            QToolButton {
                padding: 2px;
                border: 2px solid transparent;
                border-radius: 4px;
                color: palette(window-text);
            }
            QToolButton:checked {
                background-color: rgba(100, 150, 255, 100);
                border: 2px solid rgba(100, 150, 255, 180);
                border-radius: 4px;
                color: palette(window-text);
            }
            QToolButton:checked:hover {
                background-color: rgba(100, 150, 255, 120);
                border: 2px solid rgba(100, 150, 255, 200);
                color: palette(window-text);
            }
        """)

        # Source button
        source_icon = QtGui.QIcon(_get_icon_path("source.png"))
        self.act_add_source.setIcon(source_icon)
        toolbar.addAction(self.act_add_source)

        # Lens button
        lens_icon = QtGui.QIcon(_get_icon_path("lens.png"))
        self.act_add_lens.setIcon(lens_icon)
        toolbar.addAction(self.act_add_lens)

        # Mirror button
        mirror_icon = QtGui.QIcon(_get_icon_path("mirror.png"))
        self.act_add_mirror.setIcon(mirror_icon)
        toolbar.addAction(self.act_add_mirror)

        # Beamsplitter button
        bs_icon = QtGui.QIcon(_get_icon_path("beamsplitter.png"))
        self.act_add_bs.setIcon(bs_icon)
        toolbar.addAction(self.act_add_bs)

        toolbar.addSeparator()

        # Ruler button
        ruler_icon = QtGui.QIcon(_get_icon_path("ruler.png"))
        self.act_add_ruler.setIcon(ruler_icon)
        toolbar.addAction(self.act_add_ruler)

        # Pipet button
        pipet_icon = QtGui.QIcon(_get_icon_path("pipet.png"))
        self.act_pipet.setIcon(pipet_icon)
        toolbar.addAction(self.act_pipet)

        # Text button
        text_icon = QtGui.QIcon(_get_icon_path("text.png"))
        self.act_add_text.setIcon(text_icon)
        toolbar.addAction(self.act_add_text)

        # Rectangle button
        rect_icon = QtGui.QIcon(_get_icon_path("rectangle.png"))
        self.act_add_rectangle.setIcon(rect_icon)
        toolbar.addAction(self.act_add_rectangle)

    def _build_menubar(self):
        """Build menu bar."""
        mb = self.menuBar()

        # File menu
        mFile = mb.addMenu("&File")
        mFile.addAction(self.act_open)
        mFile.addAction(self.act_save)

        # Edit menu
        mEdit = mb.addMenu("&Edit")
        mEdit.addAction(self.act_undo)
        mEdit.addAction(self.act_redo)
        mEdit.addSeparator()
        mEdit.addAction(self.act_copy)
        mEdit.addAction(self.act_paste)
        mEdit.addSeparator()
        mEdit.addAction(self.act_delete)

        # Insert menu (Phase 3.2: Better menu organization)
        mInsert = mb.addMenu("&Insert")
        mInsert.addAction(self.act_add_source)
        mInsert.addAction(self.act_add_lens)
        mInsert.addAction(self.act_add_mirror)
        mInsert.addAction(self.act_add_bs)
        mInsert.addSeparator()
        mInsert.addAction(self.act_add_ruler)
        mInsert.addAction(self.act_add_text)
        mInsert.addAction(self.act_add_rectangle)

        # View menu
        mView = mb.addMenu("&View")
        mView.addAction(self.act_zoom_in)
        mView.addAction(self.act_zoom_out)
        mView.addAction(self.act_fit)
        mView.addSeparator()
        mView.addAction(self.act_autotrace)
        mView.addAction(self.act_snap)
        mView.addAction(self.act_magnetic_snap)
        mView.addSeparator()
        mView.addAction(self.act_dark_mode)
        mView.addSeparator()
        mView.addMenu(self.menu_raywidth)

        # Tools menu
        mTools = mb.addMenu("&Tools")
        mTools.addAction(self.act_retrace)
        mTools.addAction(self.act_clear)
        mTools.addSeparator()
        mTools.addAction(self.act_pipet)
        mTools.addSeparator()
        mTools.addAction(self.act_editor)
        mTools.addAction(self.act_reload)
        mTools.addSeparator()
        mTools.addAction(self.act_show_log)
        
        # Collaboration menu
        mCollab = mb.addMenu("&Collaboration")
        mCollab.addAction(self.act_collaborate)
        mCollab.addAction(self.act_disconnect)
        
        # Add collaboration status to status bar
        self.collab_status_label = QtWidgets.QLabel("Not connected")
        self.statusBar().addPermanentWidget(self.collab_status_label)

    def _build_library_dock(self):
        """Build component library dock with categorized tree view."""
        self.libDock = QtWidgets.QDockWidget("Component Library", self)
        self.libDock.setObjectName("libDock")
        self.libraryTree = LibraryTree(self)
        self.libDock.setWidget(self.libraryTree)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.libDock)
        self.populate_library()

    def _register_shortcuts(self):
        """Register actions with shortcuts to main window for global access.
        
        This ensures keyboard shortcuts work even when child widgets have focus.
        """
        # File actions
        self.addAction(self.act_open)
        self.addAction(self.act_save)
        
        # Edit actions
        self.addAction(self.act_undo)
        self.addAction(self.act_redo)
        self.addAction(self.act_delete)
        self.addAction(self.act_copy)
        self.addAction(self.act_paste)
        
        # View actions
        self.addAction(self.act_zoom_in)
        self.addAction(self.act_zoom_out)
        self.addAction(self.act_fit)
        
        # Tools actions
        self.addAction(self.act_retrace)
        self.addAction(self.act_editor)
        self.addAction(self.act_show_log)
        
        # Collaboration actions
        self.addAction(self.act_collaborate)

    def populate_library(self):
        """Load and populate component library organized by category."""
        self.libraryTree.clear()
        
        # Ensure standard components are loaded
        self.storage_service.ensure_standard_components()
        
        # Load components from storage
        records = self.storage_service.load_library()
        
        # Organize by category
        from ...objects.component_registry import ComponentRegistry
        categories = {
            "Lenses": [],
            "Objectives": [],
            "Mirrors": [],
            "Beamsplitters": [],
            "Dichroics": [],
            "Waveplates": [],
            "Sources": [],
            "Background": [],
            "Misc": [],
            "Other": []
        }
        
        for rec in records:
            name = rec.get("name", "")
            
            # Check for explicit category field first (preferred method)
            if "category" in rec:
                category_key = rec["category"].lower()
                # Map to UI category names
                category_map = {
                    "lenses": "Lenses",
                    "objectives": "Objectives",
                    "mirrors": "Mirrors",
                    "beamsplitters": "Beamsplitters",
                    "dichroics": "Dichroics",
                    "waveplates": "Waveplates",
                    "sources": "Sources",
                    "background": "Background",
                    "misc": "Misc",
                }
                category = category_map.get(category_key, "Other")
            else:
                # Fallback: Determine category from first interface element_type
                interfaces = rec.get("interfaces", [])
                if interfaces and len(interfaces) > 0:
                    element_type = interfaces[0].get("element_type", "lens")
                    category = ComponentRegistry.get_category_for_element_type(element_type, name)
                else:
                    category = "Other"
            categories[category].append(rec)
        
        # Create category nodes with components
        for category_name in ["Lenses", "Objectives", "Mirrors", "Beamsplitters", "Dichroics", "Waveplates", "Sources", "Background", "Misc", "Other"]:
            comps = categories[category_name]
            if not comps:
                continue
                
            # Create category header
            category_item = QtWidgets.QTreeWidgetItem([category_name])
            category_item.setFlags(category_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            
            # Style category header
            font = category_item.font(0)
            font.setBold(True)
            font.setPointSize(10)
            category_item.setFont(0, font)
            # Color adapts to dark/light mode
            if self.view.is_dark_mode():
                category_item.setForeground(0, QtGui.QColor(140, 150, 200))  # Light blue for dark mode
            else:
                category_item.setForeground(0, QtGui.QColor(60, 60, 100))  # Dark blue for light mode
            
            self.libraryTree.addTopLevelItem(category_item)
            
            # Add components under category
            for rec in comps:
                name = rec.get("name", "(unnamed)")
                img = rec.get("image_path")
                
                icon = QtGui.QIcon()
                if img and os.path.exists(img):
                    icon = QtGui.QIcon(img)
                else:
                    icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
                
                comp_item = QtWidgets.QTreeWidgetItem([name])
                comp_item.setIcon(0, icon)
                comp_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, rec)
                category_item.addChild(comp_item)
        
        # Expand all categories
        self.libraryTree.expandAll()

    def on_drop_component(self, rec: dict, scene_pos: QtCore.QPointF):
        """
        Handle component drop from library.
        Uses ComponentFactory to ensure dropped item matches ghost preview.
        """
        # Apply snap to grid if enabled
        if self.snap_to_grid:
            scene_pos = QtCore.QPointF(round(scene_pos.x()), round(scene_pos.y()))
        
        # Use ComponentFactory to create the item (same logic as ghost)
        from ...objects.component_factory import ComponentFactory
        item = ComponentFactory.create_item_from_dict(
            rec,
            scene_pos.x(),
            scene_pos.y()
        )
        
        if not item:
            # Invalid component (missing interfaces, etc.)
            name = rec.get("name", "Unknown")
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Component",
                f"Cannot create component '{name}': Missing or invalid interface definitions."
            )
            return
        
        # Connect signals
        item.edited.connect(self._maybe_retrace)
        item.edited.connect(lambda: self.collaboration_manager.broadcast_update_item(item))
        
        # Add to scene with undo support
        cmd = AddItemCommand(self.scene, item)
        self.undo_stack.push(cmd)
        
        # Clear previous selection and select only the newly dropped item
        self.scene.clearSelection()
        item.setSelected(True)
        
        # Broadcast addition to collaboration
        self.collaboration_manager.broadcast_add_item(item)
        
        # Trigger ray tracing if enabled
        if self.autotrace:
            self.retrace()

    # ----- Insert elements -----
    def delete_selected(self):
        """Delete selected items using undo stack."""
        from ...objects import BaseObj
        
        selected = self.scene.selectedItems()
        items_to_delete = []
        locked_items = []
        
        for item in selected:
            # Only delete optical components and annotations (not grid lines or rays)
            from ...objects import RectangleItem
            if isinstance(item, (BaseObj, RulerItem, TextNoteItem, RectangleItem)):
                # Check if item is locked (BaseObj has is_locked method)
                if isinstance(item, BaseObj) and item.is_locked():
                    locked_items.append(item)
                else:
                    items_to_delete.append(item)
                    # Broadcast deletion to collaboration
                    self.collaboration_manager.broadcast_remove_item(item)
        
        # Warn user if trying to delete locked items
        if locked_items:
            locked_count = len(locked_items)
            QtWidgets.QMessageBox.warning(
                self,
                "Locked Items",
                f"Cannot delete {locked_count} locked item(s).\nUnlock them first in the edit dialog."
            )
        
        # Use a single command for all deletions so undo/redo works correctly
        if items_to_delete:
            if len(items_to_delete) == 1:
                # Single item: use RemoveItemCommand for backwards compatibility
                cmd = RemoveItemCommand(self.scene, items_to_delete[0])
            else:
                # Multiple items: use RemoveMultipleItemsCommand to batch them
                cmd = RemoveMultipleItemsCommand(self.scene, items_to_delete)
            self.undo_stack.push(cmd)
        
        if self.autotrace:
            self.retrace()

    def copy_selected(self):
        """Copy selected items to clipboard."""
        from ...objects import BaseObj
        
        selected = self.scene.selectedItems()
        self._clipboard = []
        
        for item in selected:
            # Only copy optical components and annotations that have a clone method
            from ...objects import RectangleItem
            if isinstance(item, (BaseObj, RulerItem, TextNoteItem, RectangleItem)):
                # Store reference to the item itself, not serialized data
                # The clone() method will handle proper copying when pasting
                self._clipboard.append(item)
        
        # Enable paste action if we have items in clipboard
        self.act_paste.setEnabled(len(self._clipboard) > 0)
        
        # Provide feedback
        if len(self._clipboard) > 0:
            self.log_service.info(f"Copied {len(self._clipboard)} item(s) to clipboard", "Copy/Paste")

    def paste_items(self):
        """Paste items from clipboard using clone() method."""
        if not self._clipboard:
            self.log_service.warning("Cannot paste - clipboard is empty", "Copy/Paste")
            return
        
        # Offset for pasted items so they're visible
        paste_offset = (20.0, 20.0)
        pasted_items = []
        
        for item in self._clipboard:
            try:
                # Use the clone() method to create a proper deep copy
                # This automatically handles sprites, interfaces, and all properties
                cloned_item = item.clone(paste_offset)
                
                # Connect signals for optical components
                from ...objects import BaseObj
                if isinstance(cloned_item, BaseObj):
                    cloned_item.edited.connect(self._maybe_retrace)
                
                pasted_items.append(cloned_item)
                
            except Exception as e:
                # Log error but continue with other items
                import traceback
                self.log_service.error(
                    f"Error pasting {type(item).__name__}: {e}\n{traceback.format_exc()}",
                    "Copy/Paste"
                )
        
        if pasted_items:
            self.log_service.info(f"Successfully pasted {len(pasted_items)} item(s)", "Copy/Paste")
            # Use undo command to add all pasted items at once
            cmd = PasteItemsCommand(self.scene, pasted_items)
            self.undo_stack.push(cmd)
            
            # Clear current selection and select pasted items
            self.scene.clearSelection()
            for item in pasted_items:
                item.setSelected(True)
            
            if self.autotrace:
                self.retrace()

    def _do_undo(self):
        """Undo last action and retrace rays."""
        self.undo_stack.undo()
        if self.autotrace:
            self.retrace()

    def _do_redo(self):
        """Redo last undone action and retrace rays."""
        self.undo_stack.redo()
        if self.autotrace:
            self.retrace()

    def start_place_ruler(self):
        """Enter ruler placement mode (two-click)."""
        # Disable pipet mode if active
        if self._pipet_mode:
            self.act_pipet.setChecked(False)
        
        self._placing_ruler = True
        self._ruler_p1_scene = None
        self._prev_cursor = self.view.cursor()
        self.view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), "Click start point, then end point")

    def _finish_place_ruler(self):
        """Exit ruler placement mode."""
        self._placing_ruler = False
        self._ruler_p1_scene = None
        if self._prev_cursor is not None:
            self.view.setCursor(self._prev_cursor)
            self._prev_cursor = None

    # ----- Ray tracing -----
    def clear_rays(self):
        """Remove all ray graphics from scene."""
        for it in self.ray_items:
            try:
                # Check if item is still in scene before removing
                if it.scene() is not None:
                    self.scene.removeItem(it)
            except RuntimeError:
                # Item was already deleted (e.g., during scene clear)
                pass
        self.ray_items.clear()
        self.ray_data.clear()

    def retrace(self):
        """
        Trace all rays from sources through optical elements.
        
        This method dispatches to either the legacy or polymorphic raytracing engine
        based on the _use_polymorphic_raytracing feature flag.
        
        INTERFACE-BASED RAYTRACING:
        Both engines use a unified approach where ALL components expose their
        optical interfaces via get_interfaces_scene(). This allows:
        - Multi-interface components (doublets, AR-coated mirrors, etc.)
        - Consistent handling across all component types
        - Proper modeling of complex optical systems from Zemax imports
        """
        if self._use_polymorphic_raytracing:
            self._retrace_polymorphic()
        else:
            self._retrace_legacy()
    
    def _retrace_legacy(self):
        """
        Original raytracing implementation using string-based dispatch.
        
        This is the proven, stable implementation. Kept for backward compatibility
        and as a fallback during migration to the new polymorphic system.
        """
        self.clear_rays()

        # Collect sources
        sources: list[SourceItem] = []
        for it in self.scene.items():
            if isinstance(it, SourceItem):
                sources.append(it)

        if not sources:
            return

        # UNIFIED INTERFACE-BASED APPROACH:
        # Collect ALL interfaces from ALL components in the scene
        elems: list[OpticalElement] = []
        
        for item in self.scene.items():
            # Check if item has get_interfaces_scene() method
            if hasattr(item, 'get_interfaces_scene') and callable(item.get_interfaces_scene):
                try:
                    interfaces_scene = item.get_interfaces_scene()
                    
                    # Create OpticalElement for each interface
                    for p1, p2, iface in interfaces_scene:
                        elem = self._create_element_from_interface(p1, p2, iface, item)
                        if elem:
                            elems.append(elem)
                            
                except Exception as e:
                    # Log error but continue with other components
                    print(f"Warning: Error getting interfaces from {type(item).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

        # Build source params (use actual params from items)
        srcs: list[SourceParams] = []
        for S in sources:
            srcs.append(S.params)

        # Trace using legacy engine
        paths = trace_rays(elems, srcs, max_events=80)
        
        # Render paths
        self._render_ray_paths(paths)
    
    def _retrace_polymorphic(self):
        """
        NEW: Polymorphic raytracing implementation using IOpticalElement interface.
        
        This is the new, clean implementation that uses polymorphism instead of
        string-based dispatch. Benefits:
        - 6× faster (no pre-filtering)
        - 67% less code (120 lines vs 358)
        - 89% less complexity (cyclomatic 5 vs 45)
        - Type-safe (no strings)
        - Easy to extend (add new element types)
        """
        self.clear_rays()

        # Collect sources
        sources: list[SourceItem] = []
        for it in self.scene.items():
            if isinstance(it, SourceItem):
                sources.append(it)

        if not sources:
            return

        # Convert scene to polymorphic elements using the integration adapter
        try:
            from ...integration import convert_scene_to_polymorphic
            elements = convert_scene_to_polymorphic(self.scene.items())
        except Exception as e:
            print(f"Error converting scene to polymorphic elements: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to legacy system
            print("Falling back to legacy raytracing system")
            self._retrace_legacy()
            return

        # Build source params (use actual params from items)
        srcs: list[SourceParams] = []
        for S in sources:
            srcs.append(S.params)

        # Trace using new polymorphic engine
        try:
            from ...raytracing import trace_rays_polymorphic
            paths = trace_rays_polymorphic(elements, srcs, max_events=80)
        except Exception as e:
            print(f"Error in polymorphic raytracing: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to legacy system
            print("Falling back to legacy raytracing system")
            self._retrace_legacy()
            return
        
        # Render paths (same as legacy)
        self._render_ray_paths(paths)
    
    def _render_ray_paths(self, paths):
        """
        Render ray paths to the scene.
        
        This is shared between legacy and polymorphic engines since both
        produce the same RayPath output format.
        
        Args:
            paths: List of RayPath objects
        """
        for p in paths:
            if len(p.points) < 2:
                continue
            path = QtGui.QPainterPath(QtCore.QPointF(p.points[0][0], p.points[0][1]))
            for q in p.points[1:]:
                path.lineTo(q[0], q[1])
            item = QtWidgets.QGraphicsPathItem(path)
            r, g, b, a = p.rgba
            pen = QtGui.QPen(QtGui.QColor(r, g, b, a))
            pen.setWidthF(self._ray_width_px)
            pen.setCosmetic(True)
            item.setPen(pen)
            item.setZValue(10)
            self.scene.addItem(item)
            self.ray_items.append(item)
            self.ray_data.append(p)  # Store RayPath data for pipet tool
    
    def _create_element_from_interface(self, p1, p2, iface, parent_item):
        """
        Create OpticalElement from InterfaceDefinition or RefractiveInterface.
        
        This centralizes the conversion logic and handles all interface types.
        
        Args:
            p1: Start point in scene coordinates (numpy array)
            p2: End point in scene coordinates (numpy array)
            iface: InterfaceDefinition or RefractiveInterface object
            parent_item: The parent item (for accessing item-specific properties like angle_deg)
        
        Returns:
            OpticalElement or None if interface type is unknown
        """
        from ...core.models import RefractiveInterface
        
        # Handle legacy RefractiveInterface objects (from RefractiveObjectItem)
        if isinstance(iface, RefractiveInterface):
            # RefractiveInterface objects are always refractive surfaces
            elem = OpticalElement(
                kind="refractive_interface",
                p1=p1,
                p2=p2
            )
            elem.n1 = iface.n1
            elem.n2 = iface.n2
            # Copy curvature properties
            elem.is_curved = getattr(iface, 'is_curved', False)
            elem.radius_of_curvature_mm = getattr(iface, 'radius_of_curvature_mm', 0.0)
            # Copy beam splitter properties
            elem.is_beam_splitter = iface.is_beam_splitter
            if elem.is_beam_splitter:
                elem.split_T = iface.split_T
                elem.split_R = iface.split_R
                elem.is_polarizing = iface.is_polarizing
                elem.pbs_transmission_axis_deg = iface.pbs_transmission_axis_deg
            return elem
        
        # Handle InterfaceDefinition objects (new format)
        element_type = iface.element_type
        
        if element_type == "lens":
            return OpticalElement(
                kind="lens",
                p1=p1,
                p2=p2,
                efl_mm=iface.efl_mm
            )
        
        elif element_type == "mirror":
            return OpticalElement(
                kind="mirror",
                p1=p1,
                p2=p2
            )
        
        elif element_type in ["beam_splitter", "beamsplitter"]:
            return OpticalElement(
                kind="bs",
                p1=p1,
                p2=p2,
                split_T=iface.split_T,
                split_R=iface.split_R,
                is_polarizing=iface.is_polarizing,
                pbs_transmission_axis_deg=iface.pbs_transmission_axis_deg
            )
        
        elif element_type == "dichroic":
            return OpticalElement(
                kind="dichroic",
                p1=p1,
                p2=p2,
                cutoff_wavelength_nm=iface.cutoff_wavelength_nm,
                transition_width_nm=iface.transition_width_nm,
                pass_type=iface.pass_type
            )
        
        elif element_type == "polarizing_interface":
            # Handle polarizing interface based on subtype
            polarizer_subtype = getattr(iface, 'polarizer_subtype', 'waveplate')
            
            if polarizer_subtype == "waveplate":
                # Get waveplate-specific properties
                phase_shift_deg = iface.phase_shift_deg
                fast_axis_deg = iface.fast_axis_deg
                
                # angle_deg is needed for directionality detection - get from parent item
                angle_deg = 0.0
                if hasattr(parent_item, 'params') and hasattr(parent_item.params, 'angle_deg'):
                    angle_deg = parent_item.params.angle_deg
                
                return OpticalElement(
                    kind="waveplate",
                    p1=p1,
                    p2=p2,
                    phase_shift_deg=phase_shift_deg,
                    fast_axis_deg=fast_axis_deg,
                    angle_deg=angle_deg
                )
            else:
                # Future: handle other polarizer subtypes (linear_polarizer, faraday_rotator, etc.)
                return None
        
        elif element_type == "waveplate":
            # Legacy support for old "waveplate" element_type
            phase_shift_deg = getattr(iface, 'phase_shift_deg', 90.0)
            fast_axis_deg = getattr(iface, 'fast_axis_deg', 0.0)
            
            # angle_deg is needed for directionality detection - get from parent item
            angle_deg = 0.0
            if hasattr(parent_item, 'params') and hasattr(parent_item.params, 'angle_deg'):
                angle_deg = parent_item.params.angle_deg
            
            return OpticalElement(
                kind="waveplate",
                p1=p1,
                p2=p2,
                phase_shift_deg=phase_shift_deg,
                fast_axis_deg=fast_axis_deg,
                angle_deg=angle_deg
            )
        
        elif element_type == "refractive_interface":
            elem = OpticalElement(
                kind="refractive_interface",
                p1=p1,
                p2=p2
            )
            # Store refractive properties as attributes
            elem.n1 = iface.n1
            elem.n2 = iface.n2
            # Check if this interface acts as a beam splitter (for coating)
            elem.is_beam_splitter = getattr(iface, 'is_beam_splitter', False)
            if elem.is_beam_splitter:
                elem.split_T = getattr(iface, 'split_T', 50.0)
                elem.split_R = getattr(iface, 'split_R', 50.0)
                elem.is_polarizing = getattr(iface, 'is_polarizing', False)
                elem.pbs_transmission_axis_deg = getattr(iface, 'pbs_transmission_axis_deg', 0.0)
            return elem
        
        elif element_type == "beam_block":
            return OpticalElement(
                kind="block",
                p1=p1,
                p2=p2
            )

        else:
            print(f"Warning: Unknown interface type: {element_type}")
            return None

    def _maybe_retrace(self):
        """Retrace if autotrace is enabled."""
        if self.autotrace:
            self.retrace()

    # ----- Save / Load -----
    def save_assembly(self):
        """Save all elements to JSON file."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Assembly", "", "Optics Assembly (*.json)"
        )
        if not path:
            return

        # New format: registry-driven with separate lists for annotations
        data = {
            "version": "2.0",
            "items": [],  # All BaseObj items with type_name
            "rulers": [],  # Annotation items (not BaseObj)
            "texts": [],
            "rectangles": [],
        }

        from ...objects import RectangleItem, BlockItem, BaseObj
        
        for it in self.scene.items():
            # Handle BaseObj items (optical components) via registry
            if isinstance(it, BaseObj) and hasattr(it, 'type_name'):
                data["items"].append(it.to_dict())
            # Handle annotation items separately
            elif isinstance(it, RulerItem):
                data["rulers"].append(it.to_dict())
            elif isinstance(it, TextNoteItem):
                data["texts"].append(it.to_dict())
            elif isinstance(it, RectangleItem):
                data["rectangles"].append(it.to_dict())

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            # Mark as clean and track the file path
            self._saved_file_path = path
            self._mark_clean()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save error", str(e))

    def open_assembly(self):
        """Load all elements from JSON file."""
        # Check for unsaved changes before opening
        if self._is_modified:
            reply = self._prompt_save_changes()
            if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                return
        
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Assembly", "", "Optics Assembly (*.json)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Open error", str(e))
            return

        # Remove existing optical objects (keep grid lines)
        from ...objects import RectangleItem, BaseObj
        for it in list(self.scene.items()):
            if isinstance(it, (BaseObj, RulerItem, TextNoteItem, RectangleItem)):
                self.scene.removeItem(it)

        # Load items using registry-driven approach
        from ...objects.type_registry import deserialize_item
        
        # Load all BaseObj items from the "items" list (v2 format)
        for item_data in data.get("items", []):
            item = deserialize_item(item_data)
            if item:
                self.scene.addItem(item)
                # Connect edited signal for optical components
                if hasattr(item, 'edited'):
                    item.edited.connect(self._maybe_retrace)
        
        # Load annotation items (rulers, texts, rectangles)
        for d in data.get("rulers", []):
            R = RulerItem.from_dict(d)
            self.scene.addItem(R)
        for d in data.get("texts", []):
            T = TextNoteItem.from_dict(d)
            self.scene.addItem(T)
        for d in data.get("rectangles", []):
            R2 = RectangleItem.from_dict(d)
            self.scene.addItem(R2)

        # Clear undo history after loading
        self.undo_stack.clear()
        
        # Mark as clean and track the file path
        self._saved_file_path = path
        self._mark_clean()
        
        self.retrace()

    # ----- Settings -----
    def _toggle_autotrace(self, on: bool):
        """Toggle auto-trace."""
        self.autotrace = on
        if on:
            self.retrace()

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
        from ...app.main import apply_theme
        apply_theme(on)
        # Refresh library to update category colors
        self.populate_library()
    
    def _toggle_pipet(self, on: bool):
        """Toggle pipet tool mode."""
        self._pipet_mode = on
        if on:
            # Disable placement mode if active
            self._cancel_placement_mode()
            # Change cursor to indicate pipet mode is active
            self.view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), "Click on a ray to view its properties")
        else:
            # Restore default cursor (unset to use widget default)
            self.view.unsetCursor()
    
    def _toggle_placement_mode(self, component_type: str, on: bool):
        """Toggle component placement mode."""
        if on:
            # Disable pipet mode if active
            if self._pipet_mode:
                self.act_pipet.setChecked(False)
            
            # Disable any other placement mode buttons
            self._cancel_placement_mode(except_type=component_type)
            
            # Enter placement mode
            self._placement_mode = True
            self._placement_type = component_type
            
            # Enable mouse tracking to get move events without button press
            self.view.setMouseTracking(True)
            self.view.viewport().setMouseTracking(True)
            
            # Change cursor to crosshair
            self.view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            
            # Show tooltip
            QtWidgets.QToolTip.showText(
                QtGui.QCursor.pos(), 
                f"Click to place {component_type}. Right-click or Escape to cancel."
            )
        else:
            # Exit placement mode
            self._cancel_placement_mode()
    
    def _cancel_placement_mode(self, except_type: str | None = None):
        """Cancel placement mode and clean up."""
        # Check if we need to restore state (before clearing variables)
        should_restore = self._placement_mode or self._placement_ghost is not None
        
        # Clear ghost preview with proper cleanup
        if self._placement_ghost is not None:
            if self._placement_ghost.scene() is not None:
                # Get bounding rect before removal for proper viewport update
                ghost_rect = self._placement_ghost.sceneBoundingRect()
                # Expand rect to account for cosmetic pen rendering beyond bounds
                ghost_rect = ghost_rect.adjusted(-20, -20, 20, 20)
                # Hide first to prevent flicker
                self._placement_ghost.hide()
                self.scene.removeItem(self._placement_ghost)
                # Aggressive viewport update to clear any rendering artifacts
                self.scene.update(ghost_rect)
                self.scene.invalidate(ghost_rect)
                self.view.viewport().update()
                # Schedule another update to catch any stragglers
                QtCore.QTimer.singleShot(0, self.view.viewport().update)
            # Schedule deletion to ensure proper cleanup
            self._placement_ghost.deleteLater()
            self._placement_ghost = None
        
        # Reset state
        prev_type = self._placement_type
        self._placement_mode = False
        self._placement_type = None
        
        # Restore cursor and mouse tracking (after state reset)
        if should_restore:
            # CRITICAL FIX: Send synthetic mouse move event BEFORE disabling tracking
            # Qt needs mouse tracking to be ACTIVE when processing position updates
            # wheelEvent is received by the VIEW (not viewport), so we must update the view's position cache
            cursor_pos = self.view.mapFromGlobal(QtGui.QCursor.pos())
            move_event = QtGui.QMouseEvent(
                QtCore.QEvent.Type.MouseMove,
                QtCore.QPointF(cursor_pos),
                QtCore.Qt.MouseButton.NoButton,
                QtCore.Qt.MouseButton.NoButton,
                QtCore.Qt.KeyboardModifier.NoModifier
            )
            # Send to VIEW first (critical for wheelEvent which is received by the view)
            QtWidgets.QApplication.sendEvent(self.view, move_event)
            # Also send to viewport (for completeness)
            QtWidgets.QApplication.sendEvent(self.view.viewport(), move_event)
            
            # Process events to ensure the mouse position update completes
            # before we disable tracking
            QtWidgets.QApplication.processEvents()
            
            # Restore to default arrow cursor
            self.view.unsetCursor()
            
            # Disable mouse tracking AFTER position update is complete
            # (GraphicsView doesn't use it by default)
            self.view.setMouseTracking(False)
            self.view.viewport().setMouseTracking(False)
        
        # Uncheck toolbar buttons (except the one we're toggling to)
        if prev_type != except_type:
            if prev_type == "source":
                self.act_add_source.setChecked(False)
            elif prev_type == "lens":
                self.act_add_lens.setChecked(False)
            elif prev_type == "mirror":
                self.act_add_mirror.setChecked(False)
            elif prev_type == "beamsplitter":
                self.act_add_bs.setChecked(False)
            elif prev_type == "text":
                self.act_add_text.setChecked(False)
            elif prev_type == "rectangle":
                self.act_add_rectangle.setChecked(False)
    
    def _create_placement_ghost(self, component_type: str, scene_pos: QtCore.QPointF):
        """Create a ghost preview for the component being placed."""
        # Clear any existing ghost with proper cleanup
        if self._placement_ghost is not None:
            if self._placement_ghost.scene() is not None:
                ghost_rect = self._placement_ghost.sceneBoundingRect()
                # Expand rect to account for cosmetic pen rendering beyond bounds
                ghost_rect = ghost_rect.adjusted(-20, -20, 20, 20)
                self._placement_ghost.hide()
                self.scene.removeItem(self._placement_ghost)
                # Aggressive viewport update to clear any rendering artifacts
                self.scene.update(ghost_rect)
                self.scene.invalidate(ghost_rect)
                self.view.viewport().update()
            self._placement_ghost.deleteLater()
            self._placement_ghost = None
        
        # Create ghost based on component type
        if component_type == "source":
            params = SourceParams(x_mm=scene_pos.x(), y_mm=scene_pos.y())
            ghost = SourceItem(params)
        elif component_type == "lens":
            params = LensParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                efl_mm=100.0,
                object_height_mm=60.0,
                angle_deg=90.0,
                name="Lens"
            )
            ghost = LensItem(params)
        elif component_type == "mirror":
            params = MirrorParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                object_height_mm=80.0,
                angle_deg=45.0,
                name="Mirror"
            )
            ghost = MirrorItem(params)
        elif component_type == "beamsplitter":
            params = BeamsplitterParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                split_T=50.0,
                split_R=50.0,
                object_height_mm=80.0,
                angle_deg=45.0,
                name="Beamsplitter"
            )
            ghost = BeamsplitterItem(params)
        elif component_type == "text":
            ghost = TextNoteItem("Text")
            ghost.setPos(scene_pos)
        elif component_type == "rectangle":
            from ...objects import RectangleItem
            ghost = RectangleItem(width_mm=60.0, height_mm=40.0)
            ghost.setPos(scene_pos)
        else:
            return
        
        # Make it semi-transparent for ghost effect
        ghost.setOpacity(0.5)
        
        # Disable caching to prevent rendering artifacts (especially for SourceItem with cosmetic pens)
        ghost.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)
        
        # Add to scene
        self.scene.addItem(ghost)
        self._placement_ghost = ghost
    
    def _update_placement_ghost(self, scene_pos: QtCore.QPointF):
        """Update the position of the placement ghost."""
        if self._placement_ghost is not None:
            # Get old rect for proper invalidation (expanded for cosmetic pens)
            old_rect = self._placement_ghost.sceneBoundingRect().adjusted(-20, -20, 20, 20)
            
            # Apply snap to grid if enabled
            if self.snap_to_grid:
                scene_pos = QtCore.QPointF(round(scene_pos.x()), round(scene_pos.y()))
            
            # Update position
            self._placement_ghost.setPos(scene_pos)
            
            # Force scene update in old and new areas to prevent artifacts
            new_rect = self._placement_ghost.sceneBoundingRect().adjusted(-20, -20, 20, 20)
            update_rect = old_rect.united(new_rect)
            self.scene.update(update_rect)
            self.scene.invalidate(update_rect)
    
    def _place_component_at(self, component_type: str, scene_pos: QtCore.QPointF):
        """Place a component at the specified scene position."""
        # Apply snap to grid if enabled
        if self.snap_to_grid:
            scene_pos = QtCore.QPointF(round(scene_pos.x()), round(scene_pos.y()))
        
        # Create the component based on type
        if component_type == "source":
            params = SourceParams(x_mm=scene_pos.x(), y_mm=scene_pos.y())
            item = SourceItem(params)
        elif component_type == "lens":
            params = LensParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                efl_mm=100.0,
                object_height_mm=60.0,
                angle_deg=90.0,
                name="Lens"
            )
            item = LensItem(params)
        elif component_type == "mirror":
            params = MirrorParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                object_height_mm=80.0,
                angle_deg=45.0,
                name="Mirror"
            )
            item = MirrorItem(params)
        elif component_type == "beamsplitter":
            params = BeamsplitterParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                split_T=50.0,
                split_R=50.0,
                object_height_mm=80.0,
                angle_deg=45.0,
                name="Beamsplitter"
            )
            item = BeamsplitterItem(params)
        elif component_type == "text":
            item = TextNoteItem("Text")
            item.setPos(scene_pos)
        elif component_type == "rectangle":
            from ...objects import RectangleItem
            item = RectangleItem(width_mm=60.0, height_mm=40.0)
            item.setPos(scene_pos)
        else:
            return
        
        # Connect signals for optical components (skip annotations like text/rectangle)
        if component_type not in ("text", "rectangle") and hasattr(item, 'edited'):
            item.edited.connect(self._maybe_retrace)
            item.edited.connect(lambda: self.collaboration_manager.broadcast_update_item(item))
        
        # Add to scene with undo support
        cmd = AddItemCommand(self.scene, item)
        self.undo_stack.push(cmd)
        item.setSelected(True)
        
        # Broadcast addition to collaboration (for optical components only)
        if component_type not in ("text", "rectangle"):
            self.collaboration_manager.broadcast_add_item(item)
        
        # Retrace if enabled (only for optical components)
        if self.autotrace and component_type not in ("text", "rectangle"):
            self.retrace()
        
        # Force Qt to update its internal mouse position tracking by sending a synthetic mouse move
        # This ensures zoom-to-cursor works correctly after placing a component
        # wheelEvent is received by the VIEW, so we must send to the view (not just viewport)
        cursor_pos = self.view.mapFromGlobal(QtGui.QCursor.pos())
        move_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove,
            QtCore.QPointF(cursor_pos),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        # Send to VIEW first (critical for wheelEvent position cache)
        QtWidgets.QApplication.sendEvent(self.view, move_event)
        # Also send to viewport (for completeness)
        QtWidgets.QApplication.sendEvent(self.view.viewport(), move_event)
    
    def _point_to_segment_distance(self, point, seg_start, seg_end):
        """
        Calculate the minimum distance from a point to a line segment.
        
        Args:
            point: The point to check (numpy array)
            seg_start: Start of line segment (numpy array)
            seg_end: End of line segment (numpy array)
            
        Returns:
            Minimum distance from point to the line segment
        """
        # Vector from seg_start to seg_end
        segment = seg_end - seg_start
        segment_len_sq = np.dot(segment, segment)
        
        # Handle degenerate case (segment is a point)
        if segment_len_sq < 1e-10:
            return np.linalg.norm(point - seg_start)
        
        # Project point onto the line defined by the segment
        # t = 0 means point projects to seg_start
        # t = 1 means point projects to seg_end
        t = np.dot(point - seg_start, segment) / segment_len_sq
        
        # Clamp t to [0, 1] to stay within the segment
        t = max(0.0, min(1.0, t))
        
        # Find the closest point on the segment
        closest_point = seg_start + t * segment
        
        # Return distance to the closest point
        return np.linalg.norm(point - closest_point)
    
    def _handle_pipet_click(self, scene_pos: QtCore.QPointF):
        """Handle click in pipet mode to display ray information."""
        click_pt = np.array([scene_pos.x(), scene_pos.y()])
        
        # Find the nearest ray segment within tolerance
        # Use a tolerance that scales with zoom level for better UX
        # Get the view's transform to compute pixel-to-scene ratio
        transform = self.view.transform()
        scale_factor = transform.m11()  # Horizontal scale (zoom level)
        tolerance_px = 15.0  # pixels - generous click radius
        tolerance = tolerance_px / max(scale_factor, 0.01)  # Convert to scene units (mm)
        
        best_ray = None
        best_distance = float('inf')
        best_point_idx = None
        
        for i, ray_data in enumerate(self.ray_data):
            # Check each line segment in the ray path
            points = ray_data.points
            for j in range(len(points) - 1):
                # Calculate distance to the line segment between consecutive points
                dist = self._point_to_segment_distance(click_pt, points[j], points[j + 1])
                
                if dist < best_distance and dist < tolerance:
                    best_distance = dist
                    best_ray = ray_data
                    # Use the closest endpoint of the segment
                    dist_to_start = np.linalg.norm(click_pt - points[j])
                    dist_to_end = np.linalg.norm(click_pt - points[j + 1])
                    best_point_idx = j if dist_to_start < dist_to_end else j + 1
        
        if best_ray is not None:
            # Display the ray information
            self._show_ray_info_dialog(best_ray, best_point_idx)
        else:
            QtWidgets.QMessageBox.information(
                self,
                "No Ray Found",
                "No ray found near the clicked position.\nTry clicking closer to a ray."
            )
    
    def _show_ray_info_dialog(self, ray_data, point_idx):
        """Display a dialog with ray polarization and intensity information."""
        # Get position
        point = ray_data.points[point_idx]
        x_mm, y_mm = point[0], point[1]
        
        # Get intensity (from alpha channel)
        intensity = ray_data.rgba[3] / 255.0
        
        # Get polarization state
        pol = ray_data.polarization
        
        # Format polarization info
        if pol is not None:
            ex, ey = pol.jones_vector[0], pol.jones_vector[1]
            # Calculate Stokes parameters
            I_total = abs(ex)**2 + abs(ey)**2
            Q = abs(ex)**2 - abs(ey)**2
            U = 2 * np.real(ex * np.conj(ey))
            V = 2 * np.imag(ex * np.conj(ey))
            
            # Calculate degree of polarization
            pol_degree = np.sqrt(Q**2 + U**2 + V**2) / I_total if I_total > 0 else 0
            
            # Linear polarization angle
            pol_angle_rad = 0.5 * np.arctan2(U, Q)
            pol_angle_deg = np.degrees(pol_angle_rad)
            
            pol_text = f"""Jones Vector: [{ex:.4f}, {ey:.4f}]

Stokes Parameters:
  I = {I_total:.4f}
  Q = {Q:.4f}
  U = {U:.4f}
  V = {V:.4f}

Degree of Polarization: {pol_degree:.2%}
Linear Polarization Angle: {pol_angle_deg:.2f}°"""
        else:
            pol_text = "No polarization information available"
        
        # Get wavelength
        wavelength_text = f"{ray_data.wavelength_nm:.1f} nm" if ray_data.wavelength_nm > 0 else "Not specified"
        
        # Create info dialog
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Ray Information")
        dialog.setMinimumWidth(400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Position info
        pos_label = QtWidgets.QLabel(f"<b>Position:</b> ({x_mm:.2f}, {y_mm:.2f}) mm")
        layout.addWidget(pos_label)
        
        # Intensity info
        intensity_label = QtWidgets.QLabel(f"<b>Intensity:</b> {intensity:.2%}")
        layout.addWidget(intensity_label)
        
        # Wavelength info
        wl_label = QtWidgets.QLabel(f"<b>Wavelength:</b> {wavelength_text}")
        layout.addWidget(wl_label)
        
        layout.addSpacing(10)
        
        # Polarization info
        pol_title = QtWidgets.QLabel("<b>Polarization State:</b>")
        layout.addWidget(pol_title)
        
        pol_text_widget = QtWidgets.QTextEdit()
        pol_text_widget.setPlainText(pol_text)
        pol_text_widget.setReadOnly(True)
        pol_text_widget.setMaximumHeight(200)
        layout.addWidget(pol_text_widget)
        
        # Close button
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()

    def _set_ray_width(self, v: float):
        """Set ray width and retrace."""
        self._ray_width_px = float(v)
        if self.autotrace:
            self.retrace()

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
        except Exception as e:
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
        except Exception as e:
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

    # ----- Event filter for snap, ruler placement, pipet, and placement mode -----
    def eventFilter(self, obj, ev):
        """Handle scene events for snap, ruler placement, pipet tool, and component placement."""
        et = ev.type()

        # --- Component placement mode ---
        if self._placement_mode:
            # Mouse move - update ghost position
            if et == QtCore.QEvent.Type.GraphicsSceneMouseMove:
                mev = ev  # QGraphicsSceneMouseEvent
                scene_pt = mev.scenePos()
                
                # Create ghost if it doesn't exist yet
                if self._placement_ghost is None:
                    self._create_placement_ghost(self._placement_type, scene_pt)
                else:
                    self._update_placement_ghost(scene_pt)
                return True  # consume event
            
            # Mouse press - place component or cancel
            elif et == QtCore.QEvent.Type.GraphicsSceneMousePress:
                mev = ev  # QGraphicsSceneMouseEvent
                scene_pt = mev.scenePos()
                
                if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                    # Place the component
                    self._place_component_at(self._placement_type, scene_pt)
                    # Keep placement mode active for multiple placements
                    # Just clear the ghost so a new one is created on next move
                    if self._placement_ghost is not None:
                        if self._placement_ghost.scene() is not None:
                            # Get bounding rect before removal for proper viewport update
                            ghost_rect = self._placement_ghost.sceneBoundingRect()
                            # Expand rect to account for cosmetic pen rendering beyond bounds
                            ghost_rect = ghost_rect.adjusted(-20, -20, 20, 20)
                            # Hide first to prevent flicker
                            self._placement_ghost.hide()
                            self.scene.removeItem(self._placement_ghost)
                            # Aggressive viewport update to clear any rendering artifacts (especially for SourceItem)
                            self.scene.update(ghost_rect)
                            self.scene.invalidate(ghost_rect)
                            self.view.viewport().update()
                            # Schedule another update to catch any stragglers
                            QtCore.QTimer.singleShot(0, self.view.viewport().update)
                        # Schedule deletion to ensure proper cleanup
                        self._placement_ghost.deleteLater()
                        self._placement_ghost = None
                    return True  # consume event
                
                elif mev.button() == QtCore.Qt.MouseButton.RightButton:
                    # Cancel placement
                    self._cancel_placement_mode()
                    return True  # consume event
        
        # --- Pipet tool ---
        if self._pipet_mode and et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            mev = ev  # QGraphicsSceneMouseEvent
            if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                scene_pt = mev.scenePos()
                self._handle_pipet_click(scene_pt)
                return True  # consume event

        # --- Ruler 2-click placement ---
        if self._placing_ruler and et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            mev = ev  # QGraphicsSceneMouseEvent
            if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                scene_pt = mev.scenePos()
                if self._ruler_p1_scene is None:
                    # first click
                    self._ruler_p1_scene = QtCore.QPointF(scene_pt)
                    return True  # consume
                else:
                    # second click -> create ruler in item coords
                    p1 = QtCore.QPointF(self._ruler_p1_scene)
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
            from ...objects import BaseObj, RectangleItem
            mev = ev
            # Check if this is a rotation operation (Ctrl modifier)
            is_rotation_mode = mev.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
            
            # Store initial positions of selected items
            self._item_positions.clear()
            self._item_rotations.clear()
            self._item_group_states.clear()
            
            selected_items = [it for it in self.scene.selectedItems() 
                            if isinstance(it, (BaseObj, RulerItem, TextNoteItem, RectangleItem))]
            
            for it in selected_items:
                self._item_positions[it] = QtCore.QPointF(it.pos())
                
                # Track rotations if in rotation mode (for BaseObj and RectangleItem)
                if is_rotation_mode and isinstance(it, (BaseObj, RectangleItem)):
                    self._item_rotations[it] = it.rotation()
            
            # For group rotation, also track initial positions for orbit calculation
            if is_rotation_mode and len(selected_items) > 1:
                self._item_group_states = {
                    'items': selected_items,
                    'initial_positions': {it: QtCore.QPointF(it.pos()) for it in selected_items},
                    'initial_rotations': {it: it.rotation() for it in selected_items if isinstance(it, (BaseObj, RectangleItem))}
                }

        # --- Snap to grid and create move/rotate commands on mouse release ---
        if et == QtCore.QEvent.Type.GraphicsSceneMouseRelease:
            from ...objects import BaseObj

            # Clear snap guides
            self.view.clear_snap_guides()
            
            # Check if this was a group rotation
            was_group_rotation = bool(self._item_group_states and 'items' in self._item_group_states)
            
            for it in self.scene.selectedItems():
                if isinstance(it, BaseObj) and self.snap_to_grid:
                    p = it.pos()
                    it.setPos(round(p.x()), round(p.y()))
                
                # Create move command if item was moved (and not rotated)
                if it in self._item_positions and it not in self._item_rotations:
                    old_pos = self._item_positions[it]
                    new_pos = it.pos()
                    # Only create command if position actually changed
                    if old_pos != new_pos:
                        cmd = MoveItemCommand(it, old_pos, new_pos)
                        self.undo_stack.push(cmd)
            
            # Handle rotation commands
            if self._item_rotations and not was_group_rotation:
                # Single item rotation(s)
                for it, old_rotation in self._item_rotations.items():
                    new_rotation = it.rotation()
                    # Only create command if rotation actually changed
                    if abs(new_rotation - old_rotation) > 0.01:  # Small threshold for floating point comparison
                        cmd = RotateItemCommand(it, old_rotation, new_rotation)
                        self.undo_stack.push(cmd)
            
            elif was_group_rotation:
                # Group rotation - check if any items changed
                from ...objects import RectangleItem
                items = self._item_group_states['items']
                old_positions = self._item_group_states['initial_positions']
                old_rotations = self._item_group_states['initial_rotations']
                new_positions = {it: it.pos() for it in items}
                new_rotations = {it: it.rotation() for it in items if isinstance(it, (BaseObj, RectangleItem))}
                
                # Check if anything actually changed
                position_changed = any(
                    old_positions[it] != new_positions[it] 
                    for it in items if it in old_positions
                )
                rotation_changed = any(
                    abs(old_rotations.get(it, 0) - new_rotations.get(it, 0)) > 0.01
                    for it in items if isinstance(it, (BaseObj, RectangleItem))
                )
                
                if position_changed or rotation_changed:
                    # Filter to only items that have rotation (BaseObj and RectangleItem)
                    rotatable_items = [it for it in items if isinstance(it, (BaseObj, RectangleItem))]
                    if rotatable_items:
                        cmd = RotateItemsCommand(
                            rotatable_items,
                            old_positions,
                            new_positions,
                            old_rotations,
                            new_rotations
                        )
                        self.undo_stack.push(cmd)
            
            self._item_positions.clear()
            self._item_rotations.clear()
            self._item_group_states.clear()
            if self.autotrace:
                QtCore.QTimer.singleShot(0, self.retrace)
        elif et in (
            QtCore.QEvent.Type.GraphicsSceneMouseMove,
            QtCore.QEvent.Type.GraphicsSceneWheel,
            QtCore.QEvent.Type.GraphicsSceneDragLeave,
            QtCore.QEvent.Type.GraphicsSceneDrop,
        ):
            if self.autotrace:
                QtCore.QTimer.singleShot(0, self.retrace)

        return super().eventFilter(obj, ev)
    
    def keyPressEvent(self, ev):
        """Handle key press events for placement mode cancellation."""
        # Check if Escape is pressed and placement mode is active
        if ev.key() == QtCore.Qt.Key.Key_Escape:
            if self._placement_mode:
                self._cancel_placement_mode()
                ev.accept()
                return
        
        # Pass to parent for normal handling
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
                except:
                    self.collab_server_process.kill()
                self.log_service.info("Stopped collaboration server", "Collaboration")
            except Exception as e:
                self.log_service.warning(f"Error stopping server: {e}", "Collaboration")
            finally:
                self.collab_server_process = None
    
    def _on_collaboration_status_changed(self, status: str):
        """Update collaboration status indicator."""
        self.collab_status_label.setText(f"Collaboration: {status}")
    
    def _on_remote_item_added(self, item_type: str, data: dict):
        """Handle remote item addition."""
        # Suppress broadcasting while adding remote item
        try:
            # Create the appropriate item type
            if item_type == "source":
                item = SourceItem(SourceParams(**data), data.get("item_uuid"))
                self.scene.addItem(item)
                item.edited.connect(self._maybe_retrace)
            elif item_type == "lens":
                item = LensItem(LensParams(**data), data.get("item_uuid"))
                self.scene.addItem(item)
                item.edited.connect(self._maybe_retrace)
            elif item_type == "mirror":
                item = MirrorItem(MirrorParams(**data), data.get("item_uuid"))
                self.scene.addItem(item)
                item.edited.connect(self._maybe_retrace)
            elif item_type == "beamsplitter":
                item = BeamsplitterItem(BeamsplitterParams(**data), data.get("item_uuid"))
                self.scene.addItem(item)
                item.edited.connect(self._maybe_retrace)
            elif item_type == "dichroic":
                item = DichroicItem(DichroicParams(**data), data.get("item_uuid"))
                self.scene.addItem(item)
                item.edited.connect(self._maybe_retrace)
            elif item_type == "waveplate":
                item = WaveplateItem(WaveplateParams(**data), data.get("item_uuid"))
                self.scene.addItem(item)
                item.edited.connect(self._maybe_retrace)
            elif item_type == "ruler":
                item = RulerItem.from_dict(data)
                self.scene.addItem(item)
            elif item_type == "text":
                item = TextNoteItem.from_dict(data)
                self.scene.addItem(item)
            
            # Add to UUID map
            if hasattr(item, 'item_uuid'):
                self.collaboration_manager.item_uuid_map[item.item_uuid] = item
            
            # Retrace if autotrace is on
            if self.autotrace:
                QtCore.QTimer.singleShot(50, self.retrace)
        except Exception as e:
            print(f"Error adding remote item: {e}")
    
    # ensure clean shutdown
    def closeEvent(self, e: QtGui.QCloseEvent):
        # Check for unsaved changes
        if self._is_modified:
            reply = self._prompt_save_changes()
            if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
                e.ignore()  # Don't close the window
                return
        
        try:
            if hasattr(self, "_comp_editor") and self._comp_editor:
                self._comp_editor.close()
            # Disconnect from collaboration and stop server if running
            if hasattr(self, "collaboration_manager"):
                self.disconnect_collaboration()
        except Exception:
            pass
        super().closeEvent(e)
