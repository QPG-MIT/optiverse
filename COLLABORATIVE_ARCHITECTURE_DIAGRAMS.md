# Collaborative Optiverse - Architecture Diagrams

Visual representations of the system architecture and data flows.

---

## System Architecture

### Full Stack Overview

```
┌───────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │  Browser 1 │  │  Browser 2 │  │  Browser N │             │
│  │  (User A)  │  │  (User B)  │  │  (User C)  │             │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘             │
│        │ React+Konva   │                │                     │
└────────┼───────────────┼────────────────┼─────────────────────┘
         │               │                │
         │  HTTPS/WSS    │                │
         │               │                │
┌────────▼───────────────▼────────────────▼─────────────────────┐
│                     LOAD BALANCER                             │
│                   (Cloudflare / Nginx)                        │
└────────┬──────────────────────────────────┬───────────────────┘
         │                                  │
         │                                  │
┌────────▼──────────────────┐    ┌─────────▼──────────────────┐
│   FRONTEND HOSTING        │    │   BACKEND API SERVER       │
│      (Vercel)             │    │      (Railway)             │
│                           │    │                            │
│  • Static React files     │    │  • FastAPI                 │
│  • CDN distribution       │    │  • WebSocket handler       │
│  • Auto SSL               │    │  • Session manager         │
│  • Edge caching           │    │  • Raytracing API          │
└───────────────────────────┘    └─────────┬──────────────────┘
                                           │
                      ┌────────────────────┼────────────────────┐
                      │                    │                    │
         ┌────────────▼──────────┐  ┌──────▼─────────┐  ┌──────▼─────────┐
         │   Redis Cache         │  │  PostgreSQL    │  │  File Storage  │
         │                       │  │                │  │   (S3/CDN)     │
         │ • Active sessions     │  │ • User data    │  │ • Component    │
         │ • User presence       │  │ • Saved        │  │   images       │
         │ • Pub/Sub for WS      │  │   designs      │  │ • Exports      │
         └───────────────────────┘  └────────────────┘  └────────────────┘
```

---

## Data Flow: Component Movement

### Detailed Sequence Diagram

```
 User A          Browser A        Backend         Redis        Browser B        User B
   │                │                │              │              │              │
   │  Drag lens     │                │              │              │              │
   ├───────────────>│                │              │              │              │
   │                │                │              │              │              │
   │                │  1. Update     │              │              │              │
   │                │     local DOM  │              │              │              │
   │                │     (optimistic)              │              │              │
   │                │                │              │              │              │
   │                │  2. Send WS    │              │              │              │
   │                │    message     │              │              │              │
   │                ├───────────────>│              │              │              │
   │                │                │              │              │              │
   │                │                │  3. Validate │              │              │
   │                │                │     message  │              │              │
   │                │                │              │              │              │
   │                │                │  4. Update   │              │              │
   │                │                │     session  │              │              │
   │                │                ├─────────────>│              │              │
   │                │                │              │              │              │
   │                │                │  5. Publish  │              │              │
   │                │                │     to room  │              │              │
   │                │                │<─────────────┤              │              │
   │                │                │              │              │              │
   │                │                │  6. Broadcast│              │              │
   │                │                │     to other │              │              │
   │                │                │     clients  │              │              │
   │                │                ├──────────────┼─────────────>│              │
   │                │                │              │              │              │
   │                │                │              │              │  7. Update   │
   │                │                │              │              │     DOM      │
   │                │                │              │              │<─────────────┤
   │                │                │              │              │              │
   │                │  8. Trigger    │              │              │  9. Trigger  │
   │                │     raytrace   │              │              │     raytrace │
   │                ├───────────────>│              │              ├─────────────>│
   │                │                │              │              │              │
   │                │  10. Return    │              │              │  11. Return  │
   │                │      rays      │              │              │      rays    │
   │                │<───────────────┤              │              │<─────────────┤
   │                │                │              │              │              │
   │  See updated   │                │              │              │              │  See updated
   │  lens + rays   │                │              │              │              │  lens + rays
   │<───────────────┤                │              │              ├─────────────>│

   Total latency: ~50-100ms
```

