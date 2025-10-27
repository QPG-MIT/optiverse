# Collaborative Optiverse - Code Examples

This document provides concrete code examples for the collaborative implementation.

---

## Backend Implementation Examples

### 1. FastAPI Main Application

```python
# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import redis
from typing import Dict, Set
import asyncio

app = FastAPI(title="Optiverse Collaboration API")

# CORS for web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://optiverse.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client for session storage
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Active WebSocket connections per session
# Format: {session_id: {user_id: WebSocket}}
active_connections: Dict[str, Dict[str, WebSocket]] = {}

@app.get("/")
async def root():
    return {"message": "Optiverse Collaboration API", "version": "1.0.0"}


@app.post("/api/sessions")
async def create_session():
    """Create a new collaborative session."""
    import secrets
    
    session_id = secrets.token_urlsafe(16)
    
    # Initialize empty session state
    initial_state = {
        "components": [],
        "sources": [],
        "metadata": {
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
    }
    
    # Store in Redis with 24h expiry
    redis_client.setex(
        f"session:{session_id}",
        86400,  # 24 hours
        json.dumps(initial_state)
    )
    
    return {
        "session_id": session_id,
        "share_link": f"https://optiverse.app/session/{session_id}",
        "state": initial_state
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get current session state."""
    state = redis_client.get(f"session:{session_id}")
    
    if not state:
        return {"error": "Session not found"}, 404
    
    return json.loads(state)


@app.websocket("/ws/{session_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: str):
    """WebSocket endpoint for real-time collaboration."""
    await websocket.accept()
    
    # Add connection to active connections
    if session_id not in active_connections:
        active_connections[session_id] = {}
    active_connections[session_id][user_id] = websocket
    
    # Notify others that user joined
    await broadcast_to_session(
        session_id,
        {
            "type": "user:joined",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        },
        exclude_user=user_id
    )
    
    try:
        # Send current state to new user
        current_state = redis_client.get(f"session:{session_id}")
        if current_state:
            await websocket.send_json({
                "type": "state:initial",
                "data": json.loads(current_state)
            })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            # Process the message
            await handle_message(session_id, user_id, data)
            
    except WebSocketDisconnect:
        # Remove connection
        if session_id in active_connections and user_id in active_connections[session_id]:
            del active_connections[session_id][user_id]
        
        # Notify others
        await broadcast_to_session(
            session_id,
            {
                "type": "user:left",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


async def handle_message(session_id: str, user_id: str, message: dict):
    """Handle incoming WebSocket message and update state."""
    msg_type = message.get("type")
    
    # Get current state
    current_state_str = redis_client.get(f"session:{session_id}")
    if not current_state_str:
        return
    
    current_state = json.loads(current_state_str)
    
    # Handle different message types
    if msg_type == "component:add":
        current_state["components"].append(message["data"])
    
    elif msg_type == "component:move":
        comp_id = message["data"]["id"]
        for comp in current_state["components"]:
            if comp["id"] == comp_id:
                comp["x_mm"] = message["data"]["x_mm"]
                comp["y_mm"] = message["data"]["y_mm"]
                break
    
    elif msg_type == "component:rotate":
        comp_id = message["data"]["id"]
        for comp in current_state["components"]:
            if comp["id"] == comp_id:
                comp["angle_deg"] = message["data"]["angle_deg"]
                break
    
    elif msg_type == "component:delete":
        comp_id = message["data"]["id"]
        current_state["components"] = [
            c for c in current_state["components"] if c["id"] != comp_id
        ]
    
    elif msg_type == "cursor:move":
        # Just broadcast cursor position, don't save to state
        await broadcast_to_session(
            session_id,
            {
                "type": "cursor:move",
                "user_id": user_id,
                "data": message["data"]
            },
            exclude_user=user_id
        )
        return
    
    # Update timestamp
    current_state["metadata"]["last_updated"] = datetime.utcnow().isoformat()
    
    # Save updated state
    redis_client.setex(
        f"session:{session_id}",
        86400,
        json.dumps(current_state)
    )
    
    # Broadcast to all other users
    await broadcast_to_session(
        session_id,
        {
            "type": "state:update",
            "user_id": user_id,
            "data": message["data"],
            "operation": msg_type
        },
        exclude_user=user_id
    )


async def broadcast_to_session(session_id: str, message: dict, exclude_user: str = None):
    """Broadcast message to all users in a session."""
    if session_id not in active_connections:
        return
    
    for user_id, ws in active_connections[session_id].items():
        if user_id != exclude_user:
            try:
                await ws.send_json(message)
            except Exception:
                # Connection closed, will be cleaned up later
                pass


from datetime import datetime
```

