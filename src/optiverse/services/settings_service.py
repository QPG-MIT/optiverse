from __future__ import annotations

from typing import Any

from PyQt6 import QtCore


class SettingsService:
    def __init__(self, organization: str = "PhotonicSandbox", application: str = "PhotonicSandbox"):
        self._settings = QtCore.QSettings(organization, application)

    def get_value(self, key: str, default: Any = None, value_type: type | None = None) -> Any:
        if value_type is not None:
            return self._settings.value(key, default, value_type)  # type: ignore[arg-type]
        val = self._settings.value(key, default)
        # Best-effort coercion to default's type for common cases
        try:
            if isinstance(default, float) and isinstance(val, str):
                return float(val)
            if isinstance(default, int) and isinstance(val, str):
                return int(val)
        except Exception:
            pass
        return val

    def set_value(self, key: str, value: Any) -> None:
        self._settings.setValue(key, value)


