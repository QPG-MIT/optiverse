# Web-Based Collaborative Optiverse: Implementation Strategy

## Executive Summary

This document outlines a strategy to enable real-time collaborative editing of optical designs in Optiverse through a web-based interface. The goal is to allow multiple users to work simultaneously on the same optical system design with live synchronization.

---

## Current Architecture Analysis

### Existing System
- **Platform**: PyQt6 desktop application (Python)
- **Data Model**: Component-based system with sources, lenses, mirrors, beamsplitters
- **Storage**: Local JSON files via `StorageService`
- **UI**: Qt Graphics View with draggable components
- **Core Logic**: Ray tracing engine in pure Python/NumPy

### Key Strengths to Preserve
- Robust raytracing engine (`trace_rays` in `use_cases.py`)
- Well-defined data models (`ComponentRecord`, `SourceParams`, etc.)
- Clean separation of concerns (core, services, UI)

---

## Proposed Architecture

### Option A: Hybrid Desktop + Web Backend (RECOMMENDED)

**Overview**: Keep the PyQt desktop app as the primary client, add a web backend for collaboration.

#### Architecture Components

```
┌─────────────────────────────────────────────────────────┐
│                    Desktop Clients                      │
│         (Existing PyQt6 App with WebSocket)             │
└──────────────────┬──────────────────────────────────────┘
                   │ WebSocket
                   │
┌──────────────────▼──────────────────────────────────────┐
│              Collaboration Server                       │
│  - FastAPI / Flask backend                              │
│  - WebSocket handler (Socket.IO / native WS)            │
│  - Session management                                   │
│  - Operational Transform / CRDT for conflict resolution │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│              Database / State Store                     │
│  - Redis (for active sessions, real-time state)         │
│  - PostgreSQL / SQLite (for persistent storage)         │
└─────────────────────────────────────────────────────────┘
```

**Pros:**
- Minimal changes to existing desktop app
- Keep full Qt performance and features
- Easier to implement initially
- Users can work offline and sync later

**Cons:**
- Users need to install desktop app
- Platform-specific (Windows, Mac, Linux builds)
- Link sharing requires app installation

---

### Option B: Full Web Application (FUTURE-PROOF)

**Overview**: Build a browser-based version using modern web stack.

#### Architecture Components

```
┌─────────────────────────────────────────────────────────┐
│                   Web Frontend                          │
│  - React / Vue.js / Svelte                              │
│  - Canvas API / Fabric.js / Konva.js for graphics      │
│  - WebSocket client                                     │
└──────────────────┬──────────────────────────────────────┘
                   │ WebSocket + REST API
                   │
┌──────────────────▼──────────────────────────────────────┐
│              Backend Server                             │
│  - FastAPI (Python) - reuse existing raytracing logic   │
│  - WebSocket rooms for collaboration                    │
│  - Y.js / Automerge for CRDT                            │
│  - Authentication & authorization                       │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│              Storage Layer                              │
│  - Redis (active sessions, presence)                    │
│  - PostgreSQL (user accounts, designs)                  │
│  - S3 / Cloud Storage (component images)                │
└─────────────────────────────────────────────────────────┘
```

**Pros:**
- No installation required
- True cross-platform (works on any device)
- Easy link sharing
- Can integrate with cloud services easily
- Modern UX possibilities

**Cons:**
- Complete rewrite of UI layer
- Canvas performance limitations vs native Qt
- Significant development time
- Python raytracing may need WebAssembly or server-side execution

---

## Detailed Design: Option B (Recommended for True Collaboration)

### 1. Technology Stack

#### Frontend
```
- Framework: React 18+ with TypeScript
- Canvas Library: Konva.js or Fabric.js (for interactive graphics)
- Real-time Sync: Yjs (CRDT library) with y-websocket
- State Management: Zustand or Jotai
- Styling: TailwindCSS
- UI Components: shadcn/ui or Radix UI
```