---

### 2. Raytracing Endpoint

```python
# app/api/raytrace.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Tuple
import numpy as np

# Import existing raytracing logic
from ..core.use_cases import trace_rays
from ..core.models import OpticalElement, SourceParams

router = APIRouter()

class RaytraceRequest(BaseModel):
    sources: List[dict]
    components: List[dict]

class RaytraceResponse(BaseModel):
    rays: List[dict]  # Each ray is a list of points with color

@router.post("/api/raytrace", response_model=RaytraceResponse)
async def calculate_raytrace(request: RaytraceRequest):
    """Calculate ray paths through optical system."""
    try:
        # Convert request to internal format
        sources = [_parse_source(s) for s in request.sources]
        elements = [_parse_element(c) for c in request.components]
        
        # Run raytracing (reuse existing logic!)
        ray_paths = trace_rays(sources, elements)
        
        # Convert to response format
        rays_data = []
        for ray_path in ray_paths:
            rays_data.append({
                "points": [{"x": p[0], "y": p[1]} for p in ray_path.points],
                "color": {
                    "r": ray_path.rgba[0],
                    "g": ray_path.rgba[1],
                    "b": ray_path.rgba[2],
                    "a": ray_path.rgba[3]
                }
            })
        
        return {"rays": rays_data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Raytracing failed: {str(e)}")


def _parse_source(data: dict) -> SourceParams:
    """Convert API format to SourceParams."""
    return SourceParams(
        x_mm=data.get("x_mm", 0),
        y_mm=data.get("y_mm", 0),
        angle_deg=data.get("angle_deg", 0),
        n_rays=data.get("n_rays", 9),
        spread_deg=data.get("spread_deg", 0),
        color_hex=data.get("color_hex", "#DC143C")
    )


def _parse_element(data: dict) -> OpticalElement:
    """Convert API format to OpticalElement."""
    kind = data["kind"]
    angle_rad = np.deg2rad(data["angle_deg"])
    length_mm = data["length_mm"]
    
    # Calculate p1 and p2 from center position and angle
    x, y = data["x_mm"], data["y_mm"]
    dx = (length_mm / 2) * np.cos(angle_rad)
    dy = (length_mm / 2) * np.sin(angle_rad)
    
    p1 = np.array([x - dx, y - dy])
    p2 = np.array([x + dx, y + dy])
    
    return OpticalElement(
        kind=kind,
        p1=p1,
        p2=p2,
        efl_mm=data.get("efl_mm", 0),
        split_T=data.get("split_T", 50),
        split_R=data.get("split_R", 50)
    )
```

---

## Frontend Implementation Examples

### 3. WebSocket Hook

```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useRef, useState } from 'react';

interface WebSocketMessage {
  type: string;
  user_id?: string;
  data?: any;
  operation?: string;
}

export function useWebSocket(sessionId: string, userId: string) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket(
      `ws://localhost:8000/ws/${sessionId}/${userId}`
    );

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages((prev) => [...prev, message]);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [sessionId, userId]);

  const sendMessage = (message: WebSocketMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  };

  return { connected, messages, sendMessage };
}
```

---

### 4. Main Canvas Component

```typescript
// src/components/Canvas.tsx
import React, { useEffect, useRef, useState } from 'react';
import { Stage, Layer, Rect, Line, Circle } from 'react-konva';
import { useWebSocket } from '../hooks/useWebSocket';
import { ComponentRenderer } from './ComponentRenderer';
import { RayRenderer } from './RayRenderer';

interface Component {
  id: string;
  kind: 'lens' | 'mirror' | 'beamsplitter';
  x_mm: number;
  y_mm: number;
  angle_deg: number;
  length_mm: number;
  efl_mm?: number;
  split_T?: number;
  split_R?: number;
}

interface CanvasProps {
  sessionId: string;
  userId: string;
}

