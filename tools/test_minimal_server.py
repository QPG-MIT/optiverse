#!/usr/bin/env python3
"""
Minimal WebSocket test server to verify Qt compatibility.

This is a bare-bones server to test if Qt's QWebSocket can connect and stay connected.
If this works, we know the problem is in the collaboration logic, not the base protocol.
"""
import asyncio
import signal
import sys

try:
    import websockets
    from websockets.server import serve
except ImportError:
    print("ERROR: websockets library not installed.")
    print("Install with: pip install websockets")
    sys.exit(1)

# Global server instance for cleanup
server = None


async def echo_handler(websocket, path):
    """
    Simplest possible handler - just echo back whatever is received.
    No automatic ping/pong, no fancy logic.
    """
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    print(f"[{client_id}] Connected")

    try:
        async for message in websocket:
            print(f"[{client_id}] Received: {message[:50]}...")
            # Echo back
            await websocket.send(f"Echo: {message}")
            print(f"[{client_id}] Sent echo")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"[{client_id}] Connection closed: {e.code} {e.reason}")
    except Exception as e:
        print(f"[{client_id}] Error: {e}")
    finally:
        print(f"[{client_id}] Disconnected")


async def main():
    """Start the minimal test server."""
    global server

    host = "localhost"
    port = 8765

    print("=" * 60)
    print("MINIMAL WEBSOCKET TEST SERVER")
    print("=" * 60)
    print(f"Starting on ws://{host}:{port}")
    print("Configuration:")
    print("  - No automatic ping/pong")
    print("  - No compression")
    print("  - Simple echo handler")
    print("  - Press Ctrl+C to stop")
    print("=" * 60)

    # Create server with minimal configuration
    # This is the simplest possible setup for Qt compatibility
    server = await serve(
        echo_handler,
        host,
        port,
        # Critical settings for Qt compatibility
        ping_interval=None,     # No automatic ping
        ping_timeout=None,      # No timeout
        close_timeout=10,       # Give time for clean shutdown
        compression=None,       # No compression
    )

    print(f"✓ Server ready and listening on ws://{host}:{port}")
    print("Waiting for connections...")

    # Run forever
    await asyncio.Future()


def cleanup():
    """Clean up and close the server."""
    global server
    print("\n" + "=" * 60)
    print("SHUTTING DOWN")
    print("=" * 60)
    if server:
        server.close()
        print("✓ Server closed")
    print("✓ Port 8765 released")
    sys.exit(0)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    cleanup()


if __name__ == "__main__":
    # Register signal handler for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        cleanup()



