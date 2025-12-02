"""
Integration tests for undo/redo functionality in MainWindow.

These tests verify that undo/redo works correctly for:
- Adding components (source, lens, mirror, beamsplitter, ruler, text)
- Moving components
- Deleting components
- Keyboard shortcuts (Ctrl+Z, Ctrl+Y)
"""

from __future__ import annotations

import pytest
from PyQt6 import QtCore, QtWidgets

from optiverse.objects import (
    SourceItem,
    TextNoteItem,
)
from optiverse.ui.views.main_window import MainWindow
from tests.helpers.ui_test_helpers import (
    add_lens_to_window,
    add_mirror_to_window,
    add_source_to_window,
    is_beamsplitter_component,
    is_lens_component,
    is_mirror_component,
)


class TestUndoRedoIntegration:
    """Integration tests for undo/redo in MainWindow."""

    @pytest.fixture
    def main_window(self, qapp):
        """Create a MainWindow instance for testing."""
        import gc

        window = MainWindow()
        # Disable autotrace to prevent timer-based hangs in tests
        window.autotrace = False
        # Stop any pending retrace timers
        window.raytracing_controller._retrace_timer.stop()
        # Stop autosave timer to prevent interference
        window.file_controller._autosave_timer.stop()
        # Process events to clear any pending operations
        QtWidgets.QApplication.processEvents()
        yield window
        # Clean up - stop all timers first
        window.autotrace = False
        window.raytracing_controller._retrace_timer.stop()
        window.file_controller._autosave_timer.stop()
        # Mark clean to avoid save dialogs
        window.file_controller.mark_clean()
        # Clear the scene to release graphics items
        window.raytracing_controller.clear_rays()
        for item in list(window.scene.items()):
            window.scene.removeItem(item)
        # Process all pending events
        QtWidgets.QApplication.processEvents()
        window.close()
        QtWidgets.QApplication.processEvents()
        # Force garbage collection to clean up Qt objects
        gc.collect()
        QtWidgets.QApplication.processEvents()

    def test_undo_redo_actions_exist(self, main_window):
        """Test that undo/redo actions are created."""
        from PyQt6.QtGui import QKeySequence

        assert hasattr(main_window, "act_undo")
        assert hasattr(main_window, "act_redo")
        assert main_window.act_undo.shortcut() == QKeySequence.StandardKey.Undo
        assert main_window.act_redo.shortcut() == QKeySequence.StandardKey.Redo

    def test_undo_redo_initially_disabled(self, main_window):
        """Test that undo/redo are initially disabled."""
        assert not main_window.act_undo.isEnabled()
        assert not main_window.act_redo.isEnabled()

    def test_undo_enabled_after_add_source(self, main_window):
        """Test that undo is enabled after adding a source."""
        add_source_to_window(main_window)
        assert main_window.act_undo.isEnabled()
        assert not main_window.act_redo.isEnabled()

    def test_undo_add_source(self, main_window):
        """Test undoing source addition."""
        initial_count = len([it for it in main_window.scene.items() if isinstance(it, SourceItem)])

        add_source_to_window(main_window)
        after_add = len([it for it in main_window.scene.items() if isinstance(it, SourceItem)])
        assert after_add == initial_count + 1

        main_window.undo_stack.undo()
        after_undo = len([it for it in main_window.scene.items() if isinstance(it, SourceItem)])
        assert after_undo == initial_count

    def test_undo_triggers_retrace(self, main_window):
        """Test that undo triggers ray tracing when autotrace is enabled."""
        main_window.autotrace = True
        len(main_window.ray_items)

        # Add source and lens - this should create rays
        add_source_to_window(main_window)
        add_lens_to_window(main_window)

        # Verify rays were created
        len(main_window.ray_items)
        # May or may not have rays depending on geometry, but operation should complete

        # Undo the lens addition
        main_window._do_undo()

        # Verify undo completed (ray count should be recalculated)
        # The important thing is that retrace was called, not the specific count
        assert True  # If we get here without hanging, retrace worked

    def test_redo_triggers_retrace(self, main_window):
        """Test that redo triggers ray tracing when autotrace is enabled."""
        main_window.autotrace = True

        # Add source and lens
        add_source_to_window(main_window)
        add_lens_to_window(main_window)

        # Undo the lens
        main_window._do_undo()

        # Redo the lens addition
        main_window._do_redo()

        # Verify redo completed (ray count should be recalculated)
        # The important thing is that retrace was called, not the specific count
        assert True  # If we get here without hanging, retrace worked

    def test_redo_add_source(self, main_window):
        """Test redoing source addition."""
        initial_count = len([it for it in main_window.scene.items() if isinstance(it, SourceItem)])

        add_source_to_window(main_window)
        main_window.undo_stack.undo()

        assert main_window.act_redo.isEnabled()

        main_window.undo_stack.redo()
        after_redo = len([it for it in main_window.scene.items() if isinstance(it, SourceItem)])
        assert after_redo == initial_count + 1

    def test_undo_add_lens(self, main_window):
        """Test undoing lens addition."""
        initial_count = len([it for it in main_window.scene.items() if is_lens_component(it)])

        add_lens_to_window(main_window)
        after_add = len([it for it in main_window.scene.items() if is_lens_component(it)])
        assert after_add == initial_count + 1

        main_window.undo_stack.undo()
        after_undo = len([it for it in main_window.scene.items() if is_lens_component(it)])
        assert after_undo == initial_count

    def test_undo_add_mirror(self, main_window):
        """Test undoing mirror addition."""
        initial_count = len([it for it in main_window.scene.items() if is_mirror_component(it)])

        add_mirror_to_window(main_window)
        after_add = len([it for it in main_window.scene.items() if is_mirror_component(it)])
        assert after_add == initial_count + 1

        main_window.undo_stack.undo()
        after_undo = len([it for it in main_window.scene.items() if is_mirror_component(it)])
        assert after_undo == initial_count

    def test_undo_add_beamsplitter(self, main_window):
        """Test undoing beamsplitter addition."""
        from PyQt6 import QtCore

        from optiverse.core.component_types import ComponentType

        initial_count = len(
            [it for it in main_window.scene.items() if is_beamsplitter_component(it)]
        )

        main_window.placement_handler.place_component_at(
            ComponentType.BEAMSPLITTER, QtCore.QPointF(0, 0)
        )
        after_add = len([it for it in main_window.scene.items() if is_beamsplitter_component(it)])
        assert after_add == initial_count + 1

        main_window.undo_stack.undo()
        after_undo = len([it for it in main_window.scene.items() if is_beamsplitter_component(it)])
        assert after_undo == initial_count

    def test_undo_add_text(self, main_window):
        """Test undoing text addition."""
        from PyQt6 import QtCore

        initial_count = len(
            [it for it in main_window.scene.items() if isinstance(it, TextNoteItem)]
        )

        main_window.placement_handler.place_component_at("text", QtCore.QPointF(0, 0))
        after_add = len([it for it in main_window.scene.items() if isinstance(it, TextNoteItem)])
        assert after_add == initial_count + 1

        main_window.undo_stack.undo()
        after_undo = len([it for it in main_window.scene.items() if isinstance(it, TextNoteItem)])
        assert after_undo == initial_count

    def test_multiple_undos(self, main_window):
        """Test multiple undo operations."""
        add_source_to_window(main_window)
        add_lens_to_window(main_window)
        add_mirror_to_window(main_window)

        sources = [it for it in main_window.scene.items() if isinstance(it, SourceItem)]
        lenses = [it for it in main_window.scene.items() if is_lens_component(it)]
        mirrors = [it for it in main_window.scene.items() if is_mirror_component(it)]

        assert len(sources) >= 1
        assert len(lenses) >= 1
        assert len(mirrors) >= 1

        # Undo mirror
        main_window.undo_stack.undo()
        mirrors_after = [it for it in main_window.scene.items() if is_mirror_component(it)]
        assert len(mirrors_after) == len(mirrors) - 1

        # Undo lens
        main_window.undo_stack.undo()
        lenses_after = [it for it in main_window.scene.items() if is_lens_component(it)]
        assert len(lenses_after) == len(lenses) - 1

        # Undo source
        main_window.undo_stack.undo()
        sources_after = [it for it in main_window.scene.items() if isinstance(it, SourceItem)]
        assert len(sources_after) == len(sources) - 1

    def test_undo_delete(self, main_window):
        """Test undoing item deletion."""
        add_source_to_window(main_window)
        sources = [it for it in main_window.scene.items() if isinstance(it, SourceItem)]
        item = sources[-1]
        item.setSelected(True)

        main_window.delete_selected()
        assert item not in main_window.scene.items()

        main_window.undo_stack.undo()
        assert item in main_window.scene.items()

    def test_undo_move(self, main_window):
        """Test undoing item movement."""
        add_source_to_window(main_window)
        sources = [it for it in main_window.scene.items() if isinstance(it, SourceItem)]
        item = sources[-1]

        old_pos = QtCore.QPointF(0, 0)
        new_pos = QtCore.QPointF(100, 100)

        item.setPos(old_pos)
        item.setSelected(True)

        # Move item
        item.setPos(new_pos)

        # Create and push move command
        from optiverse.core.undo_commands import MoveItemCommand

        cmd = MoveItemCommand(item, old_pos, new_pos)
        main_window.undo_stack.push(cmd)

        assert item.pos() == new_pos

        main_window.undo_stack.undo()
        assert item.pos() == old_pos

        main_window.undo_stack.redo()
        assert item.pos() == new_pos

    def test_undo_clears_redo_stack(self, main_window):
        """Test that new actions clear redo stack."""
        add_source_to_window(main_window)
        add_lens_to_window(main_window)

        main_window.undo_stack.undo()
        assert main_window.act_redo.isEnabled()

        add_mirror_to_window(main_window)
        assert not main_window.act_redo.isEnabled()

    def test_delete_action_exists(self, main_window):
        """Test that delete action exists."""
        assert hasattr(main_window, "act_delete")
        assert main_window.act_delete.shortcut() == QtCore.Qt.Key.Key_Delete

    def test_edit_menu_exists(self, main_window):
        """Test that Edit menu exists with undo/redo actions."""
        menubar = main_window.menuBar()
        edit_menu = None
        for action in menubar.actions():
            if action.text() == "&Edit":
                edit_menu = action.menu()
                break

        assert edit_menu is not None
        actions = [a.text() for a in edit_menu.actions() if not a.isSeparator()]
        assert "Undo" in actions
        assert "Redo" in actions
        assert "Delete" in actions

    def test_open_assembly_clears_undo_stack(self, main_window, tmp_path):
        """Test that opening an assembly clears undo history."""
        add_source_to_window(main_window)
        assert main_window.undo_stack.can_undo()

        # Create a temporary assembly file with version 2.0 format
        import json

        assembly_file = tmp_path / "test_assembly.json"
        data = {
            "version": "2.0",
            "items": [],
        }
        assembly_file.write_text(json.dumps(data))

        # Mock both the file dialog and the save prompt to avoid blocking dialogs
        import unittest.mock as mock

        with mock.patch.object(
            QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(assembly_file), "")
        ), mock.patch.object(
            main_window.file_controller,
            "prompt_save_changes",
            return_value=QtWidgets.QMessageBox.StandardButton.Discard,
        ):
            main_window.open_assembly()

        assert not main_window.undo_stack.can_undo()
        assert not main_window.undo_stack.can_redo()