export function Canvas({ sessionId, userId }: CanvasProps) {
  const [components, setComponents] = useState<Component[]>([]);
  const [rays, setRays] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  
  const { connected, messages, sendMessage } = useWebSocket(sessionId, userId);

  // Handle incoming WebSocket messages
  useEffect(() => {
    messages.forEach((msg) => {
      if (msg.type === 'state:initial') {
        setComponents(msg.data.components);
      } else if (msg.type === 'state:update') {
        handleRemoteUpdate(msg);
      }
    });
  }, [messages]);

  const handleRemoteUpdate = (msg: any) => {
    if (msg.operation === 'component:add') {
      setComponents((prev) => [...prev, msg.data]);
    } else if (msg.operation === 'component:move') {
      setComponents((prev) =>
        prev.map((c) =>
          c.id === msg.data.id
            ? { ...c, x_mm: msg.data.x_mm, y_mm: msg.data.y_mm }
            : c
        )
      );
    } else if (msg.operation === 'component:delete') {
      setComponents((prev) => prev.filter((c) => c.id !== msg.data.id));
    }
  };

  const handleDragEnd = (id: string, x: number, y: number) => {
    // Update local state optimistically
    setComponents((prev) =>
      prev.map((c) => (c.id === id ? { ...c, x_mm: x, y_mm: y } : c))
    );

    // Send to server
    sendMessage({
      type: 'component:move',
      data: { id, x_mm: x, y_mm: y },
    });

    // Trigger raytracing
    recalculateRays();
  };

  const recalculateRays = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/raytrace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sources: [], // Get from state
          components: components,
        }),
      });
      const data = await response.json();
      setRays(data.rays);
    } catch (error) {
      console.error('Raytracing failed:', error);
    }
  };

  const mmToPixel = (mm: number) => mm * 1; // 1 pixel = 1 mm for now
  const pixelToMm = (px: number) => px / 1;

  return (
    <div className="canvas-container">
      <Stage width={1200} height={700}>
        {/* Grid Layer */}
        <Layer>
          <Rect x={0} y={0} width={1200} height={700} fill="#f5f5f5" />
          {/* Draw grid lines here */}
        </Layer>

        {/* Components Layer */}
        <Layer>
          {components.map((component) => (
            <ComponentRenderer
              key={component.id}
              component={component}
              selected={selectedId === component.id}
              onSelect={() => setSelectedId(component.id)}
              onDragEnd={(x, y) => handleDragEnd(component.id, x, y)}
              mmToPixel={mmToPixel}
            />
          ))}
        </Layer>

        {/* Rays Layer */}
        <Layer>
          {rays.map((ray, idx) => (
            <RayRenderer key={idx} ray={ray} mmToPixel={mmToPixel} />
          ))}
        </Layer>
      </Stage>

      <div className="status-bar">
        {connected ? '🟢 Connected' : '🔴 Disconnected'} | Session: {sessionId}
      </div>
    </div>
  );
}
```

---

### 5. Component Renderer

```typescript
// src/components/ComponentRenderer.tsx
import React from 'react';
import { Group, Rect, Line, Circle } from 'react-konva';

interface ComponentRendererProps {
  component: any;
  selected: boolean;
  onSelect: () => void;
  onDragEnd: (x: number, y: number) => void;
  mmToPixel: (mm: number) => number;
}

