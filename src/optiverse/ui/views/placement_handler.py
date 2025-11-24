"""Component placement mode handler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, Optional, Union

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.component_types import ComponentType

if TYPE_CHECKING:
    from ...objects import GraphicsView
    from ...core.undo_stack import UndoStack
    from ...services.log_service import LogService


class PlacementHandler:
    """
    Handler for component placement mode.
    
    Manages the placement workflow including ghost preview, mouse tracking,
    and component creation.
    """
    
    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        view: "GraphicsView",
        undo_stack: "UndoStack",
        log_service: "LogService",
        component_templates: Dict[str, dict],
        snap_to_grid_getter: Callable[[], bool],
        connect_item_signals: Callable[[QtWidgets.QGraphicsItem], None],
        schedule_retrace: Callable[[], None],
        broadcast_add_item: Callable[[QtWidgets.QGraphicsItem], None],
    ):
        """
        Initialize the placement handler.
        
        Args:
            scene: The graphics scene
            view: The graphics view
            undo_stack: Undo stack for commands
            log_service: Logging service
            component_templates: Dictionary mapping component types to templates
            snap_to_grid_getter: Callable to check if snap to grid is enabled
            connect_item_signals: Callback to connect item signals
            schedule_retrace: Callback to schedule ray retracing
            broadcast_add_item: Callback to broadcast item to collaboration
        """
        self.scene = scene
        self.view = view
        self.undo_stack = undo_stack
        self.log_service = log_service
        self.component_templates = component_templates
        self._get_snap_to_grid = snap_to_grid_getter
        self._connect_item_signals = connect_item_signals
        self._schedule_retrace = schedule_retrace
        self._broadcast_add_item = broadcast_add_item
        
        # State
        self._active = False
        self._component_type: Optional[str] = None
        self._ghost: Optional[QtWidgets.QGraphicsItem] = None
    
    @property
    def is_active(self) -> bool:
        """Check if placement mode is active."""
        return self._active
    
    @property
    def component_type(self) -> Optional[str]:
        """Get the current component type being placed."""
        return self._component_type
    
    def activate(self, component_type: str) -> None:
        """
        Activate placement mode for a component type.
        
        Args:
            component_type: Type of component to place (source, lens, mirror, etc.)
        """
        # Cancel any existing placement first
        if self._active:
            self._cleanup_ghost()
        
        self._active = True
        self._component_type = component_type
        
        # Enable mouse tracking to get move events without button press
        self.view.setMouseTracking(True)
        self.view.viewport().setMouseTracking(True)
        
        # Change cursor to crosshair
        self.view.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        
        # Show tooltip
        QtWidgets.QToolTip.showText(
            QtGui.QCursor.pos(),
            f"Click to place {component_type}. Right-click or Escape to cancel."
        )
    
    def deactivate(self) -> str | None:
        """
        Deactivate placement mode and clean up.
        
        Returns:
            The component type that was active, or None if not active
        """
        if not self._active and self._ghost is None:
            return None
        
        prev_type = self._component_type
        
        # Clean up ghost
        self._cleanup_ghost()
        
        # Reset state
        self._active = False
        self._component_type = None
        
        # Restore cursor and mouse tracking
        self._send_synthetic_mouse_move()
        self.view.unsetCursor()
        self.view.setMouseTracking(False)
        self.view.viewport().setMouseTracking(False)
        
        return prev_type
    
    def _cleanup_ghost(self) -> None:
        """Remove and clean up the ghost preview."""
        if self._ghost is not None:
            if self._ghost.scene() is not None:
                # Get bounding rect before removal for proper viewport update
                ghost_rect = self._ghost.sceneBoundingRect()
                # Expand rect to account for cosmetic pen rendering beyond bounds
                ghost_rect = ghost_rect.adjusted(-20, -20, 20, 20)
                # Hide first to prevent flicker
                self._ghost.hide()
                self.scene.removeItem(self._ghost)
                # Aggressive viewport update to clear any rendering artifacts
                self.scene.update(ghost_rect)
                self.scene.invalidate(ghost_rect)
                self.view.viewport().update()
                # Schedule another update to catch any stragglers
                QtCore.QTimer.singleShot(0, self.view.viewport().update)
            # Schedule deletion to ensure proper cleanup
            self._ghost.deleteLater()
            self._ghost = None
    
    def _send_synthetic_mouse_move(self) -> None:
        """Send synthetic mouse move event to update Qt's position tracking."""
        cursor_pos = self.view.mapFromGlobal(QtGui.QCursor.pos())
        move_event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove,
            QtCore.QPointF(cursor_pos),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier
        )
        # Send to VIEW first (critical for wheelEvent which is received by the view)
        QtWidgets.QApplication.sendEvent(self.view, move_event)
        # Also send to viewport (for completeness)
        QtWidgets.QApplication.sendEvent(self.view.viewport(), move_event)
        # Process events to ensure the mouse position update completes
        QtWidgets.QApplication.processEvents()
    
    def handle_mouse_move(self, scene_pos: QtCore.QPointF) -> bool:
        """
        Handle mouse move event during placement mode.
        
        Args:
            scene_pos: Current mouse position in scene coordinates
            
        Returns:
            True if event was handled, False otherwise
        """
        if not self._active:
            return False
        
        # Create ghost if it doesn't exist yet
        if self._ghost is None:
            self._create_ghost(scene_pos)
        else:
            self._update_ghost(scene_pos)
        
        return True
    
    def handle_click(self, scene_pos: QtCore.QPointF, button: QtCore.Qt.MouseButton) -> bool:
        """
        Handle mouse click event during placement mode.
        
        Args:
            scene_pos: Click position in scene coordinates
            button: Mouse button that was clicked
            
        Returns:
            True if event was handled, False otherwise
        """
        if not self._active:
            return False
        
        if button == QtCore.Qt.MouseButton.LeftButton:
            # Place the component
            self._place_component(scene_pos)
            # Clear the ghost so a new one is created on next move
            self._cleanup_ghost()
            return True
        
        elif button == QtCore.Qt.MouseButton.RightButton:
            # Cancel placement (caller should handle unchecking toolbar buttons)
            return True
        
        return False
    
    def _create_ghost(self, scene_pos: QtCore.QPointF) -> None:
        """Create a ghost preview for the component being placed."""
        from ...core.models import SourceParams
        from ...objects import SourceItem, TextNoteItem, RectangleItem
        from ...objects.component_factory import ComponentFactory
        
        # Clear any existing ghost
        self._cleanup_ghost()
        
        component_type = self._component_type
        ghost = None
        
        # Normalize component type to enum for comparison
        if isinstance(component_type, str):
            try:
                component_type = ComponentType(component_type)
            except ValueError:
                pass  # Keep as string for unknown types
        
        # Create ghost based on component type
        if component_type == ComponentType.SOURCE:
            # Source is a special case - still uses SourceItem directly
            params = SourceParams(x_mm=scene_pos.x(), y_mm=scene_pos.y())
            ghost = SourceItem(params)
        
        elif component_type in (ComponentType.LENS, ComponentType.MIRROR, ComponentType.BEAMSPLITTER):
            # Use ComponentFactory with library templates for interface-based components
            template = self.component_templates.get(component_type)
            if template is None:
                self.log_service.warning(
                    f"No template found for component type: {component_type}",
                    "Placement"
                )
                return
            
            # Create a copy of the template without the sprite image
            template_copy = dict(template)
            template_copy["image_path"] = ""  # Remove sprite to show interface lines only
            
            ghost = ComponentFactory.create_item_from_dict(
                template_copy,
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y()
            )
            if ghost is None:
                self.log_service.error(
                    f"Failed to create ghost for component type: {component_type}",
                    "Placement"
                )
                return
        
        elif component_type == "text":
            ghost = TextNoteItem("Text")
            ghost.setPos(scene_pos)
        
        elif component_type == "rectangle":
            ghost = RectangleItem(width_mm=60.0, height_mm=40.0)
            ghost.setPos(scene_pos)
        
        else:
            return
        
        # Make it semi-transparent for ghost effect
        ghost.setOpacity(0.5)
        
        # Disable caching to prevent rendering artifacts
        ghost.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.NoCache)
        
        # Add to scene
        self.scene.addItem(ghost)
        self._ghost = ghost
    
    def _update_ghost(self, scene_pos: QtCore.QPointF) -> None:
        """Update the position of the placement ghost."""
        if self._ghost is None:
            return
        
        # Get old rect for proper invalidation (expanded for cosmetic pens)
        old_rect = self._ghost.sceneBoundingRect().adjusted(-20, -20, 20, 20)
        
        # Apply snap to grid if enabled
        if self._get_snap_to_grid():
            scene_pos = QtCore.QPointF(round(scene_pos.x()), round(scene_pos.y()))
        
        # Update position
        self._ghost.setPos(scene_pos)
        
        # Force scene update in old and new areas to prevent artifacts
        new_rect = self._ghost.sceneBoundingRect().adjusted(-20, -20, 20, 20)
        update_rect = old_rect.united(new_rect)
        self.scene.update(update_rect)
        self.scene.invalidate(update_rect)
    
    def _place_component(self, scene_pos: QtCore.QPointF) -> None:
        """Place a component at the specified scene position."""
        from ...core.models import SourceParams
        from ...core.undo_commands import AddItemCommand
        from ...objects import SourceItem, TextNoteItem, RectangleItem
        from ...objects.component_factory import ComponentFactory
        
        # Apply snap to grid if enabled
        if self._get_snap_to_grid():
            scene_pos = QtCore.QPointF(round(scene_pos.x()), round(scene_pos.y()))
        
        component_type = self._component_type
        item = None
        
        # Normalize component type to enum for comparison
        if isinstance(component_type, str):
            try:
                component_type = ComponentType(component_type)
            except ValueError:
                pass  # Keep as string for unknown types
        
        # Create the component based on type
        if component_type == ComponentType.SOURCE:
            params = SourceParams(x_mm=scene_pos.x(), y_mm=scene_pos.y())
            item = SourceItem(params)
        
        elif component_type in (ComponentType.LENS, ComponentType.MIRROR, ComponentType.BEAMSPLITTER):
            template = self.component_templates.get(component_type)
            if template is None:
                self.log_service.error(
                    f"No template found for component type: {component_type}",
                    "Placement"
                )
                return
            
            template_copy = dict(template)
            template_copy["image_path"] = ""  # Remove sprite to show interface lines only
            
            item = ComponentFactory.create_item_from_dict(
                template_copy,
                x_mm=scene_pos.x(),
                y_mm=scene_pos.y()
            )
            if item is None:
                self.log_service.error(
                    f"Failed to create component for type: {component_type}",
                    "Placement"
                )
                return
        
        elif component_type == "text":
            item = TextNoteItem("Text")
            item.setPos(scene_pos)
        
        elif component_type == "rectangle":
            item = RectangleItem(width_mm=60.0, height_mm=40.0)
            item.setPos(scene_pos)
        
        else:
            return
        
        # Connect signals for optical components (skip annotations like text/rectangle)
        if component_type not in ("text", "rectangle"):
            self._connect_item_signals(item)
        
        # Add to scene with undo support
        cmd = AddItemCommand(self.scene, item)
        self.undo_stack.push(cmd)
        item.setSelected(True)
        
        # Broadcast addition to collaboration (for optical components only)
        if component_type not in ("text", "rectangle"):
            self._broadcast_add_item(item)
        
        # Retrace if enabled (only for optical components)
        if component_type not in ("text", "rectangle"):
            self._schedule_retrace()
        
        # Force Qt to update its internal mouse position tracking
        self._send_synthetic_mouse_move()