---

## WebSocket Connection Lifecycle

```
┌─────────────┐
│   Browser   │
│   Opens     │
└──────┬──────┘
       │
       │  1. Connect to WSS endpoint
       │     ws://api.optiverse.app/ws/{session_id}/{user_id}
       │
       ▼
┌──────────────────────────────────────┐
│     WebSocket Server (FastAPI)       │
│                                      │
│  on_connect():                       │
│    • Validate session exists         │
│    • Add to active_connections       │
│    • Send initial state              │
│    • Broadcast "user:joined"         │
└──────────────┬───────────────────────┘
               │
               │  2. Connection established
               │
               ▼
┌──────────────────────────────────────┐
│         Active Session               │
│  ┌────────────────────────────────┐  │
│  │  Room: session_abc123          │  │
│  │  ├─ User A: WebSocket 1        │  │
│  │  ├─ User B: WebSocket 2        │  │
│  │  └─ User C: WebSocket 3        │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
               │  3. Message loop
               │
    ┌──────────▼──────────┐
    │  Receive message    │
    │  from any user      │
    └──────────┬──────────┘
               │
               ▼
    ┌────────────────────────────┐
    │  Message Handler           │
    │  • component:add           │
    │  • component:move          │
    │  • component:rotate        │
    │  • component:delete        │
    │  • cursor:move             │
    └──────────┬─────────────────┘
               │
               ▼
    ┌────────────────────────────┐
    │  Update State in Redis     │
    └──────────┬─────────────────┘
               │
               ▼
    ┌────────────────────────────┐
    │  Broadcast to all users    │
    │  in room (except sender)   │
    └────────────────────────────┘

               │  4. User disconnects
               │
               ▼
┌──────────────────────────────────────┐
│  on_disconnect():                    │
│    • Remove from active_connections  │
│    • Broadcast "user:left"           │
│    • Clean up if last user           │
└──────────────────────────────────────┘
```

---

## Frontend Component Hierarchy

```
<App>
  │
  ├─ <Router>
  │   │
  │   ├─ / (Home)
  │   │   └─ <HomePage>
  │   │       ├─ <CreateSessionButton>
  │   │       └─ <RecentDesigns>
  │   │
  │   └─ /session/:id (Canvas)
  │       └─ <SessionPage>
  │           │
  │           ├─ <Toolbar>
  │           │   ├─ <ShareButton> ───> <ShareDialog>
  │           │   ├─ <ZoomControls>
  │           │   └─ <ToolButtons>
  │           │
  │           ├─ <Sidebar>
  │           │   ├─ <ComponentLibrary>
  │           │   │   ├─ <LensCard>
  │           │   │   ├─ <MirrorCard>
  │           │   │   ├─ <BeamsplitterCard>
  │           │   │   └─ <SourceCard>
  │           │   │
  │           │   └─ <UserPresence>
  │           │       ├─ <UserAvatar> (User A)
  │           │       ├─ <UserAvatar> (User B)
  │           │       └─ <UserAvatar> (User C)
  │           │
  │           └─ <Canvas> ◄─────── Main component
  │               │
  │               ├─ <Stage> (Konva)
  │               │   │
  │               │   ├─ <Layer name="grid">
  │               │   │   └─ <GridLines>
  │               │   │
  │               │   ├─ <Layer name="components">
  │               │   │   ├─ <LensRenderer>
  │               │   │   ├─ <MirrorRenderer>
  │               │   │   ├─ <BeamsplitterRenderer>
  │               │   │   └─ <SourceRenderer>
  │               │   │
  │               │   ├─ <Layer name="rays">
  │               │   │   └─ <RayPathRenderer>
  │               │   │
  │               │   └─ <Layer name="cursors">
  │               │       └─ <LiveCursors>
  │               │           ├─ <Cursor> (User A)
  │               │           └─ <Cursor> (User B)
  │               │
  │               └─ <ComponentEditor> (dialog)
  │                   ├─ <PropertyFields>
  │                   └─ <SaveButton>
  │
  └─ <WebSocketProvider> ◄─────── Context
      └─ useWebSocket() hook
```

