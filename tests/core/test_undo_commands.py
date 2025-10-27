"""
Unit tests for undo/redo commands.
Test-driven development: write tests first, then implement.
"""
from __future__ import annotations

import pytest
from PyQt6 import QtWidgets

from optiverse.core.undo_commands import (
    Command,
    AddItemCommand,
    RemoveItemCommand,
    MoveItemCommand,
)
from optiverse.objects import SourceItem, LensItem
from optiverse.core.models import SourceParams, LensParams


class TestCommand:
    """Test the abstract Command base class."""

    def test_command_has_execute_method(self):
        """Command should have execute method."""
        assert hasattr(Command, "execute")

    def test_command_has_undo_method(self):
        """Command should have undo method."""
        assert hasattr(Command, "undo")


class TestAddItemCommand:
    """Test AddItemCommand for adding items to scene."""

    @pytest.fixture
    def scene(self, qapp):
        """Create a QGraphicsScene for testing."""
        return QtWidgets.QGraphicsScene()

    @pytest.fixture
    def source_item(self):
        """Create a SourceItem for testing."""
        return SourceItem(SourceParams(x_mm=0, y_mm=0))

    def test_execute_adds_item_to_scene(self, scene, source_item):
        """Execute should add item to scene."""
        cmd = AddItemCommand(scene, source_item)
        assert source_item not in scene.items()
        
        cmd.execute()
        assert source_item in scene.items()

    def test_undo_removes_item_from_scene(self, scene, source_item):
        """Undo should remove item from scene."""
        cmd = AddItemCommand(scene, source_item)
        cmd.execute()
        assert source_item in scene.items()
        
        cmd.undo()
        assert source_item not in scene.items()

    def test_execute_twice_only_adds_once(self, scene, source_item):
        """Multiple execute calls should be idempotent."""
        cmd = AddItemCommand(scene, source_item)
        cmd.execute()
        cmd.execute()
        
        # Item should only appear once
        assert scene.items().count(source_item) == 1

    def test_add_lens_item(self, scene):
        """Should work with different item types."""
        lens = LensItem(LensParams())
        cmd = AddItemCommand(scene, lens)
        
        cmd.execute()
        assert lens in scene.items()
        
        cmd.undo()
        assert lens not in scene.items()


class TestRemoveItemCommand:
    """Test RemoveItemCommand for removing items from scene."""

    @pytest.fixture
    def scene(self, qapp):
        """Create a QGraphicsScene with an item."""
        scene = QtWidgets.QGraphicsScene()
        return scene

    @pytest.fixture
    def source_item(self, scene):
        """Create and add a SourceItem to scene."""
        item = SourceItem(SourceParams(x_mm=10, y_mm=20))
        scene.addItem(item)
        return item

    def test_execute_removes_item_from_scene(self, scene, source_item):
        """Execute should remove item from scene."""
        cmd = RemoveItemCommand(scene, source_item)
        assert source_item in scene.items()
        
        cmd.execute()
        assert source_item not in scene.items()

    def test_undo_adds_item_back_to_scene(self, scene, source_item):
        """Undo should add item back to scene."""
        cmd = RemoveItemCommand(scene, source_item)
        cmd.execute()
        assert source_item not in scene.items()
        
        cmd.undo()
        assert source_item in scene.items()

    def test_item_preserves_position_after_undo(self, scene, source_item):
        """Item should maintain its position after undo."""
        original_pos = source_item.pos()
        cmd = RemoveItemCommand(scene, source_item)
        
        cmd.execute()
        cmd.undo()
        
        assert source_item.pos() == original_pos


class TestMoveItemCommand:
    """Test MoveItemCommand for moving items."""

    @pytest.fixture
    def scene(self, qapp):
        """Create a QGraphicsScene."""
        return QtWidgets.QGraphicsScene()

    @pytest.fixture
    def source_item(self, scene):
        """Create and add a SourceItem to scene."""
        item = SourceItem(SourceParams(x_mm=0, y_mm=0))
        item.setPos(10, 20)
        scene.addItem(item)
        return item

    def test_execute_moves_item_to_new_position(self, source_item):
        """Execute should move item to new position."""
        old_pos = source_item.pos()
        new_pos = QtWidgets.QGraphicsScene().addEllipse(0, 0, 1, 1).pos()
        new_pos.setX(50)
        new_pos.setY(60)
        
        cmd = MoveItemCommand(source_item, old_pos, new_pos)
        cmd.execute()
        
        assert source_item.pos() == new_pos

    def test_undo_moves_item_to_old_position(self, source_item):
        """Undo should move item back to old position."""
        from PyQt6.QtCore import QPointF
        old_pos = QPointF(10, 20)
        new_pos = QPointF(50, 60)
        
        source_item.setPos(old_pos)
        cmd = MoveItemCommand(source_item, old_pos, new_pos)
        
        cmd.execute()
        assert source_item.pos() == new_pos
        
        cmd.undo()
        assert source_item.pos() == old_pos

    def test_multiple_moves(self, source_item):
        """Test multiple sequential moves."""
        from PyQt6.QtCore import QPointF
        pos1 = QPointF(0, 0)
        pos2 = QPointF(10, 10)
        pos3 = QPointF(20, 20)
        
        source_item.setPos(pos1)
        cmd1 = MoveItemCommand(source_item, pos1, pos2)
        cmd2 = MoveItemCommand(source_item, pos2, pos3)
        
        cmd1.execute()
        assert source_item.pos() == pos2
        
        cmd2.execute()
        assert source_item.pos() == pos3
        
        cmd2.undo()
        assert source_item.pos() == pos2
        
        cmd1.undo()
        assert source_item.pos() == pos1

