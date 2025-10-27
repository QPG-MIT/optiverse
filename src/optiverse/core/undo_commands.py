"""
Command pattern implementation for undo/redo functionality.
Each command encapsulates an action that can be executed and undone.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from PyQt6 import QtCore

if TYPE_CHECKING:
    from PyQt6 import QtWidgets


class Command(ABC):
    """Abstract base class for undoable commands."""

    @abstractmethod
    def execute(self) -> None:
        """Execute the command."""
        pass

    @abstractmethod
    def undo(self) -> None:
        """Undo the command."""
        pass


class AddItemCommand(Command):
    """Command to add an item to the scene."""

    def __init__(self, scene: QtWidgets.QGraphicsScene, item: QtWidgets.QGraphicsItem):
        """
        Initialize AddItemCommand.

        Args:
            scene: The graphics scene to add the item to
            item: The graphics item to add
        """
        self.scene = scene
        self.item = item
        self._executed = False

    def execute(self) -> None:
        """Add the item to the scene."""
        if not self._executed:
            self.scene.addItem(self.item)
            self._executed = True

    def undo(self) -> None:
        """Remove the item from the scene."""
        if self._executed:
            self.scene.removeItem(self.item)
            self._executed = False


class RemoveItemCommand(Command):
    """Command to remove an item from the scene."""

    def __init__(self, scene: QtWidgets.QGraphicsScene, item: QtWidgets.QGraphicsItem):
        """
        Initialize RemoveItemCommand.

        Args:
            scene: The graphics scene to remove the item from
            item: The graphics item to remove
        """
        self.scene = scene
        self.item = item
        self._executed = False

    def execute(self) -> None:
        """Remove the item from the scene."""
        if not self._executed:
            self.scene.removeItem(self.item)
            self._executed = True

    def undo(self) -> None:
        """Add the item back to the scene."""
        if self._executed:
            self.scene.addItem(self.item)
            self._executed = False


class MoveItemCommand(Command):
    """Command to move an item to a new position."""

    def __init__(
        self,
        item: QtWidgets.QGraphicsItem,
        old_pos: QtCore.QPointF,
        new_pos: QtCore.QPointF,
    ):
        """
        Initialize MoveItemCommand.

        Args:
            item: The graphics item to move
            old_pos: The original position
            new_pos: The new position
        """
        self.item = item
        self.old_pos = QtCore.QPointF(old_pos)  # Make a copy
        self.new_pos = QtCore.QPointF(new_pos)  # Make a copy

    def execute(self) -> None:
        """Move the item to the new position."""
        self.item.setPos(self.new_pos)

    def undo(self) -> None:
        """Move the item back to the old position."""
        self.item.setPos(self.old_pos)

