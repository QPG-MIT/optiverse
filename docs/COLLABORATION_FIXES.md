# Collaboration Server Fixes

## Issues Resolved

### 1. Deprecation Warning Fixed ✅
**Problem**: `websockets.server.WebSocketServerProtocol is deprecated`

**Solution**: Changed import to use the legacy module:
```python
from websockets.legacy.server import WebSocketServerProtocol
```

### 2. Subprocess Blocking Fixed ✅
**Problem**: Server process would hang when started from dialog because stdout/stderr pipes were filling up

**Solution**: 
- Redirect stdout/stderr to `DEVNULL` to prevent pipe blocking
- Server runs in background without console output
- No more hanging processes

### 3. Cross-Platform Support ✅
**Problem**: Previous implementation only considered Windows

**Solution**: Platform-specific subprocess flags:

**Windows:**
```python
creationflags = CREATE_NO_WINDOW | DETACHED_PROCESS
# Server runs hidden in background
```

**Mac/Linux:**
```python
start_new_session = True
# Server runs in new session, detached from terminal
```

### 4. Improved Error Handling ✅
- Server startup is validated (1 second wait + poll check)
- Better error messages with actionable steps
- Graceful termination with fallback to force kill
- Exception handling in stop logic

## How It Works Now

### Starting Server from Dialog:

1. Click **"Host server"** mode
2. Configure port and address
3. Click **"Start Server"**
4. Server starts **silently in background**
5. Status shows "Server running on..."
6. No console windows popup
7. No subprocess hanging

### Cross-Platform Behavior:

| Platform | Behavior |
|----------|----------|
| Windows  | Hidden background process, detached from parent |
| Mac      | Background process, new session |
| Linux    | Background process, new session |

### Server Lifecycle:

```
[Dialog] → [Start Button] → [Spawn Subprocess] → [Background Server]
                                    ↓
                            [Detached + Silent]
                                    ↓
                            [1s validation check]
                                    ↓
                        [Success or Error Message]
```

### Stopping Server:

```
[Stop Button] → [Terminate Signal] → [3s wait] → [Force Kill if needed]
```

## Technical Details

### Subprocess Configuration

```python
kwargs = {
    "args": [sys.executable, "server.py", "--host", host, "--port", port],
    "stdout": subprocess.DEVNULL,  # No output buffering issues
    "stderr": subprocess.DEVNULL,  # No error buffering issues
}

# Platform-specific flags
if sys.platform == "win32":
    kwargs["creationflags"] = 0x08000000 | 0x00000008  # NO_WINDOW + DETACHED
else:
    kwargs["start_new_session"] = True  # Unix session detach
```

### Process Validation

```python
process = subprocess.Popen(**kwargs)
time.sleep(1.0)  # Give it time to start

if process.poll() is not None:
    # Process died - show error
    raise Exception("Server failed to start")
else:
    # Success!
    show_success_status()
```

### Graceful Shutdown

```python
process.terminate()  # SIGTERM / WM_CLOSE
try:
    process.wait(timeout=3)  # Wait for clean exit
except TimeoutExpired:
    process.kill()  # SIGKILL / TerminateProcess
    process.wait()  # Reap zombie
```

## User Experience

### Before Fixes:
- ❌ Server wouldn't start from dialog
- ❌ Console windows popping up
- ❌ Process hanging/blocking
- ❌ Connection refused errors
- ❌ Manual server startup required

### After Fixes:
- ✅ Server starts cleanly from dialog
- ✅ No console windows
- ✅ No blocking or hanging
- ✅ Reliable connection
- ✅ Fully integrated experience

## Testing

### Test on Windows:
```powershell
# Open Optiverse
# Go to Collaboration → Connect/Host Session
# Select "Host server"
# Click "Start Server"
# Should see: "Server running on 0.0.0.0:8765" (green)
# No console window should appear
```

### Test on Mac/Linux:
```bash
# Open Optiverse
# Go to Collaboration → Connect/Host Session
# Select "Host server"  
# Click "Start Server"
# Should see: "Server running on 0.0.0.0:8765" (green)
# No terminal interference
```

### Verify Server is Running:
```bash
# Windows
netstat -an | findstr 8765

# Mac/Linux
lsof -i :8765
# or
netstat -an | grep 8765
```

Should show server LISTENING on port 8765.

## Dependencies

Server requires `websockets` library:

```bash
# Install for development/server hosting
pip install websockets

# Or with project
pip install -e ".[server]"
```

Client (Optiverse UI) uses PyQt6's built-in WebSocket support (no extra dependency).

## Troubleshooting

### Server Won't Start

1. **Check websockets installed**:
   ```bash
   python -c "import websockets; print('OK')"
   ```

2. **Check port not in use**:
   ```bash
   # Windows
   netstat -an | findstr 8765
   
   # Mac/Linux
   lsof -i :8765
   ```

3. **Try different port**: Change from 8765 to 9999 or another free port

4. **Check firewall**: Ensure Python is allowed through firewall

### Connection Refused

1. **Verify server is running**: Check process manager or netstat
2. **Check URL format**: Must be `ws://` not `http://` or `wss://`
3. **Check address**: Use `localhost` or `127.0.0.1` for local testing

### Server Won't Stop

1. **Use Task Manager/Activity Monitor**: Find Python process and kill it
2. **Restart Optiverse**: Dialog cleanup will attempt to stop server
3. **Reboot if necessary**: Last resort for stuck processes

## Future Enhancements

Potential improvements:
- [ ] Server log viewer in dialog
- [ ] Port conflict detection before starting
- [ ] Auto-select free port if specified port busy
- [ ] Server status LED indicator
- [ ] Server restart button
- [ ] Multiple session management

## Conclusion

The collaboration server now works reliably across all platforms with no user intervention required beyond clicking "Start Server". The implementation is clean, maintainable, and follows best practices for subprocess management.

