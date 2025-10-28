# Collaboration System V2 - Complete Implementation

## 📋 Overview

The collaboration system has been completely reworked with a robust architecture supporting:
- ✅ **Session Creation**: Host can create sessions with current or empty canvas
- ✅ **Session Joining**: Clients can join and receive full canvas state
- ✅ **Initial State Sync**: Full canvas synchronization when joining
- ✅ **Incremental Updates**: Only changes are broadcast after initial sync
- ✅ **Reconnection Handling**: Automatic state resynchronization
- ✅ **Conflict Resolution**: Host's state wins on conflicts

## 🏗️ Architecture

### Components

1. **CollaborationManager** (`src/optiverse/services/collaboration_manager.py`)
   - Manages session roles (host/client)
   - Handles state synchronization
   - Tracks version numbers for conflict detection
   - Broadcasts changes and applies remote updates

2. **CollaborationService** (`src/optiverse/services/collaboration_service.py`)
   - WebSocket connection management
   - Message sending/receiving
   - Handles full state sync messages

3. **CollaborationDialog** (`src/optiverse/ui/views/collaboration_dialog.py`)
   - UI for creating/joining sessions
   - Options for canvas state (current/empty)
   - Server hosting controls

4. **CollaborationServer** (`tools/collaboration_server.py`)
   - Stores session state
   - Identifies host (first user)
   - Serves state to new joiners
   - Broadcasts changes to all participants

## 🔄 Workflow

### Creating a Session (Host)

1. **User Action**: File → Collaboration → Connect/Host Session
2. **Choose Mode**: Select "Host server"
3. **Configure Session**:
   - Set session ID
   - Choose canvas option:
     - **Use current canvas**: Share your current work with others
     - **Start with empty canvas**: Begin fresh collaboration
   - Configure server settings (address, port)
4. **Start Server**: Click "Start Server"
5. **Auto-connect**: Host automatically connects as first user

**Behind the Scenes**:
```python
# Host creates session with role="host"
collaboration_manager.create_session(
    session_id="my-session",
    user_id="host-user",
    use_current_canvas=True  # or False
)

# State is captured
session_state = {
    'items': [...],  # All canvas items
    'version': 0,
    'timestamp': '...'
}

# Server stores state with host identity
```

### Joining a Session (Client)

1. **User Action**: File → Collaboration → Connect/Host Session
2. **Choose Mode**: Select "Connect to server"
3. **Configure Connection**:
   - Enter server URL (e.g., `ws://192.168.1.100:8765`)
   - Enter session ID (provided by host)
   - Enter your name
4. **Warning**: "Joining will replace your current canvas"
5. **Connect**: Click "Connect"

**Behind the Scenes**:
```python
# Client joins with role="client"
collaboration_manager.join_session(
    server_url="ws://192.168.1.100:8765",
    session_id="my-session",
    user_id="client-user"
)

# 1. Canvas is cleared
# 2. Connect to server
# 3. Receive full state from server
# 4. Apply all items from state
# 5. Mark initial_sync_complete = True
```

### Initial State Synchronization

```
┌─────────┐                    ┌────────┐                    ┌─────────┐
│  HOST   │                    │ SERVER │                    │ CLIENT  │
└────┬────┘                    └───┬────┘                    └────┬────┘
     │                             │                              │
     │ 1. Create session            │                              │
     │────────────────────>         │                              │
     │                             │                              │
     │                             │ 2. Store host's state        │
     │                             │────────────>                 │
     │                             │                              │
     │                             │         3. Client joins      │
     │                             │<─────────────────────────────│
     │                             │                              │
     │                             │ 4. Send full state           │
     │                             │─────────────────────────────>│
     │                             │                              │
     │                             │                         5. Apply state
     │                             │                              │
     │         6. user:joined notification                        │
     │<────────────────────────────┤─────────────────────────────>│
     │                             │                              │
     │ 7. Host sends fresh state   │                              │
     │────────────────────>        │                              │
     │                             │ 8. Broadcast to client       │
     │                             │─────────────────────────────>│
     │                             │                              │
```

### Incremental Updates

After initial sync, only changes are sent:

```python
# User adds a lens on host
lens = LensItem(...)
scene.addItem(lens)

# CollaborationManager detects change
if initial_sync_complete:
    broadcast_add_item(lens)
    _increment_version()  # version += 1
    
    # Send command message
    {
        'type': 'command',
        'command': {
            'action': 'add_item',
            'item_type': 'lens',
            'item_id': 'uuid-123',
            'data': {...}
        }
    }
```

### Reconnection & Conflict Resolution

```
┌─────────┐                    ┌────────┐                    ┌─────────┐
│ CLIENT  │                    │ SERVER │                    │  HOST   │
└────┬────┘                    └───┬────┘                    └────┬────┘
     │                             │                              │
     │ 1. Connection lost          │                              │
     │ ╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳╳           │                              │
     │                             │                              │
     │ 2. Cache local state        │                              │
     │ needs_resync = True         │                              │
     │                             │                              │
     │ 3. Reconnect                │                              │
     │────────────────────>        │                              │
     │                             │                              │
     │ 4. Request sync (with local version)                       │
     │────────────────────>        │                              │
     │                             │                              │
     │                             │ 5. Check stored state        │
     │                             │ (host's version)             │
     │                             │                              │
     │ 6. Receive full state       │                              │
     │<────────────────────        │                              │
     │                             │                              │
     │ 7. Detect version conflict  │                              │
     │    local=3, remote=5        │                              │
     │                             │                              │
     │ 8. Apply host's state       │                              │
     │    (host wins)              │                              │
     │ Clear scene                 │                              │
     │ Apply all items             │                              │
     │ session_version = 5         │                              │
     │ needs_resync = False        │                              │
     │                             │                              │
```

