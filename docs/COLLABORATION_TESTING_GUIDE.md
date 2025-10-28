# Collaboration Server Testing Guide

## Overview

This guide describes the test-driven approach to fixing and verifying the collaboration server.

## Problem

The original collaboration server was disconnecting immediately after connection with close code 1008 (Policy violation), likely due to WebSocket protocol incompatibility between Python's `websockets` library and Qt's `QWebSocket`.

## Solution: Test-Driven Development

We've created a layered testing approach to isolate and fix the issue:

### Layer 1: Minimal Server Test
**File**: `tools/test_minimal_server.py`

A bare-bones WebSocket server that just echoes messages back. This tests if the basic protocol works with Qt.

**Start the server:**
```bash
cd C:\Users\cohasset\Desktop\repos\optiverse
python tools/test_minimal_server.py
```

**Expected output:**
```
============================================================
MINIMAL WEBSOCKET TEST SERVER
============================================================
Starting on ws://localhost:8765
Configuration:
  - No automatic ping/pong
  - No compression
  - Simple echo handler
  - Press Ctrl+C to stop
============================================================
✓ Server ready and listening on ws://localhost:8765
Waiting for connections...
```

**Features:**
- ✅ Proper cleanup (Ctrl+C releases port)
- ✅ No automatic ping/pong
- ✅ Simple echo handler
- ✅ Signal handling for graceful shutdown

### Layer 2: Qt Client Test
**File**: `tools/test_qt_client.py`

Tests if Qt's QWebSocket can connect to the minimal server and stay connected.

**Start the test (with minimal server running):**
```bash
python tools/test_qt_client.py
```

**Expected output:**
```
============================================================
QT WEBSOCKET TEST CLIENT
============================================================
Make sure test_minimal_server.py is running first!
============================================================

→ Connecting to: ws://localhost:8765
✓ CONNECTED
  State: SocketState.ConnectedState
  Valid: True
  Starting to send test messages every 5 seconds...
→ Sending: Test message #1
← Received: Echo: Test message #1
→ Sending: Test message #2
← Received: Echo: Test message #2
...
```

**Success criteria:**
- ✅ Connection establishes
- ✅ Connection stays alive
- ✅ Messages are exchanged
- ✅ No unexpected disconnects

**If this fails**, there's a fundamental protocol issue between Qt and the websockets library.

### Layer 3: Full Collaboration Server
**File**: `tools/collaboration_server_v2.py`

Complete collaboration server built on the proven minimal foundation.

**Start the server:**
```bash
python tools/collaboration_server_v2.py

# Or with debug logging:
python tools/collaboration_server_v2.py --debug

# Or on a different port:
python tools/collaboration_server_v2.py --port 9000
```

**Expected output:**
```
======================================================================
OPTIVERSE COLLABORATION SERVER V2
======================================================================
Starting on ws://0.0.0.0:8765
Configuration:
  - ping_interval: None (disabled)
  - ping_timeout: None (disabled)
  - compression: None (disabled)
  - Application-level heartbeat
Press Ctrl+C to stop
======================================================================
✓ Server ready and listening
✓ Clients can connect to: ws://0.0.0.0:8765/ws/{session_id}/{user_id}
```

**Features:**
- ✅ Session management (multiple sessions)
- ✅ Multi-user support (multiple users per session)
- ✅ Application-level heartbeat
- ✅ Proper cleanup on Ctrl+C
- ✅ Graceful shutdown
- ✅ Port release
- ✅ Signal handling

### Layer 4: Automated Integration Test
**File**: `tools/test_collaboration.py`

Automated test that verifies the full collaboration workflow.

**Start the test (with collaboration_server_v2.py running):**
```bash
python tools/test_collaboration.py
```

**Expected output:**
```
======================================================================
COLLABORATION SERVER TEST
======================================================================
Test: Connect to ws://localhost:8765/ws/test_session/test_user
Expected: Connection stays alive for at least 15 seconds
======================================================================

✓ TEST STEP 1: CONNECTED
  State: SocketState.ConnectedState
  Valid: True

→ Sent heartbeat ping

✓ TEST STEP 2: MESSAGE RECEIVED
  Message: {"type": "connection:ack", ...}
  Total messages: 1

→ Sent heartbeat ping

✓ TEST STEP 2: MESSAGE RECEIVED
  Message: {"type": "pong", ...}
  Total messages: 2

======================================================================
✓ TEST PASSED
======================================================================
Connection stayed alive for 15+ seconds
Messages received: 3
Connection state: SocketState.ConnectedState
======================================================================

Closing connection...

✓ All tests passed!
```

**Success criteria:**
- ✅ Connection stays alive for 15+ seconds
- ✅ At least 2 messages received
- ✅ No unexpected disconnections
- ✅ Proper cleanup

## Running the Full Test Suite

### Step 1: Test Minimal Server + Qt Client

Terminal 1:
```bash
python tools/test_minimal_server.py
```

