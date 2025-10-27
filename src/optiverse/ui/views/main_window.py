from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import (
    BeamsplitterParams,
    LensParams,
    MirrorParams,
    OpticalElement,
    SourceParams,
)
from ...core.use_cases import trace_rays
from ...core.color_utils import qcolor_from_hex
from ...services.storage_service import StorageService
from ...widgets.beamsplitter_item import BeamsplitterItem
from ...widgets.graphics_view import GraphicsView
from ...widgets.lens_item import LensItem
from ...widgets.mirror_item import MirrorItem
from ...widgets.ruler_item import RulerItem
from ...widgets.source_item import SourceItem
from ...widgets.text_note_item import TextNoteItem


def _get_icon_path(icon_name: str) -> str:
    """Get the full path to an icon file."""
    icons_dir = Path(__file__).parent.parent / "icons"
    return str(icons_dir / icon_name)


def to_np(p: QtCore.QPointF) -> np.ndarray:
    """Convert QPointF to numpy array."""
    return np.array([p.x(), p.y()], float)


class LibraryList(QtWidgets.QListWidget):
    """Drag-enabled library list for component templates."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.setIconSize(QtCore.QSize(80, 80))
        self.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.setMovement(QtWidgets.QListView.Movement.Static)
        self.setSpacing(8)
        self.setDragEnabled(True)
        self.setSelectionMode(QtWidgets.QListWidget.SelectionMode.SingleSelection)
        self.setWordWrap(True)
        # Ensure we're in drag-only mode (not internal move)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(QtCore.Qt.DropAction.CopyAction)
    
    def startDrag(self, actions):
        it = self.currentItem()
        if not it:
            return
        payload = it.data(QtCore.Qt.ItemDataRole.UserRole)
        md = QtCore.QMimeData()
        md.setData("application/x-optics-component", json.dumps(payload).encode("utf-8"))
        drag = QtGui.QDrag(self)
        drag.setMimeData(md)
        drag.setHotSpot(QtCore.QPoint(10, 10))
        drag.setPixmap(it.icon().pixmap(64, 64))
        # Execute drag and clear selection afterwards to prevent multiple drags
        result = drag.exec(QtCore.Qt.DropAction.CopyAction)
        # Clear selection after drag to avoid confusion
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
        
        # Ruler placement mode
        self._placing_ruler = False
        self._ruler_p1_scene: Optional[QtCore.QPointF] = None
        self._prev_cursor = None
        
        # Services
        self.storage_service = StorageService()
        
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
        
        # View menu
        mView = mb.addMenu("&View")
        mView.addAction(self.act_zoom_in)
        mView.addAction(self.act_zoom_out)
        mView.addAction(self.act_fit)
        mView.addSeparator()
        mView.addAction(self.act_autotrace)
        mView.addAction(self.act_snap)
        mView.addMenu(self.menu_raywidth)
        
        # Tools menu
        mTools = mb.addMenu("&Tools")
        mTools.addAction(self.act_retrace)
        mTools.addAction(self.act_clear)
        mTools.addSeparator()
        mTools.addAction(self.act_editor)
        mTools.addAction(self.act_reload)
    
    def _build_library_dock(self):
        """Build component library dock."""
        self.libDock = QtWidgets.QDockWidget("Component Library", self)
        self.libDock.setObjectName("libDock")
        self.libraryList = LibraryList(self)
        self.libDock.setWidget(self.libraryList)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.libDock)
        self.populate_library()
    
    def populate_library(self):
        """Load and populate component library from storage."""
        self.libraryList.clear()
        records = self.storage_service.load_library()
        for rec in records:
            name = rec.get("name", "(unnamed)")
            img = rec.get("image_path")
            kind = rec.get("kind", "lens")
            icon = (
                QtGui.QIcon(img)
                if img and os.path.exists(img)
                else self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
            )
            item = QtWidgets.QListWidgetItem(icon, f"{name}\n({kind})")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, rec)
            self.libraryList.addItem(item)
    
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
        
        self.scene.addItem(item)
        item._maybe_attach_sprite()
        item.edited.connect(self._maybe_retrace)
        item.setSelected(True)
        if self.autotrace:
            self.retrace()
    
    # ----- Insert elements -----
    def add_source(self):
        """Add source with default params."""
        s = SourceItem(SourceParams())
        self.scene.addItem(s)
        s.edited.connect(self._maybe_retrace)
        s.setSelected(True)
        if self.autotrace:
            self.retrace()
    
    def add_lens(self):
        """Add lens with default params."""
        L = LensItem(LensParams())
        self.scene.addItem(L)
        L._maybe_attach_sprite()
        L.edited.connect(self._maybe_retrace)
        L.setSelected(True)
        if self.autotrace:
            self.retrace()
    
    def add_mirror(self):
        """Add mirror with default params."""
        M = MirrorItem(MirrorParams())
        self.scene.addItem(M)
        M._maybe_attach_sprite()
        M.edited.connect(self._maybe_retrace)
        M.setSelected(True)
        if self.autotrace:
            self.retrace()
    
    def add_bs(self):
        """Add beamsplitter with default params."""
        B = BeamsplitterItem(BeamsplitterParams())
        self.scene.addItem(B)
        B._maybe_attach_sprite()
        B.edited.connect(self._maybe_retrace)
        B.setSelected(True)
        if self.autotrace:
            self.retrace()
    
    def add_text(self):
        """Add text note at viewport center."""
        center = self.view.mapToScene(self.view.viewport().rect().center())
        T = TextNoteItem("Text")
        T.setPos(center)
        self.scene.addItem(T)
    
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
            with open(path, "r", encoding="utf-8") as f:
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
                    self.scene.addItem(R)
                    R.setSelected(True)
                    self._finish_place_ruler()
                    return True  # consume
            elif mev.button() == QtCore.Qt.MouseButton.RightButton:
                # cancel placement on right-click
                self._finish_place_ruler()
                return True
        
        # --- Snap to grid on mouse release ---
        if et == QtCore.QEvent.Type.GraphicsSceneMouseRelease:
            from ...widgets.base_obj import BaseObj
            
            for it in self.scene.selectedItems():
                if isinstance(it, BaseObj) and self.snap_to_grid:
                    p = it.pos()
                    it.setPos(round(p.x()), round(p.y()))
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
