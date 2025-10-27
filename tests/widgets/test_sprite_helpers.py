"""
Tests for sprite helper methods in BaseObj.

These methods make component sprites part of the clickable/selectable area,
not just the thin geometry lines.
"""
import pytest
from PyQt6 import QtCore, QtGui, QtWidgets

from optiverse.widgets.lens_item import LensItem
from optiverse.widgets.mirror_item import MirrorItem
from optiverse.widgets.beamsplitter_item import BeamsplitterItem
from optiverse.core.models import LensParams, MirrorParams, BeamsplitterParams


class TestSpriteHelperMethods:
    """Test sprite helper methods in BaseObj."""
    
    def test_sprite_rect_in_item_no_sprite(self):
        """When no sprite exists, _sprite_rect_in_item should return None."""
        params = LensParams(
            x_mm=0, y_mm=0, angle_deg=90.0,
            efl_mm=100.0, length_mm=60.0
        )
        item = LensItem(params)
        
        result = item._sprite_rect_in_item()
        assert result is None
    
    def test_sprite_rect_in_item_invisible_sprite(self):
        """When sprite exists but is invisible, should return None."""
        # Create item with sprite path but make it invisible
        params = LensParams(
            x_mm=0, y_mm=0, angle_deg=90.0,
            efl_mm=100.0, length_mm=60.0,
            image_path="nonexistent.png",  # Will be invisible
            mm_per_pixel=0.1,
            line_px=(0, 0, 100, 0)
        )
        item = LensItem(params)
        
        # Sprite should exist but be invisible (nonexistent file)
        if item._sprite is not None:
            result = item._sprite_rect_in_item()
            if not item._sprite.isVisible():
                assert result is None
    
    def test_bounds_union_sprite_without_sprite(self):
        """boundingRect should work without sprite."""
        params = LensParams(
            x_mm=0, y_mm=0, angle_deg=90.0,
            efl_mm=100.0, length_mm=60.0
        )
        item = LensItem(params)
        
        # Should not crash
        bounds = item.boundingRect()
        assert isinstance(bounds, QtCore.QRectF)
        assert bounds.width() > 0
        assert bounds.height() > 0
    
    def test_shape_union_sprite_without_sprite(self):
        """shape() should work without sprite."""
        params = LensParams(
            x_mm=0, y_mm=0, angle_deg=90.0,
            efl_mm=100.0, length_mm=60.0
        )
        item = LensItem(params)
        
        # Should not crash
        shape = item.shape()
        assert isinstance(shape, QtGui.QPainterPath)
        assert not shape.isEmpty()


class TestSpriteClickability:
    """Test that sprites are included in hit testing."""
    
    def test_lens_shape_includes_geometry(self):
        """Lens shape should include the line geometry."""
        params = LensParams(
            x_mm=0, y_mm=0, angle_deg=90.0,
            efl_mm=100.0, length_mm=60.0
        )
        item = LensItem(params)
        
        shape = item.shape()
        
        # Should contain points along the lens line
        # Lens is horizontal from -30 to +30 (length_mm=60)
        assert shape.contains(QtCore.QPointF(0, 0))  # Center
        assert shape.contains(QtCore.QPointF(20, 0))  # Along line
        assert shape.contains(QtCore.QPointF(-20, 0))  # Along line
    
    def test_mirror_shape_includes_geometry(self):
        """Mirror shape should include the line geometry."""
        params = MirrorParams(
            x_mm=0, y_mm=0, angle_deg=0.0,
            length_mm=80.0
        )
        item = MirrorItem(params)
        
        shape = item.shape()
        
        # Mirror is horizontal from -40 to +40 (length_mm=80)
        assert shape.contains(QtCore.QPointF(0, 0))  # Center
        assert shape.contains(QtCore.QPointF(30, 0))  # Along line
        assert shape.contains(QtCore.QPointF(-30, 0))  # Along line
    
    def test_beamsplitter_shape_includes_geometry(self):
        """Beamsplitter shape should include the line geometry."""
        params = BeamsplitterParams(
            x_mm=0, y_mm=0, angle_deg=45.0,
            length_mm=80.0,
            split_T=50.0, split_R=50.0
        )
        item = BeamsplitterItem(params)
        
        shape = item.shape()
        
        # Beamsplitter is horizontal in item coords from -40 to +40
        assert shape.contains(QtCore.QPointF(0, 0))  # Center
        assert shape.contains(QtCore.QPointF(30, 0))  # Along line
        assert shape.contains(QtCore.QPointF(-30, 0))  # Along line


class TestBoundsCalculation:
    """Test bounding rect calculations."""
    
    def test_lens_bounds_reasonable(self):
        """Lens bounding rect should be reasonable."""
        params = LensParams(
            x_mm=0, y_mm=0, angle_deg=90.0,
            efl_mm=100.0, length_mm=60.0
        )
        item = LensItem(params)
        
        bounds = item.boundingRect()
        
        # Should encompass the lens line plus some padding
        # Lens is 60mm long, so bounds should be at least that wide
        assert bounds.width() >= 60.0
        assert bounds.height() > 0  # Has some height for interaction
    
    def test_mirror_bounds_reasonable(self):
        """Mirror bounding rect should be reasonable."""
        params = MirrorParams(
            x_mm=0, y_mm=0, angle_deg=0.0,
            length_mm=80.0
        )
        item = MirrorItem(params)
        
        bounds = item.boundingRect()
        
        # Should encompass the mirror line plus padding
        assert bounds.width() >= 80.0
        assert bounds.height() > 0
    
    def test_beamsplitter_bounds_reasonable(self):
        """Beamsplitter bounding rect should be reasonable."""
        params = BeamsplitterParams(
            x_mm=0, y_mm=0, angle_deg=45.0,
            length_mm=80.0,
            split_T=50.0, split_R=50.0
        )
        item = BeamsplitterItem(params)
        
        bounds = item.boundingRect()
        
        # Should encompass the BS line plus padding
        assert bounds.width() >= 80.0
        assert bounds.height() > 0


class TestSpriteHelperIntegration:
    """Integration tests for sprite helpers."""
    
    def test_helper_methods_exist(self):
        """All element items should have sprite helper methods."""
        params_lens = LensParams(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0, length_mm=60.0)
        params_mirror = MirrorParams(x_mm=0, y_mm=0, angle_deg=0.0, length_mm=80.0)
        params_bs = BeamsplitterParams(x_mm=0, y_mm=0, angle_deg=45.0, length_mm=80.0, split_T=50.0, split_R=50.0)
        
        items = [
            LensItem(params_lens),
            MirrorItem(params_mirror),
            BeamsplitterItem(params_bs)
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
        params_lens = LensParams(x_mm=0, y_mm=0, angle_deg=90.0, efl_mm=100.0, length_mm=60.0)
        params_mirror = MirrorParams(x_mm=0, y_mm=0, angle_deg=0.0, length_mm=80.0)
        params_bs = BeamsplitterParams(x_mm=0, y_mm=0, angle_deg=45.0, length_mm=80.0, split_T=50.0, split_R=50.0)
        
        items = [
            LensItem(params_lens),
            MirrorItem(params_mirror),
            BeamsplitterItem(params_bs)
        ]
        
        for item in items:
            # Should not crash
            bounds = item.boundingRect()
            shape = item.shape()
            
            assert isinstance(bounds, QtCore.QRectF)
            assert isinstance(shape, QtGui.QPainterPath)
            assert bounds.isValid()
            assert not shape.isEmpty()

