"""
Tests for objects module import structure.

Verifies that the new objects folder structure has correct imports
and all classes are accessible.
"""

import pytest


class TestObjectsImports:
    """Test that objects module has proper import structure."""

    def test_objects_module_exists(self):
        """The objects module should exist."""
        try:
            import optiverse.objects

            assert optiverse.objects is not None
        except ImportError:
            pytest.fail("optiverse.objects module should exist")

    def test_base_obj_importable(self):
        """BaseObj should be importable from objects."""
        try:
            from optiverse.objects import BaseObj

            assert BaseObj is not None
        except ImportError:
            pytest.fail("BaseObj should be importable from optiverse.objects")

    def test_component_item_importable(self):
        """ComponentItem should be importable from objects."""
        try:
            from optiverse.objects import ComponentItem

            assert ComponentItem is not None
        except ImportError:
            pytest.fail("ComponentItem should be importable from optiverse.objects")

    def test_source_item_importable(self):
        """SourceItem should be importable from objects."""
        try:
            from optiverse.objects import SourceItem

            assert SourceItem is not None
        except ImportError:
            pytest.fail("SourceItem should be importable from optiverse.objects")

    def test_graphics_view_importable(self):
        """GraphicsView should be importable from objects."""
        try:
            from optiverse.objects import GraphicsView

            assert GraphicsView is not None
        except ImportError:
            pytest.fail("GraphicsView should be importable from optiverse.objects")

    def test_ruler_item_importable(self):
        """RulerItem should be importable from objects."""
        try:
            from optiverse.objects import RulerItem

            assert RulerItem is not None
        except ImportError:
            pytest.fail("RulerItem should be importable from optiverse.objects")

    def test_text_note_item_importable(self):
        """TextNoteItem should be importable from objects."""
        try:
            from optiverse.objects import TextNoteItem

            assert TextNoteItem is not None
        except ImportError:
            pytest.fail("TextNoteItem should be importable from optiverse.objects")

    def test_component_sprite_importable(self):
        """ComponentSprite should be importable from objects."""
        try:
            from optiverse.objects import ComponentSprite

            assert ComponentSprite is not None
        except ImportError:
            pytest.fail("ComponentSprite should be importable from optiverse.objects")

    def test_image_canvas_importable(self):
        """ImageCanvas should be importable from objects."""
        try:
            from optiverse.objects import ImageCanvas

            assert ImageCanvas is not None
        except ImportError:
            pytest.fail("ImageCanvas should be importable from optiverse.objects")

    def test_component_factory_importable(self):
        """ComponentFactory should be importable from objects."""
        try:
            from optiverse.objects import ComponentFactory

            assert ComponentFactory is not None
        except ImportError:
            pytest.fail("ComponentFactory should be importable from optiverse.objects")

    def test_subfolder_imports_work(self):
        """Should be able to import from subfolders directly."""
        try:
            from optiverse.objects.generic import ComponentItem
            from optiverse.objects.sources import SourceItem

            assert SourceItem is not None
            assert ComponentItem is not None
        except ImportError as e:
            pytest.fail(f"Subfolder imports should work: {e}")

    def test_no_circular_imports(self):
        """Importing objects module should not cause circular import errors."""
        try:
            # This should work without raising ImportError
            from optiverse.objects import (
                BaseObj,
                ComponentFactory,
                ComponentItem,
                ComponentSprite,
                GraphicsView,
                ImageCanvas,
                RulerItem,
                SourceItem,
                TextNoteItem,
            )

            # All should be defined
            assert all(
                [
                    BaseObj,
                    ComponentItem,
                    SourceItem,
                    GraphicsView,
                    RulerItem,
                    TextNoteItem,
                    ComponentSprite,
                    ImageCanvas,
                    ComponentFactory,
                ]
            )
        except ImportError as e:
            pytest.fail(f"Circular import or import error detected: {e}")
