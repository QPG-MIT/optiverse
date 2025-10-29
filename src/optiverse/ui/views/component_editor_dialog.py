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
from ...objects.views import MultiLineCanvas, InterfaceLine


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

        self.canvas = MultiLineCanvas()
        self.setCentralWidget(self.canvas)
        self.canvas.imageDropped.connect(self._on_image_dropped)
        self.canvas.linesChanged.connect(self._on_canvas_lines_changed)
        self.canvas.lineSelected.connect(self._on_canvas_line_selected)

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
        self.kind_combo.addItems(["lens", "mirror", "beamsplitter", "dichroic", "refractive_object"])
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
        
        # Optical interfaces (shown for all component types)
        self.interfaces_label = QtWidgets.QLabel("<b>Interfaces (drag on canvas):</b>")
        self.interfaces_list = QtWidgets.QListWidget()
        self.interfaces_list.setMaximumHeight(150)
        self.interfaces_list.setToolTip("Visual interfaces - select to highlight on canvas, drag endpoints to adjust geometry")
        
        self.interfaces_buttons = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(self.interfaces_buttons)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_add_interface = QtWidgets.QPushButton("Add")
        self.btn_add_interface.setToolTip("Add a new interface")
        self.btn_edit_interface = QtWidgets.QPushButton("Edit")
        self.btn_edit_interface.setToolTip("Edit selected interface")
        self.btn_delete_interface = QtWidgets.QPushButton("Delete")
        self.btn_delete_interface.setToolTip("Delete selected interface")
        self.btn_preset_bs_cube = QtWidgets.QPushButton("BS Cube Preset")
        self.btn_preset_bs_cube.setToolTip("Create beam splitter cube (5 interfaces)")
        
        btn_layout.addWidget(self.btn_add_interface)
        btn_layout.addWidget(self.btn_edit_interface)
        btn_layout.addWidget(self.btn_delete_interface)
        btn_layout.addWidget(self.btn_preset_bs_cube)
        
        self.btn_add_interface.clicked.connect(self._add_interface)
        self.btn_edit_interface.clicked.connect(self._edit_interface)
        self.btn_delete_interface.clicked.connect(self._delete_interface)
        self.btn_preset_bs_cube.clicked.connect(self._create_bs_cube_preset)
        
        # Storage for interfaces
        self._interfaces = []

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
        
        # Optical Interfaces - shown for ALL component types
        f.addRow(self.interfaces_label)
        f.addRow(self.interfaces_list)
        f.addRow(self.interfaces_buttons)
        
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
        
        # Connect interface list selection to canvas
        self.interfaces_list.currentRowChanged.connect(self._on_interface_list_selection)

    # ---------- Helpers ----------
    def _on_kind_changed(self, kind: str):
        """Show/hide type-specific fields."""
        is_lens = (kind == "lens")
        is_bs = (kind == "beamsplitter")
        is_dichroic = (kind == "dichroic")
        is_refractive = (kind == "refractive_object")
        
        self.efl_mm.setVisible(is_lens)
        self.split_T.setVisible(is_bs)
        self.split_R.setVisible(is_bs)
        self.cutoff_wavelength.setVisible(is_dichroic)
        self.transition_width.setVisible(is_dichroic)
        self.pass_type.setVisible(is_dichroic)
        
        # Interfaces are ALWAYS visible now, but buttons change visibility
        # For refractive objects, show all buttons
        # For simple components, hide the multi-interface buttons
        self.btn_add_interface.setVisible(is_refractive)
        self.btn_preset_bs_cube.setVisible(is_refractive)
        
        # Update canvas visualization when kind changes
        self._sync_interfaces_to_canvas()
        self._update_interface_list()

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
        
        # For simple components, get first line if it exists
        lines = self.canvas.get_all_lines()
        p1, p2 = None, None
        if lines:
            line = lines[0]
            p1 = (line.x1, line.y1)
            p2 = (line.x2, line.y2)
        
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
        self._sync_interfaces_to_canvas()
        
        kind = self.kind_combo.currentText()
        if kind == "refractive_object":
            self.statusBar().showMessage(
                "Image loaded! Use 'Add Interface' or 'BS Cube Preset' to add optical interfaces. Drag line endpoints to adjust."
            )
        else:
            self.statusBar().showMessage(
                "Image loaded! Drag the colored line endpoints to align with your optical element. Enter object height."
            )
        self._update_derived_labels()

    def _new_component(self):
        """Reset to new component state."""
        self.canvas.set_pixmap(QtGui.QPixmap(), None)
        self.canvas.clear_lines()
        self.name_edit.clear()
        self.kind_combo.setCurrentText("lens")
        self.object_height_mm.setValue(50.0)
        self.efl_mm.setValue(100.0)
        self.split_T.setValue(50.0)
        self.split_R.setValue(50.0)
        self.cutoff_wavelength.setValue(550.0)
        self.transition_width.setValue(50.0)
        self.pass_type.setCurrentIndex(0)  # longpass
        self._interfaces = []
        self._update_interface_list()
        self.notes.clear()
        self._update_derived_labels()
    
    # ---------- Canvas/Interface Synchronization ----------
    
    def _get_interface_color(self, iface: dict) -> QtGui.QColor:
        """Get color for interface based on its properties."""
        if iface.get('is_beam_splitter', False):
            if iface.get('is_polarizing', False):
                return QtGui.QColor(150, 0, 150)  # Purple for PBS
            else:
                return QtGui.QColor(0, 150, 120)  # Green for BS
        else:
            # Regular refractive interface
            n1 = iface.get('n1', 1.0)
            n2 = iface.get('n2', 1.0)
            if abs(n1 - n2) > 0.01:
                return QtGui.QColor(100, 100, 255)  # Blue for refraction
            else:
                return QtGui.QColor(150, 150, 150)  # Gray for same index
    
    def _get_simple_component_color(self) -> QtGui.QColor:
        """Get color for simple component types."""
        kind = self.kind_combo.currentText()
        colors = {
            'lens': QtGui.QColor(0, 180, 180),      # Cyan
            'mirror': QtGui.QColor(255, 140, 0),    # Orange
            'beamsplitter': QtGui.QColor(0, 150, 120),  # Green
            'dichroic': QtGui.QColor(255, 0, 255),  # Magenta
        }
        return colors.get(kind, QtGui.QColor(100, 100, 255))
    
    def _sync_interfaces_to_canvas(self):
        """Sync interface list to canvas visual display."""
        if not self.canvas.has_image():
            return
        
        kind = self.kind_combo.currentText()
        
        # Block signals during bulk update
        self.canvas.blockSignals(True)
        self.canvas.clear_lines()
        
        if kind == "refractive_object":
            # Show all interfaces as colored lines
            for i, iface in enumerate(self._interfaces):
                line = InterfaceLine(
                    x1=iface.get('x1_px', 0),
                    y1=iface.get('y1_px', 0),
                    x2=iface.get('x2_px', 100),
                    y2=iface.get('y2_px', 100),
                    color=self._get_interface_color(iface),
                    label=f"Interface {i+1}",
                    properties=iface
                )
                self.canvas.add_line(line)
                print(f"[DEBUG] Added interface line {i+1}: ({line.x1:.1f}, {line.y1:.1f}) to ({line.x2:.1f}, {line.y2:.1f}), color={line.color.name()}")
        else:
            # Simple component - ALWAYS create calibration line
            w, h = self.canvas.image_pixel_size()
            if w > 0 and h > 0:
                cx, cy = w / 2, h / 2
                line = InterfaceLine(
                    x1=cx - 50, y1=cy,
                    x2=cx + 50, y2=cy,
                    color=self._get_simple_component_color(),
                    label=kind.capitalize(),
                    properties={'type': kind}
                )
                self.canvas.add_line(line)
                print(f"[DEBUG] Created calibration line for {kind}: ({line.x1:.1f}, {line.y1:.1f}) to ({line.x2:.1f}, {line.y2:.1f}), color={line.color.name()}")
        
        self.canvas.blockSignals(False)
        self.canvas.update()  # Force repaint
        print(f"[DEBUG] Canvas now has {len(self.canvas.get_all_lines())} line(s)")
    
    def _on_canvas_lines_changed(self):
        """Called when canvas lines change (user dragging)."""
        kind = self.kind_combo.currentText()
        
        if kind == "refractive_object":
            # Update interface coordinates from canvas
            lines = self.canvas.get_all_lines()
            for i, line in enumerate(lines):
                if i < len(self._interfaces):
                    self._interfaces[i]['x1_px'] = line.x1
                    self._interfaces[i]['y1_px'] = line.y1
                    self._interfaces[i]['x2_px'] = line.x2
                    self._interfaces[i]['y2_px'] = line.y2
    
    def _on_canvas_line_selected(self, index: int):
        """Called when a line is selected on canvas."""
        # Highlight corresponding item in list
        self.interfaces_list.blockSignals(True)
        self.interfaces_list.setCurrentRow(index)
        self.interfaces_list.blockSignals(False)
    
    def _on_interface_list_selection(self, row: int):
        """Called when user selects an interface in the list."""
        if row >= 0:
            self.canvas.select_line(row)
    
    # ---------- Interface Management (Refractive Objects) ----------
    
    def _update_interface_list(self):
        """Update the interfaces list widget."""
        self.interfaces_list.clear()
        
        kind = self.kind_combo.currentText()
        
        if kind == "refractive_object":
            # Show all refractive interfaces
            for i, iface in enumerate(self._interfaces):
                desc = f"Interface {i+1}: "
                if iface.get('is_beam_splitter', False):
                    desc += "BS "
                desc += f"n={iface.get('n1', 1.0):.3f}→{iface.get('n2', 1.5):.3f}"
                if iface.get('is_beam_splitter', False):
                    desc += f" T/R={iface.get('split_T', 50):.0f}/{iface.get('split_R', 50):.0f}"
                self.interfaces_list.addItem(desc)
        else:
            # Simple component - show the calibration line
            lines = self.canvas.get_all_lines()
            if len(lines) > 0:
                line = lines[0]
                desc = f"Calibration line ({kind})"
                self.interfaces_list.addItem(desc)
        
        # Update canvas visualization
        self._sync_interfaces_to_canvas()
    
    def _add_interface(self):
        """Add a new interface."""
        # Create dialog for interface properties
        d = QtWidgets.QDialog(self)
        d.setWindowTitle("Add Interface")
        f = QtWidgets.QFormLayout(d)
        
        # Geometry
        x1 = QtWidgets.QDoubleSpinBox()
        x1.setRange(-1000, 1000)
        x1.setDecimals(2)
        x1.setSuffix(" mm")
        x1.setValue(-10.0)
        
        y1 = QtWidgets.QDoubleSpinBox()
        y1.setRange(-1000, 1000)
        y1.setDecimals(2)
        y1.setSuffix(" mm")
        y1.setValue(0.0)
        
        x2 = QtWidgets.QDoubleSpinBox()
        x2.setRange(-1000, 1000)
        x2.setDecimals(2)
        x2.setSuffix(" mm")
        x2.setValue(10.0)
        
        y2 = QtWidgets.QDoubleSpinBox()
        y2.setRange(-1000, 1000)
        y2.setDecimals(2)
        y2.setSuffix(" mm")
        y2.setValue(0.0)
        
        # Refractive indices
        n1 = QtWidgets.QDoubleSpinBox()
        n1.setRange(1.0, 3.0)
        n1.setDecimals(4)
        n1.setValue(1.0)  # Air
        n1.setToolTip("Refractive index on 'left' side (ray incident from)")
        
        n2 = QtWidgets.QDoubleSpinBox()
        n2.setRange(1.0, 3.0)
        n2.setDecimals(4)
        n2.setValue(1.517)  # BK7 glass
        n2.setToolTip("Refractive index on 'right' side (ray exits to)")
        
        # Beam splitter properties
        is_bs = QtWidgets.QCheckBox("Beam Splitter Coating")
        split_t = QtWidgets.QDoubleSpinBox()
        split_t.setRange(0, 100)
        split_t.setDecimals(1)
        split_t.setSuffix(" %")
        split_t.setValue(50.0)
        split_t.setEnabled(False)
        
        split_r = QtWidgets.QDoubleSpinBox()
        split_r.setRange(0, 100)
        split_r.setDecimals(1)
        split_r.setSuffix(" %")
        split_r.setValue(50.0)
        split_r.setEnabled(False)
        
        is_pbs = QtWidgets.QCheckBox("Polarizing (PBS)")
        is_pbs.setEnabled(False)
        
        pbs_axis = QtWidgets.QDoubleSpinBox()
        pbs_axis.setRange(-180, 180)
        pbs_axis.setDecimals(1)
        pbs_axis.setSuffix(" °")
        pbs_axis.setValue(0.0)
        pbs_axis.setEnabled(False)
        pbs_axis.setToolTip("PBS transmission axis (absolute angle in lab frame)")
        
        def on_bs_toggled(checked):
            split_t.setEnabled(checked)
            split_r.setEnabled(checked)
            is_pbs.setEnabled(checked)
            pbs_axis.setEnabled(checked and is_pbs.isChecked())
        
        def on_pbs_toggled(checked):
            pbs_axis.setEnabled(is_bs.isChecked() and checked)
        
        is_bs.toggled.connect(on_bs_toggled)
        is_pbs.toggled.connect(on_pbs_toggled)
        
        # Layout
        f.addRow("Start X", x1)
        f.addRow("Start Y", y1)
        f.addRow("End X", x2)
        f.addRow("End Y", y2)
        f.addRow("Refractive Index n1", n1)
        f.addRow("Refractive Index n2", n2)
        f.addRow("", is_bs)
        f.addRow("Transmission %", split_t)
        f.addRow("Reflection %", split_r)
        f.addRow("", is_pbs)
        f.addRow("PBS Axis", pbs_axis)
        
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        if d.exec():
            # Get image center for default positioning
            w, h = self.canvas.image_pixel_size()
            center_x = w / 2 if w > 0 else 500
            center_y = h / 2 if h > 0 else 500
            
            # Create interface dict (storing in pixels for now)
            iface = {
                'x1_px': center_x - 50,
                'y1_px': center_y,
                'x2_px': center_x + 50,
                'y2_px': center_y,
                'x1_mm': x1.value(),
                'y1_mm': y1.value(),
                'x2_mm': x2.value(),
                'y2_mm': y2.value(),
                'n1': n1.value(),
                'n2': n2.value(),
                'is_beam_splitter': is_bs.isChecked(),
                'split_T': split_t.value(),
                'split_R': split_r.value(),
                'is_polarizing': is_pbs.isChecked(),
                'pbs_transmission_axis_deg': pbs_axis.value()
            }
            self._interfaces.append(iface)
            self._update_interface_list()
    
    def _edit_interface(self):
        """Edit the selected interface."""
        row = self.interfaces_list.currentRow()
        kind = self.kind_combo.currentText()
        
        # For simple components, just enable edit mode (drag only this line)
        if kind != "refractive_object":
            if row < 0:
                QtWidgets.QMessageBox.information(self, "No Selection", "Please select the interface to edit.")
                return
            # Lock canvas to only drag this line
            self.canvas.set_drag_lock(row)
            self.statusBar().showMessage(f"Editing: Drag only this line. Click outside to finish editing.")
            return
        
        # For refractive objects, open property dialog
        if row < 0 or row >= len(self._interfaces):
            QtWidgets.QMessageBox.information(self, "No Selection", "Please select an interface to edit.")
            return
        
        iface = self._interfaces[row]
        
        # Lock canvas to only drag this line while editing
        self.canvas.set_drag_lock(row)
        
        # Create non-modal dialog that allows dragging on canvas
        d = QtWidgets.QDialog(self)
        d.setWindowTitle(f"Edit Interface {row + 1}")
        d.setWindowFlags(d.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        d.setModal(False)  # Non-modal - allows interaction with parent
        f = QtWidgets.QFormLayout(d)
        
        # Pre-fill with existing values
        x1 = QtWidgets.QDoubleSpinBox()
        x1.setRange(-1000, 1000)
        x1.setDecimals(2)
        x1.setSuffix(" mm")
        x1.setValue(iface.get('x1_mm', 0))
        
        y1 = QtWidgets.QDoubleSpinBox()
        y1.setRange(-1000, 1000)
        y1.setDecimals(2)
        y1.setSuffix(" mm")
        y1.setValue(iface.get('y1_mm', 0))
        
        x2 = QtWidgets.QDoubleSpinBox()
        x2.setRange(-1000, 1000)
        x2.setDecimals(2)
        x2.setSuffix(" mm")
        x2.setValue(iface.get('x2_mm', 0))
        
        y2 = QtWidgets.QDoubleSpinBox()
        y2.setRange(-1000, 1000)
        y2.setDecimals(2)
        y2.setSuffix(" mm")
        y2.setValue(iface.get('y2_mm', 0))
        
        n1 = QtWidgets.QDoubleSpinBox()
        n1.setRange(1.0, 3.0)
        n1.setDecimals(4)
        n1.setValue(iface.get('n1', 1.0))
        
        n2 = QtWidgets.QDoubleSpinBox()
        n2.setRange(1.0, 3.0)
        n2.setDecimals(4)
        n2.setValue(iface.get('n2', 1.5))
        
        is_bs = QtWidgets.QCheckBox("Beam Splitter Coating")
        is_bs.setChecked(iface.get('is_beam_splitter', False))
        
        split_t = QtWidgets.QDoubleSpinBox()
        split_t.setRange(0, 100)
        split_t.setDecimals(1)
        split_t.setSuffix(" %")
        split_t.setValue(iface.get('split_T', 50.0))
        split_t.setEnabled(is_bs.isChecked())
        
        split_r = QtWidgets.QDoubleSpinBox()
        split_r.setRange(0, 100)
        split_r.setDecimals(1)
        split_r.setSuffix(" %")
        split_r.setValue(iface.get('split_R', 50.0))
        split_r.setEnabled(is_bs.isChecked())
        
        is_pbs = QtWidgets.QCheckBox("Polarizing (PBS)")
        is_pbs.setChecked(iface.get('is_polarizing', False))
        is_pbs.setEnabled(is_bs.isChecked())
        
        pbs_axis = QtWidgets.QDoubleSpinBox()
        pbs_axis.setRange(-180, 180)
        pbs_axis.setDecimals(1)
        pbs_axis.setSuffix(" °")
        pbs_axis.setValue(iface.get('pbs_transmission_axis_deg', 0.0))
        pbs_axis.setEnabled(is_bs.isChecked() and is_pbs.isChecked())
        
        def on_bs_toggled(checked):
            split_t.setEnabled(checked)
            split_r.setEnabled(checked)
            is_pbs.setEnabled(checked)
            pbs_axis.setEnabled(checked and is_pbs.isChecked())
        
        def on_pbs_toggled(checked):
            pbs_axis.setEnabled(is_bs.isChecked() and checked)
        
        is_bs.toggled.connect(on_bs_toggled)
        is_pbs.toggled.connect(on_pbs_toggled)
        
        f.addRow("Start X", x1)
        f.addRow("Start Y", y1)
        f.addRow("End X", x2)
        f.addRow("End Y", y2)
        f.addRow("Refractive Index n1", n1)
        f.addRow("Refractive Index n2", n2)
        f.addRow("", is_bs)
        f.addRow("Transmission %", split_t)
        f.addRow("Reflection %", split_r)
        f.addRow("", is_pbs)
        f.addRow("PBS Axis", pbs_axis)
        
        # Apply and Close buttons (non-modal dialog)
        btn_apply = QtWidgets.QPushButton("Apply")
        btn_close = QtWidgets.QPushButton("Close")
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_close)
        f.addRow(btn_layout)
        
        def apply_changes():
            """Apply changes to interface (can be called multiple times)."""
            iface['x1_mm'] = x1.value()
            iface['y1_mm'] = y1.value()
            iface['x2_mm'] = x2.value()
            iface['y2_mm'] = y2.value()
            iface['n1'] = n1.value()
            iface['n2'] = n2.value()
            iface['is_beam_splitter'] = is_bs.isChecked()
            iface['split_T'] = split_t.value()
            iface['split_R'] = split_r.value()
            iface['is_polarizing'] = is_pbs.isChecked()
            iface['pbs_transmission_axis_deg'] = pbs_axis.value()
            self._update_interface_list()
            
            # Update line color on canvas
            lines = self.canvas.get_all_lines()
            if row < len(lines):
                lines[row].color = self._get_interface_color(iface)
                self.canvas.update_line(row, lines[row])
        
        def on_dialog_close():
            """Unlock canvas when dialog closes."""
            self.canvas.clear_drag_lock()
            self.statusBar().showMessage("Ready")
            d.close()
        
        btn_apply.clicked.connect(apply_changes)
        btn_close.clicked.connect(on_dialog_close)
        
        # Unlock when dialog is destroyed
        d.finished.connect(lambda: self.canvas.clear_drag_lock())
        
        # Show non-modal dialog (allows dragging on canvas)
        d.show()
    
    def _delete_interface(self):
        """Delete the selected interface."""
        row = self.interfaces_list.currentRow()
        if row < 0 or row >= len(self._interfaces):
            QtWidgets.QMessageBox.information(self, "No Selection", "Please select an interface to delete.")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Interface",
            f"Delete interface {row + 1}?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            del self._interfaces[row]
            self.canvas.remove_line(row)
            self._update_interface_list()
    
    def _create_bs_cube_preset(self):
        """Create a beam splitter cube preset (5 interfaces)."""
        # Ask for cube parameters
        d = QtWidgets.QDialog(self)
        d.setWindowTitle("Beam Splitter Cube Preset")
        f = QtWidgets.QFormLayout(d)
        
        size = QtWidgets.QDoubleSpinBox()
        size.setRange(1.0, 1000.0)
        size.setDecimals(2)
        size.setSuffix(" mm")
        size.setValue(25.4)  # 1 inch
        size.setToolTip("Cube side length")
        
        n_glass = QtWidgets.QDoubleSpinBox()
        n_glass.setRange(1.0, 3.0)
        n_glass.setDecimals(4)
        n_glass.setValue(1.517)  # BK7
        n_glass.setToolTip("Refractive index of glass (1.517 for BK7)")
        
        split = QtWidgets.QDoubleSpinBox()
        split.setRange(0, 100)
        split.setDecimals(1)
        split.setSuffix(" %")
        split.setValue(50.0)
        split.setToolTip("Transmission percentage")
        
        is_pbs = QtWidgets.QCheckBox("Polarizing Beam Splitter (PBS)")
        
        pbs_axis = QtWidgets.QDoubleSpinBox()
        pbs_axis.setRange(-180, 180)
        pbs_axis.setDecimals(1)
        pbs_axis.setSuffix(" °")
        pbs_axis.setValue(0.0)
        pbs_axis.setEnabled(False)
        pbs_axis.setToolTip("PBS transmission axis angle (lab frame)")
        
        is_pbs.toggled.connect(lambda checked: pbs_axis.setEnabled(checked))
        
        f.addRow("Cube Size", size)
        f.addRow("Glass Index", n_glass)
        f.addRow("Split T%", split)
        f.addRow("", is_pbs)
        f.addRow("PBS Axis", pbs_axis)
        
        btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        f.addRow(btn)
        btn.accepted.connect(d.accept)
        btn.rejected.connect(d.reject)
        
        if d.exec():
            # Clear existing interfaces and create BS cube
            self._interfaces.clear()
            
            half_size_mm = size.value() / 2.0
            n_g = n_glass.value()
            split_t = split.value()
            split_r = 100.0 - split_t
            
            # Get image dimensions for pixel positioning
            w, h = self.canvas.image_pixel_size()
            center_x = w / 2 if w > 0 else 500
            center_y = h / 2 if h > 0 else 500
            
            # Use a scale factor for visual display (pixels per mm)
            scale = 2.0  # Adjust this to make cube appropriately sized on screen
            half_size_px = half_size_mm * scale
            
            # Interface 1: Left edge (air → glass)
            self._interfaces.append({
                'x1_px': center_x - half_size_px, 'y1_px': center_y - half_size_px,
                'x2_px': center_x - half_size_px, 'y2_px': center_y + half_size_px,
                'x1_mm': -half_size_mm, 'y1_mm': -half_size_mm,
                'x2_mm': -half_size_mm, 'y2_mm': +half_size_mm,
                'n1': 1.0, 'n2': n_g,
                'is_beam_splitter': False,
                'split_T': 50.0, 'split_R': 50.0,
                'is_polarizing': False,
                'pbs_transmission_axis_deg': 0.0
            })
            
            # Interface 2: Bottom edge (air → glass)
            self._interfaces.append({
                'x1_px': center_x - half_size_px, 'y1_px': center_y + half_size_px,
                'x2_px': center_x + half_size_px, 'y2_px': center_y + half_size_px,
                'x1_mm': -half_size_mm, 'y1_mm': -half_size_mm,
                'x2_mm': +half_size_mm, 'y2_mm': -half_size_mm,
                'n1': 1.0, 'n2': n_g,
                'is_beam_splitter': False,
                'split_T': 50.0, 'split_R': 50.0,
                'is_polarizing': False,
                'pbs_transmission_axis_deg': 0.0
            })
            
            # Interface 3: Diagonal beam splitter coating
            self._interfaces.append({
                'x1_px': center_x - half_size_px, 'y1_px': center_y + half_size_px,
                'x2_px': center_x + half_size_px, 'y2_px': center_y - half_size_px,
                'x1_mm': -half_size_mm, 'y1_mm': -half_size_mm,
                'x2_mm': +half_size_mm, 'y2_mm': +half_size_mm,
                'n1': n_g, 'n2': n_g,
                'is_beam_splitter': True,
                'split_T': split_t,
                'split_R': split_r,
                'is_polarizing': is_pbs.isChecked(),
                'pbs_transmission_axis_deg': pbs_axis.value()
            })
            
            # Interface 4: Right edge (glass → air)
            self._interfaces.append({
                'x1_px': center_x + half_size_px, 'y1_px': center_y + half_size_px,
                'x2_px': center_x + half_size_px, 'y2_px': center_y - half_size_px,
                'x1_mm': +half_size_mm, 'y1_mm': -half_size_mm,
                'x2_mm': +half_size_mm, 'y2_mm': +half_size_mm,
                'n1': n_g, 'n2': 1.0,
                'is_beam_splitter': False,
                'split_T': 50.0, 'split_R': 50.0,
                'is_polarizing': False,
                'pbs_transmission_axis_deg': 0.0
            })
            
            # Interface 5: Top edge (glass → air)
            self._interfaces.append({
                'x1_px': center_x - half_size_px, 'y1_px': center_y - half_size_px,
                'x2_px': center_x + half_size_px, 'y2_px': center_y - half_size_px,
                'x1_mm': -half_size_mm, 'y1_mm': +half_size_mm,
                'x2_mm': +half_size_mm, 'y2_mm': +half_size_mm,
                'n1': n_g, 'n2': 1.0,
                'is_beam_splitter': False,
                'split_T': 50.0, 'split_R': 50.0,
                'is_polarizing': False,
                'pbs_transmission_axis_deg': 0.0
            })
            
            self._update_interface_list()
            
            # Auto-select the diagonal coating for easy identification
            self.canvas.select_line(2)
            self.interfaces_list.setCurrentRow(2)
            
            QtWidgets.QMessageBox.information(
                self,
                "Preset Created",
                f"Created beam splitter cube with 5 interfaces:\n"
                f"- 4 blue external surfaces (glass-air refraction)\n"
                f"- 1 green diagonal coating ({split_t:.0f}/{split_r:.0f} split)\n\n"
                f"You can now drag any endpoint to adjust the geometry!"
            )

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
            pix = MultiLineCanvas._render_svg_to_pixmap(path)
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
                            pix = MultiLineCanvas._render_svg_to_pixmap(path)
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
                pix = MultiLineCanvas._render_svg_to_pixmap(text)
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
            pix = MultiLineCanvas._render_svg_to_pixmap(bytes(svg_bytes))
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
        interfaces = list(self._interfaces) if kind == "refractive_object" else []

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
            interfaces=interfaces,
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
                pix = MultiLineCanvas._render_svg_to_pixmap(rec.image_path)
                if pix:
                    self._set_image(pix, rec.image_path)
            else:
                pix = QtGui.QPixmap(rec.image_path)
                if not pix.isNull():
                    self._set_image(pix, rec.image_path)

        # Populate UI
        self.name_edit.setText(rec.name)
        self.kind_combo.setCurrentText(
            rec.kind if rec.kind in ("lens", "mirror", "beamsplitter", "dichroic", "refractive_object") else "lens"
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
        
        # Load interfaces for refractive objects
        if rec.kind == "refractive_object":
            self._interfaces = list(rec.interfaces) if rec.interfaces else []
            self._update_interface_list()
        else:
            self._interfaces = []
            self._update_interface_list()
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
