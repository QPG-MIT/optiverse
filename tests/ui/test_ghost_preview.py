"""
Tests for ghost preview during drag/drop operations.

Ghost preview shows a semi-transparent preview of components when
dragging from the library to the canvas.
"""
import json
from unittest.mock import Mock, MagicMock

import pytest
from PyQt6 import QtCore, QtWidgets, QtGui

from optiverse.objects import GraphicsView, ComponentItem
from tests.helpers.ui_test_helpers import (
    is_lens_component,
    is_mirror_component,
    is_beamsplitter_component,
)


@pytest.fixture
def graphics_view(qtbot):
    """Create a GraphicsView with scene for testing."""
    scene = QtWidgets.QGraphicsScene()
    scene.setSceneRect(-600, -350, 1200, 700)
    view = GraphicsView(scene)
    qtbot.addWidget(view)
    return view


@pytest.fixture
def sample_lens_record():
    """Sample lens record for drag/drop testing."""
    return {
        "category": "lens",
        "name": "Test Lens",
        "efl_mm": 100.0,
        "length_mm": 60.0,
        "angle_deg": 90.0,
        "image_path": None,
        "mm_per_pixel": 0.1,
        "line_px": (0, 0, 100, 0),
    }


@pytest.fixture
def sample_mirror_record():
    """Sample mirror record for drag/drop testing."""
    return {
        "category": "mirror",
        "name": "Test Mirror",
        "length_mm": 80.0,
        "angle_deg": 0.0,
        "image_path": None,
        "mm_per_pixel": 0.1,
        "line_px": (0, 0, 100, 0),
    }


@pytest.fixture
def sample_beamsplitter_record():
    """Sample beamsplitter record for drag/drop testing."""
    return {
        "category": "beamsplitter",
        "name": "Test BS",
        "length_mm": 80.0,
        "angle_deg": 45.0,
        "split_T": 50.0,
        "split_R": 50.0,
        "image_path": None,
        "mm_per_pixel": 0.1,
        "line_px": (0, 0, 100, 0),
    }


class TestGhostPreviewState:
    """Test ghost preview state management."""

    def test_initial_state_no_ghost(self, graphics_view):
        """Initially, no ghost item should exist."""
        assert graphics_view._ghost_item is None
        assert graphics_view._ghost_rec is None

    def test_clear_ghost_when_no_ghost_exists(self, graphics_view):
        """Clearing ghost when none exists should not error."""
        graphics_view._clear_ghost()
        assert graphics_view._ghost_item is None
        assert graphics_view._ghost_rec is None

    def test_clear_ghost_removes_from_scene(self, graphics_view, sample_lens_record):
        """Clearing ghost should remove item from scene."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        # Ghost should exist
        assert graphics_view._ghost_item is not None
        assert graphics_view._ghost_item.scene() == graphics_view.scene()

        # Clear it
        graphics_view._clear_ghost()

        # Ghost should be gone
        assert graphics_view._ghost_item is None
        assert graphics_view._ghost_rec is None

    def test_make_ghost_creates_item(self, graphics_view, sample_lens_record):
        """Making ghost should create and add item to scene."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        assert graphics_view._ghost_item is not None
        assert graphics_view._ghost_item.scene() == graphics_view.scene()
        assert graphics_view._ghost_rec == sample_lens_record


