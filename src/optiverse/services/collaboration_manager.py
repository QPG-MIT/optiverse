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
    - Manage session roles (host/client)
    - Handle initial state sync and reconnection
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
        
        # Session management
        self.role: Optional[str] = None  # "host" or "client"
        self.session_id: Optional[str] = None
        self.session_version: int = 0  # Version counter for state tracking
        self.initial_sync_complete: bool = False  # Flag for initial sync
        
        # Reconnection handling
        self.needs_resync: bool = False  # Flag to trigger resync on reconnect
        self.last_known_state: Optional[Dict[str, Any]] = None  # Cached state
        self.pending_changes: list[Dict[str, Any]] = []  # Changes made while offline
        
        # Connect signals
        self.collaboration_service.connected.connect(self._on_connected)
        self.collaboration_service.disconnected.connect(self._on_disconnected)
        self.collaboration_service.command_received.connect(self._on_command_received)
        self.collaboration_service.sync_state_received.connect(self._on_sync_state_received)
        self.collaboration_service.user_joined.connect(self._on_user_joined)
        self.collaboration_service.user_left.connect(self._on_user_left)
        self.collaboration_service.error_occurred.connect(self._on_error)
        self.collaboration_service.connection_acknowledged.connect(self._on_connection_acknowledged)
    
    def create_session(self, session_id: str, user_id: str, use_current_canvas: bool = True) -> None:
        """
        Create a new session as host.
        
        Args:
            session_id: Session ID to create
            user_id: Your user ID/name
            use_current_canvas: If True, share current canvas state; if False, start with empty canvas
        """
        self.role = "host"
        self.session_id = session_id
        self.session_version = 0
        self.initial_sync_complete = True  # Host starts with sync complete
        
        if not use_current_canvas:
            # Clear the canvas for empty session
            if hasattr(self.main_window, 'scene') and self.main_window.scene:
                self.main_window.scene.clear()
            self.item_uuid_map.clear()
        else:
            # Rebuild UUID map from current canvas
            self.rebuild_uuid_map()
        
        # Cache initial state
        self.last_known_state = self.get_session_state()
        
        self.log.info(f"Created session '{session_id}' as host (current_canvas={use_current_canvas})", "Collaboration")
    
    def join_session(self, server_url: str, session_id: str, user_id: str) -> None:
        """
        Join an existing session as client.
        
        Args:
            server_url: WebSocket server URL (e.g., ws://localhost:8765)
            session_id: Session ID to join
            user_id: Your user ID/name
        """
        self.role = "client"
        self.session_id = session_id
        self.initial_sync_complete = False  # Client needs initial sync
        
        # Clear canvas before joining
        if hasattr(self.main_window, 'scene') and self.main_window.scene:
            self.main_window.scene.clear()
        self.item_uuid_map.clear()
        
        # Connect to session
        self.connect_to_session(server_url, session_id, user_id)
        
        self.log.info(f"Joining session '{session_id}' as client", "Collaboration")
    
    def connect_to_session(self, server_url: str, session_id: str, user_id: str) -> None:
        """
        Connect to a collaboration session.
        
        Args:
            server_url: WebSocket server URL (e.g., ws://localhost:8765)
            session_id: Session ID to join
            user_id: Your user ID/name
        """
        self.session_id = session_id
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
        
        # Suppress during initial sync
        if not self.initial_sync_complete:
            return
        
        if not hasattr(item, 'item_uuid') or not hasattr(item, 'to_dict'):
            return
        
        item_type = self._get_item_type(item)
        if not item_type:
            return
        
        # Add to UUID map
        self.item_uuid_map[item.item_uuid] = item
        
        # Increment version
        self._increment_version()
        
        # Log the broadcast
        pos = (item.x(), item.y()) if hasattr(item, 'x') and hasattr(item, 'y') else (0, 0)
        self.log.info(f"📤 Broadcasting ADD: {item_type} at ({pos[0]:.0f}, {pos[1]:.0f})", "Collaboration")
        
        # Broadcast to other users
        data = item.to_dict()
        # Ensure UUID is in the data for remote recreation
        data['item_uuid'] = item.item_uuid
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
        
        # Log the broadcast
        pos = (item.x(), item.y()) if hasattr(item, 'x') and hasattr(item, 'y') else (0, 0)
        rot = item.rotation() if hasattr(item, 'rotation') else 0
        self.log.debug(f"📤 Broadcasting MOVE: {item_type} to ({pos[0]:.0f}, {pos[1]:.0f}) rot={rot:.0f}°", "Collaboration")
        
        data = item.to_dict()
        data['item_uuid'] = item.item_uuid
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
        
        # Log the broadcast
        self.log.info(f"📤 Broadcasting REMOVE: {item_type}", "Collaboration")
        
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
        
        # Log the broadcast
        self.log.info(f"📤 Broadcasting UPDATE: {item_type}", "Collaboration")
        
        data = item.to_dict()
        data['item_uuid'] = item.item_uuid
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
            'RulerItem': 'ruler',
            'TextNoteItem': 'text',
        }
        return type_map.get(class_name)
    
    def _on_connected(self) -> None:
        """Handle successful connection."""
        from datetime import datetime
        
        self.status_changed.emit("Connected!")
        
        # If reconnecting, request sync
        if self.needs_resync and self.role == "client":
            self.log.info("Reconnected - requesting state sync", "Collaboration")
            # Send sync request with local version
            self.collaboration_service.send_message({
                'type': 'sync:request',
                'local_version': self.session_version,
                'timestamp': datetime.now().isoformat()
            })
    
    def _on_disconnected(self) -> None:
        """Handle disconnection."""
        # Cache current state before clearing
        if self.item_uuid_map:
            self.last_known_state = self.get_session_state()
        
        self.enabled = False
        self.needs_resync = True  # Flag for reconnection
        # Don't clear item_uuid_map yet - keep it for reconnection comparison
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
        # Create item from remote data
        item = self._create_item_from_remote(item_type, data)
        if item:
            # Log the remote add
            pos = (data.get('x_mm', 0), data.get('y_mm', 0))
            self.log.info(f"📥 Applying ADD: {item_type} at ({pos[0]:.0f}, {pos[1]:.0f})", "Collaboration")
            
            # Add to scene
            self.main_window.scene.addItem(item)
            # Add to UUID map
            self.item_uuid_map[item.item_uuid] = item
            # Connect signals
            item.edited.connect(self.main_window._maybe_retrace)
            # Retrace if needed
            if self.main_window.autotrace:
                self.main_window.retrace()
        else:
            self.log.error(f"📥 ADD failed: couldn't create {item_type}", "Collaboration")
        
        self.remote_item_added.emit(item_type, data)
    
    def _create_item_from_remote(self, item_type: str, data: Dict[str, Any]):
        """Create an optical component from remote data."""
        try:
            # Import component classes and params
            from ..objects.generic import ComponentItem
            from ..objects.sources import SourceItem
            from ..objects.annotations import RulerItem, TextNoteItem
            from ..core.models import (
                ComponentParams, SourceParams
            )
            
            # Extract UUID from data
            item_uuid = data.get('uuid') or data.get('item_uuid')
            
            # Prepare data dict for from_dict()
            # Note: from_dict() will set item_uuid from dict, but then passes
            # the whole dict to Params(**d), so we need to remove non-param fields
            data_copy = data.copy()
            # Remove UUID and type fields to avoid passing to params constructor
            data_copy.pop('uuid', None)
            data_copy.pop('item_uuid', None)
            data_copy.pop('item_type', None)
            
            # Create appropriate params object with default values
            if item_type in ['lens', 'mirror', 'beamsplitter', 'dichroic', 'waveplate', 'slm', 'component']:
                # All optical components now use ComponentItem
                params = ComponentParams()
                item = ComponentItem(params, item_uuid)
            elif item_type == 'source':
                params = SourceParams()
                item = SourceItem(params, item_uuid)
            elif item_type == 'ruler':
                # Rulers don't use params system
                item = RulerItem()
                if item_uuid:
                    item.item_uuid = item_uuid
            elif item_type == 'text':
                # Text notes don't use params system
                item = TextNoteItem()
                if item_uuid:
                    item.item_uuid = item_uuid
            else:
                self.log.error(f"Unknown item type: {item_type}", "Collaboration")
                return None
            
            # Load data from dict
            item.from_dict(data_copy)
            return item
            
        except Exception as e:
            self.log.error(f"Error creating remote item: {e}", "Collaboration")
            import traceback
            traceback.print_exc()
            return None
    
    def _apply_move_item(self, item_uuid: str, data: Dict[str, Any]) -> None:
        """Apply remote move item command."""
        if item_uuid in self.item_uuid_map:
            item = self.item_uuid_map[item_uuid]
            pos = (data.get('x_mm', 0), data.get('y_mm', 0))
            rot = data.get('angle_deg', 0)
            self.log.debug(f"📥 Applying MOVE: to ({pos[0]:.0f}, {pos[1]:.0f}) rot={rot:.0f}°", "Collaboration")
            
            if hasattr(item, 'setPos') and 'x_mm' in data and 'y_mm' in data:
                item.setPos(data['x_mm'], data['y_mm'])
            if hasattr(item, 'setRotation') and 'angle_deg' in data:
                item.setRotation(data['angle_deg'])
        else:
            # Item not found, might need to add it
            self.log.warning(f"📥 MOVE failed: item {item_uuid[:8]} not found", "Collaboration")
            self.remote_item_moved.emit(item_uuid, data)
    
    def _apply_remove_item(self, item_uuid: str) -> None:
        """Apply remote remove item command."""
        if item_uuid in self.item_uuid_map:
            item = self.item_uuid_map[item_uuid]
            item_type = self._get_item_type(item)
            self.log.info(f"📥 Applying REMOVE: {item_type}", "Collaboration")
            
            if hasattr(self.main_window, 'scene') and self.main_window.scene:
                self.main_window.scene.removeItem(item)
            del self.item_uuid_map[item_uuid]
        else:
            self.log.warning(f"📥 REMOVE failed: item {item_uuid[:8]} not found", "Collaboration")
        self.remote_item_removed.emit(item_uuid)
    
    def _apply_update_item(self, item_uuid: str, data: Dict[str, Any]) -> None:
        """Apply remote update item command."""
        if item_uuid in self.item_uuid_map:
            item = self.item_uuid_map[item_uuid]
            item_type = self._get_item_type(item)
            self.log.info(f"📥 Applying UPDATE: {item_type}", "Collaboration")
            
            # For BaseObj items, use deserialize_item to update
            from ..objects import BaseObj
            from ..objects.type_registry import deserialize_item
            
            if isinstance(item, BaseObj):
                # Recreate item from updated data using deserialize_item
                data_copy = data.copy()
                if '_type' not in data_copy:
                    data_copy['_type'] = item_type
                updated_item = deserialize_item(data_copy)
                if updated_item:
                    # Copy state to existing item
                    item.params = updated_item.params
                    item.setPos(updated_item.pos())
                    item.setRotation(updated_item.rotation())
                    item.setZValue(updated_item.zValue())
                    if hasattr(updated_item, '_locked'):
                        item.set_locked(updated_item._locked)
                    # Trigger update
                    if hasattr(item, '_update_geom'):
                        item._update_geom()
                    if hasattr(item, 'update'):
                        item.update()
            elif hasattr(item, 'from_dict'):
                # Annotation items use their own from_dict
                data_copy = data.copy()
                data_copy.pop('uuid', None)
                data_copy.pop('item_uuid', None)
                data_copy.pop('item_type', None)
                item.from_dict(data_copy)
        else:
            self.log.warning(f"📥 UPDATE failed: item {item_uuid[:8]} not found", "Collaboration")
        self.remote_item_updated.emit(item_uuid, data)
    
    def _on_sync_state_received(self, message: Dict[str, Any]) -> None:
        """Handle full state synchronization from server."""
        state = message.get('state')
        if not state:
            return
        
        self.log.info("Received full state sync", "Collaboration")
        
        # Check for version conflict
        conflict_resolution = message.get('conflict_resolution', 'host_wins')
        has_conflict = self._detect_version_conflict(state)
        
        if has_conflict and self.role == "client":
            self.log.warning(f"Version conflict detected: local={self.session_version}, remote={state.get('version', 0)}", "Collaboration")
            self.log.info(f"Resolving with strategy: {conflict_resolution}", "Collaboration")
        
        # Clear scene before applying state (host wins by default)
        if hasattr(self.main_window, 'scene') and self.main_window.scene:
            # Remove all items from scene
            for item in list(self.main_window.scene.items()):
                self.main_window.scene.removeItem(item)
        
        self.item_uuid_map.clear()
        
        # Suppress broadcast while applying state
        self._suppress_broadcast = True
        try:
            # Apply all items from state
            items = state.get('items', [])
            self.log.info(f"Applying {len(items)} items from state sync", "Collaboration")
            
            for item_data in items:
                item_type = item_data.get('item_type')
                if item_type:
                    self._apply_add_item(item_type, item_data)
            
            # Update version
            self.session_version = state.get('version', 0)
            self.last_known_state = state
            self.initial_sync_complete = True
            self.needs_resync = False
            
            # Retrace if needed
            if hasattr(self.main_window, 'autotrace') and self.main_window.autotrace:
                if hasattr(self.main_window, 'retrace'):
                    self.main_window.retrace()
            
            self.log.info(f"State sync complete - version {self.session_version}", "Collaboration")
        finally:
            self._suppress_broadcast = False
    
    def _on_user_joined(self, user_id: str) -> None:
        """Handle user joined notification."""
        self.log.info(f"👤 User joined: {user_id}", "Collaboration")
        self.status_changed.emit(f"{user_id} joined")
        
        # If we're the host, send full state to new client
        if self.role == "host":
            self.log.info(f"Sending full state to new client: {user_id}", "Collaboration")
            state = self.get_session_state()
            self.collaboration_service.send_message({
                'type': 'sync:full_state',
                'state': state,
                'target_user': user_id  # Optional: target specific user
            })
    
    def _on_user_left(self, user_id: str) -> None:
        """Handle user left notification."""
        self.log.info(f"👤 User left: {user_id}", "Collaboration")
        self.status_changed.emit(f"{user_id} left")
    
    def _on_error(self, error: str) -> None:
        """Handle collaboration error."""
        self.status_changed.emit(f"Error: {error}")
    
    def get_session_state(self) -> Dict[str, Any]:
        """
        Get complete session state including all items.
        
        Returns:
            Dictionary containing complete canvas state with version
        """
        items = []
        for item_uuid, item in self.item_uuid_map.items():
            if hasattr(item, 'to_dict'):
                item_data = item.to_dict()
                item_data['uuid'] = item_uuid
                item_data['item_type'] = self._get_item_type(item)
                items.append(item_data)
        
        from datetime import datetime
        state = {
            'items': items,
            'version': self.session_version,
            'timestamp': datetime.now().isoformat()
        }
        
        return state
    
    def _increment_version(self) -> None:
        """Increment session version counter."""
        self.session_version += 1
        self.last_known_state = self.get_session_state()
    
    def _detect_version_conflict(self, remote_state: Dict[str, Any]) -> bool:
        """
        Detect if remote state version conflicts with local version.
        
        Args:
            remote_state: Remote state dictionary with version
            
        Returns:
            True if versions conflict, False otherwise
        """
        remote_version = remote_state.get('version', 0)
        return remote_version != self.session_version

