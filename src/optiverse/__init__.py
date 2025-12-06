"""Optiverse: 2D ray-optics sandbox and component editor."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path


def _get_version() -> str:
    """Get the application version from pyproject.toml or package metadata."""
    # First try to read directly from pyproject.toml (most up-to-date during development)
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("version"):
                        # Parse: version = "0.2.8"
                        return line.split("=")[1].strip().strip('"')
    except Exception:
        pass
    # Fallback to installed package metadata
    try:
        return importlib.metadata.version("optiverse")
    except importlib.metadata.PackageNotFoundError:
        return "dev"


__version__ = _get_version()
__all__ = ["__version__"]
