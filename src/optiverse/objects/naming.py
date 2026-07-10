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


def _is_nameable(item: object) -> bool:
    """True for user-facing layer rows.

    Excludes autolabels (a ``TextNoteItem`` with an ``owner_uuid``), which show
    their owner's optical property and are not independently renameable — they
    must not take part in duplicate indexing or be counted as taken names.
    """
    return hasattr(item, "item_uuid") and getattr(item, "owner_uuid", None) is None


def assign_unique_name(
    scene: QtWidgets.QGraphicsScene, item: object, *, reserved: set[str] | None = None
) -> str:
    """Give *item* a duplicate-free label: ``Lens`` → ``Lens 2`` → ``Lens 3``.

    Compares the item's default label against every other named item already in
    *scene* (plus any names in *reserved*, used to keep a multi-item paste batch
    internally unique). The first element of a kind keeps its bare name; only
    collisions get a numeric suffix. Call on freshly created items *before*
    adding them to the scene. Returns the final label.
    """
    base = item_label(item)
    if not _is_nameable(item):
        return base
    existing = {
        item_label(other)
        for other in scene.items()
        if other is not item and _is_nameable(other)
    }
    if reserved:
        existing |= reserved
    if base not in existing:
        return base
    n = 2
    while f"{base} {n}" in existing:
        n += 1
    new_name = f"{base} {n}"
    set_item_label(item, new_name)
    return new_name


def assign_unique_names(scene: QtWidgets.QGraphicsScene, items: list[object]) -> None:
    """Auto-index a batch (e.g. a paste/duplicate) so it stays unique against the
    scene *and* against the rest of the batch. Autolabels are skipped."""
    taken: set[str] = set()
    for item in items:
        if not _is_nameable(item):
            continue
        taken.add(assign_unique_name(scene, item, reserved=taken))
