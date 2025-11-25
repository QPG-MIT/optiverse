"""
Scene Event Handler - Routes scene events to appropriate handlers.

Extracts eventFilter and keyPressEvent logic from MainWindow.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable

from PyQt6 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from ...core.editor_state import EditorState
    from ..controllers.item_drag_handler import ItemDragHandler
    from .placement_handler import PlacementHandler
    from .tool_handlers import InspectToolHandler, PathMeasureToolHandler, AngleMeasureToolHandler
    from .ruler_placement_handler import RulerPlacementHandler


class SceneEventHandler(QtCore.QObject):
    """
    Handles scene events and routes them to appropriate handlers.
    
    This consolidates all the eventFilter and keyPressEvent logic
    that was previously in MainWindow.
    """
    
    def __init__(
        self,
        editor_state: "EditorState",
        placement_handler: "PlacementHandler",
        inspect_handler: "InspectToolHandler",
        path_measure_handler: "PathMeasureToolHandler",
        angle_measure_handler: "AngleMeasureToolHandler",
        ruler_handler: "RulerPlacementHandler",
        drag_handler: "ItemDragHandler",
        cancel_placement_mode: Callable[[], None],
        get_inspect_action: Callable[[], QtWidgets.QAction],
        get_path_measure_action: Callable[[], QtWidgets.QAction],
        get_angle_measure_action: Callable[[], QtWidgets.QAction],
        parent: Optional[QtCore.QObject] = None,
    ):
        """
        Initialize the scene event handler.
        
        Args:
            editor_state: The editor state manager
            placement_handler: Handler for component placement
            inspect_handler: Handler for inspect tool
            path_measure_handler: Handler for path measure tool
            angle_measure_handler: Handler for angle measure tool
            ruler_handler: Handler for ruler placement
            drag_handler: Handler for item dragging
            cancel_placement_mode: Callback to cancel placement mode
            get_inspect_action: Callable to get inspect action (for unchecking)
            get_path_measure_action: Callable to get path measure action
            get_angle_measure_action: Callable to get angle measure action
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self._editor_state = editor_state
        self._placement_handler = placement_handler
        self._inspect_handler = inspect_handler
        self._path_measure_handler = path_measure_handler
        self._angle_measure_handler = angle_measure_handler
        self._ruler_handler = ruler_handler
        self._drag_handler = drag_handler
        self._cancel_placement_mode = cancel_placement_mode
        self._get_inspect_action = get_inspect_action
        self._get_path_measure_action = get_path_measure_action
        self._get_angle_measure_action = get_angle_measure_action
    
    def handle_event(self, obj: QtCore.QObject, ev: QtCore.QEvent) -> Optional[bool]:
        """
        Handle scene events and route to appropriate handlers.
        
        Args:
            obj: The object that received the event
            ev: The event
            
        Returns:
            True if event was consumed, False to continue processing,
            None to defer to parent eventFilter
        """
        et = ev.type()
        
        # --- Component placement mode ---
        if self._placement_handler.is_active:
            if et == QtCore.QEvent.Type.GraphicsSceneMouseMove:
                mev = ev  # QGraphicsSceneMouseEvent
                scene_pt = mev.scenePos()
                self._placement_handler.handle_mouse_move(scene_pt)
                return True
            
            elif et == QtCore.QEvent.Type.GraphicsSceneMousePress:
                mev = ev  # QGraphicsSceneMouseEvent
                scene_pt = mev.scenePos()
                
                if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                    self._placement_handler.handle_click(scene_pt, mev.button())
                    return True
                
                elif mev.button() == QtCore.Qt.MouseButton.RightButton:
                    self._cancel_placement_mode()
                    return True
        
        # --- Inspect tool ---
        if self._editor_state.is_inspect and et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            mev = ev  # QGraphicsSceneMouseEvent
            if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                scene_pt = mev.scenePos()
                self._inspect_handler.handle_click(scene_pt)
                return True
        
        # --- Path Measure tool ---
        if self._editor_state.is_path_measure and et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            mev = ev  # QGraphicsSceneMouseEvent
            if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                scene_pt = mev.scenePos()
                self._path_measure_handler.handle_click(scene_pt)
                return True
        
        # --- Angle Measure tool ---
        if self._editor_state.is_angle_measure:
            if et == QtCore.QEvent.Type.GraphicsSceneMousePress:
                mev = ev  # QGraphicsSceneMouseEvent
                if mev.button() == QtCore.Qt.MouseButton.LeftButton:
                    scene_pt = mev.scenePos()
                    self._angle_measure_handler.handle_click(scene_pt)
                    return True
            elif et == QtCore.QEvent.Type.GraphicsSceneMouseMove:
                mev = ev  # QGraphicsSceneMouseEvent
                scene_pt = mev.scenePos()
                self._angle_measure_handler.handle_mouse_move(scene_pt)
                return True
        
        # --- Ruler multi-segment placement ---
        if self._ruler_handler.is_active:
            if et == QtCore.QEvent.Type.GraphicsSceneMousePress:
                mev = ev  # QGraphicsSceneMouseEvent
                if self._ruler_handler.handle_mouse_press(mev.scenePos(), mev.button()):
                    return True
            elif et == QtCore.QEvent.Type.GraphicsSceneMouseMove:
                mev = ev  # QGraphicsSceneMouseEvent
                if self._ruler_handler.handle_mouse_move(mev.scenePos()):
                    return True
        
        # --- Track item positions and rotations on mouse press ---
        if et == QtCore.QEvent.Type.GraphicsSceneMousePress:
            self._drag_handler.handle_mouse_press(ev)
        
        # --- Snap to grid and create move/rotate commands on mouse release ---
        if et == QtCore.QEvent.Type.GraphicsSceneMouseRelease:
            self._drag_handler.handle_mouse_release()
        
        return None  # Defer to parent
    
    def handle_key_press(self, ev: QtGui.QKeyEvent) -> bool:
        """
        Handle key press events for mode cancellation and special keys.
        
        Args:
            ev: The key event
            
        Returns:
            True if the event was consumed, False otherwise
        """
        # Check if Escape is pressed and any special mode is active
        if ev.key() == QtCore.Qt.Key.Key_Escape:
            if self._editor_state.is_placement:
                self._cancel_placement_mode()
                return True
            
            elif self._ruler_handler.is_active:
                self._ruler_handler.handle_escape()
                return True
            
            elif self._editor_state.is_inspect:
                self._get_inspect_action().setChecked(False)
                return True
            
            elif self._editor_state.is_path_measure:
                self._get_path_measure_action().setChecked(False)
                return True
            
            elif self._editor_state.is_angle_measure:
                self._get_angle_measure_action().setChecked(False)
                return True
        
        # Handle 'A' key for adding bend during ruler placement (only if no modifiers)
        if (ev.key() == QtCore.Qt.Key.Key_A and 
            self._ruler_handler.is_active and
            ev.modifiers() == QtCore.Qt.KeyboardModifier.NoModifier):
            if self._ruler_handler.handle_add_bend():
                return True
        
        return False

