"""
Smoke tests for controller classes.

These tests verify that the controller classes can be instantiated
and their basic methods work without errors.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PyQt6 import QtWidgets, QtCore


class TestFileControllerImport:
    """Verify that FileController can be imported and instantiated."""

    def test_import_file_controller(self):
        """Test that FileController can be imported."""
        from optiverse.ui.controllers.file_controller import FileController

        assert callable(FileController)

    def test_file_controller_has_required_signals(self):
        """Test that FileController has expected signals."""
        from optiverse.ui.controllers.file_controller import FileController

        # FileController is a QObject with signals
        assert hasattr(FileController, 'traceRequested')
        assert hasattr(FileController, 'windowTitleChanged')

    def test_file_controller_instantiation(self, qapp, scene):
        """Test that FileController can be instantiated with mocks."""
        from optiverse.ui.controllers.file_controller import FileController
        from optiverse.core.undo_stack import UndoStack

        mock_log = MagicMock()
        mock_get_ray_data = MagicMock(return_value=[])
        undo_stack = UndoStack()

        controller = FileController(
            scene=scene,
            undo_stack=undo_stack,
            log_service=mock_log,
            get_ray_data=mock_get_ray_data,
            parent_widget=None,
        )

        assert controller is not None
        assert hasattr(controller, 'save_assembly')
        assert hasattr(controller, 'open_assembly')
        assert hasattr(controller, 'is_modified')


class TestCollaborationControllerImport:
    """Verify that CollaborationController can be imported and instantiated."""

    def test_import_collaboration_controller(self):
        """Test that CollaborationController can be imported."""
        from optiverse.ui.controllers.collaboration_controller import CollaborationController

        assert callable(CollaborationController)

    def test_collaboration_controller_has_required_signals(self):
        """Test that CollaborationController has expected signals."""
        from optiverse.ui.controllers.collaboration_controller import CollaborationController

        assert hasattr(CollaborationController, 'statusChanged')

    def test_collaboration_controller_instantiation(self, qapp):
        """Test that CollaborationController can be instantiated with mocks."""
        from optiverse.ui.controllers.collaboration_controller import CollaborationController

        mock_collab_manager = MagicMock()
        mock_log = MagicMock()

        controller = CollaborationController(
            collaboration_manager=mock_collab_manager,
            log_service=mock_log,
            parent_widget=None,
        )

        assert controller is not None
        assert hasattr(controller, 'open_dialog')
        assert hasattr(controller, 'disconnect')
        assert hasattr(controller, 'is_connected')


class TestRaytracingControllerImport:
    """Verify that RaytracingController can be imported and instantiated."""

    def test_import_raytracing_controller(self):
        """Test that RaytracingController can be imported."""
        from optiverse.ui.controllers.raytracing_controller import RaytracingController

        assert callable(RaytracingController)

    def test_raytracing_controller_instantiation(self, qapp, scene):
        """Test that RaytracingController can be instantiated with mocks."""
        from optiverse.ui.controllers.raytracing_controller import RaytracingController

        mock_renderer = MagicMock()
        mock_log = MagicMock()

        controller = RaytracingController(
            scene=scene,
            ray_renderer=mock_renderer,
            log_service=mock_log,
            parent=None,
        )

        assert controller is not None
        assert hasattr(controller, 'schedule_retrace')
        assert hasattr(controller, 'clear_rays')
        assert hasattr(controller, 'autotrace')

    def test_raytracing_controller_autotrace_property(self, qapp, scene):
        """Test autotrace property getter/setter."""
        from optiverse.ui.controllers.raytracing_controller import RaytracingController

        mock_renderer = MagicMock()
        mock_log = MagicMock()

        controller = RaytracingController(
            scene=scene,
            ray_renderer=mock_renderer,
            log_service=mock_log,
            parent=None,
        )

        # Default should be True
        assert controller.autotrace is True

        # Should be settable
        controller.autotrace = False
        assert controller.autotrace is False

    def test_raytracing_controller_clear_rays(self, qapp, scene):
        """Test clear_rays method."""
        from optiverse.ui.controllers.raytracing_controller import RaytracingController

        mock_renderer = MagicMock()
        mock_log = MagicMock()

        controller = RaytracingController(
            scene=scene,
            ray_renderer=mock_renderer,
            log_service=mock_log,
            parent=None,
        )

        # Should not raise
        controller.clear_rays()

        # Renderer's clear should be called
        mock_renderer.clear.assert_called_once()


class TestToolModeControllerImport:
    """Verify that ToolModeController can be imported and instantiated."""

    def test_import_tool_mode_controller(self):
        """Test that ToolModeController can be imported."""
        from optiverse.ui.controllers.tool_mode_controller import ToolModeController

        assert callable(ToolModeController)

    def test_tool_mode_controller_instantiation(self, qapp):
        """Test that ToolModeController can be instantiated with mocks."""
        from optiverse.ui.controllers.tool_mode_controller import ToolModeController
        from optiverse.core.editor_state import EditorState

        editor_state = EditorState()
        mock_view = MagicMock()
        mock_path_handler = MagicMock()
        mock_placement_handler = MagicMock()

        controller = ToolModeController(
            editor_state=editor_state,
            view=mock_view,
            path_measure_handler=mock_path_handler,
            placement_handler=mock_placement_handler,
            parent=None,
        )

        assert controller is not None
        assert hasattr(controller, 'toggle_inspect')
        assert hasattr(controller, 'toggle_path_measure')
        assert hasattr(controller, 'toggle_placement')


class TestControllerSignals:
    """Test that controller signals work correctly."""

    def test_file_controller_trace_requested_signal(self, qapp, scene):
        """Test that FileController emits traceRequested signal."""
        from optiverse.ui.controllers.file_controller import FileController
        from optiverse.core.undo_stack import UndoStack

        mock_log = MagicMock()
        mock_get_ray_data = MagicMock(return_value=[])
        undo_stack = UndoStack()

        controller = FileController(
            scene=scene,
            undo_stack=undo_stack,
            log_service=mock_log,
            get_ray_data=mock_get_ray_data,
            parent_widget=None,
        )

        # Set up signal spy
        signal_received = []
        controller.traceRequested.connect(lambda: signal_received.append(True))

        # Signal should be emittable
        controller.traceRequested.emit()
        assert len(signal_received) == 1

    def test_collaboration_controller_status_signal(self, qapp):
        """Test that CollaborationController emits statusChanged signal."""
        from optiverse.ui.controllers.collaboration_controller import CollaborationController

        mock_collab_manager = MagicMock()
        mock_log = MagicMock()

        controller = CollaborationController(
            collaboration_manager=mock_collab_manager,
            log_service=mock_log,
            parent_widget=None,
        )

        # Set up signal spy
        signal_values = []
        controller.statusChanged.connect(lambda msg: signal_values.append(msg))

        # Emit with a message
        controller.statusChanged.emit("Test status")
        assert len(signal_values) == 1
        assert signal_values[0] == "Test status"