Terminal 2:
```bash
python tools/test_qt_client.py
```

**Expected:** Qt client connects, sends messages, receives echoes, stays connected.

### Step 2: Test Full Collaboration Server

Terminal 1:
```bash
python tools/collaboration_server_v2.py --debug
```

Terminal 2:
```bash
python tools/test_collaboration.py
```

**Expected:** Test passes after 15 seconds.

### Step 3: Test with Real Optiverse Application

Terminal 1:
```bash
python tools/collaboration_server_v2.py
```

Terminal 2:
```bash
optiverse
```

In Optiverse:
1. Open View → Show Log
2. Set Category to "Collaboration"
3. File → Collaboration → Connect
   - Server: `ws://localhost:8765`
   - Session: `default`
   - User: Your computer name
4. Click Connect

**Expected in Log Window:**
```
[HH:MM:SS] INFO | Collaboration | → Connecting to: ws://localhost:8765/ws/default/YOUR_USER
[HH:MM:SS] INFO | Collaboration | ✓ Connected to session 'default' as 'YOUR_USER'
[HH:MM:SS] INFO | Collaboration | Connection acknowledged with 1 user(s)
```

Connection should remain stable.

## Troubleshooting

### Test 1 (Minimal Server) Fails

**Problem:** Qt client can't connect or disconnects immediately.

**Diagnosis:**
- Check if `websockets` library is installed: `pip install websockets`
- Check if port 8765 is available: `netstat -an | findstr 8765`
- Try running with `--debug` flag

**Possible causes:**
- Firewall blocking port 8765
- Another process using port 8765
- Incompatible websockets library version

### Test 2 (Collaboration Server) Fails

**Problem:** Test client disconnects during the test.

**Check the server logs:**
- Look for error messages
- Check close code (should not be 1008)
- Verify no exceptions in server

**Check the client output:**
- Note the close code
- Check if any messages were received
- Look at timing of disconnect

### Connection to Optiverse Fails

**Problem:** Optiverse client disconnects immediately.

**Check collaboration logs:**
1. View → Show Log
2. Category: Collaboration
3. Look for close code and reason

**Common issues:**
- Server not running: Start `collaboration_server_v2.py`
- Wrong URL: Should be `ws://localhost:8765` (not `http://`)
- Port blocked: Check firewall
- Old server running: Kill old `collaboration_server.py` process

## Key Configuration Settings

### Server Settings (collaboration_server_v2.py)

```python
ping_interval=None,     # CRITICAL: No automatic ping
ping_timeout=None,      # CRITICAL: No automatic pong timeout
close_timeout=10,       # Give time for clean shutdown
compression=None,       # CRITICAL: No compression for Qt
max_size=2**20,        # 1MB max message size
```

### Client Settings (collaboration_service.py)

```python
# Heartbeat timer
self.heartbeat_timer.setInterval(30000)  # 30 seconds

# Application sends:
{"type": "ping"}

# Server responds:
{"type": "pong", "timestamp": "..."}
```

## Success Checklist

- [ ] Minimal server + Qt client: Connection stays alive
- [ ] Collaboration server + test client: Test passes
- [ ] Optiverse + collaboration server: Connection stable for 30+ seconds
- [ ] Optiverse + collaboration server: Heartbeat messages work
- [ ] Multiple Optiverse instances can connect to same session
- [ ] Server cleanup works (Ctrl+C releases port)
- [ ] Can restart server immediately after stopping

## Migration from Old Server

To switch from the old server to the new one:

1. Stop the old server (if running)
2. Update any scripts/docs to use `collaboration_server_v2.py`
3. Test thoroughly with the test suite
4. Once verified, can rename:
   - `collaboration_server.py` → `collaboration_server_old.py` (backup)
   - `collaboration_server_v2.py` → `collaboration_server.py`

## Next Steps

Once all tests pass:

1. ✅ Verify connection stability (15+ seconds)
2. ✅ Test multi-user collaboration
3. ✅ Test item synchronization (add/move/remove)
4. ✅ Test state synchronization
5. ✅ Test reconnection after disconnect
6. ✅ Load test (5+ users)

## Files Reference

```
tools/
  ├── test_minimal_server.py       # Layer 1: Basic protocol test
  ├── test_qt_client.py            # Layer 2: Qt WebSocket test
  ├── collaboration_server_v2.py   # Layer 3: Full collaboration server
  ├── test_collaboration.py        # Layer 4: Integration test
  └── collaboration_server.py      # OLD (keep as backup)

docs/
  ├── COLLABORATION_TESTING_GUIDE.md        # This file
  └── COLLABORATION_CONNECTION_FIX.md       # Original fix documentation
```

## Contact

If tests still fail after following this guide, provide:
1. Which test failed (1, 2, 3, or 4)
2. Complete output from both server and client
3. Close code and reason if connection failed
4. Operating system and Python version
5. `websockets` library version: `pip show websockets`