---

## State Management Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      APPLICATION STATE                       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌──────────────┐
│  Local State  │    │  Server State  │    │  UI State    │
│  (Zustand)    │    │  (Redis)       │    │  (React)     │
└───────────────┘    └────────────────┘    └──────────────┘
        │                     │                     │
        │                     │                     │
┌───────▼────────┐   ┌────────▼────────┐   ┌───────▼──────┐
│ • components[] │   │ • session data  │   │ • selected   │
│ • sources[]    │   │ • user list     │   │ • zoom level │
│ • rays[]       │   │ • timestamp     │   │ • pan offset │
│ • users[]      │   │                 │   │ • tool mode  │
└────────────────┘   └─────────────────┘   └──────────────┘

User Action (e.g., drag lens)
        │
        ▼
┌─────────────────────────────────────┐
│  1. Optimistic Update (Local)       │
│     components[0].x = newX          │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  2. Send to Server (WebSocket)      │
│     ws.send({ type: "move", ... })  │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  3. Server Updates Redis            │
│     session:abc123 → new state      │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  4. Broadcast to Other Clients      │
│     ws.broadcast(update)            │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  5. Other Clients Update Local      │
│     store.updateComponent(data)     │
└─────────────────────────────────────┘
```

---

## Redis Data Structure

```
Redis Key-Value Store
│
├─ session:{session_id}
│   └─ Value (JSON string):
│       {
│         "components": [
│           {
│             "id": "lens_abc123",
│             "kind": "lens",
│             "x_mm": 150,
│             "y_mm": 75,
│             "angle_deg": 90,
│             "length_mm": 60,
│             "efl_mm": 100
│           },
│           ...
│         ],
│         "sources": [ ... ],
│         "metadata": {
│           "created_at": "2025-01-15T10:30:00Z",
│           "last_updated": "2025-01-15T11:45:23Z"
│         }
│       }
│   └─ TTL: 86400 seconds (24 hours)
│
├─ session:{session_id}:users
│   └─ Set: ["user_a", "user_b", "user_c"]
│   └─ TTL: 86400 seconds
│
├─ user:{user_id}:cursor
│   └─ Hash:
│       {
│         "session_id": "abc123",
│         "x": 250,
│         "y": 130,
│         "timestamp": 1705318523
│       }
│   └─ TTL: 60 seconds (expires if inactive)
│
└─ pubsub:session:{session_id}
    └─ Channel for broadcasting updates
        (no persistent storage, just messaging)
```

---

## Component Rendering Pipeline

```
Component Data
    │
    ▼
┌─────────────────────────────────┐
│  ComponentRenderer              │
│  (React Component)              │
└──────────┬──────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│  Props Extraction                                    │
│  • id, kind, x_mm, y_mm, angle_deg, length_mm, etc. │
└──────────┬───────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Coordinate Transformation      │
│  mmToPixel(): mm → canvas px    │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Konva Group                    │
│  <Group x={x} y={y}             │
│         rotation={angle}        │
│         draggable>              │
└──────────┬──────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌───────┐    ┌────────┐
│ Shape │    │ Image  │
│ (SVG) │    │ (PNG)  │
└───────┘    └────────┘
    │             │
    └──────┬──────┘
           │
           ▼
┌─────────────────────────────────┐
│  Event Handlers                 │
│  • onDragMove                   │
│  • onDragEnd                    │
│  • onClick                      │
│  • onTransform                  │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Update Callback                │
│  → Update store                 │
│  → Send WebSocket message       │
└─────────────────────────────────┘
```

---

## Raytracing Computation Flow

```
User Action (move component)
    │
    ▼
