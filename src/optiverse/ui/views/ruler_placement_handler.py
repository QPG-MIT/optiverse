"""
Ruler Placement Handler - Manages ruler placement mode.

Extracts ruler placement logic from MainWindow.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.undo_commands import AddItemCommand
from ...objects import RulerItem

if TYPE_CHECKING:
    from ...core.editor_state import EditorState
    from ...core.undo_stack import UndoStack


class RulerPlacementHandler:
    """
    Handler for ruler placement mode.

    Manages the two-click ruler placement workflow with multi-segment support.
    """

    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        view: QtWidgets.QGraphicsView,
        editor_state: "EditorState",
        undo_stack: "UndoStack",
        get_ruler_action: Callable[[], QtWidgets.QAction],
        finish_ruler_mode: Callable[[], None],
    ):
        """
        Initialize the ruler placement handler.

        Args:
            scene: The graphics scene
            view: The graphics view
            editor_state: The editor state manager
            undo_stack: The undo stack for commands
            get_ruler_action: Callable that returns the ruler action (for checking state)
            finish_ruler_mode: Callback to call when finishing ruler placement mode
        """
        self._scene = scene
        self._view = view
        self._editor_state = editor_state
        self._undo_stack = undo_stack
        self._get_ruler_action = get_ruler_action
        self._finish_ruler_mode = finish_ruler_mode
        self._prev_cursor: Optional[QtGui.QCursor] = None

    @property
    def is_active(self) -> bool:
        """Check if ruler placement mode is active."""
        return self._editor_state.is_ruler_placement

    def start(self, cancel_other_modes: Callable[[str], None]) -> None:
        """
        Enter ruler placement mode.

        Args:
            cancel_other_modes: Callback to cancel other modes
        """
        cancel_other_modes("ruler")

        self._editor_state.enter_ruler_placement()

        # Set the action as checked to show blue underlay (block signals to avoid recursion)
        action = self._get_ruler_action()
        if not action.isChecked():
            action.blockSignals(True)
            action.setChecked(True)
            action.blockSignals(False)

        self._prev_cursor = self._view.cursor()
        self._view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), "Click start point, then end point")

    def finish(self) -> None:
        """Exit ruler placement mode."""
        # Remove any ruler in progress from scene if it exists
        if self._editor_state.ruler_in_progress is not None:
            if self._editor_state.ruler_in_progress.scene():
                self._scene.removeItem(self._editor_state.ruler_in_progress)
            self._editor_state.ruler_in_progress = None

        self._finish_ruler_mode()

        if self._prev_cursor is not None:
            self._view.setCursor(self._prev_cursor)
            self._prev_cursor = None

        # Uncheck the action to remove blue underlay (block signals to avoid recursion)
        action = self._get_ruler_action()
        if action.isChecked():
            action.blockSignals(True)
            action.setChecked(False)
            action.blockSignals(False)

    def toggle(self, on: bool, cancel_other_modes: Callable[[str], None]) -> None:
        """
        Toggle ruler placement mode.

        Args:
            on: Whether to enable or disable the mode
            cancel_other_modes: Callback to cancel other modes
        """
        if on:
            if not self._editor_state.is_ruler_placement:
                self.start(cancel_other_modes)
        else:
            if self._editor_state.is_ruler_placement:
                self.finish()

    def handle_mouse_press(self, scene_pt: QtCore.QPointF, button: QtCore.Qt.MouseButton) -> bool:
        """
        Handle mouse press during ruler placement.

        Args:
            scene_pt: The scene position of the click
            button: The mouse button that was pressed

        Returns:
            True if the event was consumed, False otherwise
        """
        if not self.is_active:
            return False

        if button == QtCore.Qt.MouseButton.LeftButton:
            ruler_in_progress = self._editor_state.ruler_in_progress

            if ruler_in_progress is None:
                # First click: create new ruler with first point
                p1 = QtCore.QPointF(scene_pt)
                p2 = QtCore.QPointF(scene_pt)  # Temporary second point for preview
                ruler = RulerItem(p1, p2)
                ruler.setPos(0, 0)
                self._scene.addItem(ruler)  # Add temporarily for preview
                self._editor_state.ruler_in_progress = ruler
                return True
            else:
                # Subsequent click: finalize current segment and prepare for next
                item_pt = ruler_in_progress.mapFromScene(scene_pt)
                if ruler_in_progress.point_count() >= 2:
                    ruler_in_progress.finalize_segment(item_pt)
                return True

        elif button == QtCore.Qt.MouseButton.RightButton:
            ruler_in_progress = self._editor_state.ruler_in_progress

            if ruler_in_progress is None:
                # Cancel placement mode if no ruler started
                self.finish()
                return True
            else:
                # Finalize ruler at current mouse position (like pressing Escape)
                # This is more intuitive than adding a bend on right-click
                item_pt = ruler_in_progress.mapFromScene(scene_pt)
                if ruler_in_progress.point_count() >= 2:
                    # Update the last point to current position
                    ruler_in_progress.set_preview_point(item_pt)
                # Finalize the ruler (same as handle_escape)
                self.handle_escape()
                return True

        return False

    def handle_mouse_move(self, scene_pt: QtCore.QPointF) -> bool:
        """
        Handle mouse move during ruler placement (update preview).

        Args:
            scene_pt: The scene position of the mouse

        Returns:
            True if the event was consumed, False otherwise
        """
        if not self.is_active:
            return False

        ruler_in_progress = self._editor_state.ruler_in_progress
        if ruler_in_progress is not None:
            item_pt = ruler_in_progress.mapFromScene(scene_pt)
            if ruler_in_progress.point_count() >= 2:
                ruler_in_progress.set_preview_point(item_pt)
            return True

        return False

    def handle_escape(self) -> bool:
        """
        Handle escape key to finalize ruler placement.

        Returns:
            True if the event was consumed, False otherwise
        """
        if not self.is_active:
            return False

        ruler_in_progress = self._editor_state.ruler_in_progress
        if ruler_in_progress is not None:
            # Remove the preview point (last point) - only keep placed segments
            ruler_in_progress.remove_preview_point()

            # Ensure at least 2 points (start and end)
            if ruler_in_progress.point_count() >= 2:
                # Remove from scene temporarily (it was added for preview)
                if ruler_in_progress.scene() is not None:
                    self._scene.removeItem(ruler_in_progress)
                # Connect signals for undo support
                ruler_in_progress.commandCreated.connect(self._undo_stack.push)
                ruler_in_progress.requestDelete.connect(self._handle_item_delete)
                # Finalize ruler with undo command
                cmd = AddItemCommand(self._scene, ruler_in_progress)
                self._undo_stack.push(cmd)
                ruler_in_progress.setSelected(True)
                # Clear ruler_in_progress so finish() doesn't remove it
                self._editor_state.ruler_in_progress = None
            else:
                # Not enough points, remove it
                if ruler_in_progress.scene():
                    self._scene.removeItem(ruler_in_progress)
                self._editor_state.ruler_in_progress = None

        self.finish()
        return True

    def _handle_item_delete(self, item) -> None:
        """Handle delete request from item's context menu."""
        from ...core.undo_commands import RemoveItemCommand
        if item.scene():
            cmd = RemoveItemCommand(item.scene(), item)
            self._undo_stack.push(cmd)

    def handle_add_bend(self) -> bool:
        """
        Handle 'A' key to add bend during ruler placement.

        Returns:
            True if the event was consumed, False otherwise
        """
        if not self.is_active:
            return False

        ruler_in_progress = self._editor_state.ruler_in_progress
        if ruler_in_progress is not None:
            # Get current mouse position from view
            view_pos = self._view.mapFromGlobal(QtGui.QCursor.pos())
            scene_pt = self._view.mapToScene(view_pos)
            item_pt = ruler_in_progress.mapFromScene(scene_pt)

            # Finalize current segment and add new preview point
            if ruler_in_progress.point_count() >= 2:
                ruler_in_progress.finalize_segment(item_pt)
            return True

        return False


