"""
Tests for component placement from toolbar and library.

These tests verify that:
- All component types can be placed via toolbar
- Components can be placed from library drag-drop
- Placement respects snapping settings
- Components are correctly positioned
"""

from __future__ import annotations

import json

from PyQt6 import QtCore, QtGui, QtWidgets

from optiverse.core.component_types import ComponentType
from optiverse.core.constants import MIME_OPTICS_COMPONENT
from optiverse.objects import (
    ComponentItem,
    RulerItem,
    SourceItem,
    TextNoteItem,
)
from tests.helpers.ui_test_helpers import (
    is_beamsplitter_component,
    is_lens_component,
    is_mirror_component,
)


class TestToolbarPlacement:
    """Test placing components via toolbar/placement handler."""

    def test_place_source(self, main_window):
        """Test placing a source from toolbar."""
        initial_sources = len(
            [it for it in main_window.scene.items() if isinstance(it, SourceItem)]
        )

        pos = QtCore.QPointF(100.0, 50.0)
        item = main_window.placement_handler.place_component_at(ComponentType.SOURCE, pos)

        assert item is not None
        assert isinstance(item, SourceItem)

        # Check item was added to scene
        sources = [it for it in main_window.scene.items() if isinstance(it, SourceItem)]
        assert len(sources) == initial_sources + 1

        # Check position
        assert abs(item.pos().x() - pos.x()) < 1.0
        assert abs(item.pos().y() - pos.y()) < 1.0

    def test_place_lens(self, main_window):
        """Test placing a lens from toolbar."""
        initial_lenses = len([it for it in main_window.scene.items() if is_lens_component(it)])

        pos = QtCore.QPointF(200.0, 100.0)
        item = main_window.placement_handler.place_component_at(ComponentType.LENS, pos)

        assert item is not None
        assert is_lens_component(item)

        # Check item was added to scene
        lenses = [it for it in main_window.scene.items() if is_lens_component(it)]
        assert len(lenses) == initial_lenses + 1

    def test_place_mirror(self, main_window):
        """Test placing a mirror from toolbar."""
        initial_mirrors = len([it for it in main_window.scene.items() if is_mirror_component(it)])

        pos = QtCore.QPointF(300.0, 150.0)
        item = main_window.placement_handler.place_component_at(ComponentType.MIRROR, pos)

        assert item is not None
        assert is_mirror_component(item)

        # Check item was added to scene
        mirrors = [it for it in main_window.scene.items() if is_mirror_component(it)]
        assert len(mirrors) == initial_mirrors + 1

    def test_place_beamsplitter(self, main_window):
        """Test placing a beamsplitter from toolbar."""
        initial_bs = len([it for it in main_window.scene.items() if is_beamsplitter_component(it)])

        pos = QtCore.QPointF(400.0, 200.0)
        item = main_window.placement_handler.place_component_at(ComponentType.BEAMSPLITTER, pos)

        assert item is not None
        assert is_beamsplitter_component(item)

        # Check item was added to scene
        beamsplitters = [it for it in main_window.scene.items() if is_beamsplitter_component(it)]
        assert len(beamsplitters) == initial_bs + 1

    def test_place_dichroic(self, main_window):
        """Test placing a dichroic from toolbar."""

        def is_dichroic(item):
            if not isinstance(item, ComponentItem):
                return False
            if not item.params.interfaces:
                return False
            return any(iface.element_type == "dichroic" for iface in item.params.interfaces)

        initial_count = len([it for it in main_window.scene.items() if is_dichroic(it)])

        pos = QtCore.QPointF(500.0, 250.0)
        item = main_window.placement_handler.place_component_at(ComponentType.DICHROIC, pos)

        assert item is not None
        assert is_dichroic(item)

        # Check item was added to scene
        dichroics = [it for it in main_window.scene.items() if is_dichroic(it)]
        assert len(dichroics) == initial_count + 1

    def test_place_waveplate(self, main_window):
        """Test placing a waveplate from toolbar."""

        def is_waveplate(item):
            if not isinstance(item, ComponentItem):
                return False
            if not item.params.interfaces:
                return False
            return any(
                iface.element_type in ("waveplate", "polarizing_interface")
                for iface in item.params.interfaces
            )

        initial_count = len([it for it in main_window.scene.items() if is_waveplate(it)])

        pos = QtCore.QPointF(600.0, 300.0)
        item = main_window.placement_handler.place_component_at(ComponentType.WAVEPLATE, pos)

        assert item is not None

        # Check item was added to scene
        waveplates = [it for it in main_window.scene.items() if is_waveplate(it)]
        assert len(waveplates) == initial_count + 1

    def test_place_ruler(self, main_window):
        """Test placing a ruler from toolbar."""
        initial_rulers = len([it for it in main_window.scene.items() if isinstance(it, RulerItem)])

        pos = QtCore.QPointF(700.0, 350.0)
        item = main_window.placement_handler.place_component_at("ruler", pos)

        assert item is not None
        assert isinstance(item, RulerItem)

        # Check item was added to scene
        rulers = [it for it in main_window.scene.items() if isinstance(it, RulerItem)]
        assert len(rulers) == initial_rulers + 1

    def test_place_text(self, main_window):
        """Test placing a text note from toolbar."""
        initial_texts = len(
            [it for it in main_window.scene.items() if isinstance(it, TextNoteItem)]
        )

        pos = QtCore.QPointF(800.0, 400.0)
        item = main_window.placement_handler.place_component_at("text", pos)

        assert item is not None
        assert isinstance(item, TextNoteItem)

        # Check item was added to scene
        texts = [it for it in main_window.scene.items() if isinstance(it, TextNoteItem)]
        assert len(texts) == initial_texts + 1

    def test_placement_creates_undo_command(self, main_window):
        """Test that placement creates an undo command."""
        assert not main_window.undo_stack.can_undo()

        pos = QtCore.QPointF(100.0, 100.0)
        main_window.placement_handler.place_component_at(ComponentType.SOURCE, pos)

        assert main_window.undo_stack.can_undo()


