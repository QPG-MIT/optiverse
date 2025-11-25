"""
Helper module to avoid circular imports when importing from core.

This provides lazy imports of undo commands and other core modules.
"""

from __future__ import annotations


def get_rotate_commands():
    """
    Get rotation command classes for undo/redo.

    Returns:
        Tuple of (RotateItemCommand, RotateItemsCommand)
    """
    from ..core.undo_commands import RotateItemCommand, RotateItemsCommand
    return RotateItemCommand, RotateItemsCommand



