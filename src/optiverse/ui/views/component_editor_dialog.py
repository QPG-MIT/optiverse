from __future__ import annotations

import os
import json
import re
import time
from typing import Optional, Tuple, List
import math

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import ComponentRecord, serialize_component, deserialize_component
from ...core.interface_definition import InterfaceDefinition
from ...core import interface_types
from ...services.storage_service import StorageService
from ...platform.paths import assets_dir, get_library_path
from ...objects.views import MultiLineCanvas, InterfaceLine
from ..widgets.interface_tree_panel import InterfaceTreePanel
from ..widgets.ruler_widget import CanvasWithRulers


def slugify(name: str) -> str:
    """Convert name to filesystem-safe slug."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "component"


class MoveInterfaceCommand(QtGui.QUndoCommand):
    """Undo command for moving one or more interfaces."""
    
    def __init__(self, editor: 'ComponentEditor', interface_indices: List[int], 
                 old_positions: List[Tuple[float, float, float, float]], 
                 new_positions: List[Tuple[float, float, float, float]]):
        """
        Initialize move command.
        
        Args:
            editor: ComponentEditor instance
            interface_indices: List of interface indices that were moved
            old_positions: List of (x1, y1, x2, y2) tuples for original positions
            new_positions: List of (x1, y1, x2, y2) tuples for new positions
        """
        if len(interface_indices) == 1:
            super().__init__(f"Move Interface {interface_indices[0] + 1}")
        else:
            super().__init__(f"Move {len(interface_indices)} Interfaces")
        
        self.editor = editor
        self.indices = interface_indices
        self.old_positions = old_positions
        self.new_positions = new_positions
    
    def undo(self):
        """Restore old positions."""
        self._apply_positions(self.old_positions)
    
    def redo(self):
        """Apply new positions."""
        self._apply_positions(self.new_positions)
    
    def _apply_positions(self, positions: List[Tuple[float, float, float, float]]):
        """Apply given positions to interfaces."""
        interfaces = self.editor.interface_panel.get_interfaces()
        
        for i, idx in enumerate(self.indices):
            if 0 <= idx < len(interfaces) and i < len(positions):
                x1, y1, x2, y2 = positions[i]
                interfaces[idx].x1_mm = x1
                interfaces[idx].y1_mm = y1
                interfaces[idx].x2_mm = x2
                interfaces[idx].y2_mm = y2
                self.editor.interface_panel.update_interface(idx, interfaces[idx])
        
        # Sync to canvas
        self.editor._sync_interfaces_to_canvas()


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

        # Create undo stack
        self.undo_stack = QtGui.QUndoStack(self)

        self.canvas = MultiLineCanvas()
        self.canvas_with_rulers = CanvasWithRulers(self.canvas)
        self.setCentralWidget(self.canvas_with_rulers)
        self.canvas.imageDropped.connect(self._on_image_dropped)
        self.canvas.linesChanged.connect(self._on_canvas_lines_changed)
        self.canvas.lineSelected.connect(self._on_canvas_line_selected)
        self.canvas.linesSelected.connect(self._on_canvas_lines_selected)
        self.canvas.linesMoved.connect(self._on_canvas_lines_moved)

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
        
        # Ensure toolbar text is visible in light mode on Mac
        tb.setStyleSheet("""
            QToolBar QToolButton {
                color: palette(window-text);
            }
        """)

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
        
        act_import_zemax = QtGui.QAction("Import Zemax…", self)
        act_import_zemax.triggered.connect(self._import_zemax)
        tb.addAction(act_import_zemax)

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
        
        # Undo/Redo shortcuts
        sc_undo = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Undo, self)
        sc_undo.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        sc_undo.activated.connect(self.undo_stack.undo)
        
        sc_redo = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Redo, self)
        sc_redo.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        sc_redo.activated.connect(self.undo_stack.redo)

    def _build_side_dock(self):
        """Build side dock with component settings (v2 interface-based)."""
        dock = QtWidgets.QDockWidget("Component Settings", self)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
        
        w = QtWidgets.QWidget()
        dock.setWidget(w)
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Basic component info
        info_form = QtWidgets.QFormLayout()
        
        self.name_edit = QtWidgets.QLineEdit()
        info_form.addRow("Name", self.name_edit)
        
        # OBJECT HEIGHT (mm) -> physical size reference for calibration
        self.object_height_mm = QtWidgets.QDoubleSpinBox()
        self.object_height_mm.setRange(0.01, 1e7)
        self.object_height_mm.setDecimals(3)
        self.object_height_mm.setSuffix(" mm")
        self.object_height_mm.setValue(25.4)  # Default: 1 inch
        self.object_height_mm.setToolTip("Physical height for calibration (typically size of first interface)")
        self.object_height_mm.valueChanged.connect(self._on_object_height_changed)
        info_form.addRow("Object Height", self.object_height_mm)
        
        layout.addLayout(info_form)
        
        # Separator
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Interface tree panel (collapsible with simplified properties)
        self.interface_panel = InterfaceTreePanel()
        self.interface_panel.interfacesChanged.connect(self._on_interfaces_changed)
        self.interface_panel.interfaceSelected.connect(self._on_interface_panel_selection)
        self.interface_panel.interfacesSelected.connect(self._on_interface_panel_multi_selection)
        layout.addWidget(self.interface_panel, 1)  # Stretch factor 1
        
        # Separator
        separator2 = QtWidgets.QFrame()
        separator2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(separator2)
        
        # Notes field
        notes_form = QtWidgets.QFormLayout()
        self.notes = QtWidgets.QPlainTextEdit()
        self.notes.setPlaceholderText("Optional notes…")
        self.notes.setMaximumHeight(60)
        notes_form.addRow("Notes", self.notes)
        layout.addLayout(notes_form)

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

    # ---------- Callbacks (New Interface-Based System) ----------
    
    def _on_object_height_changed(self):
        """Handle object height changes."""
        # Recalculate mm/px ratio and update canvas synchronization
        self._sync_interfaces_to_canvas()
    
    def _on_interfaces_changed(self):
        """Handle interface list changes from panel."""
        # Sync to canvas
        self._sync_interfaces_to_canvas()
    
    def _on_interface_panel_selection(self, index: int):
        """Handle interface selection in panel (single)."""
        # Highlight corresponding line on canvas
        if 0 <= index < len(self.canvas.get_all_lines()):
            self.canvas.select_line(index)
    
    def _on_interface_panel_multi_selection(self, indices: List[int]):
        """Handle multiple interface selection in panel."""
        # Highlight corresponding lines on canvas
        self.canvas.select_lines(indices)
    
    def _on_canvas_lines_selected(self, indices: List[int]):
        """Handle multiple line selection on canvas."""
        # Sync selection to interface panel
        self.interface_panel.select_interfaces(indices)
    
    def _on_canvas_lines_moved(self, indices: List[int], 
                                old_positions: List[Tuple[float, float, float, float]], 
                                new_positions: List[Tuple[float, float, float, float]]):
        """Handle line movement completion - create undo command."""
        if indices and old_positions and new_positions:
            # Create and push undo command
            command = MoveInterfaceCommand(self, indices, old_positions, new_positions)
            self.undo_stack.push(command)
    
    # ---------- Legacy Helpers (deprecated but kept for compatibility) ----------

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
        """Set canvas image (v2 system)."""
        if pix.isNull():
            QtWidgets.QMessageBox.warning(self, "Load failed", "Could not load image.")
            return
        self.canvas.set_pixmap(pix, source_path)
        self._sync_interfaces_to_canvas()
        
        # Update status message based on number of interfaces
        num_interfaces = self.interface_panel.count()
        if num_interfaces == 0:
            self.statusBar().showMessage(
                "Image loaded! Add interfaces using the 'Add Interface' button."
            )
        else:
            self.statusBar().showMessage(
                "Image loaded! Drag interface endpoints to align with your optical elements."
            )

    def _new_component(self):
        """Reset to new component state (v2 system)."""
        self.canvas.set_pixmap(QtGui.QPixmap(), None)
        self.canvas.clear_lines()
        self.name_edit.clear()
        self.object_height_mm.setValue(25.4)  # 1 inch default
        self.interface_panel.clear()
        self.notes.clear()
        
        # Status message
        self.statusBar().showMessage("Ready. Load an image and add interfaces to begin.")
    
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
        """Sync interface panel to canvas visual display (v2 system)."""
        if not self.canvas.has_image():
            return
        
        # Block signals during bulk update
        self.canvas.blockSignals(True)
        self.canvas.clear_lines()
        
        # Get interfaces from panel
        interfaces = self.interface_panel.get_interfaces()
        
        if not interfaces:
            self.canvas.blockSignals(False)
            return
        
        # Compute scaling: Y-axis goes from 0 (top) to object_height (bottom)
        # Image height in pixels maps to object_height in mm
        object_height = self.object_height_mm.value()
        w, h = self.canvas.image_pixel_size()
        
        if h > 0 and object_height > 0:
            # mm_per_px based on image height mapping to object_height
            mm_per_px = object_height / h
        else:
            mm_per_px = 1.0  # Fallback
        
        # Set the canvas's coordinate conversion factor
        self.canvas.set_mm_per_pixel(mm_per_px)
        
        # COORDINATE SYSTEM
        # Storage (InterfaceDefinition): (0,0) at IMAGE CENTER, Y-up (math), in mm
        # Canvas (MultiLineCanvas): (0,0) at IMAGE CENTER, Y-up (math), in mm
        # No transformation needed.
        
        # Add each interface for display
        for i, interface in enumerate(interfaces):
            # Get color from interface
            r, g, b = interface.get_color()
            color = QtGui.QColor(r, g, b)
            
            # Use coords directly (both storage and canvas use Y-up)
            x1_canvas = interface.x1_mm
            y1_canvas = interface.y1_mm
            x2_canvas = interface.x2_mm
            y2_canvas = interface.y2_mm
            
            # Debug validation: Check if coordinates are reasonable
            max_coord = object_height * 2  # Sanity check: coords shouldn't exceed 2x object height
            if (abs(x1_canvas) > max_coord or abs(y1_canvas) > max_coord or 
                abs(x2_canvas) > max_coord or abs(y2_canvas) > max_coord):
                print(f"Warning: Interface {i} has unusually large coordinates:")
                print(f"  Storage: ({interface.x1_mm:.2f}, {interface.y1_mm:.2f}) to ({interface.x2_mm:.2f}, {interface.y2_mm:.2f})")
                print(f"  Canvas: ({x1_canvas:.2f}, {y1_canvas:.2f}) to ({x2_canvas:.2f}, {y2_canvas:.2f})")
            
            # Create InterfaceLine for canvas display
            line = InterfaceLine(
                x1=x1_canvas, y1=y1_canvas,
                x2=x2_canvas, y2=y2_canvas,
                color=color,
                label=interface.get_label(),
                properties={'interface': interface}
            )
            self.canvas.add_line(line)
        
        self.canvas.blockSignals(False)
        self.canvas.update()  # Force repaint
    
    def _on_canvas_lines_changed(self):
        """Called when canvas lines change (user dragging) - v2 system."""
        # Get interfaces from panel
        interfaces = self.interface_panel.get_interfaces()
        if not interfaces:
            return
        
        # Block interface panel signals to prevent feedback loop during drag
        self.interface_panel.blockSignals(True)
        
        try:
            # COORDINATE SYSTEM
            # Both Canvas and Storage use Y-up coordinates - no transformation needed!
            
            # Update interface coordinates from canvas
            lines = self.canvas.get_all_lines()
            for i, line in enumerate(lines):
                if i < len(interfaces):
                    # Use coords directly (both canvas and storage use Y-up)
                    interfaces[i].x1_mm = line.x1
                    interfaces[i].y1_mm = line.y1
                    interfaces[i].x2_mm = line.x2
                    interfaces[i].y2_mm = line.y2
                    
                    # Debug: Log coordinates (both use Y-down)
                    if False:  # Set to True for debugging
                        print(f"Interface {i} dragged:")
                        print(f"  Canvas (Y-down): ({line.x1:.2f}, {line.y1:.2f}) to ({line.x2:.2f}, {line.y2:.2f})")
                        print(f"  Storage (Y-down): ({interfaces[i].x1_mm:.2f}, {interfaces[i].y1_mm:.2f}) to ({interfaces[i].x2_mm:.2f}, {interfaces[i].y2_mm:.2f})")
                    
                    # Update the interface in the panel (silently - signals blocked)
                    self.interface_panel.update_interface(i, interfaces[i])
        finally:
            # Always unblock signals
            self.interface_panel.blockSignals(False)
    
    def _on_canvas_line_selected(self, index: int):
        """Called when a line is selected on canvas - v2 system."""
        # Select corresponding interface in panel
        self.interface_panel.select_interface(index)
    

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
    
    def _import_zemax(self):
        """Import Zemax ZMX file."""
        from ...services.zemax_parser import ZemaxParser
        from ...services.zemax_converter import ZemaxToInterfaceConverter
        from ...services.glass_catalog import GlassCatalog
        
        # Open file dialog
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import Zemax File",
            "",
            "Zemax Files (*.zmx *.ZMX);;All Files (*.*)"
        )
        
        if not filepath:
            return
        
        try:
            # Parse Zemax file
            parser = ZemaxParser()
            zemax_data = parser.parse(filepath)
            
            if not zemax_data:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Import Error",
                    "Failed to parse Zemax file. The file may be corrupted or in an unsupported format."
                )
                return
            
            # Convert to interfaces
            catalog = GlassCatalog()
            converter = ZemaxToInterfaceConverter(catalog)
            component = converter.convert(zemax_data)
            
            # Load into editor
            self._load_component_record(component)
            
            # Show success message with summary
            num_interfaces = len(component.interfaces) if component.interfaces else 0
            
            # Determine component type from interfaces
            if num_interfaces > 1:
                component_type = f"Multi-element ({num_interfaces} interfaces)"
            elif num_interfaces == 1:
                element_type = component.interfaces[0].element_type.replace("_", " ").title()
                component_type = element_type
            else:
                component_type = "Unknown"
            
            msg = f"Successfully imported {num_interfaces} interface(s) from Zemax file:\n\n"
            msg += f"Name: {component.name}\n"
            msg += f"Type: {component_type}\n"
            msg += f"Aperture: {component.object_height_mm:.2f} mm\n\n"
            
            if component.interfaces:
                msg += "Interfaces:\n"
                for i, iface in enumerate(component.interfaces[:5]):  # Show first 5
                    curv_str = f" [R={iface.radius_of_curvature_mm:.1f}mm]" if iface.is_curved else ""
                    msg += f"  {i+1}. {iface.name}{curv_str}\n"
                if num_interfaces > 5:
                    msg += f"  ... and {num_interfaces - 5} more\n"
                
                msg += "\n"
                if not self.canvas.has_image():
                    msg += "💡 TIP: Load an image (File → Open Image) to visualize\n"
                    msg += "    the interfaces on the canvas. The interfaces are listed\n"
                    msg += "    in the panel on the right.\n"
                    msg += "\n"
                msg += "👉 Expand each interface in the list to see:\n"
                msg += "   • Refractive indices (n₁, n₂)\n"
                msg += "   • Curvature (is_curved, radius_of_curvature_mm)\n"
                msg += "   • Position and geometry\n"
            
            self.statusBar().showMessage(
                f"Imported {num_interfaces} interfaces from Zemax"
            )
            
            QtWidgets.QMessageBox.information(
                self,
                "Import Successful",
                msg
            )
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QtWidgets.QMessageBox.critical(
                self,
                "Import Error",
                f"Error importing Zemax file:\n\n{str(e)}\n\nDetails:\n{error_details}"
            )
    
    def _load_component_record(self, component: ComponentRecord):
        """Load a ComponentRecord into the editor."""
        # Clear existing
        self.canvas.clear_points()
        
        # Set component properties
        self.name_edit.setText(component.name)
        self.object_height_mm.setValue(component.object_height_mm)
        
        # Load interfaces into panel
        self.interface_panel.clear()
        if component.interfaces:
            for interface in component.interfaces:
                self.interface_panel.add_interface(interface)
            
            # Sync interfaces to canvas
            self._sync_interfaces_to_canvas()
            
            # Update status
            self.statusBar().showMessage(
                f"Loaded component with {len(component.interfaces)} interface(s)"
            )

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
        """Build ComponentRecord from UI state (v2 format)."""
        # Get interfaces from panel first
        interfaces = self.interface_panel.get_interfaces()
        
        # Check if we have either an image or interfaces (Zemax imports may have no image)
        has_image = self.canvas.has_image()
        if not has_image and not interfaces:
            QtWidgets.QMessageBox.warning(
                self, 
                "Missing data", 
                "Either load an image with calibration line, or import interfaces from Zemax."
            )
            return None
        
        if not interfaces:
            QtWidgets.QMessageBox.warning(
                self,
                "No interfaces",
                "Add at least one interface to define the component."
            )
            return None
        
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Missing name", "Please enter a component name.")
            return None

        object_height = self._get_object_height()
        
        if object_height <= 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing object height",
                "Please set a positive object height (mm)."
            )
            return None
        
        # Save asset file (normalized to 1000px height) only if image exists
        asset_path = ""
        if has_image:
            asset_path = self._ensure_asset_file_normalized(name)

        # Create v2 ComponentRecord
        return ComponentRecord(
            name=name,
            image_path=asset_path,
            object_height_mm=object_height,
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
            
            # Display element type and interface count instead of kind
            if rec.interfaces and len(rec.interfaces) > 0:
                if len(rec.interfaces) > 1:
                    type_label = f"Multi-element ({len(rec.interfaces)} interfaces)"
                else:
                    element_type = rec.interfaces[0].element_type.replace("_", " ").title()
                    type_label = element_type
            else:
                type_label = "Unknown"
            
            it = QtWidgets.QListWidgetItem(icon, f"{name}\n({type_label})")
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
        
        # Set object height
        if rec.object_height_mm > 0:
            self.object_height_mm.setValue(rec.object_height_mm)
        
        # Load interfaces into panel
        self.interface_panel.clear()
        if rec.interfaces:
            for interface in rec.interfaces:
                self.interface_panel.add_interface(interface)
        
        # Notes
        self.notes.setPlainText(rec.notes)
        
        # Sync to canvas
        self._sync_interfaces_to_canvas()

    def save_component(self):
        """Save component to library."""
        rec = self._build_record_from_ui()
        if not rec:
            return
        
        # Debug: Print what we're about to save
        print(f"[DEBUG] Saving component: {rec.name}")
        print(f"[DEBUG] Number of interfaces: {len(rec.interfaces) if rec.interfaces else 0}")
        if rec.interfaces:
            for i, iface in enumerate(rec.interfaces[:3]):  # Show first 3
                print(f"[DEBUG]   Interface {i+1}: {iface.name} at ({iface.x1_mm:.2f}, {iface.y1_mm:.2f})")
        
        serialized = serialize_component(rec)
        print(f"[DEBUG] Serialized keys: {serialized.keys()}")
        print(f"[DEBUG] Has 'interfaces' in serialized: {'interfaces' in serialized}")
        if 'interfaces' in serialized:
            print(f"[DEBUG] Number of interfaces in serialized: {len(serialized['interfaces'])}")
        
        allrows = self.storage.load_library()
        # Replace by name or append
        replaced = False
        for i, row in enumerate(allrows):
            if row.get("name") == rec.name:
                allrows[i] = serialized
                replaced = True
                break
        
        if not replaced:
            allrows.append(serialized)
        
        self.storage.save_library(allrows)
        QtWidgets.QApplication.clipboard().setText(json.dumps(serialized, indent=2))
        QtWidgets.QMessageBox.information(
            self,
            "Saved",
            f"Saved component '{rec.name}'\n\n"
            f"Interfaces: {len(rec.interfaces) if rec.interfaces else 0}\n"
            f"Library file:\n{get_library_path()}\n\n"
            f"Component JSON copied to clipboard."
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
