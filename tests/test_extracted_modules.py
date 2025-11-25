"""
Smoke tests for newly extracted modules.

These tests verify that the extracted modules can be imported
and their classes instantiated without errors.
"""

from __future__ import annotations


class TestExtractedModulesImport:
    """Verify that extracted modules can be imported."""

    def test_import_log_categories(self):
        """Test that LogCategory can be imported."""
        from optiverse.core.log_categories import LogCategory

        assert hasattr(LogCategory, "COLLABORATION")
        assert hasattr(LogCategory, "RAYTRACING")
        assert hasattr(LogCategory, "COPY_PASTE")

    def test_import_zorder_utils(self):
        """Test that z-order utilities can be imported."""
        from optiverse.core.zorder_utils import (
            apply_z_order_change,
            get_z_order_items_from_item,
            handle_z_order_from_menu,
        )

        # Verify the functions are callable
        assert callable(apply_z_order_change)
        assert callable(handle_z_order_from_menu)
        assert callable(get_z_order_items_from_item)

    def test_import_protocols(self):
        """Test that new protocols can be imported."""
        from optiverse.core.protocols import (
            HasCollaboration,
            HasSettings,
            HasSnapping,
            HasUndoStack,
        )

        # Verify these are runtime checkable protocols
        assert hasattr(HasUndoStack, "__protocol_attrs__")
        assert hasattr(HasCollaboration, "__protocol_attrs__")
        assert hasattr(HasSettings, "__protocol_attrs__")
        assert hasattr(HasSnapping, "__protocol_attrs__")

    def test_import_constants(self):
        """Test that MIME type constants are available."""
        from optiverse.core.constants import MIME_OPTICS_COMPONENT

        assert MIME_OPTICS_COMPONENT == "application/x-optics-component"


class TestLogCategory:
    """Test LogCategory class."""

    def test_category_values_are_strings(self):
        """Verify all category values are strings."""
        from optiverse.core.log_categories import LogCategory

        categories = [
            LogCategory.COLLABORATION,
            LogCategory.RAYTRACING,
            LogCategory.FILE_IO,
            LogCategory.COPY_PASTE,
            LogCategory.UI,
            LogCategory.COMPONENT,
            LogCategory.SESSION,
        ]

        for category in categories:
            assert isinstance(category, str)
            assert len(category) > 0


class TestProtocolsAreRuntimeCheckable:
    """Test that protocols work with isinstance."""

    def test_has_undo_stack_protocol(self):
        """Test HasUndoStack protocol can be checked at runtime."""
        from optiverse.core.protocols import HasUndoStack

        # Create a mock object that has undo_stack
        class MockWithUndoStack:
            undo_stack = None

        # Note: Protocol checking requires the attribute to exist
        obj = MockWithUndoStack()
        assert isinstance(obj, HasUndoStack)

    def test_has_settings_protocol(self):
        """Test HasSettings protocol can be checked at runtime."""
        from optiverse.core.protocols import HasSettings

        class MockWithSettings:
            settings = None

        obj = MockWithSettings()
        assert isinstance(obj, HasSettings)


class TestZOrderUtils:
    """Test z-order utility functions."""

    def test_get_z_order_items_empty_scene(self, qapp):
        """Test get_z_order_items_from_item with no scene."""
        from PyQt6 import QtWidgets

        from optiverse.core.zorder_utils import get_z_order_items_from_item

        # Create an item not in a scene
        item = QtWidgets.QGraphicsRectItem()

        # Should return empty list when item has no scene
        result = get_z_order_items_from_item(item)
        assert result == []

    def test_get_z_order_items_single_item(self, qapp, scene):
        """Test get_z_order_items_from_item with single unselected item."""
        from PyQt6 import QtWidgets

        from optiverse.core.zorder_utils import get_z_order_items_from_item

        item = QtWidgets.QGraphicsRectItem(0, 0, 10, 10)
        scene.addItem(item)

        # Should return just this item when not selected
        result = get_z_order_items_from_item(item)
        assert len(result) == 1
        assert result[0] is item
