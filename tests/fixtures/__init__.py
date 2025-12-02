"""
Test fixtures for Optiverse.

This module provides factory fixtures and mock services for testing.

Usage in tests:
    from tests.fixtures import create_source_item, create_lens_item
    from tests.fixtures.mocks import MockStorageService, MockCollaborationManager
"""

from .factories import (
    create_component_item,
    create_lens_item,
    create_mirror_item,
    create_scene_with_items,
    create_source_item,
)
from .mocks import (
    MockCollaborationManager,
    MockLogService,
    MockSettingsService,
    MockStorageService,
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
