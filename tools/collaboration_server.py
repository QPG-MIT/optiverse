#!/usr/bin/env python3
"""
Optiverse Collaboration Server

A lightweight WebSocket server for real-time collaborative optical design.
Supports multiple sessions with independent state management.

Usage:
    python collaboration_server.py [--host HOST] [--port PORT]

Default: ws://localhost:8765
"""
from __future__ import annotations

import asyncio
import json
import logging
import argparse
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, Any
from datetime import datetime

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("ERROR: websockets library not installed.")
    print("Install with: pip install websockets")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class User:
    """Represents a connected user."""
    user_id: str
    websocket: WebSocketServerProtocol
    session_id: str
    connected_at: datetime = field(default_factory=datetime.now)


@dataclass
class Session:
    """Represents a collaboration session."""
    session_id: str
    users: Dict[str, User] = field(default_factory=dict)
    scene_state: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_user(self, user: User) -> None:
        """Add a user to this session."""
        self.users[user.user_id] = user
        logger.info(f"User {user.user_id} joined session {self.session_id}")
    
    def remove_user(self, user_id: str) -> None:
        """Remove a user from this session."""
        if user_id in self.users:
            del self.users[user_id]
            logger.info(f"User {user_id} left session {self.session_id}")
    
    async def broadcast(self, message: Dict[str, Any], exclude_user: Optional[str] = None) -> None:
        """
        Broadcast a message to all users in the session.
        
        Args:
            message: Message dictionary to broadcast
            exclude_user: Optional user_id to exclude from broadcast
        """
        if not self.users:
            return
        
        message_str = json.dumps(message)
        tasks = []
        
        for user_id, user in list(self.users.items()):
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                tasks.append(user.websocket.send(message_str))
            except Exception as e:
                logger.error(f"Error queuing message to {user_id}: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_user_list(self) -> list:
        """Get list of connected users."""
        return [
            {
                "user_id": u.user_id,
                "connected_at": u.connected_at.isoformat()
            }
            for u in self.users.values()
        ]


class CollaborationServer:
    """Main collaboration server managing sessions and connections."""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.websocket_to_user: Dict[WebSocketServerProtocol, User] = {}
    
    def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create a new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(session_id=session_id)
            logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """
        Handle a new WebSocket connection.
        
        Path format: /ws/{session_id}/{user_id}
        """
        # Parse path to get session_id and user_id
        parts = path.strip('/').split('/')
        if len(parts) < 3 or parts[0] != 'ws':
            await websocket.close(code=1008, reason="Invalid path format")
            return
        
        session_id = parts[1]
        user_id = parts[2]
        
        # Create user and add to session
        user = User(user_id=user_id, websocket=websocket, session_id=session_id)
        session = self.get_or_create_session(session_id)
        session.add_user(user)
        self.websocket_to_user[websocket] = user
        
        try:
            # Send connection acknowledgment
            await websocket.send(json.dumps({
                "type": "connection:ack",
                "session_id": session_id,
                "user_id": user_id,
                "users": session.get_user_list()
            }))
            
            # Notify other users
            await session.broadcast({
                "type": "user:joined",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }, exclude_user=user_id)
            
            # If session has state, send it to the new user
            if session.scene_state:
                await websocket.send(json.dumps({
                    "type": "sync:state",
                    "state": session.scene_state,
                    "timestamp": datetime.now().isoformat()
                }))
            
            # Handle incoming messages
            async for message in websocket:
                await self.handle_message(user, session, message)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"Error handling connection for {user_id}: {e}")
        finally:
            # Clean up
            await self.handle_disconnect(user, session)
    
    async def handle_message(self, user: User, session: Session, message: str) -> None:
        """
        Handle an incoming message from a user.
        
        Args:
            user: User who sent the message
            session: Session the user belongs to
            message: Raw message string
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')
            
            logger.debug(f"Received {msg_type} from {user.user_id}")
            
            if msg_type == 'command':
                # Broadcast command to all other users
                data['timestamp'] = datetime.now().isoformat()
                data['user_id'] = user.user_id
                await session.broadcast(data, exclude_user=user.user_id)
            
            elif msg_type == 'sync:request':
                # Send current state to requesting user
                if session.scene_state:
                    await user.websocket.send(json.dumps({
                        "type": "sync:state",
                        "state": session.scene_state,
                        "timestamp": datetime.now().isoformat()
                    }))
                else:
                    await user.websocket.send(json.dumps({
                        "type": "sync:state",
                        "state": None,
                        "timestamp": datetime.now().isoformat()
                    }))
            
            elif msg_type == 'sync:update':
                # Update session state
                session.scene_state = data.get('state')
                logger.info(f"Session {session.session_id} state updated by {user.user_id}")
                # Broadcast to others
                await session.broadcast({
                    "type": "sync:state",
                    "state": session.scene_state,
                    "timestamp": datetime.now().isoformat()
                }, exclude_user=user.user_id)
            
            elif msg_type == 'cursor':
                # Broadcast cursor position
                data['user_id'] = user.user_id
                await session.broadcast(data, exclude_user=user.user_id)
            
            elif msg_type == 'ping':
                # Respond to ping
                await user.websocket.send(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
            
            else:
                # Forward unknown message types
                logger.warning(f"Unknown message type: {msg_type}")
                data['user_id'] = user.user_id
                await session.broadcast(data, exclude_user=user.user_id)
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {user.user_id}: {e}")
        except Exception as e:
            logger.error(f"Error handling message from {user.user_id}: {e}")
    
    async def handle_disconnect(self, user: User, session: Session) -> None:
        """
        Handle user disconnection.
        
        Args:
            user: User who disconnected
            session: Session the user belonged to
        """
        # Remove from tracking
        if user.websocket in self.websocket_to_user:
            del self.websocket_to_user[user.websocket]
        
        session.remove_user(user.user_id)
        
        # Notify other users
        await session.broadcast({
            "type": "user:left",
            "user_id": user.user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Clean up empty sessions
        if not session.users:
            logger.info(f"Session {session.session_id} is empty, removing")
            if session.session_id in self.sessions:
                del self.sessions[session.session_id]


async def main(host: str = "0.0.0.0", port: int = 8765):
    """
    Start the collaboration server.
    
    Args:
        host: Host address to bind to (0.0.0.0 for all interfaces)
        port: Port to listen on
    """
    server = CollaborationServer()
    
    logger.info(f"Starting Optiverse Collaboration Server on {host}:{port}")
    logger.info("Press Ctrl+C to stop")
    
    async with websockets.serve(server.handle_connection, host, port):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optiverse Collaboration Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

