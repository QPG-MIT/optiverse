"""
Test for undo/redo with multiple item deletions.

This test verifies the fix for the bug where deleting multiple items
together would require multiple undo operations instead of just one.
"""
from __future__ import annotations

import pytest
from PyQt6 import QtWidgets

from optiverse.core.undo_stack import UndoStack
from optiverse.core.undo_commands import RemoveMultipleItemsCommand
from optiverse.objects import SourceItem, LensItem, MirrorItem
from optiverse.core.models import SourceParams, LensParams, MirrorParams


class TestMultipleItemDeletionUndo:
    """Test that multiple deletions are undone together."""

    @pytest.fixture
    def stack(self):
        """Create an UndoStack for testing."""
        return UndoStack()

    @pytest.fixture
    def scene(self, qapp):
        """Create a QGraphicsScene with multiple items."""
        scene = QtWidgets.QGraphicsScene()
        return scene

    def test_delete_multiple_items_undo_with_single_operation(self, stack, scene):
        """
        When multiple items are deleted together, a single undo should restore all of them.

        This is the main fix for the reported bug.
        """
        # Create 3 different items
        item1 = SourceItem(SourceParams(x_mm=0, y_mm=0))
        item2 = LensItem(LensParams(x_mm=10, y_mm=10))
        item3 = MirrorItem(MirrorParams(x_mm=20, y_mm=20))

        # Add them to the scene
        scene.addItem(item1)
        scene.addItem(item2)
        scene.addItem(item3)

        assert len(scene.items()) == 3

        # Delete all 3 items using RemoveMultipleItemsCommand
        cmd = RemoveMultipleItemsCommand(scene, [item1, item2, item3])
        stack.push(cmd)

        # All items should be gone
        assert len(scene.items()) == 0
        assert item1 not in scene.items()
        assert item2 not in scene.items()
        assert item3 not in scene.items()

        # Single undo should restore ALL items
        stack.undo()
        assert len(scene.items()) == 3
        assert item1 in scene.items()
        assert item2 in scene.items()
        assert item3 in scene.items()

        # Single redo should remove ALL items again
        stack.redo()
        assert len(scene.items()) == 0
        assert item1 not in scene.items()
        assert item2 not in scene.items()
        assert item3 not in scene.items()

    def test_delete_multiple_preserves_item_state(self, stack, scene):
        """Items should preserve their state (position, etc.) after undo."""
        from PyQt6.QtCore import QPointF

        item1 = SourceItem(SourceParams(x_mm=0, y_mm=0))
        item2 = LensItem(LensParams(x_mm=10, y_mm=10))

        pos1 = QPointF(100, 200)
        pos2 = QPointF(300, 400)

        scene.addItem(item1)
        scene.addItem(item2)
        item1.setPos(pos1)
        item2.setPos(pos2)

        # Delete both items
        cmd = RemoveMultipleItemsCommand(scene, [item1, item2])
        stack.push(cmd)

        # Undo deletion
        stack.undo()

        # Items should be back with original positions
        assert item1 in scene.items()
        assert item2 in scene.items()
        assert item1.pos() == pos1
        assert item2.pos() == pos2

    def test_empty_list_doesnt_crash(self, stack, scene):
        """Deleting empty list of items should not crash."""
        cmd = RemoveMultipleItemsCommand(scene, [])
        stack.push(cmd)

        # Should not crash
        stack.undo()
        stack.redo()

    def test_single_item_in_list_works(self, stack, scene):
        """RemoveMultipleItemsCommand should work with a single item."""
        item = SourceItem(SourceParams(x_mm=0, y_mm=0))
        scene.addItem(item)

        cmd = RemoveMultipleItemsCommand(scene, [item])
        stack.push(cmd)

        assert item not in scene.items()

        stack.undo()
        assert item in scene.items()

    def test_comparison_with_individual_commands(self, stack, scene):
        """
        Demonstrate the difference between individual commands vs batched command.

        This test shows the bug that was fixed.
        """
        # Setup: 3 items
        item1 = SourceItem(SourceParams(x_mm=0, y_mm=0))
        item2 = LensItem(LensParams(x_mm=10, y_mm=10))
        item3 = MirrorItem(MirrorParams(x_mm=20, y_mm=20))

        scene.addItem(item1)
        scene.addItem(item2)
        scene.addItem(item3)

        # Use the batched command (FIXED behavior)
        cmd = RemoveMultipleItemsCommand(scene, [item1, item2, item3])
        stack.push(cmd)

        assert len(scene.items()) == 0

        # ONE undo restores ALL items
        assert stack.can_undo()
        stack.undo()
        assert len(scene.items()) == 3

        # Stack should be empty now (no more undos needed)
        assert not stack.can_undo()



