# Client-Based Collaborative Optiverse Strategy

## 🎯 Approach: Desktop App + Minimal Backend

Keep your existing PyQt6 application, add real-time collaboration with minimal server infrastructure.

---

## Architecture Overview

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Desktop App   │         │   Desktop App   │         │   Desktop App   │
│    (User A)     │         │    (User B)     │         │    (User C)     │
│                 │         │                 │         │                 │
│  PyQt6 UI       │         │  PyQt6 UI       │         │  PyQt6 UI       │
│  Local Raytracing◄────────┼─────────────────┼────────►│  Local Raytracing
│  WebSocket Client│        │  WebSocket Client│        │  WebSocket Client│
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │        WebSocket          │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Coordination Server│
                          │   (Minimal/Simple)  │
                          │                     │
                          │  • Session manager  │
                          │  • Message router   │
                          │  • No computation!  │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   Redis (optional)  │
                          │   Session state     │
                          └─────────────────────┘
```

**Key Principle**: Clients do all the work (raytracing, rendering), server just coordinates.

---

## Why This Approach?

### Pros ✅
- **Keep existing PyQt6 app** - 95% code reuse
- **Local raytracing** - Full performance, no server computation
- **Quick to implement** - 2-3 weeks
- **Low hosting cost** - Minimal server ($5-10/month)
- **Users familiar with app** - No learning curve
- **Works offline** - Edit locally, sync when connected

### Cons ❌
- **Still need app installation** - Can't just "click a link"
- **Platform builds required** - Windows, Mac, Linux
- **Update distribution** - Users need to download new versions
- **No mobile support** - Qt doesn't work on phones

---

## Implementation Strategy

### Option 1: Lightweight WebSocket Server (RECOMMENDED)

**Server does:**
- Session management (create/join rooms)
- Message routing (broadcast to room members)
- User presence tracking

**Clients do:**
- All raytracing (reuse existing code)
- All rendering (existing Qt)
- State management (local)
- Send only state changes

**Cost**: $5-10/month  
**Timeline**: 2-3 weeks

---

### Option 2: WebRTC Peer-to-Peer

**Server does:**
- Signaling (help clients find each other)
- STUN/TURN for NAT traversal

**Clients do:**
- Direct P2P connection
- Everything (no server involvement after connection)

**Cost**: $5-15/month (STUN/TURN)  
**Timeline**: 3-4 weeks (WebRTC is complex)

---

## Recommended: Option 1 (Lightweight WebSocket)

Simpler, more reliable, easier to debug than WebRTC.

---

## Detailed Implementation Plan

### Phase 1: Minimal Backend (3-4 days)

#### Simple Python WebSocket Server

```python
# server.py - Ultra-minimal coordination server
import asyncio
import json
import secrets
from aiohttp import web
import aiohttp

# Active connections: {session_id: {user_id: websocket}}
sessions = {}

async def create_session(request):
    """Create a new session and return ID."""
    session_id = secrets.token_urlsafe(12)
    sessions[session_id] = {}
    return web.json_response({
        'session_id': session_id,
        'share_link': f'optiverse://join/{session_id}'
    })

