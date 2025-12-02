"""Test right-click context menu on library components."""

import gc
import os

import pytest
from PyQt6 import QtCore, QtWidgets

from tests.helpers import safe_wait_exposed


def _is_headless():
    """Check if running in headless mode where context menus block."""
    qpa_platform = os.environ.get("QT_QPA_PLATFORM", "").lower()
    return qpa_platform in ("offscreen", "minimal", "vnc")


@pytest.fixture
def main_window(qapp, qtbot):
    """Create a MainWindow instance for testing with proper cleanup."""
    from optiverse.ui.views.main_window import MainWindow

    window = MainWindow()
    # Disable autotrace and stop timers to prevent hangs in CI
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    window.file_controller._autosave_timer.stop()
    QtWidgets.QApplication.processEvents()
    qtbot.addWidget(window)
    window.show()
    safe_wait_exposed(qtbot, window)
    yield window
    # Clean up
    window.autotrace = False
    window.raytracing_controller._retrace_timer.stop()
    window.file_controller._autosave_timer.stop()
    window.file_controller.mark_clean()
    window.raytracing_controller.clear_rays()
    for item in list(window.scene.items()):
        window.scene.removeItem(item)
    QtWidgets.QApplication.processEvents()
    window.close()
    QtWidgets.QApplication.processEvents()
    gc.collect()
    QtWidgets.QApplication.processEvents()


def test_library_tree_has_components(main_window, qtbot):
    """Test that library tree contains component items with valid data."""
    w = main_window

    # Find a component item in the library tree
    tree = w.libraryTree
    assert tree is not None

    # Wait for library to populate
    qtbot.wait(100)

    # Find first component item (not a category)
    component_item = None
    for i in range(tree.topLevelItemCount()):
        category = tree.topLevelItem(i)
        if category.childCount() > 0:
            component_item = category.child(0)
            break

    if component_item is None:
        pytest.skip("No components found in library")

    # Verify the item has component data
    payload = component_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
    assert payload is not None
    assert isinstance(payload, dict)


@pytest.mark.skipif(_is_headless(), reason="Context menu blocks in headless mode")
def test_library_context_menu_on_component(main_window, qtbot):
    """Test that right-clicking on a component shows context menu with Edit option.

    This test is skipped in headless environments because menu.exec() blocks.
    """
    w = main_window

    # Find a component item in the library tree
    tree = w.libraryTree
    assert tree is not None

    # Wait for library to populate
    qtbot.wait(100)

    # Find first component item (not a category)
    component_item = None
    for i in range(tree.topLevelItemCount()):
        category = tree.topLevelItem(i)
        if category.childCount() > 0:
            component_item = category.child(0)
            break

    if component_item is None:
        pytest.skip("No components found in library")

    # Verify the item has component data
    payload = component_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
    assert payload is not None
    assert isinstance(payload, dict)

    # Simulate context menu request
    # Get the position of the item
    rect = tree.visualItemRect(component_item)
    position = rect.center()

    # Call the context menu handler directly
    tree._show_context_menu(position)


def test_library_category_has_children(main_window, qtbot):
    """Test that library categories contain child component items."""
    w = main_window

    tree = w.libraryTree
    assert tree is not None

    # Wait for library to populate
    qtbot.wait(100)

    # Find a category item (one with children)
    category_item = None
    for i in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(i)
        if item.childCount() > 0:
            category_item = item
            break

    if category_item is None:
        pytest.skip("No categories found in library")

    # Verify it's a category (has children)
    assert category_item.childCount() > 0


@pytest.mark.skipif(_is_headless(), reason="Context menu blocks in headless mode")
def test_library_no_context_menu_on_category(main_window, qtbot):
    """Test that right-clicking on a category header doesn't show component menu.

    This test is skipped in headless environments because menu.exec() blocks.
    """
    w = main_window

    tree = w.libraryTree
    assert tree is not None

    # Wait for library to populate
    qtbot.wait(100)

    # Find a category item (one with children)
    category_item = None
    for i in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(i)
        if item.childCount() > 0:
            category_item = item
            break

    if category_item is None:
        pytest.skip("No categories found in library")

    # Verify it's a category (has children)
    assert category_item.childCount() > 0

    # Get the position of the category item
    rect = tree.visualItemRect(category_item)
    position = rect.center()

    # Call the context menu handler directly - should not show menu
    # (no exception should be raised, it should just return early)
    tree._show_context_menu(position)


def test_open_component_editor(main_window, qtbot):
    """Test that opening component editor works."""
    w = main_window

    # Open component editor (without data)
    w.open_component_editor()

    # Verify editor opened
    assert hasattr(w, "_comp_editor")
    assert w._comp_editor is not None
    assert w._comp_editor.isVisible()

    # Clean up
    w._comp_editor.close()
