from __future__ import annotations

import json
import logging
import os

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import ComponentRecord, deserialize_component, serialize_component
from ...core.undo_commands import Command
from ...core.undo_stack import UndoStack
from ...objects.views import InterfaceLine, MultiLineCanvas
from ...services.storage_service import StorageService
from ..widgets.interface_tree_panel import InterfaceTreePanel
from ..widgets.ruler_widget import CanvasWithRulers
from .component_image_handler import ComponentImageHandler
from .component_library_io import ComponentLibraryIO
from .zemax_importer import ZemaxImporter

_logger = logging.getLogger(__name__)


class MoveInterfaceCommand(Command):
    """Undo command for moving one or more interfaces."""

    def __init__(
        self,
        editor: ComponentEditor,
        interface_indices: list[int],
        old_positions: list[tuple[float, float, float, float]],
        new_positions: list[tuple[float, float, float, float]],
    ):
        """
        Initialize move command.

        Args:
            editor: ComponentEditor instance
            interface_indices: List of interface indices that were moved
            old_positions: List of (x1, y1, x2, y2) tuples for original positions
            new_positions: List of (x1, y1, x2, y2) tuples for new positions
        """
        self.editor = editor
        self.indices = interface_indices
        self.old_positions = old_positions
        self.new_positions = new_positions

    def execute(self):
        """Apply new positions."""
        self._apply_positions(self.new_positions)

    def undo(self):
        """Restore old positions."""
        self._apply_positions(self.old_positions)

    def _apply_positions(self, positions: list[tuple[float, float, float, float]]):
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
        self.undo_stack = UndoStack()
        self.undo_stack.canUndoChanged.connect(self._update_undo_actions)
        self.undo_stack.canRedoChanged.connect(self._update_undo_actions)
        self.undo_stack.commandPushed.connect(self._mark_modified)

        # Track unsaved changes
        self._modified = False

        # Library I/O handler (initialized after UI setup in _build_library_dock)
        self._library_io: ComponentLibraryIO | None = None

        # Image handler (initialized after canvas creation)
        self._image_handler: ComponentImageHandler | None = None

        self.canvas = MultiLineCanvas()
        self.canvas_with_rulers = CanvasWithRulers(self.canvas)
        self.setCentralWidget(self.canvas_with_rulers)
        self.canvas.linesChanged.connect(self._on_canvas_lines_changed)
        self.canvas.linesChanged.connect(self._mark_modified)
        self.canvas.lineSelected.connect(self._on_canvas_line_selected)
        self.canvas.linesSelected.connect(self._on_canvas_lines_selected)
        self.canvas.linesMoved.connect(self._on_canvas_lines_moved)
        self.canvas.linesMoved.connect(self._mark_modified)

        # Image handler
        self._image_handler = ComponentImageHandler(
            canvas=self.canvas,
            parent_widget=self,
            set_image_callback=self._set_image,
            paste_json_callback=self.paste_component_json,
        )
        self.canvas.imageDropped.connect(self._image_handler.on_image_dropped)

        # Zemax importer
        self._zemax_importer = ZemaxImporter(self)

        self._build_side_dock()
        self._build_library_dock()
        self._build_toolbar()
        self._build_shortcuts()

        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage(
                "Load image, enter object height (mm), "
                "then click two points on the optical element."
            )

    # ---------- UI Building ----------
    def _build_toolbar(self):
        """Build main toolbar with actions."""
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        # Ensure toolbar text is visible in light mode on Mac
        tb.setStyleSheet(
            """
            QToolBar QToolButton {
                color: palette(window-text);
            }
        """
        )

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

        act_export = QtGui.QAction("Export Component…", self)
        act_export.triggered.connect(self.export_component)
        tb.addAction(act_export)

        act_import = QtGui.QAction("Import Component…", self)
        act_import.triggered.connect(self.import_component)
        tb.addAction(act_import)

        tb.addSeparator()

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

        # Save shortcut
        sc_save = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Save, self)
        sc_save.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        sc_save.activated.connect(self.save_component)

    def _update_undo_actions(self):
        """Update undo/redo action states (called by undo stack signals)."""
        # Actions can be added here if needed
        pass

    def _mark_modified(self):
        """Mark the component as having unsaved changes."""
        self._modified = True

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
        self.name_edit.textChanged.connect(self._mark_modified)
        info_form.addRow("Name", self.name_edit)

        # Category selector (editable to allow custom categories)
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(
            [
                "Lenses",
                "Objectives",
                "Mirrors",
                "Beamsplitters",
                "Dichroics",
                "Waveplates",
                "Sources",
                "Background",
                "Misc",
                "Other",
            ]
        )
        self.category_combo.setToolTip("Select a category or type a custom one")
        self.category_combo.currentTextChanged.connect(self._mark_modified)
        info_form.addRow("Category", self.category_combo)

        # OBJECT HEIGHT (mm) -> physical size reference for calibration
        self.object_height_mm = QtWidgets.QDoubleSpinBox()
        self.object_height_mm.setRange(0.01, 1e7)
        self.object_height_mm.setDecimals(3)
        self.object_height_mm.setSuffix(" mm")
        self.object_height_mm.setValue(25.4)  # Default: 1 inch
        self.object_height_mm.setToolTip(
            "Physical height for calibration (typically size of first interface)"
        )
        self.object_height_mm.valueChanged.connect(self._on_object_height_changed)
        self.object_height_mm.valueChanged.connect(self._mark_modified)
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
        self.interface_panel.interfacesChanged.connect(self._mark_modified)
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
        self.notes.textChanged.connect(self._mark_modified)
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

        # Initialize library I/O handler
        self._library_io = ComponentLibraryIO(
            storage=self.storage,
            parent_widget=self,
            build_record_callback=self._build_record_from_ui,
            refresh_callback=self._refresh_library_list,
            saved_callback=self.saved.emit,
        )

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

    def _on_interface_panel_multi_selection(self, indices: list[int]):
        """Handle multiple interface selection in panel."""
        # Highlight corresponding lines on canvas
        self.canvas.select_lines(indices)

    def _on_canvas_lines_selected(self, indices: list[int]):
        """Handle multiple line selection on canvas."""
        # Sync selection to interface panel
        self.interface_panel.select_interfaces(indices)

    def _on_canvas_lines_moved(
        self,
        indices: list[int],
        old_positions: list[tuple[float, float, float, float]],
        new_positions: list[tuple[float, float, float, float]],
    ):
        """Handle line movement completion - create undo command."""
        if indices and old_positions and new_positions:
            # Create and push undo command
            command = MoveInterfaceCommand(self, indices, old_positions, new_positions)
            self.undo_stack.push(command)

    # ---------- Legacy Helpers (deprecated but kept for compatibility) ----------

    def _update_derived_labels(self, *args):
        """Update computed values from object height and picked line."""
        float(self.object_height_mm.value())

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
            px_len = (dx * dx + dy * dy) ** 0.5

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
        status_bar = self.statusBar()
        if status_bar is not None:
            if num_interfaces == 0:
                status_bar.showMessage(
                    "Image loaded! Add interfaces using the 'Add Interface' button."
                )
            else:
                status_bar.showMessage(
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
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage("Ready. Load an image and add interfaces to begin.")

    # ---------- Canvas/Interface Synchronization ----------

    def _get_interface_color(self, iface: dict) -> QtGui.QColor:
        """Get color for interface based on its properties."""
        if iface.get("is_beam_splitter", False):
            if iface.get("is_polarizing", False):
                return QtGui.QColor(150, 0, 150)  # Purple for PBS
            else:
                return QtGui.QColor(0, 150, 120)  # Green for BS
        else:
            # Regular refractive interface
            n1 = iface.get("n1", 1.0)
            n2 = iface.get("n2", 1.0)
            if abs(n1 - n2) > 0.01:
                return QtGui.QColor(100, 100, 255)  # Blue for refraction
            else:
                return QtGui.QColor(150, 150, 150)  # Gray for same index

    def _get_simple_component_color(self) -> QtGui.QColor:
        """Get color for simple component types."""
        if not hasattr(self, "kind_combo") or self.kind_combo is None:
            return QtGui.QColor(150, 150, 150)  # Default gray
        kind = self.kind_combo.currentText()
        colors = {
            "lens": QtGui.QColor(0, 180, 180),  # Cyan
            "mirror": QtGui.QColor(255, 140, 0),  # Orange
            "beamsplitter": QtGui.QColor(0, 150, 120),  # Green
            "dichroic": QtGui.QColor(255, 0, 255),  # Magenta
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
        # Qt Display: Y-down conversion happens in ComponentSprite only
        # No transformation needed here - both use Y-up.

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
            if (
                abs(x1_canvas) > max_coord
                or abs(y1_canvas) > max_coord
                or abs(x2_canvas) > max_coord
                or abs(y2_canvas) > max_coord
            ):
                _logger.warning(
                    "Interface %d has unusually large coordinates: "
                    "Storage: (%.2f, %.2f) to (%.2f, %.2f), Canvas: (%.2f, %.2f) to (%.2f, %.2f)",
                    i,
                    interface.x1_mm,
                    interface.y1_mm,
                    interface.x2_mm,
                    interface.y2_mm,
                    x1_canvas,
                    y1_canvas,
                    x2_canvas,
                    y2_canvas,
                )

            # Create InterfaceLine for canvas display
            line = InterfaceLine(
                x1=x1_canvas,
                y1=y1_canvas,
                x2=x2_canvas,
                y2=y2_canvas,
                color=color,
                label=interface.get_label(),
                properties={"interface": interface},
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

                    # Debug: Log coordinates (both use Y-up)
                    _logger.debug(
                        "Interface %d dragged: Canvas (Y-up): (%.2f, %.2f) to (%.2f, %.2f), "
                        "Storage (Y-up): (%.2f, %.2f) to (%.2f, %.2f)",
                        i,
                        line.x1,
                        line.y1,
                        line.x2,
                        line.y2,
                        interfaces[i].x1_mm,
                        interfaces[i].y1_mm,
                        interfaces[i].x2_mm,
                        interfaces[i].y2_mm,
                    )

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
        """Open image file dialog (delegated to image_handler)."""
        if self._image_handler:
            self._image_handler.open_image()

    def _import_zemax(self):
        """Import Zemax ZMX file."""
        component = self._zemax_importer.import_file()
        if component:
            self._load_component_record(component)
            num_interfaces = len(component.interfaces) if component.interfaces else 0
            status_bar = self.statusBar()
            if status_bar is not None:
                status_bar.showMessage(f"Imported {num_interfaces} interfaces from Zemax")

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
            status_bar = self.statusBar()
            if status_bar is not None:
                status_bar.showMessage(
                    f"Loaded component with {len(component.interfaces)} interface(s)"
                )

    def paste_image(self):
        """Paste image from clipboard (delegated to image_handler)."""
        if self._image_handler:
            self._image_handler.paste_image()

    def _smart_paste(self):
        """Smart paste (delegated to image_handler)."""
        if self._image_handler:
            self._image_handler.smart_paste()

    # ---------- JSON Copy/Paste ----------
    def _build_record_from_ui(self) -> ComponentRecord | None:
        """Build ComponentRecord from UI state (v2 format)."""
        # Get interfaces from panel first
        interfaces = self.interface_panel.get_interfaces()

        # Check if we have either an image or interfaces (Zemax imports may have no image)
        has_image = self.canvas.has_image()
        if not has_image and not interfaces:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing data",
                "Either load an image with calibration line, or import interfaces from Zemax.",
            )
            return None

        if not interfaces:
            QtWidgets.QMessageBox.information(
                self,
                "No interfaces",
                "This component has no interfaces defined. "
                "It will be saved as a decorative/background item "
                "with no optical properties.",
            )
            # Continue without returning None - allow saving as decorative item

        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Missing name", "Please enter a component name.")
            return None

        object_height = self._get_object_height()

        if object_height <= 0:
            QtWidgets.QMessageBox.warning(
                self, "Missing object height", "Please set a positive object height (mm)."
            )
            return None

        # Save asset file (normalized to 1000px height) only if image exists
        asset_path = ""
        if has_image and self._image_handler:
            asset_path = self._image_handler.ensure_asset_file_normalized(name)

        # Get category from combobox and convert to storage format (lowercase)
        category = self.category_combo.currentText().strip().lower()

        # Create v2 ComponentRecord
        return ComponentRecord(
            name=name,
            image_path=asset_path,
            object_height_mm=object_height,
            interfaces=interfaces,
            category=category,
            notes=self.notes.toPlainText().strip(),
        )

    def copy_component_json(self):
        """Copy component as JSON to clipboard."""
        rec = self._build_record_from_ui()
        if not rec:
            return
        payload = json.dumps(serialize_component(rec, self.storage.settings_service), indent=2)
        QtWidgets.QApplication.clipboard().setText(payload)
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage("Component JSON copied to clipboard.", 2000)

    def paste_component_json(self):
        """Paste component from JSON."""
        clipboard = QtWidgets.QApplication.clipboard()
        if clipboard is None:
            QtWidgets.QMessageBox.information(
                self, "Paste Component JSON", "Clipboard is not available."
            )
            return
        text = clipboard.text()
        if text is None:
            QtWidgets.QMessageBox.information(self, "Paste Component JSON", "Clipboard is empty.")
            return
        text = text.strip()
        if not text:
            QtWidgets.QMessageBox.information(self, "Paste Component JSON", "Clipboard is empty.")
            return

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.warning(self, "Invalid JSON", f"Could not parse JSON:\n{e}")
            return

        self._load_from_dict(data)
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage("Component JSON pasted.", 2000)

    # ---------- Library ----------
    def _refresh_library_list(self):
        """Refresh library list widget."""
        self.libList.clear()
        rows = self.storage.load_library()

        for row in rows:
            rec = deserialize_component(row, self.storage.settings_service)
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
        rec = deserialize_component(data, self.storage.settings_service)
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

        # Set category
        if rec.category:
            # Convert from storage format (lowercase) to UI format (capitalized)
            category_ui = rec.category.capitalize()
            self.category_combo.setCurrentText(category_ui)
        else:
            self.category_combo.setCurrentText("Other")

        # Load interfaces into panel
        self.interface_panel.clear()
        if rec.interfaces:
            for interface in rec.interfaces:
                self.interface_panel.add_interface(interface)

        # Notes
        self.notes.setPlainText(rec.notes)

        # Sync to canvas
        self._sync_interfaces_to_canvas()

    def save_component(self) -> bool:
        """Save component to library (delegated to library_io).

        Returns:
            True if save was successful, False otherwise.
        """
        if self._library_io:
            if self._library_io.save_component():
                self._modified = False
                return True
        return False

    def export_component(self):
        """Export current component to a folder (delegated to library_io)."""
        if self._library_io:
            self._library_io.export_component()

    def import_component(self):
        """Import a component from a folder (delegated to library_io)."""
        if self._library_io:
            self._library_io.import_component()

    def reload_library(self):
        """Reload library from disk (delegated to library_io)."""
        if self._library_io:
            self._library_io.reload_library()

    def load_library_from_path(self):
        """Load component library from a custom path (delegated to library_io)."""
        if self._library_io:
            self._library_io.load_library_from_path()

    def closeEvent(self, event: QtGui.QCloseEvent):
        """Handle window close event, prompting to save unsaved changes."""
        if self._modified:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QtWidgets.QMessageBox.StandardButton.Save
                | QtWidgets.QMessageBox.StandardButton.Discard
                | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Save,
            )

            if reply == QtWidgets.QMessageBox.StandardButton.Save:
                if self.save_component():
                    event.accept()
                else:
                    # Save failed or was cancelled, don't close
                    event.ignore()
            elif reply == QtWidgets.QMessageBox.StandardButton.Discard:
                event.accept()
            else:  # Cancel
                event.ignore()
        else:
            event.accept()


# Keep old name for backward compatibility
ComponentEditorDialog = ComponentEditor