async def websocket_handler(request):
    """Handle WebSocket connections."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    session_id = request.match_info['session_id']
    user_id = request.match_info['user_id']
    
    # Add to session
    if session_id not in sessions:
        sessions[session_id] = {}
    sessions[session_id][user_id] = ws
    
    # Notify others
    await broadcast(session_id, {
        'type': 'user:joined',
        'user_id': user_id
    }, exclude=user_id)
    
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                # Just forward to all others in session
                await broadcast(session_id, data, exclude=user_id)
    finally:
        # Cleanup
        if session_id in sessions and user_id in sessions[session_id]:
            del sessions[session_id][user_id]
        await broadcast(session_id, {
            'type': 'user:left',
            'user_id': user_id
        })
    
    return ws

async def broadcast(session_id, message, exclude=None):
    """Send message to all users in session except one."""
    if session_id not in sessions:
        return
    
    for user_id, ws in sessions[session_id].items():
        if user_id != exclude:
            try:
                await ws.send_json(message)
            except:
                pass

# Setup routes
app = web.Application()
app.router.add_post('/api/sessions', create_session)
app.router.add_get('/ws/{session_id}/{user_id}', websocket_handler)

if __name__ == '__main__':
    web.run_app(app, port=8080)
```

**That's it! ~70 lines.** No database, no complex logic, just message routing.

---

### Phase 2: PyQt6 WebSocket Client (5-7 days)

#### Add WebSocket to Existing App

```python
# src/optiverse/services/collaboration_service.py
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWebSockets import QWebSocket
from PyQt6.QtCore import QUrl
import json

class CollaborationService(QObject):
    """Handles real-time collaboration via WebSocket."""
    
    # Signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(dict)
    user_joined = pyqtSignal(str)  # user_id
    user_left = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.ws = QWebSocket()
        self.session_id = None
        self.user_id = None
        self.connected_state = False
        
        # Connect signals
        self.ws.connected.connect(self._on_connected)
        self.ws.disconnected.connect(self._on_disconnected)
        self.ws.textMessageReceived.connect(self._on_message)
        self.ws.error.connect(self._on_error)
    
    def connect_to_session(self, session_id: str, user_id: str, server_url: str = "ws://localhost:8080"):
        """Connect to a collaboration session."""
        self.session_id = session_id
        self.user_id = user_id
        url = f"{server_url}/ws/{session_id}/{user_id}"
        self.ws.open(QUrl(url))
    
    def disconnect_from_session(self):
        """Disconnect from current session."""
        if self.ws.isValid():
            self.ws.close()
    
    def send_message(self, message: dict):
        """Send a message to other users in session."""
        if self.connected_state:
            self.ws.sendTextMessage(json.dumps(message))
    
    def _on_connected(self):
        """Called when WebSocket connection established."""
        self.connected_state = True
        self.connected.emit()
        print(f"Connected to session {self.session_id}")
    
    def _on_disconnected(self):
        """Called when WebSocket disconnected."""
        self.connected_state = False
        self.disconnected.emit()
        print("Disconnected from session")
    
    def _on_message(self, message: str):
        """Called when message received from server."""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'user:joined':
                self.user_joined.emit(data['user_id'])
            elif msg_type == 'user:left':
                self.user_left.emit(data['user_id'])
            else:
                self.message_received.emit(data)
        except Exception as e:
            print(f"Error parsing message: {e}")
    
    def _on_error(self, error_code):
        """Called on WebSocket error."""
        print(f"WebSocket error: {error_code}")
```

---

### Phase 3: Integrate into MainWindow (3-4 days)

#### Modify Existing MainWindow

```python
# src/optiverse/ui/views/main_window.py
# Add to existing MainWindow class

from ...services.collaboration_service import CollaborationService

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # ... existing code ...
        
        # NEW: Add collaboration service
        self.collab_service = CollaborationService()
        self.collab_service.message_received.connect(self._on_remote_update)
        self.collab_service.user_joined.connect(self._on_user_joined)
        self.collab_service.user_left.connect(self._on_user_left)
        self.collab_service.connected.connect(self._on_collab_connected)
        
        self._setup_collaboration_ui()
    
    def _setup_collaboration_ui(self):
        """Add collaboration UI elements."""
        # Add "Share" button to toolbar
        share_btn = QtWidgets.QPushButton("📤 Share")
        share_btn.clicked.connect(self._show_share_dialog)
        self.toolbar.addWidget(share_btn)
        
        # Add status indicator
        self.collab_status = QtWidgets.QLabel("Not connected")
        self.statusBar().addPermanentWidget(self.collab_status)
    
    def _show_share_dialog(self):
        """Show dialog to create/join session."""
        dialog = ShareDialog(self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            session_id = dialog.session_id
            user_id = dialog.user_id or "user_" + str(int(time.time()))
            self.collab_service.connect_to_session(session_id, user_id)
    
    def _on_collab_connected(self):
        """Called when connected to session."""
        self.collab_status.setText(f"🟢 Connected ({self.collab_service.session_id})")
        # Send current state to sync with others
        self._send_full_state()
    
    def _send_full_state(self):
        """Send all components to newly joined user."""
        for item in self.scene.items():
            if isinstance(item, (SourceItem, LensItem, MirrorItem, BeamsplitterItem)):
                self._send_component_state(item, "component:add")
    
    def _send_component_state(self, item, action_type):
        """Send component state to other users."""
        data = {
            'type': action_type,
            'data': item.serialize()  # Need to add serialize() method to items
        }
        self.collab_service.send_message(data)
    
    def _on_remote_update(self, message: dict):
        """Handle update from another user."""
        msg_type = message.get('type')
        data = message.get('data', {})
        
        if msg_type == 'component:add':
            self._add_remote_component(data)
        elif msg_type == 'component:move':
            self._move_remote_component(data)
        elif msg_type == 'component:delete':
            self._delete_remote_component(data)
        elif msg_type == 'component:edit':
            self._edit_remote_component(data)
        
        # Retrace rays after any change
        if self.autotrace:
            self.refresh_rays()
    
    def _add_remote_component(self, data):
        """Add component from remote user."""
        # Prevent sending back the same change
        self._suppress_collab_send = True
        try:
            kind = data.get('kind')
            if kind == 'source':
                item = SourceItem()
            elif kind == 'lens':
                item = LensItem()
            elif kind == 'mirror':
                item = MirrorItem()
            elif kind == 'beamsplitter':
                item = BeamsplitterItem()
            else:
                return
            
            item.deserialize(data)
            self.scene.addItem(item)
        finally:
            self._suppress_collab_send = False
    
    def _move_remote_component(self, data):
        """Move component from remote user."""
        comp_id = data.get('id')
        x_mm = data.get('x_mm')
        y_mm = data.get('y_mm')
        
        # Find item by ID
        item = self._find_item_by_id(comp_id)
        if item:
            self._suppress_collab_send = True
            try:
                item.setPos(x_mm, y_mm)
            finally:
                self._suppress_collab_send = False
    
    def _on_user_joined(self, user_id: str):
        """Called when another user joins."""
        self.statusBar().showMessage(f"User {user_id} joined", 3000)
        # Send full state to new user (they'll request it, we'll send)
    
    def _on_user_left(self, user_id: str):
        """Called when another user leaves."""
        self.statusBar().showMessage(f"User {user_id} left", 3000)
```

---

### Phase 4: Hook into Existing Item Classes (2-3 days)

#### Add Serialization to Items

```python
# src/optiverse/widgets/source_item.py
# Add to SourceItem class

class SourceItem(BaseObj):
    # ... existing code ...
    
    def __init__(self):
        super().__init__()
        # Generate unique ID for this component
        import uuid
        self.component_id = str(uuid.uuid4())
    
    def serialize(self) -> dict:
        """Serialize item state for network transmission."""
        return {
            'id': self.component_id,
            'kind': 'source',
            'x_mm': self.pos().x(),
            'y_mm': self.pos().y(),
            'angle_deg': self.rotation(),
            'n_rays': self.n_rays,
            'spread_deg': self.spread_deg,
            'ray_length_mm': self.ray_length_mm,
            'color_hex': self.color_hex,
            'size_mm': self.size_mm
        }
    
    def deserialize(self, data: dict):
        """Restore item state from network data."""
        self.component_id = data.get('id')
        self.setPos(data.get('x_mm', 0), data.get('y_mm', 0))
        self.setRotation(data.get('angle_deg', 0))
        self.n_rays = data.get('n_rays', 9)
        self.spread_deg = data.get('spread_deg', 0)
        self.ray_length_mm = data.get('ray_length_mm', 1000)
        self.color_hex = data.get('color_hex', '#DC143C')
        self.size_mm = data.get('size_mm', 10)
    
    def mouseMoveEvent(self, event):
        """Override to send updates during drag."""
        super().mouseMoveEvent(event)
        
        # Send update to collaborators
        if hasattr(self.scene(), 'views') and len(self.scene().views()) > 0:
            main_window = self.scene().views()[0].parent()
            if hasattr(main_window, 'collab_service') and main_window.collab_service.connected_state:
                if not getattr(main_window, '_suppress_collab_send', False):
                    main_window._send_component_state(self, 'component:move')
```

Similar changes for `LensItem`, `MirrorItem`, `BeamsplitterItem`.

---

### Phase 5: Share Dialog (1-2 days)

```python
# src/optiverse/ui/views/share_dialog.py
from PyQt6 import QtWidgets, QtCore
import requests

class ShareDialog(QtWidgets.QDialog):
    """Dialog for creating/joining collaboration sessions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Collaborate")
        self.session_id = None
        self.user_id = None
        self.server_url = "http://localhost:8080"  # Make configurable
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Tab widget for Create vs Join
        tabs = QtWidgets.QTabWidget()
        
        # Create tab
        create_tab = QtWidgets.QWidget()
        create_layout = QtWidgets.QVBoxLayout(create_tab)
        
        create_layout.addWidget(QtWidgets.QLabel("Create a new session to share with others:"))
        
        self.user_name_input = QtWidgets.QLineEdit()
        self.user_name_input.setPlaceholderText("Your name")
        create_layout.addWidget(self.user_name_input)
        
        create_btn = QtWidgets.QPushButton("Create Session")
        create_btn.clicked.connect(self._create_session)
        create_layout.addWidget(create_btn)
        
        self.share_link_label = QtWidgets.QLabel("")
        self.share_link_label.setWordWrap(True)
        self.share_link_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        create_layout.addWidget(self.share_link_label)
        
        copy_btn = QtWidgets.QPushButton("Copy Link")
        copy_btn.clicked.connect(self._copy_link)
        create_layout.addWidget(copy_btn)
        
        create_layout.addStretch()
        tabs.addTab(create_tab, "Create")
        
        # Join tab
        join_tab = QtWidgets.QWidget()
        join_layout = QtWidgets.QVBoxLayout(join_tab)
        
        join_layout.addWidget(QtWidgets.QLabel("Join an existing session:"))
        
        self.session_id_input = QtWidgets.QLineEdit()
        self.session_id_input.setPlaceholderText("Session ID")
        join_layout.addWidget(self.session_id_input)
        
        self.join_name_input = QtWidgets.QLineEdit()
        self.join_name_input.setPlaceholderText("Your name")
        join_layout.addWidget(self.join_name_input)
        
        join_layout.addStretch()
        tabs.addTab(join_tab, "Join")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _create_session(self):
        """Create a new session on the server."""
        try:
            response = requests.post(f"{self.server_url}/api/sessions", timeout=5)
            data = response.json()
            self.session_id = data['session_id']
            self.share_link_label.setText(f"Share this: {data['share_link']}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to create session: {e}")
    
    def _copy_link(self):
        """Copy share link to clipboard."""
        if self.session_id:
            link = f"optiverse://join/{self.session_id}"
            QtWidgets.QApplication.clipboard().setText(link)
            QtWidgets.QMessageBox.information(self, "Copied", "Link copied to clipboard!")
    
    def _on_accept(self):
        """Handle OK button."""
        # Get session ID (either created or entered)
        if not self.session_id:
            self.session_id = self.session_id_input.text().strip()
        
        if not self.session_id:
            QtWidgets.QMessageBox.warning(self, "Error", "Please create or enter a session ID")
            return
        
        # Get user name
        self.user_id = self.user_name_input.text().strip() or self.join_name_input.text().strip()
        if not self.user_id:
            self.user_id = f"User_{int(time.time())}"
        
        self.accept()
