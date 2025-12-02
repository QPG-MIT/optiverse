"""
Unit tests for undo/redo commands.
Test-driven development: write tests first, then implement.
"""

from __future__ import annotations

import pytest
from PyQt6 import QtWidgets

from optiverse.core.models import SourceParams
from optiverse.core.undo_commands import (
    AddItemCommand,
    Command,
    MoveItemCommand,
    RemoveItemCommand,
)
from optiverse.objects import SourceItem


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
        from tests.fixtures.factories import create_lens_item

        lens = create_lens_item()
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
        from PyQt6.QtCore import QPointF

        old_pos = source_item.pos()
        new_pos = QPointF(50, 60)

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


class TestRotateItemCommand:
    """Test RotateItemCommand for rotating items."""

    @pytest.fixture
    def scene(self, qapp):
        """Create a QGraphicsScene."""
        return QtWidgets.QGraphicsScene()

    @pytest.fixture
    def source_item(self, scene):
        """Create and add a SourceItem to scene."""
        item = SourceItem(SourceParams(x_mm=0, y_mm=0))
        item.setPos(10, 20)
        item.setRotation(0)
        scene.addItem(item)
        return item

    def test_execute_rotates_item_to_new_angle(self, source_item):
        """Execute should rotate item to new angle."""
        from optiverse.core.undo_commands import RotateItemCommand

        old_rotation = 0.0
        new_rotation = 45.0

        cmd = RotateItemCommand(source_item, old_rotation, new_rotation)
        cmd.execute()

        assert source_item.rotation() == new_rotation

    def test_undo_rotates_item_to_old_angle(self, source_item):
        """Undo should rotate item back to old angle."""
        from optiverse.core.undo_commands import RotateItemCommand

        old_rotation = 0.0
        new_rotation = 90.0

        source_item.setRotation(old_rotation)
        cmd = RotateItemCommand(source_item, old_rotation, new_rotation)

        cmd.execute()
        assert source_item.rotation() == new_rotation

        cmd.undo()
        assert source_item.rotation() == old_rotation

    def test_multiple_rotations(self, source_item):
        """Test multiple sequential rotations."""
        from optiverse.core.undo_commands import RotateItemCommand

        rot1 = 0.0
        rot2 = 45.0
        rot3 = 90.0

        source_item.setRotation(rot1)
        cmd1 = RotateItemCommand(source_item, rot1, rot2)
        cmd2 = RotateItemCommand(source_item, rot2, rot3)

        cmd1.execute()
        assert source_item.rotation() == rot2

        cmd2.execute()
        assert source_item.rotation() == rot3

        cmd2.undo()
        assert source_item.rotation() == rot2

        cmd1.undo()
        assert source_item.rotation() == rot1


class TestRotateItemsCommand:
    """Test RotateItemsCommand for group rotation."""

    @pytest.fixture
    def scene(self, qapp):
        """Create a QGraphicsScene."""
        return QtWidgets.QGraphicsScene()

    @pytest.fixture
    def source_items(self, scene):
        """Create and add multiple SourceItems to scene."""
        items = []
        for i in range(3):
            item = SourceItem(SourceParams(x_mm=i * 10, y_mm=0))
            item.setPos(i * 10, 0)
            item.setRotation(0)
            scene.addItem(item)
            items.append(item)
        return items

    def test_execute_rotates_all_items(self, source_items):
        """Execute should rotate all items to new positions and angles."""
        from PyQt6.QtCore import QPointF

        from optiverse.core.undo_commands import RotateItemsCommand

        old_positions = {item: QPointF(item.pos()) for item in source_items}
        old_rotations = {item: item.rotation() for item in source_items}

        # Simulate rotation
        new_positions = {
            source_items[0]: QPointF(5, 5),
            source_items[1]: QPointF(10, 10),
            source_items[2]: QPointF(15, 15),
        }
        new_rotations = {item: 45.0 for item in source_items}

        cmd = RotateItemsCommand(
            source_items, old_positions, new_positions, old_rotations, new_rotations
        )
        cmd.execute()

        for item in source_items:
            assert item.pos() == new_positions[item]
            assert item.rotation() == new_rotations[item]

    def test_undo_restores_all_items(self, source_items):
        """Undo should restore all items to old positions and angles."""
        from PyQt6.QtCore import QPointF

        from optiverse.core.undo_commands import RotateItemsCommand

        old_positions = {item: QPointF(item.pos()) for item in source_items}
        old_rotations = {item: item.rotation() for item in source_items}

        new_positions = {
            source_items[0]: QPointF(5, 5),
            source_items[1]: QPointF(10, 10),
            source_items[2]: QPointF(15, 15),
        }
        new_rotations = {item: 45.0 for item in source_items}

        cmd = RotateItemsCommand(
            source_items, old_positions, new_positions, old_rotations, new_rotations
        )

        cmd.execute()
        for item in source_items:
            assert item.pos() == new_positions[item]
            assert item.rotation() == 45.0

        cmd.undo()
        for item in source_items:
            assert item.pos() == old_positions[item]
            assert item.rotation() == old_rotations[item]
