"""
Tests for Optiverse exception classes.

These tests verify that:
- All exception classes can be raised and caught
- Exception messages are formatted correctly
- Exception inheritance hierarchy is correct
- Exception attributes are properly stored
"""

from __future__ import annotations

import pytest

from optiverse.core.exceptions import (
    AssemblyLoadError,
    AssemblySaveError,
    CollaborationError,
    ComponentError,
    ComponentLoadError,
    ComponentSaveError,
    ConfigurationError,
    ConnectionError,
    InterfaceError,
    IntersectionError,
    InvalidComponentError,
    InvalidRayError,
    OptiverseError,
    RaytracingError,
    SerializationError,
    SessionError,
    SettingsError,
    SyncError,
    UnknownTypeError,
)


class TestOptiverseError:
    """Tests for base OptiverseError."""

    def test_basic_error(self):
        """Test creating basic error."""
        error = OptiverseError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.context is None

    def test_error_with_context(self):
        """Test creating error with context."""
        error = OptiverseError("Test error", context="test_function")
        assert "Test error" in str(error)
        assert "test_function" in str(error)
        assert error.context == "test_function"

    def test_error_is_exception(self):
        """Test that OptiverseError is a proper Exception."""
        assert issubclass(OptiverseError, Exception)

        with pytest.raises(OptiverseError):
            raise OptiverseError("Test")

    def test_error_can_be_caught_as_exception(self):
        """Test that OptiverseError can be caught as Exception."""
        try:
            raise OptiverseError("Test")
        except Exception as e:
            assert isinstance(e, OptiverseError)


class TestSerializationErrors:
    """Tests for serialization-related exceptions."""

    def test_serialization_error_inheritance(self):
        """Test SerializationError inherits from OptiverseError."""
        assert issubclass(SerializationError, OptiverseError)

    def test_component_load_error(self):
        """Test ComponentLoadError creation and attributes."""
        error = ComponentLoadError("/path/to/file.json", "File not found")

        assert error.path == "/path/to/file.json"
        assert error.reason == "File not found"
        assert "File not found" in str(error)
        assert "/path/to/file.json" in str(error)

    def test_component_load_error_inheritance(self):
        """Test ComponentLoadError can be caught as SerializationError."""
        with pytest.raises(SerializationError):
            raise ComponentLoadError("/path", "reason")

    def test_component_save_error(self):
        """Test ComponentSaveError creation and attributes."""
        error = ComponentSaveError("/path/to/file.json", "Permission denied")

        assert error.path == "/path/to/file.json"
        assert error.reason == "Permission denied"
        assert "Permission denied" in str(error)

    def test_assembly_load_error(self):
        """Test AssemblyLoadError creation and attributes."""
        error = AssemblyLoadError("assembly.json", "Invalid JSON")

        assert error.path == "assembly.json"
        assert error.reason == "Invalid JSON"
        assert "Invalid JSON" in str(error)

    def test_assembly_save_error(self):
        """Test AssemblySaveError creation and attributes."""
        error = AssemblySaveError("assembly.json", "Disk full")

        assert error.path == "assembly.json"
        assert error.reason == "Disk full"
        assert "Disk full" in str(error)

    def test_unknown_type_error(self):
        """Test UnknownTypeError creation and attributes."""
        error = UnknownTypeError("weird_type")

        assert error.type_name == "weird_type"
        assert "weird_type" in str(error)


class TestComponentErrors:
    """Tests for component-related exceptions."""

    def test_component_error_inheritance(self):
        """Test ComponentError inherits from OptiverseError."""
        assert issubclass(ComponentError, OptiverseError)

    def test_invalid_component_error(self):
        """Test InvalidComponentError creation and attributes."""
        error = InvalidComponentError("TestLens", "Missing EFL")

        assert error.name == "TestLens"
        assert error.reason == "Missing EFL"
        assert "TestLens" in str(error)
        assert "Missing EFL" in str(error)

    def test_interface_error(self):
        """Test InterfaceError creation and attributes."""
        error = InterfaceError("MyLens", "surface1", "Invalid curvature")

        assert error.component_name == "MyLens"
        assert error.interface_name == "surface1"
        assert error.reason == "Invalid curvature"
        assert "MyLens" in str(error)
        assert "surface1" in str(error)
        assert "Invalid curvature" in str(error)


class TestCollaborationErrors:
    """Tests for collaboration-related exceptions."""

    def test_collaboration_error_inheritance(self):
        """Test CollaborationError inherits from OptiverseError."""
        assert issubclass(CollaborationError, OptiverseError)

    def test_connection_error(self):
        """Test ConnectionError creation and attributes."""
        error = ConnectionError("ws://localhost:8000", "Connection refused")

        assert error.server_url == "ws://localhost:8000"
        assert error.reason == "Connection refused"
        assert "ws://localhost:8000" in str(error)

    def test_sync_error(self):
        """Test SyncError creation and attributes."""
        error = SyncError("session-123", "Version mismatch")

        assert error.session_id == "session-123"
        assert error.reason == "Version mismatch"
        assert "session-123" in str(error)

    def test_session_error(self):
        """Test SessionError creation and attributes."""
        error = SessionError("abc-def", "Session expired")

        assert error.session_id == "abc-def"
        assert error.reason == "Session expired"
        assert "abc-def" in str(error)


