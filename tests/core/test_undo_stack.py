"""
Unit tests for UndoStack.
Test-driven development: write tests first, then implement.
"""
from __future__ import annotations

import pytest
from PyQt6 import QtWidgets, QtCore

from optiverse.core.undo_stack import UndoStack
from optiverse.core.undo_commands import AddItemCommand, RemoveItemCommand, MoveItemCommand
from optiverse.objects import SourceItem
from optiverse.core.models import SourceParams


class TestUndoStack:
    """Test UndoStack functionality."""

    @pytest.fixture
    def stack(self):
        """Create an UndoStack for testing."""
        return UndoStack()

    @pytest.fixture
    def scene(self, qapp):
        """Create a QGraphicsScene for testing."""
        return QtWidgets.QGraphicsScene()

    def test_new_stack_has_no_commands(self, stack):
        """New stack should be empty."""
        assert not stack.can_undo()
        assert not stack.can_redo()

    def test_push_command_enables_undo(self, stack, scene):
        """Pushing a command should enable undo."""
        item = SourceItem(SourceParams())
        cmd = AddItemCommand(scene, item)
        
        stack.push(cmd)
        assert stack.can_undo()
        assert not stack.can_redo()

    def test_push_executes_command(self, stack, scene):
        """Pushing a command should execute it."""
        item = SourceItem(SourceParams())
        cmd = AddItemCommand(scene, item)
        
        assert item not in scene.items()
        stack.push(cmd)
        assert item in scene.items()

    def test_undo_reverses_command(self, stack, scene):
        """Undo should reverse the last command."""
        item = SourceItem(SourceParams())
        cmd = AddItemCommand(scene, item)
        
        stack.push(cmd)
        assert item in scene.items()
        
        stack.undo()
        assert item not in scene.items()

    def test_undo_enables_redo(self, stack, scene):
        """After undo, redo should be available."""
        item = SourceItem(SourceParams())
        cmd = AddItemCommand(scene, item)
        
        stack.push(cmd)
        stack.undo()
        
        assert not stack.can_undo()
        assert stack.can_redo()

    def test_redo_reapplies_command(self, stack, scene):
        """Redo should reapply the undone command."""
        item = SourceItem(SourceParams())
        cmd = AddItemCommand(scene, item)
        
        stack.push(cmd)
        stack.undo()
        assert item not in scene.items()
        
        stack.redo()
        assert item in scene.items()

    def test_push_after_undo_clears_redo_stack(self, stack, scene):
        """Pushing a new command after undo should clear redo history."""
        item1 = SourceItem(SourceParams(x_mm=0, y_mm=0))
        item2 = SourceItem(SourceParams(x_mm=10, y_mm=10))
        
        cmd1 = AddItemCommand(scene, item1)
        cmd2 = AddItemCommand(scene, item2)
        
        stack.push(cmd1)
        stack.undo()
        assert stack.can_redo()
        
        stack.push(cmd2)
        assert not stack.can_redo()

    def test_multiple_undos(self, stack, scene):
        """Should support multiple undo operations."""
        item1 = SourceItem(SourceParams(x_mm=0, y_mm=0))
        item2 = SourceItem(SourceParams(x_mm=10, y_mm=10))
        item3 = SourceItem(SourceParams(x_mm=20, y_mm=20))
        
        stack.push(AddItemCommand(scene, item1))
        stack.push(AddItemCommand(scene, item2))
        stack.push(AddItemCommand(scene, item3))
        
        assert len(scene.items()) == 3
        
        stack.undo()
        assert len(scene.items()) == 2
        assert item3 not in scene.items()
        
        stack.undo()
        assert len(scene.items()) == 1
        assert item2 not in scene.items()
        
        stack.undo()
        assert len(scene.items()) == 0
        assert item1 not in scene.items()

    def test_multiple_redos(self, stack, scene):
        """Should support multiple redo operations."""
        item1 = SourceItem(SourceParams(x_mm=0, y_mm=0))
        item2 = SourceItem(SourceParams(x_mm=10, y_mm=10))
        
        stack.push(AddItemCommand(scene, item1))
        stack.push(AddItemCommand(scene, item2))
        
        stack.undo()
        stack.undo()
        assert len(scene.items()) == 0
        
        stack.redo()
        assert len(scene.items()) == 1
        assert item1 in scene.items()
        
        stack.redo()
        assert len(scene.items()) == 2
        assert item2 in scene.items()

    def test_undo_when_empty_does_nothing(self, stack):
        """Undo on empty stack should do nothing."""
        stack.undo()  # Should not raise
        assert not stack.can_undo()

    def test_redo_when_empty_does_nothing(self, stack):
        """Redo when no redo available should do nothing."""
        stack.redo()  # Should not raise
        assert not stack.can_redo()

    def test_clear_empties_both_stacks(self, stack, scene):
        """Clear should empty both undo and redo stacks."""
        item = SourceItem(SourceParams())
        stack.push(AddItemCommand(scene, item))
        stack.undo()
        
        assert stack.can_redo()
        
        stack.clear()
        assert not stack.can_undo()
        assert not stack.can_redo()

    def test_signals_emitted_on_state_change(self, stack, scene, qtbot):
        """Stack should emit signals when state changes."""
        # UndoStack should emit canUndoChanged and canRedoChanged signals
        assert hasattr(stack, "canUndoChanged")
        assert hasattr(stack, "canRedoChanged")
        
        with qtbot.waitSignal(stack.canUndoChanged):
            item = SourceItem(SourceParams())
            stack.push(AddItemCommand(scene, item))
        
        with qtbot.waitSignal(stack.canRedoChanged):
            stack.undo()

    def test_move_command_undo_redo(self, stack, scene):
        """Test undo/redo with move commands."""
        from PyQt6.QtCore import QPointF
        
        item = SourceItem(SourceParams())
        scene.addItem(item)
        
        old_pos = QPointF(0, 0)
        new_pos = QPointF(50, 50)
        item.setPos(old_pos)
        
        cmd = MoveItemCommand(item, old_pos, new_pos)
        stack.push(cmd)
        
        assert item.pos() == new_pos
        
        stack.undo()
        assert item.pos() == old_pos
        
        stack.redo()
        assert item.pos() == new_pos

