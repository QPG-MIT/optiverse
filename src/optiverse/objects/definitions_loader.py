from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..core.models import ComponentRecord, deserialize_component, serialize_component
import os


def _library_root() -> Path:
    """Return the path to the built-in component library root under objects/library."""
    # src/optiverse/objects/library
    return Path(__file__).parent / "library"


def _iter_component_json_files() -> List[Path]:
    """Find all component.json files one level under the library root."""
    root = _library_root()
    if not root.exists():
        return []
    return [p for p in root.iterdir() if p.is_dir() and (p / "component.json").exists()]


def load_component_records() -> List[ComponentRecord]:
    """
    Load all standard components from per-object folders into typed ComponentRecord objects.
    Skips invalid or unreadable component definitions.
    """
    records: List[ComponentRecord] = []
    for folder in _iter_component_json_files():
        json_path = folder / "component.json"
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            # Resolve image_path to package-relative format if it's relative
            image_path = data.get("image_path")
            if isinstance(image_path, str) and image_path and not os.path.isabs(image_path):
                # Convert images/file.png -> objects/library/<component>/images/file.png
                component_name = folder.name
                package_relative = f"objects/library/{component_name}/{image_path}"
                data["image_path"] = package_relative
            rec = deserialize_component(data)
            if rec is not None:
                records.append(rec)
        except Exception:
            # Ignore malformed entries silently for now
            continue
    return records


def load_component_dicts() -> List[Dict[str, Any]]:
    """
    Load all standard components and return them as JSON-serializable dicts.
    
    Note: Unlike serialize_component(), this preserves absolute image paths
    so that the library UI can load thumbnail icons.
    """
    result: List[Dict[str, Any]] = []
    for rec in load_component_records():
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
        except Exception:
            continue
    return result


