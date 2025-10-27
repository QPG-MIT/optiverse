"""Tests for ComponentEditor (upgraded from ComponentEditorDialog)."""
import pytest

# Note: These tests require PyQt6 to be properly installed
try:
    from PyQt6 import QtGui, QtCore
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

    from optiverse.ui.views.component_editor_dialog import ComponentEditor
    from optiverse.services.storage_service import StorageService

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)

    # set fields
    editor.name_edit.setText("TestLens")
    editor.kind_combo.setCurrentText("lens")

    # prepare a dummy 100x100 image
    img = QtGui.QImage(100, 100, QtGui.QImage.Format.Format_ARGB32)
    img.fill(0)
    pix = QtGui.QPixmap.fromImage(img)
    editor.canvas.set_pixmap(pix)

    # set height 50mm => mm_per_px = 0.5
    editor.height_mm.setValue(50.0)
    # pick a 80px line
    editor.canvas.set_points((10.0, 50.0), (90.0, 50.0))

    # save
    editor.save_component()

    rows = StorageService().load_library()
    assert any(r.get("name") == "TestLens" for r in rows)
    rec = next(r for r in rows if r.get("name") == "TestLens")
    # length should be ~80px * 0.5 = 40mm
    assert abs(float(rec.get("length_mm", 0.0)) - 40.0) < 0.5
    # should have efl_mm for lens
    assert "efl_mm" in rec
    # should not have beamsplitter fields
    assert "split_TR" not in rec


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_component_editor_beamsplitter_fields(qtbot, tmp_path, monkeypatch):
    """Test beamsplitter T/R fields with auto-complement."""
    lib_path = tmp_path / "components_library.json"
    monkeypatch.setattr(
        "optiverse.platform.paths.get_library_path",
        lambda: str(lib_path),
        raising=True,
    )

    from optiverse.ui.views.component_editor_dialog import ComponentEditor
    from optiverse.services.storage_service import StorageService

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)

    # set to beamsplitter
    editor.kind_combo.setCurrentText("beamsplitter")
    
    # Check fields are visible
    assert editor.split_T.isVisible()
    assert editor.split_R.isVisible()
    assert not editor.efl_mm.isVisible()

    # Test auto-complement: set T=30, should set R=70
    editor.split_T.setValue(30.0)
    assert editor.split_R.value() == pytest.approx(70.0)

    # Test reverse: set R=25, should set T=75
    editor.split_R.setValue(25.0)
    assert editor.split_T.value() == pytest.approx(75.0)


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_component_editor_has_toolbar_actions(qtbot):
    """Test that component editor has toolbar with expected actions."""
    from optiverse.ui.views.component_editor_dialog import ComponentEditor
    from optiverse.services.storage_service import StorageService

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)

    # Check toolbar exists
    toolbars = editor.findChildren(type(editor.toolBarArea(QtCore.Qt.ToolBarArea.TopToolBarArea)))
    # MainWindow should have at least one toolbar
    assert len(editor.findChildren(type(editor.addToolBar("test")))) > 0

    # Check for key actions
    actions = [a.text() for a in editor.findChildren(type(editor.actions()[0])) if a.text()]
    action_texts = [a.lower() for a in actions]
    
    assert any("new" in t for t in action_texts)
    assert any("save" in t for t in action_texts)
    assert any("open" in t for t in action_texts)


@pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")
def test_component_editor_has_library_dock(qtbot):
    """Test that component editor has library dock."""
    from optiverse.ui.views.component_editor_dialog import ComponentEditor
    from optiverse.services.storage_service import StorageService

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
    from optiverse.ui.views.component_editor_dialog import ComponentEditor
    from optiverse.services.storage_service import StorageService

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

    from optiverse.ui.views.component_editor_dialog import ComponentEditor
    from optiverse.services.storage_service import StorageService

    editor = ComponentEditor(storage=StorageService())
    qtbot.addWidget(editor)

    # Setup component
    editor.name_edit.setText("SignalTest")
    img = QtGui.QImage(100, 100, QtGui.QImage.Format.Format_ARGB32)
    img.fill(0)
    pix = QtGui.QPixmap.fromImage(img)
    editor.canvas.set_pixmap(pix)
    editor.height_mm.setValue(50.0)
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
    from optiverse.ui.views.component_editor_dialog import ComponentEditorDialog
    from optiverse.services.storage_service import StorageService

    # Should be able to import and instantiate with old name
    editor = ComponentEditorDialog(storage=StorageService())
    qtbot.addWidget(editor)
    
    assert editor is not None
    assert hasattr(editor, "saved")  # New feature should be present
