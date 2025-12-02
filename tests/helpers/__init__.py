"""
Test helpers for Optiverse.

This module provides utility functions for UI testing.
"""

from .ui_test_helpers import (
    UIStateChecker,
    add_lens_to_window,
    add_mirror_to_window,
    add_source_to_window,
    assert_item_count,
    assert_params_match,
    assert_property_matches,
    assert_widget_enabled,
    assert_widget_visible,
    create_component_editor,
    create_main_window,
    create_test_image,
    get_scene_items_by_type,
    get_widget_by_type,
    is_beamsplitter_component,
    is_lens_component,
    is_mirror_component,
    mock_file_dialog_cancel,
    mock_file_dialog_open,
    mock_file_dialog_save,
    safe_wait_exposed,
    simulate_drag_and_drop,
    simulate_keyboard_shortcut,
    trigger_action,
    wait_for_signal,
    wait_for_widget_visible,
)

__all__ = [
    # Window creation
    "create_main_window",
    "create_component_editor",
    # Item addition helpers
    "add_source_to_window",
    "add_lens_to_window",
    "add_mirror_to_window",
    # Mock helpers
    "mock_file_dialog_save",
    "mock_file_dialog_open",
    "mock_file_dialog_cancel",
    # Scene helpers
    "get_scene_items_by_type",
    "assert_item_count",
    # Component type detection
    "is_lens_component",
    "is_mirror_component",
    "is_beamsplitter_component",
    # Drag and drop
    "simulate_drag_and_drop",
    # Signals
    "wait_for_signal",
    # Assertions
    "assert_property_matches",
    "assert_params_match",
    # Actions
    "trigger_action",
    "simulate_keyboard_shortcut",
    # Widget helpers
    "wait_for_widget_visible",
    "safe_wait_exposed",
    "get_widget_by_type",
    "assert_widget_enabled",
    "assert_widget_visible",
    # Test utilities
    "create_test_image",
    # State checker
    "UIStateChecker",
]
