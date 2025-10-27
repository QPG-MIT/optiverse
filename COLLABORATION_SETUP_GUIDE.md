# Collaboration Setup Guide

Quick guide to get real-time collaboration working in your Optiverse app.

---

## 📦 Installation

### 1. Install Server Dependencies

```bash
pip install aiohttp requests
```

### 2. Install PyQt6 WebSocket Support

```bash
pip install PyQt6-WebSockets
```

---

## 🚀 Quick Start (5 minutes!)

### Step 1: Start the Server

```bash
# In a terminal/command prompt
python collaboration_server.py
```

You should see:
```
🚀 Optiverse Collaboration Server
==================================================
Server running on http://localhost:8080
WebSocket endpoint: ws://localhost:8080/ws/{session_id}/{user_id}
Create session: POST http://localhost:8080/api/sessions
==================================================
```

**Leave this running!** Open a new terminal for the next steps.

---

### Step 2: Test the Server (Optional)

```bash
# In a new terminal, test the server is working
curl http://localhost:8080/health
```

Should return: `{"status":"ok","active_sessions":0,"total_users":0}`

---

### Step 3: Run Your App

```bash
# In another terminal
python -m optiverse.app.main
```

---

### Step 4: Test Collaboration

1. **Open TWO instances** of your app (just run `python -m optiverse.app.main` twice)

2. **In Window 1:**
   - Click the "📤 Share" button (if you added it to the UI)
   - Click "Create New Session"
   - Enter your name (e.g., "Alice")
   - Click "Create New Session" button
   - Copy the Session ID that appears

3. **In Window 2:**
   - Click the "📤 Share" button
   - Go to the "Join" tab
   - Paste the Session ID
   - Enter your name (e.g., "Bob")
   - Click OK

4. **Test it:**
   - In Window 1: Add a lens or source
   - It should appear in Window 2 instantly!
   - Try dragging components in either window
   - Both should stay in sync

---

## 📝 Integration Checklist

### ✅ Files Created

- [x] `collaboration_server.py` - The minimal server
- [x] `src/optiverse/services/collaboration_service.py` - PyQt6 WebSocket client
- [x] `src/optiverse/ui/views/share_dialog.py` - Share/Join UI
- [x] `COLLABORATIVE_CLIENT_INTEGRATION_EXAMPLE.py` - Integration examples

### 📋 Files to Modify

#### 1. `src/optiverse/ui/views/main_window.py`

Add to `__init__()`:
```python
# At the end of __init__, after other initialization
self._init_collaboration()
```

Add all methods from `MainWindowCollaborationMixin` in the example file.

#### 2. Component Items (SourceItem, LensItem, MirrorItem, BeamsplitterItem)

For EACH component class, add:

```python
import uuid

class SourceItem(BaseObj):  # or LensItem, MirrorItem, etc.
    def __init__(self):
        super().__init__()
        # ADD THIS:
        self.component_id = str(uuid.uuid4())
        # ... rest of existing init ...
    
    # ADD THESE METHODS:
    def serialize(self) -> dict:
        """See example file for complete implementation."""
        return {
            'id': self.component_id,
            'kind': 'source',  # or 'lens', 'mirror', 'beamsplitter'
            'x_mm': self.pos().x(),
            'y_mm': self.pos().y(),
            'angle_deg': self.rotation(),
            # ... add type-specific fields ...
        }
    
    def deserialize(self, data: dict):
        """See example file for complete implementation."""
        self.component_id = data.get('id', self.component_id)
        self.setPos(data.get('x_mm', 0), data.get('y_mm', 0))
        self.setRotation(data.get('angle_deg', 0))
        # ... restore type-specific fields ...
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # ADD THIS at the end:
        self._send_collab_update('component:move')
    
    def _send_collab_update(self, action_type: str):
        """See example file for complete implementation."""
        # Gets main window and calls _send_component_message
```

See `COLLABORATIVE_CLIENT_INTEGRATION_EXAMPLE.py` for complete implementations.

---

## 🧪 Testing

### Test 1: Local (Same Machine)

1. Start server: `python collaboration_server.py`
2. Open app instance 1
3. Open app instance 2
4. Create session in #1, join in #2
5. Test adding/moving components

### Test 2: Network (Different Machines)

1. Start server on Machine A: `python collaboration_server.py`
2. Find Machine A's IP address:
   - Windows: `ipconfig`
   - Mac/Linux: `ifconfig` or `ip addr`
3. On Machine B, modify `share_dialog.py`:
   ```python
   self.server_url = "http://MACHINE_A_IP:8080"
   ```
4. Create session on Machine A
5. Join on Machine B with the session ID

### Test 3: Internet (Using ngrok)

```bash
# On the machine running the server
ngrok http 8080
```

ngrok will give you a public URL like: `https://abc123.ngrok.io`

Update `share_dialog.py`:
```python
self.server_url = "https://abc123.ngrok.io"
```

Now anyone on the internet can collaborate!

---

## 🐛 Troubleshooting

### "Connection refused" error

**Problem:** Server is not running or wrong URL.

**Solution:**
1. Check server is running: `curl http://localhost:8080/health`
2. Check firewall isn't blocking port 8080
3. Verify `server_url` in share_dialog.py matches server address

