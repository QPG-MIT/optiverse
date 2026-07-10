"""Unit tests for layer-name resolution and duplicate auto-indexing (issue #103).

These exercise ``optiverse.objects.naming`` with lightweight duck-typed fakes so
they run without a QApplication (and therefore in the headless CI suite, which
skips ``tests/ui``). The Qt model/view and serialization integration is covered
separately in ``tests/ui/test_layer_rename_and_autoindex.py``.
"""

from __future__ import annotations

from types import SimpleNamespace

from optiverse.objects.naming import (
    assign_unique_name,
    assign_unique_names,
    item_label,
    set_item_label,
)

_uid = 0


def _next_uuid() -> str:
    global _uid
    _uid += 1
    return f"uuid-{_uid}"


class FakeScene:
    """Minimal stand-in for QGraphicsScene exposing ``items()``."""

    def __init__(self, items=()):
        self._items = list(items)

    def items(self):
        return list(self._items)

    def add(self, item):
        self._items.append(item)
        return item


def component(name=None):
    """Component-like item: label comes from ``params.name`` (falls back to type)."""
    return SimpleNamespace(
        item_uuid=_next_uuid(),
        params=SimpleNamespace(name=name),
        type_name="component",
        owner_uuid=None,
    )


def text(display_name=None, owner_uuid=None):
    """Text-like item: label comes from ``display_name`` (falls back to type)."""
    return SimpleNamespace(
        item_uuid=_next_uuid(),
        display_name=display_name,
        type_name="text",
        owner_uuid=owner_uuid,
    )


# --- label resolution -------------------------------------------------------
def test_item_label_resolution_order():
    assert item_label(text(display_name="Custom")) == "Custom"
    assert item_label(component(name="Achromat")) == "Achromat"
    assert item_label(component(name=None)) == "Component"  # type_name fallback
    assert item_label(SimpleNamespace(type_name="beam_source")) == "Beam Source"


def test_set_item_label_targets_the_right_field():
    t = text()
    set_item_label(t, "Note A")
    assert t.display_name == "Note A"

    c = component(name="Lens")
    set_item_label(c, "Lens 2")
    assert c.params.name == "Lens 2"


# --- single-add auto-indexing ----------------------------------------------
def test_first_of_a_kind_keeps_bare_name():
    scene = FakeScene()
    c = component("Lens")
    assert assign_unique_name(scene, c) == "Lens"
    assert c.params.name == "Lens"  # unchanged


def test_sequential_adds_increment():
    scene = FakeScene()
    labels = []
    for _ in range(3):
        c = component("Lens")
        assign_unique_name(scene, c)
        scene.add(c)
        labels.append(item_label(c))
    assert labels == ["Lens", "Lens 2", "Lens 3"]


def test_gap_is_refilled():
    scene = FakeScene()
    kept = []
    for _ in range(3):  # Lens, Lens 2, Lens 3
        c = component("Lens")
        assign_unique_name(scene, c)
        scene.add(c)
        kept.append(c)
    scene._items.remove(kept[1])  # drop "Lens 2"

    c = component("Lens")
    assign_unique_name(scene, c)
    assert item_label(c) == "Lens 2"


# --- batch (paste / duplicate) auto-indexing --------------------------------
def test_batch_is_unique_against_scene_and_itself():
    scene = FakeScene([component("Lens")])  # scene already has "Lens"
    batch = [component("Lens"), component("Lens")]
    assign_unique_names(scene, batch)
    assert [item_label(b) for b in batch] == ["Lens 2", "Lens 3"]


def test_batch_of_distinct_kinds():
    scene = FakeScene([component("Lens"), component("Mirror")])
    batch = [component("Lens"), component("Mirror")]
    assign_unique_names(scene, batch)
    assert [item_label(b) for b in batch] == ["Lens 2", "Mirror 2"]


# --- autolabels are excluded ------------------------------------------------
def test_autolabel_not_counted_as_taken():
    scene = FakeScene([text(owner_uuid="owner-1")])  # autolabel resolves to "Text"
    note = text()
    assign_unique_name(scene, note)
    assert item_label(note) == "Text"  # not bumped to "Text 2"


def test_autolabel_in_batch_is_left_untouched():
    scene = FakeScene()
    autolabel = text(owner_uuid="owner-2")
    note = text()
    assign_unique_names(scene, [autolabel, note])
    assert autolabel.display_name is None  # never renamed
    assert item_label(note) == "Text"
