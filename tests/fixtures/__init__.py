"""
Test fixtures for Optiverse.

This module provides factory fixtures and mock services for testing.

Usage in tests:
    from tests.fixtures import create_source_item, create_lens_item
    from tests.fixtures.mocks import MockStorageService, MockCollaborationManager
"""

from .factories import (
    create_source_item,
    create_lens_item,
    create_mirror_item,
    create_component_item,
    create_scene_with_items,
)

from .mocks import (
    MockStorageService,
    MockSettingsService,
    MockCollaborationManager,
    MockLogService,
)

__all__ = [
    # Factories
    "create_source_item",
    "create_lens_item",
    "create_mirror_item",
    "create_component_item",
    "create_scene_with_items",
    # Mocks
    "MockStorageService",
    "MockSettingsService",
    "MockCollaborationManager",
    "MockLogService",
]

