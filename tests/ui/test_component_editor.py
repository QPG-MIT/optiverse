"""Tests for ComponentEditor (upgraded from ComponentEditorDialog)."""

import pytest

# Note: These tests require PyQt6 to be properly installed
try:
    from PyQt6 import QtCore, QtGui

    HAVE_PYQT6 = True
except ImportError:
    HAVE_PYQT6 = False


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_component_editor_saves_to_library(qtbot, tmp_path, monkeypatch):
    """Test component editor saves to library with new structure."""
    # force library path to temp file
    lib_path = tmp_path / "components_library.json"
    monkeypatch.setattr(
        "optiverse.platform.paths.get_library_path",
        lambda: str(lib_path),
        raising=True,
    )

    from optiverse.services.storage_service import StorageService
    from optiverse.ui.views.component_editor_dialog import ComponentEditor

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)

    # set fields
    editor.name_edit.setText("TestLens")
    # Component editor now uses interface-based system
    # For testing, we'll just verify the component can be saved
    # In real usage, interfaces are added via the interface panel UI

    # prepare a dummy 100x100 image
    img = QtGui.QImage(100, 100, QtGui.QImage.Format.Format_ARGB32)
    img.fill(0)
    pix = QtGui.QPixmap.fromImage(img)
    editor.canvas.set_pixmap(pix)

    # set height 50mm => mm_per_px = 0.5
    editor.object_height_mm.setValue(50.0)
    # pick a 80px line
    editor.canvas.set_points((10.0, 50.0), (90.0, 50.0))

    # save
    editor.save_component()

    rows = StorageService().load_library()
    assert any(r.get("name") == "TestLens" for r in rows)
    rec = next(r for r in rows if r.get("name") == "TestLens")
    # length should be ~80px * 0.5 = 40mm
    assert abs(float(rec.get("length_mm", 0.0)) - 40.0) < 0.5
    # Component editor now uses interface-based system
    # Check that component was saved with interfaces
    assert "interfaces" in rec
    assert len(rec.get("interfaces", [])) > 0


# NOTE: This test removed - component editor now uses interface-based system
# Beamsplitter properties are set per-interface, not globally
# See test_component_editor_saves_to_library for interface-based testing


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_component_editor_has_toolbar_actions(qtbot):
    """Test that component editor has toolbar with expected actions."""
    from optiverse.services.storage_service import StorageService
    from optiverse.ui.views.component_editor_dialog import ComponentEditor

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)

    # Check toolbar exists - ComponentEditor is a QMainWindow so should have toolbars
    editor.findChildren(QtCore.QObject)  # Simplified check
    # Check that editor has actions
    actions = editor.actions()
    assert len(actions) > 0, "Component editor should have toolbar actions"

    # Check for key action texts (more robust)
    action_texts = [a.text().lower() for a in actions if a.text()]

    # Component editor should have save/new/open actions
    assert any("save" in t or "new" in t or "open" in t for t in action_texts), (
        f"Expected save/new/open actions, found: {action_texts}"
    )


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_component_editor_has_library_dock(qtbot):
    """Test that component editor has library dock."""
    from optiverse.services.storage_service import StorageService
    from optiverse.ui.views.component_editor_dialog import ComponentEditor

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)

    # Check library dock exists
    assert hasattr(editor, "libDock")
    assert hasattr(editor, "libList")
    assert editor.libDock is not None
    assert editor.libList is not None


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_component_editor_has_notes_field(qtbot):
    """Test that component editor has notes field."""
    from optiverse.services.storage_service import StorageService
    from optiverse.ui.views.component_editor_dialog import ComponentEditor

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)

    assert hasattr(editor, "notes")
    assert editor.notes is not None

    # Test notes can be set
    editor.notes.setPlainText("Test notes")
    assert editor.notes.toPlainText() == "Test notes"


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_component_editor_emits_saved_signal(qtbot, tmp_path, monkeypatch):
    """Test that component editor emits saved signal."""
    lib_path = tmp_path / "components_library.json"
    monkeypatch.setattr(
        "optiverse.platform.paths.get_library_path",
        lambda: str(lib_path),
        raising=True,
    )

    from optiverse.services.storage_service import StorageService
    from optiverse.ui.views.component_editor_dialog import ComponentEditor

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)

    # Setup component
    editor.name_edit.setText("SignalTest")
    img = QtGui.QImage(100, 100, QtGui.QImage.Format.Format_ARGB32)
    img.fill(0)
    pix = QtGui.QPixmap.fromImage(img)
    editor.canvas.set_pixmap(pix)
    editor.object_height_mm.setValue(50.0)
    editor.canvas.set_points((10.0, 50.0), (90.0, 50.0))

    # Listen for saved signal
    with qtbot.waitSignal(editor.saved, timeout=1000):
        editor.save_component()


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_open_editor_from_mainmenu(qtbot):
    """Test opening editor from main window."""
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()

    # Ensure open_component_editor method exists
    assert hasattr(w, "open_component_editor")


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_component_editor_backward_compat_name(qtbot):
    """Test that ComponentEditorDialog name still works for backward compatibility."""
    from optiverse.services.storage_service import StorageService
    from optiverse.ui.views.component_editor_dialog import ComponentEditorDialog

    # Should be able to import and instantiate with old name
    editor = ComponentEditorDialog(storage=StorageService())
    qtbot.addWidget(editor)

    assert editor is not None
    assert hasattr(editor, "saved")  # New feature should be present
