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
    OpticalElement,
    SourceParams,
)
from ...core.snap_helper import SnapHelper
from ...core.undo_commands import AddItemCommand, MoveItemCommand, RemoveItemCommand, PasteItemsCommand
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
        self.autotrace = True
        # Grid now drawn in GraphicsView.drawBackground() for better performance
        
        # Snap helper for magnetic alignment
        self._snap_helper = SnapHelper(tolerance_px=10.0)

        # Ruler placement mode
        self._placing_ruler = False
        self._ruler_p1_scene: QtCore.QPointF | None = None
        self._prev_cursor = None

        # Undo/Redo tracking
        self._item_positions: dict[QtWidgets.QGraphicsItem, QtCore.QPointF] = {}

        # Services
        self.storage_service = StorageService()
        self.settings_service = SettingsService()
        self.undo_stack = UndoStack()
        self.collaboration_manager = CollaborationManager(self)
        self.log_service = get_log_service()
        self.collab_server_process = None  # Track hosted server process
        
        # Load saved preferences
        self.magnetic_snap = self.settings_service.get_value("magnetic_snap", True, bool)
        
        # Load dark mode preference
        dark_mode_saved = self.settings_service.get_value("dark_mode", self.view.is_dark_mode(), bool)
        self.view.set_dark_mode(dark_mode_saved)
        
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

    def _build_actions(self):
        """Build all menu actions."""
        # --- File ---
        self.act_open = QtGui.QAction("Open Assembly…", self)
        self.act_open.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self.act_open.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        self.act_open.triggered.connect(self.open_assembly)

        self.act_save = QtGui.QAction("Save Assembly…", self)
        self.act_save.setShortcut(QtGui.QKeySequence.StandardKey.Save)
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
        self.act_delete.setShortcut(QtGui.QKeySequence.StandardKey.Delete)
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

        # --- Insert ---
        self.act_add_source = QtGui.QAction("Source", self)
        self.act_add_source.triggered.connect(self.add_source)

        self.act_add_lens = QtGui.QAction("Lens", self)
        self.act_add_lens.triggered.connect(self.add_lens)

        self.act_add_mirror = QtGui.QAction("Mirror", self)
        self.act_add_mirror.triggered.connect(self.add_mirror)

        self.act_add_bs = QtGui.QAction("Beamsplitter", self)
        self.act_add_bs.triggered.connect(self.add_bs)

        self.act_add_ruler = QtGui.QAction("Ruler", self)
        self.act_add_ruler.triggered.connect(self.start_place_ruler)

        self.act_add_text = QtGui.QAction("Text", self)
        self.act_add_text.triggered.connect(self.add_text)

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

        # Text button
        text_icon = QtGui.QIcon(_get_icon_path("text.png"))
        self.act_add_text.setIcon(text_icon)
        toolbar.addAction(self.act_add_text)

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
            "Misc": [],
            "Other": []
        }
        
        for rec in records:
            kind = rec.get("kind", "other")
            name = rec.get("name", "")
            category = ComponentRegistry.get_category_for_kind(kind, name)
            categories[category].append(rec)
        
        # Create category nodes with components
        for category_name in ["Lenses", "Objectives", "Mirrors", "Beamsplitters", "Dichroics", "Waveplates", "Sources", "Misc", "Other"]:
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
        """Handle component drop from library with normalized 1000px system."""
        kind = rec.get("kind", "lens")
        name = rec.get("name")
        img = rec.get("image_path")
        line_px = tuple(rec.get("line_px", (0, 0, 1, 0)))
        # Support new object_height_mm and legacy object_height/length_mm
        object_height_mm = float(rec.get("object_height_mm", rec.get("object_height", rec.get("length_mm", 60.0))))
        # mm_per_pixel computed from object_height_mm in normalized 1000px system
        
        # Get optical axis angle from library (with sensible defaults)
        if "angle_deg" in rec:
            angle_deg = float(rec.get("angle_deg"))
        else:
            # Fallback defaults if not specified
            if kind == "lens":
                angle_deg = 90.0
            elif kind == "beamsplitter":
                angle_deg = 45.0
            elif kind == "dichroic":
                angle_deg = 45.0
            elif kind == "waveplate":
                angle_deg = 90.0
            else:
                angle_deg = 0.0

        if kind == "lens":
            efl_mm = float(rec.get("efl_mm", 100.0))
            params = LensParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle_deg,
                efl_mm=efl_mm,
                object_height_mm=object_height_mm,
                image_path=img,
                line_px=line_px,
                name=name,
            )
            item = LensItem(params)
        elif kind == "beamsplitter":
            if "split_TR" in rec and isinstance(rec["split_TR"], (list, tuple)) and len(rec["split_TR"]) == 2:
                T, R = float(rec["split_TR"][0]), float(rec["split_TR"][1])
            else:
                T, R = float(rec.get("split_T", 50.0)), float(rec.get("split_R", 50.0))
            params = BeamsplitterParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                split_T=T,
                split_R=R,
                image_path=img,
                line_px=line_px,
                name=name,
                is_polarizing=bool(rec.get("is_polarizing", False)),
                pbs_transmission_axis_deg=float(rec.get("pbs_transmission_axis_deg", 0.0)),
            )
            item = BeamsplitterItem(params)
        elif kind == "waveplate":
            phase_shift_deg = float(rec.get("phase_shift_deg", 90.0))
            fast_axis_deg = float(rec.get("fast_axis_deg", 0.0))
            params = WaveplateParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                phase_shift_deg=phase_shift_deg,
                fast_axis_deg=fast_axis_deg,
                image_path=img,
                line_px=line_px,
                name=name,
            )
            item = WaveplateItem(params)
        elif kind == "dichroic":
            cutoff_wavelength_nm = float(rec.get("cutoff_wavelength_nm", 550.0))
            transition_width_nm = float(rec.get("transition_width_nm", 50.0))
            pass_type = str(rec.get("pass_type", "longpass"))
            params = DichroicParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                cutoff_wavelength_nm=cutoff_wavelength_nm,
                transition_width_nm=transition_width_nm,
                pass_type=pass_type,
                image_path=img,
                line_px=line_px,
                name=name,
            )
            item = DichroicItem(params)
        elif kind == "slm":
            params = SLMParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                image_path=img,
                line_px=line_px,
                name=name,
            )
            item = SLMItem(params)
        else:  # mirror
            params = MirrorParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=angle_deg,
                object_height_mm=object_height_mm,
                image_path=img,
                line_px=line_px,
                name=name,
            )
            item = MirrorItem(params)

        # Sprite is automatically attached in constructor, no need to call again
        item.edited.connect(self._maybe_retrace)
        item.edited.connect(lambda: self.collaboration_manager.broadcast_update_item(item))
        cmd = AddItemCommand(self.scene, item)
        self.undo_stack.push(cmd)
        # Clear previous selection and select only the newly dropped item
        self.scene.clearSelection()
        item.setSelected(True)
        # Broadcast addition to collaboration
        self.collaboration_manager.broadcast_add_item(item)
        if self.autotrace:
            self.retrace()

    # ----- Insert elements -----
    def add_source(self):
        """Add source with default params."""
        s = SourceItem(SourceParams())
        s.edited.connect(self._maybe_retrace)
        s.edited.connect(lambda: self.collaboration_manager.broadcast_update_item(s))
        cmd = AddItemCommand(self.scene, s)
        self.undo_stack.push(cmd)
        s.setSelected(True)
        # Broadcast addition to collaboration
        self.collaboration_manager.broadcast_add_item(s)
        if self.autotrace:
            self.retrace()

    def add_lens(self):
        """Add lens with standard params from component registry."""
        try:
            from ...objects.component_registry import ComponentRegistry
            std_comp = ComponentRegistry.get_standard_lens()
            params = LensParams(
                efl_mm=std_comp["efl_mm"],
                object_height_mm=std_comp["object_height_mm"],
                image_path=std_comp["image_path"],
                line_px=tuple(std_comp["line_px"]),
                name=std_comp.get("name"),
            )
        except Exception:
            # Fallback to basic params if registry fails
            params = LensParams()
        
        L = LensItem(params)
        # Sprite is automatically attached in constructor
        L.edited.connect(self._maybe_retrace)
        cmd = AddItemCommand(self.scene, L)
        self.undo_stack.push(cmd)
        L.setSelected(True)
        if self.autotrace:
            self.retrace()

    def add_mirror(self):
        """Add mirror with standard params from component registry."""
        try:
            from ...objects.component_registry import ComponentRegistry
            std_comp = ComponentRegistry.get_standard_mirror()
            params = MirrorParams(
                object_height_mm=std_comp["object_height_mm"],
                image_path=std_comp["image_path"],
                line_px=tuple(std_comp["line_px"]),
                name=std_comp.get("name"),
            )
        except Exception:
            # Fallback to basic params if registry fails
            params = MirrorParams()
        
        M = MirrorItem(params)
        # Sprite is automatically attached in constructor
        M.edited.connect(self._maybe_retrace)
        cmd = AddItemCommand(self.scene, M)
        self.undo_stack.push(cmd)
        M.setSelected(True)
        if self.autotrace:
            self.retrace()

    def add_bs(self):
        """Add beamsplitter with standard params from component registry."""
        try:
            from ...objects.component_registry import ComponentRegistry
            std_comp = ComponentRegistry.get_standard_beamsplitter()
            params = BeamsplitterParams(
                split_T=std_comp["split_T"],
                split_R=std_comp["split_R"],
                object_height_mm=std_comp["object_height_mm"],
                image_path=std_comp["image_path"],
                line_px=tuple(std_comp["line_px"]),
                name=std_comp.get("name"),
            )
        except Exception:
            # Fallback to basic params if registry fails
            params = BeamsplitterParams()
        
        B = BeamsplitterItem(params)
        # Sprite is automatically attached in constructor
        B.edited.connect(self._maybe_retrace)
        cmd = AddItemCommand(self.scene, B)
        self.undo_stack.push(cmd)
        B.setSelected(True)
        if self.autotrace:
            self.retrace()

    def add_text(self):
        """Add text note at viewport center."""
        center = self.view.mapToScene(self.view.viewport().rect().center())
        T = TextNoteItem("Text")
        T.setPos(center)
        cmd = AddItemCommand(self.scene, T)
        self.undo_stack.push(cmd)

    def delete_selected(self):
        """Delete selected items using undo stack."""
        from ...objects import BaseObj
        
        selected = self.scene.selectedItems()
        for item in selected:
            # Only delete optical components, rulers, and text notes (not grid lines or rays)
            if isinstance(item, (BaseObj, RulerItem, TextNoteItem)):
                # Broadcast deletion to collaboration
                self.collaboration_manager.broadcast_remove_item(item)
                cmd = RemoveItemCommand(self.scene, item)
                self.undo_stack.push(cmd)
        
        if self.autotrace:
            self.retrace()

    def copy_selected(self):
        """Copy selected items to clipboard."""
        from ...objects import BaseObj
        
        selected = self.scene.selectedItems()
        self._clipboard = []
        
        for item in selected:
            # Only copy optical components, rulers, and text notes
            if isinstance(item, (BaseObj, RulerItem, TextNoteItem)):
                try:
                    # Serialize the item to dictionary
                    item_data = item.to_dict()
                    # Store the type of the item for reconstruction
                    item_data['_item_type'] = type(item).__name__
                    self._clipboard.append(item_data)
                except Exception as e:
                    # Log error but continue with other items
                    import traceback
                    self.log_service.error(
                        f"Could not copy {type(item).__name__}: {e}\n{traceback.format_exc()}",
                        "Copy/Paste"
                    )
        
        # Enable paste action if we have items in clipboard
        self.act_paste.setEnabled(len(self._clipboard) > 0)
        
        # Provide feedback
        if len(self._clipboard) > 0:
            self.log_service.info(f"Copied {len(self._clipboard)} item(s) to clipboard", "Copy/Paste")

    def paste_items(self):
        """Paste items from clipboard."""
        if not self._clipboard:
            self.log_service.warning("Cannot paste - clipboard is empty", "Copy/Paste")
            return
        
        self.log_service.debug(f"Pasting {len(self._clipboard)} item(s) from clipboard", "Copy/Paste")
        
        # Offset for pasted items so they're visible
        paste_offset = QtCore.QPointF(20.0, 20.0)
        pasted_items = []
        
        # Fields to exclude when pasting (these get recalculated or belong to item, not params)
        excluded_fields = {'_item_type', 'mm_per_pixel', 'item_uuid'}
        
        for item_data in self._clipboard:
            try:
                item_type = item_data.get('_item_type')
                
                # Create new item based on type
                if item_type == 'SourceItem':
                    params = SourceParams(**{k: v for k, v in item_data.items() if k not in excluded_fields})
                    params.x_mm += paste_offset.x()
                    params.y_mm += paste_offset.y()
                    item = SourceItem(params)
                    item.edited.connect(self._maybe_retrace)
                    pasted_items.append(item)
                    
                elif item_type == 'LensItem':
                    params = LensParams(**{k: v for k, v in item_data.items() if k not in excluded_fields})
                    params.x_mm += paste_offset.x()
                    params.y_mm += paste_offset.y()
                    item = LensItem(params)
                    # Sprite is automatically attached in constructor
                    item.edited.connect(self._maybe_retrace)
                    pasted_items.append(item)
                    
                elif item_type == 'MirrorItem':
                    params = MirrorParams(**{k: v for k, v in item_data.items() if k not in excluded_fields})
                    params.x_mm += paste_offset.x()
                    params.y_mm += paste_offset.y()
                    item = MirrorItem(params)
                    # Sprite is automatically attached in constructor
                    item.edited.connect(self._maybe_retrace)
                    pasted_items.append(item)
                    
                elif item_type == 'BeamsplitterItem':
                    params = BeamsplitterParams(**{k: v for k, v in item_data.items() if k not in excluded_fields})
                    params.x_mm += paste_offset.x()
                    params.y_mm += paste_offset.y()
                    item = BeamsplitterItem(params)
                    # Sprite is automatically attached in constructor
                    item.edited.connect(self._maybe_retrace)
                    pasted_items.append(item)
                
                elif item_type == 'DichroicItem':
                    params = DichroicParams(**{k: v for k, v in item_data.items() if k not in excluded_fields})
                    params.x_mm += paste_offset.x()
                    params.y_mm += paste_offset.y()
                    item = DichroicItem(params)
                    item.edited.connect(self._maybe_retrace)
                    pasted_items.append(item)
                
                elif item_type == 'WaveplateItem':
                    params = WaveplateParams(**{k: v for k, v in item_data.items() if k not in excluded_fields})
                    params.x_mm += paste_offset.x()
                    params.y_mm += paste_offset.y()
                    item = WaveplateItem(params)
                    item.edited.connect(self._maybe_retrace)
                    pasted_items.append(item)
                
                elif item_type == 'SLMItem':
                    params = SLMParams(**{k: v for k, v in item_data.items() if k not in excluded_fields})
                    params.x_mm += paste_offset.x()
                    params.y_mm += paste_offset.y()
                    item = SLMItem(params)
                    item.edited.connect(self._maybe_retrace)
                    pasted_items.append(item)
                    
                elif item_type == 'RulerItem':
                    # Remove _item_type and reconstruct ruler
                    data = {k: v for k, v in item_data.items() if k != '_item_type'}
                    item = RulerItem.from_dict(data)
                    # Offset the ruler position
                    item.setPos(item.pos() + paste_offset)
                    pasted_items.append(item)
                    
                elif item_type == 'TextNoteItem':
                    # Remove _item_type and reconstruct text note
                    data = {k: v for k, v in item_data.items() if k != '_item_type'}
                    item = TextNoteItem.from_dict(data)
                    # Offset the text note position
                    item.setPos(item.pos() + paste_offset)
                    pasted_items.append(item)
                
                else:
                    self.log_service.warning(f"Unknown item type '{item_type}' - skipping", "Copy/Paste")
                    
            except Exception as e:
                # Log error but continue with other items
                import traceback
                self.log_service.error(
                    f"Error pasting {item_type}: {e}\n{traceback.format_exc()}",
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

    def retrace(self):
        """Trace all rays from sources through optical elements."""
        self.clear_rays()

        # Collect elements
        sources: list[SourceItem] = []
        lenses: list[LensItem] = []
        mirrors: list[MirrorItem] = []
        beamsplitters: list[BeamsplitterItem] = []
        dichroics: list[DichroicItem] = []
        waveplates: list[WaveplateItem] = []
        slms: list[SLMItem] = []

        for it in self.scene.items():
            if isinstance(it, SourceItem):
                sources.append(it)
            elif isinstance(it, LensItem):
                lenses.append(it)
            elif isinstance(it, MirrorItem):
                mirrors.append(it)
            elif isinstance(it, BeamsplitterItem):
                beamsplitters.append(it)
            elif isinstance(it, DichroicItem):
                dichroics.append(it)
            elif isinstance(it, WaveplateItem):
                waveplates.append(it)
            elif isinstance(it, SLMItem):
                slms.append(it)

        if not sources:
            return

        # Build optical elements
        elems: list[OpticalElement] = []
        for L in lenses:
            p1, p2 = L.endpoints_scene()
            elems.append(OpticalElement(kind="lens", p1=p1, p2=p2, efl_mm=L.params.efl_mm))
        for M in mirrors:
            p1, p2 = M.endpoints_scene()
            elems.append(OpticalElement(kind="mirror", p1=p1, p2=p2))
        for B in beamsplitters:
            p1, p2 = B.endpoints_scene()
            # PBS transmission axis is stored in absolute lab frame coordinates
            # It does NOT rotate with the element - you must manually adjust it
            # if you want the axis to have a specific orientation
            elems.append(
                OpticalElement(
                    kind="bs",
                    p1=p1,
                    p2=p2,
                    split_T=B.params.split_T,
                    split_R=B.params.split_R,
                    is_polarizing=B.params.is_polarizing,
                    pbs_transmission_axis_deg=B.params.pbs_transmission_axis_deg,
                )
            )
        for W in waveplates:
            p1, p2 = W.endpoints_scene()
            # Waveplate fast axis is stored in absolute lab frame coordinates
            # Phase shift determines QWP (90°) or HWP (180°) behavior
            elems.append(
                OpticalElement(
                    kind="waveplate",
                    p1=p1,
                    p2=p2,
                    phase_shift_deg=W.params.phase_shift_deg,
                    fast_axis_deg=W.params.fast_axis_deg,
                )
            )
        for D in dichroics:
            p1, p2 = D.endpoints_scene()
            # Dichroic mirrors have wavelength-dependent reflection/transmission
            pass_type = getattr(D.params, "pass_type", "longpass")
            elems.append(
                OpticalElement(
                    kind="dichroic",
                    p1=p1,
                    p2=p2,
                    cutoff_wavelength_nm=D.params.cutoff_wavelength_nm,
                    transition_width_nm=D.params.transition_width_nm,
                    pass_type=pass_type,
                )
            )
        for S in slms:
            p1, p2 = S.endpoints_scene()
            # SLMs act as mirrors for ray tracing
            elems.append(OpticalElement(kind="mirror", p1=p1, p2=p2))

        # Build source params (use actual params from items)
        srcs: list[SourceParams] = []
        for S in sources:
            srcs.append(S.params)

        # Trace
        paths = trace_rays(elems, srcs, max_events=80)
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

        data = {
            "sources": [],
            "lenses": [],
            "mirrors": [],
            "beamsplitters": [],
            "dichroics": [],
            "waveplates": [],
            "rulers": [],
            "texts": [],
        }

        for it in self.scene.items():
            if isinstance(it, SourceItem):
                data["sources"].append(it.to_dict())
            elif isinstance(it, LensItem):
                data["lenses"].append(it.to_dict())
            elif isinstance(it, MirrorItem):
                data["mirrors"].append(it.to_dict())
            elif isinstance(it, BeamsplitterItem):
                data["beamsplitters"].append(it.to_dict())
            elif isinstance(it, DichroicItem):
                data["dichroics"].append(it.to_dict())
            elif isinstance(it, WaveplateItem):
                data["waveplates"].append(it.to_dict())
            elif isinstance(it, RulerItem):
                data["rulers"].append(it.to_dict())
            elif isinstance(it, TextNoteItem):
                data["texts"].append(it.to_dict())

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save error", str(e))

    def open_assembly(self):
        """Load all elements from JSON file."""
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
        for it in list(self.scene.items()):
            if isinstance(it, (SourceItem, LensItem, MirrorItem, BeamsplitterItem, DichroicItem, WaveplateItem, RulerItem, TextNoteItem)):
                self.scene.removeItem(it)

        # Re-create everything
        for d in data.get("sources", []):
            s = SourceItem(SourceParams(**d))
            self.scene.addItem(s)
            s.edited.connect(self._maybe_retrace)
        for d in data.get("lenses", []):
            L = LensItem(LensParams(**d))
            self.scene.addItem(L)
            # Sprite is automatically attached in constructor
            L.edited.connect(self._maybe_retrace)
        for d in data.get("mirrors", []):
            M = MirrorItem(MirrorParams(**d))
            self.scene.addItem(M)
            # Sprite is automatically attached in constructor
            M.edited.connect(self._maybe_retrace)
        for d in data.get("beamsplitters", []):
            B = BeamsplitterItem(BeamsplitterParams(**d))
            self.scene.addItem(B)
            # Sprite is automatically attached in constructor
            B.edited.connect(self._maybe_retrace)
        for d in data.get("dichroics", []):
            D = DichroicItem(DichroicParams(**d))
            self.scene.addItem(D)
            # Sprite is automatically attached in constructor
            D.edited.connect(self._maybe_retrace)
        for d in data.get("waveplates", []):
            W = WaveplateItem(WaveplateParams(**d))
            self.scene.addItem(W)
            # Sprite is automatically attached in constructor
            W.edited.connect(self._maybe_retrace)
        for d in data.get("rulers", []):
            R = RulerItem.from_dict(d)
            self.scene.addItem(R)
        for d in data.get("texts", []):
            T = TextNoteItem.from_dict(d)
            self.scene.addItem(T)

        # Clear undo history after loading
        self.undo_stack.clear()
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

    # ----- Event filter for snap and ruler placement -----
    def eventFilter(self, obj, ev):
        """Handle scene events for snap and ruler placement."""
        et = ev.type()

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

        # --- Track item positions on mouse press ---
        if et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            from ...objects import BaseObj
            # Store initial positions of selected items
            self._item_positions.clear()
            for it in self.scene.selectedItems():
                if isinstance(it, (BaseObj, RulerItem, TextNoteItem)):
                    self._item_positions[it] = QtCore.QPointF(it.pos())

        # --- Snap to grid and create move commands on mouse release ---
        if et == QtCore.QEvent.Type.GraphicsSceneMouseRelease:
            from ...objects import BaseObj

            # Clear snap guides
            self.view.clear_snap_guides()
            
            for it in self.scene.selectedItems():
                if isinstance(it, BaseObj) and self.snap_to_grid:
                    p = it.pos()
                    it.setPos(round(p.x()), round(p.y()))
                
                # Create move command if item was moved
                if it in self._item_positions:
                    old_pos = self._item_positions[it]
                    new_pos = it.pos()
                    # Only create command if position actually changed
                    if old_pos != new_pos:
                        cmd = MoveItemCommand(it, old_pos, new_pos)
                        self.undo_stack.push(cmd)
            
            self._item_positions.clear()
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
        try:
            if hasattr(self, "_comp_editor") and self._comp_editor:
                self._comp_editor.close()
            # Disconnect from collaboration and stop server if running
            if hasattr(self, "collaboration_manager"):
                self.disconnect_collaboration()
        except Exception:
            pass
        super().closeEvent(e)
