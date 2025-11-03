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
        # Force Qt to update cached transforms (fixes BeamsplitterItem position tracking)
        self.item.setTransform(self.item.transform())

    def undo(self) -> None:
        """Move the item back to the old position."""
        self.item.setPos(self.old_pos)
        # Force Qt to update cached transforms (fixes BeamsplitterItem position tracking)
        self.item.setTransform(self.item.transform())


class RemoveMultipleItemsCommand(Command):
    """Command to remove multiple items from the scene in a single operation."""

    def __init__(self, scene: QtWidgets.QGraphicsScene, items: list[QtWidgets.QGraphicsItem]):
        """
        Initialize RemoveMultipleItemsCommand.

        Args:
            scene: The graphics scene to remove items from
            items: The list of graphics items to remove
        """
        self.scene = scene
        self.items = items
        self._executed = False

    def execute(self) -> None:
        """Remove all items from the scene."""
        if not self._executed:
            for item in self.items:
                self.scene.removeItem(item)
            self._executed = True

    def undo(self) -> None:
        """Add all items back to the scene."""
        if self._executed:
            for item in self.items:
                self.scene.addItem(item)
            self._executed = False


class PasteItemsCommand(Command):
    """Command to paste multiple items to the scene."""

    def __init__(self, scene: QtWidgets.QGraphicsScene, items: list[QtWidgets.QGraphicsItem]):
        """
        Initialize PasteItemsCommand.

        Args:
            scene: The graphics scene to add items to
            items: The list of graphics items to add
        """
        self.scene = scene
        self.items = items
        self._executed = False

    def execute(self) -> None:
        """Add all items to the scene."""
        if not self._executed:
            for item in self.items:
                self.scene.addItem(item)
            self._executed = True

    def undo(self) -> None:
        """Remove all items from the scene."""
        if self._executed:
            for item in self.items:
                self.scene.removeItem(item)
            self._executed = False


class RotateItemCommand(Command):
    """Command to rotate an item to a new angle."""

    def __init__(
        self,
        item: QtWidgets.QGraphicsItem,
        old_rotation: float,
        new_rotation: float,
    ):
        """
        Initialize RotateItemCommand.

        Args:
            item: The graphics item to rotate
            old_rotation: The original rotation in degrees
            new_rotation: The new rotation in degrees
        """
        self.item = item
        self.old_rotation = old_rotation
        self.new_rotation = new_rotation

    def execute(self) -> None:
        """Rotate the item to the new angle."""
        self.item.setRotation(self.new_rotation)

    def undo(self) -> None:
        """Rotate the item back to the old angle."""
        self.item.setRotation(self.old_rotation)


class RotateItemsCommand(Command):
    """Command to rotate multiple items together (group rotation)."""

    def __init__(
        self,
        items: list[QtWidgets.QGraphicsItem],
        old_positions: dict[QtWidgets.QGraphicsItem, QtCore.QPointF],
        new_positions: dict[QtWidgets.QGraphicsItem, QtCore.QPointF],
        old_rotations: dict[QtWidgets.QGraphicsItem, float],
        new_rotations: dict[QtWidgets.QGraphicsItem, float],
    ):
        """
        Initialize RotateItemsCommand for group rotation.

        Args:
            items: The list of graphics items to rotate
            old_positions: Dict mapping items to their original positions
            new_positions: Dict mapping items to their new positions
            old_rotations: Dict mapping items to their original rotations
            new_rotations: Dict mapping items to their new rotations
        """
        self.items = items
        self.old_positions = {item: QtCore.QPointF(pos) for item, pos in old_positions.items()}
        self.new_positions = {item: QtCore.QPointF(pos) for item, pos in new_positions.items()}
        self.old_rotations = dict(old_rotations)
        self.new_rotations = dict(new_rotations)

    def execute(self) -> None:
        """Apply new positions and rotations to all items."""
        for item in self.items:
            item.setPos(self.new_positions[item])
            item.setRotation(self.new_rotations[item])

    def undo(self) -> None:
        """Restore old positions and rotations for all items."""
        for item in self.items:
            item.setPos(self.old_positions[item])
            item.setRotation(self.old_rotations[item])


class ZOrderCommand(Command):
    """Command to change z-order (stacking order) of items."""

    def __init__(
        self,
        items: list[QtWidgets.QGraphicsItem],
        old_z_values: dict[QtWidgets.QGraphicsItem, float],
        new_z_values: dict[QtWidgets.QGraphicsItem, float],
    ):
        """
        Initialize ZOrderCommand.

        Args:
            items: The list of graphics items to change z-order for
            old_z_values: Dict mapping items to their original z-values
            new_z_values: Dict mapping items to their new z-values
        """
        self.items = items
        self.old_z_values = dict(old_z_values)
        self.new_z_values = dict(new_z_values)

    def execute(self) -> None:
        """Apply new z-values to all items."""
        for item in self.items:
            item.setZValue(self.new_z_values[item])

    def undo(self) -> None:
        """Restore old z-values for all items."""
        for item in self.items:
            item.setZValue(self.old_z_values[item])