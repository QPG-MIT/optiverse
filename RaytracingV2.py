# ray_sandbox_2d.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2D (top view) ray-optics sandbox + Component Library & Editor.

- Sources, thin Lenses, Mirrors, Beam Splitters (right-click → Edit)
- Grid in mm/cm, zoom/pan, snap, autotrace
- Decorative component image rendered under geometry (correct mm-per-pixel alignment)
- Scale bar overlay (auto-updates on zoom/resize)
- Save/Open assembly (JSON) with file dialogs
- Component Editor window + persistent library in ./library (shared with editor)

Updates:
- FIX: Source rotation used only once (no double-counting); 45° now rotates rays by 45°.
- Beamsplitter branches keep the source color; only alpha scales with intensity (T/R).
- Source color is user-editable and saved as hex (#RRGGBB).
- New Ruler tool: add a draggable two-point distance bar with live mm label; delete via right-click.
- New Text Note: add movable, editable text; delete via right-click.
"""

import json, math, os, sys, traceback
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Dict, Any

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

def _default_angle_for_record(rec: dict) -> float:
    # Prefer an explicit angle in the record if it exists (e.g. your editor might save it)
    if "angle_deg" in rec:
        try: return float(rec["angle_deg"])
        except Exception: pass
    # Fall back to current app defaults
    kind = (rec.get("kind") or "").lower()
    if kind == "lens": return 90.0
    if kind == "beamsplitter": return 45.0
    if kind == "mirror": return 0.0
    # Source not in the library list typically, but just in case:
    if kind == "source": return 0.0
    return 0.0

# ---------- Local library paths (next to this .py) ----------
def _here_dir() -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    return base

def library_root_dir() -> str:
    root = os.path.join(_here_dir(), "library")
    os.makedirs(root, exist_ok=True)
    return root

def assets_dir() -> str:
    d = os.path.join(library_root_dir(), "assets")
    os.makedirs(d, exist_ok=True)
    return d

def get_library_path() -> str:
    return os.path.join(library_root_dir(), "components_library.json")

LIBRARY_JSON = get_library_path()


# -------------------- helpers --------------------
def deg2rad(a): return a * math.pi / 180.0
def normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v);  return v if n == 0 else v / n
def reflect_vec(v: np.ndarray, n_hat: np.ndarray) -> np.ndarray:
    return v - 2.0 * np.dot(v, n_hat) * n_hat

def ray_hit_element(P: np.ndarray, V: np.ndarray,
                    A: np.ndarray, B: np.ndarray,
                    tol: float = 1e-9):
    """Intersect ray (P + t V, t>0) with finite segment AB centered geometry."""
    t_hat = normalize(B - A)
    L = np.linalg.norm(B - A)
    if L < tol: return None
    n_hat = np.array([-t_hat[1], t_hat[0]])   # left-normal of segment
    C = 0.5 * (A + B)                          # segment center
    denom = np.dot(V, n_hat)
    if abs(denom) < tol: return None
    t = np.dot(C - P, n_hat) / denom
    if t <= tol: return None
    X = P + t * V
    s = np.dot(X - C, t_hat)
    if abs(s) > 0.5 * L + 1e-7: return None
    return t, X, t_hat, n_hat, C, L

def qcolor_from_hex(h: str, fallback: str = "#DC143C") -> QtGui.QColor:
    try:
        c = QtGui.QColor(h)
        return c if c.isValid() else QtGui.QColor(fallback)
    except Exception:
        return QtGui.QColor(fallback)

def hex_from_qcolor(c: QtGui.QColor) -> str:
    return c.name()  # #RRGGBB


# -------------------- parameters --------------------
@dataclass
class SourceParams:
    x_mm: float = -400.0
    y_mm: float = 0.0
    angle_deg: float = 0.0
    size_mm: float = 10.0
    n_rays: int = 9
    ray_length_mm: float = 1000.0
    spread_deg: float = 0.0
    color_hex: str = "#DC143C"  # default crimson

@dataclass
class LensParams:
    x_mm: float = -150.0
    y_mm: float = 0.0
    angle_deg: float = 90.0
    efl_mm: float = 100.0
    length_mm: float = 60.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float,float,float,float]] = None
    name: Optional[str] = None

@dataclass
class MirrorParams:
    x_mm: float = 150.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    length_mm: float = 80.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float,float,float,float]] = None
    name: Optional[str] = None

@dataclass
class BeamsplitterParams:
    x_mm: float = 0.0
    y_mm: float = 0.0
    angle_deg: float = 45.0
    length_mm: float = 80.0
    split_T: float = 50.0
    split_R: float = 50.0
    image_path: Optional[str] = None
    mm_per_pixel: float = 0.1
    line_px: Optional[Tuple[float,float,float,float]] = None
    name: Optional[str] = None


# -------------------- base graphics object --------------------
class BaseObj(QtWidgets.QGraphicsObject):
    edited = QtCore.pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self.setTransformOriginPoint(0.0, 0.0)
        self._ready = False
        # NEW: keep dataclass params in sync on user interactions

    def _sprite_rect_in_item(self) -> Optional[QtCore.QRectF]:
        sp = getattr(self, "_sprite", None)
        if sp is None or not sp.isVisible():
            return None
        # parent == this item ⇒ returned rect is in *item-local* coords
        return sp.mapRectToParent(sp.boundingRect())

    def _shape_union_sprite(self, shape_path: QtGui.QPainterPath) -> QtGui.QPainterPath:
        r = self._sprite_rect_in_item()
        if r is not None:
            pad = 1.0
            rp = QtGui.QPainterPath()
            rp.addRect(r.adjusted(-pad, -pad, pad, pad))
            shape_path = shape_path.united(rp)
        return shape_path

    def _bounds_union_sprite(self, base_rect: QtCore.QRectF) -> QtCore.QRectF:
        r = self._sprite_rect_in_item()
        if r is not None:
            pad = 2.0
            r = r.adjusted(-pad, -pad, pad, pad)
            base_rect = base_rect.united(r)
        return base_rect
    def itemChange(self, change, value):
        if change in (QtWidgets.QGraphicsItem.ItemPositionHasChanged,
                      QtWidgets.QGraphicsItem.ItemRotationHasChanged):
            if getattr(self, "_ready", False) and self.scene() is not None:
                self._sync_params_from_item()
                self.edited.emit()

        # ensure sprite re-renders when selection toggles (remove lingering tint)
        if change in (QtWidgets.QGraphicsItem.ItemSelectedChange,
                      QtWidgets.QGraphicsItem.ItemSelectedHasChanged):
            # repaint this item and its sprite (if any)
            self.update()
            sp = getattr(self, "_sprite", None)
            if sp is not None:
                sp.update()

        return super().itemChange(change, value)

    def _sync_params_from_item(self):
        # Overridden in subclasses that have params
        pass
    def _parent_window(self):
        sc = self.scene()
        if sc:
            views = sc.views()
            if views:
                return views[0].window()
        return QtWidgets.QApplication.activeWindow()

    def wheelEvent(self, ev: QtWidgets.QGraphicsSceneWheelEvent):
        # Ctrl + wheel when selected → rotate the element
        if self.isSelected() and (ev.modifiers() & QtCore.Qt.ControlModifier):
            steps = ev.delta() / 120.0
            self.setRotation(self.rotation() + 2.0 * steps)
            self.edited.emit(); ev.accept()
        else:
            ev.ignore()

    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent):
        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit…")
        act_delete = m.addAction("Delete")
        a = m.exec_(ev.screenPos())
        if a == act_edit:
            self.open_editor()
        elif a == act_delete and self.scene():
            self.scene().removeItem(self)
    def _sprite_hitshape_union(self, shape_path: QtGui.QPainterPath) -> QtGui.QPainterPath:
        """Union the child sprite's bounding rect (in parent coords) into the given shape path."""
        sp = getattr(self, "_sprite", None)
        if sp is not None and sp.isVisible():
            rect_parent = sp.mapRectToParent(sp.boundingRect())
            rpath = QtGui.QPainterPath()
            rpath.addRect(rect_parent.adjusted(-1, -1, 1, 1))  # tiny pad so strokes are easy to grab
            shape_path = shape_path.united(rpath)
        return shape_path
    def open_editor(self): pass
    def to_dict(self) -> Dict[str, Any]: return {}
    def from_dict(self, d: Dict[str, Any]): pass
        

# -------------------- Source --------------------
class SourceItem(BaseObj):
    def __init__(self, params: SourceParams):
        super().__init__()
        self.params = params
        self._color = qcolor_from_hex(self.params.color_hex)
        self._update_shape()
        self.setPos(self.params.x_mm, self.params.y_mm)
        # The item's rotation is the authoritative pose
        self.setRotation(self.params.angle_deg)
    def _sync_params_from_item(self):
        self.params.x_mm = float(self.pos().x())
        self.params.y_mm = float(self.pos().y())
        self.params.angle_deg = float(self.rotation())

    def to_dict(self):
        d = asdict(self.params)
        # force live pose + color
        d["x_mm"] = float(self.pos().x())
        d["y_mm"] = float(self.pos().y())
        d["angle_deg"] = float(self.rotation())
        d["color_hex"] = hex_from_qcolor(self._color)
        return d
    
    #def to_dict(self): return asdict(self.params)

    def _update_shape(self):
        self.prepareGeometryChange()
        self._half = max(1.0, self.params.size_mm / 2.0)
        self._bar = QtGui.QPainterPath(); self._bar.moveTo(0, -self._half); self._bar.lineTo(0, self._half)
        self._arrow = QtGui.QPainterPath(); self._arrow.moveTo(0, 0); self._arrow.lineTo(18.0, 0.0)

    def boundingRect(self) -> QtCore.QRectF:
        r = 22
        return QtCore.QRectF(-r, -self._half-2, r+2, self._half+2)

    def shape(self) -> QtGui.QPainterPath:
        s = QtGui.QPainterPathStroker(); s.setWidth(10)
        return s.createStroke(self._bar).united(self._arrow)

    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        pen1 = QtGui.QPen(self._color, 2)
        pen2 = QtGui.QPen(self._color, 1.5)
        p.setPen(pen1); p.drawPath(self._bar)
        p.setPen(pen2); p.drawPath(self._arrow)

    def open_editor(self):
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent); d.setWindowTitle("Edit Source")
        f = QtWidgets.QFormLayout(d)
        x = QtWidgets.QDoubleSpinBox(); x.setRange(-1e6,1e6); x.setDecimals(3); x.setSuffix(" mm"); x.setValue(self.pos().x())
        y = QtWidgets.QDoubleSpinBox(); y.setRange(-1e6,1e6); y.setDecimals(3); y.setSuffix(" mm"); y.setValue(self.pos().y())
        ang=QtWidgets.QDoubleSpinBox(); ang.setRange(-180,180); ang.setDecimals(2); ang.setSuffix(" °"); ang.setValue(self.rotation())
        size=QtWidgets.QDoubleSpinBox(); size.setRange(0,1e6); size.setDecimals(3); size.setSuffix(" mm"); size.setValue(self.params.size_mm)
        nr  =QtWidgets.QSpinBox(); nr.setRange(1,2001); nr.setValue(self.params.n_rays)
        rlen=QtWidgets.QDoubleSpinBox(); rlen.setRange(1,1e7); rlen.setDecimals(1); rlen.setSuffix(" mm"); rlen.setValue(self.params.ray_length_mm)
        spr =QtWidgets.QDoubleSpinBox(); spr.setRange(0,89.9); spr.setDecimals(2); spr.setSuffix(" °"); spr.setValue(self.params.spread_deg)

        # color picker
        color_btn = QtWidgets.QToolButton()
        color_btn.setText("Pick…")
        color_disp = QtWidgets.QLabel(self.params.color_hex)
        def paint_chip(lbl, hexstr):
            pm = QtGui.QPixmap(40, 16); pm.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pm); p.fillRect(0,0,40,16, qcolor_from_hex(hexstr)); p.end()
            lbl.setPixmap(pm)
        chip = QtWidgets.QLabel()
        paint_chip(chip, self.params.color_hex)
        def pick_color():
            c = QtWidgets.QColorDialog.getColor(self._color, d, "Choose Ray Color",
                                                QtWidgets.QColorDialog.DontUseNativeDialog)
            if c.isValid():
                self._color = c
                color_disp.setText(c.name())
                paint_chip(chip, c.name())
        row_color = QtWidgets.QHBoxLayout()
        row_color.addWidget(color_btn); row_color.addWidget(color_disp); row_color.addWidget(chip); row_color.addStretch(1)
        color_btn.clicked.connect(pick_color)

        for lab,w in [("X",x),("Y",y),("Angle",ang),("Aperture size",size),("# Rays",nr),("Ray length",rlen),("Angular spread (±)",spr)]:
            f.addRow(lab,w)
        f.addRow("Ray color", row_color)

        btn=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel); f.addRow(btn)
        btn.accepted.connect(d.accept); btn.rejected.connect(d.reject)
        if d.exec_():
            self.setPos(x.value(), y.value()); self.params.x_mm=x.value(); self.params.y_mm=y.value()
            self.setRotation(ang.value()); self.params.angle_deg=ang.value()
            self.params.size_mm=size.value(); self.params.n_rays=nr.value()
            self.params.ray_length_mm=rlen.value(); self.params.spread_deg=spr.value()
            self.params.color_hex = hex_from_qcolor(self._color)
            self._update_shape(); self.edited.emit()

    # def to_dict(self):
    #     d = asdict(self.params)
    #     d["angle_deg"] = float(self.rotation())  # persist actual pose
    #     d["color_hex"] = hex_from_qcolor(self._color)
    #     return d

    def from_dict(self, d):
        self.params = SourceParams(**d)
        self._color = qcolor_from_hex(self.params.color_hex)
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._update_shape()
        self.edited.emit()