## 🔑 Key Features

### 1. Role-Based System

**Host**:
- First user to join a session
- Manages authoritative state
- Can share current canvas or start fresh
- Version updates originate from host

**Client**:
- Joins existing session
- Receives initial full state
- Sends changes that get merged into host's state
- On conflict, adopts host's state

### 2. Version Tracking

Every change increments the version:
```python
session_version: int = 0  # Starts at 0

# On each change:
self._increment_version()  # version += 1
```

Version is used to detect conflicts during reconnection.

### 3. Broadcast Suppression

Prevents feedback loops:
```python
# When applying remote changes:
self._suppress_broadcast = True
try:
    # Apply changes without broadcasting back
    scene.addItem(remote_item)
finally:
    self._suppress_broadcast = False
```

During initial sync:
```python
if not self.initial_sync_complete:
    return  # Don't broadcast during sync
```

### 4. State Management

**Complete State** (sent on join/reconnection):
```python
{
    'items': [
        {
            'item_type': 'lens',
            'uuid': 'abc-123',
            'x_mm': 100.0,
            'y_mm': 50.0,
            'focal_length_mm': 100.0,
            ...
        },
        ...
    ],
    'version': 5,
    'timestamp': '2025-10-28T12:00:00'
}
```

**Incremental Command** (sent on change):
```python
{
    'type': 'command',
    'command': {
        'action': 'add_item',  # or 'move_item', 'remove_item', 'update_item'
        'item_type': 'lens',
        'item_id': 'abc-123',
        'data': {...}
    }
}
```

## 🧪 Testing

Comprehensive test suites have been created:

### State Sync Tests (`tests/services/test_collaboration_state_sync.py`)
- ✅ Session creation with current/empty canvas
- ✅ Host/client role assignment
- ✅ Initial state sync to clients
- ✅ Incremental updates after sync
- ✅ Version tracking and JSON serialization

### Reconnection Tests (`tests/services/test_collaboration_reconnection.py`)
- ✅ Disconnection detection
- ✅ State caching before disconnect
- ✅ Reconnection triggers sync request
- ✅ Version conflict detection
- ✅ Conflict resolution (host wins)
- ✅ Scene clearing and reapplication

### Running Tests

```bash
# Run state sync tests
python -m pytest tests/services/test_collaboration_state_sync.py -v

# Run reconnection tests
python -m pytest tests/services/test_collaboration_reconnection.py -v

# Run all collaboration tests
python -m pytest tests/services/test_collaboration*.py -v
```

## 📝 Usage Guide

### For the Host

1. **Start with current work**:
   - File → Collaboration → Connect/Host Session
   - Select "Host server"
   - Choose "Use current canvas"
   - Start server and share the connection info

2. **Start fresh**:
   - Same as above, but choose "Start with empty canvas"
   - Your current canvas will be cleared

3. **Share connection info**:
   - Give others: `ws://YOUR_IP:8765` and session ID
   - Find your IP in the dialog info label

### For Clients

1. **Join session**:
   - File → Collaboration → Connect/Host Session
   - Select "Connect to server"
   - Enter host's server URL and session ID
   - Click Connect

2. **⚠️ Warning**: Your current canvas will be replaced!

3. **Work collaboratively**:
   - Add/move/delete objects
   - Changes sync in real-time
   - See others' cursors (if implemented)

### Disconnecting

- File → Collaboration → Disconnect
- Server stops if you were hosting
- Canvas remains in current state

## 🔧 Implementation Details

### New Properties in CollaborationManager

```python
# Session management
self.role: Optional[str] = None  # "host" or "client"
self.session_id: Optional[str] = None
self.session_version: int = 0
self.initial_sync_complete: bool = False

# Reconnection handling
self.needs_resync: bool = False
self.last_known_state: Optional[Dict[str, Any]] = None
self.pending_changes: list[Dict[str, Any]] = []
```

### New Methods

**CollaborationManager**:
- `create_session()`: Create session as host
- `join_session()`: Join session as client
- `get_session_state()`: Get complete canvas state
- `_increment_version()`: Increment version counter
- `_detect_version_conflict()`: Detect state conflicts

**Server**:
- Stores `session_state` mapping session_id to state
- Identifies first user as host
- Sends stored state to new joiners
- Handles `sync:request` for reconnection

## 🎯 Future Enhancements

Potential improvements (not yet implemented):
- [ ] User cursors/selections visualization
- [ ] Undo/redo across collaboration
- [ ] Session persistence (save/load)
- [ ] More conflict resolution strategies
- [ ] Bandwidth optimization (delta compression)
- [ ] Presence indicators (who's editing what)

## 🐛 Known Limitations

1. **No partial state updates**: On conflict, entire canvas is replaced
2. **Host dependency**: If host disconnects, clients may lose sync
3. **No authentication**: Anyone with URL can join
4. **Local server only**: No cloud hosting built-in

## 📚 Related Documentation

- `COLLABORATION.md` - Original collaboration docs
- `COLLABORATION_SERVER_V2_SUMMARY.md` - Server implementation
- `COLLABORATION_TESTING_GUIDE.md` - Testing procedures
- `COLLABORATION_VERIFIED_WORKING.md` - Verification results

## ✅ Summary

The collaboration system now supports:
1. ✅ Creating sessions with canvas options
2. ✅ Joining sessions with full state sync  
3. ✅ Real-time incremental updates
4. ✅ Automatic reconnection with conflict resolution
5. ✅ Comprehensive test coverage
6. ✅ Intuitive UI for all operations

The system is ready for collaborative optical design work!

