"""
Example UI test demonstrating best practices.

This file shows how to write comprehensive UI tests that test the right things.
Use this as a reference when writing new UI tests.
"""

from __future__ import annotations

import unittest.mock as mock
from typing import TypeVar

import pytest
from PyQt6 import QtCore, QtWidgets

from optiverse.objects import SourceItem
from tests.helpers.ui_test_helpers import (
    add_source_to_window,
    create_main_window,
)

T = TypeVar("T")


def mock_file_dialog_save(file_path):
    return mock.patch.object(
        QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(file_path), "")
    )


def mock_file_dialog_open(file_path):
    return mock.patch.object(
        QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(file_path), "")
    )


def get_scene_items_by_type(scene, item_type: type[T]) -> list[T]:
    return [item for item in scene.items() if isinstance(item, item_type)]


def assert_item_count(scene, item_type: type[T], expected_count: int):
    items = get_scene_items_by_type(scene, item_type)
    assert (
        len(items) == expected_count
    ), f"Expected {expected_count} {item_type.__name__}, got {len(items)}"


def assert_params_match(item, expected_params: dict, tolerance: float = 0.01):
    params = item.params
    for param_name, expected_value in expected_params.items():
        actual_value = getattr(params, param_name)
        if isinstance(expected_value, (int, float)):
            assert (
                abs(actual_value - expected_value) <= tolerance
            ), f"{param_name}: expected {expected_value}±{tolerance}, got {actual_value}"
        else:
            assert (
                actual_value == expected_value
            ), f"{param_name}: expected {expected_value}, got {actual_value}"


def simulate_keyboard_shortcut(qtbot, widget, key, modifier):
    qtbot.keyClick(widget, key, modifier)


class UIStateChecker:
    def __init__(self, main_window):
        self.window = main_window

    def assert_mode(self, expected_mode):
        assert self.window.editor_state.mode == expected_mode

    def assert_undo_enabled(self, enabled=True):
        assert self.window.act_undo.isEnabled() == enabled

    def assert_redo_enabled(self, enabled=True):
        assert self.window.act_redo.isEnabled() == enabled