# -------------------- Sprite helper (image underlay) --------------------
class ComponentSprite(QtWidgets.QGraphicsPixmapItem):
    """
    Image underlay for an optical element.
    - Picked line's midpoint is aligned to the parent's local origin using setOffset.
    - Uniform scale px→mm via mm_per_pixel (no Y-stretch).
    - Pre-rotated so picked line lies on +X in local coords.
    """
    def __init__(self, image_path: str, mm_per_pixel: float,
                 line_px: Tuple[float, float, float, float],
                 element_length_mm: float,
                 parent_item: QtWidgets.QGraphicsItem):
        super().__init__(parent_item)

        if not (image_path and os.path.exists(image_path)):
            self.setVisible(False)
            return

        pix0 = QtGui.QPixmap(image_path)
        img = pix0.toImage()
        img.setDevicePixelRatio(1.0)
        pix = QtGui.QPixmap.fromImage(img)
        self.setPixmap(pix)

        x1, y1, x2, y2 = line_px
        dx, dy = (x2 - x1), (y2 - y1)
        angle_img_deg = math.degrees(math.atan2(dy, dx))
        cx = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)

        self.setOffset(-cx, -cy)
        self.setRotation(-angle_img_deg)
        s_px_to_mm = float(mm_per_pixel) if mm_per_pixel > 0 else 1.0
        self.setScale(s_px_to_mm)

        self.setZValue(-100)
        self.setOpacity(0.95)
        self.setTransformationMode(QtCore.Qt.SmoothTransformation)
        self.setCacheMode(QtWidgets.QGraphicsItem.NoCache)  # <- important
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
    def paint(self, p: QtGui.QPainter, opt, widget=None):
        super().paint(p, opt, widget)
        par = self.parentItem()
        if par is not None and par.isSelected():
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(30, 144, 255, 70))  # translucent blue
            p.drawRect(self.boundingRect())
# -------------------- Lens --------------------
class LensItem(BaseObj):
    def __init__(self, params: LensParams):
        super().__init__()
        self.params = params
        self._sprite: Optional[ComponentSprite] = None
        self._update_geom()
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._maybe_attach_sprite()

    def _sync_params_from_item(self):
        self.params.x_mm = float(self.pos().x())
        self.params.y_mm = float(self.pos().y())
        self.params.angle_deg = float(self.rotation())

    def to_dict(self):
        d = asdict(self.params)
        d["x_mm"] = float(self.pos().x())
        d["y_mm"] = float(self.pos().y())
        d["angle_deg"] = float(self.rotation())
        return d
    
    
    def _maybe_attach_sprite(self):
        # Our bounds/shape depend on the sprite, so notify Qt first.
        self.prepareGeometryChange()

        # Remove previous sprite if any
        old = getattr(self, "_sprite", None)
        if old is not None:
            try:
                # Detach from scene cleanly
                if old.scene() is not None:
                    old.scene().removeItem(old)
            except Exception:
                pass
        self._sprite = None

        # Create new sprite if we have all the pieces
        img = getattr(self.params, "image_path", None)
        line = getattr(self.params, "line_px", None)
        mm_per_px = float(getattr(self.params, "mm_per_pixel", 0.0) or 0.0)

        if img and line and os.path.exists(img):
            x1, y1, x2, y2 = line
            picked_len_px = max(1.0, math.hypot(x2 - x1, y2 - y1))
            picked_len_mm = picked_len_px * (mm_per_px if mm_per_px > 0 else 1.0)

            # If the decorative pick length differs from current, sync our geometry length
            if abs(self.params.length_mm - picked_len_mm) > 1e-6:
                self.params.length_mm = picked_len_mm
                # Our primitives depend on length -> rebuild them
                self._update_geom()

            # Build the underlay sprite
            sp = ComponentSprite(
                image_path=img,
                mm_per_pixel=mm_per_px if mm_per_px > 0 else 1.0,
                line_px=line,
                element_length_mm=self.params.length_mm,
                parent_item=self
            )

            # Make sure the sprite never steals input (so the parent item gets the events)
            sp.setAcceptedMouseButtons(QtCore.Qt.NoButton)
            sp.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
            sp.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
            sp.setAcceptHoverEvents(False)

            # Keep it behind the vector primitive
            sp.setZValue(-100)

            # Optional: if the item is currently selected, tint the sprite a bit (blue)
            if self.isSelected():
                eff = QtWidgets.QGraphicsColorizeEffect()
                eff.setColor(QtGui.QColor(64, 128, 255))
                eff.setStrength(0.28)
                sp.setGraphicsEffect(eff)
            else:
                sp.setGraphicsEffect(None)

            self._sprite = sp

        # Bounds/shape changed → update
        self.update()


    def _update_geom(self):
        self.prepareGeometryChange()
        L = max(1.0, self.params.length_mm)
        self._p1 = QtCore.QPointF(-L/2, 0); self._p2 = QtCore.QPointF(+L/2, 0); self._len=L

    def boundingRect(self) -> QtCore.QRectF:
        pad = 8
        rect = QtCore.QRectF(-self._len/2 - pad, -pad, self._len + 2*pad, 2*pad)
        return self._bounds_union_sprite(rect)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath(); path.moveTo(self._p1); path.lineTo(self._p2)
        s = QtGui.QPainterPathStroker(); s.setWidth(8)
        shp = s.createStroke(path)
        return self._shape_union_sprite(shp)


    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)

        if opt.state & QtWidgets.QStyle.State_Selected:
            halo = QtGui.QPen(QtGui.QColor(30, 144, 255, 120), 8)
            halo.setCosmetic(True)
            p.setPen(halo); p.drawLine(self._p1, self._p2)
            p.setBrush(QtCore.Qt.NoBrush)

        pen = QtGui.QPen(QtGui.QColor("royalblue"), 2); pen.setCosmetic(True)
        p.setPen(pen); p.drawLine(self._p1, self._p2)
        p.setBrush(QtGui.QColor("royalblue"))
        p.drawEllipse(QtCore.QPointF(0,0), 2, 2)


    def open_editor(self):
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent); d.setWindowTitle("Edit Lens")
        f = QtWidgets.QFormLayout(d)
        x = QtWidgets.QDoubleSpinBox(); x.setRange(-1e6,1e6); x.setDecimals(3); x.setSuffix(" mm"); x.setValue(self.pos().x())
        y = QtWidgets.QDoubleSpinBox(); y.setRange(-1e6,1e6); y.setDecimals(3); y.setSuffix(" mm"); y.setValue(self.pos().y())
        ang=QtWidgets.QDoubleSpinBox(); ang.setRange(-180,180); ang.setDecimals(2); ang.setSuffix(" °"); ang.setValue(self.rotation())
        efl=QtWidgets.QDoubleSpinBox(); efl.setRange(-1e7,1e7); efl.setDecimals(3); efl.setSuffix(" mm"); efl.setValue(self.params.efl_mm)
        length=QtWidgets.QDoubleSpinBox(); length.setRange(1,1e7); length.setDecimals(2); length.setSuffix(" mm"); length.setValue(self.params.length_mm)
        for lab,w in [("X",x),("Y",y),("Angle",ang),("EFL",efl),("Clear length",length)]: f.addRow(lab,w)
        btn=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel); f.addRow(btn)
        btn.accepted.connect(d.accept); btn.rejected.connect(d.reject)
        if d.exec_():
            self.setPos(x.value(), y.value()); self.params.x_mm=x.value(); self.params.y_mm=y.value()
            self.setRotation(ang.value()); self.params.angle_deg=ang.value()
            self.params.efl_mm=efl.value(); self.params.length_mm=length.value()
            self._update_geom(); self._maybe_attach_sprite(); self.edited.emit()

    def endpoints_scene(self) -> Tuple[np.ndarray, np.ndarray]:
        p1 = self.mapToScene(self._p1); p2 = self.mapToScene(self._p2)
        return np.array([p1.x(), p1.y()]), np.array([p2.x(), p2.y()])

    #def to_dict(self): return asdict(self.params)
    def from_dict(self, d): self.params = LensParams(**d); self.setPos(self.params.x_mm, self.params.y_mm); self.setRotation(self.params.angle_deg); self._update_geom(); self._maybe_attach_sprite(); self.edited.emit()


