"""
Base class for measurement items (ruler, angle, path).

Provides common functionality for context menus, z-order handling,
and undo/redo support via commandCreated signal.
"""
from __future__ import annotations

import uuid
from typing import Dict, Any, Optional

from PyQt6 import QtCore, QtWidgets

from ...core.zorder_utils import handle_z_order_from_menu


class BaseMeasureItem(QtWidgets.QGraphicsObject):
    """
    Base class for measurement annotation items.

    Provides:
    - commandCreated signal for undo/redo support
    - Common context menu with z-order and delete options
    - requestDelete signal for undoable deletion
    - UUID for collaboration
    """

    # Signal emitted when an undo command is created
    commandCreated = QtCore.pyqtSignal(object)

    # Signal emitted when item requests deletion (for undoable delete)
    requestDelete = QtCore.pyqtSignal(object)  # Emits self

    def __init__(self, item_uuid: str | None = None):
        super().__init__()
        # Generate or use provided UUID for collaboration
        self.item_uuid = item_uuid if item_uuid else str(uuid.uuid4())

    def _emit_property_change_command(
        self,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any]
    ) -> None:
        """Create and emit a property change command for undo/redo."""
        from ...core.undo_commands import PropertyChangeCommand
        cmd = PropertyChangeCommand(self, before_state, after_state)
        self.commandCreated.emit(cmd)

    def _build_context_menu(self) -> tuple[QtWidgets.QMenu, Dict[str, QtWidgets.QAction]]:
        """
        Build a standard context menu with delete and z-order options.

        Returns:
            Tuple of (menu, action_dict) where action_dict maps action names
            to their QAction objects.
        """
        menu = QtWidgets.QMenu()
        actions = {}

        actions['delete'] = menu.addAction("Delete")

        menu.addSeparator()
        actions['bring_to_front'] = menu.addAction("Bring to Front")
        actions['bring_forward'] = menu.addAction("Bring Forward")
        actions['send_backward'] = menu.addAction("Send Backward")
        actions['send_to_back'] = menu.addAction("Send to Back")

        return menu, actions

    def _handle_context_menu_action(
        self,
        selected_action: Optional[QtWidgets.QAction],
        actions: Dict[str, QtWidgets.QAction]
    ) -> bool:
        """
        Handle a context menu action.

        Args:
            selected_action: The action selected by the user
            actions: Dict of action names to QAction objects

        Returns:
            True if an action was handled, False otherwise
        """
        if selected_action is None:
            return False

        if selected_action == actions.get('delete'):
            # Emit requestDelete signal for undoable deletion
            self.requestDelete.emit(self)
            return True

        # Handle z-order actions
        z_order_map = {
            actions.get('bring_to_front'): "bring_to_front",
            actions.get('bring_forward'): "bring_forward",
            actions.get('send_backward'): "send_backward",
            actions.get('send_to_back'): "send_to_back",
        }

        if selected_action in z_order_map:
            handle_z_order_from_menu(self, selected_action, z_order_map)
            return True

        return False

    def capture_state(self) -> Dict[str, Any]:
        """
        Capture current state for undo/redo.

        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement capture_state()")

    def apply_state(self, state: Dict[str, Any]) -> None:
        """
        Apply a previously captured state.

        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement apply_state()")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for save/load.

        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement to_dict()")