#### Backend
```
- Framework: FastAPI (Python 3.11+)
- Real-time: FastAPI WebSocket + Yjs backend
- Database: PostgreSQL with SQLAlchemy
- Cache: Redis for session state
- Auth: OAuth2 with JWT tokens
- Deployment: Docker + Kubernetes or Railway/Render
```

#### Shared/Core
```
- Raytracing: Reuse existing Python core logic
- Models: Pydantic models (compatible with existing dataclasses)
```

---

### 2. Data Synchronization Strategy

#### Conflict-Free Replicated Data Types (CRDT)

Use **Yjs** for automatic conflict resolution:

```typescript
// Document structure
{
  components: Y.Map<ComponentID, Component>,
  sources: Y.Map<SourceID, Source>,
  metadata: Y.Map<string, any>,
  history: Y.UndoManager
}
```

**Why CRDT?**
- Automatic merge of concurrent edits
- No central authority needed for conflict resolution
- Works offline (local-first approach)
- Battle-tested (Google Docs, Figma use similar tech)

#### Alternative: Operational Transformation (OT)

If CRDT is too complex initially:
- Server maintains authoritative state
- Clients send operations (add, move, delete, modify)
- Server transforms operations to resolve conflicts
- Broadcast transformed ops to all clients

---

### 3. Collaboration Features

#### Session Management
```python
# Session lifecycle
1. User creates/joins session → Generate unique link
2. Server creates/loads room in Redis
3. WebSocket connection established
4. Initial state synchronized
5. Changes broadcast to room participants
6. Periodic auto-save to PostgreSQL
7. Session closes → Final save
```

#### Presence Indicators
- Show who's online (avatars with colors)
- Live cursors for each user
- Component selection highlighting per user
- Activity feed (who did what)

#### Undo/Redo
- Per-user undo stack (Y.UndoManager)
- Option for global undo (coordinator mode)

#### Permissions
- Owner: full control
- Editor: can modify
- Viewer: read-only, see live updates
- Commentator: can add notes/annotations

---

### 4. API Design

#### REST Endpoints
```python
POST   /api/sessions              # Create new design session
GET    /api/sessions/{id}         # Get session metadata
POST   /api/sessions/{id}/join    # Join existing session
DELETE /api/sessions/{id}         # Delete session
GET    /api/sessions/{id}/export  # Export as JSON/PDF

POST   /api/raytrace              # Run raytracing on current state
GET    /api/library/components    # Get component library
POST   /api/library/components    # Add custom component
```

#### WebSocket Protocol
```typescript
// Client → Server
{
  type: "component:add" | "component:move" | "component:delete" | "component:edit",
  sessionId: string,
  userId: string,
  data: {
    componentId: string,
    position: { x: number, y: number },
    rotation: number,
    // ... other properties
  },
  timestamp: number
}

// Server → Clients
{
  type: "state:update" | "user:joined" | "user:left" | "cursor:move",
  userId: string,
  data: any,
  timestamp: number
}
```

---

### 5. Frontend Architecture

#### Component Structure
```
src/
├── components/
│   ├── Canvas/
│   │   ├── OpticsCanvas.tsx          # Main canvas component
│   │   ├── ComponentRenderer.tsx     # Render optics components
│   │   ├── RayRenderer.tsx           # Render ray traces
│   │   └── GridOverlay.tsx           # Grid background
│   ├── Toolbar/
│   │   ├── ComponentLibrary.tsx      # Drag-drop library
│   │   └── Tools.tsx                 # Selection, pan, zoom tools
│   ├── Collaboration/
│   │   ├── UserCursors.tsx           # Live cursor overlay
│   │   ├── UsersList.tsx             # Active users panel
│   │   └── ActivityFeed.tsx          # Recent actions
│   └── Dialogs/
│       ├── ComponentEditor.tsx       # Edit component properties
│       └── ShareDialog.tsx           # Share link management
├── hooks/
│   ├── useCollaboration.ts          # WebSocket & Yjs integration
│   ├── useRaytracing.ts             # Raytracing computation
│   └── useCanvasInteractions.ts     # Mouse/touch handling
├── store/
│   ├── documentStore.ts             # Yjs document wrapper
│   ├── uiStore.ts                   # UI state (zoom, selection)
│   └── authStore.ts                 # User authentication
└── services/
    ├── api.ts                       # REST API client
    ├── websocket.ts                 # WebSocket manager
    └── raytracer.ts                 # Bridge to backend raytracer
```