# -------------------- Mirror --------------------
class MirrorItem(BaseObj):
    def __init__(self, params: MirrorParams):
        super().__init__()
        self.params = params
        self._sprite: Optional[ComponentSprite] = None
        self._update_geom()
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._maybe_attach_sprite()
    def _sync_params_from_item(self):
        self.params.x_mm = float(self.pos().x())
        self.params.y_mm = float(self.pos().y())
        self.params.angle_deg = float(self.rotation())

    def to_dict(self):
        d = asdict(self.params)
        d["x_mm"] = float(self.pos().x())
        d["y_mm"] = float(self.pos().y())
        d["angle_deg"] = float(self.rotation())
        return d
    def _maybe_attach_sprite(self):
        # Our bounds/shape depend on the sprite, so notify Qt first.
        self.prepareGeometryChange()

        # Remove previous sprite if any
        old = getattr(self, "_sprite", None)
        if old is not None:
            try:
                # Detach from scene cleanly
                if old.scene() is not None:
                    old.scene().removeItem(old)
            except Exception:
                pass
        self._sprite = None

        # Create new sprite if we have all the pieces
        img = getattr(self.params, "image_path", None)
        line = getattr(self.params, "line_px", None)
        mm_per_px = float(getattr(self.params, "mm_per_pixel", 0.0) or 0.0)

        if img and line and os.path.exists(img):
            x1, y1, x2, y2 = line
            picked_len_px = max(1.0, math.hypot(x2 - x1, y2 - y1))
            picked_len_mm = picked_len_px * (mm_per_px if mm_per_px > 0 else 1.0)

            # If the decorative pick length differs from current, sync our geometry length
            if abs(self.params.length_mm - picked_len_mm) > 1e-6:
                self.params.length_mm = picked_len_mm
                # Our primitives depend on length -> rebuild them
                self._update_geom()

            # Build the underlay sprite
            sp = ComponentSprite(
                image_path=img,
                mm_per_pixel=mm_per_px if mm_per_px > 0 else 1.0,
                line_px=line,
                element_length_mm=self.params.length_mm,
                parent_item=self
            )

            # Make sure the sprite never steals input (so the parent item gets the events)
            sp.setAcceptedMouseButtons(QtCore.Qt.NoButton)
            sp.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
            sp.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
            sp.setAcceptHoverEvents(False)

            # Keep it behind the vector primitive
            sp.setZValue(-100)

            # Optional: if the item is currently selected, tint the sprite a bit (blue)
            if self.isSelected():
                eff = QtWidgets.QGraphicsColorizeEffect()
                eff.setColor(QtGui.QColor(64, 128, 255))
                eff.setStrength(0.28)
                sp.setGraphicsEffect(eff)
            else:
                sp.setGraphicsEffect(None)

            self._sprite = sp

        # Bounds/shape changed → update
        self.update()


    def _update_geom(self):
        self.prepareGeometryChange()
        L = max(1.0, self.params.length_mm)
        self._p1 = QtCore.QPointF(-L/2, 0); self._p2 = QtCore.QPointF(+L/2, 0); self._len=L

    def boundingRect(self) -> QtCore.QRectF:
        pad = 8
        rect = QtCore.QRectF(-self._len/2 - pad, -pad, self._len + 2*pad, 2*pad)
        return self._bounds_union_sprite(rect)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath(); path.moveTo(self._p1); path.lineTo(self._p2)
        s = QtGui.QPainterPathStroker(); s.setWidth(10)
        shp = s.createStroke(path)
        return self._shape_union_sprite(shp)


    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setPen(QtGui.QPen(QtGui.QColor("darkslategray"), 3))
        p.drawLine(self._p1, self._p2)

    def open_editor(self):
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent); d.setWindowTitle("Edit Mirror")
        f = QtWidgets.QFormLayout(d)
        x = QtWidgets.QDoubleSpinBox(); x.setRange(-1e6,1e6); x.setDecimals(3); x.setSuffix(" mm"); x.setValue(self.pos().x())
        y = QtWidgets.QDoubleSpinBox(); y.setRange(-1e6,1e6); y.setDecimals(3); y.setSuffix(" mm"); y.setValue(self.pos().y())
        ang=QtWidgets.QDoubleSpinBox(); ang.setRange(-180,180); ang.setDecimals(2); ang.setSuffix(" °"); ang.setValue(self.rotation())
        length=QtWidgets.QDoubleSpinBox(); length.setRange(1,1e7); length.setDecimals(2); length.setSuffix(" mm"); length.setValue(self.params.length_mm)
        for lab,w in [("X",x),("Y",y),("Angle",ang),("Length",length)]: f.addRow(lab,w)
        btn=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel); f.addRow(btn)
        btn.accepted.connect(d.accept); btn.rejected.connect(d.reject)
        if d.exec_():
            self.setPos(x.value(), y.value()); self.params.x_mm=x.value(); self.params.y_mm=y.value()
            self.setRotation(ang.value()); self.params.angle_deg=ang.value()
            self.params.length_mm=length.value(); self._update_geom(); self._maybe_attach_sprite(); self.edited.emit()

    def endpoints_scene(self) -> Tuple[np.ndarray, np.ndarray]:
        p1 = self.mapToScene(self._p1); p2 = self.mapToScene(self._p2)
        return np.array([p1.x(), p1.y()]), np.array([p2.x(), p2.y()])

    #def to_dict(self): return asdict(self.params)
    def from_dict(self, d): self.params = MirrorParams(**d); self.setPos(self.params.x_mm, self.params.y_mm); self.setRotation(self.params.angle_deg); self._update_geom(); self._maybe_attach_sprite(); self.edited.emit()


# -------------------- Beamsplitter --------------------
class BeamsplitterItem(BaseObj):
    def __init__(self, params: BeamsplitterParams):
        super().__init__()
        self.params = params
        self._sprite: Optional[ComponentSprite] = None
        self._update_geom()
        self.setPos(self.params.x_mm, self.params.y_mm)
        self.setRotation(self.params.angle_deg)
        self._maybe_attach_sprite()

    def _maybe_attach_sprite(self):
        if getattr(self, "_sprite", None):
            try:
                self.scene().removeItem(self._sprite)
            except Exception:
                pass
            self._sprite = None

        if self.params.image_path and self.params.line_px:
            x1, y1, x2, y2 = self.params.line_px
            picked_len_px = max(1.0, math.hypot(x2 - x1, y2 - y1))
            picked_len_mm = picked_len_px * (self.params.mm_per_pixel if self.params.mm_per_pixel > 0 else 1.0)
            if abs(self.params.length_mm - picked_len_mm) > 1e-6:
                self.params.length_mm = picked_len_mm
                self._update_geom()

            self._sprite = ComponentSprite(
                self.params.image_path,
                self.params.mm_per_pixel,
                self.params.line_px,
                self.params.length_mm,
                self
            )

        self.setZValue(0)

    def _update_geom(self):
        self.prepareGeometryChange()
        L = max(1.0, self.params.length_mm)
        self._p1 = QtCore.QPointF(-L/2, 0); self._p2 = QtCore.QPointF(+L/2, 0); self._len=L

    def boundingRect(self) -> QtCore.QRectF:
        pad = 8
        rect = QtCore.QRectF(-self._len/2 - pad, -pad, self._len + 2*pad, 2*pad)
        return self._bounds_union_sprite(rect)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath(); path.moveTo(self._p1); path.lineTo(self._p2)
        s = QtGui.QPainterPathStroker(); s.setWidth(10)
        shp = s.createStroke(path)
        return self._shape_union_sprite(shp)



    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setPen(QtGui.QPen(QtGui.QColor(0, 150, 120), 3))
        p.drawLine(self._p1, self._p2)

    def open_editor(self):
        parent = self._parent_window()
        d = QtWidgets.QDialog(parent); d.setWindowTitle("Edit Beamsplitter")
        f = QtWidgets.QFormLayout(d)
        x = QtWidgets.QDoubleSpinBox(); x.setRange(-1e6,1e6); x.setDecimals(3); x.setSuffix(" mm"); x.setValue(self.pos().x())
        y = QtWidgets.QDoubleSpinBox(); y.setRange(-1e6,1e6); y.setDecimals(3); y.setSuffix(" mm"); y.setValue(self.pos().y())
        ang=QtWidgets.QDoubleSpinBox(); ang.setRange(-180,180); ang.setDecimals(2); ang.setSuffix(" °"); ang.setValue(self.rotation())
        length=QtWidgets.QDoubleSpinBox(); length.setRange(1,1e7); length.setDecimals(2); length.setSuffix(" mm"); length.setValue(self.params.length_mm)
        t = QtWidgets.QDoubleSpinBox(); t.setRange(0,100); t.setDecimals(1); t.setSuffix(" %"); t.setValue(self.params.split_T)
        r = QtWidgets.QDoubleSpinBox(); r.setRange(0,100); r.setDecimals(1); r.setSuffix(" %"); r.setValue(self.params.split_R)
        def sync_from_t(val):
            r.blockSignals(True); r.setValue(max(0.0, min(100.0, 100.0 - val))); r.blockSignals(False)
        def sync_from_r(val):
            t.blockSignals(True); t.setValue(max(0.0, min(100.0, 100.0 - val))); t.blockSignals(False)
        t.valueChanged.connect(sync_from_t)
        r.valueChanged.connect(sync_from_r)

        for lab,w in [("X",x),("Y",y),("Angle",ang),("Length",length),("Split T",t),("Split R",r)]: f.addRow(lab,w)
        btn=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel); f.addRow(btn)
        btn.accepted.connect(d.accept); btn.rejected.connect(d.reject)
        if d.exec_():
            self.setPos(x.value(), y.value()); self.params.x_mm=x.value(); self.params.y_mm=y.value()
            self.setRotation(ang.value()); self.params.angle_deg=ang.value()
            self.params.length_mm=length.value()
            self.params.split_T=t.value(); self.params.split_R=r.value()
            self._update_geom(); self._maybe_attach_sprite(); self.edited.emit()

    def endpoints_scene(self) -> Tuple[np.ndarray, np.ndarray]:
        p1 = self.mapToScene(self._p1); p2 = self.mapToScene(self._p2)
        return np.array([p1.x(), p1.y()]), np.array([p2.x(), p2.y()])

   # def to_dict(self): return asdict(self.params)
    def to_dict(self):
        d = asdict(self.params)               # includes length_mm, split_T, split_R
        d["x_mm"] = float(self.pos().x())
        d["y_mm"] = float(self.pos().y())
        d["angle_deg"] = float(self.rotation())
        return d
    def from_dict(self, d): self.params = BeamsplitterParams(**d); self.setPos(self.params.x_mm, self.params.y_mm); self.setRotation(self.params.angle_deg); self._update_geom(); self._maybe_attach_sprite(); self.edited.emit()


