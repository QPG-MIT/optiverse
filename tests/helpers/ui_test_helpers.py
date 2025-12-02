"""
Helper utilities for writing UI tests.

This module provides common patterns and utilities to make UI testing easier
and more consistent.
"""

from __future__ import annotations

import os
import unittest.mock as mock
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from PyQt6 import QtCore, QtGui, QtWidgets
from pytestqt.qtbot import QtBot

if TYPE_CHECKING:
    from optiverse.ui.views.component_editor_dialog import ComponentEditor
    from optiverse.ui.views.main_window import EditorMode, MainWindow

T = TypeVar("T")


def _is_headless_environment() -> bool:
    """Check if running in a headless environment where waitExposed might hang."""
    qpa_platform = os.environ.get("QT_QPA_PLATFORM", "").lower()
    return qpa_platform in ("offscreen", "minimal", "vnc")


def safe_wait_exposed(qtbot: QtBot, widget: QtWidgets.QWidget, timeout: int = 5000) -> None:
    """
    Wait for a widget to be exposed, with headless environment support.

    In headless environments (QT_QPA_PLATFORM=offscreen), waitExposed can hang
    indefinitely. This function uses a brief wait as a fallback.

    Args:
        qtbot: QtBot instance
        widget: Widget to wait for
        timeout: Timeout in milliseconds (ignored in headless mode)
    """
    if _is_headless_environment():
        # In headless mode, process events and give Qt a brief moment to settle
        QtWidgets.QApplication.processEvents()
        qtbot.wait(50)  # Brief wait to let Qt process pending events
        QtWidgets.QApplication.processEvents()
    else:
        qtbot.waitExposed(widget, timeout=timeout)


def create_main_window(qtbot: QtBot) -> MainWindow:  # type: ignore[valid-type]
    """
    Create and show a MainWindow for testing.

    Args:
        qtbot: QtBot instance from pytest fixture

    Returns:
        Configured MainWindow instance
    """
    from optiverse.ui.views.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    safe_wait_exposed(qtbot, window)
    return window


def create_component_editor(qtbot: QtBot) -> ComponentEditor:  # type: ignore[valid-type]
    """
    Create and show a ComponentEditor for testing.

    Args:
        qtbot: QtBot instance from pytest fixture

    Returns:
        Configured ComponentEditor instance
    """
    from optiverse.services.storage_service import StorageService
    from optiverse.ui.views.component_editor_dialog import ComponentEditor

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)
    editor.show()
    safe_wait_exposed(qtbot, editor)
    return editor


def add_source_to_window(window: MainWindow, x_mm: float = 0.0, y_mm: float = 0.0):  # type: ignore[valid-type]
    """
    Add a source to a MainWindow (for testing).

    Args:
        window: MainWindow instance
        x_mm: X position in mm
        y_mm: Y position in mm

    Returns:
        Created SourceItem
    """
    from PyQt6 import QtCore

    from optiverse.core.component_types import ComponentType

    return window.placement_handler.place_component_at(
        ComponentType.SOURCE, QtCore.QPointF(x_mm, y_mm)
    )


def add_lens_to_window(window: MainWindow, x_mm: float = 0.0, y_mm: float = 0.0):  # type: ignore[valid-type]
    """
    Add a lens to a MainWindow (for testing).

    Args:
        window: MainWindow instance
        x_mm: X position in mm
        y_mm: Y position in mm

    Returns:
        Created ComponentItem
    """
    from PyQt6 import QtCore

    from optiverse.core.component_types import ComponentType

    return window.placement_handler.place_component_at(
        ComponentType.LENS, QtCore.QPointF(x_mm, y_mm)
    )


def add_mirror_to_window(window: MainWindow, x_mm: float = 0.0, y_mm: float = 0.0):  # type: ignore[valid-type]
    """
    Add a mirror to a MainWindow (for testing).

    Args:
        window: MainWindow instance
        x_mm: X position in mm
        y_mm: Y position in mm

    Returns:
        Created ComponentItem
    """
    from PyQt6 import QtCore

    from optiverse.core.component_types import ComponentType

    return window.placement_handler.place_component_at(
        ComponentType.MIRROR, QtCore.QPointF(x_mm, y_mm)
    )


def mock_file_dialog_save(file_path: Path) -> mock.Mock:
    """
    Create a mock for QFileDialog.getSaveFileName that returns the given path.

    Args:
        file_path: Path to return from dialog

    Returns:
        Mock object ready to use in context manager
    """
    return mock.patch.object(
        QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(file_path), "")
    )


def mock_file_dialog_open(file_path: Path) -> mock.Mock:
    """
    Create a mock for QFileDialog.getOpenFileName that returns the given path.

    Args:
        file_path: Path to return from dialog

    Returns:
        Mock object ready to use in context manager
    """
    return mock.patch.object(
        QtWidgets.QFileDialog, "getOpenFileName", return_value=(str(file_path), "")
    )


