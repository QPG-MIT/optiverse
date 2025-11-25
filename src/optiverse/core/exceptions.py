"""
Custom exceptions for Optiverse.

This module defines domain-specific exceptions for better error handling
and more informative error messages.

Usage:
    from optiverse.core.exceptions import (
        OptiverseError,
        SerializationError,
        ComponentError,
        CollaborationError,
    )

    try:
        component = load_component(path)
    except ComponentLoadError as e:
        logger.error(f"Failed to load component: {e}")
"""

from __future__ import annotations


class OptiverseError(Exception):
    """Base exception for all Optiverse errors."""

    def __init__(self, message: str, context: str | None = None):
        """
        Initialize the exception.

        Args:
            message: Error description
            context: Optional context about where/why the error occurred
        """
        self.message = message
        self.context = context
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the full error message."""
        if self.context:
            return f"{self.message} (context: {self.context})"
        return self.message


# =============================================================================
# Serialization Errors
# =============================================================================


class SerializationError(OptiverseError):
    """Base class for serialization-related errors."""

    pass


class ComponentLoadError(SerializationError):
    """Raised when a component cannot be loaded from disk."""

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load component from '{path}': {reason}", context=path)


class ComponentSaveError(SerializationError):
    """Raised when a component cannot be saved to disk."""

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to save component to '{path}': {reason}", context=path)


class AssemblyLoadError(SerializationError):
    """Raised when an assembly file cannot be loaded."""

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load assembly from '{path}': {reason}", context=path)


class AssemblySaveError(SerializationError):
    """Raised when an assembly file cannot be saved."""

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to save assembly to '{path}': {reason}", context=path)


class UnknownTypeError(SerializationError):
    """Raised when encountering an unknown item type during deserialization."""

    def __init__(self, type_name: str):
        self.type_name = type_name
        super().__init__(f"Unknown item type: '{type_name}'", context=f"type={type_name}")


# =============================================================================
# Component Errors
# =============================================================================


class ComponentError(OptiverseError):
    """Base class for component-related errors."""

    pass


class InvalidComponentError(ComponentError):
    """Raised when a component is invalid or malformed."""

    def __init__(self, name: str, reason: str):
        self.name = name
        self.reason = reason
        super().__init__(f"Invalid component '{name}': {reason}", context=name)


class InterfaceError(ComponentError):
    """Raised when there's an error with optical interfaces."""

    def __init__(self, component_name: str, interface_name: str, reason: str):
        self.component_name = component_name
        self.interface_name = interface_name
        self.reason = reason
        super().__init__(
            f"Interface error in '{component_name}.{interface_name}': {reason}",
            context=f"{component_name}.{interface_name}",
        )


# =============================================================================
# Collaboration Errors
# =============================================================================


class CollaborationError(OptiverseError):
    """Base class for collaboration-related errors."""

    pass


class ConnectionError(CollaborationError):
    """Raised when a collaboration connection fails."""

    def __init__(self, server_url: str, reason: str):
        self.server_url = server_url
        self.reason = reason
        super().__init__(f"Failed to connect to '{server_url}': {reason}", context=server_url)


class SyncError(CollaborationError):
    """Raised when state synchronization fails."""

    def __init__(self, session_id: str, reason: str):
        self.session_id = session_id
        self.reason = reason
        super().__init__(f"Sync failed for session '{session_id}': {reason}", context=session_id)


class SessionError(CollaborationError):
    """Raised when there's an error with session management."""

    def __init__(self, session_id: str, reason: str):
        self.session_id = session_id
        self.reason = reason
        super().__init__(f"Session error '{session_id}': {reason}", context=session_id)


# =============================================================================
# Raytracing Errors
# =============================================================================


class RaytracingError(OptiverseError):
    """Base class for raytracing-related errors."""

    pass


class InvalidRayError(RaytracingError):
    """Raised when a ray is invalid or cannot be traced."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid ray: {reason}")


class IntersectionError(RaytracingError):
    """Raised when ray-surface intersection fails unexpectedly."""

    def __init__(self, surface_type: str, reason: str):
        self.surface_type = surface_type
        self.reason = reason
        super().__init__(f"Intersection error with {surface_type}: {reason}", context=surface_type)


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(OptiverseError):
    """Base class for configuration-related errors."""

    pass


class SettingsError(ConfigurationError):
    """Raised when there's an error with application settings."""

    def __init__(self, setting_key: str, reason: str):
        self.setting_key = setting_key
        self.reason = reason
        super().__init__(f"Settings error for '{setting_key}': {reason}", context=setting_key)
