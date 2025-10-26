from __future__ import annotations

from dataclasses import dataclass

from ...app.app_context import AppContext


@dataclass
class MainViewModel:
    ctx: AppContext

    @staticmethod
    def with_default_ctx() -> "MainViewModel":
        return MainViewModel(AppContext.create_default())