```

---

## Timeline

### Week 1: Backend + Core Integration
- **Day 1-2**: Set up minimal WebSocket server
- **Day 3-4**: Create CollaborationService class
- **Day 5**: Test WebSocket connection from PyQt6

### Week 2: UI Integration
- **Day 6-7**: Add Share dialog
- **Day 8-9**: Integrate into MainWindow
- **Day 10**: Add serialization to all item types

### Week 3: Testing & Polish
- **Day 11-12**: Multi-user testing
- **Day 13**: Bug fixes
- **Day 14**: Deployment and documentation

---

## Deployment

### Server
```bash
# Minimal server - can run on Railway, Heroku, or even Raspberry Pi!
pip install aiohttp
python server.py

# Or use Docker
docker build -t optiverse-server .
docker run -p 8080:8080 optiverse-server
```

### Desktop App
No changes to distribution! Just:
1. Update existing PyQt6 app with new code
2. Build as usual (PyInstaller)
3. Users download new version

---

## Cost Estimate

### Hosting
- **Railway/Heroku**: $5-10/month
- **Or self-host**: $0 (run on your own server)
- **Or ngrok for testing**: $0 (free tier)

### Development
- **Your time**: 2-3 weeks
- **No other costs**

---

## Testing Plan

### Local Testing (ngrok)
```bash
# Terminal 1: Run server
python server.py