┌─────────────────────────────────┐
│  Debounce (300ms)               │
│  (avoid hammering server)       │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Gather Current State           │
│  • All components[]             │
│  • All sources[]                │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  POST /api/raytrace             │
│  {                              │
│    sources: [...],              │
│    components: [...]            │
│  }                              │
└──────────┬──────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Backend: Parse Request                  │
│  • Convert to SourceParams               │
│  • Convert to OpticalElement[]           │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Backend: Call trace_rays()              │
│  (Reuse existing core/use_cases.py!)    │
│  • Generate rays from each source        │
│  • Intersect with each optical element   │
│  • Apply lens/mirror/beamsplitter rules  │
│  • Track ray paths and colors            │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Backend: Format Response                │
│  {                                       │
│    rays: [                               │
│      {                                   │
│        points: [{x, y}, ...],            │
│        color: {r, g, b, a}               │
│      }                                   │
│    ]                                     │
│  }                                       │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Frontend: Receive & Store              │
│  setRays(data.rays)                      │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Frontend: Render Rays                   │
│  <Layer name="rays">                     │
│    {rays.map(ray =>                      │
│      <Line points={ray.points}           │
│            stroke={ray.color} />         │
│    )}                                    │
│  </Layer>                                │
└──────────────────────────────────────────┘

Total time: ~200-500ms
```

---

## Deployment Architecture

### Development Environment
```
┌─────────────────────────────────────────────────────────┐
│                    Developer Machine                    │
│                                                         │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────┐ │
│  │  Frontend   │     │   Backend    │     │  Redis  │ │
│  │  localhost  │────>│  localhost   │────>│  local  │ │
│  │  :3000      │     │  :8000       │     │  :6379  │ │
│  └─────────────┘     └──────────────┘     └─────────┘ │
│         │                                              │
│         └──> Browser DevTools                         │
└─────────────────────────────────────────────────────────┘
```

### Production Environment
```
┌──────────────────────────────────────────────────────────┐
│                    User's Browser                        │
└────────────────┬─────────────────────────────────────────┘
                 │  HTTPS/WSS
                 │
┌────────────────▼─────────────────────────────────────────┐
│              Cloudflare CDN                              │
│  • DDoS protection                                       │
│  • SSL termination                                       │
│  • Edge caching                                          │
└────────────┬──────────────────────┬──────────────────────┘
             │                      │
             │ Static files         │ API/WebSocket
             │                      │
┌────────────▼──────────┐   ┌───────▼────────────────────┐
│   Vercel (Frontend)   │   │  Railway (Backend)         │
│                       │   │                            │
│  • Next.js/React      │   │  ┌──────────────────────┐ │
│  • Global CDN         │   │  │  FastAPI Server      │ │
│  • Auto-scaling       │   │  │  • WebSocket         │ │
│  • CI/CD from GitHub  │   │  │  • Session manager   │ │
│                       │   │  │  • Raytracing API    │ │
│                       │   │  └──────┬───────────────┘ │
│                       │   │         │                 │
│                       │   │  ┌──────▼───────────────┐ │
│                       │   │  │  Redis (Railway)     │ │
│                       │   │  │  • In-memory cache   │ │
│                       │   │  └──────────────────────┘ │
│                       │   │         │                 │
│                       │   │  ┌──────▼───────────────┐ │
│                       │   │  │  PostgreSQL          │ │
│                       │   │  │  • Persistent data   │ │
│                       │   │  └──────────────────────┘ │
└───────────────────────┘   └────────────────────────────┘
```

---

## Security Layers

```
┌───────────────────────────────────────────────────────────┐
│  Layer 1: Network Security                                │
│  • HTTPS/TLS encryption                                   │
│  • WSS (WebSocket Secure)                                 │
│  • DDoS protection (Cloudflare)                           │
└────────────────┬──────────────────────────────────────────┘
                 │
┌────────────────▼──────────────────────────────────────────┐
│  Layer 2: Application Security                            │
│  • CORS whitelisting                                      │
│  • Rate limiting (10 req/sec per IP)                      │
│  • Input validation (Pydantic)                            │
│  • XSS protection (React escaping + CSP headers)          │
└────────────────┬──────────────────────────────────────────┘
                 │
┌────────────────▼──────────────────────────────────────────┐
│  Layer 3: Session Security                                │
│  • Cryptographically random session IDs (32 bytes)        │
│  • Session expiry (24 hours)                              │
│  • Optional password protection                           │
└────────────────┬──────────────────────────────────────────┘
                 │
