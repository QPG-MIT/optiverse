"""
Collaboration Manager - Bridge between UI and network layer.

Manages item synchronization, command broadcasting, and state reconciliation
for real-time collaborative editing.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from PyQt6.QtCore import QObject, pyqtSignal

from .collaboration_service import CollaborationService
from .log_service import get_log_service

if TYPE_CHECKING:
    from ..ui.views.main_window import MainWindow


class CollaborationManager(QObject):
    """
    Manages collaboration state and coordinates between UI and network.
    
    Responsibilities:
    - Track local vs remote changes
    - Broadcast local changes to other users
    - Apply remote changes to local scene
    - Handle conflicts and synchronization
    """
    
    # Signals
    remote_item_added = pyqtSignal(str, dict)  # item_type, data
    remote_item_moved = pyqtSignal(str, dict)  # item_uuid, data
    remote_item_removed = pyqtSignal(str)  # item_uuid
    remote_item_updated = pyqtSignal(str, dict)  # item_uuid, data
    status_changed = pyqtSignal(str)  # status message
    
    def __init__(self, main_window: MainWindow, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.main_window = main_window
        self.collaboration_service = CollaborationService(self)
        self.enabled = False
        self._suppress_broadcast = False  # Flag to prevent re-broadcasting remote changes
        
        # Get log service
        self.log = get_log_service()
        
        # Track items by UUID
        self.item_uuid_map: Dict[str, Any] = {}  # uuid -> item object
        
        # Connect signals
        self.collaboration_service.connected.connect(self._on_connected)
        self.collaboration_service.disconnected.connect(self._on_disconnected)
        self.collaboration_service.command_received.connect(self._on_command_received)
        self.collaboration_service.sync_state_received.connect(self._on_sync_state_received)
        self.collaboration_service.user_joined.connect(self._on_user_joined)
        self.collaboration_service.user_left.connect(self._on_user_left)
        self.collaboration_service.error_occurred.connect(self._on_error)
        self.collaboration_service.connection_acknowledged.connect(self._on_connection_acknowledged)
    
    def connect_to_session(self, server_url: str, session_id: str, user_id: str) -> None:
        """
        Connect to a collaboration session.
        
        Args:
            server_url: WebSocket server URL (e.g., ws://localhost:8765)
            session_id: Session ID to join
            user_id: Your user ID/name
        """
        self.collaboration_service.set_server_url(server_url)
        self.collaboration_service.connect_to_session(session_id, user_id)
        self.status_changed.emit(f"Connecting to {server_url}...")
    
    def disconnect(self) -> None:
        """Disconnect from current session."""
        self.collaboration_service.disconnect_from_session()
        self.enabled = False
        self.item_uuid_map.clear()
    
    def is_connected(self) -> bool:
        """Check if connected to a collaboration session."""
        return self.collaboration_service.is_connected()
    
    def rebuild_uuid_map(self) -> None:
        """Rebuild the UUID map from current scene items."""
        self.item_uuid_map.clear()
        if not hasattr(self.main_window, 'scene'):
            return
        
        for item in self.main_window.scene.items():
            if hasattr(item, 'item_uuid'):
                self.item_uuid_map[item.item_uuid] = item
    
    def broadcast_add_item(self, item: Any) -> None:
        """
        Broadcast that an item was added locally.
        
        Args:
            item: The item that was added
        """
        if not self.enabled or self._suppress_broadcast:
            return
        
        if not hasattr(item, 'item_uuid') or not hasattr(item, 'to_dict'):
            return
        
        item_type = self._get_item_type(item)
        if not item_type:
            return
        
        # Add to UUID map
        self.item_uuid_map[item.item_uuid] = item
        
        # Broadcast to other users
        data = item.to_dict()
        self.collaboration_service.send_command(
            action="add_item",
            item_type=item_type,
            item_id=item.item_uuid,
            data=data
        )
    
    def broadcast_move_item(self, item: Any) -> None:
        """
        Broadcast that an item was moved locally.
        
        Args:
            item: The item that was moved
        """
        if not self.enabled or self._suppress_broadcast:
            return
        
        if not hasattr(item, 'item_uuid') or not hasattr(item, 'to_dict'):
            return
        
        item_type = self._get_item_type(item)
        if not item_type:
            return
        
        data = item.to_dict()
        self.collaboration_service.send_command(
            action="move_item",
            item_type=item_type,
            item_id=item.item_uuid,
            data=data
        )
    
    def broadcast_remove_item(self, item: Any) -> None:
        """
        Broadcast that an item was removed locally.
        
        Args:
            item: The item that was removed
        """
        if not self.enabled or self._suppress_broadcast:
            return
        
        if not hasattr(item, 'item_uuid'):
            return
        
        item_type = self._get_item_type(item)
        if not item_type:
            return
        
        # Remove from UUID map
        if item.item_uuid in self.item_uuid_map:
            del self.item_uuid_map[item.item_uuid]
        
        self.collaboration_service.send_command(
            action="remove_item",
            item_type=item_type,
            item_id=item.item_uuid,
            data={}
        )
    
    def broadcast_update_item(self, item: Any) -> None:
        """
        Broadcast that an item was updated locally.
        
        Args:
            item: The item that was updated
        """
        if not self.enabled or self._suppress_broadcast:
            return
        
        if not hasattr(item, 'item_uuid') or not hasattr(item, 'to_dict'):
            return
        
        item_type = self._get_item_type(item)
        if not item_type:
            return
        
        data = item.to_dict()
        self.collaboration_service.send_command(
            action="update_item",
            item_type=item_type,
            item_id=item.item_uuid,
            data=data
        )
    
    def _get_item_type(self, item: Any) -> Optional[str]:
        """Get the type string for an item."""
        class_name = item.__class__.__name__
        type_map = {
            'SourceItem': 'source',
            'LensItem': 'lens',
            'MirrorItem': 'mirror',
            'BeamsplitterItem': 'beamsplitter',
            'DichroicItem': 'dichroic',
            'WaveplateItem': 'waveplate',
            'SLMItem': 'slm',
            'RulerItem': 'ruler',
            'TextNoteItem': 'text',
        }
        return type_map.get(class_name)
    
    def _on_connected(self) -> None:
        """Handle successful connection."""
        self.status_changed.emit("Connected!")
    
    def _on_disconnected(self) -> None:
        """Handle disconnection."""
        self.enabled = False
        self.item_uuid_map.clear()
        self.status_changed.emit("Disconnected")
    
    def _on_connection_acknowledged(self, data: Dict[str, Any]) -> None:
        """Handle connection acknowledgment with user list."""
        self.enabled = True
        users = data.get('users', [])
        user_count = len(users)
        self.status_changed.emit(f"Connected ({user_count} users)")
        
        # Request initial state sync
        self.collaboration_service.request_sync()
        
        # Rebuild UUID map from current scene
        self.rebuild_uuid_map()
    
    def _on_command_received(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming command from another user.
        
        Args:
            message: Command message from server
        """
        if not self.enabled:
            return
        
        command = message.get('command', {})
        action = command.get('action')
        item_type = command.get('item_type')
        item_id = command.get('item_id')
        data = command.get('data', {})
        
        self.log.debug(f"Processing remote command: {action} {item_type} {item_id}", "Collaboration")
        
        # Suppress broadcasting while applying remote changes
        self._suppress_broadcast = True
        try:
            if action == 'add_item':
                self._apply_add_item(item_type, data)
            elif action == 'move_item':
                self._apply_move_item(item_id, data)
            elif action == 'remove_item':
                self._apply_remove_item(item_id)
            elif action == 'update_item':
                self._apply_update_item(item_id, data)
        finally:
            self._suppress_broadcast = False
    
    def _apply_add_item(self, item_type: str, data: Dict[str, Any]) -> None:
        """Apply remote add item command."""
        self.remote_item_added.emit(item_type, data)
    
    def _apply_move_item(self, item_uuid: str, data: Dict[str, Any]) -> None:
        """Apply remote move item command."""
        if item_uuid in self.item_uuid_map:
            item = self.item_uuid_map[item_uuid]
            if hasattr(item, 'setPos') and 'x_mm' in data and 'y_mm' in data:
                item.setPos(data['x_mm'], data['y_mm'])
            if hasattr(item, 'setRotation') and 'angle_deg' in data:
                item.setRotation(data['angle_deg'])
        else:
            # Item not found, might need to add it
            self.remote_item_moved.emit(item_uuid, data)
    
    def _apply_remove_item(self, item_uuid: str) -> None:
        """Apply remote remove item command."""
        if item_uuid in self.item_uuid_map:
            item = self.item_uuid_map[item_uuid]
            if hasattr(self.main_window, 'scene') and self.main_window.scene:
                self.main_window.scene.removeItem(item)
            del self.item_uuid_map[item_uuid]
        self.remote_item_removed.emit(item_uuid)
    
    def _apply_update_item(self, item_uuid: str, data: Dict[str, Any]) -> None:
        """Apply remote update item command."""
        if item_uuid in self.item_uuid_map:
            item = self.item_uuid_map[item_uuid]
            if hasattr(item, 'from_dict'):
                item.from_dict(data)
        self.remote_item_updated.emit(item_uuid, data)
    
    def _on_sync_state_received(self, message: Dict[str, Any]) -> None:
        """Handle full state synchronization from server."""
        state = message.get('state')
        if state:
            self.log.debug("Applying state sync...", "Collaboration")
            # TODO: Apply full state (requires scene serialization/deserialization)
    
    def _on_user_joined(self, user_id: str) -> None:
        """Handle user joined notification."""
        self.status_changed.emit(f"{user_id} joined")
    
    def _on_user_left(self, user_id: str) -> None:
        """Handle user left notification."""
        self.status_changed.emit(f"{user_id} left")
    
    def _on_error(self, error: str) -> None:
        """Handle collaboration error."""
        self.status_changed.emit(f"Error: {error}")

