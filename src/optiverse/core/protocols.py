"""
Protocols for structural subtyping in Optiverse.

This module defines Protocol classes that enable structural subtyping (duck typing
with type checking support). Use these instead of hasattr() checks for better
type safety and IDE support.

Example usage:
    from optiverse.core.protocols import Editable, Undoable
    
    def process_editable(item: Editable) -> None:
        # Type checker knows item has edited signal and to_dict method
        item.edited.emit()
        data = item.to_dict()
    
    # Better than:
    def process_item(item) -> None:
        if hasattr(item, 'edited'):
            item.edited.emit()  # No type checking here
"""
from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

from PyQt6.QtCore import pyqtSignal


@runtime_checkable
class Editable(Protocol):
    """
    Protocol for items that can be edited and emit edit signals.
    
    Items implementing this protocol:
    - Have an `edited` signal that emits when the item is modified
    - Have an `update()` method to refresh visual state
    """
    
    edited: pyqtSignal
    
    def update(self) -> None:
        """Refresh the visual representation."""
        ...


@runtime_checkable
class Serializable(Protocol):
    """
    Protocol for items that can be serialized to/from dictionaries.
    
    Items implementing this protocol:
    - Can convert to a dict via `to_dict()`
    - Have a type_name for identification
    - Have a unique item_uuid for collaboration
    """
    
    type_name: str
    item_uuid: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert item state to a dictionary for serialization."""
        ...


@runtime_checkable
class Undoable(Protocol):
    """
    Protocol for items that support undo/redo state capture.
    
    Items implementing this protocol:
    - Can capture current state via `capture_state()`
    - Can restore state via `apply_state()`
    """
    
    def capture_state(self) -> Dict[str, Any]:
        """Capture current state for undo/redo."""
        ...
    
    def apply_state(self, state: Dict[str, Any]) -> None:
        """Apply a previously captured state."""
        ...


@runtime_checkable
class Lockable(Protocol):
    """
    Protocol for items that can be locked to prevent editing.
    
    Items implementing this protocol:
    - Can check lock state via `is_locked()`
    - Can toggle lock state via `set_locked()`
    """
    
    def is_locked(self) -> bool:
        """Check if item is locked."""
        ...
    
    def set_locked(self, locked: bool) -> None:
        """Set the locked state."""
        ...


@runtime_checkable
class HasParams(Protocol):
    """
    Protocol for items that have a params dataclass.
    
    Items implementing this protocol:
    - Have a `params` attribute containing configuration
    - Can sync params from visual state
    """
    
    params: Any
    
    def _sync_params_from_item(self) -> None:
        """Synchronize params from visual state."""
        ...


@runtime_checkable
class HasShape(Protocol):
    """
    Protocol for items that have updatable geometry.
    
    Items implementing this protocol:
    - Have `_update_shape()` to update collision shape
    - Have `_update_geom()` to update visual geometry
    """
    
    def _update_shape(self) -> None:
        """Update the collision shape."""
        ...
    
    def _update_geom(self) -> None:
        """Update the visual geometry."""
        ...


@runtime_checkable
class Clonable(Protocol):
    """
    Protocol for items that can be cloned.
    
    Items implementing this protocol:
    - Can create a copy of themselves via `clone()`
    """
    
    def clone(self, offset_mm: tuple[float, float] = (20.0, 20.0)) -> Any:
        """Create a clone of this item with an offset."""
        ...


@runtime_checkable  
class HasInterfaces(Protocol):
    """
    Protocol for items that have optical interfaces.
    
    Items implementing this protocol:
    - Have an `interfaces` property returning interface definitions
    - Can get interface positions via `get_interface_positions()`
    """
    
    @property
    def interfaces(self) -> Any:
        """Get the interface definitions."""
        ...
    
    def get_interface_positions(self) -> Dict[str, tuple[float, float]]:
        """Get positions of all interfaces in scene coordinates."""
        ...


@runtime_checkable
class HasUndoStack(Protocol):
    """
    Protocol for objects that provide an undo stack.
    
    Used by items that need to push undo commands.
    """
    
    undo_stack: Any  # UndoStack


@runtime_checkable
class HasCollaboration(Protocol):
    """
    Protocol for objects that provide collaboration management.
    
    Used by items that broadcast changes during collaboration.
    """
    
    collaboration_manager: Any  # CollaborationManager


@runtime_checkable
class HasSettings(Protocol):
    """
    Protocol for objects that provide settings access.
    
    Used by objects needing access to application settings.
    """
    
    settings: Any  # SettingsService


@runtime_checkable
class HasSnapping(Protocol):
    """
    Protocol for objects that provide magnetic snapping.
    
    Used by draggable items for snap-to-interface behavior.
    """
    
    magnetic_snap: bool
    _snap_helper: Any  # SnapHelper

