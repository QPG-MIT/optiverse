from __future__ import annotations

import os
import json
import re
import time
from typing import Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import ComponentRecord, serialize_component, deserialize_component
from ...services.storage_service import StorageService
from ...platform.paths import assets_dir, get_library_path
from ...objects import ImageCanvas


def slugify(name: str) -> str:
    """Convert name to filesystem-safe slug."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "component"


class ComponentEditor(QtWidgets.QMainWindow):
    """
    Full-featured component editor with library management.
    Upgraded from Dialog to MainWindow with toolbar, library dock, and clipboard operations.
    """
    saved = QtCore.pyqtSignal()

    def __init__(self, storage: StorageService, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Component Editor")
        self.resize(1100, 680)
        self.storage = storage

        self.canvas = ImageCanvas()
        self.setCentralWidget(self.canvas)
        self.canvas.imageDropped.connect(self._on_image_dropped)
        self.canvas.clickedPoint.connect(self._update_derived_labels)

        self._build_side_dock()
        self._build_library_dock()
        self._build_toolbar()
        self._build_shortcuts()
        
        self.statusBar().showMessage(
            "Load or paste an image, enter object height (mm), then click two points for the optical line."
        )

    # ---------- UI Building ----------
    def _build_toolbar(self):
        """Build main toolbar with actions."""
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        act_new = QtGui.QAction("New", self)
        act_new.triggered.connect(self._new_component)
        tb.addAction(act_new)

        act_open = QtGui.QAction("Open Image…", self)
        act_open.triggered.connect(self.open_image)
        tb.addAction(act_open)

        act_paste = QtGui.QAction("Paste (Img/JSON)", self)
        act_paste.setShortcut(QtGui.QKeySequence.StandardKey.Paste)
        act_paste.triggered.connect(self._smart_paste)
        tb.addAction(act_paste)

        act_clear = QtGui.QAction("Clear Points", self)
        act_clear.triggered.connect(self.canvas.clear_points)
        tb.addAction(act_clear)

        tb.addSeparator()

        act_copy_json = QtGui.QAction("Copy Component JSON", self)
        act_copy_json.triggered.connect(self.copy_component_json)
        tb.addAction(act_copy_json)

        act_paste_json = QtGui.QAction("Paste Component JSON", self)
        act_paste_json.triggered.connect(self.paste_component_json)
        tb.addAction(act_paste_json)

        tb.addSeparator()

        act_save = QtGui.QAction("Save Component", self)
        act_save.triggered.connect(self.save_component)
        tb.addAction(act_save)

        act_reload = QtGui.QAction("Reload Library", self)
        act_reload.triggered.connect(self.reload_library)
        tb.addAction(act_reload)

    def _build_shortcuts(self):
        """Setup keyboard shortcuts."""
        sc_copy = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Copy, self)
        sc_copy.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        sc_copy.activated.connect(self.copy_component_json)

        sc_paste = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Paste, self)
        sc_paste.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        sc_paste.activated.connect(self._smart_paste)

    def _build_side_dock(self):
        """Build side dock with component settings."""
        dock = QtWidgets.QDockWidget("Component Settings", self)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
        
        w = QtWidgets.QWidget()
        dock.setWidget(w)
        f = QtWidgets.QFormLayout(w)

        self.name_edit = QtWidgets.QLineEdit()
        
        self.kind_combo = QtWidgets.QComboBox()
        self.kind_combo.addItems(["lens", "mirror", "beamsplitter"])
        self.kind_combo.currentTextChanged.connect(self._on_kind_changed)

        # HEIGHT (mm) -> auto mm_per_pixel
        self.height_mm = QtWidgets.QDoubleSpinBox()
        self.height_mm.setRange(0.01, 1e7)
        self.height_mm.setDecimals(3)
        self.height_mm.setSuffix(" mm")
        self.height_mm.setValue(50.0)
        self.height_mm.valueChanged.connect(self._update_derived_labels)

        self.mm_per_px_lbl = QtWidgets.QLabel("— mm/px")
        self.line_len_lbl = QtWidgets.QLabel("— px / — mm")

        # Lens EFL
        self.efl_mm = QtWidgets.QDoubleSpinBox()
        self.efl_mm.setRange(-1e7, 1e7)
        self.efl_mm.setDecimals(3)
        self.efl_mm.setSuffix(" mm")
        self.efl_mm.setValue(100.0)

        # Beamsplitter T/R with auto-complement
        self.split_T = QtWidgets.QDoubleSpinBox()
        self.split_T.setRange(0, 100)
        self.split_T.setDecimals(1)
        self.split_T.setSuffix(" %")
        self.split_T.setValue(50.0)
        self.split_T.valueChanged.connect(self._sync_TR_from_T)

        self.split_R = QtWidgets.QDoubleSpinBox()
        self.split_R.setRange(0, 100)
        self.split_R.setDecimals(1)
        self.split_R.setSuffix(" %")
        self.split_R.setValue(50.0)
        self.split_R.valueChanged.connect(self._sync_TR_from_R)

        # Notes field
        self.notes = QtWidgets.QPlainTextEdit()
        self.notes.setPlaceholderText("Optional notes…")
        self.notes.setMaximumHeight(80)

        f.addRow("Name", self.name_edit)
        f.addRow("Type", self.kind_combo)
        f.addRow("Object height (Y)", self.height_mm)
        f.addRow("mm per pixel", self.mm_per_px_lbl)
        f.addRow("Picked line", self.line_len_lbl)
        f.addRow("EFL (lens)", self.efl_mm)
        f.addRow("Split T (BS)", self.split_T)
        f.addRow("Split R (BS)", self.split_R)
        f.addRow("Notes", self.notes)

        self._on_kind_changed(self.kind_combo.currentText())
        self._update_derived_labels()

    def _build_library_dock(self):
        """Build library dock showing saved components."""
        self.libDock = QtWidgets.QDockWidget("Library", self)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.libDock)
        
        self.libList = QtWidgets.QListWidget()
        self.libList.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.libList.setIconSize(QtCore.QSize(80, 80))
        self.libList.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.libList.setMovement(QtWidgets.QListView.Movement.Static)
        self.libList.setSpacing(8)
        self.libList.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.libList.itemClicked.connect(self._load_from_item)
        
        self.libDock.setWidget(self.libList)
        self._refresh_library_list()

    # ---------- Helpers ----------
    def _on_kind_changed(self, kind: str):
        """Show/hide type-specific fields."""
        is_lens = (kind == "lens")
        is_bs = (kind == "beamsplitter")
        self.efl_mm.setVisible(is_lens)
        self.split_T.setVisible(is_bs)
        self.split_R.setVisible(is_bs)

    def _sync_TR_from_T(self, v: float):
        """Auto-complement R from T."""
        self.split_R.blockSignals(True)
        self.split_R.setValue(max(0.0, min(100.0, 100.0 - v)))
        self.split_R.blockSignals(False)

    def _sync_TR_from_R(self, v: float):
        """Auto-complement T from R."""
        self.split_T.blockSignals(True)
        self.split_T.setValue(max(0.0, min(100.0, 100.0 - v)))
        self.split_T.blockSignals(False)

    def _update_derived_labels(self, *args):
        """Update mm_per_pixel and line length displays."""
        h_mm = float(self.height_mm.value())
        h_px = self.canvas.image_pixel_size()[1]
        
        if h_px > 0:
            mm_per_px = h_mm / float(h_px)
            self.mm_per_px_lbl.setText(f"{mm_per_px:.6g} mm/px  (image h={h_px} px)")
        else:
            self.mm_per_px_lbl.setText("— mm/px")

        # Picked line live length
        p1, p2 = self.canvas.get_points()
        if self.canvas.has_image() and p1 and p2 and h_px > 0:
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            px_len = (dx*dx + dy*dy)**0.5
            mm_per_px = h_mm / float(h_px) if h_px > 0 else 0.0
            mm_len = px_len * mm_per_px
            self.line_len_lbl.setText(f"{px_len:.2f} px / {mm_len:.3f} mm")
        else:
            self.line_len_lbl.setText("— px / — mm")

    def _get_mm_per_pixel(self) -> float:
        """Calculate current mm_per_pixel ratio."""
        h_px = self.canvas.image_pixel_size()[1]
        if h_px <= 0:
            return 0.0
        return float(self.height_mm.value()) / float(h_px)

    def _get_line_length_mm(self) -> float:
        """Calculate optical line length in mm."""
        p1, p2 = self.canvas.get_points()
        if not (p1 and p2):
            return 0.0
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        px_len = (dx*dx + dy*dy)**0.5
        return px_len * self._get_mm_per_pixel()

    def _set_image(self, pix: QtGui.QPixmap, source_path: str | None = None):
        """Set canvas image."""
        if pix.isNull():
            QtWidgets.QMessageBox.warning(self, "Load failed", "Could not load image.")
            return
        self.canvas.set_pixmap(pix, source_path)
        self.canvas.clear_points()
        self.statusBar().showMessage(
            "Image ready. Enter object height (mm), then click two points to define the optical line."
        )
        self._update_derived_labels()

    def _new_component(self):
        """Reset to new component state."""
        self.canvas.set_pixmap(QtGui.QPixmap(), None)
        self.canvas.clear_points()
        self.name_edit.clear()
        self.kind_combo.setCurrentText("lens")
        self.height_mm.setValue(50.0)
        self.efl_mm.setValue(100.0)
        self.split_T.setValue(50.0)
        self.split_R.setValue(50.0)
        self.notes.clear()
        self._update_derived_labels()

    # ---------- File & Clipboard ----------
    def open_image(self):
        """Open image file dialog."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.tif *.tiff *.svg)"
        )
        if not path:
            return
        
        if path.lower().endswith(".svg"):
            pix = ImageCanvas._render_svg_to_pixmap(path)
            if not pix:
                QtWidgets.QMessageBox.warning(self, "Load failed", "Invalid SVG.")
                return
        else:
            pix = QtGui.QPixmap(path)
        
        self._set_image(pix, path)

    def paste_image(self):
        """Paste image from clipboard."""
        cb = QtWidgets.QApplication.clipboard()
        mime = cb.mimeData()

        # 1) Direct bitmap/SVG bytes
        pix = self._pixmap_from_mime(mime)
        if pix is not None and not pix.isNull():
            self._set_image(pix, None)
            return

        # 2) URLs
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    low = path.lower()
                    if low.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg")):
                        if low.endswith(".svg"):
                            pix = ImageCanvas._render_svg_to_pixmap(path)
                            if pix:
                                self._set_image(pix, path)
                                return
                        else:
                            pix = QtGui.QPixmap(path)
                            if not pix.isNull():
                                self._set_image(pix, path)
                                return

        # 3) Plain text path
        text = cb.text().strip()
        if text and os.path.exists(text) and text.lower().endswith(
            (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg")
        ):
            if text.lower().endswith(".svg"):
                pix = ImageCanvas._render_svg_to_pixmap(text)
                if pix:
                    self._set_image(pix, text)
                    return
            else:
                pix = QtGui.QPixmap(text)
                if not pix.isNull():
                    self._set_image(pix, text)
                    return

        QtWidgets.QMessageBox.information(
            self,
            "Paste Image",
            "Clipboard doesn't contain an image (PNG/JPEG/TIFF/SVG) or an image file path/URL."
        )

    def _pixmap_from_mime(self, mime: QtCore.QMimeData) -> Optional[QtGui.QPixmap]:
        """Extract pixmap from mime data."""
        if not mime:
            return None
        
        if mime.hasImage():
            img = mime.imageData()
            if isinstance(img, QtGui.QImage):
                return QtGui.QPixmap.fromImage(img)
            if isinstance(img, QtGui.QPixmap):
                return img
        
        for fmt in ("image/png", "image/jpeg", "image/jpg", "image/tiff", "image/x-qt-image"):
            if fmt in mime.formats():
                ba = mime.data(fmt)
                img = QtGui.QImage()
                if img.loadFromData(ba):
                    return QtGui.QPixmap.fromImage(img)
        
        if "image/svg+xml" in mime.formats():
            svg_bytes = mime.data("image/svg+xml")
            pix = ImageCanvas._render_svg_to_pixmap(bytes(svg_bytes))
            if pix:
                return pix
        
        return None

    def _smart_paste(self):
        """Smart paste: detect focus widget, image, or JSON."""
        fw = self.focusWidget()
        if isinstance(fw, (QtWidgets.QLineEdit, QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit)):
            fw.paste()
            return
        
        before = self.canvas.has_image()
        self.paste_image()
        after = self.canvas.has_image()
        
        if not after and not before:
            # No image pasted, try JSON
            self.paste_component_json()

    def _on_image_dropped(self, pix: QtGui.QPixmap, path: str):
        """Handle image drop."""
        self._set_image(pix, path or None)

    # ---------- JSON Copy/Paste ----------
    def _build_record_from_ui(self) -> Optional[ComponentRecord]:
        """Build ComponentRecord from UI state."""
        if not self.canvas.has_image():
            QtWidgets.QMessageBox.warning(self, "Missing image", "Load or paste an image first.")
            return None
        
        p1, p2 = self.canvas.get_points()
        if not (p1 and p2):
            QtWidgets.QMessageBox.warning(
                self,
                "Missing line",
                "Click two points on the image to define the optical line."
            )
            return None
        
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Missing name", "Please enter a component name.")
            return None

        kind = self.kind_combo.currentText()
        mm_per_px = self._get_mm_per_pixel()
        if mm_per_px <= 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing height",
                "Please set a positive object height (mm)."
            )
            return None

        length_mm = self._get_line_length_mm()
        asset_path = self._ensure_asset_file(name)

        # Type-specific
        efl = float(self.efl_mm.value()) if kind == "lens" else 0.0
        TR = (
            (float(self.split_T.value()), float(self.split_R.value()))
            if kind == "beamsplitter"
            else (50.0, 50.0)
        )

        return ComponentRecord(
            name=name,
            kind=kind,
            image_path=asset_path,
            mm_per_pixel=mm_per_px,
            line_px=(float(p1[0]), float(p1[1]), float(p2[0]), float(p2[1])),
            length_mm=length_mm,
            efl_mm=efl,
            split_TR=TR,
            notes=self.notes.toPlainText().strip()
        )

    def _ensure_asset_file(self, name: str) -> str:
        """Save asset file, preserving original format if possible."""
        assets_folder = assets_dir()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = f"{slugify(name)}-{stamp}"

        src_path = self.canvas.source_path()
        pix = self.canvas.current_pixmap()
        
        if src_path and os.path.exists(src_path):
            ext = os.path.splitext(src_path)[1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg"):
                dst = os.path.join(assets_folder, base + ext)
                try:
                    with open(src_path, "rb") as fsrc, open(dst, "wb") as fdst:
                        fdst.write(fsrc.read())
                    return dst
                except Exception:
                    pass
        
        if pix is None or pix.isNull():
            raise RuntimeError("No image available to save.")
        
        dst = os.path.join(assets_folder, base + ".png")
        pix.save(dst, "PNG")
        return dst

    def copy_component_json(self):
        """Copy component as JSON to clipboard."""
        rec = self._build_record_from_ui()
        if not rec:
            return
        payload = json.dumps(serialize_component(rec), indent=2)
        QtWidgets.QApplication.clipboard().setText(payload)
        self.statusBar().showMessage("Component JSON copied to clipboard.", 2000)

    def paste_component_json(self):
        """Paste component from JSON."""
        text = QtWidgets.QApplication.clipboard().text().strip()
        if not text:
            QtWidgets.QMessageBox.information(self, "Paste Component JSON", "Clipboard is empty.")
            return
        
        try:
            data = json.loads(text)
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid JSON",
                f"Could not parse JSON:\n{e}"
            )
            return
        
        self._load_from_dict(data)
        self.statusBar().showMessage("Component JSON pasted.", 2000)

    # ---------- Library ----------
    def _refresh_library_list(self):
        """Refresh library list widget."""
        self.libList.clear()
        rows = self.storage.load_library()
        
        for row in rows:
            rec = deserialize_component(row)
            if not rec:
                continue
            
            name = rec.name
            img = rec.image_path
            icon = (
                QtGui.QIcon(img)
                if img and os.path.exists(img)
                else self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
            )
            it = QtWidgets.QListWidgetItem(icon, f"{name}\n({rec.kind})")
            it.setData(QtCore.Qt.ItemDataRole.UserRole, row)  # store plain dict
            self.libList.addItem(it)

    def _load_from_item(self, item: QtWidgets.QListWidgetItem):
        """Load component from library item."""
        data = item.data(QtCore.Qt.ItemDataRole.UserRole) or {}
        self._load_from_dict(data)

    def _load_from_dict(self, data: dict):
        """Load component from dict."""
        rec = deserialize_component(data)
        if not rec:
            return

        # Load image if available
        if rec.image_path and os.path.exists(rec.image_path):
            if rec.image_path.lower().endswith(".svg"):
                pix = ImageCanvas._render_svg_to_pixmap(rec.image_path)
                if pix:
                    self._set_image(pix, rec.image_path)
            else:
                pix = QtGui.QPixmap(rec.image_path)
                if not pix.isNull():
                    self._set_image(pix, rec.image_path)

        # Populate UI
        self.name_edit.setText(rec.name)
        self.kind_combo.setCurrentText(
            rec.kind if rec.kind in ("lens", "mirror", "beamsplitter") else "lens"
        )
        
        # Derive height from mm_per_pixel if possible
        h_px = self.canvas.image_pixel_size()[1]
        if h_px > 0:
            self.height_mm.setValue(rec.mm_per_pixel * h_px)
        
        self.efl_mm.setValue(rec.efl_mm if rec.kind == "lens" else 0.0)
        self.split_T.setValue(rec.split_TR[0] if rec.kind == "beamsplitter" else 50.0)
        self.split_R.setValue(rec.split_TR[1] if rec.kind == "beamsplitter" else 50.0)
        self.notes.setPlainText(rec.notes)
        
        if rec.line_px:
            p1 = (float(rec.line_px[0]), float(rec.line_px[1]))
            p2 = (float(rec.line_px[2]), float(rec.line_px[3]))
            self.canvas.set_points(p1, p2)
        
        self._update_derived_labels()

    def save_component(self):
        """Save component to library."""
        rec = self._build_record_from_ui()
        if not rec:
            return
        
        allrows = self.storage.load_library()
        # Replace by name or append
        replaced = False
        for i, row in enumerate(allrows):
            if row.get("name") == rec.name:
                allrows[i] = serialize_component(rec)
                replaced = True
                break
        
        if not replaced:
            allrows.append(serialize_component(rec))
        
        self.storage.save_library(allrows)
        QtWidgets.QApplication.clipboard().setText(json.dumps(serialize_component(rec), indent=2))
        QtWidgets.QMessageBox.information(
            self,
            "Saved",
            f"Saved component '{rec.name}'\n\nLibrary file:\n{get_library_path()}"
        )
        self._refresh_library_list()
        self.saved.emit()

    def reload_library(self):
        """Reload library from disk."""
        self._refresh_library_list()
        rows = self.storage.load_library()
        QtWidgets.QMessageBox.information(
            self,
            "Library",
            f"Loaded {len(rows)} component(s).\n\nLibrary file:\n{get_library_path()}"
        )


# Keep old name for backward compatibility
ComponentEditorDialog = ComponentEditor