### "Module 'requests' not found"

**Problem:** Missing dependency.

**Solution:**
```bash
pip install requests
```

### "Module 'PyQt6.QtWebSockets' not found"

**Problem:** Missing PyQt6 WebSocket module.

**Solution:**
```bash
pip install PyQt6-WebSockets
```

### Components don't sync between windows

**Problem:** Missing `serialize()`/`deserialize()` methods or not sending updates.

**Solution:**
1. Check that all component classes have `serialize()` and `deserialize()`
2. Check that `_send_collab_update()` is called in `mouseMoveEvent()`
3. Look for errors in terminal output

### Server crashes or becomes unresponsive

**Problem:** Possible bug in server code or too many connections.

**Solution:**
1. Restart server
2. Check server terminal for error messages
3. Try with fewer concurrent users

### Changes lag or feel slow

**Problem:** Network latency or server overload.

**Solution:**
1. If testing locally: Should be <50ms, check for other issues
2. If over internet: Expected, consider local server or better hosting
3. Reduce update frequency (debounce mouseMoveEvent updates)

---

## 🔒 Security Notes

### For Development
- Default setup runs on localhost only (safe for testing)
- No authentication required (anyone with session ID can join)

### For Production
Consider adding:
1. **Password protection** for sessions
2. **Session expiry** after 24 hours
3. **Rate limiting** to prevent abuse
4. **HTTPS/WSS** for encrypted connections
5. **User authentication** (login system)

See `collaboration_server.py` comments for password protection example.

---

## 📊 Monitoring

### Check Server Status

```bash
curl http://localhost:8080/health
```

Returns:
```json
{
  "status": "ok",
  "active_sessions": 2,
  "total_users": 5
}
```

### Check Session Info

```bash
curl http://localhost:8080/api/sessions/SESSION_ID_HERE
```

---

## 🚀 Deployment

### Option 1: Railway (Free Tier)

1. Create account at railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your repo
4. Railway will detect Python and run `collaboration_server.py`
5. Get the public URL from Railway dashboard
6. Update `share_dialog.py` with the Railway URL

### Option 2: Heroku

1. Create `Procfile`:
   ```
   web: python collaboration_server.py
   ```
2. Create `requirements.txt`:
   ```
   aiohttp==3.9.1
   ```
3. Deploy to Heroku:
   ```bash
   heroku create
   git push heroku main
   ```

### Option 3: Your Own Server

```bash
# On your server (Ubuntu example)
sudo apt install python3-pip
pip3 install aiohttp
python3 collaboration_server.py
```

To run in background:
```bash
nohup python3 collaboration_server.py &
```

Or use systemd service:
```ini
# /etc/systemd/system/optiverse-collab.service
[Unit]
Description=Optiverse Collaboration Server
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/optiverse
ExecStart=/usr/bin/python3 collaboration_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable optiverse-collab
sudo systemctl start optiverse-collab
```

---

## 📈 Performance Tips

### For Better Performance

1. **Debounce mouse move events** - Don't send every pixel
   ```python
   def mouseMoveEvent(self, event):
       super().mouseMoveEvent(event)
       # Only send every N pixels
       if not hasattr(self, '_last_sent_pos'):
           self._last_sent_pos = self.pos()
       
       dist = (self.pos() - self._last_sent_pos).manhattanLength()
       if dist > 5:  # Only send if moved >5 pixels
           self._send_collab_update('component:move')
           self._last_sent_pos = self.pos()
   ```

2. **Send final position on mouse release**
   ```python
   def mouseReleaseEvent(self, event):
       super().mouseReleaseEvent(event)
       self._send_collab_update('component:move')  # Final position
   ```

3. **Use Redis for larger deployments**
   - Modify server to use Redis pub/sub
   - Allows multiple server instances
   - Better scalability

---

## 🎯 Next Steps

Once basic collaboration works:

1. **Add user presence indicators**
   - Show list of active users
   - Color-coded by user

2. **Add live cursors**
   - Show where other users' cursors are
   - Send cursor position periodically

3. **Add chat or comments**
   - Text chat between users
   - Comments on specific components

4. **Add version history**
   - Save state snapshots
   - Allow rollback

5. **Add permissions**
   - Owner, editor, viewer roles
   - Control who can edit

---

## 📚 Resources

- **aiohttp docs**: https://docs.aiohttp.org/
- **PyQt6 WebSockets**: https://doc.qt.io/qtforpython-6/PySide6/QtWebSockets/
- **WebSocket protocol**: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket

---

## 🆘 Getting Help

If you run into issues:

1. Check terminal output for errors (both server and client)
2. Test server with curl to isolate issues
3. Start with local testing before network testing
4. Refer to `COLLABORATIVE_CLIENT_INTEGRATION_EXAMPLE.py` for code samples

---

## ✅ Success!

If you can see components appear in both windows when you add/move them, **congratulations!** You have real-time collaboration working! 🎉

Total time from zero to working: **~30-60 minutes** (mostly code changes)

**Next:** Deploy the server to the cloud and invite others to collaborate from anywhere!

