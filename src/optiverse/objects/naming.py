"""Shared helpers for the display names shown in the layer panel.

The label for a scene item is resolved the same way in three places (the layer
model, the rename command, and duplicate auto-indexing), so the logic lives here
once: ``display_name`` → ``params.name`` → prettified ``type_name``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6 import QtWidgets


def item_label(item: object) -> str:
    """Return the label shown for *item* in the layer panel.

    Mirrors ``LayerItemModel._get_item_name``: a custom ``display_name`` wins,
    then ``params.name``, then the item's ``type_name`` (prettified).
    """
    display_name = getattr(item, "display_name", None)
    if display_name:
        return str(display_name)
    params = getattr(item, "params", None)
    name = getattr(params, "name", None) if params is not None else None
    if name:
        return str(name)
    type_name = getattr(item, "type_name", None)
    return type_name.replace("_", " ").title() if type_name else "Item"


def set_item_label(item: object, name: str) -> None:
    """Write *name* to the item's rename target (``display_name`` or ``params.name``)."""
    if hasattr(item, "display_name"):
        item.display_name = name
        return
    params = getattr(item, "params", None)
    if params is not None and hasattr(params, "name"):
        params.name = name


def assign_unique_name(scene: QtWidgets.QGraphicsScene, item: object) -> None:
    """Give *item* a duplicate-free label: ``Lens`` → ``Lens 2`` → ``Lens 3``.

    Compares the item's default label against every other named item already in
    *scene*. The first element of a kind keeps its bare name; only collisions get
    a numeric suffix. Call this on freshly created items *before* adding them to
    the scene (the new item is excluded from the comparison either way).
    """
    base = item_label(item)
    existing = {
        item_label(other)
        for other in scene.items()
        if other is not item and hasattr(other, "item_uuid")
    }
    if base not in existing:
        return
    n = 2
    while f"{base} {n}" in existing:
        n += 1
    set_item_label(item, f"{base} {n}")
