from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from ..core.models import ComponentRecord, deserialize_component

_logger = logging.getLogger(__name__)


def _library_root() -> Path:
    """Return the path to the built-in component library root under objects/library."""
    # src/optiverse/objects/library
    return Path(__file__).parent / "library"


def _iter_component_json_files(library_path: Path | None = None) -> list[Path]:
    """
    Find all component.json files one level under the library root.

    Args:
        library_path: Optional custom library path. If None, uses built-in library.

    Returns:
        List of Path objects to component folders
    """
    root = library_path if library_path else _library_root()
    if not root.exists():
        return []
    return [p for p in root.iterdir() if p.is_dir() and (p / "component.json").exists()]


def load_component_records(
    library_path: Path | None = None, settings_service=None
) -> list[ComponentRecord]:
    """
    Load components from per-object folders into typed ComponentRecord objects.
    Skips invalid or unreadable component definitions.

    Args:
        library_path: Optional custom library path. If None, uses built-in library.
        settings_service: Optional SettingsService for path resolution

    Returns:
        List of ComponentRecord objects
    """
    records: list[ComponentRecord] = []
    is_builtin = library_path is None

    for folder in _iter_component_json_files(library_path):
        json_path = folder / "component.json"
        try:
            with open(json_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)

            # Resolve image_path
            image_path = data.get("image_path")
            if isinstance(image_path, str) and image_path and not os.path.isabs(image_path):
                if is_builtin:
                    # Convert images/file.png -> objects/library/<component>/images/file.png
                    component_name = folder.name
                    package_relative = f"objects/library/{component_name}/{image_path}"
                    data["image_path"] = package_relative
                else:
                    # For user/custom libraries, make path absolute relative to component folder
                    abs_path = (folder / image_path).resolve()
                    data["image_path"] = str(abs_path)

            rec = deserialize_component(data, settings_service)
            if rec is not None:
                records.append(rec)
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as e:
            _logger.warning("Failed to load component from %s: %s", folder, e)
            continue
    return records


def load_component_records_from_multiple(
    library_paths: list[str | Path], settings_service=None
) -> list[ComponentRecord]:
    """
    Load components from multiple library paths.

    Args:
        library_paths: List of library directory paths

    Returns:
        Combined list of ComponentRecord objects from all libraries
    """
    all_records: list[ComponentRecord] = []

    for lib_path in library_paths:
        try:
            path = Path(lib_path) if isinstance(lib_path, str) else lib_path
            if path.exists() and path.is_dir():
                records = load_component_records(path, settings_service)
                all_records.extend(records)
        except OSError as e:
            _logger.warning("Failed to load library from %s: %s", lib_path, e)
            continue

    return all_records


def load_component_dicts(library_path: Path | None = None) -> list[dict[str, Any]]:
    """
    Load components and return them as JSON-serializable dicts.

    Note: Unlike serialize_component(), this preserves absolute image paths
    so that the library UI can load thumbnail icons.

    Args:
        library_path: Optional custom library path. If None, uses built-in library.

    Returns:
        List of component dictionaries
    """
    result: list[dict[str, Any]] = []
    for rec in load_component_records(library_path):
        try:
            # Create dict manually to preserve absolute image_path
            # (serialize_component() would convert to relative for portability)
            component_dict = {
                "name": rec.name,
                "image_path": rec.image_path,  # Keep absolute for UI thumbnails
                "object_height_mm": float(rec.object_height_mm),
                "angle_deg": float(rec.angle_deg),
                "notes": rec.notes or "",
            }

            # Include category if present
            if rec.category:
                component_dict["category"] = rec.category

            # Serialize interfaces
            if rec.interfaces:
                component_dict["interfaces"] = [iface.to_dict() for iface in rec.interfaces]

            result.append(component_dict)
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as e:
            _logger.warning("Failed to load component dict from %s: %s", folder, e)
            continue
    return result


def load_component_dicts_from_multiple(
    library_paths: list[str | Path],
) -> list[dict[str, Any]]:
    """
    Load components from multiple library paths as dictionaries.

    Args:
        library_paths: List of library directory paths

    Returns:
        Combined list of component dictionaries from all libraries
    """
    all_dicts: list[dict[str, Any]] = []

    for lib_path in library_paths:
        try:
            path = Path(lib_path) if isinstance(lib_path, str) else lib_path
            if path.exists() and path.is_dir():
                dicts = load_component_dicts(path)
                all_dicts.extend(dicts)
        except OSError as e:
            _logger.warning("Failed to load library dicts from %s: %s", lib_path, e)
            continue

    return all_dicts
