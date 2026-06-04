from pathlib import Path


def test_storage_library_roundtrip(tmp_path, monkeypatch):
    # Force paths under tmp
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    from optiverse.services.storage_service import StorageService

    svc = StorageService()
    comp = {
        "name": "lens100",
        "category": "lens",
        "image_path": str(tmp_path / "assets" / "img.png"),
        "mm_per_pixel": 0.1,
        "line_px": [0.0, 0.0, 10.0, 0.0],
        "length_mm": 60.0,
        "efl_mm": 100.0,
        "notes": "",
    }
    svc.save_library([comp])
    items = svc.load_library()
    assert isinstance(items, list)
    # Find our saved component in the loaded items
    matching = [item for item in items if item.get("name") == "lens100"]
    assert len(matching) >= 1
    assert matching[0]["name"] == "lens100"


def test_storage_roundtrips_attached_step_file(tmp_path):
    from optiverse.core.models import ComponentRecord
    from optiverse.services.storage_service import StorageService

    source_step = tmp_path / "model.step"
    source_step.write_text("ISO-10303-21 fake step content", encoding="utf-8")

    library = tmp_path / "library"
    library.mkdir()
    svc = StorageService(str(library))
    svc.save_component(ComponentRecord(name="STEP Component", step_file_path=str(source_step)))

    saved = svc.get_component("STEP Component")

    assert saved is not None
    saved_step = saved["step_file_path"]
    assert Path(saved_step).parts[-2:] == ("step", "model.step")
    assert (library / "step_component" / "step" / "model.step").is_file()

    loaded = svc.load_library()
    matching = [item for item in loaded if item.get("name") == "STEP Component"]
    assert len(matching) == 1
    assert matching[0]["step_file_path"] == saved_step


def test_storage_component_folders_are_deterministic(tmp_path):
    from optiverse.services.storage_service import StorageService

    library = tmp_path / "library"
    library.mkdir()
    for folder_name in ["z_component", "A_component", "m_component"]:
        folder = library / folder_name
        folder.mkdir(parents=True)
        (folder / "component.json").write_text("{}", encoding="utf-8")

    svc = StorageService(str(library))

    assert [folder.name for folder in svc._iter_component_folders()] == [
        "A_component",
        "m_component",
        "z_component",
    ]
