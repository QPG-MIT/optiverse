"""
Tool mode controller for managing editor tool modes.

Extracts tool mode toggle logic from MainWindow.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.component_types import ComponentType
from ...core.editor_state import EditorState

if TYPE_CHECKING:
    from ..views.tool_handlers import PathMeasureToolHandler
    from ..views.placement_handler import PlacementHandler


class ToolModeController(QtCore.QObject):
    """
    Controller for editor tool modes (inspect, path measure, placement).
    
    Manages mutual exclusion between modes and UI state updates.
    """
    
    # Signals for UI updates
    inspectModeChanged = QtCore.pyqtSignal(bool)
    pathMeasureModeChanged = QtCore.pyqtSignal(bool)
    placementModeChanged = QtCore.pyqtSignal(str, bool)  # (component_type, is_active)
    rulerPlacementChanged = QtCore.pyqtSignal(bool)
    
    def __init__(
        self,
        editor_state: EditorState,
        view: QtWidgets.QGraphicsView,
        path_measure_handler: "PathMeasureToolHandler",
        placement_handler: "PlacementHandler",
        parent: Optional[QtCore.QObject] = None,
    ):
        super().__init__(parent)
        
        self._editor_state = editor_state
        self._view = view
        self._path_measure_handler = path_measure_handler
        self._placement_handler = placement_handler
        
        # Action references (set by MainWindow after initialization)
        self._action_inspect: Optional[QtWidgets.QAction] = None
        self._action_measure_path: Optional[QtWidgets.QAction] = None
        self._placement_actions: Dict[ComponentType, QtWidgets.QAction] = {}
    
    def set_action_inspect(self, action: QtWidgets.QAction):
        """Set the inspect action for unchecking."""
        self._action_inspect = action
    
    def set_action_measure_path(self, action: QtWidgets.QAction):
        """Set the measure path action for unchecking."""
        self._action_measure_path = action
    
    def set_placement_actions(self, actions: Dict[ComponentType, QtWidgets.QAction]):
        """Set placement actions for unchecking."""
        self._placement_actions = actions
    
    def toggle_inspect(self, on: bool):
        """Toggle inspect tool mode."""
        if on:
            self._cancel_other_modes("inspect")
            self._editor_state.enter_inspect()
            self._view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            QtWidgets.QToolTip.showText(
                QtGui.QCursor.pos(), 
                "Click on a ray to view its properties"
            )
        else:
            self._editor_state.enter_default()
            self._view.unsetCursor()
        
        self.inspectModeChanged.emit(on)
    
    def toggle_path_measure(self, on: bool):
        """Toggle path measure tool mode."""
        if on:
            self._cancel_other_modes("path_measure")
            self._editor_state.enter_path_measure()
            self._path_measure_handler.activate()
            self._view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            QtWidgets.QToolTip.showText(
                QtGui.QCursor.pos(),
                "Click on a ray to set start point.\n\n"
                "Tip: At beam splitters, transmitted and reflected are separate rays.\n"
                "Create one measurement for each path."
            )
        else:
            self._editor_state.enter_default()
            self._path_measure_handler.deactivate()
            self._view.unsetCursor()
        
        self.pathMeasureModeChanged.emit(on)
    
    def toggle_placement(self, component_type: str, on: bool):
        """Toggle component placement mode."""
        if on:
            self._cancel_other_modes("placement", except_placement_type=component_type)
            self._editor_state.enter_placement(component_type)
            self._placement_handler.activate(component_type)
        else:
            self.cancel_placement()
        
        self.placementModeChanged.emit(component_type, on)
    
    def cancel_placement(self, except_type: Optional[str] = None):
        """Cancel placement mode and clean up."""
        prev_type = (
            self._placement_handler.component_type 
            if self._placement_handler.is_active 
            else self._editor_state.placement_type
        )
        
        self._placement_handler.deactivate()
        self._editor_state.enter_default()
        
        # Uncheck toolbar buttons (except the one we're toggling to)
        if prev_type != except_type:
            if isinstance(prev_type, str):
                try:
                    prev_type = ComponentType(prev_type)
                except ValueError:
                    prev_type = None
            if prev_type in self._placement_actions:
                self._placement_actions[prev_type].setChecked(False)
    
    def finish_ruler_placement(self):
        """Finish ruler placement mode."""
        self._editor_state.exit_ruler_placement()
        self._view.unsetCursor()
        self.rulerPlacementChanged.emit(False)
    
    def _cancel_other_modes(
        self, 
        active_mode: str, 
        except_placement_type: Optional[str] = None
    ):
        """Cancel all modes except the specified one."""
        if active_mode != "inspect" and self._editor_state.is_inspect:
            if self._action_inspect:
                self._action_inspect.setChecked(False)
        
        if active_mode != "path_measure" and self._editor_state.is_path_measure:
            if self._action_measure_path:
                self._action_measure_path.setChecked(False)
        
        if active_mode != "placement" and self._editor_state.is_placement:
            self.cancel_placement(except_type=except_placement_type)
        
        if self._editor_state.is_ruler_placement:
            self.finish_ruler_placement()

