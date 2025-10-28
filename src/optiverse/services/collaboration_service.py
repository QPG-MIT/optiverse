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

from .log_service import get_log_service, LogLevel


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
        
        # Get log service
        self.log = get_log_service()
        
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
        # Close existing connection if any
        if self.ws.isValid():
            self.log.info("Closing existing connection before reconnecting", "Collaboration")
            self.ws.close()
        
        self.session_id = session_id
        self.user_id = user_id
        
        url = f"{self.server_url}/ws/{session_id}/{user_id}"
        self.log.info(f"→ Connecting to: {url}", "Collaboration")
        self.log.debug(f"CollaborationService id: {id(self)}", "Collaboration")
        self.log.debug(f"QWebSocket id: {id(self.ws)}", "Collaboration")
        self.log.debug(f"Parent: {self.parent()}", "Collaboration")
        
        try:
            self.ws.open(QUrl(url))
        except Exception as e:
            self.log.error(f"Failed to initiate connection: {e}", "Collaboration")
            self.error_occurred.emit(str(e))
    
    def disconnect_from_session(self) -> None:
        """Disconnect from current session."""
        self.log.debug(f"disconnect_from_session called, isValid={self.ws.isValid()}", "Collaboration")
        if self.ws.isValid():
            self.log.info("Closing WebSocket", "Collaboration")
            self.ws.close()
        else:
            self.log.warning("WebSocket already invalid, not closing", "Collaboration")
    
    def send_message(self, message: dict) -> None:
        """
        Send a message to other users in the session.
        
        Args:
            message: Dictionary containing message data
        """
        if not self.connected_state:
            self.log.warning("Not connected, message not sent", "Collaboration")
            return
        
        try:
            # Add user_id to message if not present
            if 'user_id' not in message:
                message['user_id'] = self.user_id
            
            json_str = json.dumps(message)
            self.ws.sendTextMessage(json_str)
        except Exception as e:
            self.log.error(f"Error sending message: {e}", "Collaboration")
            self.error_occurred.emit(str(e))
    
    def is_connected(self) -> bool:
        """Check if currently connected to a session."""
        return self.connected_state
    
    def _on_connected(self) -> None:
        """Called when WebSocket connection is established."""
        self.connected_state = True
        self.log.info(f"✓ Connected to session '{self.session_id}' as '{self.user_id}'", "Collaboration")
        self.log.debug(f"WebSocket state: {self.ws.state()}", "Collaboration")
        self.log.debug(f"WebSocket isValid: {self.ws.isValid()}", "Collaboration")
        self.log.debug(f"Starting heartbeat timer (interval: {self.heartbeat_timer.interval()}ms)", "Collaboration")
        self.heartbeat_timer.start()
        self.connected.emit()
    
    def _on_disconnected(self) -> None:
        """Called when WebSocket is disconnected."""
        self.connected_state = False
        self.heartbeat_timer.stop()
        self.users_in_session.clear()
        
        close_code_enum = self.ws.closeCode()
        close_reason = self.ws.closeReason()
        
        # Convert enum to int for comparison
        # PyQt6 returns QWebSocketProtocol.CloseCode enum
        try:
            close_code = int(close_code_enum)
        except (ValueError, TypeError):
            close_code = 0
        
        # Map close codes to readable messages
        close_code_messages = {
            1000: "Normal closure",
            1001: "Going away",
            1002: "Protocol error",
            1003: "Unsupported data",
            1006: "Abnormal closure (no close frame)",
            1007: "Invalid frame payload data",
            1008: "Policy violation (ping/pong issue)",
            1009: "Message too big",
            1010: "Missing extension",
            1011: "Internal server error",
            1015: "TLS handshake error"
        }
        
        close_code_msg = close_code_messages.get(close_code, f"Unknown code {close_code} ({close_code_enum})")
        
        if close_code in [1000, 1001]:
            self.log.info(f"✓ Disconnected from session '{self.session_id}' - {close_code_msg}", "Collaboration")
        else:
            self.log.warning(f"✗ Disconnected from session '{self.session_id}' - {close_code_msg}", "Collaboration")
            self.log.warning(f"Close code enum: {close_code_enum}, int value: {close_code}", "Collaboration")
        
        self.log.debug(f"WebSocket state: {self.ws.state()}", "Collaboration")
        
        if close_reason:
            self.log.info(f"Reason: {close_reason}", "Collaboration")
        
        # Log stack trace for debugging only on abnormal close codes
        if close_code not in [1000, 1001]:  # Normal close codes
            import traceback
            stack_trace = ''.join(traceback.format_stack())
            self.log.debug(f"Disconnect called from:\n{stack_trace}", "Collaboration")
        
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
                users = data.get('users', [])
                self.log.info(f"Connection acknowledged with {len(users)} user(s)", "Collaboration")
                self.users_in_session = {u['user_id']: u for u in users}
                self.connection_acknowledged.emit(data)
            
            elif msg_type == 'user:joined':
                user_id = data.get('user_id', 'unknown')
                self.log.info(f"User joined: {user_id}", "Collaboration")
                self.users_in_session[user_id] = {
                    'user_id': user_id,
                    'connected_at': data.get('timestamp')
                }
                self.user_joined.emit(user_id)
            
            elif msg_type == 'user:left':
                user_id = data.get('user_id', 'unknown')
                self.log.info(f"User left: {user_id}", "Collaboration")
                if user_id in self.users_in_session:
                    del self.users_in_session[user_id]
                self.user_left.emit(user_id)
            
            elif msg_type == 'command':
                # Remote command from another user
                sender = data.get('user_id', 'unknown')
                action = data.get('command', {}).get('action', 'unknown')
                self.log.debug(f"Received command from {sender}: {action}", "Collaboration")
                self.command_received.emit(data)
            
            elif msg_type == 'sync:state':
                # Full state synchronization
                self.log.info("Received state sync", "Collaboration")
                self.sync_state_received.emit(data)
            
            elif msg_type == 'pong':
                # Heartbeat response
                self.log.debug("← Received heartbeat pong", "Collaboration")
                pass
            
            else:
                # Forward all other messages
                self.message_received.emit(data)
        
        except json.JSONDecodeError as e:
            self.log.error(f"Error parsing message: {e}", "Collaboration")
            self.error_occurred.emit(f"Invalid JSON: {e}")
        except Exception as e:
            self.log.error(f"Error processing message: {e}", "Collaboration")
            self.error_occurred.emit(str(e))
    
    def _on_error(self, error_code) -> None:
        """
        Called when a WebSocket error occurs.
        
        Args:
            error_code: Qt WebSocket error code
        """
        error_str = self.ws.errorString()
        self.log.error(f"WebSocket error ({error_code}): {error_str}", "Collaboration")
        self.error_occurred.emit(error_str)
    
    def _send_heartbeat(self) -> None:
        """Send heartbeat ping to keep connection alive."""
        if self.connected_state:
            self.log.debug("→ Sending heartbeat ping", "Collaboration")
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

