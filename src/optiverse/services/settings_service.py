from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6 import QtCore


class SettingsService:
    # Maximum number of recent files to store
    MAX_RECENT_FILES = 10

    def __init__(self, organization: str = "PhotonicSandbox", application: str = "PhotonicSandbox"):
        self._settings = QtCore.QSettings(organization, application)

    def get_value(self, key: str, default: Any = None, value_type: type | None = None) -> Any:
        if value_type is not None:
            return self._settings.value(key, default, value_type)
        val = self._settings.value(key, default)
        # Best-effort coercion to default's type for common cases
        try:
            if isinstance(default, float) and isinstance(val, str):
                return float(val)
            if isinstance(default, int) and isinstance(val, str):
                return int(val)
        except (TypeError, ValueError):
            pass
        return val

    def set_value(self, key: str, value: Any) -> None:
        self._settings.setValue(key, value)

    # --- Recent Files ---

    def get_recent_files(self) -> list[str]:
        """
        Get list of recent file paths.

        Returns:
            List of file paths, most recent first. Only includes files that still exist.
        """
        files = self._settings.value("recent_files", [], list)
        if not isinstance(files, list):
            files = []
        # Filter out files that no longer exist
        existing = [f for f in files if Path(f).exists()]
        # If we filtered some out, update stored list
        if len(existing) != len(files):
            self._settings.setValue("recent_files", existing)
        return existing

    def add_recent_file(self, path: str) -> None:
        """
        Add a file path to the recent files list.

        The file is added at the front. If it already exists in the list,
        it is moved to the front. The list is trimmed to MAX_RECENT_FILES.

        Args:
            path: File path to add
        """
        # Normalize the path
        normalized = str(Path(path).resolve())
        files = self._settings.value("recent_files", [], list)
        if not isinstance(files, list):
            files = []
        # Remove if already present
        files = [f for f in files if f != normalized]
        # Add to front
        files.insert(0, normalized)
        # Trim to max
        files = files[: self.MAX_RECENT_FILES]
        self._settings.setValue("recent_files", files)

    def clear_recent_files(self) -> None:
        """Clear the recent files list."""
        self._settings.setValue("recent_files", [])