#### Canvas Rendering Strategy

**Option 1: Canvas API (Custom)**
- Direct control over rendering
- Maximum performance
- More development work

**Option 2: Konva.js (Recommended)**
- Built-in interactivity (drag, rotate)
- Layer management
- Good performance
- React wrapper available (react-konva)

**Option 3: Fabric.js**
- Rich object model
- Built-in transformations
- Slightly heavier than Konva

---

### 6. Raytracing Execution

#### Challenge
Python raytracing engine needs to run somehow in the browser context.

#### Solutions

**A. Server-Side Raytracing (RECOMMENDED)**
```
Client → Send component state → Server → Compute rays → Return paths → Client renders
```
- Reuse existing Python code
- Fast computation on server
- Client just renders results
- Works for collaborative updates

**B. WebAssembly Port**
- Compile NumPy raytracing to WASM (via Pyodide)
- Runs in browser
- Lower latency
- Complex setup, potential performance issues

**C. JavaScript Rewrite**
- Port raytracing to TypeScript
- Native browser execution
- Good performance with typed arrays
- Maintenance burden (two codebases)

**Recommended**: Start with server-side, optimize later if needed.

---

### 7. Sharing & Link Generation

#### Share Link Format
```
https://optiverse.app/session/abc123xyz456?role=editor
```

#### Implementation
```python
# Session creation
import secrets
session_id = secrets.token_urlsafe(16)  # Cryptographically secure
shareable_link = f"https://optiverse.app/session/{session_id}"

# Optional: Add access tokens for permission control
editor_token = secrets.token_urlsafe(32)
viewer_token = secrets.token_urlsafe(32)

editor_link = f"{base_url}?token={editor_token}"
viewer_link = f"{base_url}?token={viewer_token}"
```

#### Security Considerations
- Session IDs should be unguessable (use crypto-strong random)
- Optional password protection
- Expiry times for sessions
- Rate limiting on session creation

---

### 8. Migration Path: Desktop → Web

#### Phase 1: Backend Foundation (Weeks 1-3)
- [ ] Set up FastAPI project
- [ ] Port core models to Pydantic
- [ ] Implement REST API for CRUD operations
- [ ] Add WebSocket infrastructure
- [ ] Implement session management
- [ ] Port raytracing engine
- [ ] Database setup (PostgreSQL + Redis)

#### Phase 2: Basic Web Frontend (Weeks 4-6)
- [ ] Create React app with TypeScript
- [ ] Implement canvas with Konva.js
- [ ] Basic component rendering (lens, mirror, beamsplitter)
- [ ] Drag-and-drop from library
- [ ] Component editing dialog
- [ ] Ray visualization

#### Phase 3: Real-time Collaboration (Weeks 7-9)
- [ ] Integrate Yjs for CRDT
- [ ] WebSocket connection management
- [ ] Live cursor tracking
- [ ] User presence indicators
- [ ] Conflict resolution testing
- [ ] Multi-user stress testing

#### Phase 4: Feature Parity (Weeks 10-12)
- [ ] Implement all component types
- [ ] Grid & snap functionality
- [ ] Zoom & pan
- [ ] Ruler tool
- [ ] Text notes
- [ ] Export functionality (JSON, PNG, PDF)
- [ ] Undo/redo