export function ComponentRenderer({
  component,
  selected,
  onSelect,
  onDragEnd,
  mmToPixel,
}: ComponentRendererProps) {
  const x = mmToPixel(component.x_mm);
  const y = mmToPixel(component.y_mm);
  const length = mmToPixel(component.length_mm);

  const handleDragEnd = (e: any) => {
    const node = e.target;
    const x_px = node.x();
    const y_px = node.y();
    onDragEnd(x_px, y_px); // Convert back to mm in parent
  };

  // Render different shapes based on component type
  if (component.kind === 'lens') {
    return (
      <Group
        x={x}
        y={y}
        rotation={component.angle_deg}
        draggable
        onDragEnd={handleDragEnd}
        onClick={onSelect}
      >
        {/* Lens representation */}
        <Line
          points={[-length / 2, 0, length / 2, 0]}
          stroke="blue"
          strokeWidth={selected ? 4 : 2}
        />
        <Circle x={-length / 2} y={0} radius={5} fill="blue" />
        <Circle x={length / 2} y={0} radius={5} fill="blue" />
        {selected && (
          <Rect
            x={-length / 2 - 5}
            y={-5}
            width={length + 10}
            height={10}
            stroke="cyan"
            strokeWidth={1}
            dash={[5, 5]}
          />
        )}
      </Group>
    );
  }

  if (component.kind === 'mirror') {
    return (
      <Group
        x={x}
        y={y}
        rotation={component.angle_deg}
        draggable
        onDragEnd={handleDragEnd}
        onClick={onSelect}
      >
        {/* Mirror representation */}
        <Line
          points={[-length / 2, 0, length / 2, 0]}
          stroke="silver"
          strokeWidth={selected ? 5 : 3}
        />
      </Group>
    );
  }

  if (component.kind === 'beamsplitter') {
    return (
      <Group
        x={x}
        y={y}
        rotation={component.angle_deg}
        draggable
        onDragEnd={handleDragEnd}
        onClick={onSelect}
      >
        {/* Beamsplitter representation */}
        <Line
          points={[-length / 2, 0, length / 2, 0]}
          stroke="purple"
          strokeWidth={selected ? 4 : 2}
          dash={[5, 5]}
        />
      </Group>
    );
  }

  return null;
}
```

---

### 6. Share Dialog Component

```typescript
// src/components/ShareDialog.tsx
import React, { useState } from 'react';

interface ShareDialogProps {
  sessionId: string;
  onClose: () => void;
}

