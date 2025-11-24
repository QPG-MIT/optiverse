"""
Pytest configuration and shared fixtures for Optiverse tests.

This module provides:
- QApplication fixture for Qt tests (session-scoped)
- QtBot fixture for Qt interaction testing
- Scene fixtures with automatic cleanup
- Mock service fixtures
- Factory fixtures for common test objects
"""
import os
import sys
import pytest


@pytest.fixture(scope="session", autouse=True)
def _ensure_src_on_path():
    """Ensure src directory is on Python path for imports."""
    root = os.path.dirname(os.path.dirname(__file__))
    src = os.path.join(root, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)
    yield


@pytest.fixture(scope="session")
def qapp():
    """
    Create a QApplication instance for tests.
    
    Session-scoped to avoid creating multiple QApplications.
    """
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        # Pass empty list to avoid issues with command line args
        app = QApplication([])
    yield app


@pytest.fixture
def qtbot(qapp):
    """
    Provides a QtBot object for Qt widget testing.
    
    Requires qapp fixture to ensure QApplication exists.
    """
    from pytestqt.qtbot import QtBot
    bot = QtBot(qapp)
    yield bot


# =============================================================================
# Scene Fixtures
# =============================================================================

@pytest.fixture
def scene(qapp):
    """
    Create a QGraphicsScene with proper size and automatic cleanup.
    
    The scene is automatically cleared after the test.
    """
    from PyQt6 import QtWidgets
    from optiverse.core.constants import SCENE_SIZE_MM, SCENE_MIN_COORD
    
    scene = QtWidgets.QGraphicsScene()
    scene.setSceneRect(
        SCENE_MIN_COORD,
        SCENE_MIN_COORD,
        SCENE_SIZE_MM,
        SCENE_SIZE_MM,
    )
    yield scene
    # Cleanup: remove all items
    scene.clear()


@pytest.fixture
def view(qapp, scene):
    """
    Create a GraphicsView attached to a scene.
    
    The view is automatically deleted after the test.
    """
    from optiverse.objects import GraphicsView
    
    view = GraphicsView()
    view.setScene(scene)
    yield view
    # Cleanup
    view.setScene(None)
    view.deleteLater()


# =============================================================================
# Mock Service Fixtures
# =============================================================================

@pytest.fixture
def mock_storage_service():
    """Provide a MockStorageService for testing."""
    from tests.fixtures.mocks import MockStorageService
    return MockStorageService()


@pytest.fixture
def mock_settings_service():
    """Provide a MockSettingsService for testing."""
    from tests.fixtures.mocks import MockSettingsService
    return MockSettingsService()


@pytest.fixture
def mock_collaboration_manager():
    """Provide a MockCollaborationManager for testing."""
    from tests.fixtures.mocks import MockCollaborationManager
    return MockCollaborationManager()


@pytest.fixture
def mock_log_service():
    """Provide a MockLogService for testing."""
    from tests.fixtures.mocks import MockLogService
    return MockLogService()


# =============================================================================
# Factory Fixtures
# =============================================================================

@pytest.fixture
def source_factory():
    """
    Provide a factory function for creating SourceItems.
    
    Usage:
        def test_something(source_factory):
            source = source_factory(x_mm=100, num_rays=10)
    """
    from tests.fixtures.factories import create_source_item
    return create_source_item


@pytest.fixture
def lens_factory():
    """Provide a factory function for creating LensItems."""
    from tests.fixtures.factories import create_lens_item
    return create_lens_item


@pytest.fixture
def mirror_factory():
    """Provide a factory function for creating MirrorItems."""
    from tests.fixtures.factories import create_mirror_item
    return create_mirror_item


@pytest.fixture
def component_factory():
    """Provide a factory function for creating ComponentItems."""
    from tests.fixtures.factories import create_component_item
    return create_component_item


# =============================================================================
# Undo Stack Fixtures
# =============================================================================

@pytest.fixture
def undo_stack():
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
def basic_optical_setup(qapp, scene):
    """
    Provide a basic optical setup: source -> lens -> mirror.
    
    Returns:
        Tuple of (source, lens, mirror) items already added to scene
    """
    from tests.fixtures.factories import create_source_item, create_lens_item, create_mirror_item
    
    source = create_source_item(x_mm=-100, y_mm=0, angle_deg=0)
    lens = create_lens_item(x_mm=0, y_mm=0, angle_deg=90, efl_mm=50)
    mirror = create_mirror_item(x_mm=100, y_mm=0, angle_deg=45)
    
    scene.addItem(source)
    scene.addItem(lens)
    scene.addItem(mirror)
    
    yield source, lens, mirror
