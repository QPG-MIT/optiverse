from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import (
    BeamsplitterParams,
    LensParams,
    MirrorParams,
    OpticalElement,
    SourceParams,
)
from ...core.snap_helper import SnapHelper
from ...core.undo_commands import AddItemCommand, MoveItemCommand, RemoveItemCommand
from ...core.undo_stack import UndoStack
from ...core.use_cases import trace_rays
from ...services.settings_service import SettingsService
from ...services.storage_service import StorageService
from ...objects import (
    BeamsplitterItem,
    GraphicsView,
    LensItem,
    MirrorItem,
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
        
        # Expand all categories by default
        self.expandAll()

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
        drag.setHotSpot(QtCore.QPoint(10, 10))
        
        # Use icon if available
        icon = it.icon(0)
        if not icon.isNull():
            drag.setPixmap(icon.pixmap(64, 64))
        
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
        self.scene.setSceneRect(-600, -350, 1200, 700)
        self.view = GraphicsView(self.scene)
        self.view.parent = lambda: self  # For dropEvent callback
        self.setCentralWidget(self.view)

        # State variables
        self.snap_to_grid = True
        self._ray_width_px = 2.0
        self.ray_items: list[QtWidgets.QGraphicsPathItem] = []
        self.autotrace = True
        self._grid_items: list[QtWidgets.QGraphicsLineItem] = []
        
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
        
        # Load saved preferences
        self.magnetic_snap = self.settings_service.get_value("magnetic_snap", True, bool)

        # Build UI
        self._draw_grid()
        self._build_actions()
        self._build_toolbar()
        self._build_menubar()
        self._build_library_dock()

        # Install event filter for snap and ruler placement
        self.scene.installEventFilter(self)

    def _draw_grid(self):
        """Draw mm/cm grid lines."""
        for it in self._grid_items:
            try:
                self.scene.removeItem(it)
            except Exception:
                pass
        self._grid_items.clear()

        minor_pen = QtGui.QPen(QtGui.QColor(242, 242, 242))
        major_pen = QtGui.QPen(QtGui.QColor(215, 215, 215))
        axis_pen = QtGui.QPen(QtGui.QColor(170, 170, 170))
        axis_pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        for pen in (minor_pen, major_pen, axis_pen):
            pen.setCosmetic(True)
            pen.setWidth(1)

        rect = self.scene.sceneRect()
        xmin, xmax = int(rect.left()) - 1000, int(rect.right()) + 1000
        ymin, ymax = int(rect.top()) - 1000, int(rect.bottom()) + 1000

        for x in range(xmin, xmax + 1, 1):
            line = self.scene.addLine(x, ymin, x, ymax, major_pen if x % 10 == 0 else minor_pen)
            self._grid_items.append(line)
        for y in range(ymin, ymax + 1, 1):
            line = self.scene.addLine(xmin, y, xmax, y, major_pen if y % 10 == 0 else minor_pen)
            self._grid_items.append(line)

        self._grid_items.append(self.scene.addLine(-10000, 0, 10000, 0, axis_pen))
        self._grid_items.append(self.scene.addLine(0, -10000, 0, 10000, axis_pen))

    def _build_actions(self):
        """Build all menu actions."""
        # --- File ---
        self.act_open = QtGui.QAction("Open Assembly…", self)
        self.act_open.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.open_assembly)

        self.act_save = QtGui.QAction("Save Assembly…", self)
        self.act_save.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self.save_assembly)

        # --- Edit ---
        self.act_undo = QtGui.QAction("Undo", self)
        self.act_undo.setShortcut(QtGui.QKeySequence("Ctrl+Z"))
        self.act_undo.triggered.connect(self._do_undo)
        self.act_undo.setEnabled(False)

        self.act_redo = QtGui.QAction("Redo", self)
        self.act_redo.setShortcut(QtGui.QKeySequence("Ctrl+Y"))
        self.act_redo.triggered.connect(self._do_redo)
        self.act_redo.setEnabled(False)

        self.act_delete = QtGui.QAction("Delete", self)
        self.act_delete.setShortcut(QtGui.QKeySequence.StandardKey.Delete)
        self.act_delete.triggered.connect(self.delete_selected)

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
        self.act_zoom_in.triggered.connect(lambda: (self.view.scale(1.15, 1.15), self.view.zoomChanged.emit()))

        self.act_zoom_out = QtGui.QAction("Zoom Out", self)
        self.act_zoom_out.setShortcut(QtGui.QKeySequence.StandardKey.ZoomOut)
        self.act_zoom_out.triggered.connect(lambda: (self.view.scale(1 / 1.15, 1 / 1.15), self.view.zoomChanged.emit()))

        self.act_fit = QtGui.QAction("Fit Scene", self)
        self.act_fit.setShortcut("Ctrl+0")
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
        self.act_retrace.triggered.connect(self.retrace)

        self.act_clear = QtGui.QAction("Clear Rays", self)
        self.act_clear.triggered.connect(self.clear_rays)

        self.act_editor = QtGui.QAction("Component Editor…", self)
        self.act_editor.setShortcut("Ctrl+E")
        self.act_editor.triggered.connect(self.open_component_editor)

        self.act_reload = QtGui.QAction("Reload Library", self)
        self.act_reload.triggered.connect(self.populate_library)

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
        mView.addMenu(self.menu_raywidth)

        # Tools menu
        mTools = mb.addMenu("&Tools")
        mTools.addAction(self.act_retrace)
        mTools.addAction(self.act_clear)
        mTools.addSeparator()
        mTools.addAction(self.act_editor)
        mTools.addAction(self.act_reload)

    def _build_library_dock(self):
        """Build component library dock with categorized tree view."""
        self.libDock = QtWidgets.QDockWidget("Component Library", self)
        self.libDock.setObjectName("libDock")
        self.libraryTree = LibraryTree(self)
        self.libDock.setWidget(self.libraryTree)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.libDock)
        self.populate_library()

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
            "Mirrors": [],
            "Beamsplitters": [],
            "Sources": [],
            "Other": []
        }
        
        for rec in records:
            kind = rec.get("kind", "other")
            category = ComponentRegistry.get_category_for_kind(kind)
            categories[category].append(rec)
        
        # Create category nodes with components
        for category_name in ["Lenses", "Mirrors", "Beamsplitters", "Sources", "Other"]:
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
            category_item.setForeground(0, QtGui.QColor(60, 60, 100))
            
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
        """Handle component drop from library."""
        kind = rec.get("kind", "lens")
        name = rec.get("name")
        img = rec.get("image_path")
        mm_per_px = float(rec.get("mm_per_pixel", 0.1))
        line_px = tuple(rec.get("line_px", (0, 0, 1, 0)))
        length_mm = float(rec.get("length_mm", 60.0))

        if kind == "lens":
            efl_mm = float(rec.get("efl_mm", 100.0))
            params = LensParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=90.0,
                efl_mm=efl_mm,
                length_mm=length_mm,
                image_path=img,
                mm_per_pixel=mm_per_px,
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
                angle_deg=45.0,
                length_mm=length_mm,
                split_T=T,
                split_R=R,
                image_path=img,
                mm_per_pixel=mm_per_px,
                line_px=line_px,
                name=name,
            )
            item = BeamsplitterItem(params)
        else:  # mirror
            params = MirrorParams(
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y(),
                angle_deg=0.0,
                length_mm=length_mm,
                image_path=img,
                mm_per_pixel=mm_per_px,
                line_px=line_px,
                name=name,
            )
            item = MirrorItem(params)

        item._maybe_attach_sprite()
        item.edited.connect(self._maybe_retrace)
        cmd = AddItemCommand(self.scene, item)
        self.undo_stack.push(cmd)
        item.setSelected(True)
        if self.autotrace:
            self.retrace()

    # ----- Insert elements -----
    def add_source(self):
        """Add source with default params."""
        s = SourceItem(SourceParams())
        s.edited.connect(self._maybe_retrace)
        cmd = AddItemCommand(self.scene, s)
        self.undo_stack.push(cmd)
        s.setSelected(True)
        if self.autotrace:
            self.retrace()

    def add_lens(self):
        """Add lens with standard params from component registry."""
        try:
            from ...objects.component_registry import ComponentRegistry
            std_comp = ComponentRegistry.get_standard_lens()
            params = LensParams(
                efl_mm=std_comp["efl_mm"],
                length_mm=std_comp["length_mm"],
                image_path=std_comp["image_path"],
                mm_per_pixel=std_comp["mm_per_pixel"],
                line_px=tuple(std_comp["line_px"]),
                name=std_comp.get("name"),
            )
        except Exception:
            # Fallback to basic params if registry fails
            params = LensParams()
        
        L = LensItem(params)
        L._maybe_attach_sprite()
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
                length_mm=std_comp["length_mm"],
                image_path=std_comp["image_path"],
                mm_per_pixel=std_comp["mm_per_pixel"],
                line_px=tuple(std_comp["line_px"]),
                name=std_comp.get("name"),
            )
        except Exception:
            # Fallback to basic params if registry fails
            params = MirrorParams()
        
        M = MirrorItem(params)
        M._maybe_attach_sprite()
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
                length_mm=std_comp["length_mm"],
                image_path=std_comp["image_path"],
                mm_per_pixel=std_comp["mm_per_pixel"],
                line_px=tuple(std_comp["line_px"]),
                name=std_comp.get("name"),
            )
        except Exception:
            # Fallback to basic params if registry fails
            params = BeamsplitterParams()
        
        B = BeamsplitterItem(params)
        B._maybe_attach_sprite()
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
                cmd = RemoveItemCommand(self.scene, item)
                self.undo_stack.push(cmd)
        
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
            self.scene.removeItem(it)
        self.ray_items.clear()

    def retrace(self):
        """Trace all rays from sources through optical elements."""
        self.clear_rays()

        # Collect elements
        sources: list[SourceItem] = []
        lenses: list[LensItem] = []
        mirrors: list[MirrorItem] = []
        beamsplitters: list[BeamsplitterItem] = []

        for it in self.scene.items():
            if isinstance(it, SourceItem):
                sources.append(it)
            elif isinstance(it, LensItem):
                lenses.append(it)
            elif isinstance(it, MirrorItem):
                mirrors.append(it)
            elif isinstance(it, BeamsplitterItem):
                beamsplitters.append(it)

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
            if isinstance(it, (SourceItem, LensItem, MirrorItem, BeamsplitterItem, RulerItem, TextNoteItem)):
                self.scene.removeItem(it)

        # Re-create everything
        for d in data.get("sources", []):
            s = SourceItem(SourceParams(**d))
            self.scene.addItem(s)
            s.edited.connect(self._maybe_retrace)
        for d in data.get("lenses", []):
            L = LensItem(LensParams(**d))
            self.scene.addItem(L)
            L._maybe_attach_sprite()
            L.edited.connect(self._maybe_retrace)
        for d in data.get("mirrors", []):
            M = MirrorItem(MirrorParams(**d))
            self.scene.addItem(M)
            M._maybe_attach_sprite()
            M.edited.connect(self._maybe_retrace)
        for d in data.get("beamsplitters", []):
            B = BeamsplitterItem(BeamsplitterParams(**d))
            self.scene.addItem(B)
            B._maybe_attach_sprite()
            B.edited.connect(self._maybe_retrace)
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

    # ensure clean shutdown
    def closeEvent(self, e: QtGui.QCloseEvent):
        try:
            if hasattr(self, "_comp_editor") and self._comp_editor:
                self._comp_editor.close()
        except Exception:
            pass
        super().closeEvent(e)