def mock_file_dialog_cancel() -> mock.Mock:
    """
    Create a mock for file dialog that simulates cancel (empty path).

    Returns:
        Mock object ready to use in context manager
    """
    return mock.patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=("", ""))


def get_scene_items_by_type(scene: QtWidgets.QGraphicsScene, item_type: type[T]) -> list[T]:
    """
    Get all items of a specific type from a scene.

    Args:
        scene: QGraphicsScene to search
        item_type: Type of items to find

    Returns:
        List of items of the specified type
    """
    return [item for item in scene.items() if isinstance(item, item_type)]


def assert_item_count(
    scene: QtWidgets.QGraphicsScene, item_type: type[T], expected_count: int, tolerance: int = 0
) -> None:
    """
    Assert that scene contains expected number of items of a type.

    Args:
        scene: Scene to check
        item_type: Type of items to count
        expected_count: Expected number of items
        tolerance: Allowed deviation from expected count

    Raises:
        AssertionError: If count doesn't match
    """
    items = get_scene_items_by_type(scene, item_type)
    actual_count = len(items)
    assert abs(actual_count - expected_count) <= tolerance, (
        f"Expected {expected_count}±{tolerance} {item_type.__name__} items, got {actual_count}"
    )


def simulate_drag_and_drop(
    qtbot: QtBot,
    source_widget: QtWidgets.QWidget,
    target_widget: QtWidgets.QWidget,
    source_pos: QtCore.QPoint | None = None,
    target_pos: QtCore.QPoint | None = None,
) -> None:
    """
    Simulate drag and drop operation.

    Args:
        qtbot: QtBot instance
        source_widget: Widget to drag from
        target_widget: Widget to drop on
        source_pos: Position in source widget (defaults to center)
        target_pos: Position in target widget (defaults to center)
    """
    if source_pos is None:
        source_pos = source_widget.rect().center()
    if target_pos is None:
        target_pos = target_widget.rect().center()

    # Press mouse at source
    qtbot.mousePress(source_widget, QtCore.Qt.MouseButton.LeftButton, pos=source_pos)

    # Move to target
    qtbot.mouseMove(target_widget, pos=target_pos)

    # Release at target
    qtbot.mouseRelease(target_widget, QtCore.Qt.MouseButton.LeftButton, pos=target_pos)


def wait_for_signal(
    qtbot: QtBot, signal: QtCore.pyqtSignal, timeout: int = 5000
) -> QtCore.QSignalBlocker:
    """
    Wait for a signal to be emitted.

    Args:
        qtbot: QtBot instance
        signal: Signal to wait for
        timeout: Timeout in milliseconds

    Returns:
        Context manager for use in 'with' statement
    """
    return qtbot.waitSignal(signal, timeout=timeout)


def assert_property_matches(
    item: object, property_name: str, expected_value: any, tolerance: float | None = None
) -> None:
    """
    Assert that an item's property matches expected value.

    Args:
        item: Object with property
        property_name: Name of property (e.g., 'x_mm')
        expected_value: Expected value
        tolerance: Optional tolerance for float comparisons

    Raises:
        AssertionError: If property doesn't match
    """
    actual_value = getattr(item, property_name)

    if tolerance is not None and isinstance(expected_value, (int, float)):
        assert abs(actual_value - expected_value) <= tolerance, (
            f"{property_name}: expected {expected_value}±{tolerance}, got {actual_value}"
        )
    else:
        assert actual_value == expected_value, (
            f"{property_name}: expected {expected_value}, got {actual_value}"
        )


def assert_params_match(item: object, expected_params: dict, tolerance: float = 0.01) -> None:
    """
    Assert that an item's params match expected values.

    Args:
        item: Item with params attribute
        expected_params: Dictionary of param_name -> expected_value
        tolerance: Tolerance for float comparisons
    """
    params = item.params
    for param_name, expected_value in expected_params.items():
        assert_property_matches(params, param_name, expected_value, tolerance)


def trigger_action(qtbot: QtBot, action: QtGui.QAction) -> None:
    """
    Trigger a QAction programmatically.

    Args:
        qtbot: QtBot instance
        action: Action to trigger
    """
    action.trigger()


def simulate_keyboard_shortcut(
    qtbot: QtBot,
    widget: QtWidgets.QWidget,
    key: QtCore.Qt.Key,
    modifier: QtCore.Qt.KeyboardModifier = QtCore.Qt.KeyboardModifier.NoModifier,
) -> None:
    """
    Simulate a keyboard shortcut.

    Args:
        qtbot: QtBot instance
        widget: Widget to send key event to
        key: Key to press
        modifier: Keyboard modifier (Ctrl, Shift, etc.)
    """
    qtbot.keyClick(widget, key, modifier)


