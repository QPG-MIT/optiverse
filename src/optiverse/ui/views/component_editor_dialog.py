from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets

from ...services.storage_service import StorageService
from ...platform.paths import assets_dir
from ...widgets.image_canvas import ImageCanvas


class ComponentEditorDialog(QtWidgets.QDialog):
    def __init__(self, storage: StorageService, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Component Editor")
        self.resize(900, 600)
        self.storage = storage

        self.canvas = ImageCanvas()
        self.name_edit = QtWidgets.QLineEdit()
        self.kind_combo = QtWidgets.QComboBox(); self.kind_combo.addItems(["lens", "mirror", "beamsplitter"])
        self.height_mm = QtWidgets.QDoubleSpinBox(); self.height_mm.setRange(0.01, 1e7); self.height_mm.setDecimals(3); self.height_mm.setSuffix(" mm"); self.height_mm.setValue(50.0)
        self.mm_per_px_lbl = QtWidgets.QLabel("— mm/px")
        self.line_len_lbl = QtWidgets.QLabel("— px / — mm")
        self.efl_mm = QtWidgets.QDoubleSpinBox(); self.efl_mm.setRange(-1e7, 1e7); self.efl_mm.setDecimals(3); self.efl_mm.setSuffix(" mm"); self.efl_mm.setValue(100.0)

        self.height_mm.valueChanged.connect(self._update_derived)
        self.canvas.clickedPoint.connect(self._update_derived)

        left = QtWidgets.QVBoxLayout(); left.addWidget(self.canvas); left.addStretch(1)
        form = QtWidgets.QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Type", self.kind_combo)
        form.addRow("Object height (Y)", self.height_mm)
        form.addRow("mm per pixel", self.mm_per_px_lbl)
        form.addRow("Picked line", self.line_len_lbl)
        form.addRow("EFL (lens)", self.efl_mm)
        btn_save = QtWidgets.QPushButton("Save")
        btn_save.clicked.connect(self._on_save)
        right = QtWidgets.QVBoxLayout(); right.addLayout(form); right.addStretch(1); right.addWidget(btn_save)

        lay = QtWidgets.QHBoxLayout(self)
        lay.addLayout(left, 2); lay.addLayout(right, 1)

    def _update_derived(self, *args):
        h_px = self.canvas.image_pixel_size()[1]
        h_mm = float(self.height_mm.value())
        if h_px > 0:
            mm_per_px = h_mm / float(h_px)
            self.mm_per_px_lbl.setText(f"{mm_per_px:.6g} mm/px  (image h={h_px} px)")
        else:
            self.mm_per_px_lbl.setText("— mm/px")
        p1, p2 = self.canvas.get_points()
        if self.canvas.has_image() and p1 and p2 and h_px > 0:
            dx = p2[0]-p1[0]; dy = p2[1]-p1[1]; px_len = (dx*dx + dy*dy)**0.5
            mm_len = px_len * (h_mm / float(h_px))
            self.line_len_lbl.setText(f"{px_len:.2f} px / {mm_len:.3f} mm")
        else:
            self.line_len_lbl.setText("— px / — mm")

    def _build_record(self) -> Optional[dict]:
        if not self.canvas.has_image():
            QtWidgets.QMessageBox.warning(self, "Missing image", "Load or paste an image first."); return None
        p1, p2 = self.canvas.get_points()
        if not (p1 and p2):
            QtWidgets.QMessageBox.warning(self, "Missing line", "Click two points to define the optical line."); return None
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Missing name", "Please enter a component name."); return None
        h_px = self.canvas.image_pixel_size()[1]
        if h_px <= 0:
            QtWidgets.QMessageBox.warning(self, "Missing height", "Please set a positive object height (mm). "); return None
        mm_per_px = float(self.height_mm.value()) / float(h_px)
        dx = p2[0]-p1[0]; dy = p2[1]-p1[1]; px_len = (dx*dx + dy*dy)**0.5
        length_mm = px_len * mm_per_px
        asset_path = self._save_asset(name)
        kind = self.kind_combo.currentText()
        rec = {
            "name": name,
            "kind": kind,
            "image_path": asset_path,
            "mm_per_pixel": mm_per_px,
            "line_px": [float(p1[0]), float(p1[1]), float(p2[0]), float(p2[1])],
            "length_mm": float(length_mm),
            "notes": "",
        }
        if kind == "lens":
            rec["efl_mm"] = float(self.efl_mm.value())
        return rec

    def _save_asset(self, name: str) -> str:
        assets = assets_dir()
        base = f"{slugify(name)}-{time.strftime('%Y%m%d-%H%M%S')}"
        pix = self.canvas.current_pixmap()
        dst = assets + "/" + base + ".png"
        assert pix is not None
        pix.save(dst, "PNG")
        return dst

    def _on_save(self):
        rec = self._build_record()
        if not rec:
            return
        rows = self.storage.load_library()
        # replace by name or append
        replaced = False
        for i, r in enumerate(rows):
            if r.get("name") == rec["name"]:
                rows[i] = rec; replaced = True; break
        if not replaced:
            rows.append(rec)
        self.storage.save_library(rows)
        QtWidgets.QMessageBox.information(self, "Saved", f"Saved '{rec['name']}'")


def slugify(name: str) -> str:
    s = name.strip().lower()
    out = []
    for ch in s:
        if ch.isalnum(): out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("-")
    t = "".join(out).strip("-")
    return t or "component"


