"""
Tests for MainWindow UI functionality.

These tests verify that the MainWindow opens correctly and has
all expected UI elements.
"""

from __future__ import annotations


def test_main_window_smoke(main_window):
    """Test that MainWindow opens with correct title."""
    # Title could be "Photonic Sandbox" or "2D Ray Optics Sandbox" depending on version
    title = main_window.windowTitle()
    assert "Sandbox" in title or "Optics" in title


def test_main_window_has_scene(main_window):
    """Test that MainWindow has a scene."""
    assert main_window.scene is not None


def test_main_window_has_view(main_window):
    """Test that MainWindow has a graphics view."""
    assert main_window.view is not None


def test_main_window_has_undo_stack(main_window):
    """Test that MainWindow has an undo stack."""
    assert main_window.undo_stack is not None


def test_main_window_has_toolbar(main_window):
    """Test that MainWindow has toolbars."""
    toolbars = main_window.findChildren(type(main_window.toolBar()))
    assert len(toolbars) > 0


def test_main_window_has_menu_bar(main_window):
    """Test that MainWindow has a menu bar."""
    menubar = main_window.menuBar()
    assert menubar is not None
    actions = menubar.actions()
    assert len(actions) > 0


def test_main_window_has_file_menu(main_window):
    """Test that File menu exists with expected actions."""
    menubar = main_window.menuBar()
    file_menu = None
    for action in menubar.actions():
        if action.text() == "&File":
            file_menu = action.menu()
            break

    assert file_menu is not None
    action_texts = [a.text() for a in file_menu.actions() if not a.isSeparator()]
    assert any("New" in t for t in action_texts)
    assert any("Open" in t for t in action_texts)
    assert any("Save" in t for t in action_texts)


def test_main_window_has_edit_menu(main_window):
    """Test that Edit menu exists with expected actions."""
    menubar = main_window.menuBar()
    edit_menu = None
    for action in menubar.actions():
        if action.text() == "&Edit":
            edit_menu = action.menu()
            break

    assert edit_menu is not None
    action_texts = [a.text() for a in edit_menu.actions() if not a.isSeparator()]
    assert "Undo" in action_texts
    assert "Redo" in action_texts
    assert "Delete" in action_texts


def test_main_window_has_view_menu(main_window):
    """Test that View menu exists."""
    menubar = main_window.menuBar()
    view_menu = None
    for action in menubar.actions():
        if action.text() == "&View":
            view_menu = action.menu()
            break

    assert view_menu is not None


def test_main_window_has_library_dock(main_window):
    """Test that library dock exists."""
    assert hasattr(main_window, "libDock")
    assert main_window.libDock is not None


def test_main_window_has_controllers(main_window):
    """Test that MainWindow has all required controllers."""
    assert hasattr(main_window, "raytracing_controller")
    assert hasattr(main_window, "file_controller")
    assert hasattr(main_window, "placement_handler")


def test_main_window_has_undo_redo_actions(main_window):
    """Test that undo/redo actions exist."""
    assert hasattr(main_window, "act_undo")
    assert hasattr(main_window, "act_redo")
    assert main_window.act_undo is not None
    assert main_window.act_redo is not None


def test_main_window_has_delete_action(main_window):
    """Test that delete action exists."""
    assert hasattr(main_window, "act_delete")
    assert main_window.act_delete is not None