def wait_for_widget_visible(qtbot: QtBot, widget: QtWidgets.QWidget, timeout: int = 5000) -> None:
    """
    Wait for a widget to become visible.

    Args:
        qtbot: QtBot instance
        widget: Widget to wait for
        timeout: Timeout in milliseconds
    """
    safe_wait_exposed(qtbot, widget, timeout)


def get_widget_by_type(parent: QtWidgets.QWidget, widget_type: type[T]) -> T | None:
    """
    Find a widget of a specific type within a parent widget.

    Args:
        parent: Parent widget to search
        widget_type: Type of widget to find

    Returns:
        Found widget or None
    """
    widgets = parent.findChildren(widget_type)
    return widgets[0] if widgets else None


def assert_widget_enabled(widget: QtWidgets.QWidget, enabled: bool = True) -> None:
    """
    Assert that a widget is enabled or disabled.

    Args:
        widget: Widget to check
        enabled: Expected enabled state
    """
    assert widget.isEnabled() == enabled, (
        f"Widget {widget.__class__.__name__} enabled state: "
        f"expected {enabled}, got {widget.isEnabled()}"
    )


def assert_widget_visible(widget: QtWidgets.QWidget, visible: bool = True) -> None:
    """
    Assert that a widget is visible or hidden.

    Args:
        widget: Widget to check
        visible: Expected visible state
    """
    assert widget.isVisible() == visible, (
        f"Widget {widget.__class__.__name__} visible state: "
        f"expected {visible}, got {widget.isVisible()}"
    )


def create_test_image(width: int = 100, height: int = 100) -> QtGui.QPixmap:
    """
    Create a test image for use in tests.

    Args:
        width: Image width
        height: Image height

    Returns:
        QPixmap with test image
    """
    pixmap = QtGui.QPixmap(width, height)
    pixmap.fill(QtCore.Qt.GlobalColor.white)
    return pixmap


def is_lens_component(item: QtWidgets.QGraphicsItem) -> bool:
    """
    Check if a ComponentItem is a lens based on its interfaces.

    Args:
        item: Graphics item to check

    Returns:
        True if item is a ComponentItem with lens interfaces
    """
    from optiverse.objects import ComponentItem

    if not isinstance(item, ComponentItem):
        return False
    if not item.params.interfaces:
        return False
    return any(iface.element_type == "lens" for iface in item.params.interfaces)


def is_mirror_component(item: QtWidgets.QGraphicsItem) -> bool:
    """
    Check if a ComponentItem is a mirror based on its interfaces.

    Args:
        item: Graphics item to check

    Returns:
        True if item is a ComponentItem with mirror interfaces
    """
    from optiverse.objects import ComponentItem

    if not isinstance(item, ComponentItem):
        return False
    if not item.params.interfaces:
        return False
    return any(iface.element_type == "mirror" for iface in item.params.interfaces)


def is_beamsplitter_component(item: QtWidgets.QGraphicsItem) -> bool:
    """
    Check if a ComponentItem is a beamsplitter based on its interfaces.

    Args:
        item: Graphics item to check

    Returns:
        True if item is a ComponentItem with beamsplitter interfaces
    """
    from optiverse.objects import ComponentItem

    if not isinstance(item, ComponentItem):
        return False
    if not item.params.interfaces:
        return False
    return any(
        iface.element_type in ("beam_splitter", "beamsplitter") for iface in item.params.interfaces
    )


class UIStateChecker:
    """
    Helper class for checking UI state in tests.
    """

    def __init__(self, main_window: MainWindow):
        """
        Initialize checker with main window.

        Args:
            main_window: MainWindow instance to check
        """
        self.window = main_window

    def assert_mode(self, expected_mode: EditorMode) -> None:  # type: ignore[valid-type]
        """Assert current editor mode."""
        assert self.window.editor_state.mode == expected_mode, (
            f"Expected mode {expected_mode}, got {self.window.editor_state.mode}"
        )

    def assert_selection_count(self, expected_count: int) -> None:
        """Assert number of selected items."""
        selected = self.window.scene.selectedItems()
        assert len(selected) == expected_count, (
            f"Expected {expected_count} selected items, got {len(selected)}"
        )

    def assert_undo_enabled(self, enabled: bool = True) -> None:
        """Assert undo action enabled state."""
        assert self.window.act_undo.isEnabled() == enabled

    def assert_redo_enabled(self, enabled: bool = True) -> None:
        """Assert redo action enabled state."""
        assert self.window.act_redo.isEnabled() == enabled

    def assert_scene_item_count(self, item_type: type[T], expected_count: int) -> None:
        """Assert scene item count."""
        assert_item_count(self.window.scene, item_type, expected_count)
