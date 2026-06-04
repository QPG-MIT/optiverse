from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.models import ComponentRecord, deserialize_component, serialize_component
from ...core.undo_commands import Command
from ...core.undo_stack import UndoStack
from ...objects.views import InterfaceLine, MultiLineCanvas
from ...services.storage_service import StorageService
from ..widgets.interface_tree_panel import InterfaceTreePanel
from ..widgets.ruler_widget import CanvasWithRulers
from ..widgets.smart_spinbox import SmartDoubleSpinBox
from .component_image_handler import ComponentImageHandler
from .component_library_io import ComponentLibraryIO, _pick_existing_directory, _pick_open_file
from .zemax_importer import ZemaxImporter

_logger = logging.getLogger(__name__)

# Save To combo: extra rows (userData) — not real library paths
_SAVE_TO_CREATE_NEW_DATA = "__create_new__"
_SAVE_TO_MANAGE_LIBRARIES_DATA = "__manage_libraries__"
_SAVE_TO_SENTINEL_DATA = frozenset({_SAVE_TO_CREATE_NEW_DATA, _SAVE_TO_MANAGE_LIBRARIES_DATA})


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
    Upgraded from Dialog to MainWindow with menu bar, library dock, and clipboard operations.
    """

    saved = QtCore.pyqtSignal()

    def __init__(
        self,
        storage: StorageService,
        parent: QtWidgets.QWidget | None = None,
        library_service=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Component Editor")
        self.resize(1100, 680)
        self.storage = storage
        self._library_service = library_service

        # Create undo stack
        self.undo_stack = UndoStack()
        self.undo_stack.commandPushed.connect(self._mark_modified)

        # Track unsaved changes
        self._modified = False

        # Last real library path for Save To (restored after sentinel actions / repopulate)
        self._save_to_last_path: str | None = None

        # Track editing context for save guards
        self._original_name: str | None = None
        self._component_source: str | None = None  # "builtin", "user", or None (new)

        # STEP file attached during STEP import (persisted in component folder on save)
        self._step_file_path: str | None = None

        # Back-reference to main window (set externally after construction)
        self._main_window: QtWidgets.QWidget | None = None

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
        self._build_menu_bar()

        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage(
                "Load image, enter object height (mm), "
                "then click two points on the optical element."
            )

    # ---------- UI Building ----------

    def _build_menu_bar(self):
        """Build the menu bar with File, Edit, Library, and Canvas menus."""
        mb = self.menuBar()
        if mb is None:
            return

        # --- File menu ---
        file_menu = mb.addMenu("&File")
        if file_menu is None:
            return

        self._act_new = file_menu.addAction("&New")
        if self._act_new:
            self._act_new.setShortcut(QtGui.QKeySequence.StandardKey.New)
            self._act_new.triggered.connect(self._new_component)

        act = file_menu.addAction("&Open Image\u2026")
        if act:
            act.triggered.connect(self.open_image)

        file_menu.addSeparator()

        act = file_menu.addAction("Import &Zemax\u2026")
        if act:
            act.triggered.connect(self._import_zemax)

        act = file_menu.addAction("Import &STEP\u2026")
        if act:
            act.triggered.connect(self._import_step)

        act = file_menu.addAction("&Import Component\u2026")
        if act:
            act.triggered.connect(self.import_component)

        act = file_menu.addAction("&Export Component\u2026")
        if act:
            act.triggered.connect(self.export_component)

        file_menu.addSeparator()

        self._act_save = file_menu.addAction("&Save")
        if self._act_save:
            self._act_save.setShortcut(QtGui.QKeySequence.StandardKey.Save)
            self._act_save.setIcon(QtGui.QIcon())
            self._act_save.triggered.connect(self.save_component)

        # --- Edit menu ---
        edit_menu = mb.addMenu("&Edit")
        if edit_menu is None:
            return

        self._act_undo = edit_menu.addAction("&Undo")
        if self._act_undo:
            self._act_undo.setShortcut(QtGui.QKeySequence.StandardKey.Undo)
            self._act_undo.setIcon(QtGui.QIcon())
            self._act_undo.triggered.connect(self.undo_stack.undo)

        self._act_redo = edit_menu.addAction("&Redo")
        if self._act_redo:
            self._act_redo.setShortcut(QtGui.QKeySequence.StandardKey.Redo)
            self._act_redo.setIcon(QtGui.QIcon())
            self._act_redo.triggered.connect(self.undo_stack.redo)

        edit_menu.addSeparator()

        self._act_copy = edit_menu.addAction("Copy Component &JSON")
        if self._act_copy:
            self._act_copy.setShortcut(QtGui.QKeySequence.StandardKey.Copy)
            self._act_copy.triggered.connect(self.copy_component_json)

        self._act_paste = edit_menu.addAction("&Paste")
        if self._act_paste:
            self._act_paste.setShortcut(QtGui.QKeySequence.StandardKey.Paste)
            self._act_paste.triggered.connect(self._smart_paste)

        act = edit_menu.addAction("Paste Component JSON")
        if act:
            act.triggered.connect(self.paste_component_json)

        edit_menu.addSeparator()

        act = edit_menu.addAction("Clear &Points")
        if act:
            act.triggered.connect(self.canvas.clear_points)

        # --- Library menu ---
        lib_menu = mb.addMenu("&Library")
        if lib_menu is None:
            return

        act = lib_menu.addAction("&Reload Library")
        if act:
            act.triggered.connect(self.reload_library)

        act = lib_menu.addAction("Load Library from &Path\u2026")
        if act:
            act.triggered.connect(self.load_library_from_path)

        # --- Canvas menu ---
        canvas_menu = mb.addMenu("&Canvas")
        if canvas_menu is None:
            return

        act = canvas_menu.addAction("&Update Canvas Instances\u2026")
        if act:
            act.triggered.connect(self._on_update_canvas_instances)

        # Register shortcut-bearing actions on the window with WindowShortcut
        # context so they reliably fire when this editor is active.
        for a in (
            self._act_new, self._act_save,
            self._act_undo, self._act_redo,
            self._act_copy, self._act_paste,
        ):
            if a:
                a.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
                self.addAction(a)

    def _mark_modified(self):
        """Mark the component as having unsaved changes."""
        self._modified = True

    def _set_name_edit_text(self, text: str) -> None:
        """Set the Name field and show the start of the text.

        QLineEdit leaves the cursor at the end after setText(), so long names
        appear truncated on the left; users expect to see the beginning first.
        """
        self.name_edit.setText(text)
        self.name_edit.setCursorPosition(0)

    def _populate_save_to_combo(self):
        """Populate the 'Save To' dropdown with writable library directories."""
        self.save_to_combo.clear()
        if self._library_service is not None:
            for lib in self._library_service.get_writable():
                self.save_to_combo.addItem(lib.name, str(lib.path))
        else:
            from ...platform.paths import get_user_library_root

            root = get_user_library_root()
            self.save_to_combo.addItem(root.name, str(root))

        self.save_to_combo.insertSeparator(self.save_to_combo.count())
        self.save_to_combo.addItem("Create New...", _SAVE_TO_CREATE_NEW_DATA)
        self.save_to_combo.addItem("Manage Libraries...", _SAVE_TO_MANAGE_LIBRARIES_DATA)

        self._restore_save_to_combo_after_repopulate()

    def _first_real_save_to_index(self) -> int:
        """Index of first library row (skip separator / sentinel items)."""
        for i in range(self.save_to_combo.count()):
            data = self.save_to_combo.itemData(i)
            if isinstance(data, str) and data and data not in _SAVE_TO_SENTINEL_DATA:
                return i
        return -1

    def _restore_save_to_combo_selection(self) -> None:
        """Select last known library path, or the first real library row."""
        if self._save_to_last_path:
            idx = self.save_to_combo.findData(self._save_to_last_path)
            if idx >= 0:
                self.save_to_combo.setCurrentIndex(idx)
                return
        first = self._first_real_save_to_index()
        if first >= 0:
            self.save_to_combo.setCurrentIndex(first)
            d = self.save_to_combo.itemData(first)
            if isinstance(d, str) and d and d not in _SAVE_TO_SENTINEL_DATA:
                self._save_to_last_path = d

    def _restore_save_to_combo_after_repopulate(self) -> None:
        """After rebuilding the combo, re-select the last library if still present."""
        self._restore_save_to_combo_selection()

    def _on_save_to_activated(self, index: int) -> None:
        """Handle user picking a Save To row (sentinel rows open flows, not a save target)."""
        data = self.save_to_combo.itemData(index)
        if data == _SAVE_TO_CREATE_NEW_DATA:
            self._create_new_library()
        elif data == _SAVE_TO_MANAGE_LIBRARIES_DATA:
            self._open_library_preferences()
        elif isinstance(data, str) and data and data not in _SAVE_TO_SENTINEL_DATA:
            self._save_to_last_path = data

    def _create_new_library(self) -> None:
        """Pick/create a folder and register it as a library via LibraryService."""
        if self._library_service is None:
            QtWidgets.QMessageBox.information(
                self,
                "Create New Library",
                "Creating a library from here requires the application library service. "
                "Use Manage Libraries... to open Preferences and add library paths.",
            )
            self._restore_save_to_combo_selection()
            return

        start_dir = str(Path.home())
        if self._save_to_last_path:
            parent = Path(self._save_to_last_path).parent
            if parent.is_dir():
                start_dir = str(parent)

        path = _pick_existing_directory(self, "Create New Library", start_dir)
        if not path:
            self._restore_save_to_combo_selection()
            return

        lib = self._library_service.create_library(Path(path))
        if lib is not None:
            self._save_to_last_path = str(lib.path)
        self._populate_save_to_combo()
        if lib is None:
            self._restore_save_to_combo_selection()

    def _open_library_preferences(self) -> None:
        """Open Preferences (Library page) to add or manage component libraries."""
        from .settings_dialog import SettingsDialog

        dialog = SettingsDialog(
            self.storage.settings_service, self, library_service=self._library_service
        )
        dialog.exec()
        self._populate_save_to_combo()

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

        # Save-to library selector
        self.save_to_combo = QtWidgets.QComboBox()
        self.save_to_combo.setToolTip("Library directory where the component will be saved")
        self._populate_save_to_combo()
        self.save_to_combo.activated.connect(self._on_save_to_activated)
        info_form.addRow("Save To", self.save_to_combo)

        # OBJECT HEIGHT (mm) -> physical size reference for calibration
        self.object_height_mm = SmartDoubleSpinBox()
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

        # Reset editing context
        self._original_name = None
        self._component_source = None
        self._step_file_path = None

        # Status message
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage("Ready. Load an image and add interfaces to begin.")

    # ---------- Canvas/Interface Synchronization ----------

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

    def _import_step(self):
        """Import a STEP file as the component image via 3-D preview."""
        from ...cad.step_preview_dialog import StepPreviewDialog
        from ...cad.step_renderer import (
            is_cad_available,
            load_step_mesh,
            missing_dependency_message,
        )

        if not is_cad_available():
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Dependencies",
                missing_dependency_message()
                or "cadquery/OCP is required for STEP import.",
            )
            return

        path, _ = _pick_open_file(
            self,
            "Import STEP File",
            "",
            "STEP Files (*.step *.stp);;All Files (*)",
        )
        if not path:
            return

        result = load_step_mesh(path)
        if result is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Import Failed",
                f"Could not load or tessellate:\n{path}",
            )
            return

        vertices, faces, face_colors = result
        dlg = StepPreviewDialog(
            vertices,
            faces,
            face_colors=face_colors,
            parent=self,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        if dlg.result_pixmap and not dlg.result_pixmap.isNull():
            self._set_image(dlg.result_pixmap, path)
            self._step_file_path = path
            if dlg.result_height_mm > 0:
                self.object_height_mm.setValue(dlg.result_height_mm)
            status_bar = self.statusBar()
            if status_bar is not None:
                status_bar.showMessage(
                    f"Imported STEP projection from {Path(path).name}", 5000
                )

    def _load_component_record(self, component: ComponentRecord):
        """Load a ComponentRecord into the editor."""
        # Clear existing
        self.canvas.clear_points()

        # Set component properties
        self._set_name_edit_text(component.name)
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

    def _on_update_canvas_instances(self):
        """Push the current editor definition to all matching items on the main canvas."""
        parent = self._main_window
        if parent is None or not hasattr(parent, "update_canvas_instances_from_component_editor"):
            QtWidgets.QMessageBox.information(
                self,
                "Update Canvas Instances",
                (
                    "Open the component editor from the main Optiverse window "
                    "to update placed components."
                ),
            )
            return
        parent.update_canvas_instances_from_component_editor(self)

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
            step_file_path=self._step_file_path or "",
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
        """Refresh library list widget, loading from all known libraries."""
        from ...objects.definitions_loader import load_component_dicts_from_multiple

        self.libList.clear()

        # Collect component dicts from every library root
        if self._library_service is not None:
            roots = [
                lib.path for lib in self._library_service.get_all()
                if lib.source_type != "builtin" and lib.exists and lib.enabled
            ]
        else:
            roots = [self.storage.get_library_root()]

        all_rows = load_component_dicts_from_multiple([str(p) for p in roots])

        for row in all_rows:
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

            if rec.interfaces and len(rec.interfaces) > 0:
                if len(rec.interfaces) > 1:
                    type_label = f"Multi-element ({len(rec.interfaces)} interfaces)"
                else:
                    element_type = rec.interfaces[0].element_type.replace("_", " ").title()
                    type_label = element_type
            else:
                type_label = "Unknown"

            it = QtWidgets.QListWidgetItem(icon, f"{name}\n({type_label})")
            it.setData(QtCore.Qt.ItemDataRole.UserRole, row)
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

        # Track editing context for save guards
        self._original_name = rec.name
        self._component_source = data.get("_source")

        # Restore attached STEP file path
        self._step_file_path = rec.step_file_path or None

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
        self._set_name_edit_text(rec.name)

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

    # ---------- Save Guards ----------

    def _get_all_component_names(self) -> set[str]:
        """Collect all known component names (builtin + all user libraries)."""
        from ...objects.component_registry import ComponentRegistry
        from ...objects.definitions_loader import load_component_dicts_from_multiple

        names: set[str] = set()
        for rec in ComponentRegistry.get_standard_components():
            if name := rec.get("name", ""):
                names.add(name)

        if self._library_service is not None:
            custom_roots = [
                lib.path for lib in self._library_service.get_all()
                if lib.source_type != "builtin" and lib.exists and lib.enabled
            ]
        else:
            from ...platform.paths import get_all_custom_library_roots

            custom_roots = get_all_custom_library_roots()

        for rec in load_component_dicts_from_multiple([str(p) for p in custom_roots]):
            if name := rec.get("name", ""):
                names.add(name)
        return names

    def _get_builtin_names(self) -> set[str]:
        """Return the set of standard (builtin) component names."""
        from ...objects.component_registry import ComponentRegistry

        return {r.get("name", "") for r in ComponentRegistry.get_standard_components()} - {""}

    def _prompt_for_unique_name(
        self, suggestion: str, all_names: set[str], *, allow_name: str | None = None
    ) -> str | None:
        """Show an input dialog that loops until the user provides a unique name or cancels.

        Args:
            suggestion: Pre-filled name suggestion.
            all_names: Set of all existing component names.
            allow_name: Optional name that is allowed even if it appears in *all_names*
                        (used when replacing an existing component).

        Returns:
            A unique name string, or ``None`` if the user cancelled.
        """
        builtin_names = self._get_builtin_names()
        current = suggestion
        while True:
            name, ok = QtWidgets.QInputDialog.getText(
                self,
                "Component Name",
                "Enter a unique component name:",
                QtWidgets.QLineEdit.EchoMode.Normal,
                current,
            )
            if not ok or not name:
                return None
            name = name.strip()
            if not name:
                QtWidgets.QMessageBox.warning(self, "Invalid Name", "Name cannot be empty.")
                continue
            if name in builtin_names:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Reserved Name",
                    f"'{name}' is a standard component name and cannot be overwritten.\n"
                    "Please choose a different name.",
                )
                current = name
                continue
            if name in all_names and name != allow_name:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Name Already Exists",
                    f"A component named '{name}' already exists.\n"
                    "Please choose a different name.",
                )
                current = name
                continue
            return name

    def save_component(self) -> bool:
        """Save component to library with name-conflict and builtin guards.

        Returns:
            True if save was successful, False otherwise.
        """
        if not self._library_io:
            return False

        current_name = self.name_edit.text().strip()
        if not current_name:
            QtWidgets.QMessageBox.warning(self, "Missing name", "Please enter a component name.")
            return False

        builtin_names = self._get_builtin_names()
        all_names = self._get_all_component_names()

        # --- Guard 1: builtin component ---
        if self._component_source == "builtin" or current_name in builtin_names:
            QtWidgets.QMessageBox.information(
                self,
                "Standard Component",
                f"'{current_name}' is a standard component and cannot be overwritten.\n\n"
                "Your changes will be saved as a new component in your user library.\n"
                "Please choose a different name.",
            )
            new_name = self._prompt_for_unique_name(f"{current_name} (Custom)", all_names)
            if not new_name:
                return False
            self._set_name_edit_text(new_name)

        # --- Guard 2: existing user component with same name ---
        elif (
            self._original_name is not None
            and current_name == self._original_name
            and self._component_source == "user"
        ):
            msg = QtWidgets.QMessageBox(self)
            msg.setWindowTitle("Replace or Copy?")
            msg.setText(
                f"Do you want to replace the existing component '{current_name}'\n"
                "or save it as a new copy with a different name?"
            )
            replace_btn = msg.addButton("Replace", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            copy_btn = msg.addButton("Save as Copy", QtWidgets.QMessageBox.ButtonRole.ActionRole)
            msg.addButton(QtWidgets.QMessageBox.StandardButton.Cancel)
            msg.setDefaultButton(replace_btn)
            msg.exec()

            clicked = msg.clickedButton()
            if clicked == copy_btn:
                new_name = self._prompt_for_unique_name(f"{current_name} (Copy)", all_names)
                if not new_name:
                    return False
                self._set_name_edit_text(new_name)
            elif clicked != replace_btn:
                return False
            # Replace: fall through to save with same name

        # --- Guard 3: name changed or new component — uniqueness check ---
        elif current_name in all_names and current_name != self._original_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Name Already Exists",
                f"A component named '{current_name}' already exists.\n"
                "Please choose a different name.",
            )
            new_name = self._prompt_for_unique_name(current_name, all_names)
            if not new_name:
                return False
            self._set_name_edit_text(new_name)

        # --- Perform the actual save (builds record from UI, writes to disk) ---
        # Point StorageService at the library selected in "Save To" dropdown
        selected_path = self.save_to_combo.currentData()
        if isinstance(selected_path, str) and selected_path not in _SAVE_TO_SENTINEL_DATA:
            target_storage = StorageService(
                library_path=selected_path,
                settings_service=self.storage.settings_service,
            )
            self._library_io.storage = target_storage

        if self._library_io.save_component():
            saved_name = self.name_edit.text().strip()
            self._original_name = saved_name
            self._component_source = "user"
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

    def closeEvent(self, event: QtGui.QCloseEvent | None) -> None:  # type: ignore[override]
        """Handle window close event, prompting to save unsaved changes."""
        if not event:
            return
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