┌────────────────▼──────────────────────────────────────────┐
│  Layer 4: Data Security                                   │
│  • Sanitize user input                                    │
│  • Validate component properties                          │
│  • No code execution from user data                       │
└───────────────────────────────────────────────────────────┘
```

---

## Scaling Strategy

### Phase 1: Single Server (0-1000 users)
```
┌──────────────────────────────┐
│     Single Railway Instance  │
│  • FastAPI app               │
│  • Redis (co-located)        │
│  • PostgreSQL (co-located)   │
└──────────────────────────────┘

Cost: $5-20/month
Handles: ~100 concurrent users
```

### Phase 2: Separated Services (1000-10,000 users)
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  FastAPI     │───>│  Redis       │    │  PostgreSQL  │
│  Instances   │    │  (dedicated) │    │  (dedicated) │
│  (3 servers) │    └──────────────┘    └──────────────┘
└──────────────┘
       │
       ▼
┌──────────────┐
│ Load Balancer│
└──────────────┘

Cost: $50-100/month
Handles: ~1000 concurrent users
```

### Phase 3: Horizontal Scaling (10,000+ users)
```
┌────────────────────────────────────────────────────┐
│             Load Balancer (Nginx/Cloudflare)       │
└──────┬──────────┬──────────┬──────────┬───────────┘
       │          │          │          │
┌──────▼────┐ ┌──▼──────┐ ┌─▼───────┐ ┌▼──────────┐
│ FastAPI 1 │ │FastAPI 2│ │FastAPI 3│ │ FastAPI N │
└──────┬────┘ └──┬──────┘ └─┬───────┘ └┬──────────┘
       │         │           │          │
       └─────────┴───────────┴──────────┘
                 │
         ┌───────▼────────┐
         │ Redis Cluster  │
         │ (Pub/Sub)      │
         └───────┬────────┘
                 │
         ┌───────▼────────┐
         │ PostgreSQL     │
         │ (Read replicas)│
         └────────────────┘

Cost: $200-500/month
Handles: 10,000+ concurrent users
```

---

## Error Handling Flow

```
User Action
    │
    ▼
┌─────────────────────────────────┐
│  Optimistic Update (Frontend)   │
│  → Update UI immediately         │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Send to Server                 │
└──────────┬──────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌────────┐   ┌──────────┐
│Success │   │  Error   │
└───┬────┘   └────┬─────┘
    │             │
    ▼             ▼
┌────────┐   ┌──────────────────────────────┐
│ Confirm│   │  Rollback Optimistic Update  │
│ Update │   │  • Revert UI change          │
└────────┘   │  • Show error toast          │
             │  • Log error for debugging   │
             └──────────────────────────────┘

WebSocket Disconnect
    │
    ▼
┌─────────────────────────────────┐
│  Show "Reconnecting..." banner  │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Attempt Reconnection           │
│  • Exponential backoff          │
│  • Max 5 attempts               │
└──────────┬──────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌─────────┐  ┌──────────────┐
│Connected│  │ Failed       │
└────┬────┘  └──────┬───────┘
     │              │
     ▼              ▼
┌─────────┐  ┌────────────────────┐
│ Sync    │  │ Show error         │
│ State   │  │ "Please refresh"   │
└─────────┘  └────────────────────┘
```

---

## Summary

These diagrams illustrate:

1. **System Architecture**: Complete stack from browser to database
2. **Data Flow**: How user actions propagate through the system
3. **WebSocket Lifecycle**: Connection management and message handling
4. **Component Hierarchy**: Frontend React structure
5. **State Management**: Where and how data is stored
6. **Redis Structure**: Key-value organization
7. **Rendering Pipeline**: Component to canvas rendering
8. **Raytracing Flow**: Server-side computation process
9. **Deployment**: Dev and production environments
10. **Security Layers**: Multi-level protection
11. **Scaling**: Growth path from 100 to 10,000+ users
12. **Error Handling**: Graceful degradation and recovery

Use these as reference during implementation!