# -------------------- Ruler & Text Items --------------------
class RulerItem(QtWidgets.QGraphicsObject):
    """
    Draggable two-point ruler that shows the distance in mm.
    - Drag endpoint bars to measure; drag elsewhere to move as a whole.
    - Right-click → Delete.
    """
    def __init__(self, p1=QtCore.QPointF(-50, 0), p2=QtCore.QPointF(50, 0)):
        super().__init__()
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable | self.ItemSendsGeometryChanges)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.setCacheMode(QtWidgets.QGraphicsItem.NoCache)  # avoid paint caching artifacts
        self.setZValue(10_000)  # keep ruler + label on top

        self._p1 = QtCore.QPointF(p1)
        self._p2 = QtCore.QPointF(p2)
        self._grab = None  # 'p1' | 'p2' | None

        # Appearance
        self._line_w = 2.0
        self._bar_w = 2.0      # bar thickness along the line
        self._bar_h = 18.0     # bar height perpendicular to the line
        self._hit_radius = 10.0
        self._pad = 90.0       # padding to fully cover label area when moving

    # ----- geometry helpers -----
    def _len(self) -> float:
        return math.hypot(self._p2.x() - self._p1.x(), self._p2.y() - self._p1.y())

    def _angle_deg(self) -> float:
        return math.degrees(math.atan2(self._p2.y() - self._p1.y(), self._p2.x() - self._p1.x()))

    # ----- QGraphicsItem overrides -----
    def boundingRect(self) -> QtCore.QRectF:
        rect = QtCore.QRectF(self._p1, self._p2).normalized()
        pad = max(self._pad, self._bar_h * 1.5)
        return rect.adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QtGui.QPainterPath:
        # baseline pick area
        path = QtGui.QPainterPath()
        path.moveTo(self._p1); path.lineTo(self._p2)
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(max(12.0, self._bar_h))
        shp = stroker.createStroke(path)

        # build perpendicular bars geometrically (no rotations)
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        L = math.hypot(dx, dy) or 1.0
        dirx, diry = dx / L, dy / L
        perpx, perpy = -diry, dirx

        def bar_poly(center: QtCore.QPointF) -> QtGui.QPainterPath:
            cx, cy = center.x(), center.y()
            hw = self._bar_w / 2.0  # half width along dir
            hh = self._bar_h / 2.0  # half height along perp

            # rectangle corners (dir ± hw) + (perp ± hh)
            p1 = QtCore.QPointF(cx + (-hw*dirx + -hh*perpx), cy + (-hw*diry + -hh*perpy))
            p2 = QtCore.QPointF(cx + ( hw*dirx + -hh*perpx), cy + ( hw*diry + -hh*perpy))
            p3 = QtCore.QPointF(cx + ( hw*dirx +  hh*perpx), cy + ( hw*diry +  hh*perpy))
            p4 = QtCore.QPointF(cx + (-hw*dirx +  hh*perpx), cy + (-hw*diry +  hh*perpy))

            poly = QtGui.QPainterPath(p1)
            poly.lineTo(p2); poly.lineTo(p3); poly.lineTo(p4); poly.closeSubpath()
            return poly

        shp = shp.united(bar_poly(self._p1)).united(bar_poly(self._p2))
        return shp
    def to_dict(self) -> Dict[str, Any]:
        # Save absolute endpoints in scene space so reopening is exact
        p1_scene = self.mapToScene(self._p1)
        p2_scene = self.mapToScene(self._p2)
        return {
            "type": "ruler",
            "p1": [float(p1_scene.x()), float(p1_scene.y())],
            "p2": [float(p2_scene.x()), float(p2_scene.y())],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RulerItem":
        p1 = QtCore.QPointF(float(d["p1"][0]), float(d["p1"][1]))
        p2 = QtCore.QPointF(float(d["p2"][0]), float(d["p2"][1]))
        # store points in item coords and keep item at origin
        return RulerItem(p1, p2)


    def paint(self, p: QtGui.QPainter, opt, widget=None):
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)

        # baseline (flat caps)
        base_pen = QtGui.QPen(QtGui.QColor(30, 30, 30), self._line_w)
        base_pen.setCosmetic(True)
        base_pen.setCapStyle(QtCore.Qt.FlatCap)
        base_pen.setJoinStyle(QtCore.Qt.MiterJoin)
        p.setPen(base_pen); p.setBrush(QtCore.Qt.NoBrush)
        p.drawLine(self._p1, self._p2)

        # vectors
        dx = self._p2.x() - self._p1.x()
        dy = self._p2.y() - self._p1.y()
        L = math.hypot(dx, dy) or 1.0
        dirx, diry = dx / L, dy / L
        perpx, perpy = -diry, dirx

        # helper to draw a bar rectangle perpendicular to the line (BLACK)
        def draw_bar(center: QtCore.QPointF):
            cx, cy = center.x(), center.y()
            hw = self._bar_w / 2.0  # along dir
            hh = self._bar_h / 2.0  # along perp
            pts = [
                QtCore.QPointF(cx + (-hw*dirx + -hh*perpx), cy + (-hw*diry + -hh*perpy)),
                QtCore.QPointF(cx + ( hw*dirx + -hh*perpx), cy + ( hw*diry + -hh*perpy)),
                QtCore.QPointF(cx + ( hw*dirx +  hh*perpx), cy + ( hw*diry +  hh*perpy)),
                QtCore.QPointF(cx + (-hw*dirx +  hh*perpx), cy + (-hw*diry +  hh*perpy)),
            ]
            poly = QtGui.QPolygonF(pts)
            p.save()
            p.setPen(QtGui.QPen(QtCore.Qt.black, 1))
            p.setBrush(QtCore.Qt.black)
            p.drawPolygon(poly)
            p.restore()

        draw_bar(self._p1)
        draw_bar(self._p2)

        # label (same anti-smear method; uses QRectF overload)
        mid = (self._p1 + self._p2) * 0.5
        txt = f"{L:.1f} mm"
        angle = math.degrees(math.atan2(dy, dx))

        p.save()
        p.translate(mid)
        p.rotate(angle)
        fm = QtGui.QFontMetrics(p.font())
        w = fm.horizontalAdvance(txt) + 12
        h = fm.height() + 6
        y_off = -(self._bar_h/2.0 + 10.0 + h)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(255, 255, 255, 240))
        p.drawRoundedRect(QtCore.QRectF(-w/2.0, y_off, float(w), float(h)), 4.0, 4.0)
        p.setPen(QtGui.QPen(QtGui.QColor(20, 20, 20)))
        p.drawText(QtCore.QRectF(-w/2.0, y_off, float(w), float(h)), QtCore.Qt.AlignCenter, txt)
        p.restore()


    # ----- interaction -----
    def _nearest_endpoint(self, pos: QtCore.QPointF) -> Optional[str]:
        if QtCore.QLineF(pos, self._p1).length() <= self._hit_radius: return 'p1'
        if QtCore.QLineF(pos, self._p2).length() <= self._hit_radius: return 'p2'
        return None

    def mousePressEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        if ev.button() == QtCore.Qt.RightButton:
            # context menu on right-click
            m = QtWidgets.QMenu()
            act_del = m.addAction("Delete")
            if m.exec_(ev.screenPos()) == act_del and self.scene():
                self.scene().removeItem(self)
            ev.accept()
            return
        which = self._nearest_endpoint(ev.pos())
        if ev.button() == QtCore.Qt.LeftButton and which:
            self._grab = which
            ev.accept()
            return
        self._grab = None
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        if self._grab == 'p1':
            self.prepareGeometryChange()
            self._p1 = ev.pos()
            self.update()
            ev.accept()
            return
        if self._grab == 'p2':
            self.prepareGeometryChange()
            self._p2 = ev.pos()
            self.update()
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        self._grab = None
        super().mouseReleaseEvent(ev)

