from __future__ import annotations

from dataclasses import dataclass

from ..services.settings_service import SettingsService
from ..services.storage_service import StorageService


@dataclass
class AppContext:
    settings: SettingsService
    storage: StorageService

    @staticmethod
    def create_default() -> AppContext:
        return AppContext(
            settings=SettingsService(),
            storage=StorageService(),
        )
