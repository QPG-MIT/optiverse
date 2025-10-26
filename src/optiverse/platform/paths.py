from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6 import QtCore


def _app_data_root() -> Path:
    # Prefer Qt standard writable location
    base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.AppDataLocation)
    if not base:
        # Fallback to HOME
        home = os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path("~").expanduser())
        base = os.path.join(home, ".optiverse")
    root = Path(base) / "Optiverse"
    root.mkdir(parents=True, exist_ok=True)
    return root


def library_root_dir() -> str:
    root = _app_data_root() / "library"
    root.mkdir(parents=True, exist_ok=True)
    return str(root)


def assets_dir() -> str:
    d = Path(library_root_dir()) / "assets"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def get_library_path() -> str:
    return str(Path(library_root_dir()) / "components_library.json")


