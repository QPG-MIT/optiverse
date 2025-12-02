"""
Global error handling service for the application.

Provides centralized exception handling with user-friendly error dialogs
and logging integration. Prevents the application from crashing on errors.
"""

from __future__ import annotations

import logging
import sys
import traceback
from typing import Callable

from PyQt6 import QtCore, QtWidgets

from .log_service import get_log_service

_logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handling service.

    Features:
    - Catches unhandled exceptions
    - Displays user-friendly error dialogs
    - Logs errors to log service
    - Prevents application crashes
    """

    def __init__(self):
        """Initialize the error handler."""
        self.log_service = get_log_service()
        self._error_callback: Callable[[Exception, str], None] | None = None

        # Install global exception hook
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._handle_exception

    def set_error_callback(self, callback: Callable[[Exception, str], None]):
        """
        Set a callback to be called when an error occurs.

        Args:
            callback: Function that takes (exception, traceback_str)
        """
        self._error_callback = callback

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Handle an uncaught exception.

        Args:
            exc_type: Exception type
            exc_value: Exception instance
            exc_traceback: Traceback object
        """
        # Ignore keyboard interrupt (Ctrl+C)
        if issubclass(exc_type, KeyboardInterrupt):
            self._original_excepthook(exc_type, exc_value, exc_traceback)
            return

        # Format traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_str = "".join(tb_lines)

        # Log the error
        error_msg = f"Unhandled exception: {exc_type.__name__}: {exc_value}"
        self.log_service.error(error_msg, "Error Handler")
        self.log_service.debug(f"Traceback:\n{tb_str}", "Error Handler")

        # Show error dialog
        self.show_error_dialog(
            "Unexpected Error", f"An unexpected error occurred:\n\n{exc_value}", tb_str
        )

        # Call custom callback if set
        if self._error_callback:
            try:
                self._error_callback(exc_value, tb_str)
            except Exception as e:
                _logger.error("Error in error callback: %s", e)

    def show_error_dialog(self, title: str, message: str, details: str = ""):
        """
        Show an error dialog to the user.

        Args:
            title: Dialog title
            message: User-friendly error message
            details: Technical details (traceback, etc.)
        """
        import os

        # Skip dialogs in headless environments (CI, tests) to avoid hanging
        qpa_platform = os.environ.get("QT_QPA_PLATFORM", "").lower()
        if qpa_platform in ("offscreen", "minimal", "vnc"):
            _logger.error("ERROR: %s - %s", title, message)
            if details:
                _logger.debug("Details:\n%s", details)
            return

        # Get the QApplication instance
        app = QtWidgets.QApplication.instance()
        if not app:
            # No Qt application running, log to console
            _logger.error("ERROR: %s - %s", title, message)
            if details:
                _logger.debug("Details:\n%s", details)
            return

        # Create error dialog
        msg_box = QtWidgets.QMessageBox()
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        if details:
            msg_box.setDetailedText(details)

        msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def handle_error(self, error: Exception, context: str = "", show_dialog: bool = True):
        """
        Handle an error that was caught in a try/except block.

        Args:
            error: The exception that was caught
            context: Context information (e.g., "while loading file")
            show_dialog: Whether to show an error dialog
        """
        # Get traceback
        tb_str = traceback.format_exc()

        # Log the error
        error_msg = f"Error {context}: {type(error).__name__}: {error}"
        self.log_service.error(error_msg, "Error Handler")
        self.log_service.debug(f"Traceback:\n{tb_str}", "Error Handler")

        # Show dialog if requested
        if show_dialog:
            user_msg = f"An error occurred {context}:\n\n{error}"
            self.show_error_dialog("Error", user_msg, tb_str)

        # Call custom callback if set
        if self._error_callback:
            try:
                self._error_callback(error, tb_str)
            except Exception as e:
                _logger.error("Error in error callback: %s", e)


# Global singleton instance
_error_handler: ErrorHandler | None = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_errors(suppress: bool = False):
    """
    Decorator factory to wrap a function with error handling.

    By default, logs errors and re-raises them. Set suppress=True only
    for truly recoverable errors.

    Usage:
        # Default: logs and re-raises (RECOMMENDED)
        @handle_errors()
        def my_function():
            pass

        # Suppress mode: logs and returns None (USE SPARINGLY)
        @handle_errors(suppress=True)
        def optional_function():
            pass

    Args:
        suppress: If True, suppress exception after logging (default: False)

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler()
                context = f"in {func.__name__}"
                handler.handle_error(e, context)
                if suppress:
                    return None
                raise  # Re-raise by default

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


class ErrorContext:
    """
    Context manager for error handling.

    By default, logs and re-raises exceptions. Set suppress=True only for
    truly recoverable errors where you want to continue execution.

    Usage:
        # Default: logs error and re-raises (RECOMMENDED)
        with ErrorContext("loading file"):
            load_file(path)

        # Suppress mode: logs error and continues (USE SPARINGLY)
        with ErrorContext("optional operation", suppress=True):
            optional_operation()
    """

    def __init__(self, context: str, show_dialog: bool = True, suppress: bool = False):
        """
        Initialize error context.

        Args:
            context: Context description (e.g., "loading file")
            show_dialog: Whether to show error dialog on error
            suppress: If True, suppress exception after logging (default: False)
                     WARNING: Only use for truly recoverable errors!
        """
        self.context = context
        self.show_dialog = show_dialog
        self.suppress = suppress
        self.handler = get_error_handler()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is not None:
            # An exception occurred - always log it
            self.handler.handle_error(exc_value, self.context, self.show_dialog)
            # Only suppress if explicitly requested
            # Default behavior: re-raise the exception
            return self.suppress
        return False


# Install Qt message handler to catch Qt warnings/errors
def qt_message_handler(mode, context, message):
    """Handle Qt messages and log them."""
    log = get_log_service()

    # Map Qt message types to log levels
    if mode == QtCore.QtMsgType.QtDebugMsg:
        log.debug(message, "Qt")
    elif mode == QtCore.QtMsgType.QtInfoMsg:
        log.info(message, "Qt")
    elif mode == QtCore.QtMsgType.QtWarningMsg:
        log.warning(message, "Qt")
    elif mode == QtCore.QtMsgType.QtCriticalMsg:
        log.error(f"Critical: {message}", "Qt")
    elif mode == QtCore.QtMsgType.QtFatalMsg:
        log.error(f"Fatal: {message}", "Qt")
        # Don't suppress fatal errors
        sys.stderr.write(f"Qt Fatal Error: {message}\n")


def install_qt_message_handler():
    """Install the Qt message handler."""
    QtCore.qInstallMessageHandler(qt_message_handler)
