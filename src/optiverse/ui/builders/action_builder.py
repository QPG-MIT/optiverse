"""
Action Builder - Constructs actions, menus, and toolbars for MainWindow.

This module extracts the UI building logic from MainWindow into a dedicated
builder class for better separation of concerns.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.component_types import ComponentType

if TYPE_CHECKING:
    from ..views.main_window import MainWindow


def _get_icon_path(icon_name: str, dark_mode: bool) -> str:
    """Get path to a themed toolbar icon."""
    icons_dir = Path(__file__).parent.parent / "icons"
    theme = "dark" if dark_mode else "light"
    return str(icons_dir / theme / icon_name)


# Toolbar stylesheet for checked tool buttons
_TOOLBAR_STYLESHEET = """
    QToolButton {
        padding: 2px;
        border: 2px solid transparent;
        border-radius: 4px;
        color: palette(window-text);
    }
    QToolButton:checked {
        background-color: rgba(100, 150, 255, 100);
        border: 2px solid rgba(100, 150, 255, 180);
        border-radius: 4px;
        color: palette(window-text);
    }
    QToolButton:checked:hover {
        background-color: rgba(100, 150, 255, 120);
        border: 2px solid rgba(100, 150, 255, 200);
        color: palette(window-text);
    }
"""


class ActionBuilder:
    """
    Builds actions, menus, and toolbars for MainWindow.

    This class encapsulates all the UI construction logic that was previously
    in MainWindow._build_actions(), _build_toolbar(), and _build_menubar().

    The builder receives a MainWindow instance and attaches the built actions
    and menus to it.
    """

    def __init__(self, window: MainWindow):
        """
        Initialize the action builder.

        Args:
            window: The MainWindow instance to build actions for
        """
        self.window = window
        # Mapping of actions to their icon filenames for theme switching
        self._toolbar_icon_map: list[tuple[QtGui.QAction, str]] = []

    def build_all(self) -> None:
        """Build all actions, toolbar, and menubar."""
        self.build_actions()
        self.build_toolbar()
        self.build_menubar()
        self.register_shortcuts()
        self._register_tool_controller_actions()

    def build_actions(self) -> None:
        """Build all menu actions and attach them to the window."""
        w = self.window

        # --- File Actions ---
        w.act_open = QtGui.QAction("Open Assembly…", w)
        w.act_open.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        w.act_open.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_open.triggered.connect(w.open_assembly)

        w.act_save = QtGui.QAction("Save", w)
        w.act_save.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        w.act_save.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_save.triggered.connect(w.save_assembly)

        w.act_save_as = QtGui.QAction("Save As…", w)
        w.act_save_as.setShortcut(QtGui.QKeySequence("Ctrl+Shift+S"))
        w.act_save_as.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_save_as.triggered.connect(w.save_assembly_as)

        # --- Edit Actions ---
        w.act_undo = QtGui.QAction("Undo", w)
        w.act_undo.setShortcut(QtGui.QKeySequence("Ctrl+Z"))
        w.act_undo.setShortcutContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        w.act_undo.triggered.connect(w._do_undo)
        w.act_undo.setEnabled(False)

        w.act_redo = QtGui.QAction("Redo", w)
        w.act_redo.setShortcut(QtGui.QKeySequence("Ctrl+Y"))
        w.act_redo.setShortcutContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
        w.act_redo.triggered.connect(w._do_redo)
        w.act_redo.setEnabled(False)

        w.act_delete = QtGui.QAction("Delete", w)
        w.act_delete.setShortcuts(
            [QtGui.QKeySequence.StandardKey.Delete, QtGui.QKeySequence(QtCore.Qt.Key.Key_Backspace)]
        )
        w.act_delete.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_delete.triggered.connect(w.delete_selected)

        w.act_copy = QtGui.QAction("Copy", w)
        w.act_copy.setShortcut(QtGui.QKeySequence("Ctrl+C"))
        w.act_copy.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_copy.triggered.connect(w.copy_selected)

        w.act_paste = QtGui.QAction("Paste", w)
        w.act_paste.setShortcut(QtGui.QKeySequence("Ctrl+V"))
        w.act_paste.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_paste.triggered.connect(w.paste_items)
        w.act_paste.setEnabled(False)

        # --- Preferences ---
        w.act_preferences = QtGui.QAction("Preferences...", w)
        w.act_preferences.setShortcut(QtGui.QKeySequence.StandardKey.Preferences)
        w.act_preferences.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_preferences.triggered.connect(w.open_preferences)
        w.act_preferences.setMenuRole(QtGui.QAction.MenuRole.PreferencesRole)

        # Connect undo stack signals
        w.undo_stack.canUndoChanged.connect(w.act_undo.setEnabled)
        w.undo_stack.canRedoChanged.connect(w.act_redo.setEnabled)

        # --- Insert Actions (Placement Mode) ---
        w.act_add_source = QtGui.QAction("Source", w, checkable=True)  # type: ignore[call-overload]
        w.act_add_source.toggled.connect(partial(w._toggle_placement_mode, ComponentType.SOURCE))

        w.act_add_lens = QtGui.QAction("Lens", w, checkable=True)  # type: ignore[call-overload]
        w.act_add_lens.toggled.connect(partial(w._toggle_placement_mode, ComponentType.LENS))

        w.act_add_mirror = QtGui.QAction("Mirror", w, checkable=True)  # type: ignore[call-overload]
        w.act_add_mirror.toggled.connect(partial(w._toggle_placement_mode, ComponentType.MIRROR))

        w.act_add_bs = QtGui.QAction("Beamsplitter", w, checkable=True)  # type: ignore[call-overload]
        w.act_add_bs.toggled.connect(partial(w._toggle_placement_mode, ComponentType.BEAMSPLITTER))

        w.act_add_ruler = QtGui.QAction("Ruler", w, checkable=True)  # type: ignore[call-overload]
        w.act_add_ruler.setChecked(False)
        w.act_add_ruler.setShortcut("R")
        w.act_add_ruler.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_add_ruler.toggled.connect(w._toggle_ruler_placement)

        w.act_add_text = QtGui.QAction("Text", w, checkable=True)  # type: ignore[call-overload]
        w.act_add_text.toggled.connect(partial(w._toggle_placement_mode, ComponentType.TEXT))

        w.act_add_rectangle = QtGui.QAction("Rectangle", w, checkable=True)  # type: ignore[call-overload]
        w.act_add_rectangle.toggled.connect(
            partial(w._toggle_placement_mode, ComponentType.RECTANGLE)
        )

        # --- Tool Actions ---
        w.act_inspect = QtGui.QAction("Inspect", w, checkable=True)  # type: ignore[call-overload]
        w.act_inspect.setChecked(False)
        w.act_inspect.toggled.connect(w._toggle_inspect)

        w.act_measure_path = QtGui.QAction("Path Measure", w, checkable=True)  # type: ignore[call-overload]
        w.act_measure_path.setChecked(False)
        w.act_measure_path.toggled.connect(w._toggle_path_measure)

        w.act_measure_angle = QtGui.QAction("Angle Measure", w, checkable=True)  # type: ignore[call-overload]
        w.act_measure_angle.setChecked(False)
        w.act_measure_angle.toggled.connect(w._toggle_angle_measure)

        # --- View Actions ---
        w.act_zoom_in = QtGui.QAction("Zoom In", w)
        w.act_zoom_in.setShortcut(QtGui.QKeySequence.StandardKey.ZoomIn)
        w.act_zoom_in.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_zoom_in.triggered.connect(w._zoom_in)

        w.act_zoom_out = QtGui.QAction("Zoom Out", w)
        w.act_zoom_out.setShortcut(QtGui.QKeySequence.StandardKey.ZoomOut)
        w.act_zoom_out.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_zoom_out.triggered.connect(w._zoom_out)

        w.act_fit = QtGui.QAction("Fit Scene", w)
        w.act_fit.setShortcut("Ctrl+0")
        w.act_fit.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_fit.triggered.connect(w._fit_scene)

        w.act_recenter = QtGui.QAction("Recenter View", w)
        w.act_recenter.setShortcut("Ctrl+Shift+0")
        w.act_recenter.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_recenter.triggered.connect(w._recenter_view)

        # --- Checkable View Options ---
        w.act_autotrace = QtGui.QAction("Auto-trace", w, checkable=True)  # type: ignore[call-overload]
        w.act_autotrace.setChecked(True)
        w.act_autotrace.toggled.connect(w._toggle_autotrace)

        w.act_snap = QtGui.QAction("Snap to mm grid", w, checkable=True)  # type: ignore[call-overload]
        w.act_snap.setChecked(False)
        w.act_snap.toggled.connect(w._toggle_snap)

        w.act_magnetic_snap = QtGui.QAction("Magnetic snap", w, checkable=True)  # type: ignore[call-overload]
        w.act_magnetic_snap.setChecked(w.magnetic_snap)
        w.act_magnetic_snap.toggled.connect(w._toggle_magnetic_snap)

        w.act_dark_mode = QtGui.QAction("Dark mode", w, checkable=True)  # type: ignore[call-overload]
        w.act_dark_mode.setChecked(w.view.is_dark_mode())
        w.act_dark_mode.toggled.connect(w._toggle_dark_mode)

        # --- Ray Width Submenu ---
        w.menu_raywidth = QtWidgets.QMenu("Ray width", w)
        w._raywidth_group = QtGui.QActionGroup(w)
        w._raywidth_group.setExclusive(True)
        for v in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]:
            a = w.menu_raywidth.addAction(f"{v:.1f} px")
            if a is not None:
                a.setCheckable(True)
                if abs(v - w._ray_width_px) < 1e-9:
                    a.setChecked(True)
                a.triggered.connect(partial(w._set_ray_width, v))
                w._raywidth_group.addAction(a)
        w.menu_raywidth.addSeparator()
        a_custom = w.menu_raywidth.addAction("Custom…")
        if a_custom is not None:
            a_custom.triggered.connect(w._choose_ray_width)

        # --- Tools Menu Actions ---
        w.act_retrace = QtGui.QAction("Retrace", w)
        w.act_retrace.setShortcut("Space")
        w.act_retrace.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_retrace.triggered.connect(w.retrace)

        w.act_clear = QtGui.QAction("Clear Rays", w)
        w.act_clear.triggered.connect(w.clear_rays)

        w.act_editor = QtGui.QAction("Component Editor…", w)
        w.act_editor.setShortcut("Ctrl+E")
        w.act_editor.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_editor.triggered.connect(w.open_component_editor)

        w.act_reload = QtGui.QAction("Reload Library", w)
        w.act_reload.triggered.connect(w.populate_library)

        w.act_open_library_folder = QtGui.QAction("Open User Library Folder…", w)
        w.act_open_library_folder.triggered.connect(w.open_user_library_folder)

        w.act_import_library = QtGui.QAction("Import Component Library…", w)
        w.act_import_library.triggered.connect(w.import_component_library)

        w.act_show_log = QtGui.QAction("Show Log Window...", w)
        w.act_show_log.setShortcut("Ctrl+L")
        w.act_show_log.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_show_log.triggered.connect(w.show_log_window)

        # --- Collaboration Actions ---
        w.act_collaborate = QtGui.QAction("Connect/Host Session…", w)
        w.act_collaborate.setShortcut("Ctrl+Shift+C")
        w.act_collaborate.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
        w.act_collaborate.triggered.connect(w.open_collaboration_dialog)

        w.act_disconnect = QtGui.QAction("Disconnect", w)
        w.act_disconnect.setEnabled(False)
        w.act_disconnect.triggered.connect(w.disconnect_collaboration)

    def build_toolbar(self) -> None:
        """Build the component toolbar with icons."""
        w = self.window
        dark_mode = w.view.is_dark_mode()

        toolbar = QtWidgets.QToolBar("Components")
        toolbar.setObjectName("component_toolbar")
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        toolbar.setIconSize(QtCore.QSize(32, 32))
        w.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, toolbar)
        toolbar.setStyleSheet(_TOOLBAR_STYLESHEET)

        # Create exclusive action group for tool buttons
        # ExclusiveOptional allows unchecking all (clicking checked action unchecks it)
        w._tool_action_group = QtGui.QActionGroup(w)
        w._tool_action_group.setExclusive(True)
        w._tool_action_group.setExclusionPolicy(
            QtGui.QActionGroup.ExclusionPolicy.ExclusiveOptional
        )

        # Helper to set icon and register for theme switching
        def add_toolbar_action(action: QtGui.QAction, icon_name: str) -> None:
            action.setIcon(QtGui.QIcon(_get_icon_path(icon_name, dark_mode)))
            toolbar.addAction(action)
            w._tool_action_group.addAction(action)
            self._toolbar_icon_map.append((action, icon_name))

        # Source button
        add_toolbar_action(w.act_add_source, "source.png")

        # Lens button
        add_toolbar_action(w.act_add_lens, "lens.png")

        # Mirror button
        add_toolbar_action(w.act_add_mirror, "mirror.png")

        # Beamsplitter button
        add_toolbar_action(w.act_add_bs, "beamsplitter.png")

        toolbar.addSeparator()

        # --- Measurement Tools ---
        # Ruler button
        add_toolbar_action(w.act_add_ruler, "ruler.png")

        # Path Measure tool - HIDDEN: Feature is buggy, hiding UI but keeping code
        # add_toolbar_action(w.act_measure_path, "ruler.png")

        # Angle Measure tool
        add_toolbar_action(w.act_measure_angle, "angle_measure.png")

        toolbar.addSeparator()

        # --- Inspection & Annotation Tools ---
        # Inspect button
        add_toolbar_action(w.act_inspect, "inspect.png")

        # Text button
        add_toolbar_action(w.act_add_text, "text.png")

        # Rectangle button
        add_toolbar_action(w.act_add_rectangle, "rectangle.png")

    def refresh_toolbar_icons(self, dark_mode: bool) -> None:
        """Refresh all toolbar icons for the given theme.

        Args:
            dark_mode: If True, use dark mode (inverted) icons
        """
        for action, icon_name in self._toolbar_icon_map:
            action.setIcon(QtGui.QIcon(_get_icon_path(icon_name, dark_mode)))

    def build_menubar(self) -> None:
        """Build the menu bar."""
        w = self.window
        mb = w.menuBar()
        if mb is None:
            return

        # File menu
        mFile = mb.addMenu("&File")
        if mFile is None:
            return
        mFile.addAction(w.act_open)
        mFile.addAction(w.act_save)
        mFile.addAction(w.act_save_as)

        # Edit menu
        mEdit = mb.addMenu("&Edit")
        if mEdit is None:
            return
        mEdit.addAction(w.act_undo)
        mEdit.addAction(w.act_redo)
        mEdit.addSeparator()
        mEdit.addAction(w.act_copy)
        mEdit.addAction(w.act_paste)
        mEdit.addSeparator()
        mEdit.addAction(w.act_delete)
        mEdit.addSeparator()
        mEdit.addAction(w.act_preferences)

        # Insert menu
        mInsert = mb.addMenu("&Insert")
        if mInsert is None:
            return
        mInsert.addAction(w.act_add_source)
        mInsert.addAction(w.act_add_lens)
        mInsert.addAction(w.act_add_mirror)
        mInsert.addAction(w.act_add_bs)
        mInsert.addSeparator()
        mInsert.addAction(w.act_add_ruler)
        mInsert.addAction(w.act_add_text)
        mInsert.addAction(w.act_add_rectangle)

        # View menu
        mView = mb.addMenu("&View")
        if mView is None:
            return
        mView.addAction(w.libDock.toggleViewAction())
        mView.addSeparator()
        mView.addAction(w.act_zoom_in)
        mView.addAction(w.act_zoom_out)
        mView.addAction(w.act_fit)
        mView.addAction(w.act_recenter)
        mView.addSeparator()
        mView.addAction(w.act_autotrace)
        mView.addAction(w.act_snap)
        mView.addAction(w.act_magnetic_snap)
        mView.addSeparator()
        mView.addAction(w.act_dark_mode)
        mView.addSeparator()
        mView.addMenu(w.menu_raywidth)

        # Tools menu
        mTools = mb.addMenu("&Tools")
        if mTools is None:
            return
        mTools.addAction(w.act_retrace)
        mTools.addAction(w.act_clear)
        mTools.addSeparator()
        mTools.addAction(w.act_inspect)
        mTools.addAction(w.act_measure_path)
        mTools.addAction(w.act_measure_angle)
        mTools.addSeparator()
        mTools.addAction(w.act_editor)
        mTools.addAction(w.act_reload)
        mTools.addSeparator()
        mTools.addAction(w.act_open_library_folder)
        mTools.addAction(w.act_import_library)
        mTools.addSeparator()
        mTools.addAction(w.act_show_log)

        # Collaboration menu
        mCollab = mb.addMenu("&Collaboration")
        if mCollab is None:
            return
        mCollab.addAction(w.act_collaborate)
        mCollab.addAction(w.act_disconnect)

        # Add collaboration status to status bar
        w.collab_status_label = QtWidgets.QLabel("Not connected")
        status_bar = w.statusBar()
        if status_bar is not None:
            status_bar.addPermanentWidget(w.collab_status_label)

        # Connect collab controller status signal
        w.collab_controller.statusChanged.connect(w.collab_status_label.setText)

    def register_shortcuts(self) -> None:
        """Register actions with shortcuts to main window for global access."""
        w = self.window

        # File actions
        w.addAction(w.act_open)
        w.addAction(w.act_save)
        w.addAction(w.act_save_as)

        # Edit actions
        w.addAction(w.act_undo)
        w.addAction(w.act_redo)
        w.addAction(w.act_delete)
        w.addAction(w.act_copy)
        w.addAction(w.act_paste)

        # View actions
        w.addAction(w.act_zoom_in)
        w.addAction(w.act_zoom_out)
        w.addAction(w.act_fit)
        w.addAction(w.act_recenter)

        # Tools actions
        w.addAction(w.act_retrace)
        w.addAction(w.act_editor)
        w.addAction(w.act_show_log)

        # Collaboration actions
        w.addAction(w.act_collaborate)

    def _register_tool_controller_actions(self) -> None:
        """Register actions with ToolModeController for mutual exclusion."""
        w = self.window

        # Register inspect and path measure actions
        w.tool_controller.set_action_inspect(w.act_inspect)
        w.tool_controller.set_action_measure_path(w.act_measure_path)
        w.tool_controller.set_action_measure_angle(w.act_measure_angle)

        # Register placement actions
        w.tool_controller.set_placement_actions(
            {
                ComponentType.SOURCE: w.act_add_source,
                ComponentType.LENS: w.act_add_lens,
                ComponentType.MIRROR: w.act_add_mirror,
                ComponentType.BEAMSPLITTER: w.act_add_bs,
                ComponentType.TEXT: w.act_add_text,
                ComponentType.RECTANGLE: w.act_add_rectangle,
            }
        )