class TextNoteItem(QtWidgets.QGraphicsTextItem):
    """
    Movable, editable text note. Double-click to edit; right-click → Delete/Edit.
    """
    def __init__(self, text="Text"):
        super().__init__(text)
        self.setFlags(self.ItemIsMovable | self.ItemIsSelectable)
        self.setDefaultTextColor(QtGui.QColor(10,10,40))
        f = self.font(); f.setPointSizeF(11.0); self.setFont(f)
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

    def mouseDoubleClickEvent(self, ev: QtWidgets.QGraphicsSceneMouseEvent):
        self.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        super().mouseDoubleClickEvent(ev)

    def focusOutEvent(self, ev: QtGui.QFocusEvent):
        super().focusOutEvent(ev)
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

    def contextMenuEvent(self, ev: QtWidgets.QGraphicsSceneContextMenuEvent):
        m = QtWidgets.QMenu()
        act_edit = m.addAction("Edit")
        act_del = m.addAction("Delete")
        a = m.exec_(ev.screenPos())
        if a == act_edit:
            self.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
            cursor = self.textCursor()
            cursor.movePosition(cursor.End)
            self.setTextCursor(cursor)
            self.setFocus()
        elif a == act_del and self.scene():
            self.scene().removeItem(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "text",
            "text": self.toPlainText(),
            "x": float(self.scenePos().x()),
            "y": float(self.scenePos().y()),
            "color": self.defaultTextColor().name(),
            "point_size": float(self.font().pointSizeF()),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TextNoteItem":
        item = TextNoteItem(d.get("text", "Text"))
        col = QtGui.QColor(d.get("color", "#0A0A28"))
        item.setDefaultTextColor(col)
        f = item.font()
        ps = d.get("point_size")
        if ps is not None:
            f.setPointSizeF(float(ps))
            item.setFont(f)
        item.setPos(float(d.get("x", 0.0)), float(d.get("y", 0.0)))
        return item
# -------------------- Ray tracer --------------------
@dataclass
class RayPath:
    points: List[np.ndarray]
    rgba: Tuple[int,int,int,int]  # color with alpha

class RayTracer2D:
    def __init__(self, scene: QtWidgets.QGraphicsScene):
        self.scene = scene

    def collect(self):
        lenses: List[LensItem] = []
        mirrors: List[MirrorItem] = []
        beamsplitters: List[BeamsplitterItem] = []
        sources: List[SourceItem] = []
        for it in self.scene.items():
            if isinstance(it, LensItem): lenses.append(it)
            elif isinstance(it, MirrorItem): mirrors.append(it)
            elif isinstance(it, BeamsplitterItem): beamsplitters.append(it)
            elif isinstance(it, SourceItem): sources.append(it)
        return lenses, mirrors, beamsplitters, sources

    def _segments(self, items):
        return [(obj, *obj.endpoints_scene()) for obj in items]

    def trace_all(self, max_events: int = 80) -> List[RayPath]:
        lenses, mirrors, beamsplitters, sources = self.collect()
        lens_segments = self._segments(lenses)
        mirror_segments = self._segments(mirrors)
        bs_segments = self._segments(beamsplitters)

        paths: List[RayPath] = []
        EPS_ADV = 1e-3  # mm advance after hit
        MIN_I = 0.02    # drop very dim branches

        for S in sources:
            # FIX: use ONLY the item's rotation (already stores pose)
            base = deg2rad(S.rotation())
            spread = deg2rad(S.params.spread_deg)

            # source base color (kept for all branches)
            src_col = qcolor_from_hex(S.params.color_hex)
            base_rgb = (src_col.red(), src_col.green(), src_col.blue())

            ys = [0.0] if (S.params.n_rays <= 1 or S.params.size_mm == 0) \
                 else list(np.linspace(-S.params.size_mm/2, S.params.size_mm/2, S.params.n_rays))
            if spread == 0 or S.params.n_rays <= 1:
                angles = [base] * len(ys)
            else:
                fan = np.linspace(-spread, +spread, len(ys))
                angles = [base + a for a in fan]

            for i, y0 in enumerate(ys):
                P0 = S.mapToScene(QtCore.QPointF(0, y0))
                P = np.array([P0.x(), P0.y()], float)
                th = angles[i]
                V = np.array([math.cos(th), math.sin(th)], float)

                # Stack of active branches: (points, P, V, remaining, last_obj, events, intensity)
                stack: List[Tuple[List[np.ndarray], np.ndarray, np.ndarray, float, Any, int, float]] = []
                stack.append(([P.copy()], P.copy(), V.copy(), S.params.ray_length_mm, None, 0, 1.0))

                while stack:
                    pts, P, V, remaining, last_obj, events, I = stack.pop()
                    if remaining <= 0 or events >= max_events or I < MIN_I:
                        if len(pts) >= 2:
                            a = int(255 * max(0.0, min(1.0, I)))
                            paths.append(RayPath(pts, (base_rgb[0], base_rgb[1], base_rgb[2], a)))
                        continue

                    nearest = (None, None, None, None, None, None, None, None)  # t,X,kind,obj,t_hat,n_hat,C,L
                    vnorm = np.linalg.norm(V)

                    # mirrors
                    for obj, A, B in mirror_segments:
                        if last_obj is obj: continue
                        res = ray_hit_element(P, V, A, B)
                        if res is None: continue
                        t, X, t_hat, n_hat, C, L = res
                        if t * vnorm > remaining: continue
                        if nearest[0] is None or t < nearest[0]:
                            nearest = (t, X, "mirror", obj, t_hat, n_hat, C, L)

                    # lenses
                    for obj, A, B in lens_segments:
                        if last_obj is obj: continue
                        res = ray_hit_element(P, V, A, B)
                        if res is None: continue
                        t, X, t_hat, n_hat, C, L = res
                        if t * vnorm > remaining: continue
                        if nearest[0] is None or t < nearest[0]:
                            nearest = (t, X, "lens", obj, t_hat, n_hat, C, L)

                    # beamsplitters
                    for obj, A, B in bs_segments:
                        if last_obj is obj: continue
                        res = ray_hit_element(P, V, A, B)
                        if res is None: continue
                        t, X, t_hat, n_hat, C, L = res
                        if t * vnorm > remaining: continue
                        if nearest[0] is None or t < nearest[0]:
                            nearest = (t, X, "bs", obj, t_hat, n_hat, C, L)

                    t, X, kind, obj, t_hat, n_hat, C, L = nearest
                    if X is None:
                        P2 = P + V * (remaining / max(1e-12, vnorm))
                        pts2 = pts + [P2.copy()]
                        a = int(255 * max(0.0, min(1.0, I)))
                        paths.append(RayPath(pts2, (base_rgb[0], base_rgb[1], base_rgb[2], a)))
                        continue

                    # advance to hit point
                    step = t * vnorm
                    P = X; pts = pts + [P.copy()]; remaining -= step

                    # make normal face incoming ray
                    if np.dot(V, n_hat) < 0:
                        n_hat = -n_hat; t_hat = -t_hat

                    if kind == "mirror":
                        V2 = normalize(reflect_vec(V, n_hat))
                        P2 = P + V2 * 1e-3
                        stack.append((pts + [P2.copy()], P2.copy(), V2, remaining - 1e-3, obj, events+1, I))
                        continue

                    if kind == "lens":
                        y = np.dot(P - C, t_hat)
                        a_n = np.dot(V, n_hat); a_t = np.dot(V, t_hat)
                        theta_in = math.atan2(a_t, a_n)
                        f = obj.params.efl_mm
                        theta_out = theta_in - (y / f) if abs(f) > 1e-12 else theta_in
                        Vloc = np.array([math.cos(theta_out), math.sin(theta_out)])
                        V2 = normalize(Vloc[0]*n_hat + Vloc[1]*t_hat)
                        P2 = P + V2 * 1e-3
                        stack.append((pts + [P2.copy()], P2.copy(), V2, remaining - 1e-3, obj, events+1, I))
                        continue

                    if kind == "bs":
                        T = getattr(obj.params, "split_T", 50.0) / 100.0
                        R = getattr(obj.params, "split_R", 50.0) / 100.0
                        T = max(0.0, min(1.0, T))
                        R = max(0.0, min(1.0, R))

                        # transmitted (straight)
                        Vt = normalize(V)
                        Pt = P + Vt * 1e-3
                        It = I * T
                        if It >= MIN_I:
                            stack.append((pts + [Pt.copy()], Pt.copy(), Vt, remaining - 1e-3, obj, events+1, It))

                        # reflected
                        Vr = normalize(reflect_vec(V, n_hat))
                        Pr = P + Vr * 1e-3
                        Ir = I * R
                        if Ir >= MIN_I:
                            stack.append((pts + [Pr.copy()], Pr.copy(), Vr, remaining - 1e-3, obj, events+1, Ir))
                        continue

        return paths


# -------------------- view / grid / scale bar --------------------
class GraphicsView(QtWidgets.QGraphicsView):
    zoomChanged = QtCore.pyqtSignal()

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        self.setViewportUpdateMode(self.BoundingRectViewportUpdate)
        self.setTransformationAnchor(self.AnchorUnderMouse)
        self.setResizeAnchor(self.AnchorUnderMouse)
        self.setDragMode(self.RubberBandDrag)
        self.setAcceptDrops(True)
        self._hand = False
        # scale bar prefs
        self._sb_len_px = 120
        self._sb_height_px = 10
        self._sb_margin_px = 10
        self._sb_font = QtGui.QFont()
        self._sb_font.setPointSize(9)
        self._ghost_item = None
        self._ghost_rec = None
    def _clear_ghost(self):
        if self._ghost_item is not None:
            try:
                # The ghost is owned by the scene; remove it safely.
                self.scene().removeItem(self._ghost_item)
            except Exception:
                pass
        self._ghost_item = None
        self._ghost_rec = None

    def _make_ghost(self, rec: dict, scene_pos: QtCore.QPointF):
        # Build the same item we’ll drop, but non-interactive & semi-transparent.
        kind = (rec.get("kind") or "lens").lower()
        name = rec.get("name")
        img = rec.get("image_path")
        mm_per_px = float(rec.get("mm_per_pixel", 0.1))
        line_px = tuple(rec.get("line_px", (0,0,1,0)))
        length_mm = float(rec.get("length_mm", 60.0))
        angle = _default_angle_for_record(rec)

        if kind == "lens":
            efl_mm = float(rec.get("efl_mm", 100.0))
            params = LensParams(
                x_mm=scene_pos.x(), y_mm=scene_pos.y(),
                angle_deg=angle, efl_mm=efl_mm, length_mm=length_mm,
                image_path=img, mm_per_pixel=mm_per_px, line_px=line_px, name=name
            )
            item = LensItem(params)
        elif kind == "beamsplitter":
            if "split_TR" in rec and isinstance(rec["split_TR"], (list, tuple)) and len(rec["split_TR"]) == 2:
                T, R = float(rec["split_TR"][0]), float(rec["split_TR"][1])
            else:
                T, R = float(rec.get("split_T", 50.0)), float(rec.get("split_R", 50.0))
            params = BeamsplitterParams(
                x_mm=scene_pos.x(), y_mm=scene_pos.y(),
                angle_deg=angle, length_mm=length_mm,
                split_T=T, split_R=R,
                image_path=img, mm_per_pixel=mm_per_px, line_px=line_px, name=name
            )
            item = BeamsplitterItem(params)
        elif kind == "mirror":
            params = MirrorParams(
                x_mm=scene_pos.x(), y_mm=scene_pos.y(),
                angle_deg=angle, length_mm=length_mm,
                image_path=img, mm_per_pixel=mm_per_px, line_px=line_px, name=name
            )
            item = MirrorItem(params)
        else:
            # Fallback (just in case)
            params = MirrorParams(
                x_mm=scene_pos.x(), y_mm=scene_pos.y(),
                angle_deg=angle, length_mm=length_mm,
                image_path=img, mm_per_pixel=mm_per_px, line_px=line_px, name=name
            )
            item = MirrorItem(params)

        # Make it a non-interactive “ghost”
        item.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        item.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        item.setOpacity(0.7)
        item.setZValue(9_999)  # above almost everything, below the ruler (10_000) if you like

        # Ensure the decorative sprite is visible on the ghost
        try:
            item._maybe_attach_sprite()
        except Exception:
            pass

        self.scene().addItem(item)
        self._ghost_item = item
        self._ghost_rec = dict(rec)  # keep a copy so we can reuse on move

    
    # --- zoom/pan ---
    def wheelEvent(self, e: QtGui.QWheelEvent):
        factor = 1.15 if e.angleDelta().y() > 0 else 1/1.15
        self.scale(factor, factor); e.accept()
        self.zoomChanged.emit()
        self.viewport().update()

    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        self.zoomChanged.emit()
        self.viewport().update()

    # --- drag&drop for components ---
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        if e.mimeData().hasFormat("application/x-optics-component"):
            e.acceptProposedAction()
            # Build a ghost right away so the moment you cross into the canvas you see it
            try:
                rec = json.loads(bytes(e.mimeData().data("application/x-optics-component")).decode("utf-8"))
                self._clear_ghost()
                self._make_ghost(rec, self.mapToScene(e.pos()))
            except Exception:
                pass
        else:
            e.ignore()

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        if e.mimeData().hasFormat("application/x-optics-component"):
            e.acceptProposedAction()
            # Move the ghost with the pointer; if it doesn’t exist yet, (re)create it
            try:
                if self._ghost_item is None:
                    rec = json.loads(bytes(e.mimeData().data("application/x-optics-component")).decode("utf-8"))
                    self._make_ghost(rec, self.mapToScene(e.pos()))
                else:
                    self._ghost_item.setPos(self.mapToScene(e.pos()))
            except Exception:
                pass
        else:
            e.ignore()

    def dragLeaveEvent(self, e: QtGui.QDragLeaveEvent):
        self._clear_ghost()
        e.accept()

    def dropEvent(self, e: QtGui.QDropEvent):
        if not e.mimeData().hasFormat("application/x-optics-component"):
            e.ignore(); return
        data = e.mimeData().data("application/x-optics-component")
        try:
            rec = json.loads(bytes(data).decode("utf-8"))
        except Exception:
            e.ignore(); return

        # Finalize: remove ghost and create the real object (same orientation defaults)
        self._clear_ghost()

        # Ensure we drop with the same default angle we previewed
        if "angle_deg" not in rec:
            rec = dict(rec)  # copy then inject the angle we used for ghost
            rec["angle_deg"] = _default_angle_for_record(rec)

        scene_pos = self.mapToScene(e.pos())
        self.parent().on_drop_component(rec, scene_pos)
        e.acceptProposedAction()


    # --- pan with space/middle button ---
    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if e.key() in (QtCore.Qt.Key_Plus, QtCore.Qt.Key_Equal):
            self.scale(1.15, 1.15); self.zoomChanged.emit(); self.viewport().update(); return
        if e.key() in (QtCore.Qt.Key_Minus, QtCore.Qt.Key_Underscore):
            self.scale(1/1.15, 1/1.15); self.zoomChanged.emit(); self.viewport().update(); return
        if e.key() == QtCore.Qt.Key_Space:
            self._hand = True; self.setDragMode(self.ScrollHandDrag); return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QtGui.QKeyEvent):
        if e.key() == QtCore.Qt.Key_Space and self._hand:
            self._hand = False; self.setDragMode(self.RubberBandDrag); return
        super().keyReleaseEvent(e)

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.MiddleButton:
            self.setDragMode(self.ScrollHandDrag)
            fake = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, e.localPos(),
                                     QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, e.modifiers())
            super().mousePressEvent(fake)
        else:
            super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.MiddleButton:
            fake = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, e.localPos(),
                                     QtCore.Qt.LeftButton, QtCore.Qt.NoButton, e.modifiers())
            super().mouseReleaseEvent(fake); self.setDragMode(self.RubberBandDrag)
        else:
            super().mouseReleaseEvent(e)

    # --- view overlay: scale bar ---
    def drawForeground(self, painter: QtGui.QPainter, rect: QtCore.QRectF):
        painter.save()
        painter.resetTransform()

        vsize = self.viewport().size()
        box_w = self._sb_len_px + 70
        box_h = self._sb_height_px + 22
        x0 = self._sb_margin_px
        y0 = vsize.height() - box_h - self._sb_margin_px

        # pixels per mm = m11
        px_per_mm = max(1e-12, self.transform().m11())
        mm_value = self._sb_len_px / px_per_mm

        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(QtGui.QPen(QtGui.QColor(0,0,0,90)))
        painter.setBrush(QtGui.QColor(255,255,255,200))
        painter.drawRoundedRect(x0, y0, box_w, box_h, 6, 6)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(30,30,30))
        painter.drawRect(x0+12, y0+11, self._sb_len_px, self._sb_height_px)

        painter.setPen(QtGui.QColor(20,20,20))
        painter.setFont(self._sb_font)
        label = f"{mm_value:.1f} mm"
        painter.drawText(x0+12+self._sb_len_px+8, y0+11+self._sb_height_px, label)

        painter.restore()


