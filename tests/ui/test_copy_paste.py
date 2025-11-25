"""
Tests for copy/paste functionality in the main window.
"""

import pytest
from tests.helpers.ui_test_helpers import (
    is_lens_component,
    is_mirror_component,
)


@pytest.fixture
def main_window(qtbot):
    """Create a main window for testing."""
    from optiverse.ui.views.main_window import MainWindow
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_copy_paste_single_source(main_window, qtbot):
    """Test copying and pasting a single source item."""
    from optiverse.core.models import SourceParams
    from optiverse.objects import SourceItem

    # Add a source item
    source = SourceItem(SourceParams(x_mm=100.0, y_mm=50.0))
    main_window.scene.addItem(source)

    # Select the source
    source.setSelected(True)

    # Copy
    main_window.copy_selected()
    assert len(main_window._clipboard) == 1
    assert main_window.act_paste.isEnabled()

    # Get initial item count
    initial_count = len([item for item in main_window.scene.items()
                        if isinstance(item, SourceItem)])

    # Paste
    main_window.paste_items()

    # Check that a new item was added
    new_count = len([item for item in main_window.scene.items()
                    if isinstance(item, SourceItem)])
    assert new_count == initial_count + 1

    # Check that the new item has an offset
    sources = [item for item in main_window.scene.items()
               if isinstance(item, SourceItem)]
    assert len(sources) == 2


def test_copy_paste_multiple_items(main_window, qtbot):
    """Test copying and pasting multiple items at once."""
    from optiverse.core.models import SourceParams, LensParams, MirrorParams
    from optiverse.objects import SourceItem
    from tests.fixtures.factories import create_component_from_params

    # Add multiple items
    source = SourceItem(SourceParams(x_mm=0.0, y_mm=0.0))
    lens = create_component_from_params(LensParams(x_mm=100.0, y_mm=0.0))
    mirror = create_component_from_params(MirrorParams(x_mm=200.0, y_mm=0.0))

    main_window.scene.addItem(source)
    main_window.scene.addItem(lens)
    main_window.scene.addItem(mirror)

    # Select all items
    source.setSelected(True)
    lens.setSelected(True)
    mirror.setSelected(True)

    # Copy
    main_window.copy_selected()
    assert len(main_window._clipboard) == 3

    # Get initial counts
    initial_sources = len([item for item in main_window.scene.items()
                          if isinstance(item, SourceItem)])
    initial_lenses = len([item for item in main_window.scene.items()
                         if is_lens_component(item)])
    initial_mirrors = len([item for item in main_window.scene.items()
                          if is_mirror_component(item)])

    # Paste
    main_window.paste_items()

    # Check that new items were added
    new_sources = len([item for item in main_window.scene.items()
                      if isinstance(item, SourceItem)])
    new_lenses = len([item for item in main_window.scene.items()
                     if is_lens_component(item)])
    new_mirrors = len([item for item in main_window.scene.items()
                      if is_mirror_component(item)])

    assert new_sources == initial_sources + 1
    assert new_lenses == initial_lenses + 1
    assert new_mirrors == initial_mirrors + 1


def test_paste_undo_redo(main_window, qtbot):
    """Test that paste operation can be undone and redone."""
    from optiverse.core.models import SourceParams
    from optiverse.objects import SourceItem

    # Add a source item
    source = SourceItem(SourceParams(x_mm=100.0, y_mm=50.0))
    main_window.scene.addItem(source)
    source.setSelected(True)

    # Copy
    main_window.copy_selected()

    # Get initial count
    initial_count = len([item for item in main_window.scene.items()
                        if isinstance(item, SourceItem)])

    # Paste
    main_window.paste_items()

    # Verify paste worked
    after_paste = len([item for item in main_window.scene.items()
                      if isinstance(item, SourceItem)])
    assert after_paste == initial_count + 1

    # Undo
    main_window.undo_stack.undo()

    # Verify undo worked
    after_undo = len([item for item in main_window.scene.items()
                     if isinstance(item, SourceItem)])
    assert after_undo == initial_count

    # Redo
    main_window.undo_stack.redo()

    # Verify redo worked
    after_redo = len([item for item in main_window.scene.items()
                     if isinstance(item, SourceItem)])
    assert after_redo == initial_count + 1


def test_copy_empty_selection(main_window, qtbot):
    """Test that copying with no selection doesn't crash."""
    # Clear any existing clipboard
    main_window._clipboard = []

    # Copy with no selection
    main_window.copy_selected()

    # Clipboard should be empty and paste should be disabled
    assert len(main_window._clipboard) == 0
    assert not main_window.act_paste.isEnabled()


def test_paste_preserves_properties(main_window, qtbot):
    """Test that pasted items preserve their properties."""
    from optiverse.core.models import SourceParams
    from optiverse.objects import SourceItem

    # Add a source with specific properties
    params = SourceParams(
        x_mm=100.0,
        y_mm=50.0,
        angle_deg=45.0,
        n_rays=15,
        size_mm=25.0,
        spread_deg=10.0,
        color_hex="#FF0000"
    )
    source = SourceItem(params)
    main_window.scene.addItem(source)
    source.setSelected(True)

    # Copy and paste
    main_window.copy_selected()
    main_window.paste_items()

    # Get the pasted item (should be selected after paste)
    pasted_items = [item for item in main_window.scene.selectedItems()
                   if isinstance(item, SourceItem)]
    assert len(pasted_items) == 1

    pasted = pasted_items[0]

    # Verify properties are preserved (except position which is offset)
    assert pasted.params.angle_deg == params.angle_deg
    assert pasted.params.n_rays == params.n_rays
    assert pasted.params.size_mm == params.size_mm
    assert pasted.params.spread_deg == params.spread_deg
    assert pasted.params.color_hex == params.color_hex

    # Verify position is offset
    assert pasted.params.x_mm == params.x_mm + 20.0
    assert pasted.params.y_mm == params.y_mm + 20.0


def test_keyboard_shortcuts(main_window, qtbot):
    """Test that Ctrl+C and Ctrl+V keyboard shortcuts work."""
    from PyQt6 import QtCore
    from optiverse.core.models import SourceParams
    from optiverse.objects import SourceItem

    # Add a source item
    source = SourceItem(SourceParams(x_mm=100.0, y_mm=50.0))
    main_window.scene.addItem(source)
    source.setSelected(True)

    # Simulate Ctrl+C
    qtbot.keyClick(main_window, QtCore.Qt.Key.Key_C, QtCore.Qt.KeyboardModifier.ControlModifier)
    assert len(main_window._clipboard) == 1

    # Get initial count
    initial_count = len([item for item in main_window.scene.items()
                        if isinstance(item, SourceItem)])

    # Simulate Ctrl+V
    qtbot.keyClick(main_window, QtCore.Qt.Key.Key_V, QtCore.Qt.KeyboardModifier.ControlModifier)

    # Verify paste worked
    new_count = len([item for item in main_window.scene.items()
                    if isinstance(item, SourceItem)])
    assert new_count == initial_count + 1



