"""
Logging service for the application.

Provides a centralized logging system that can be viewed in a log window.
All debug messages are timestamped and stored in memory.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Callable, List

_logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log message severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogMessage:
    """A single log message with timestamp and metadata."""

    def __init__(self, level: LogLevel, message: str, category: str = "General"):
        self.timestamp = datetime.now()
        self.level = level
        self.message = message
        self.category = category

    def format(self) -> str:
        """Format the log message for display."""
        time_str = self.timestamp.strftime("%H:%M:%S.%f")[:-3]  # milliseconds
        return f"[{time_str}] {self.level.value:7s} | {self.category:12s} | {self.message}"

    def __str__(self) -> str:
        return self.format()


class LogService:
    """
    Centralized logging service.

    Features:
    - Stores log messages in memory
    - Notifies listeners when new messages arrive
    - Supports filtering by level and category
    - Thread-safe for future async operations
    """

    def __init__(self, max_messages: int = 1000):
        """
        Initialize the log service.

        Args:
            max_messages: Maximum number of messages to keep in memory
        """
        self._messages: List[LogMessage] = []
        self._max_messages = max_messages
        self._listeners: List[Callable[[LogMessage], None]] = []

    def add_listener(self, callback: Callable[[LogMessage], None]):
        """
        Register a callback to be notified of new log messages.

        Args:
            callback: Function that takes a LogMessage
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[LogMessage], None]):
        """Remove a registered listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def log(self, level: LogLevel, message: str, category: str = "General"):
        """
        Log a message.

        Args:
            level: Severity level
            message: Log message content
            category: Message category (e.g., "Copy/Paste", "Raytracing", "File I/O")
        """
        log_msg = LogMessage(level, message, category)

        # Add to message buffer
        self._messages.append(log_msg)

        # Trim old messages if over limit
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(log_msg)
            except Exception as e:
                # Don't let listener errors break logging
                _logger.debug("Error in log listener: %s", e)

    def debug(self, message: str, category: str = "General"):
        """Log a debug message."""
        self.log(LogLevel.DEBUG, message, category)

    def info(self, message: str, category: str = "General"):
        """Log an info message."""
        self.log(LogLevel.INFO, message, category)

    def warning(self, message: str, category: str = "General"):
        """Log a warning message."""
        self.log(LogLevel.WARNING, message, category)

    def error(self, message: str, category: str = "General"):
        """Log an error message."""
        self.log(LogLevel.ERROR, message, category)

    def get_messages(self,
                     level: LogLevel | None = None,
                     category: str | None = None) -> List[LogMessage]:
        """
        Get all log messages, optionally filtered.

        Args:
            level: Filter by log level (None = all)
            category: Filter by category (None = all)

        Returns:
            List of matching log messages
        """
        messages = self._messages

        if level is not None:
            messages = [m for m in messages if m.level == level]

        if category is not None:
            messages = [m for m in messages if m.category == category]

        return messages

    def clear(self):
        """Clear all log messages."""
        self._messages.clear()

    def get_categories(self) -> List[str]:
        """Get list of all categories that have been logged."""
        categories = set(msg.category for msg in self._messages)
        return sorted(categories)


# Global singleton instance
_log_service: LogService | None = None


def get_log_service() -> LogService:
    """Get the global log service instance."""
    global _log_service
    if _log_service is None:
        _log_service = LogService()
    return _log_service