# Terminal 2: Expose to internet
ngrok http 8080

# Now share ngrok URL with collaborator
# They can connect from anywhere!
```

### Multi-Machine Testing
1. Run server on Railway (free tier)
2. Open desktop app on Computer A
3. Click "Share" → Create session
4. Copy link
5. Open desktop app on Computer B
6. Click "Share" → Join → Paste session ID
7. Both users should see each other's changes live!

---

## Message Protocol

### Messages Sent by Clients

```json
// Component added
{
  "type": "component:add",
  "data": {
    "id": "uuid-1234",
    "kind": "lens",
    "x_mm": 100,
    "y_mm": 50,
    "angle_deg": 90,
    "length_mm": 60,
    "efl_mm": 100
  }
}

// Component moved
{
  "type": "component:move",
  "data": {
    "id": "uuid-1234",
    "x_mm": 150,
    "y_mm": 75
  }
}

// Component deleted
{
  "type": "component:delete",
  "data": {
    "id": "uuid-1234"
  }
}

// Component edited
{
  "type": "component:edit",
  "data": {
    "id": "uuid-1234",
    "efl_mm": 150
  }
}
```

### Messages Sent by Server

```json
// User joined
{
  "type": "user:joined",
  "user_id": "Alice"
}

// User left
{
  "type": "user:left",
  "user_id": "Bob"
}

