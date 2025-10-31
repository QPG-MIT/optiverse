import json
import os
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
    assert items and items[0]["name"] == "lens100"