class TestGhostPreviewProperties:
    """Test ghost item properties."""

    def test_ghost_is_non_interactive(self, graphics_view, sample_lens_record):
        """Ghost should not accept mouse events."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        ghost = graphics_view._ghost_item
        assert ghost.acceptedMouseButtons() == QtCore.Qt.MouseButton.NoButton

    def test_ghost_is_non_movable(self, graphics_view, sample_lens_record):
        """Ghost should not be movable by user."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        ghost = graphics_view._ghost_item
        flags = ghost.flags()
        assert not (flags & QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def test_ghost_is_non_selectable(self, graphics_view, sample_lens_record):
        """Ghost should not be selectable."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        ghost = graphics_view._ghost_item
        flags = ghost.flags()
        assert not (flags & QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

    def test_ghost_is_semi_transparent(self, graphics_view, sample_lens_record):
        """Ghost should have reduced opacity."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        ghost = graphics_view._ghost_item
        assert ghost.opacity() == 0.7

    def test_ghost_has_high_z_value(self, graphics_view, sample_lens_record):
        """Ghost should render on top of other items."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        ghost = graphics_view._ghost_item
        assert ghost.zValue() == 9999

    def test_ghost_positioned_at_scene_pos(self, graphics_view, sample_lens_record):
        """Ghost should be positioned at the specified scene position."""
        scene_pos = QtCore.QPointF(123, 456)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        ghost = graphics_view._ghost_item
        assert ghost.pos() == scene_pos


class TestGhostPreviewComponentTypes:
    """Test ghost creation for different component types."""

    def test_make_ghost_for_lens(self, graphics_view, sample_lens_record):
        """Should create LensItem ghost."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        ghost = graphics_view._ghost_item
        assert is_lens_component(ghost)
        assert len(ghost.params.interfaces) > 0
        assert ghost.params.interfaces[0].efl_mm == 100.0

    def test_make_ghost_for_mirror(self, graphics_view, sample_mirror_record):
        """Should create MirrorItem ghost."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_mirror_record, scene_pos)

        ghost = graphics_view._ghost_item
        assert is_mirror_component(ghost)

    def test_make_ghost_for_beamsplitter(self, graphics_view, sample_beamsplitter_record):
        """Should create BeamsplitterItem ghost."""
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_beamsplitter_record, scene_pos)

        ghost = graphics_view._ghost_item
        assert is_beamsplitter_component(ghost)
        assert len(ghost.params.interfaces) > 0
        assert ghost.params.interfaces[0].split_T == 50.0
        assert ghost.params.interfaces[0].split_R == 50.0


class TestGhostPreviewDragEvents:
    """Test ghost preview behavior during drag events."""

    def test_drag_enter_creates_ghost(self, graphics_view, sample_lens_record):
        """dragEnterEvent should create ghost preview."""
        # Create drag enter event with component mime data
        mime_data = QtCore.QMimeData()
        mime_data.setData(
            "application/x-optics-component",
            json.dumps(sample_lens_record).encode("utf-8")
        )

        event = QtGui.QDragEnterEvent(
            QtCore.QPoint(100, 100),
            QtCore.Qt.DropAction.CopyAction,
            mime_data,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )

        # Initially no ghost
        assert graphics_view._ghost_item is None

        # Process event
        graphics_view.dragEnterEvent(event)

        # Ghost should now exist
        assert graphics_view._ghost_item is not None
        assert is_lens_component(graphics_view._ghost_item)

    def test_drag_move_updates_ghost_position(self, graphics_view, sample_lens_record):
        """dragMoveEvent should move existing ghost."""
        # Create ghost first
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)

        # Create drag move event at different position
        mime_data = QtCore.QMimeData()
        mime_data.setData(
            "application/x-optics-component",
            json.dumps(sample_lens_record).encode("utf-8")
        )

        event = QtGui.QDragMoveEvent(
            QtCore.QPoint(200, 200),
            QtCore.Qt.DropAction.CopyAction,
            mime_data,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )

        # Process event
        graphics_view.dragMoveEvent(event)

        # Ghost should have moved
        ghost = graphics_view._ghost_item
        # Convert view coordinates to scene coordinates
        expected_scene_pos = graphics_view.mapToScene(QtCore.QPoint(200, 200))
        assert ghost.pos() == expected_scene_pos

    def test_drag_leave_removes_ghost(self, graphics_view, sample_lens_record):
        """dragLeaveEvent should remove ghost."""
        # Create ghost first
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)
        assert graphics_view._ghost_item is not None

        # Create drag leave event
        event = QtGui.QDragLeaveEvent()

        # Process event
        graphics_view.dragLeaveEvent(event)

        # Ghost should be gone
        assert graphics_view._ghost_item is None

    def test_drop_removes_ghost(self, graphics_view, sample_lens_record):
        """dropEvent should remove ghost before creating real item."""
        # Create ghost first
        scene_pos = QtCore.QPointF(100, 100)
        graphics_view._make_ghost(sample_lens_record, scene_pos)
        assert graphics_view._ghost_item is not None

        # Create drop event
        mime_data = QtCore.QMimeData()
        mime_data.setData(
            "application/x-optics-component",
            json.dumps(sample_lens_record).encode("utf-8")
        )

        event = QtGui.QDropEvent(
            QtCore.QPointF(150, 150),
            QtCore.Qt.DropAction.CopyAction,
            mime_data,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )

        # Process event (need parent with on_drop_component method)
        mock_parent = Mock()
        mock_parent.on_drop_component = Mock()
        graphics_view.parent = lambda: mock_parent

        graphics_view.dropEvent(event)

        # Ghost should be cleared
        assert graphics_view._ghost_item is None


class TestGhostPreviewMemoryManagement:
    """Test that ghost preview doesn't leak memory."""

    def test_repeated_ghost_creation_cleanup(self, graphics_view, sample_lens_record):
        """Creating multiple ghosts should properly clean up previous ones."""
        scene = graphics_view.scene()

        # Create and clear multiple ghosts
        for i in range(10):
            scene_pos = QtCore.QPointF(i * 10, i * 10)
            graphics_view._make_ghost(sample_lens_record, scene_pos)
            assert graphics_view._ghost_item is not None

            graphics_view._clear_ghost()
            assert graphics_view._ghost_item is None

        # Scene should not accumulate ghost items
        # (All should have been properly removed)
        item_count = len(scene.items())
        assert item_count == 0, f"Scene has {item_count} items, expected 0"

    def test_ghost_cleanup_on_new_ghost_creation(self, graphics_view, sample_lens_record):
        """Creating new ghost should clean up old ghost automatically."""
        # Create first ghost
        graphics_view._make_ghost(sample_lens_record, QtCore.QPointF(100, 100))
        first_ghost = graphics_view._ghost_item

        # Create second ghost
        graphics_view._make_ghost(sample_lens_record, QtCore.QPointF(200, 200))
        second_ghost = graphics_view._ghost_item

        # Should be different objects
        assert first_ghost is not second_ghost

        # First ghost should be removed from scene
        assert first_ghost.scene() is None
        assert second_ghost.scene() == graphics_view.scene()


class TestGhostPreviewDefaultAngles:
    """Test that ghosts use correct default angles for each component type."""

    def test_lens_default_angle(self, graphics_view, sample_lens_record):
        """Lens ghost should default to 90 degrees."""
        rec = sample_lens_record.copy()
        rec.pop("angle_deg", None)  # Remove explicit angle

        graphics_view._make_ghost(rec, QtCore.QPointF(100, 100))
        ghost = graphics_view._ghost_item

        assert ghost.rotation() == 90.0

    def test_mirror_default_angle(self, graphics_view, sample_mirror_record):
        """Mirror ghost should default to 0 degrees."""
        rec = sample_mirror_record.copy()
        rec.pop("angle_deg", None)  # Remove explicit angle

        graphics_view._make_ghost(rec, QtCore.QPointF(100, 100))
        ghost = graphics_view._ghost_item

        assert ghost.rotation() == 0.0

    def test_beamsplitter_default_angle(self, graphics_view, sample_beamsplitter_record):
        """Beamsplitter ghost should default to 45 degrees."""
        rec = sample_beamsplitter_record.copy()
        rec.pop("angle_deg", None)  # Remove explicit angle

        graphics_view._make_ghost(rec, QtCore.QPointF(100, 100))
        ghost = graphics_view._ghost_item

        assert ghost.rotation() == 45.0



