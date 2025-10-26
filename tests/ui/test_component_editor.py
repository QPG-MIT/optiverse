from PyQt6 import QtGui


def test_component_editor_saves_to_library(qtbot, tmp_path, monkeypatch):
    # force library path to temp file
    lib_path = tmp_path / "components_library.json"
    monkeypatch.setattr(
        "optiverse.platform.paths.get_library_path",
        lambda: str(lib_path),
        raising=True,
    )

    from optiverse.ui.views.component_editor_dialog import ComponentEditorDialog
    from optiverse.services.storage_service import StorageService

    dlg = ComponentEditorDialog(storage=StorageService())
    qtbot.addWidget(dlg)

    # set fields
    dlg.name_edit.setText("TestLens")
    dlg.kind_combo.setCurrentText("lens")

    # prepare a dummy 100x100 image
    img = QtGui.QImage(100, 100, QtGui.QImage.Format.Format_ARGB32)
    img.fill(0)
    pix = QtGui.QPixmap.fromImage(img)
    dlg.canvas.set_pixmap(pix)

    # set height 50mm => mm_per_px = 0.5
    dlg.height_mm.setValue(50.0)
    # pick a 80px line
    dlg.canvas.set_points((10.0, 50.0), (90.0, 50.0))

    # save
    dlg._on_save()

    rows = StorageService().load_library()
    assert any(r.get("name") == "TestLens" for r in rows)
    rec = next(r for r in rows if r.get("name") == "TestLens")
    # length should be ~80px * 0.5 = 40mm
    assert abs(float(rec.get("length_mm", 0.0)) - 40.0) < 0.5


def test_open_editor_from_mainmenu(qtbot):
    from optiverse.ui.views.main_window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    # Ensure menu action exists
    acts = w.findChildren(type(w.menuBar().actions()[0]))
    assert any(a.text().lower().startswith("component editor") or a.text().lower().endswith("editor…") for a in w.menuBar().actions() or []) or hasattr(w, "open_component_editor")


