from __future__ import annotations

import json
import os
from typing import List, Dict, Any

from ..platform.paths import get_library_path


class StorageService:
    def __init__(self):
        self._lib_path = get_library_path()

    def load_library(self) -> List[Dict[str, Any]]:
        path = self._lib_path
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
        except Exception:
            return []

    def save_library(self, rows: List[Dict[str, Any]]) -> None:
        tmp = self._lib_path + ".tmp"
        os.makedirs(os.path.dirname(self._lib_path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
        os.replace(tmp, self._lib_path)