#### Phase 5: Polish & Deploy (Weeks 13-14)
- [ ] Authentication (OAuth2 / email)
- [ ] User accounts & saved designs
- [ ] Share dialog with permissions
- [ ] Performance optimization
- [ ] Mobile responsiveness
- [ ] Deploy to production (Vercel + Railway/Render)

---

### 9. Deployment Architecture

#### Production Setup
```
┌───────────────────────────────────────────────────────┐
│                   Cloudflare / CDN                    │
│              (Static assets, DDoS protection)         │
└─────────────────────┬─────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────┐
│                   Vercel / Netlify                    │
│              (React Frontend hosting)                 │
└─────────────────────┬─────────────────────────────────┘
                      │ API calls
┌─────────────────────▼─────────────────────────────────┐
│              Railway / Render / Fly.io                │
│          (FastAPI Backend + WebSocket)                │
│              - Docker container                       │
│              - Auto-scaling                           │
└─────────────┬────────────────────┬────────────────────┘
              │                    │
┌─────────────▼──────────┐  ┌──────▼─────────────────┐
│    PostgreSQL          │  │      Redis Cloud       │
│  (Persistent storage)  │  │  (Session cache)       │
└────────────────────────┘  └────────────────────────┘
```

#### Cost Estimates (Monthly)
- Vercel (Frontend): $0 - $20 (Hobby → Pro)
- Railway (Backend): $5 - $20 (usage-based)
- PostgreSQL: $5 - $15 (small instance)
- Redis Cloud: $0 - $10 (free tier → small)
- **Total**: $10 - $65/month for small scale

---

### 10. Security Considerations

#### Authentication
- OAuth2 with Google/GitHub for easy onboarding
- JWT tokens for session management
- Refresh token rotation

#### Authorization
- Role-based access control (Owner, Editor, Viewer)
- Session-level permissions
- Rate limiting per user

#### Data Protection
- Encrypt sensitive data at rest
- TLS/HTTPS for all connections
- Secure WebSocket (WSS)
- Input validation & sanitization
- XSS protection (React default + CSP headers)

#### Session Security
- Unpredictable session IDs (32+ bytes entropy)
- Session expiry (e.g., 24 hours of inactivity)
- IP-based anomaly detection (optional)

---

### 11. Testing Strategy

#### Unit Tests
- Core raytracing logic (reuse existing tests)
- Data model serialization
- API endpoints

#### Integration Tests
- WebSocket message flow
- Session lifecycle
- CRDT conflict resolution
- Multi-user scenarios

#### E2E Tests (Playwright)
- User creates session
- User shares link
- Second user joins
- Both users add/move components
- Verify state consistency
- Test permissions

#### Performance Tests
- Raytracing speed (1000+ rays)
- WebSocket latency (<100ms)
- Concurrent users per session (target: 10+)
- Memory usage over long sessions

---

### 12. Alternative: Quick Prototype with Existing Tools

If full custom development is too heavy, consider using existing collaboration platforms:

#### Option: Figma Plugin
- Build Optiverse as a Figma plugin
- Figma handles all collaboration
- Use Figma's shapes for components
- Use plugin API for raytracing
- **Pros**: Collaboration for free, fast prototype
- **Cons**: Limited by Figma API, not standalone

#### Option: Excalidraw Fork
- Fork Excalidraw (open-source collaborative whiteboard)
- Add optics components
- Add raytracing layer
- **Pros**: Collaboration already built, great UX
- **Cons**: Less control, complex codebase to modify

#### Option: Tldraw Integration
- Use tldraw (open-source, embeddable whiteboard)
- Add custom shapes for optical components
- Add raytracing as overlay
- **Pros**: Modern, well-maintained, React-based
- **Cons**: Learning curve for custom shapes

---

## Recommended Implementation Plan

### Minimal Viable Product (MVP) - 6 Weeks

**Goal**: Shareable link with basic collaboration

