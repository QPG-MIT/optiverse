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
        self.canvas.pointsChanged.connect(self._update_derived_labels)

        self._build_side_dock()
        self._build_library_dock()
        self._build_toolbar()
        self._build_shortcuts()
        
        self.statusBar().showMessage(
            "Load image, enter object height (mm), then click two points on the optical element."
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

        act_load_lib = QtGui.QAction("Load Library from Path…", self)
        act_load_lib.triggered.connect(self.load_library_from_path)
        tb.addAction(act_load_lib)

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
        self.kind_combo.addItems(["lens", "mirror", "beamsplitter", "dichroic"])
        self.kind_combo.currentTextChanged.connect(self._on_kind_changed)

        # OBJECT HEIGHT (mm) -> physical size of the optical element
        self.object_height_mm = QtWidgets.QDoubleSpinBox()
        self.object_height_mm.setRange(0.01, 1e7)
        self.object_height_mm.setDecimals(3)
        self.object_height_mm.setSuffix(" mm")
        self.object_height_mm.setValue(30.0)  # Default: ~1 inch
        self.object_height_mm.setToolTip("Physical height of the optical element (e.g., 25.4mm for 1-inch optic)")
        self.object_height_mm.valueChanged.connect(self._update_derived_labels)

        self.mm_per_px_lbl = QtWidgets.QLabel("— mm/px")
        self.line_len_lbl = QtWidgets.QLabel("— px")
        self.image_height_lbl = QtWidgets.QLabel("— mm")

        # Line points manual edit (normalized 1000px space)
        self.p1_x = QtWidgets.QDoubleSpinBox()
        self.p1_x.setRange(0, 1000)
        self.p1_x.setDecimals(2)
        self.p1_x.setSuffix(" px")
        self.p1_x.valueChanged.connect(self._on_manual_point_changed)
        
        self.p1_y = QtWidgets.QDoubleSpinBox()
        self.p1_y.setRange(0, 1000)
        self.p1_y.setDecimals(2)
        self.p1_y.setSuffix(" px")
        self.p1_y.valueChanged.connect(self._on_manual_point_changed)
        
        self.p2_x = QtWidgets.QDoubleSpinBox()
        self.p2_x.setRange(0, 1000)
        self.p2_x.setDecimals(2)
        self.p2_x.setSuffix(" px")
        self.p2_x.valueChanged.connect(self._on_manual_point_changed)
        
        self.p2_y = QtWidgets.QDoubleSpinBox()
        self.p2_y.setRange(0, 1000)
        self.p2_y.setDecimals(2)
        self.p2_y.setSuffix(" px")
        self.p2_y.valueChanged.connect(self._on_manual_point_changed)

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

        # Dichroic cutoff wavelength
        self.cutoff_wavelength = QtWidgets.QDoubleSpinBox()
        self.cutoff_wavelength.setRange(200, 2000)
        self.cutoff_wavelength.setDecimals(1)
        self.cutoff_wavelength.setSuffix(" nm")
        self.cutoff_wavelength.setValue(550.0)
        
        # Dichroic transition width
        self.transition_width = QtWidgets.QDoubleSpinBox()
        self.transition_width.setRange(1, 200)
        self.transition_width.setDecimals(1)
        self.transition_width.setSuffix(" nm")
        self.transition_width.setValue(50.0)
        
        # Dichroic pass type
        self.pass_type = QtWidgets.QComboBox()
        self.pass_type.addItems(["longpass", "shortpass"])

        # Notes field
        self.notes = QtWidgets.QPlainTextEdit()
        self.notes.setPlaceholderText("Optional notes…")
        self.notes.setMaximumHeight(80)

        f.addRow("Name", self.name_edit)
        f.addRow("Type", self.kind_combo)
        f.addRow("Object height", self.object_height_mm)
        f.addRow("Line length", self.line_len_lbl)
        f.addRow("→ mm/px", self.mm_per_px_lbl)
        f.addRow("→ Image height", self.image_height_lbl)
        
        # Point coordinates section
        f.addRow(QtWidgets.QLabel("─── Line Points (px) ───"))
        p1_layout = QtWidgets.QHBoxLayout()
        p1_layout.addWidget(QtWidgets.QLabel("X:"))
        p1_layout.addWidget(self.p1_x)
        p1_layout.addWidget(QtWidgets.QLabel("Y:"))
        p1_layout.addWidget(self.p1_y)
        f.addRow("Point 1", p1_layout)
        
        p2_layout = QtWidgets.QHBoxLayout()
        p2_layout.addWidget(QtWidgets.QLabel("X:"))
        p2_layout.addWidget(self.p2_x)
        p2_layout.addWidget(QtWidgets.QLabel("Y:"))
        p2_layout.addWidget(self.p2_y)
        f.addRow("Point 2", p2_layout)
        
        f.addRow(QtWidgets.QLabel("─── Properties ───"))
        f.addRow("EFL (lens)", self.efl_mm)
        f.addRow("Split T (BS)", self.split_T)
        f.addRow("Split R (BS)", self.split_R)
        f.addRow("Cutoff λ (dichroic)", self.cutoff_wavelength)
        f.addRow("Trans. Width (dichroic)", self.transition_width)
        f.addRow("Pass Type (dichroic)", self.pass_type)
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
        is_dichroic = (kind == "dichroic")
        self.efl_mm.setVisible(is_lens)
        self.split_T.setVisible(is_bs)
        self.split_R.setVisible(is_bs)
        self.cutoff_wavelength.setVisible(is_dichroic)
        self.transition_width.setVisible(is_dichroic)
        self.pass_type.setVisible(is_dichroic)

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
        """Update computed values from object height and picked line."""
        object_height = float(self.object_height_mm.value())
        
        # Picked line live length (canvas returns actual pixel coordinates)
        p1, p2 = self.canvas.get_points()
        
        # Normalize canvas points to 1000px space for display
        _, h_px = self.canvas.image_pixel_size()
        scale = 1000.0 / float(h_px) if h_px > 0 else 1.0
        
        # Update spinboxes with normalized coordinates (without triggering change events)
        if p1:
            self.p1_x.blockSignals(True)
            self.p1_y.blockSignals(True)
            self.p1_x.setValue(p1[0] * scale)
            self.p1_y.setValue(p1[1] * scale)
            self.p1_x.blockSignals(False)
            self.p1_y.blockSignals(False)
        
        if p2:
            self.p2_x.blockSignals(True)
            self.p2_y.blockSignals(True)
            self.p2_x.setValue(p2[0] * scale)
            self.p2_y.setValue(p2[1] * scale)
            self.p2_x.blockSignals(False)
            self.p2_y.blockSignals(False)
        
        # Compute values based on normalized coordinates (spinbox values)
        self._update_computed_values()
    
    def _update_computed_values(self):
        """Update computed value labels from normalized coordinates."""
        object_height = float(self.object_height_mm.value())
        
        # Get normalized coordinates from spinboxes
        p1_norm = (float(self.p1_x.value()), float(self.p1_y.value()))
        p2_norm = (float(self.p2_x.value()), float(self.p2_y.value()))
        
        if self.canvas.has_image() and p1_norm and p2_norm and object_height > 0:
            dx = p2_norm[0] - p1_norm[0]
            dy = p2_norm[1] - p1_norm[1]
            px_len = (dx*dx + dy*dy)**0.5
            
            if px_len > 0:
                # Compute mm_per_pixel from object height and line length (in normalized space)
                mm_per_px = object_height / px_len
                # Compute full image height (normalized to 1000px)
                image_height = mm_per_px * 1000.0
                
                self.line_len_lbl.setText(f"{px_len:.2f} px")
                self.mm_per_px_lbl.setText(f"{mm_per_px:.6g} mm/px")
                self.image_height_lbl.setText(f"{image_height:.2f} mm (normalized to 1000px)")
            else:
                self.line_len_lbl.setText("— px")
                self.mm_per_px_lbl.setText("— mm/px")
                self.image_height_lbl.setText("— mm")
        else:
            self.line_len_lbl.setText("— px")
            self.mm_per_px_lbl.setText("— mm/px")
            self.image_height_lbl.setText("— mm")

    def _on_manual_point_changed(self):
        """Handle manual changes to point coordinates (normalized 1000px space)."""
        # Get normalized coordinates from spinboxes
        p1_norm = (float(self.p1_x.value()), float(self.p1_y.value()))
        p2_norm = (float(self.p2_x.value()), float(self.p2_y.value()))
        
        # Denormalize to actual image space for canvas
        _, h_px = self.canvas.image_pixel_size()
        scale = float(h_px) / 1000.0 if h_px > 0 else 1.0
        
        p1 = (p1_norm[0] * scale, p1_norm[1] * scale)
        p2 = (p2_norm[0] * scale, p2_norm[1] * scale)
        
        # Only update if both points have non-zero values
        canvas_p1, canvas_p2 = self.canvas.get_points()
        if canvas_p1 is not None or p1 != (0.0, 0.0):
            if canvas_p2 is not None or p2 != (0.0, 0.0):
                self.canvas.set_points(p1, p2)
                # Don't call _update_derived_labels here to avoid recursion
                # Just update the computed values
                self._update_computed_values()

    def _get_object_height(self) -> float:
        """Get the object height entered by user."""
        return float(self.object_height_mm.value())

    def _set_image(self, pix: QtGui.QPixmap, source_path: str | None = None):
        """Set canvas image."""
        if pix.isNull():
            QtWidgets.QMessageBox.warning(self, "Load failed", "Could not load image.")
            return
        self.canvas.set_pixmap(pix, source_path)
        self.canvas.clear_points()
        self.statusBar().showMessage(
            "Image ready. Enter object height (mm), then click two points on the optical element."
        )
        self._update_derived_labels()

    def _new_component(self):
        """Reset to new component state."""
        self.canvas.set_pixmap(QtGui.QPixmap(), None)
        self.canvas.clear_points()
        self.name_edit.clear()
        self.kind_combo.setCurrentText("lens")
        self.object_height_mm.setValue(50.0)
        self.efl_mm.setValue(100.0)
        self.split_T.setValue(50.0)
        self.split_R.setValue(50.0)
        self.cutoff_wavelength.setValue(550.0)
        self.transition_width.setValue(50.0)
        self.pass_type.setCurrentIndex(0)  # longpass
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
        """Build ComponentRecord from UI state with normalized 1000px coordinates."""
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
        object_height = self._get_object_height()
        
        if object_height <= 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing object height",
                "Please set a positive object height (mm)."
            )
            return None

        # Normalize line_px to 1000px coordinate space
        _, h_px = self.canvas.image_pixel_size()
        if h_px <= 0:
            h_px = 1000  # Fallback
        
        scale = 1000.0 / float(h_px)
        line_px_normalized = (
            float(p1[0]) * scale,
            float(p1[1]) * scale,
            float(p2[0]) * scale,
            float(p2[1]) * scale
        )
        
        asset_path = self._ensure_asset_file_normalized(name)

        # Type-specific
        efl = float(self.efl_mm.value()) if kind == "lens" else 0.0
        TR = (
            (float(self.split_T.value()), float(self.split_R.value()))
            if kind == "beamsplitter"
            else (50.0, 50.0)
        )
        cutoff_wavelength = float(self.cutoff_wavelength.value()) if kind == "dichroic" else 550.0
        transition_width = float(self.transition_width.value()) if kind == "dichroic" else 50.0
        pass_type_value = self.pass_type.currentText() if kind == "dichroic" else "longpass"

        return ComponentRecord(
            name=name,
            kind=kind,
            image_path=asset_path,
            line_px=line_px_normalized,
            object_height_mm=object_height,
            efl_mm=efl,
            split_TR=TR,
            cutoff_wavelength_nm=cutoff_wavelength,
            transition_width_nm=transition_width,
            pass_type=pass_type_value,
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
    
    def _ensure_asset_file_normalized(self, name: str) -> str:
        """Save asset file normalized to 1000px height."""
        assets_folder = assets_dir()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = f"{slugify(name)}-{stamp}"
        dst = os.path.join(assets_folder, base + ".png")
        
        pix = self.canvas.current_pixmap()
        if pix is None or pix.isNull():
            raise RuntimeError("No image available to save.")
        
        # Ensure device pixel ratio = 1.0 before scaling
        img = pix.toImage()
        img.setDevicePixelRatio(1.0)
        pix = QtGui.QPixmap.fromImage(img)
        
        # Normalize to 1000px height while preserving aspect ratio
        if pix.height() != 1000:
            pix = pix.scaledToHeight(1000, QtCore.Qt.TransformationMode.SmoothTransformation)
        
        # Ensure saved image has device pixel ratio = 1.0
        img = pix.toImage()
        img.setDevicePixelRatio(1.0)
        img.save(dst, "PNG")
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
            rec.kind if rec.kind in ("lens", "mirror", "beamsplitter", "dichroic") else "lens"
        )
        
        # Set object height directly from component record
        if rec.object_height_mm > 0:
            self.object_height_mm.setValue(rec.object_height_mm)
        
        self.efl_mm.setValue(rec.efl_mm if rec.kind == "lens" else 0.0)
        self.split_T.setValue(rec.split_TR[0] if rec.kind == "beamsplitter" else 50.0)
        self.split_R.setValue(rec.split_TR[1] if rec.kind == "beamsplitter" else 50.0)
        self.cutoff_wavelength.setValue(rec.cutoff_wavelength_nm if rec.kind == "dichroic" else 550.0)
        self.transition_width.setValue(rec.transition_width_nm if rec.kind == "dichroic" else 50.0)
        if rec.kind == "dichroic":
            idx = self.pass_type.findText(rec.pass_type)
            if idx >= 0:
                self.pass_type.setCurrentIndex(idx)
        self.notes.setPlainText(rec.notes)
        
        if rec.line_px:
            # rec.line_px is in normalized 1000px space, denormalize for canvas
            _, h_px = self.canvas.image_pixel_size()
            scale = float(h_px) / 1000.0 if h_px > 0 else 1.0
            
            p1 = (float(rec.line_px[0]) * scale, float(rec.line_px[1]) * scale)
            p2 = (float(rec.line_px[2]) * scale, float(rec.line_px[3]) * scale)
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
    
    def load_library_from_path(self):
        """Load component library from a custom path."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Library File",
            "",
            "JSON files (*.json);;All files (*.*)"
        )
        if not path:
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid Library",
                    "The selected file does not contain a valid component library (expected JSON array)."
                )
                return
            
            # Merge with existing library
            existing = self.storage.load_library()
            existing_names = {comp.get("name") for comp in existing}
            
            new_count = 0
            for comp in data:
                if isinstance(comp, dict) and comp.get("name"):
                    if comp.get("name") not in existing_names:
                        existing.append(comp)
                        existing_names.add(comp.get("name"))
                        new_count += 1
            
            if new_count > 0:
                self.storage.save_library(existing)
                self._refresh_library_list()
                QtWidgets.QMessageBox.information(
                    self,
                    "Library Loaded",
                    f"Loaded {new_count} new component(s) from:\n{path}\n\nTotal components: {len(existing)}"
                )
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Library Loaded",
                    "No new components found in the library file (all components already exist)."
                )
        
        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid JSON",
                f"Could not parse JSON file:\n{e}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Load Error",
                f"Could not load library file:\n{e}"
            )


# Keep old name for backward compatibility
ComponentEditorDialog = ComponentEditor
