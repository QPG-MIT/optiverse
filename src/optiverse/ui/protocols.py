"""
Protocol definitions for Optiverse UI components.

Contains typing protocols used across UI modules to define interfaces
without creating circular imports or tight coupling.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class HasComponentEditor(Protocol):
    """
    Protocol for windows that can open a component editor.
    
    Used by LibraryTree to communicate with the main window without
    direct imports.
    """

    def open_component_editor(self, component: dict | None = None) -> None:
        """
        Open the component editor.
        
        Args:
            component: Optional component data to load into the editor.
                      If None, opens with default/empty state.
        """
        ...


@runtime_checkable  
class HasUndoStack(Protocol):
    """
    Protocol for windows that have an undo stack.
    
    Used to access undo functionality without direct coupling.
    """

    @property
    def undo_stack(self) -> object:
        """Get the undo stack."""
        ...

