# Debugging Collaboration Connection Issues

## Diagnostic Tools Added

### Client-Side Diagnostics
The CollaborationService now logs:
- `[COLLAB]` prefixed messages
- Object IDs (to track if objects are recreated)
- Parent relationships
- WebSocket state transitions
- Close codes and reasons
- Stack traces when disconnect occurs

### Server-Side Diagnostics
The server now logs:
- Connection lifecycle events
- Message loop entry/exit
- Close codes and reasons
- Error stack traces

## Running Diagnostics

### Step 1: Start Server with Logging
```bash
python tools/collaboration_server.py --host 0.0.0.0 --port 8765
```

Watch for these log messages:
- "server listening on..."
- "User {id} joined session"
- "Entering message loop for {id}"
- "Message loop ended for {id}" (shouldn't happen immediately)

### Step 2: Connect from Optiverse

1. Open Optiverse
2. Collaboration → Connect/Host Session
3. Connect to ws://localhost:8765
4. Watch console output

### Expected Output (WORKING):
```
[COLLAB] Connecting to: ws://localhost:8765/ws/default/USER
[COLLAB] CollaborationService id: 123456789
[COLLAB] QWebSocket id: 987654321
[COLLAB] Parent: <CollaborationManager object>
[COLLAB] Connected to session default as USER
[COLLAB] WebSocket state: ConnectedState
[COLLAB] WebSocket isValid: True
Connection acknowledged: {...}
```

### Problematic Output (AUTO-DISCONNECT):
```
[COLLAB] Connected to session default as USER
[COLLAB] Disconnected from session default
[COLLAB] WebSocket state: UnconnectedState  
[COLLAB] WebSocket closeCode: 1000
[COLLAB] WebSocket closeReason: ""
[COLLAB] Disconnect called from:
  <stack trace will show exact call path>
```

## Interpretation Guide

### Close Codes
- **1000**: Normal closure (initiated by client or server)
- **1001**: Going Away (endpoint going away)
- **1002**: Protocol error
- **1006**: Abnormal closure (no close frame received)

### Common Issues

#### Issue: Stack trace shows disconnect_from_session
**Cause**: Something is explicitly calling disconnect
**Solution**: Check what triggered the disconnect call

#### Issue: closeCode 1006, no close frame
**Cause**: Network issue or server crash
**Solution**: Check server is still running, check network

#### Issue: "Parent: None"
**Cause**: CollaborationService has no parent, might get garbage collected
**Solution**: Ensure proper parent ownership

#### Issue: Message loop ends immediately on server
**Cause**: Server closing connection right after accepting
**Solution**: Check server exception logs

## Test Checklist

Run through these scenarios:

- [ ] Start server, verify it stays running
- [ ] Connect from one client, stays connected for 30+ seconds
- [ ] Connect from two clients simultaneously
- [ ] Both clients see each other join
- [ ] Add item in one client, appears in other
- [ ] Move item in one client, updates in other
- [ ] Delete item in one client, removes in other
- [ ] Close one client, other stays connected

## Next Steps Based on Diagnostics

### If disconnect shows stack trace from your code:
1. Identify the code path
2. Add condition to prevent unwanted disconnect
3. Test again

### If disconnect shows no user-code in stack:
1. Check Qt event loop isn't being blocked
2. Verify WebSocket parent ownership
3. Check for Qt signals disconnecting prematurely

### If server shows connection close immediately:
1. Check server exception logs
2. Verify websockets library compatibility
3. Test server with simple WebSocket client

## Manual Server Test

Test server independently:
```python
import asyncio
import websockets

async def test():
    uri = "ws://localhost:8765/ws/test/testuser"
    async with websockets.connect(uri) as ws:
        # Should receive connection:ack
        msg = await ws.recv()
        print(f"Received: {msg}")
        
        # Wait 5 seconds
        await asyncio.sleep(5)
        
        # Still connected?
        await ws.send('{"type": "ping"}')
        print("Still connected!")

asyncio.run(test())
```

If this works but Qt client doesn't, issue is Qt-specific.
If this fails too, issue is server-side.

## Report Format

When reporting issues, include:

1. **Console output** from Optiverse (with [COLLAB] logs)
2. **Server logs** from terminal
3. **Stack trace** if disconnect occurs
4. **Close code and reason** from diagnostics
5. **Object IDs** (to check if objects were recreated)

This information will pinpoint the exact cause of the disconnect.

