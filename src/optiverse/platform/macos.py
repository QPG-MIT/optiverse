"""
macOS-specific platform utilities.

This module provides utilities for handling macOS-specific behavior,
including suppressing harmless system warnings.
"""

from __future__ import annotations

import sys


class _StderrFilter:
    """
    Filter stderr to suppress known harmless macOS warnings.

    The TSMSendMessageToUIServer warning occurs when Qt modal dialogs
    (QInputDialog, QMessageBox) are shown on macOS. This is a harmless
    warning from the Text Services Manager that clutters console output.
    """

    # Patterns to suppress (macOS TSM warnings)
    SUPPRESS_PATTERNS = [
        "TSMSendMessageToUIServer",
        "CFMessagePortSendRequest FAILED",
    ]

    def __init__(self, original_stderr):
        self._original = original_stderr

    def write(self, text):
        # Check if this message should be suppressed
        if any(pattern in text for pattern in self.SUPPRESS_PATTERNS):
            return  # Suppress the message
        self._original.write(text)

    def flush(self):
        self._original.flush()

    def __getattr__(self, name):
        return getattr(self._original, name)


def install_macos_stderr_filter() -> None:
    """
    Install a stderr filter to suppress harmless macOS warnings.

    This should be called early in application startup, before any
    Qt dialogs are shown. Only has effect on macOS; no-op on other platforms.
    """
    if sys.platform == "darwin":
        sys.stderr = _StderrFilter(sys.stderr)

