"""
Collaboration service for real-time multi-user editing.

This service handles WebSocket connections to a collaboration server,
allowing multiple users to work on the same optical design simultaneously.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtWebSockets import QWebSocket
import json
from typing import Optional


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
    user_joined = pyqtSignal(str)  # user_id
    user_left = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.ws = QWebSocket()
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.server_url: str = "ws://localhost:8080"
        self.connected_state = False
        
        # Connect WebSocket signals
        self.ws.connected.connect(self._on_connected)
        self.ws.disconnected.connect(self._on_disconnected)
        self.ws.textMessageReceived.connect(self._on_message)
        self.ws.errorOccurred.connect(self._on_error)
    
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
        self.connected.emit()
    
    def _on_disconnected(self) -> None:
        """Called when WebSocket is disconnected."""
        self.connected_state = False
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
            if msg_type == 'user:joined':
                user_id = data.get('user_id', 'unknown')
                print(f"User joined: {user_id}")
                self.user_joined.emit(user_id)
            
            elif msg_type == 'user:left':
                user_id = data.get('user_id', 'unknown')
                print(f"User left: {user_id}")
                self.user_left.emit(user_id)
            
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

