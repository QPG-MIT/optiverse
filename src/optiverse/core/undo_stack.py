"""
UndoStack manages the history of commands and provides undo/redo functionality.
"""
from __future__ import annotations

from typing import List

from PyQt6 import QtCore

from .undo_commands import Command


class UndoStack(QtCore.QObject):
    """
    Manages a stack of commands for undo/redo functionality.
    
    Signals:
        canUndoChanged: Emitted when undo availability changes
        canRedoChanged: Emitted when redo availability changes
    """

    canUndoChanged = QtCore.pyqtSignal(bool)
    canRedoChanged = QtCore.pyqtSignal(bool)

    def __init__(self):
        """Initialize an empty undo stack."""
        super().__init__()
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []

    def push(self, command: Command) -> None:
        """
        Execute and push a command onto the undo stack.
        
        Args:
            command: The command to execute and push
        """
        # Execute the command
        command.execute()
        
        # Clear redo stack when new command is pushed
        old_can_redo = self.can_redo()
        self._redo_stack.clear()
        if old_can_redo:
            self.canRedoChanged.emit(False)
        
        # Add to undo stack
        old_can_undo = self.can_undo()
        self._undo_stack.append(command)
        if not old_can_undo:
            self.canUndoChanged.emit(True)

    def undo(self) -> None:
        """Undo the last command."""
        if not self.can_undo():
            return
        
        command = self._undo_stack.pop()
        command.undo()
        
        old_can_redo = self.can_redo()
        self._redo_stack.append(command)
        if not old_can_redo:
            self.canRedoChanged.emit(True)
        
        if not self.can_undo():
            self.canUndoChanged.emit(False)

    def redo(self) -> None:
        """Redo the last undone command."""
        if not self.can_redo():
            return
        
        command = self._redo_stack.pop()
        command.execute()
        
        old_can_undo = self.can_undo()
        self._undo_stack.append(command)
        if not old_can_undo:
            self.canUndoChanged.emit(True)
        
        if not self.can_redo():
            self.canRedoChanged.emit(False)

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        """Clear both undo and redo stacks."""
        old_can_undo = self.can_undo()
        old_can_redo = self.can_redo()
        
        self._undo_stack.clear()
        self._redo_stack.clear()
        
        if old_can_undo:
            self.canUndoChanged.emit(False)
        if old_can_redo:
            self.canRedoChanged.emit(False)