# -------------------- property dock --------------------
class PropertyDock(QtWidgets.QWidget):
    edited = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.form = QtWidgets.QFormLayout(self)
        self.inputs: Dict[str, QtWidgets.QWidget] = {}
    def clear(self):
        while self.form.count():
            it = self.form.takeAt(0); w = it.widget()
            if w: w.deleteLater()
        self.inputs.clear()
    def bind_object(self, obj: BaseObj):
        self.clear()
        rows: List[Tuple[str, QtWidgets.QWidget]] = []
        def dsb(v, mn=-1e6, mx=1e6, dec=3, suf=" mm"):
            sb = QtWidgets.QDoubleSpinBox(); sb.setRange(mn,mx); sb.setDecimals(dec); sb.setSuffix(suf); sb.setValue(v); return sb
        rows.append(("X", dsb(obj.pos().x())))
        rows.append(("Y", dsb(obj.pos().y())))
        rows.append(("Angle", dsb(obj.rotation(), mn=-180, mx=180, dec=2, suf=" °")))
        if isinstance(obj, SourceItem):
            p = obj.params
            nr = QtWidgets.QSpinBox(); nr.setRange(1,2001); nr.setValue(p.n_rays)
            rows += [("Aperture size", dsb(p.size_mm)),
                     ("# Rays", nr),
                     ("Ray length", dsb(p.ray_length_mm)),
                     ("Angular spread (±)", dsb(p.spread_deg, mn=0, mx=89.9, dec=2, suf=" °"))]
            # Color picker in dock
            color_btn = QtWidgets.QToolButton(); color_btn.setText("Pick…")
            color_show = QtWidgets.QLabel(p.color_hex)
            chip = QtWidgets.QLabel()
            def paint_chip(lbl, hexstr):
                pm = QtGui.QPixmap(40, 16); pm.fill(QtCore.Qt.transparent)
                painter = QtGui.QPainter(pm); painter.fillRect(0,0,40,16, qcolor_from_hex(hexstr)); painter.end()
                lbl.setPixmap(pm)
            paint_chip(chip, p.color_hex)
            def pick_color():
                c = QtWidgets.QColorDialog.getColor(qcolor_from_hex(p.color_hex), self, "Choose Ray Color",
                                                    QtWidgets.QColorDialog.DontUseNativeDialog)
                if c.isValid():
                    color_show.setText(c.name())
                    paint_chip(chip, c.name())
                    self.inputs["_picked_color"] = c  # stash temporarily
            roww = QtWidgets.QHBoxLayout()
            roww.addWidget(color_btn); roww.addWidget(color_show); roww.addWidget(chip); roww.addStretch(1)
            wrap = QtWidgets.QWidget(); wrap.setLayout(roww)
            color_btn.clicked.connect(pick_color)
            self.form.addRow("Ray color", wrap)
        if isinstance(obj, LensItem):
            p = obj.params
            rows += [("EFL", dsb(p.efl_mm)),
                     ("Clear length", dsb(p.length_mm))]
        if isinstance(obj, MirrorItem):
            p = obj.params
            rows += [("Length", dsb(p.length_mm))]
        if isinstance(obj, BeamsplitterItem):
            p = obj.params
            t = dsb(p.split_T, mn=0, mx=100, dec=1, suf=" %")
            r = dsb(p.split_R, mn=0, mx=100, dec=1, suf=" %")
            rows += [("Length", dsb(p.length_mm)),
                     ("Split T", t),
                     ("Split R", r)]
        for lab, w in rows:
            self.form.addRow(lab, w); self.inputs[lab] = w
        btn = QtWidgets.QPushButton("Apply"); self.form.addRow(btn)
        def apply():
            try:
                x = self.inputs["X"].value(); y = self.inputs["Y"].value(); ang = self.inputs["Angle"].value()
                obj.setPos(x, y); obj.setRotation(ang)
                if isinstance(obj, SourceItem):
                    p = obj.params; p.x_mm, p.y_mm, p.angle_deg = x, y, ang
                    p.size_mm = self.inputs["Aperture size"].value()
                    p.n_rays  = self.inputs["# Rays"].value()
                    p.ray_length_mm = self.inputs["Ray length"].value()
                    p.spread_deg = self.inputs["Angular spread (±)"].value()
                    if "_picked_color" in self.inputs:
                        c: QtGui.QColor = self.inputs["_picked_color"]
                        p.color_hex = c.name()
                        obj._color = c
                    obj._update_shape()
                elif isinstance(obj, LensItem):
                    p = obj.params; p.x_mm, p.y_mm, p.angle_deg = x, y, ang
                    p.efl_mm = self.inputs["EFL"].value()
                    p.length_mm = self.inputs["Clear length"].value()
                    obj._update_geom(); obj._maybe_attach_sprite()
                elif isinstance(obj, MirrorItem):
                    p = obj.params; p.x_mm, p.y_mm, p.angle_deg = x, y, ang
                    p.length_mm = self.inputs["Length"].value()
                    obj._update_geom(); obj._maybe_attach_sprite()
                elif isinstance(obj, BeamsplitterItem):
                    p = obj.params; p.x_mm, p.y_mm, p.angle_deg = x, y, ang
                    p.length_mm = self.inputs["Length"].value()
                    p.split_T = self.inputs["Split T"].value()
                    p.split_R = self.inputs["Split R"].value()
                    obj._update_geom(); obj._maybe_attach_sprite()
                obj.edited.emit(); self.edited.emit()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Apply error", str(e))
        btn.clicked.connect(apply)


# -------------------- Library Dock --------------------
class LibraryList(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QtWidgets.QListView.IconMode)
        self.setIconSize(QtCore.QSize(80,80))
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setMovement(QtWidgets.QListView.Static)
        self.setSpacing(8)
        self.setDragEnabled(True)
        self.setSelectionMode(self.SingleSelection)
        self.setWordWrap(True)

    def startDrag(self, actions):
        it = self.currentItem()
        if not it: return
        payload = it.data(QtCore.Qt.UserRole)
        md = QtCore.QMimeData()
        md.setData("application/x-optics-component", json.dumps(payload).encode("utf-8"))
        drag = QtGui.QDrag(self)
        drag.setMimeData(md)
        drag.setHotSpot(QtCore.QPoint(10,10))
        pm = QtGui.QPixmap(1, 1)
        pm.fill(QtCore.Qt.transparent)
        drag.setPixmap(pm)              # <- hide OS-level drag image
        drag.setHotSpot(QtCore.QPoint(0, 0))       
        drag.exec_(QtCore.Qt.CopyAction)


