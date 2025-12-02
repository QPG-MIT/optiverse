#!/usr/bin/env python3
"""
Simple collaboration server specifically for websockets 15.x
Designed to work with Qt WebSocket without issues.
"""

import asyncio
import json
import logging
import signal
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Store connections and session state
connections = {}
session_state = {}  # session_id -> {state: dict, version: int, host: str}
server = None


async def handler(websocket):
    """Handle a WebSocket connection."""
    path = websocket.request.path if hasattr(websocket.request, "path") else websocket.path
    logger.info(f"New connection: {path}")

    # Parse path
    parts = path.strip("/").split("/")
    if len(parts) < 3 or parts[0] != "ws":
        await websocket.close(1008, "Invalid path")
        return

    session_id = parts[1]
    user_id = parts[2]

    # Store connection
    connections[user_id] = websocket
    logger.info(f"User {user_id} joined session {session_id}")

    # Determine if this is the first user (becomes host)
    is_first_user = (session_id not in session_state) or (
        session_state[session_id].get("host") is None
    )

    if is_first_user:
        session_state[session_id] = {
            "state": {"items": [], "version": 0, "timestamp": "2025-10-28T12:00:00"},
            "version": 0,
            "host": user_id,
        }
        logger.info(f"User {user_id} is the host of session {session_id}")

    try:
        # Send connection ack
        await websocket.send(
            json.dumps(
                {
                    "type": "connection:ack",
                    "session_id": session_id,
                    "user_id": user_id,
                    "is_host": is_first_user,
                    "users": [{"user_id": u} for u in connections.keys()],
                    "timestamp": "2025-10-28T12:00:00",
                }
            )
        )
        logger.info(f"Sent ack to {user_id} (host={is_first_user})")

        # Send current session state to new joiner if not the first user
        if not is_first_user and session_id in session_state:
            stored_state = session_state[session_id]["state"]
            await websocket.send(
                json.dumps({"type": "sync:full_state", "state": stored_state, "from_server": True})
            )
            logger.info(
                f"Sent session state to {user_id} ({len(stored_state.get('items', []))} items)"
            )

        # Notify other users
        for other_id, other_ws in connections.items():
            if other_id != user_id:
                try:
                    await other_ws.send(json.dumps({"type": "user:joined", "user_id": user_id}))
                except Exception:
                    pass

        # Handle messages
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send(
                    json.dumps({"type": "pong", "timestamp": "2025-10-28T12:00:00"})
                )
                logger.debug(f"Sent pong to {user_id}")

            elif msg_type == "sync:full_state":
                # Host is sending full state update
                if session_id in session_state and session_state[session_id]["host"] == user_id:
                    state = data.get("state", {})
                    session_state[session_id]["state"] = state
                    session_state[session_id]["version"] = state.get("version", 0)
                    logger.info(
                        f"📦 Stored session state from host {user_id} "
                        f"(version {state.get('version', 0)})"
                    )

                # Broadcast to other users
                for other_id, other_ws in connections.items():
                    if other_id != user_id:
                        try:
                            await other_ws.send(message)
                        except Exception as e:
                            logger.error(f"Failed to send state to {other_id}: {e}")

            elif msg_type == "sync:request":
                # Client requesting sync (reconnection)
                logger.info(f"📥 Sync request from {user_id}")
                if session_id in session_state:
                    stored_state = session_state[session_id]["state"]
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "sync:full_state",
                                "state": stored_state,
                                "from_server": True,
                                "conflict_resolution": "host_wins",
                            }
                        )
                    )
                    logger.info(f"📤 Sent stored state to {user_id}")

            elif msg_type == "command":
                # Broadcast command to other users in the session
                command = data.get("command", {})
                action = command.get("action", "")
                item_type = command.get("item_type", "")
                logger.info(
                    f"📤 Broadcasting {action} ({item_type}) from {user_id} "
                    f"to {len(connections) - 1} other(s)"
                )

                for other_id, other_ws in connections.items():
                    if other_id != user_id:
                        try:
                            await other_ws.send(message)
                        except Exception as e:
                            logger.error(f"Failed to send to {other_id}: {e}")
            else:
                logger.info(f"Received from {user_id}: {msg_type}")

    except Exception as e:
        logger.error(f"Error for {user_id}: {e}")
    finally:
        if user_id in connections:
            del connections[user_id]
        logger.info(f"User {user_id} disconnected")

        # Notify other users
        for _other_id, other_ws in connections.items():
            try:
                await other_ws.send(json.dumps({"type": "user:left", "user_id": user_id}))
            except Exception:
                pass


async def main(host="0.0.0.0", port=8765):
    """Start the server."""
    global server

    logger.info("=" * 70)
    logger.info("SIMPLE COLLABORATION SERVER (websockets 15.x compatible)")
    logger.info("=" * 70)
    logger.info(f"Starting on ws://{host}:{port}")

    try:
        # Try websockets 14+ async API
        from websockets.asyncio.server import serve

        logger.info("Using websockets.asyncio.server API")
    except ImportError:
        # Fall back to legacy API
        from websockets import serve

        logger.info("Using websockets legacy API")

    async with serve(handler, host, port, ping_interval=None, ping_timeout=None) as server:
        logger.info("✓ Server ready")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 70)
        await asyncio.Future()


def cleanup(sig=None, frame=None):
    """Clean up on exit."""
    logger.info("\nShutting down...")
    sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple Collaboration Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Port number (default: 8765)")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, cleanup)
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        cleanup()
