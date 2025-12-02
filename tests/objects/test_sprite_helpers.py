"""
Tests for sprite helper methods in BaseObj.

These methods make component sprites part of the clickable/selectable area,
not just the thin geometry lines.
"""

from PyQt6 import QtCore, QtGui

from optiverse.core.interface_definition import InterfaceDefinition
from optiverse.core.models import ComponentParams
from optiverse.objects import ComponentItem
from tests.fixtures.factories import create_lens_item, create_mirror_item


def _create_beamsplitter_item(
    x_mm: float = 0.0, y_mm: float = 0.0, angle_deg: float = 45.0, object_height_mm: float = 80.0
) -> ComponentItem:
    """Create a beamsplitter component for testing."""
    half_height = object_height_mm / 2.0
    interface = InterfaceDefinition(
        x1_mm=0.0,
        y1_mm=-half_height,
        x2_mm=0.0,
        y2_mm=half_height,
        element_type="beam_splitter",
        split_T=50.0,
        split_R=50.0,
    )
    params = ComponentParams(
        x_mm=x_mm,
        y_mm=y_mm,
        angle_deg=angle_deg,
        object_height_mm=object_height_mm,
        interfaces=[interface],
    )
    return ComponentItem(params)


class TestSpriteHelperMethods:
    """Test sprite helper methods in BaseObj."""

    def test_sprite_rect_in_item_no_sprite(self):
        """When no sprite exists, _sprite_rect_in_item should return None."""
        item = create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0)

        result = item._sprite_rect_in_item()
        assert result is None

    def test_bounds_union_sprite_without_sprite(self):
        """boundingRect should work without sprite."""
        item = create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0)

        # Should not crash
        bounds = item.boundingRect()
        assert isinstance(bounds, QtCore.QRectF)
        assert bounds.width() > 0
        assert bounds.height() > 0

    def test_shape_union_sprite_without_sprite(self):
        """shape() should work without sprite."""
        item = create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0)

        # Should not crash
        shape = item.shape()
        assert isinstance(shape, QtGui.QPainterPath)
        assert not shape.isEmpty()


class TestSpriteClickability:
    """Test that sprites are included in hit testing."""

    def test_lens_shape_includes_geometry(self):
        """Lens shape should include the line geometry."""
        item = create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0, object_height_mm=60.0)

        shape = item.shape()

        # Should contain points along the lens line
        assert shape.contains(QtCore.QPointF(0, 0))  # Center

    def test_mirror_shape_includes_geometry(self):
        """Mirror shape should include the line geometry."""
        item = create_mirror_item(x_mm=0, y_mm=0, angle_deg=0.0, object_height_mm=80.0)

        shape = item.shape()

        # Should contain center
        assert shape.contains(QtCore.QPointF(0, 0))

    def test_beamsplitter_shape_includes_geometry(self):
        """Beamsplitter shape should include the line geometry."""
        item = _create_beamsplitter_item(x_mm=0, y_mm=0, angle_deg=45.0, object_height_mm=80.0)

        shape = item.shape()

        # Should contain center
        assert shape.contains(QtCore.QPointF(0, 0))


class TestBoundsCalculation:
    """Test bounding rect calculations."""

    def test_lens_bounds_reasonable(self):
        """Lens bounding rect should be reasonable."""
        item = create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0, object_height_mm=60.0)

        bounds = item.boundingRect()

        # Should have some reasonable dimensions
        assert bounds.width() > 0
        assert bounds.height() > 0

    def test_mirror_bounds_reasonable(self):
        """Mirror bounding rect should be reasonable."""
        item = create_mirror_item(x_mm=0, y_mm=0, angle_deg=0.0, object_height_mm=80.0)

        bounds = item.boundingRect()

        # Should have some reasonable dimensions
        assert bounds.width() > 0
        assert bounds.height() > 0

    def test_beamsplitter_bounds_reasonable(self):
        """Beamsplitter bounding rect should be reasonable."""
        item = _create_beamsplitter_item(x_mm=0, y_mm=0, angle_deg=45.0, object_height_mm=80.0)

        bounds = item.boundingRect()

        # Should have some reasonable dimensions
        assert bounds.width() > 0
        assert bounds.height() > 0


class TestSpriteHelperIntegration:
    """Integration tests for sprite helpers."""

    def test_helper_methods_exist(self):
        """All element items should have sprite helper methods."""
        items = [
            create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0),
            create_mirror_item(x_mm=0, y_mm=0, angle_deg=0.0),
            _create_beamsplitter_item(x_mm=0, y_mm=0, angle_deg=45.0),
        ]

        for item in items:
            # All should have these helper methods
            assert hasattr(item, "_sprite_rect_in_item")
            assert hasattr(item, "_shape_union_sprite")
            assert hasattr(item, "_bounds_union_sprite")
            assert callable(item._sprite_rect_in_item)
            assert callable(item._shape_union_sprite)
            assert callable(item._bounds_union_sprite)

    def test_bounds_and_shape_dont_crash(self):
        """Calling boundingRect() and shape() should never crash."""
        items = [
            create_lens_item(x_mm=0, y_mm=0, angle_deg=90.0),
            create_mirror_item(x_mm=0, y_mm=0, angle_deg=0.0),
            _create_beamsplitter_item(x_mm=0, y_mm=0, angle_deg=45.0),
        ]

        for item in items:
            # Should not crash
            bounds = item.boundingRect()
            shape = item.shape()

            assert isinstance(bounds, QtCore.QRectF)
            assert isinstance(shape, QtGui.QPainterPath)
            assert bounds.isValid()
            assert not shape.isEmpty()
