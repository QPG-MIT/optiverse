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

    def test_lens_item_importable(self):
        """LensItem should be importable from objects."""
        try:
            from optiverse.objects import LensItem

            assert LensItem is not None
        except ImportError:
            pytest.fail("LensItem should be importable from optiverse.objects")

    def test_mirror_item_importable(self):
        """MirrorItem should be importable from objects."""
        try:
            from optiverse.objects import MirrorItem

            assert MirrorItem is not None
        except ImportError:
            pytest.fail("MirrorItem should be importable from optiverse.objects")

    def test_beamsplitter_item_importable(self):
        """BeamsplitterItem should be importable from objects."""
        try:
            from optiverse.objects import BeamsplitterItem

            assert BeamsplitterItem is not None
        except ImportError:
            pytest.fail("BeamsplitterItem should be importable from optiverse.objects")

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

    def test_subfolder_imports_work(self):
        """Should be able to import from subfolders directly."""
        try:
            from optiverse.objects.beamsplitters import BeamsplitterItem
            from optiverse.objects.lenses import LensItem
            from optiverse.objects.mirrors import MirrorItem

            from optiverse.objects.sources import SourceItem

            assert LensItem is not None
            assert MirrorItem is not None
            assert BeamsplitterItem is not None
            assert SourceItem is not None
        except ImportError as e:
            pytest.fail(f"Subfolder imports should work: {e}")

    def test_component_registry_importable(self):
        """ComponentRegistry should be importable."""
        try:
            from optiverse.objects.component_registry import ComponentRegistry

            assert ComponentRegistry is not None
        except ImportError:
            pytest.fail("ComponentRegistry should be importable")

    def test_no_circular_imports(self):
        """Importing objects module should not cause circular import errors."""
        try:
            # This should work without raising ImportError
            from optiverse.objects import (
                BaseObj,
                BeamsplitterItem,
                ComponentSprite,
                GraphicsView,
                ImageCanvas,
                LensItem,
                MirrorItem,
                RulerItem,
                SourceItem,
                TextNoteItem,
            )

            # All should be defined
            assert all(
                [
                    BaseObj,
                    LensItem,
                    MirrorItem,
                    BeamsplitterItem,
                    SourceItem,
                    GraphicsView,
                    RulerItem,
                    TextNoteItem,
                    ComponentSprite,
                    ImageCanvas,
                ]
            )
        except ImportError as e:
            pytest.fail(f"Circular import or import error detected: {e}")