// All client messages are forwarded as-is
```

---

## Security

### Session IDs
- Use `secrets.token_urlsafe()` - cryptographically secure
- 12-16 bytes = hard to guess

### Optional: Add Password Protection
```python
# In server.py
sessions_passwords = {}

async def create_session(request):
    data = await request.json()
    session_id = secrets.token_urlsafe(12)
    password = data.get('password')
    if password:
        sessions_passwords[session_id] = password
    sessions[session_id] = {}
    return web.json_response({'session_id': session_id})

# Verify password when joining
```

---

## Advanced Features (Post-MVP)

### 1. Presence Indicators
Show who's currently in the session in the UI.

### 2. User Cursors
Show where other users' cursors are (send cursor position periodically).

### 3. Conflict Resolution
If two users edit the same component simultaneously, use "last write wins" or prompt to resolve.

### 4. Session History
Save session state periodically for recovery.

### 5. Voice Chat
Integrate WebRTC audio for team communication.

---

## Advantages of This Approach

1. **✅ Keeps full Qt performance** - Raytracing runs locally
2. **✅ Minimal backend** - Server just routes messages (~70 lines!)
3. **✅ Fast to implement** - 2-3 weeks
4. **✅ Low cost** - $5-10/month or self-host
5. **✅ Reuses 95%+ existing code** - Just add WebSocket layer
6. **✅ Works offline** - Can edit locally, sync when connected
7. **✅ No raytracing latency** - Computed locally as before

---

## Limitations vs Full Web

- ❌ Still requires app installation
- ❌ No mobile support
- ❌ Platform-specific builds needed
- ❌ Less "wow" factor than web app

**But**: Much faster to implement and perfect for existing desktop users!

---

## Next Steps

1. **✅ Review this strategy**
2. **⬜ Set up minimal server** (copy server.py above)
3. **⬜ Test server locally** (run and connect with curl/wscat)
4. **⬜ Add CollaborationService** to your PyQt6 app
5. **⬜ Add ShareDialog**
6. **⬜ Integrate into MainWindow**
7. **⬜ Test with second instance of app**
8. **⬜ Deploy server to Railway**
9. **⬜ Distribute updated app to users**

---

## Quick Start Code

Save this as `server.py` and you're ready to go:

```python
#!/usr/bin/env python3
"""Minimal collaboration server for Optiverse."""
import asyncio
import json
import secrets
from aiohttp import web
import aiohttp

sessions = {}

async def create_session(request):
    session_id = secrets.token_urlsafe(12)
    sessions[session_id] = {}
    return web.json_response({'session_id': session_id, 'share_link': f'optiverse://join/{session_id}'})

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    session_id = request.match_info['session_id']
    user_id = request.match_info['user_id']
    
    if session_id not in sessions:
        sessions[session_id] = {}
    sessions[session_id][user_id] = ws
    
    await broadcast(session_id, {'type': 'user:joined', 'user_id': user_id}, exclude=user_id)
    
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await broadcast(session_id, json.loads(msg.data), exclude=user_id)
    finally:
        if session_id in sessions and user_id in sessions[session_id]:
            del sessions[session_id][user_id]
        await broadcast(session_id, {'type': 'user:left', 'user_id': user_id})
    return ws

async def broadcast(session_id, message, exclude=None):
    if session_id not in sessions:
        return
    for user_id, ws in sessions[session_id].items():
        if user_id != exclude:
            try:
                await ws.send_json(message)
            except:
                pass

app = web.Application()
app.router.add_post('/api/sessions', create_session)
app.router.add_get('/ws/{session_id}/{user_id}', websocket_handler)

if __name__ == '__main__':
    print("🚀 Optiverse Collaboration Server running on http://localhost:8080")
    web.run_app(app, port=8080)
```

Run it:
```bash
pip install aiohttp
python server.py
```

**That's it!** Now add the PyQt6 client code and you have live collaboration! 🎉

---

## Summary

**What you get:**
- ✅ Real-time collaboration in existing desktop app
- ✅ Minimal backend (70 lines)
- ✅ 2-3 week timeline
- ✅ $5-10/month hosting (or free self-hosted)
- ✅ Full local performance
- ✅ 95% code reuse

**What you need to do:**
1. Run the minimal server (provided above)
2. Add WebSocket client to PyQt6 app (CollaborationService class)
3. Add Share dialog
4. Add serialize/deserialize to item classes
5. Hook up signals in MainWindow

**Ready to start?** The server code is ready to copy-paste! 🚀