class TestLibraryPlacement:
    """Test placing components from the library via drag-drop."""

    def test_drop_lens_from_library(self, main_window, qtbot):
        """Test dropping a lens component from library."""
        initial_lenses = len([it for it in main_window.scene.items() if is_lens_component(it)])

        # Create library record for a lens
        lens_record = {
            "category": "lens",
            "name": "Test Lens",
            "efl_mm": 100.0,
            "object_height_mm": 50.0,
            "angle_deg": 90.0,
            "image_path": "",
            "mm_per_pixel": 0.1,
            "interfaces": [
                {
                    "element_type": "lens",
                    "name": "Lens Surface",
                    "x1_mm": -25.0,
                    "y1_mm": 0.0,
                    "x2_mm": 25.0,
                    "y2_mm": 0.0,
                    "efl_mm": 100.0,
                }
            ],
        }

        # Simulate drop event
        drop_pos = QtCore.QPointF(200.0, 100.0)
        main_window.on_drop_component(lens_record, drop_pos)

        QtWidgets.QApplication.processEvents()

        # Check lens was added
        lenses = [it for it in main_window.scene.items() if is_lens_component(it)]
        assert len(lenses) == initial_lenses + 1

    def test_drop_mirror_from_library(self, main_window, qtbot):
        """Test dropping a mirror component from library."""
        initial_mirrors = len([it for it in main_window.scene.items() if is_mirror_component(it)])

        # Create library record for a mirror
        mirror_record = {
            "category": "mirror",
            "name": "Test Mirror",
            "object_height_mm": 60.0,
            "angle_deg": 45.0,
            "image_path": "",
            "mm_per_pixel": 0.1,
            "interfaces": [
                {
                    "element_type": "mirror",
                    "name": "Mirror Surface",
                    "x1_mm": -30.0,
                    "y1_mm": 0.0,
                    "x2_mm": 30.0,
                    "y2_mm": 0.0,
                }
            ],
        }

        # Simulate drop event
        drop_pos = QtCore.QPointF(300.0, 150.0)
        main_window.on_drop_component(mirror_record, drop_pos)

        QtWidgets.QApplication.processEvents()

        # Check mirror was added
        mirrors = [it for it in main_window.scene.items() if is_mirror_component(it)]
        assert len(mirrors) == initial_mirrors + 1

    def test_drop_beamsplitter_from_library(self, main_window, qtbot):
        """Test dropping a beamsplitter component from library."""
        initial_bs = len([it for it in main_window.scene.items() if is_beamsplitter_component(it)])

        # Create library record for a beamsplitter
        bs_record = {
            "category": "beamsplitter",
            "name": "50:50 BS",
            "object_height_mm": 50.0,
            "angle_deg": 45.0,
            "image_path": "",
            "mm_per_pixel": 0.1,
            "interfaces": [
                {
                    "element_type": "beam_splitter",
                    "name": "BS Surface",
                    "x1_mm": -25.0,
                    "y1_mm": 0.0,
                    "x2_mm": 25.0,
                    "y2_mm": 0.0,
                    "split_T": 50.0,
                    "split_R": 50.0,
                    "is_polarizing": False,
                }
            ],
        }

        # Simulate drop event
        drop_pos = QtCore.QPointF(400.0, 200.0)
        main_window.on_drop_component(bs_record, drop_pos)

        QtWidgets.QApplication.processEvents()

        # Check beamsplitter was added
        beamsplitters = [it for it in main_window.scene.items() if is_beamsplitter_component(it)]
        assert len(beamsplitters) == initial_bs + 1

    def test_drop_creates_undo_command(self, main_window, qtbot):
        """Test that dropping from library creates an undo command."""
        assert not main_window.undo_stack.can_undo()

        lens_record = {
            "category": "lens",
            "name": "Test Lens",
            "efl_mm": 100.0,
            "object_height_mm": 50.0,
            "angle_deg": 90.0,
            "image_path": "",
            "mm_per_pixel": 0.1,
            "interfaces": [
                {
                    "element_type": "lens",
                    "name": "Surface",
                    "x1_mm": -25.0,
                    "y1_mm": 0.0,
                    "x2_mm": 25.0,
                    "y2_mm": 0.0,
                    "efl_mm": 100.0,
                }
            ],
        }

        drop_pos = QtCore.QPointF(100.0, 100.0)
        main_window.on_drop_component(lens_record, drop_pos)

        QtWidgets.QApplication.processEvents()

        assert main_window.undo_stack.can_undo()

    def test_drag_enter_accepts_component_mime(self, main_window, qtbot):
        """Test that drag enter accepts component MIME data."""
        # Create MIME data with component
        lens_record = {
            "category": "lens",
            "name": "Test Lens",
            "efl_mm": 100.0,
            "object_height_mm": 50.0,
            "interfaces": [],
        }

        mime_data = QtCore.QMimeData()
        mime_data.setData(MIME_OPTICS_COMPONENT, json.dumps(lens_record).encode("utf-8"))

        # Create drag enter event
        event = QtGui.QDragEnterEvent(
            QtCore.QPoint(100, 100),
            QtCore.Qt.DropAction.CopyAction,
            mime_data,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )

        # Process event
        main_window.view.dragEnterEvent(event)

        # Event should be accepted
        assert event.isAccepted()


