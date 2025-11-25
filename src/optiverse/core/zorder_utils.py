"""
Utility functions for z-order (stacking order) manipulation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6 import QtWidgets


def calculate_bring_to_front(
    items: list[QtWidgets.QGraphicsItem],
    scene: QtWidgets.QGraphicsScene
) -> dict[QtWidgets.QGraphicsItem, float]:
    """
    Calculate new z-values to bring items to front.
    
    Args:
        items: Items to bring to front
        scene: The graphics scene containing the items
        
    Returns:
        Dict mapping items to their new z-values
    """
    # Get all scene items and find max z-value
    all_items = scene.items()
    if not all_items:
        max_z = 0.0
    else:
        max_z = max(item.zValue() for item in all_items)
    
    # Assign new z-values starting from max + 1
    new_z_values = {}
    for i, item in enumerate(items):
        new_z_values[item] = max_z + 1 + i
    
    return new_z_values


def calculate_send_to_back(
    items: list[QtWidgets.QGraphicsItem],
    scene: QtWidgets.QGraphicsScene
) -> dict[QtWidgets.QGraphicsItem, float]:
    """
    Calculate new z-values to send items to back.
    
    Args:
        items: Items to send to back
        scene: The graphics scene containing the items
        
    Returns:
        Dict mapping items to their new z-values
    """
    # Get all scene items and find min z-value
    all_items = scene.items()
    if not all_items:
        min_z = 0.0
    else:
        min_z = min(item.zValue() for item in all_items)
    
    # Assign new z-values starting from min - len(items)
    new_z_values = {}
    for i, item in enumerate(items):
        new_z_values[item] = min_z - len(items) + i
    
    return new_z_values


def calculate_bring_forward(
    items: list[QtWidgets.QGraphicsItem],
    scene: QtWidgets.QGraphicsScene
) -> dict[QtWidgets.QGraphicsItem, float]:
    """
    Calculate new z-values to bring items forward (one step up).
    
    Args:
        items: Items to bring forward
        scene: The graphics scene containing the items
        
    Returns:
        Dict mapping items to their new z-values
    """
    new_z_values = {}
    for item in items:
        current_z = item.zValue()
        # Increment by 1
        new_z_values[item] = current_z + 1
    
    return new_z_values


def calculate_send_backward(
    items: list[QtWidgets.QGraphicsItem],
    scene: QtWidgets.QGraphicsScene
) -> dict[QtWidgets.QGraphicsItem, float]:
    """
    Calculate new z-values to send items backward (one step down).
    
    Args:
        items: Items to send backward
        scene: The graphics scene containing the items
        
    Returns:
        Dict mapping items to their new z-values
    """
    new_z_values = {}
    for item in items:
        current_z = item.zValue()
        # Decrement by 1
        new_z_values[item] = current_z - 1
    
    return new_z_values


def apply_z_order_change(
    items: list[QtWidgets.QGraphicsItem],
    operation: str,
    scene: QtWidgets.QGraphicsScene,
    undo_stack=None
) -> None:
    """
    Apply z-order change operation with optional undo support.
    
    Args:
        items: Items to change z-order for
        operation: One of "bring_to_front", "send_to_back", "bring_forward", "send_backward"
        scene: The graphics scene containing the items
        undo_stack: Optional undo stack to push command to
    """
    if not items:
        return
    
    # Store old z-values
    old_z_values = {item: item.zValue() for item in items}
    
    # Calculate new z-values based on operation
    if operation == "bring_to_front":
        new_z_values = calculate_bring_to_front(items, scene)
    elif operation == "send_to_back":
        new_z_values = calculate_send_to_back(items, scene)
    elif operation == "bring_forward":
        new_z_values = calculate_bring_forward(items, scene)
    elif operation == "send_backward":
        new_z_values = calculate_send_backward(items, scene)
    else:
        return
    
    # Apply changes via undo command if undo_stack provided
    if undo_stack is not None:
        from .undo_commands import ZOrderCommand
        cmd = ZOrderCommand(items, old_z_values, new_z_values)
        undo_stack.push(cmd)
    else:
        # Apply directly without undo support
        for item in items:
            item.setZValue(new_z_values[item])


def get_z_order_items_from_item(
    item: QtWidgets.QGraphicsItem,
) -> list[QtWidgets.QGraphicsItem]:
    """
    Get items for z-order operations based on selection state.
    
    If the item is selected, returns all selected items.
    Otherwise returns just the single item.
    
    Args:
        item: The item to get z-order targets for
        
    Returns:
        List of items to apply z-order change to
    """
    if not item.scene():
        return []
    
    if item.isSelected():
        # All QGraphicsItems have setZValue, no filtering needed
        return list(item.scene().selectedItems())
    else:
        return [item]


def handle_z_order_from_menu(
    item: QtWidgets.QGraphicsItem,
    selected_action,
    action_map: dict,
) -> None:
    """
    Handle z-order menu action selection and apply the change.
    
    This helper simplifies the boilerplate in annotation items' context menus.
    
    Args:
        item: The item whose context menu was triggered
        selected_action: The QAction that was selected
        action_map: Dict mapping QActions to operation strings
                   e.g., {act_bring_to_front: "bring_to_front", ...}
    
    Example:
        action_map = {
            act_bring_to_front: "bring_to_front",
            act_bring_forward: "bring_forward",
            act_send_backward: "send_backward",
            act_send_to_back: "send_to_back",
        }
        handle_z_order_from_menu(self, selected_action, action_map)
    """
    from .protocols import HasUndoStack
    
    operation = action_map.get(selected_action)
    if not operation:
        return
    
    if not item.scene():
        return
    
    items = get_z_order_items_from_item(item)
    if not items:
        return
    
    # Get undo stack from main window
    undo_stack = None
    views = item.scene().views()
    if views:
        main_window = views[0].window()
        if isinstance(main_window, HasUndoStack):
            undo_stack = main_window.undo_stack
    
    apply_z_order_change(items, operation, item.scene(), undo_stack)