export function ShareDialog({ sessionId, onClose }: ShareDialogProps) {
  const [copied, setCopied] = useState(false);
  
  const shareLink = `${window.location.origin}/session/${sessionId}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(shareLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="dialog-overlay">
      <div className="dialog">
        <h2>Share This Design</h2>
        <p>Anyone with this link can view and edit this optical design.</p>
        
        <div className="share-link-container">
          <input
            type="text"
            value={shareLink}
            readOnly
            className="share-link-input"
          />
          <button onClick={handleCopy} className="copy-button">
            {copied ? '✓ Copied!' : 'Copy Link'}
          </button>
        </div>

        <div className="permissions">
          <h3>Permissions</h3>
          <label>
            <input type="checkbox" defaultChecked />
            Anyone with the link can edit
          </label>
          <label>
            <input type="checkbox" />
            Require password
          </label>
        </div>

        <div className="dialog-actions">
          <button onClick={onClose} className="close-button">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

### 7. User Presence Component

```typescript
// src/components/UserPresence.tsx
import React from 'react';

interface User {
  id: string;
  name: string;
  color: string;
  cursor?: { x: number; y: number };
}

interface UserPresenceProps {
  users: User[];
}

export function UserPresence({ users }: UserPresenceProps) {
  return (
    <div className="user-presence">
      <h4>Active Users ({users.length})</h4>
      <div className="user-list">
        {users.map((user) => (
          <div key={user.id} className="user-item">
            <div
              className="user-avatar"
              style={{ backgroundColor: user.color }}
            >
              {user.name.charAt(0).toUpperCase()}
            </div>
            <span className="user-name">{user.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### 8. Live Cursors Component

```typescript
// src/components/LiveCursors.tsx
import React from 'react';
import { Circle, Text, Group } from 'react-konva';

interface Cursor {
  userId: string;
  userName: string;
  color: string;
  x: number;
  y: number;
}

interface LiveCursorsProps {
  cursors: Cursor[];
}

export function LiveCursors({ cursors }: LiveCursorsProps) {
  return (
    <>
      {cursors.map((cursor) => (
        <Group key={cursor.userId} x={cursor.x} y={cursor.y}>
          {/* Cursor pointer */}
          <Circle radius={8} fill={cursor.color} opacity={0.8} />
          
          {/* User name label */}
          <Group x={10} y={-5}>
            <Rect
              width={cursor.userName.length * 8 + 10}
              height={20}
              fill={cursor.color}
              cornerRadius={3}
            />
            <Text
              text={cursor.userName}
              fontSize={12}
              fill="white"
              padding={5}
            />
          </Group>
        </Group>
      ))}
    </>
  );
}
```

---

## Testing Examples

### 9. Backend Test

```python
# tests/test_websocket.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_session():
    """Test session creation."""
    response = client.post("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "share_link" in data
    assert len(data["session_id"]) > 10  # Should be long random string


def test_get_session():
    """Test retrieving session state."""
    # Create session
    create_resp = client.post("/api/sessions")
    session_id = create_resp.json()["session_id"]
    
    # Get session
    get_resp = client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "components" in data
    assert "sources" in data


def test_websocket_connection():
    """Test WebSocket connection."""
    # Create session
    create_resp = client.post("/api/sessions")
    session_id = create_resp.json()["session_id"]
    
    # Connect via WebSocket
    with client.websocket_connect(f"/ws/{session_id}/user123") as websocket:
        # Should receive initial state
        data = websocket.receive_json()
        assert data["type"] == "state:initial"
        
        # Send a component add message
        websocket.send_json({
            "type": "component:add",
            "data": {
                "id": "lens1",
                "kind": "lens",
                "x_mm": 100,
                "y_mm": 50,
                "angle_deg": 90,
                "length_mm": 60,
                "efl_mm": 100
            }
        })
        
        # Should be processed (no error)
```

---

### 10. Frontend Test

```typescript
// src/__tests__/Canvas.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { Canvas } from '../components/Canvas';

// Mock WebSocket
class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  
  constructor(url: string) {
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 100);
  }
  
  send(data: string) {
    // Mock send
  }
  
  close() {}
}

global.WebSocket = MockWebSocket as any;

test('renders canvas and connects to WebSocket', async () => {
  render(<Canvas sessionId="test123" userId="user1" />);
  
  await waitFor(() => {
    expect(screen.getByText(/Connected/)).toBeInTheDocument();
  });
});

test('renders components from initial state', async () => {
  const { container } = render(<Canvas sessionId="test123" userId="user1" />);
  
  // Mock receiving initial state
  // ... test implementation
});
```

---

## Performance Optimization Examples

### 11. Debounced Raytracing

```typescript
// src/hooks/useRaytracing.ts
import { useCallback, useRef } from 'react';
import debounce from 'lodash/debounce';

export function useRaytracing() {
  const [rays, setRays] = useState([]);
  const [loading, setLoading] = useState(false);

  const calculateRays = async (components: any[], sources: any[]) => {
    setLoading(true);
    try {
      const response = await fetch('/api/raytrace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ components, sources }),
      });
      const data = await response.json();
      setRays(data.rays);
    } finally {
      setLoading(false);
    }
  };

  // Debounce raytracing to avoid hammering the server
  const debouncedCalculate = useCallback(
    debounce(calculateRays, 300),
    []
  );

  return { rays, loading, calculateRays: debouncedCalculate };
}
```

---

### 12. Optimistic Updates

```typescript
// src/store/documentStore.ts
import create from 'zustand';

interface Component {
  id: string;
  // ... other fields
}

interface DocumentStore {
  components: Component[];
  pendingChanges: Map<string, Component>;
  
  addComponent: (component: Component) => void;
  moveComponent: (id: string, x: number, y: number) => void;
  confirmChange: (id: string) => void;
  revertChange: (id: string) => void;
}

export const useDocumentStore = create<DocumentStore>((set, get) => ({
  components: [],
  pendingChanges: new Map(),
  
  addComponent: (component) => {
    // Optimistically add to state
    set((state) => ({
      components: [...state.components, component],
      pendingChanges: new Map(state.pendingChanges).set(component.id, component),
    }));
  },
  
  moveComponent: (id, x, y) => {
    set((state) => ({
      components: state.components.map((c) =>
        c.id === id ? { ...c, x_mm: x, y_mm: y } : c
      ),
      pendingChanges: new Map(state.pendingChanges).set(id, { x, y }),
    }));
  },
  
  confirmChange: (id) => {
    set((state) => {
      const newPending = new Map(state.pendingChanges);
      newPending.delete(id);
      return { pendingChanges: newPending };
    });
  },
  
  revertChange: (id) => {
    // Server rejected change, revert to previous state
    // Implementation depends on how you track history
  },
}));
```

---

## Summary

These code examples demonstrate:

1. **Backend**: FastAPI with WebSocket for real-time collaboration
2. **Frontend**: React with Konva.js for interactive canvas
3. **Real-time Sync**: WebSocket messages for state updates
4. **Raytracing**: Server-side computation, reusing existing Python code
5. **UI Components**: Share dialog, user presence, live cursors
6. **Testing**: Both backend and frontend test examples
7. **Performance**: Debouncing, optimistic updates

All of this reuses your existing raytracing logic from `core/use_cases.py` while adding the collaboration layer on top!