class TestPlacementWithSnapping:
    """Test that placement respects snapping settings."""

    def test_placement_with_snap_disabled(self, main_window):
        """Test placement without snapping."""
        # Disable snapping
        if hasattr(main_window, "settings_service"):
            main_window.settings_service.set_value("magnetic_snap", False)

        # Place at arbitrary position
        pos = QtCore.QPointF(123.456, 78.9)
        item = main_window.placement_handler.place_component_at(ComponentType.SOURCE, pos)

        # Position should be close to specified (might have some rounding)
        assert abs(item.pos().x() - pos.x()) < 5.0
        assert abs(item.pos().y() - pos.y()) < 5.0


class TestPlacementEdgeCases:
    """Test edge cases for component placement."""

    def test_place_multiple_same_type(self, main_window):
        """Test placing multiple components of the same type."""
        # Place 5 sources
        for i in range(5):
            pos = QtCore.QPointF(i * 100.0, 0.0)
            main_window.placement_handler.place_component_at(ComponentType.SOURCE, pos)

        sources = [it for it in main_window.scene.items() if isinstance(it, SourceItem)]
        assert len(sources) == 5

    def test_place_at_negative_coordinates(self, main_window):
        """Test placing component at negative coordinates."""
        pos = QtCore.QPointF(-500.0, -300.0)
        item = main_window.placement_handler.place_component_at(ComponentType.SOURCE, pos)

        assert item is not None
        assert item.pos().x() < 0
        assert item.pos().y() < 0

    def test_place_at_origin(self, main_window):
        """Test placing component at origin."""
        pos = QtCore.QPointF(0.0, 0.0)
        item = main_window.placement_handler.place_component_at(ComponentType.LENS, pos)

        assert item is not None
        assert abs(item.pos().x()) < 1.0
        assert abs(item.pos().y()) < 1.0

    def test_placement_followed_by_delete(self, main_window):
        """Test placing and then deleting a component."""
        pos = QtCore.QPointF(100.0, 100.0)
        item = main_window.placement_handler.place_component_at(ComponentType.MIRROR, pos)

        assert item in main_window.scene.items()

        # Select and delete
        item.setSelected(True)
        main_window.delete_selected()

        assert item not in main_window.scene.items()

    def test_placement_undo_redo_cycle(self, main_window):
        """Test complete undo/redo cycle for placement."""
        initial_count = len([it for it in main_window.scene.items() if isinstance(it, SourceItem)])

        pos = QtCore.QPointF(100.0, 100.0)
        main_window.placement_handler.place_component_at(ComponentType.SOURCE, pos)

        # Verify placed
        assert (
            len([it for it in main_window.scene.items() if isinstance(it, SourceItem)])
            == initial_count + 1
        )

        # Undo
        main_window.undo_stack.undo()
        assert (
            len([it for it in main_window.scene.items() if isinstance(it, SourceItem)])
            == initial_count
        )

        # Redo
        main_window.undo_stack.redo()
        assert (
            len([it for it in main_window.scene.items() if isinstance(it, SourceItem)])
            == initial_count + 1
        )
