"""Layer model - single source of truth for z-order.

This model holds the authoritative order of items in the scene.
The tree view displays this order, and z-values are derived from it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets

if TYPE_CHECKING:
    pass


class LayerModel(QtCore.QObject):
    """
    Model holding z-order state. Single source of truth.
    
    The model maintains an ordered list of item UUIDs from top to bottom.
    Z-values are derived from this order (top = highest z, bottom = lowest).
    
    Signals:
        orderChanged: Emitted when the order changes (add, remove, move)
    """

    orderChanged = QtCore.pyqtSignal()

    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self._order: list[str] = []  # UUIDs in z-order (top to bottom)
        self._scene: QtWidgets.QGraphicsScene | None = None

    def set_scene(self, scene: QtWidgets.QGraphicsScene | None) -> None:
        """Set the graphics scene."""
        self._scene = scene
        if scene:
            self._sync_from_scene()

    def _sync_from_scene(self) -> None:
        """
        Sync model order from current scene z-values.
        
        Called once when scene is set to initialize model from existing state.
        """
        if not self._scene:
            return

        # Collect items with z-values
        items_with_z: list[tuple[float, str]] = []
        for item in self._scene.items():
            if hasattr(item, "item_uuid") and hasattr(item, "type_name"):
                items_with_z.append((item.zValue(), item.item_uuid))

        # Sort by z-value descending (highest z = top of list)
        items_with_z.sort(key=lambda x: x[0], reverse=True)
        
        self._order = [uuid for _, uuid in items_with_z]

    def sync_with_scene(self) -> bool:
        """
        Sync model order with current scene items.
        
        This is a batch operation - adds new items and removes deleted items
        with a single emit and single z-value apply.
        
        Returns:
            True if order changed, False otherwise.
        """
        if not self._scene:
            return False
        
        # Get current scene UUIDs
        scene_uuids: set[str] = set()
        for item in self._scene.items():
            if hasattr(item, "item_uuid") and hasattr(item, "type_name"):
                scene_uuids.add(item.item_uuid)
        
        model_uuids = set(self._order)
        new_uuids = scene_uuids - model_uuids
        deleted_uuids = model_uuids - scene_uuids
        
        if not new_uuids and not deleted_uuids:
            return False  # No changes
        
        # New items go to top, existing items keep their relative order
        new_items = list(new_uuids)
        self._order = new_items + [u for u in self._order if u in scene_uuids]
        
        # Single apply and emit
        self._apply_to_scene()
        self.orderChanged.emit()
        return True

    # --- Public API ---

    def add_item(self, uuid: str, at_top: bool = True) -> None:
        """
        Add item to order.
        
        Args:
            uuid: Item UUID to add
            at_top: If True, add at top (default). If False, add at bottom.
        """
        if uuid in self._order:
            return  # Already in order
        
        if at_top:
            self._order.insert(0, uuid)
        else:
            self._order.append(uuid)
        
        self._apply_to_scene()
        self.orderChanged.emit()

    def remove_item(self, uuid: str) -> None:
        """Remove item from order."""
        if uuid in self._order:
            self._order.remove(uuid)
            self.orderChanged.emit()

    def move_item(self, uuid: str, new_index: int) -> None:
        """
        Move item to new position in order.
        
        Args:
            uuid: Item UUID to move
            new_index: New index (0 = top)
        """
        if uuid not in self._order:
            return
        
        old_index = self._order.index(uuid)
        if old_index == new_index:
            return
        
        self._order.remove(uuid)
        self._order.insert(new_index, uuid)
        
        self._apply_to_scene()
        self.orderChanged.emit()

    def reorder(self, new_order: list[str]) -> None:
        """
        Set a completely new order.
        
        Args:
            new_order: List of UUIDs in new order (top to bottom)
        """
        self._order = list(new_order)
        self._apply_to_scene()
        self.orderChanged.emit()

    def get_order(self) -> list[str]:
        """Get current order (top to bottom)."""
        return list(self._order)

    def get_index(self, uuid: str) -> int:
        """Get index of item in order (-1 if not found)."""
        try:
            return self._order.index(uuid)
        except ValueError:
            return -1

    def __len__(self) -> int:
        """Get number of items in order."""
        return len(self._order)

    def __contains__(self, uuid: str) -> bool:
        """Check if UUID is in order."""
        return uuid in self._order

    # --- Z-Value Management ---

    def _apply_to_scene(self) -> None:
        """Apply z-values to scene items based on model order."""
        if not self._scene:
            return

        # Build UUID to item mapping
        uuid_to_item: dict[str, QtWidgets.QGraphicsItem] = {}
        for item in self._scene.items():
            if hasattr(item, "item_uuid"):
                uuid_to_item[item.item_uuid] = item

        # Assign z-values: top of list (index 0) = highest z
        total = len(self._order)
        for i, uuid in enumerate(self._order):
            if item := uuid_to_item.get(uuid):
                # i=0 (top) gets z = total-1 (highest)
                # i=total-1 (bottom) gets z = 0 (lowest)
                z_value = total - 1 - i
                item.setZValue(z_value)

    def get_z_value(self, uuid: str) -> float:
        """
        Get the z-value for an item based on its position in the order.
        
        Args:
            uuid: Item UUID
            
        Returns:
            Z-value (higher = on top), or 0 if not found
        """
        if uuid not in self._order:
            return 0.0
        
        index = self._order.index(uuid)
        total = len(self._order)
        return float(total - 1 - index)

