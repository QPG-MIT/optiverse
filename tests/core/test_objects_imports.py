"""
Tests for module import structure.

These tests verify that all key classes and modules can be imported correctly
and that there are no circular import errors.
"""

from __future__ import annotations

import pytest

# Module-class pairs for parametrized import tests
IMPORTABLE_CLASSES = [
    ("optiverse.objects", "BaseObj"),
    ("optiverse.objects", "ComponentItem"),
    ("optiverse.objects", "SourceItem"),
    ("optiverse.objects", "GraphicsView"),
    ("optiverse.objects", "RulerItem"),
    ("optiverse.objects", "TextNoteItem"),
    ("optiverse.objects", "ComponentSprite"),
    ("optiverse.objects", "ImageCanvas"),
    ("optiverse.objects", "ComponentFactory"),
    ("optiverse.objects.generic", "ComponentItem"),
    ("optiverse.objects.sources", "SourceItem"),
    ("optiverse.core.models", "SourceParams"),
    ("optiverse.core.models", "ComponentParams"),
    ("optiverse.core.interface_definition", "InterfaceDefinition"),
    ("optiverse.core.log_categories", "LogCategory"),
    ("optiverse.core.protocols", "HasUndoStack"),
    ("optiverse.core.protocols", "HasSettings"),
    ("optiverse.core.protocols", "HasCollaboration"),
    ("optiverse.core.protocols", "HasSnapping"),
    ("optiverse.core.zorder_utils", "apply_z_order_change"),
    ("optiverse.core.zorder_utils", "get_z_order_items_from_item"),
    ("optiverse.core.undo_stack", "UndoStack"),
    ("optiverse.core.undo_commands", "AddItemCommand"),
    ("optiverse.core.undo_commands", "MoveItemCommand"),
    ("optiverse.raytracing.ray", "RayState"),
    ("optiverse.raytracing.ray", "Polarization"),
    ("optiverse.raytracing.elements", "MirrorElement"),
    ("optiverse.raytracing.elements", "LensElement"),
    ("optiverse.raytracing.elements", "BeamsplitterElement"),
    ("optiverse.services.zemax_parser", "ZemaxFile"),
    ("optiverse.services.zemax_parser", "ZemaxSurface"),
    ("optiverse.services.glass_catalog", "GlassCatalog"),
]


@pytest.mark.parametrize("module_path,class_name", IMPORTABLE_CLASSES)
def test_class_importable(module_path: str, class_name: str):
    """Test that class can be imported from module."""
    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name, None)
    assert cls is not None, f"{class_name} should be importable from {module_path}"


IMPORTABLE_MODULES = [
    "optiverse",
    "optiverse.objects",
    "optiverse.core",
    "optiverse.core.models",
    "optiverse.core.constants",
    "optiverse.core.log_categories",
    "optiverse.core.protocols",
    "optiverse.core.zorder_utils",
    "optiverse.core.undo_stack",
    "optiverse.core.undo_commands",
    "optiverse.core.interface_definition",
    "optiverse.raytracing",
    "optiverse.raytracing.ray",
    "optiverse.raytracing.elements",
    "optiverse.services",
    "optiverse.services.zemax_parser",
    "optiverse.services.glass_catalog",
    "optiverse.platform.paths",
    "optiverse.app.app_context",
    "optiverse.app.main",
]


@pytest.mark.parametrize("module_path", IMPORTABLE_MODULES)
def test_module_importable(module_path: str):
    """Test that module can be imported."""
    import importlib

    module = importlib.import_module(module_path)
    assert module is not None, f"{module_path} should be importable"


class TestObjectsModuleStructure:
    """Test objects module has correct structure."""

    def test_no_circular_imports(self):
        """Importing objects module should not cause circular import errors."""
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


class TestCoreModuleStructure:
    """Test core module has correct structure."""

    def test_constants_available(self):
        """Test that MIME type constants are available."""
        from optiverse.core.constants import MIME_OPTICS_COMPONENT

        assert MIME_OPTICS_COMPONENT == "application/x-optics-component"

    def test_log_categories_are_strings(self):
        """Verify all log category values are strings."""
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


class TestProtocolsRuntime:
    """Test that protocols work with isinstance."""

    def test_has_undo_stack_protocol(self):
        """Test HasUndoStack protocol can be checked at runtime."""
        from optiverse.core.protocols import HasUndoStack

        class MockWithUndoStack:
            undo_stack = None

        obj = MockWithUndoStack()
        assert isinstance(obj, HasUndoStack)

    def test_has_settings_protocol(self):
        """Test HasSettings protocol can be checked at runtime."""
        from optiverse.core.protocols import HasSettings

        class MockWithSettings:
            settings = None

        obj = MockWithSettings()
        assert isinstance(obj, HasSettings)

    def test_has_collaboration_protocol(self):
        """Test HasCollaboration protocol can be checked at runtime."""
        from optiverse.core.protocols import HasCollaboration

        class MockWithCollab:
            collab = None

        obj = MockWithCollab()
        assert isinstance(obj, HasCollaboration)

    def test_has_snapping_protocol(self):
        """Test HasSnapping protocol can be checked at runtime."""
        from optiverse.core.protocols import HasSnapping

        class MockWithSnapping:
            snapper = None
            snap_enabled = True

        obj = MockWithSnapping()
        assert isinstance(obj, HasSnapping)