class TestUIBestPractices:
    """
    Example test class showing best practices for UI testing.
    """

    def test_user_can_add_and_remove_component(self, qtbot):
        """
        Example: Test complete user workflow.

        This test follows the user's perspective:
        1. User opens application
        2. User adds a component
        3. User verifies it appears
        4. User removes it
        5. User verifies it's gone
        """
        # Create window
        window = create_main_window(qtbot)

        # Initial state: empty scene
        from optiverse.objects import SourceItem

        assert_item_count(window.scene, SourceItem, 0)

        # User adds source via menu/button
        add_source_to_window(window)

        # Verify source appears
        assert_item_count(window.scene, SourceItem, 1)

        # Get the added source
        sources = get_scene_items_by_type(window.scene, SourceItem)
        source = sources[0]

        # Verify it has reasonable defaults
        assert source.params.x_mm == 0.0
        assert source.params.y_mm == 0.0

        # User selects and deletes source
        source.setSelected(True)
        window.delete_selected()

        # Verify it's gone
        assert_item_count(window.scene, SourceItem, 0)

    def test_save_load_preserves_all_properties(self, qtbot, tmp_path):
        """
        Example: Test that save/load preserves all component properties.

        This ensures data integrity - critical for user trust.
        """
        window = create_main_window(qtbot)

        # Create component with specific properties
        from optiverse.core.models import SourceParams
        from optiverse.objects import SourceItem

        params = SourceParams(
            x_mm=123.45,
            y_mm=678.90,
            angle_deg=45.0,
            n_rays=11,
            size_mm=15.0,
            wavelength_nm=532.0,
            color_hex="#FF0000",
        )
        source = SourceItem(params)
        window.scene.addItem(source)

        # Save
        save_path = tmp_path / "test.json"
        with mock_file_dialog_save(save_path):
            window.save_assembly()

        assert save_path.exists()

        # Clear scene
        window.scene.clear()
        assert_item_count(window.scene, SourceItem, 0)

        # Load
        with mock_file_dialog_open(save_path):
            window.open_assembly()

        # Verify all properties preserved
        sources = get_scene_items_by_type(window.scene, SourceItem)
        assert len(sources) == 1

        loaded_source = sources[0]
        assert_params_match(
            loaded_source,
            {
                "x_mm": 123.45,
                "y_mm": 678.90,
                "angle_deg": 45.0,
                "n_rays": 11,
                "size_mm": 15.0,
                "wavelength_nm": 532.0,
                "color_hex": "#FF0000",
            },
        )

    def test_keyboard_shortcuts_work(self, qtbot):
        """
        Example: Test keyboard shortcuts match documentation.

        Users rely on keyboard shortcuts - they must work!
        """
        window = create_main_window(qtbot)

        # Add a source
        add_source_to_window(window)

        # Select it
        sources = get_scene_items_by_type(window.scene, SourceItem)
        sources[0].setSelected(True)

        # Test Ctrl+C (copy)
        simulate_keyboard_shortcut(
            qtbot, window, QtCore.Qt.Key.Key_C, QtCore.Qt.KeyboardModifier.ControlModifier
        )

        # Verify clipboard has item
        assert len(window._clipboard) == 1

        # Test Ctrl+V (paste)
        initial_count = len(get_scene_items_by_type(window.scene, SourceItem))
        simulate_keyboard_shortcut(
            qtbot, window, QtCore.Qt.Key.Key_V, QtCore.Qt.KeyboardModifier.ControlModifier
        )

        # Verify new item added
        assert_item_count(window.scene, SourceItem, initial_count + 1)

    def test_undo_redo_integration(self, qtbot):
        """
        Example: Test undo/redo works correctly.

        Undo/redo is critical for user experience.
        """
        window = create_main_window(qtbot)
        checker = UIStateChecker(window)

        # Initially undo/redo disabled
        checker.assert_undo_enabled(False)
        checker.assert_redo_enabled(False)

        # Add component
        add_source_to_window(window)

        # Undo should be enabled
        checker.assert_undo_enabled(True)
        checker.assert_redo_enabled(False)

        # Verify item exists
        assert_item_count(window.scene, SourceItem, 1)

        # Undo
        window.undo_stack.undo()

        # Item should be gone
        assert_item_count(window.scene, SourceItem, 0)
        checker.assert_redo_enabled(True)

        # Redo
        window.undo_stack.redo()

        # Item should be back
        assert_item_count(window.scene, SourceItem, 1)

    def test_error_handling_graceful(self, qtbot, tmp_path):
        """
        Example: Test error handling doesn't crash application.

        Errors happen - application should handle them gracefully.
        """
        window = create_main_window(qtbot)

        # Try to load invalid file
        invalid_path = tmp_path / "invalid.json"
        invalid_path.write_text("{ invalid json }")

        # Should not crash
        with mock_file_dialog_open(invalid_path):
            try:
                window.open_assembly()
            except Exception:
                pytest.fail("Loading invalid file should not raise exception")

        # Application should still be functional
        assert window.isVisible()
        add_source_to_window(window)
        assert_item_count(window.scene, SourceItem, 1)

    def test_ui_state_consistency(self, qtbot):
        """
        Example: Test UI state is consistent.

        UI elements should reflect application state correctly.
        """
        window = create_main_window(qtbot)
        checker = UIStateChecker(window)

        # Initially in default mode
        from optiverse.core.editor_state import EditorMode

        checker.assert_mode(EditorMode.DEFAULT)

        # Enter inspect mode
        window.act_inspect.trigger()
        checker.assert_mode(EditorMode.INSPECT)

        # Add lens (should enter placement mode)
        window.act_add_lens.trigger()
        checker.assert_mode(EditorMode.PLACEMENT)

        # Cancel with Esc
        simulate_keyboard_shortcut(qtbot, window, QtCore.Qt.Key.Key_Escape)
        checker.assert_mode(EditorMode.DEFAULT)

    def test_component_interaction(self, qtbot):
        """
        Example: Test user can interact with components.

        Components should respond to user interactions correctly.
        """
        window = create_main_window(qtbot)

        # Add component
        from optiverse.core.models import LensParams
        from tests.fixtures.factories import create_component_from_params

        lens = create_component_from_params(LensParams(x_mm=100, y_mm=100, efl_mm=50))
        window.scene.addItem(lens)

        # Select component
        lens.setSelected(True)
        assert lens.isSelected()

        # Move component
        new_pos = QtCore.QPointF(200, 200)
        lens.setPos(new_pos)

        # Verify position updated
        assert abs(lens.pos().x() - 200) < 0.01
        assert abs(lens.pos().y() - 200) < 0.01

        # Verify params updated
        assert abs(lens.params.x_mm - 200) < 0.01
        assert abs(lens.params.y_mm - 200) < 0.01
