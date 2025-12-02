---
layout: default
title: Collaboration Guide
nav_order: 15
parent: User Guides
---

# Collaborative Editing in Optiverse

Optiverse supports real-time collaborative editing via WebSocket connections, allowing multiple users on the same local network to work together on optical designs.

## Features

- **Real-time synchronization**: See changes from other users instantly
- **Local network support**: Works on LAN without internet connection
- **Host or connect**: Either start a server or connect to an existing one
- **Independent schematics**: Each user has their own view while sharing the same design
- **Automatic conflict resolution**: Last-write-wins strategy for simplicity

## Quick Start

### Option 1: Host a Server

1. Open Optiverse
2. Go to **Collaboration → Connect/Host Session…**
3. Select **Host server**
4. Configure:
   - **Listen Address**: `0.0.0.0` (accessible from LAN) or `localhost` (local only)
   - **Port**: `8765` (default)
   - **Auto-connect**: Enable to automatically join your own session
5. Click **Start Server**
6. Share the connection URL with collaborators:
   ```
   ws://YOUR_IP:8765
   ```
   Replace `YOUR_IP` with your computer's local IP address (shown in the dialog)

### Option 2: Connect to Existing Server

1. Get the server URL from the host (e.g., `ws://192.168.1.100:8765`)
2. Open Optiverse
3. Go to **Collaboration → Connect/Host Session…**
4. Select **Connect to server**
5. Enter:
   - **Server URL**: The URL provided by the host
   - **Session ID**: A session name (e.g., "default", "project-alpha")
   - **Your Name**: Your display name for other users to see
6. Click **Connect**

## Usage

### Adding Components

When you add, move, or delete components, all connected users will see the changes in real-time:

- Drag components from the library
- Use Insert menu to add sources, lenses, mirrors, etc.
- Move items by dragging
- Delete items with Delete key or context menu

### Status Indicator

The bottom-right corner of the window shows your collaboration status:
- **Not connected**: No active collaboration session
- **Connecting...**: Attempting to connect
- **Connected (N users)**: Successfully connected with N users in session
- **User joined/left**: Notifications when users enter or leave

### Disconnecting

To disconnect from a collaboration session:
1. Go to **Collaboration → Disconnect**
2. Or close the application (automatically disconnects)

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Local Network                         │
│                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │ Client A │◄───┤  Server  ├───►│ Client B │         │
│  └──────────┘    └──────────┘    └──────────┘         │
│       │               │                 │               │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐            │
│  │Local DB │    │Session  │    │Local DB │            │
│  └─────────┘    │Manager  │    └─────────┘            │
│                 └─────────┘                             │
└─────────────────────────────────────────────────────────┘
```

1. **Collaboration Server** (`tools/collaboration_server.py`)
   - Manages WebSocket connections
   - Routes messages between users
   - Maintains session state
   - Tracks connected users

2. **CollaborationService** (`src/optiverse/services/collaboration_service.py`)
   - Low-level WebSocket client
   - Handles connection lifecycle
   - Sends/receives messages
   - Heartbeat management

3. **CollaborationManager** (`src/optiverse/services/collaboration_manager.py`)
   - Bridges UI and network layer
   - Tracks item UUIDs
   - Broadcasts local changes
   - Applies remote changes
   - Prevents broadcast loops

4. **MainWindow Integration**
   - Collaboration menu and dialog
   - Status indicator
   - Item creation/deletion hooks
   - Remote change handlers

### Message Protocol

Messages are JSON objects sent over WebSocket:

#### Command Message
```json
{
  "type": "command",
  "user_id": "user_123",
  "timestamp": "2025-10-28T12:34:56",
  "command": {
    "action": "add_item",
    "item_type": "lens",
    "item_id": "uuid-1234-5678",
    "data": {...}
  }
}
```

#### Actions
- `add_item`: New component added
- `move_item`: Component moved or rotated
- `remove_item`: Component deleted
- `update_item`: Component properties changed

## Server Installation

The collaboration server requires the `websockets` library:

```bash
# Install with server dependencies
pip install -e ".[server]"

# Or directly
pip install websockets
```

## Advanced Usage

### Running Server Standalone

You can run the server independently without the Optiverse GUI:

```bash
python tools/collaboration_server.py --host 0.0.0.0 --port 8765
```

Options:
- `--host HOST`: Address to bind to (default: 0.0.0.0)
- `--port PORT`: Port to listen on (default: 8765)
- `--debug`: Enable debug logging

### Multiple Sessions

The server supports multiple independent sessions. Users specify a session ID when connecting, and only users in the same session see each other's changes.

### Network Configuration

#### Firewall
Ensure port 8765 (or your chosen port) is open in your firewall for local network access.

#### Finding Your IP
- **Windows**: `ipconfig` in Command Prompt, look for "IPv4 Address"
- **Mac/Linux**: `ifconfig` or `ip addr`, look for inet address on your active interface
- **Dialog**: The collaboration dialog shows your local IP automatically

## Troubleshooting

### Cannot Connect

1. **Check server is running**: Ensure the host has started the server
2. **Verify URL**: Ensure you're using `ws://` not `http://` or `wss://`
3. **Check firewall**: Port must be open on host machine
4. **Network connectivity**: Ping the host IP to verify network access
5. **Port conflict**: Try a different port if 8765 is already in use

### Changes Not Syncing

1. **Check connection status**: Look at the status indicator in the bottom-right
2. **Reconnect**: Disconnect and reconnect to refresh the session
3. **Server logs**: Check the server console for error messages

### Server Won't Start

1. **Port in use**: Another application might be using port 8765
2. **Missing dependency**: Install websockets: `pip install websockets`
3. **Python path**: Ensure Python can find the server script

## Security Considerations

- **Local network only**: The default configuration is designed for trusted local networks
- **No authentication**: The current implementation has no password protection
- **No encryption**: Messages are sent in plain text over WebSocket
- **Production use**: Not recommended for untrusted networks or sensitive data

For production deployments, consider:
- Adding authentication (username/password)
- Using WSS (WebSocket Secure) with TLS
- Implementing access control lists
- Running behind a reverse proxy (nginx, Apache)

## Performance

- **Recommended users**: 2-10 concurrent users
- **Network latency**: Best on LAN (<1ms), acceptable on local WiFi (<50ms)
- **Bandwidth**: Minimal, typically <10 KB/s per user
- **Scene size**: No hard limit, tested with 100+ components

## Future Enhancements

Potential improvements for future versions:

- **Cursor tracking**: See where other users are pointing
- **User colors**: Color-code changes by user
- **Undo remote changes**: Ability to revert others' changes with permission
- **Voice chat integration**: Built-in audio communication
- **Session recording**: Replay design sessions
- **Conflict visualization**: Highlight simultaneous edits
- **Cloud hosting**: Optional cloud server for internet-wide collaboration

## License

The collaboration feature is part of Optiverse and follows the same MIT license.

