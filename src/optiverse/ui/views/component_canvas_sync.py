"""
Apply Component Editor / library records onto placed ComponentItem instances.

Shared by single-instance save-from-canvas and batch "update canvas instances".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.interface_definition import InterfaceDefinition
from ...core.models import ComponentRecord, serialize_component

if TYPE_CHECKING:
    from ...objects.generic.component_item import ComponentItem
    from ...services.settings_service import SettingsService


def normalized_component_name(name: str | None) -> str:
    """Strip and normalize for matching editor name to placed params.name."""
    return (name or "").strip()


def apply_record_to_component_item(
    item: ComponentItem,
    rec: ComponentRecord,
    settings_service: SettingsService | None,
) -> None:
    """Copy definition fields from *rec* onto *item* (pose and uuid unchanged).

    Mirrors the field updates in MainWindow.open_component_editor_for_item _apply_back.
    """
    serialized = serialize_component(rec, settings_service)

    if serialized.get("interfaces"):
        item.params.interfaces = [
            InterfaceDefinition.from_dict(d) for d in serialized["interfaces"]
        ]
    item.params.name = rec.name
    item.params.object_height_mm = rec.object_height_mm
    item.params.category = rec.category
    item.params.notes = rec.notes or ""
    if rec.image_path:
        item.params.image_path = rec.image_path
    item.params.step_file_path = rec.step_file_path or None

    item._update_geom()
    item._maybe_attach_sprite()
    item.edited.emit()
