"""Regression tests for issue #103: layer rename persistence + duplicate auto-indexing.

Three rename defects are covered:
  1. A debounced panel refresh/selection-sync firing mid-edit tore down the inline
     editor before the typed name was committed (affected all item types).
  2. SourceParams had no ``name`` field, so a source rename wrote nowhere and reverted.
  3. TextNoteItem.display_name was not serialized, losing text renames on reload.

Plus the auto-indexing feature (``Lens`` -> ``Lens 2`` -> ``Lens 3``).
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6 import QtWidgets  # noqa: F401

    HAVE_PYQT6 = True
except ImportError:
    HAVE_PYQT6 = False

pytestmark = pytest.mark.skipif(not HAVE_PYQT6, reason="PyQt6 not available")


def _uuid_index(model, item):
    """Find the model index whose node maps to *item*."""
    from PyQt6 import QtCore

    for r in range(model.rowCount(QtCore.QModelIndex())):
        idx = model.index(r, 0, QtCore.QModelIndex())
        node = model._node_from_index(idx)
        if node and node.uuid == item.item_uuid:
            return idx
    raise AssertionError("item not found in model")


# --------------------------------------------------------------------------- #
# Defect 1 + 2: rename must survive a refresh/sync firing while the editor is
# open, and must persist for a source (whose name had nowhere to be stored).
# Renaming here drives the full model/view path: setData -> RenameNodeCommand.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind", ["source", "text"])
def test_rename_survives_refresh_and_sync_during_edit(qtbot, kind):
    from PyQt6 import QtCore

    from optiverse.core.layer_tree_state import LayerTreeState
    from optiverse.core.models import SourceParams
    from optiverse.objects.annotations.text_note_item import TextNoteItem
    from optiverse.objects.naming import item_label
    from optiverse.objects.sources.source_item import SourceItem
    from optiverse.ui.widgets.layer_panel import LayerPanel

    scene = QtWidgets.QGraphicsScene()
    item = SourceItem(SourceParams()) if kind == "source" else TextNoteItem("Text")
    scene.addItem(item)
    ls = LayerTreeState()
    ls.add_item(item.item_uuid, None, 0, emit=False)

    panel = LayerPanel()
    qtbot.addWidget(panel)
    panel.set_layer_state(ls)
    panel.set_scene(scene)

    tree, model = panel._tree, panel._model
    idx = _uuid_index(model, item)
    tree.setCurrentIndex(idx)
    tree.edit(idx)
    editor = tree.findChild(QtWidgets.QLineEdit)
    assert editor is not None
    editor.setText("Renamed")

    # These debounced callbacks previously tore down the editor mid-edit. With the
    # EditingState guard they must be no-ops while the editor is open.
    panel._do_sync_from_scene_selection()
    panel._do_refresh()
    assert tree.findChild(QtWidgets.QLineEdit) is not None  # editor survived

    tree.commitData(editor)
    tree.closeEditor(editor, QtWidgets.QAbstractItemDelegate.EndEditHint.SubmitModelCache)

    assert item_label(item) == "Renamed"
    assert model.data(idx, int(QtCore.Qt.ItemDataRole.DisplayRole)) == "Renamed"


# --------------------------------------------------------------------------- #
# Auto-indexing through real scene items (logic is unit-tested in
# tests/core/test_naming.py; this checks it against actual QGraphicsItems).
# --------------------------------------------------------------------------- #
def test_assign_unique_name_indexes_real_items(qtbot):
    from optiverse.core.models import SourceParams
    from optiverse.objects.naming import assign_unique_names, item_label
    from optiverse.objects.sources.source_item import SourceItem

    scene = QtWidgets.QGraphicsScene()
    original = SourceItem(SourceParams())
    scene.addItem(original)  # label "Source" already present

    batch = [SourceItem(SourceParams()), SourceItem(SourceParams())]
    assign_unique_names(scene, batch)  # simulates pasting/duplicating two clones

    assert [item_label(original), item_label(batch[0]), item_label(batch[1])] == [
        "Source",
        "Source 2",
        "Source 3",
    ]


# --------------------------------------------------------------------------- #
# Persistence round-trips (defects 2 & 3)
# --------------------------------------------------------------------------- #
def test_source_name_survives_serialization(qtbot):
    from optiverse.core.models import SourceParams
    from optiverse.objects.sources.source_item import SourceItem
    from optiverse.objects.type_registry import deserialize_item, serialize_item

    src = SourceItem(SourceParams())
    src.params.name = "Pump Laser"
    restored = deserialize_item(serialize_item(src))
    assert restored is not None
    assert restored.params.name == "Pump Laser"


def test_text_display_name_survives_serialization(qtbot):
    from optiverse.objects.annotations.text_note_item import TextNoteItem

    note = TextNoteItem("hello")
    note.display_name = "Collimator Label"
    restored = TextNoteItem.from_dict(note.to_dict())
    assert restored.display_name == "Collimator Label"


def test_clone_preserves_display_name_for_indexing(qtbot):
    """Duplicating a renamed text note keeps the custom name so it indexes on it."""
    from optiverse.objects.annotations.text_note_item import TextNoteItem
    from optiverse.objects.naming import assign_unique_names, item_label

    scene = QtWidgets.QGraphicsScene()
    original = TextNoteItem("body")
    original.display_name = "My Note"
    scene.addItem(original)

    clone = original.clone((10.0, 10.0))
    assert clone.display_name == "My Note"

    assign_unique_names(scene, [clone])
    assert item_label(clone) == "My Note 2"
