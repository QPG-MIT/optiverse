"""
Collaboration service for real-time multi-user editing.

This service handles WebSocket connections to a collaboration server,
allowing multiple users to work on the same optical design simultaneously.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QTimer
from PyQt6.QtWebSockets import QWebSocket
import json
from typing import Optional, Dict, Any
from datetime import datetime


class CollaborationService(QObject):
    """
    Handles real-time collaboration via WebSocket.
    
    Signals:
        connected: Emitted when connection is established
        disconnected: Emitted when connection is lost
        message_received: Emitted when a message is received (dict)
        user_joined: Emitted when another user joins (user_id: str)
        user_left: Emitted when another user leaves (user_id: str)
        error_occurred: Emitted on error (error_message: str)
    """
    
    # Signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(dict)
    command_received = pyqtSignal(dict)  # Remote command from another user
    sync_state_received = pyqtSignal(dict)  # Full state sync
    user_joined = pyqtSignal(str)  # user_id
    user_left = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    connection_acknowledged = pyqtSignal(dict)  # Connection ack with user list
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.ws = QWebSocket()
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.server_url: str = "ws://localhost:8765"
        self.connected_state = False
        self.users_in_session: Dict[str, Dict[str, Any]] = {}  # Track connected users
        
        # Connect WebSocket signals
        self.ws.connected.connect(self._on_connected)
        self.ws.disconnected.connect(self._on_disconnected)
        self.ws.textMessageReceived.connect(self._on_message)
        self.ws.errorOccurred.connect(self._on_error)
        
        # Heartbeat timer to keep connection alive
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self._send_heartbeat)
        self.heartbeat_timer.setInterval(30000)  # 30 seconds
    
    def set_server_url(self, url: str) -> None:
        """Set the collaboration server URL."""
        self.server_url = url
    
    def connect_to_session(self, session_id: str, user_id: str) -> None:
        """
        Connect to a collaboration session.
        
        Args:
            session_id: The session ID to join
            user_id: Your user ID/name
        """
        self.session_id = session_id
        self.user_id = user_id
        
        url = f"{self.server_url}/ws/{session_id}/{user_id}"
        print(f"Connecting to: {url}")
        self.ws.open(QUrl(url))
    
    def disconnect_from_session(self) -> None:
        """Disconnect from current session."""
        if self.ws.isValid():
            self.ws.close()
    
    def send_message(self, message: dict) -> None:
        """
        Send a message to other users in the session.
        
        Args:
            message: Dictionary containing message data
        """
        if not self.connected_state:
            print("Warning: Not connected, message not sent")
            return
        
        try:
            # Add user_id to message if not present
            if 'user_id' not in message:
                message['user_id'] = self.user_id
            
            json_str = json.dumps(message)
            self.ws.sendTextMessage(json_str)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.error_occurred.emit(str(e))
    
    def is_connected(self) -> bool:
        """Check if currently connected to a session."""
        return self.connected_state
    
    def _on_connected(self) -> None:
        """Called when WebSocket connection is established."""
        self.connected_state = True
        print(f"Connected to session {self.session_id} as {self.user_id}")
        self.heartbeat_timer.start()
        self.connected.emit()
    
    def _on_disconnected(self) -> None:
        """Called when WebSocket is disconnected."""
        self.connected_state = False
        self.heartbeat_timer.stop()
        self.users_in_session.clear()
        print(f"Disconnected from session {self.session_id}")
        self.disconnected.emit()
    
    def _on_message(self, message: str) -> None:
        """
        Called when a message is received from the server.
        
        Args:
            message: JSON string from server
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')
            
            # Handle special message types
            if msg_type == 'connection:ack':
                # Connection acknowledged with user list
                print(f"Connection acknowledged: {data}")
                users = data.get('users', [])
                self.users_in_session = {u['user_id']: u for u in users}
                self.connection_acknowledged.emit(data)
            
            elif msg_type == 'user:joined':
                user_id = data.get('user_id', 'unknown')
                print(f"User joined: {user_id}")
                self.users_in_session[user_id] = {
                    'user_id': user_id,
                    'connected_at': data.get('timestamp')
                }
                self.user_joined.emit(user_id)
            
            elif msg_type == 'user:left':
                user_id = data.get('user_id', 'unknown')
                print(f"User left: {user_id}")
                if user_id in self.users_in_session:
                    del self.users_in_session[user_id]
                self.user_left.emit(user_id)
            
            elif msg_type == 'command':
                # Remote command from another user
                print(f"Received command from {data.get('user_id')}: {data.get('command', {}).get('action')}")
                self.command_received.emit(data)
            
            elif msg_type == 'sync:state':
                # Full state synchronization
                print("Received state sync")
                self.sync_state_received.emit(data)
            
            elif msg_type == 'pong':
                # Heartbeat response
                pass
            
            else:
                # Forward all other messages
                self.message_received.emit(data)
        
        except json.JSONDecodeError as e:
            print(f"Error parsing message: {e}")
            self.error_occurred.emit(f"Invalid JSON: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")
            self.error_occurred.emit(str(e))
    
    def _on_error(self, error_code) -> None:
        """
        Called when a WebSocket error occurs.
        
        Args:
            error_code: Qt WebSocket error code
        """
        error_str = self.ws.errorString()
        print(f"WebSocket error ({error_code}): {error_str}")
        self.error_occurred.emit(error_str)
    
    def _send_heartbeat(self) -> None:
        """Send heartbeat ping to keep connection alive."""
        if self.connected_state:
            self.send_message({"type": "ping"})
    
    def send_command(self, action: str, item_type: str, item_id: str, data: Dict[str, Any]) -> None:
        """
        Send a command to other users.
        
        Args:
            action: Action type (add_item, move_item, remove_item, update_item)
            item_type: Type of item (lens, mirror, source, etc.)
            item_id: UUID of the item
            data: Item data dictionary
        """
        message = {
            "type": "command",
            "command": {
                "action": action,
                "item_type": item_type,
                "item_id": item_id,
                "data": data
            },
            "timestamp": datetime.now().isoformat()
        }
        self.send_message(message)
    
    def request_sync(self) -> None:
        """Request full state synchronization from server."""
        if self.connected_state:
            self.send_message({"type": "sync:request"})
    
    def update_scene_state(self, state: Dict[str, Any]) -> None:
        """
        Send updated scene state to server.
        
        Args:
            state: Complete scene state dictionary
        """
        if self.connected_state:
            message = {
                "type": "sync:update",
                "state": state,
                "timestamp": datetime.now().isoformat()
            }
            self.send_message(message)
    
    def get_connected_users(self) -> list[str]:
        """Get list of connected user IDs."""
        return list(self.users_in_session.keys())

