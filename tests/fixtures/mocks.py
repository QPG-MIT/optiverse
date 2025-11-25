"""
Mock services for testing.

These mocks provide test doubles for services that have external dependencies
or side effects (file I/O, network, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class MockStorageService:
    """
    Mock StorageService that stores data in memory instead of disk.

    Use this in tests to avoid file system operations.
    """

    def __init__(self):
        self.settings_service = MockSettingsService()
        self._components: dict[str, dict[str, Any]] = {}
        self._library_paths: list[Path] = []

    def list_components(self) -> list[dict[str, Any]]:
        """Return list of stored component data."""
        return list(self._components.values())

    def save_component(
        self,
        name: str,
        image_data: bytes | None = None,
        object_height_mm: float = 25.4,
        angle_deg: float = 0.0,
        category: str | None = None,
        notes: str | None = None,
        interfaces: list | None = None,
    ) -> bool:
        """Store component in memory."""
        self._components[name] = {
            "name": name,
            "object_height_mm": object_height_mm,
            "angle_deg": angle_deg,
            "category": category,
            "notes": notes,
            "interfaces": interfaces or [],
            "image_path": f"/mock/{name}.png" if image_data else None,
        }
        return True

    def delete_component(self, name: str) -> bool:
        """Remove component from memory."""
        if name in self._components:
            del self._components[name]
            return True
        return False

    def get_all_library_roots(self) -> list[Path]:
        """Return mock library roots."""
        return self._library_paths


class MockSettingsService:
    """
    Mock SettingsService that stores settings in memory.

    Use this in tests to avoid QSettings/file operations.
    """

    def __init__(self):
        self._settings: dict[str, Any] = {
            "dark_mode": True,
            "autotrace": True,
            "magnetic_snap": True,
            "snap_to_grid": False,
            "ray_width_px": 1.5,
            "last_directory": "/mock/path",
        }

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)

    def set_value(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self._settings[key] = value

    def get_library_path(self) -> str | None:
        """Return mock library path."""
        return self._settings.get("library_path")

    def set_library_path(self, path: str) -> None:
        """Set mock library path."""
        self._settings["library_path"] = path


class MockCollaborationManager:
    """
    Mock CollaborationManager that doesn't connect to any server.

    Use this in tests to avoid network operations.
    """

    def __init__(self):
        self.is_connected = False
        self.role: str | None = None
        self.session_id: str | None = None
        self._broadcasts: list[dict[str, Any]] = []
        self.item_uuid_map: dict[str, Any] = {}

    def connect_to_session(self, server_url: str, session_id: str, user_id: str) -> None:
        """Simulate connecting to a session."""
        self.is_connected = True
        self.session_id = session_id

    def disconnect(self) -> None:
        """Simulate disconnecting."""
        self.is_connected = False
        self.session_id = None
        self.role = None

    def broadcast_add_item(self, item: Any) -> None:
        """Record broadcast without actually sending."""
        self._broadcasts.append(
            {
                "action": "add",
                "item_uuid": getattr(item, "item_uuid", None),
            }
        )

    def broadcast_update_item(self, item: Any) -> None:
        """Record broadcast without actually sending."""
        self._broadcasts.append(
            {
                "action": "update",
                "item_uuid": getattr(item, "item_uuid", None),
            }
        )

    def broadcast_remove_item(self, item: Any) -> None:
        """Record broadcast without actually sending."""
        self._broadcasts.append(
            {
                "action": "remove",
                "item_uuid": getattr(item, "item_uuid", None),
            }
        )

    def get_broadcasts(self) -> list[dict[str, Any]]:
        """Return all recorded broadcasts (for test assertions)."""
        return self._broadcasts

    def clear_broadcasts(self) -> None:
        """Clear recorded broadcasts."""
        self._broadcasts.clear()


class MockLogService:
    """
    Mock LogService that captures log messages in memory.

    Use this in tests to verify logging behavior.
    """

    def __init__(self):
        self._messages: list[dict[str, Any]] = []

    def info(self, message: str, category: str = "") -> None:
        """Record info message."""
        self._messages.append({"level": "info", "message": message, "category": category})

    def debug(self, message: str, category: str = "") -> None:
        """Record debug message."""
        self._messages.append({"level": "debug", "message": message, "category": category})

    def warning(self, message: str, category: str = "") -> None:
        """Record warning message."""
        self._messages.append({"level": "warning", "message": message, "category": category})

    def error(self, message: str, category: str = "") -> None:
        """Record error message."""
        self._messages.append({"level": "error", "message": message, "category": category})

    def get_messages(self, level: str | None = None) -> list[dict[str, Any]]:
        """
        Return captured messages, optionally filtered by level.

        Args:
            level: Optional level filter ("info", "debug", "warning", "error")

        Returns:
            List of message dicts
        """
        if level:
            return [m for m in self._messages if m["level"] == level]
        return self._messages

    def clear(self) -> None:
        """Clear captured messages."""
        self._messages.clear()

    def assert_message_logged(self, substring: str, level: str | None = None) -> bool:
        """
        Check if a message containing substring was logged.

        Args:
            substring: Text to search for in messages
            level: Optional level filter

        Returns:
            True if message found, False otherwise
        """
        messages = self.get_messages(level)
        return any(substring in m["message"] for m in messages)
