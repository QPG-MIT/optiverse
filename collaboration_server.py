#!/usr/bin/env python3
"""
Minimal collaboration server for Optiverse.

This server provides real-time collaboration by routing messages between
connected clients. It does NOT perform any computation - clients do all
the work (raytracing, rendering, etc.).

Usage:
    python collaboration_server.py

Then in your desktop app, connect to ws://localhost:8080/ws/{session_id}/{user_id}
"""
import asyncio
import json
import secrets
import logging
from datetime import datetime
from aiohttp import web
import aiohttp

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Active sessions: {session_id: {user_id: websocket}}
sessions = {}

# Session metadata: {session_id: {'created_at': datetime, 'users': set()}}
sessions_meta = {}


async def create_session(request):
    """Create a new collaboration session."""
    session_id = secrets.token_urlsafe(12)
    sessions[session_id] = {}
    sessions_meta[session_id] = {
        'created_at': datetime.utcnow().isoformat(),
        'users': set()
    }
    
    logger.info(f"Created session: {session_id}")
    
    return web.json_response({
        'session_id': session_id,
        'share_link': f'optiverse://join/{session_id}'
    })


async def get_session(request):
    """Get session metadata."""
    session_id = request.match_info['session_id']
    
    if session_id not in sessions_meta:
        return web.json_response({'error': 'Session not found'}, status=404)
    
    meta = sessions_meta[session_id]
    return web.json_response({
        'session_id': session_id,
        'created_at': meta['created_at'],
        'active_users': list(meta['users']),
        'user_count': len(meta['users'])
    })


async def websocket_handler(request):
    """Handle WebSocket connections for real-time collaboration."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    session_id = request.match_info['session_id']
    user_id = request.match_info['user_id']
    
    logger.info(f"User {user_id} connecting to session {session_id}")
    
    # Create session if it doesn't exist
    if session_id not in sessions:
        sessions[session_id] = {}
        sessions_meta[session_id] = {
            'created_at': datetime.utcnow().isoformat(),
            'users': set()
        }
    
    # Add user to session
    sessions[session_id][user_id] = ws
    sessions_meta[session_id]['users'].add(user_id)
    
    # Notify others that user joined
    await broadcast(session_id, {
        'type': 'user:joined',
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat()
    }, exclude=user_id)
    
    logger.info(f"User {user_id} joined session {session_id}. Active users: {len(sessions[session_id])}")
    
    try:
        # Message loop
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    # Add timestamp if not present
                    if 'timestamp' not in data:
                        data['timestamp'] = datetime.utcnow().isoformat()
                    # Forward to all other users in session
                    await broadcast(session_id, data, exclude=user_id)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {user_id}: {msg.data}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"WebSocket error from {user_id}: {ws.exception()}")
    
    finally:
        # Cleanup when user disconnects
        if session_id in sessions and user_id in sessions[session_id]:
            del sessions[session_id][user_id]
        
        if session_id in sessions_meta:
            sessions_meta[session_id]['users'].discard(user_id)
        
        # Notify others that user left
        await broadcast(session_id, {
            'type': 'user:left',
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Clean up empty sessions
        if session_id in sessions and len(sessions[session_id]) == 0:
            del sessions[session_id]
            if session_id in sessions_meta:
                del sessions_meta[session_id]
            logger.info(f"Session {session_id} closed (no users)")
        else:
            logger.info(f"User {user_id} left session {session_id}. Remaining: {len(sessions.get(session_id, {}))}")
    
    return ws


async def broadcast(session_id, message, exclude=None):
    """Send message to all users in session except one."""
    if session_id not in sessions:
        return
    
    disconnected = []
    for user_id, ws in sessions[session_id].items():
        if user_id != exclude:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to {user_id}: {e}")
                disconnected.append(user_id)
    
    # Clean up disconnected users
    for user_id in disconnected:
        if user_id in sessions[session_id]:
            del sessions[session_id][user_id]
        if session_id in sessions_meta:
            sessions_meta[session_id]['users'].discard(user_id)


async def health_check(request):
    """Health check endpoint."""
    return web.json_response({
        'status': 'ok',
        'active_sessions': len(sessions),
        'total_users': sum(len(users) for users in sessions.values())
    })


# Setup routes
app = web.Application()
app.router.add_get('/', health_check)
app.router.add_get('/health', health_check)
app.router.add_post('/api/sessions', create_session)
app.router.add_get('/api/sessions/{session_id}', get_session)
app.router.add_get('/ws/{session_id}/{user_id}', websocket_handler)


if __name__ == '__main__':
    print("🚀 Optiverse Collaboration Server")
    print("=" * 50)
    print("Server running on http://localhost:8080")
    print("WebSocket endpoint: ws://localhost:8080/ws/{session_id}/{user_id}")
    print("Create session: POST http://localhost:8080/api/sessions")
    print("=" * 50)
    
    web.run_app(app, host='0.0.0.0', port=8080)