#### Week 1-2: Backend Core
- FastAPI setup with WebSocket
- Port core models
- Basic session management (in-memory for MVP)
- REST API for CRUD
- Raytracing endpoint

#### Week 3-4: Frontend Basic
- React + Konva.js setup
- Render lens, mirror, beamsplitter
- Drag to add components
- Basic editing
- Connect to backend for raytracing

#### Week 5: Collaboration
- WebSocket integration
- Simple state sync (no CRDT yet, just broadcast)
- Live updates between clients
- Share link generation

#### Week 6: Polish
- Deployment setup
- Basic authentication (session-based)
- Bug fixes
- Demo preparation

### Post-MVP Enhancements
- Full CRDT implementation (Yjs)
- User accounts & persistent designs
- Advanced permissions
- Mobile support
- Performance optimization
- Additional component types
- Export features

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| CRDT complexity | High | Start with simple operational transform, add CRDT later |
| WebSocket scaling | Medium | Use Redis pub/sub, add load balancing |
| Raytracing performance | Medium | Optimize algorithm, add caching, debounce calculations |
| Browser compatibility | Low | Test on major browsers, provide polyfills |
| State inconsistency | High | Rigorous testing, rollback mechanism, conflict detection |
| User adoption | Medium | Keep desktop app, offer web as option |

---

## Success Metrics

### Technical
- [ ] Sub-100ms latency for component moves
- [ ] Support 10+ concurrent users per session
- [ ] 99.9% uptime
- [ ] Raytracing completes in <500ms for typical scenes

### User Experience
- [ ] Share link works in one click
- [ ] No user reports of lost changes
- [ ] Responsive on desktop and tablet
- [ ] Intuitive for new users (<5 min to first design)

---

## Conclusion

**Recommendation**: Proceed with **Option B (Full Web Application)** with the MVP approach outlined above.

**Rationale**:
1. True cross-platform accessibility (no app installation)
2. Modern collaboration UX (like Figma, Miro)
3. Can reuse core Python raytracing logic via API
4. Easier to iterate and deploy updates
5. Better for sharing (just send a link)

**Alternative**: If preserving the desktop experience is critical, start with **Option A (Hybrid)** and add a web client later as a separate interface to the same backend.

**Next Steps**:
1. Review and approve this strategy
2. Set up development environment
3. Create detailed task breakdown
4. Begin Phase 1 implementation

---

## Appendix: Technology Alternatives

### Frontend Frameworks
- **React**: Most popular, huge ecosystem, good for complex UIs
- **Vue 3**: Easier learning curve, good performance, smaller bundle
- **Svelte**: Fastest, smallest bundle, newer ecosystem
- **Solid.js**: React-like, better performance, smaller community

**Recommendation**: React (best balance of features, ecosystem, hiring)

### Canvas Libraries
- **Konva.js**: Best for interactive graphics, good React support
- **Fabric.js**: More object-oriented, heavier
- **PixiJS**: Best for performance, game-oriented
- **Paper.js**: Vector graphics focus, good for precise drawing

**Recommendation**: Konva.js (best fit for draggable components)

### Real-time Sync
- **Yjs**: CRDT, best for P2P, offline support
- **Automerge**: CRDT, more opinionated
- **ShareDB**: OT-based, simpler than CRDT
- **Custom WebSocket**: Full control, more work

**Recommendation**: Start custom, migrate to Yjs when needed

### Backend Frameworks
- **FastAPI**: Modern, async, auto-docs, Python 3.11+ features
- **Flask**: Simpler, more mature, synchronous
- **Django**: Full-featured, includes auth/ORM, heavier

**Recommendation**: FastAPI (best for real-time, modern Python)

### Deployment
- **Frontend**: Vercel, Netlify, Cloudflare Pages
- **Backend**: Railway, Render, Fly.io, AWS Fargate
- **Database**: Supabase, PlanetScale, Neon, Railway Postgres

**Recommendation**: Vercel + Railway (best DX, reasonable cost)

