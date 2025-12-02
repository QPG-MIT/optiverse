"""
Pytest configuration and shared fixtures for Optiverse tests.

This module provides:
- QApplication fixture for Qt tests (session-scoped)
- QtBot fixture for Qt interaction testing
- Scene fixtures with automatic cleanup
- Mock service fixtures
- Factory fixtures for common test objects
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from typing import TYPE_CHECKING, Callable

import pytest

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication, QGraphicsScene

    from optiverse.core.undo_stack import UndoStack
    from optiverse.objects.generic import ComponentItem
    from optiverse.objects.sources import SourceItem
    from optiverse.objects.views import GraphicsView
    from tests.fixtures.mocks import (
        MockCollaborationManager,
        MockLogService,
        MockSettingsService,
        MockStorageService,
    )


@pytest.fixture(scope="session", autouse=True)
def _ensure_src_on_path() -> Generator[None, None, None]:
    """Ensure src directory is on Python path for imports."""
    root = os.path.dirname(os.path.dirname(__file__))
    src = os.path.join(root, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)
    yield


# Use pytest-qt's built-in qapp and qtbot fixtures
# Do not override them - pytest-qt handles everything correctly


# =============================================================================
# Scene Fixtures
# =============================================================================


@pytest.fixture
def scene(qapp: QApplication) -> Generator[QGraphicsScene, None, None]:
    """
    Create a QGraphicsScene with proper size and automatic cleanup.

    The scene is automatically cleared after the test.
    """
    import gc

    from PyQt6 import QtWidgets

    from optiverse.core.constants import SCENE_MIN_COORD, SCENE_SIZE_MM

    s = QtWidgets.QGraphicsScene()
    s.setSceneRect(
        SCENE_MIN_COORD,
        SCENE_MIN_COORD,
        SCENE_SIZE_MM,
        SCENE_SIZE_MM,
    )
    yield s
    # Cleanup: remove all items
    s.clear()
    QtWidgets.QApplication.processEvents()
    gc.collect()
    QtWidgets.QApplication.processEvents()


@pytest.fixture
def view(qapp: QApplication, scene: QGraphicsScene) -> Generator[GraphicsView, None, None]:
    """
    Create a GraphicsView attached to a scene.

    The view is automatically deleted after the test.
    """
    from optiverse.objects import GraphicsView

    v = GraphicsView()
    v.setScene(scene)
    yield v
    # Cleanup
    v.setScene(None)
    v.deleteLater()


# =============================================================================
# Mock Service Fixtures
# =============================================================================


@pytest.fixture
def mock_storage_service() -> MockStorageService:
    """Provide a MockStorageService for testing."""
    from tests.fixtures.mocks import MockStorageService

    return MockStorageService()


@pytest.fixture
def mock_settings_service() -> MockSettingsService:
    """Provide a MockSettingsService for testing."""
    from tests.fixtures.mocks import MockSettingsService

    return MockSettingsService()


@pytest.fixture
def mock_collaboration_manager() -> MockCollaborationManager:
    """Provide a MockCollaborationManager for testing."""
    from tests.fixtures.mocks import MockCollaborationManager

    return MockCollaborationManager()


@pytest.fixture
def mock_log_service() -> MockLogService:
    """Provide a MockLogService for testing."""
    from tests.fixtures.mocks import MockLogService

    return MockLogService()


# =============================================================================
# Factory Fixtures
# =============================================================================


@pytest.fixture
def source_factory() -> Callable[..., SourceItem]:
    """
    Provide a factory function for creating SourceItems.

    Usage:
        def test_something(source_factory):
            source = source_factory(x_mm=100, num_rays=10)
    """
    from tests.fixtures.factories import create_source_item

    return create_source_item


@pytest.fixture
def lens_factory() -> Callable[..., ComponentItem]:
    """Provide a factory function for creating LensItems."""
    from tests.fixtures.factories import create_lens_item

    return create_lens_item


@pytest.fixture
def mirror_factory() -> Callable[..., ComponentItem]:
    """Provide a factory function for creating MirrorItems."""
    from tests.fixtures.factories import create_mirror_item

    return create_mirror_item


@pytest.fixture
def component_factory() -> Callable[..., ComponentItem]:
    """Provide a factory function for creating ComponentItems."""
    from tests.fixtures.factories import create_component_item

    return create_component_item


# =============================================================================
# Undo Stack Fixtures
# =============================================================================


@pytest.fixture
def undo_stack() -> Generator[UndoStack, None, None]:
    """
    Provide a fresh UndoStack for testing.

    The stack is automatically cleared after the test.
    """
    from optiverse.core.undo_stack import UndoStack

    stack = UndoStack()
    yield stack
    stack.clear()


# =============================================================================
# Complete Setup Fixtures
# =============================================================================


@pytest.fixture
def basic_optical_setup(
    qapp: QApplication, scene: QGraphicsScene
) -> Generator[tuple[SourceItem, ComponentItem, ComponentItem], None, None]:
    """
    Provide a basic optical setup: source -> lens -> mirror.

    Returns:
        Tuple of (source, lens, mirror) items already added to scene
    """
    from tests.fixtures.factories import create_lens_item, create_mirror_item, create_source_item

    source = create_source_item(x_mm=-100, y_mm=0, angle_deg=0)
    lens = create_lens_item(x_mm=0, y_mm=0, angle_deg=90, efl_mm=50)
    mirror = create_mirror_item(x_mm=100, y_mm=0, angle_deg=45)

    scene.addItem(source)
    scene.addItem(lens)
    scene.addItem(mirror)

    yield source, lens, mirror