class TestRaytracingErrors:
    """Tests for raytracing-related exceptions."""

    def test_raytracing_error_inheritance(self):
        """Test RaytracingError inherits from OptiverseError."""
        assert issubclass(RaytracingError, OptiverseError)

    def test_invalid_ray_error(self):
        """Test InvalidRayError creation and attributes."""
        error = InvalidRayError("Zero direction vector")

        assert error.reason == "Zero direction vector"
        assert "Zero direction vector" in str(error)

    def test_intersection_error(self):
        """Test IntersectionError creation and attributes."""
        error = IntersectionError("curved_surface", "Numerical instability")

        assert error.surface_type == "curved_surface"
        assert error.reason == "Numerical instability"
        assert "curved_surface" in str(error)
        assert "Numerical instability" in str(error)


class TestConfigurationErrors:
    """Tests for configuration-related exceptions."""

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inherits from OptiverseError."""
        assert issubclass(ConfigurationError, OptiverseError)

    def test_settings_error(self):
        """Test SettingsError creation and attributes."""
        error = SettingsError("theme_name", "Invalid theme")

        assert error.setting_key == "theme_name"
        assert error.reason == "Invalid theme"
        assert "theme_name" in str(error)
        assert "Invalid theme" in str(error)


class TestExceptionHierarchy:
    """Tests for exception hierarchy correctness."""

    def test_all_inherit_from_base(self):
        """Test all exceptions inherit from OptiverseError."""
        exceptions = [
            SerializationError,
            ComponentLoadError,
            ComponentSaveError,
            AssemblyLoadError,
            AssemblySaveError,
            UnknownTypeError,
            ComponentError,
            InvalidComponentError,
            InterfaceError,
            CollaborationError,
            ConnectionError,
            SyncError,
            SessionError,
            RaytracingError,
            InvalidRayError,
            IntersectionError,
            ConfigurationError,
            SettingsError,
        ]

        for exc_class in exceptions:
            assert issubclass(
                exc_class, OptiverseError
            ), f"{exc_class.__name__} should inherit from OptiverseError"

    def test_serialization_children(self):
        """Test serialization error hierarchy."""
        serialization_exceptions = [
            ComponentLoadError,
            ComponentSaveError,
            AssemblyLoadError,
            AssemblySaveError,
            UnknownTypeError,
        ]

        for exc_class in serialization_exceptions:
            assert issubclass(exc_class, SerializationError)

    def test_component_children(self):
        """Test component error hierarchy."""
        component_exceptions = [
            InvalidComponentError,
            InterfaceError,
        ]

        for exc_class in component_exceptions:
            assert issubclass(exc_class, ComponentError)

    def test_collaboration_children(self):
        """Test collaboration error hierarchy."""
        collaboration_exceptions = [
            ConnectionError,
            SyncError,
            SessionError,
        ]

        for exc_class in collaboration_exceptions:
            assert issubclass(exc_class, CollaborationError)

    def test_raytracing_children(self):
        """Test raytracing error hierarchy."""
        raytracing_exceptions = [
            InvalidRayError,
            IntersectionError,
        ]

        for exc_class in raytracing_exceptions:
            assert issubclass(exc_class, RaytracingError)

    def test_configuration_children(self):
        """Test configuration error hierarchy."""
        config_exceptions = [
            SettingsError,
        ]

        for exc_class in config_exceptions:
            assert issubclass(exc_class, ConfigurationError)


class TestExceptionUsage:
    """Test practical exception usage patterns."""

    def test_catch_specific_before_general(self):
        """Test that specific exceptions can be caught before general ones."""
        caught_type = None

        try:
            raise ComponentLoadError("/path", "reason")
        except ComponentLoadError:
            caught_type = "specific"
        except SerializationError:
            caught_type = "general"

        assert caught_type == "specific"

    def test_catch_general_catches_specific(self):
        """Test that catching general exception catches specific ones."""
        with pytest.raises(SerializationError):
            raise ComponentLoadError("/path", "reason")

    def test_exceptions_in_try_except(self):
        """Test exceptions work correctly in try-except blocks."""

        def load_component(path: str):
            if not path.endswith(".json"):
                raise ComponentLoadError(path, "Invalid extension")
            return {"name": "test"}

        with pytest.raises(ComponentLoadError) as exc_info:
            load_component("file.txt")

        assert exc_info.value.path == "file.txt"
        assert "Invalid extension" in str(exc_info.value)