# -------------------- main window --------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D Ray Optics Sandbox — Top View (mm/cm grid)")
        self.resize(1450, 860)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.scene.setSceneRect(-600, -350, 1200, 700)

        self.view = GraphicsView(self.scene)
        self.view.parent = lambda: self  # callback used in dropEvent
        self.setCentralWidget(self.view)

        self.snap_to_grid = True
        self._ray_width_px = 2.0
        self.ray_items: List[QtWidgets.QGraphicsPathItem] = []
        self.autotrace = True

        self._draw_grid()
        # self._build_toolbar()   # ← remove this line
        self._build_actions()
        self._build_menubar()
        self._build_dock()
        self._build_library_dock()


        self.scene.installEventFilter(self)

        self._placing_ruler = False
        self._ruler_p1_scene: Optional[QtCore.QPointF] = None
        self._prev_cursor = None
    def _build_actions(self):
        # --- File ---
        self.act_open = QtWidgets.QAction("Open Assembly…", self)
        self.act_open.setShortcut(QtGui.QKeySequence.Open)
        self.act_open.triggered.connect(self.open_assembly)

        self.act_save = QtWidgets.QAction("Save Assembly…", self)
        self.act_save.setShortcut(QtGui.QKeySequence.Save)
        self.act_save.triggered.connect(self.save_assembly)

        # --- Insert ---
        self.act_add_source = QtWidgets.QAction("Source", self);           self.act_add_source.triggered.connect(self.add_source)
        self.act_add_lens   = QtWidgets.QAction("Lens", self);             self.act_add_lens.triggered.connect(self.add_lens)
        self.act_add_mirror = QtWidgets.QAction("Mirror", self);           self.act_add_mirror.triggered.connect(self.add_mirror)
        self.act_add_bs     = QtWidgets.QAction("Beamsplitter", self);     self.act_add_bs.triggered.connect(self.add_bs)
        self.act_add_ruler  = QtWidgets.QAction("Ruler", self);            self.act_add_ruler.triggered.connect(self.start_place_ruler)
        self.act_add_text   = QtWidgets.QAction("Text", self);             self.act_add_text.triggered.connect(self.add_text)

        # --- View ---
        self.act_zoom_in  = QtWidgets.QAction("Zoom In", self);            self.act_zoom_in.setShortcut(QtGui.QKeySequence.ZoomIn)
        self.act_zoom_in.triggered.connect(lambda: (self.view.scale(1.15,1.15), self.view.zoomChanged.emit()))
        self.act_zoom_out = QtWidgets.QAction("Zoom Out", self);           self.act_zoom_out.setShortcut(QtGui.QKeySequence.ZoomOut)
        self.act_zoom_out.triggered.connect(lambda: (self.view.scale(1/1.15,1/1.15), self.view.zoomChanged.emit()))
        self.act_fit      = QtWidgets.QAction("Fit Scene", self);          self.act_fit.setShortcut("Ctrl+0")
        self.act_fit.triggered.connect(lambda: (self.view.fitInView(self.scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio), self.view.zoomChanged.emit()))

        # Checkable options
        self.act_autotrace = QtWidgets.QAction("Auto-trace", self, checkable=True)
        self.act_autotrace.setChecked(True)
        self.act_autotrace.toggled.connect(self._toggle_autotrace)

        self.act_snap = QtWidgets.QAction("Snap to mm grid", self, checkable=True)
        self.act_snap.setChecked(True)
        self.act_snap.toggled.connect(self._toggle_snap)

        # Ray width submenu with presets + Custom…
        self.menu_raywidth = QtWidgets.QMenu("Ray width", self)
        self._raywidth_group = QtWidgets.QActionGroup(self); self._raywidth_group.setExclusive(True)
        for v in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]:
            a = self.menu_raywidth.addAction(f"{v:.1f} px"); a.setCheckable(True)
            if abs(v - self._ray_width_px) < 1e-9: a.setChecked(True)
            a.triggered.connect(lambda _, vv=v: self._set_ray_width(vv))
            self._raywidth_group.addAction(a)
        self.menu_raywidth.addSeparator()
        a_custom = self.menu_raywidth.addAction("Custom…")
        a_custom.triggered.connect(self._choose_ray_width)

        # --- Tools ---
        self.act_retrace = QtWidgets.QAction("Retrace", self);             self.act_retrace.setShortcut("Space")
        self.act_retrace.triggered.connect(self.retrace)
        self.act_clear   = QtWidgets.QAction("Clear Rays", self);          self.act_clear.triggered.connect(self.clear_rays)
        self.act_editor  = QtWidgets.QAction("Component Editor…", self);   self.act_editor.setShortcut("Ctrl+E")
        self.act_editor.triggered.connect(self.open_component_editor)
        self.act_reload  = QtWidgets.QAction("Reload Library", self);      self.act_reload.triggered.connect(self.populate_library)

    def _build_menubar(self):
        mb = self.menuBar()

        mFile = mb.addMenu("&File")
        mFile.addAction(self.act_open)
        mFile.addAction(self.act_save)

        mInsert = mb.addMenu("&Insert")
        mInsert.addAction(self.act_add_source)
        mInsert.addAction(self.act_add_lens)
        mInsert.addAction(self.act_add_mirror)
        mInsert.addAction(self.act_add_bs)
        mInsert.addSeparator()
        mInsert.addAction(self.act_add_ruler)
        mInsert.addAction(self.act_add_text)

        mView = mb.addMenu("&View")
        mView.addAction(self.act_zoom_in)
        mView.addAction(self.act_zoom_out)
        mView.addAction(self.act_fit)
        mView.addSeparator()
        mView.addAction(self.act_autotrace)
        mView.addAction(self.act_snap)
        mView.addMenu(self.menu_raywidth)

        mTools = mb.addMenu("&Tools")
        mTools.addAction(self.act_retrace)
        mTools.addAction(self.act_clear)
        mTools.addSeparator()
        mTools.addAction(self.act_editor)
        mTools.addAction(self.act_reload)

    def _choose_ray_width(self):
        v, ok = QtWidgets.QInputDialog.getDouble(self, "Ray width", "Width (px):",
                                                float(self._ray_width_px), 0.5, 20.0, 1)
        if ok:
            self._set_ray_width(v)
            # update checked state in presets if it matches one
            for act in self._raywidth_group.actions():
                act.setChecked(abs(float(act.text().split()[0]) - v) < 1e-9)

    def _build_menubar(self):
        mb = self.menuBar()

        mFile = mb.addMenu("&File")
        mFile.addAction(self.act_open)
        mFile.addAction(self.act_save)

        mInsert = mb.addMenu("&Insert")
        for a in (self.act_add_source, self.act_add_lens, self.act_add_mirror, self.act_add_bs,
                self.act_add_ruler, self.act_add_text):
            mInsert.addAction(a)

        mView = mb.addMenu("&View")
        for a in (self.act_zoom_in, self.act_zoom_out, self.act_fit):
            mView.addAction(a)

        mTools = mb.addMenu("&Tools")
        for a in (self.act_retrace, self.act_clear, self.act_editor, self.act_reload):
            mTools.addAction(a)

    # ----- grid -----
    def _draw_grid(self):
        minor_pen = QtGui.QPen(QtGui.QColor(242, 242, 242))
        major_pen = QtGui.QPen(QtGui.QColor(215, 215, 215))
        axis_pen  = QtGui.QPen(QtGui.QColor(170, 170, 170)); axis_pen.setStyle(QtCore.Qt.DashLine)
        for pen in (minor_pen, major_pen, axis_pen):
            pen.setCosmetic(True); pen.setWidth(1)
        rect = self.scene.sceneRect()
        xmin, xmax = int(rect.left())-1000, int(rect.right())+1000
        ymin, ymax = int(rect.top())-1000, int(rect.bottom())+1000
        for x in range(xmin, xmax+1, 1):
            self.scene.addLine(x, ymin, x, ymax, major_pen if x % 10 == 0 else minor_pen)
        for y in range(ymin, ymax+1, 1):
            self.scene.addLine(xmin, y, xmax, y, major_pen if y % 10 == 0 else minor_pen)
        self.scene.addLine(-10000, 0, 10000, 0, axis_pen)
        self.scene.addLine(0, -10000, 0, 10000, axis_pen)

    # ----- UI -----
    def _build_toolbar(self):
        tb = self.addToolBar("Tools"); tb.setMovable(False)

        # Add actions (store on self so we can reuse in menus)
        self.act_add_source = QtWidgets.QAction("Add Source", self); self.act_add_source.triggered.connect(self.add_source); tb.addAction(self.act_add_source)
        self.act_add_lens   = QtWidgets.QAction("Add Lens",   self); self.act_add_lens.triggered.connect(self.add_lens);   tb.addAction(self.act_add_lens)
        self.act_add_mirror = QtWidgets.QAction("Add Mirror", self); self.act_add_mirror.triggered.connect(self.add_mirror); tb.addAction(self.act_add_mirror)
        self.act_add_bs     = QtWidgets.QAction("Add Beamsplitter", self); self.act_add_bs.triggered.connect(self.add_bs); tb.addAction(self.act_add_bs)

        tb.addSeparator()
        self.act_add_ruler  = QtWidgets.QAction("Add Ruler", self);  self.act_add_ruler.triggered.connect(self.start_place_ruler); tb.addAction(self.act_add_ruler)
        self.act_add_text   = QtWidgets.QAction("Add Text",  self);  self.act_add_text.triggered.connect(self.add_text); tb.addAction(self.act_add_text)

        tb.addSeparator()
        self.act_retrace = QtWidgets.QAction("Retrace (Space)", self); self.act_retrace.triggered.connect(self.retrace); tb.addAction(self.act_retrace)
        self.act_clear   = QtWidgets.QAction("Clear Rays",       self); self.act_clear.triggered.connect(self.clear_rays); tb.addAction(self.act_clear)

        tb.addSeparator()
        self.act_zoom_in  = QtWidgets.QAction("Zoom In (+)",  self);  self.act_zoom_in.triggered.connect(lambda: (self.view.scale(1.15,1.15), self.view.zoomChanged.emit())); tb.addAction(self.act_zoom_in)
        self.act_zoom_out = QtWidgets.QAction("Zoom Out (-)", self);  self.act_zoom_out.triggered.connect(lambda: (self.view.scale(1/1.15,1/1.15), self.view.zoomChanged.emit())); tb.addAction(self.act_zoom_out)
        self.act_fit      = QtWidgets.QAction("Fit",          self);  self.act_fit.triggered.connect(lambda: (self.view.fitInView(self.scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio), self.view.zoomChanged.emit())); tb.addAction(self.act_fit)

        tb.addSeparator()
        self.auto_chk = QtWidgets.QCheckBox("Auto-trace"); self.auto_chk.setChecked(True); self.auto_chk.toggled.connect(self._toggle_autotrace); tb.addWidget(self.auto_chk)
        self.snap_chk = QtWidgets.QCheckBox("Snap (mm)");  self.snap_chk.setChecked(True);  self.snap_chk.toggled.connect(self._toggle_snap); tb.addWidget(self.snap_chk)

        tb.addSeparator()
        tb.addWidget(QtWidgets.QLabel("Ray width "))
        spin = QtWidgets.QDoubleSpinBox(); spin.setRange(0.5, 6.0); spin.setSingleStep(0.5); spin.setValue(self._ray_width_px)
        tb.addWidget(spin); spin.valueChanged.connect(self._set_ray_width)

        tb.addSeparator()
        self.act_open   = QtWidgets.QAction("Open Assembly…", self); self.act_open.setShortcut(QtGui.QKeySequence.Open); self.act_open.triggered.connect(self.open_assembly); tb.addAction(self.act_open)
        self.act_save   = QtWidgets.QAction("Save Assembly…", self); self.act_save.setShortcut(QtGui.QKeySequence.Save); self.act_save.triggered.connect(self.save_assembly); tb.addAction(self.act_save)

        tb.addSeparator()
        self.act_editor = QtWidgets.QAction("Component Editor…", self)
        # Handy shortcut (Cmd+E on macOS, Ctrl+E elsewhere)
        self.act_editor.setShortcut(QtGui.QKeySequence("Ctrl+E"))
        self.act_editor.triggered.connect(self.open_component_editor)
        tb.addAction(self.act_editor)

        self.act_reload = QtWidgets.QAction("Reload Library", self); self.act_reload.triggered.connect(self.populate_library); tb.addAction(self.act_reload)

        # Also expose in a menu so it’s always reachable (no popup)
        self._build_menubar()


    def _build_dock(self):
        self.propDock = QtWidgets.QDockWidget("Properties", self)
        self.propDock.setObjectName("propDock")
        self.propPanel = PropertyDock(self)
        self.propPanel.edited.connect(self._maybe_retrace)
        self.propDock.setWidget(self.propPanel)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.propDock)

    def _build_library_dock(self):
        self.libDock = QtWidgets.QDockWidget("Component Library", self)
        self.libDock.setObjectName("libDock")
        self.libraryList = LibraryList(self)
        self.libDock.setWidget(self.libraryList)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.libDock)
        self.tabifyDockWidget(self.propDock, self.libDock)
        self.populate_library()

    def populate_library(self):
        self.libraryList.clear()
        records = self.load_library_records()
        for rec in records:
            name = rec.get("name","(unnamed)")
            img = rec.get("image_path")
            kind = rec.get("kind","lens")
            icon = QtGui.QIcon(img) if img and os.path.exists(img) else self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
            item = QtWidgets.QListWidgetItem(icon, f"{name}\n({kind})")
            item.setData(QtCore.Qt.UserRole, rec)
            self.libraryList.addItem(item)

    def load_library_records(self):
        try:
            with open(LIBRARY_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _set_ray_width(self, v):
        self._ray_width_px = float(v)
        if self.autotrace: self.retrace()

    def _toggle_autotrace(self, on: bool):
        self.autotrace = on
        if on: self.retrace()

    def _toggle_snap(self, on: bool):
        self.snap_to_grid = on

    # ----- add objects -----
    def add_source(self):
        s = SourceItem(SourceParams())
        self.scene.addItem(s); s.edited.connect(self._maybe_retrace)
        s.setSelected(True); self.propPanel.bind_object(s)
        if self.autotrace: self.retrace()

    def add_lens(self):
        L = LensItem(LensParams())
        self.scene.addItem(L); L._maybe_attach_sprite()
        L.edited.connect(self._maybe_retrace)
        L.setSelected(True); self.propPanel.bind_object(L)
        if self.autotrace: self.retrace()

    def add_mirror(self):
        M = MirrorItem(MirrorParams())
        self.scene.addItem(M); M._maybe_attach_sprite()
        M.edited.connect(self._maybe_retrace)
        M.setSelected(True); self.propPanel.bind_object(M)
        if self.autotrace: self.retrace()

    def add_bs(self):
        B = BeamsplitterItem(BeamsplitterParams())
        self.scene.addItem(B); B._maybe_attach_sprite()
        B.edited.connect(self._maybe_retrace)
        B.setSelected(True); self.propPanel.bind_object(B)
        if self.autotrace: self.retrace()

    def add_ruler(self):
        center = self.view.mapToScene(self.view.viewport().rect().center())
        R = RulerItem(QtCore.QPointF(-50, 0), QtCore.QPointF(50, 0))
        R.setPos(center)
        self.scene.addItem(R)

    def add_text(self):
        center = self.view.mapToScene(self.view.viewport().rect().center())
        T = TextNoteItem("Text")
        T.setPos(center)
        self.scene.addItem(T)

    # Drop handler from GraphicsView
    def on_drop_component(self, rec: dict, scene_pos: QtCore.QPointF):
        kind = rec.get("kind","lens")
        name = rec.get("name")
        img = rec.get("image_path")
        mm_per_px = float(rec.get("mm_per_pixel", 0.1))
        line_px = tuple(rec.get("line_px", (0,0,1,0)))
        length_mm = float(rec.get("length_mm", 60.0))
        angle = float(rec.get("angle_deg", _default_angle_for_record(rec)))

        if kind == "lens":
            efl_mm = float(rec.get("efl_mm", 100.0))
            params = LensParams(
                x_mm=scene_pos.x(), y_mm=scene_pos.y(),
                angle_deg=angle, efl_mm=efl_mm, length_mm=length_mm,
                image_path=img, mm_per_pixel=mm_per_px, line_px=line_px, name=name
            )
            item = LensItem(params)

        elif kind == "beamsplitter":
            if "split_TR" in rec and isinstance(rec["split_TR"], (list, tuple)) and len(rec["split_TR"]) == 2:
                T, R = float(rec["split_TR"][0]), float(rec["split_TR"][1])
            else:
                T, R = float(rec.get("split_T", 50.0)), float(rec.get("split_R", 50.0))
            params = BeamsplitterParams(
                x_mm=scene_pos.x(), y_mm=scene_pos.y(),
                angle_deg=angle, length_mm=length_mm,
                split_T=T, split_R=R,
                image_path=img, mm_per_pixel=mm_per_px, line_px=line_px, name=name
            )
            item = BeamsplitterItem(params)

        else:  # mirror
            params = MirrorParams(
                x_mm=scene_pos.x(), y_mm=scene_pos.y(),
                angle_deg=angle, length_mm=length_mm,
                image_path=img, mm_per_pixel=mm_per_px, line_px=line_px, name=name
            )
            item = MirrorItem(params)

        self.scene.addItem(item)
        item._maybe_attach_sprite()
        item.edited.connect(self._maybe_retrace)
        item.setSelected(True)
        self.propPanel.bind_object(item)
        if self.autotrace: self.retrace()


    # ----- rays -----
    def clear_rays(self):
        for it in self.ray_items: self.scene.removeItem(it)
        self.ray_items.clear()

    def retrace(self):
        self.clear_rays()
        tracer = RayTracer2D(self.scene)
        for p in tracer.trace_all(max_events=80):
            if len(p.points) < 2:
                continue
            path = QtGui.QPainterPath(QtCore.QPointF(p.points[0][0], p.points[0][1]))
            for q in p.points[1:]:
                path.lineTo(q[0], q[1])
            item = QtWidgets.QGraphicsPathItem(path)
            r,g,b,a = p.rgba
            pen = QtGui.QPen(QtGui.QColor(r,g,b,a))
            pen.setWidthF(self._ray_width_px)
            pen.setCosmetic(True)
            item.setPen(pen)
            item.setZValue(10)
            self.scene.addItem(item)
            self.ray_items.append(item)

    def _maybe_retrace(self):
        if self.autotrace: self.retrace()

    def open_component_editor(self):
        try:
            from component_editor import ComponentEditor
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import error", f"Could not import component_editor.py:\n{e}")
            return
        self._comp_editor = ComponentEditor()
        self._comp_editor.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self._comp_editor.saved.connect(self.populate_library)
        self._comp_editor.show()

    # ----- save / open assembly -----
    def save_assembly(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Assembly", "", "Optics Assembly (*.json)")
        if not path: return

        data = {
            "sources": [], "lenses": [], "mirrors": [], "beamsplitters": [],
            "rulers": [], "texts": []
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
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Assembly", "", "Optics Assembly (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Open error", str(e)); return

        # remove existing optical objects (keep grid lines)
        for it in list(self.scene.items()):
            if isinstance(it, (SourceItem, LensItem, MirrorItem, BeamsplitterItem, RulerItem, TextNoteItem)):
                self.scene.removeItem(it)

        # re-create everything
        for d in data.get("sources", []):
            s = SourceItem(SourceParams(**d)); self.scene.addItem(s); s.edited.connect(self._maybe_retrace)
        for d in data.get("lenses", []):
            L = LensItem(LensParams(**d)); self.scene.addItem(L); L._maybe_attach_sprite(); L.edited.connect(self._maybe_retrace)
        for d in data.get("mirrors", []):
            M = MirrorItem(MirrorParams(**d)); self.scene.addItem(M); M._maybe_attach_sprite(); M.edited.connect(self._maybe_retrace)
        for d in data.get("beamsplitters", []):
            B = BeamsplitterItem(BeamsplitterParams(**d)); self.scene.addItem(B); B._maybe_attach_sprite(); B.edited.connect(self._maybe_retrace)
        for d in data.get("rulers", []):
            R = RulerItem.from_dict(d); self.scene.addItem(R)
        for d in data.get("texts", []):
            T = TextNoteItem.from_dict(d); self.scene.addItem(T)

        self.retrace()

    def start_place_ruler(self):
        # enter placement mode: next two left-clicks in the scene pick p1 and p2
        self._placing_ruler = True
        self._ruler_p1_scene = None
        self._prev_cursor = self.view.cursor()
        self.view.setCursor(QtCore.Qt.CrossCursor)
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), "Click start point, then end point")

    def _finish_place_ruler(self):
        self._placing_ruler = False
        self._ruler_p1_scene = None
        if self._prev_cursor is not None:
            self.view.setCursor(self._prev_cursor)
            self._prev_cursor = None

    # snap to grid on release; live retrace on interactions
    def eventFilter(self, obj, ev):
        et = ev.type()
            # --- Ruler 2-click placement ---
        if self._placing_ruler and et == QtCore.QEvent.GraphicsSceneMousePress:
            mev = ev  # QGraphicsSceneMouseEvent
            if mev.button() == QtCore.Qt.LeftButton:
                scene_pt = mev.scenePos()
                if self._ruler_p1_scene is None:
                    # first click
                    self._ruler_p1_scene = QtCore.QPointF(scene_pt)
                    return True  # consume
                else:
                    # second click -> create ruler in item coords
                    p1 = QtCore.QPointF(self._ruler_p1_scene)
                    p2 = QtCore.QPointF(scene_pt)

                    # RulerItem interprets its points in *item* coordinates.
                    # We’ll place the item at the origin so scene==item coords.
                    R = RulerItem(p1, p2)
                    R.setPos(0, 0)
                    self.scene.addItem(R)
                    R.setSelected(True)
                    self._finish_place_ruler()
                    return True  # consume
            elif mev.button() == QtCore.Qt.RightButton:
                # cancel placement on right-click
                self._finish_place_ruler()
                return True
        if et == QtCore.QEvent.GraphicsSceneMouseRelease:
            for it in self.scene.selectedItems():
                if isinstance(it, BaseObj) and self.snap_to_grid:
                    p = it.pos(); it.setPos(round(p.x()), round(p.y()))
            if self.autotrace: QtCore.QTimer.singleShot(0, self.retrace)
        elif et in (QtCore.QEvent.GraphicsSceneMouseMove,
                    QtCore.QEvent.GraphicsSceneWheel,
                    QtCore.QEvent.GraphicsSceneDragLeave,
                    QtCore.QEvent.GraphicsSceneDrop):
            if self.autotrace: QtCore.QTimer.singleShot(0, self.retrace)
        return super().eventFilter(obj, ev)
        
    # ensure clean shutdown
    def closeEvent(self, e: QtGui.QCloseEvent):
        try:
            if hasattr(self, "_comp_editor") and self._comp_editor:
                self._comp_editor.close()
        except Exception:
            pass
        super().closeEvent(e)


# -------------------- crash hook & main --------------------
def excepthook(exc_type, exc, tb):
    msg = "".join(traceback.format_exception(exc_type, exc, tb))
    print(msg, file=sys.stderr)
    QtWidgets.QMessageBox.critical(None, "Unhandled exception", msg)

def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    sys.excepthook = excepthook
    w = MainWindow(); w.show()
    app.lastWindowClosed.connect(app.quit)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()