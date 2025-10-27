# Collaborative Optiverse - Quick Reference

## 🎯 Goal
Enable multiple users to work on the same optical design simultaneously via shared link.

---

## 🏗️ Recommended Architecture (at a glance)

```
┌─────────────────────────────────────┐
│  Browser A    Browser B    Browser C │
│     👤            👤           👤     │
└────────────┬────────────────────────┘
             │ WebSocket
             │
┌────────────▼────────────────────────┐
│    FastAPI Backend (Python)         │
│  • WebSocket rooms                  │
│  • Reuse existing raytracing core   │
│  • Session management               │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│   Redis (sessions) + PostgreSQL     │
└─────────────────────────────────────┘
```

---

## 📋 Implementation Checklist (MVP - 6 weeks)

### Backend (Weeks 1-2)
- [ ] Set up FastAPI project
- [ ] Port `core/models.py` to Pydantic models
- [ ] Create REST API endpoints for components
- [ ] Implement WebSocket handler
- [ ] Create session management (Redis)
- [ ] Add raytracing endpoint (reuse `trace_rays`)

### Frontend (Weeks 3-4)
- [ ] Create React + TypeScript app
- [ ] Install Konva.js for canvas
- [ ] Build component library panel
- [ ] Implement drag-and-drop
- [ ] Component rendering (lens, mirror, BS, source)
- [ ] Connect to backend for raytracing
- [ ] Edit component dialog

### Collaboration (Week 5)
- [ ] WebSocket client integration
- [ ] State synchronization
- [ ] Live updates between users
- [ ] Share link generation
- [ ] Basic user presence indicators

### Deploy (Week 6)
- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Railway
- [ ] Set up Redis + PostgreSQL
- [ ] Testing with multiple users
- [ ] Bug fixes

---

## 🔧 Tech Stack (Final Recommendation)

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | React 18 + TypeScript | Industry standard, great ecosystem |
| **Canvas** | Konva.js | Interactive graphics, drag/drop built-in |
| **Backend** | FastAPI (Python) | Reuse existing code, async, WebSocket |
| **Real-time** | Native WebSocket + Redis Pub/Sub | Simple initially, scalable |
| **Database** | PostgreSQL | Reliable, full-featured |
| **Cache** | Redis | Fast session state, presence |
| **Deployment** | Vercel (FE) + Railway (BE) | Easy, affordable, good DX |

---

## 🚀 Quick Start Commands (when implementing)

### Backend Setup
```bash
# Create backend project
mkdir optiverse-backend
cd optiverse-backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install fastapi uvicorn websockets redis sqlalchemy pydantic

# Copy core raytracing logic
cp -r ../optiverse/src/optiverse/core ./app/core

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
# Create React app
npx create-react-app optiverse-web --template typescript
cd optiverse-web

# Install dependencies
npm install konva react-konva zustand axios socket.io-client

# Run dev server
npm start
```

---

## 🔗 Share Link Flow

```
1. User clicks "Share"
   ↓
2. Backend creates session ID: abc123xyz456
   ↓
3. Frontend shows link: optiverse.app/session/abc123xyz456
   ↓
4. User copies link and sends to collaborator
   ↓
5. Collaborator opens link
   ↓
6. Both connect to same WebSocket room
   ↓
7. Changes sync in real-time via WebSocket
```

---

## 🔄 Data Flow for Component Move

```
User drags lens in Browser A
    ↓
1. Update local state (optimistic)
    ↓
2. Send to server: { type: "move", id: "lens1", x: 100, y: 50 }
    ↓
3. Server receives, updates session state in Redis
    ↓
4. Server broadcasts to all connected clients in room
    ↓
5. Browser B receives update
    ↓
6. Browser B renders lens at new position
```

---

## 📁 Proposed Code Structure

### Backend
```
optiverse-backend/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── websocket.py            # WebSocket handler
│   ├── sessions.py             # Session management
│   ├── database.py             # DB connection
│   ├── models/
│   │   ├── component.py        # Pydantic models
│   │   └── session.py
│   ├── core/                   # Copy from existing project
│   │   ├── geometry.py
│   │   ├── use_cases.py        # trace_rays() lives here
│   │   └── models.py
│   └── api/
│       ├── components.py       # REST endpoints
│       └── raytrace.py
├── requirements.txt
└── Dockerfile
```

### Frontend
```
optiverse-web/
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── Canvas.tsx          # Konva stage
│   │   ├── ComponentLibrary.tsx
│   │   ├── UserCursors.tsx
│   │   └── Toolbar.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts     # WebSocket connection
│   │   └── useSession.ts       # Session state
│   ├── store/
│   │   └── documentStore.ts    # Zustand store
│   ├── services/
│   │   ├── api.ts              # REST client
│   │   └── websocket.ts
│   └── types/
│       └── optics.ts           # TypeScript interfaces
├── package.json
└── tsconfig.json
```

---

## 🧪 Testing Multi-User Collaboration

### Manual Test
1. Open two browser windows side-by-side
2. In Window 1: Create new session, get share link
3. In Window 2: Open share link
4. In Window 1: Drag a lens onto canvas
5. **Expected**: Lens appears in Window 2 instantly
6. In Window 2: Rotate the lens
7. **Expected**: Lens rotates in Window 1 instantly

### Automated Test (Playwright)
```typescript
test('two users can collaborate', async ({ browser }) => {
  const user1 = await browser.newContext();
  const user2 = await browser.newContext();
  
  const page1 = await user1.newPage();
  const page2 = await user2.newPage();
  
  // User 1 creates session
  await page1.goto('/');
  await page1.click('[data-testid="new-session"]');
  const shareLink = await page1.textContent('[data-testid="share-link"]');
  
  // User 2 joins
  await page2.goto(shareLink);
  
  // User 1 adds component
  await page1.click('[data-testid="lens-button"]');
  await page1.click('canvas', { position: { x: 100, y: 100 } });
  
  // Verify user 2 sees it
  await expect(page2.locator('canvas')).toContainText('Lens');
});
```

---

## 🛡️ Security Checklist

- [x] Use cryptographically secure random for session IDs
- [x] Implement rate limiting (max 10 sessions per IP per hour)
- [x] Validate all WebSocket messages
- [x] Sanitize user input (component names, notes)
- [x] Use HTTPS/WSS in production
- [x] Set CORS headers appropriately
- [x] Add session expiry (24 hours inactive)
- [x] Optional: Add password protection for sensitive designs

---

## 💰 Estimated Costs (Monthly)

| Service | Provider | Cost |
|---------|----------|------|
| Frontend Hosting | Vercel | $0 (hobby tier) |
| Backend Hosting | Railway | $5-20 (usage-based) |
| PostgreSQL | Railway | Included |
| Redis | Upstash | $0 (free tier, 10k commands/day) |
| Domain | Namecheap | $1/month |
| **Total** | | **$6-21/month** |

Scale to 1000+ users: ~$50-100/month

---

## 🎨 UI/UX Considerations

### Desktop App vs Web
- **Keep**: Component library, drag-drop, snap to grid
- **Add**: Share button, user avatars, live cursors, chat (optional)
- **Improve**: Modern UI with Tailwind, better mobile support

### Collaboration Features Priority
1. ✅ **Must Have**: Live component sync, share link
2. ✅ **Should Have**: User presence, cursor tracking
3. 🎯 **Nice to Have**: Chat, comments, version history
4. 🔮 **Future**: Voice/video, AI suggestions

---

## 📈 Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| WebSocket latency | <100ms | Feels instant |
| Raytracing (100 rays) | <200ms | Smooth interaction |
| Component move | <50ms | Smooth dragging |
| Page load | <2s | Good UX |
| Support concurrent users | 10+ per session | Typical team size |

---

## 🔄 Fallback Plan: Hybrid Approach

If full web rewrite is too ambitious:

### Phase 1: Desktop + Cloud Backend
- Keep PyQt6 desktop app
- Add WebSocket client to desktop app
- Build lightweight FastAPI backend
- Users share link, both open desktop app
- **Pros**: Less work, preserve existing UI
- **Cons**: Requires app installation

### Phase 2: Add Web Client
- Build web frontend later
- Use same backend
- Desktop and web clients work together
- **Pros**: Incremental migration, support both

---

## 🎯 Decision Time

### Choose Your Path:

**Option A: Full Web (Recommended)**
- Timeline: 6-8 weeks MVP
- Effort: High
- Best for: Maximum reach, modern UX

**Option B: Hybrid Desktop + Backend**
- Timeline: 3-4 weeks MVP
- Effort: Medium
- Best for: Faster launch, existing users

**Option C: Quick Prototype**
- Use Tldraw or Excalidraw as base
- Add custom optics shapes
- Timeline: 2 weeks
- Best for: Testing concept

---

## 📞 Next Steps

1. ✅ Review strategy document
2. ⬜ Choose architecture (A, B, or C)
3. ⬜ Approve tech stack
4. ⬜ Set up development environment
5. ⬜ Create GitHub repo
6. ⬜ Start backend scaffolding
7. ⬜ Build frontend prototype
8. ⬜ Implement collaboration
9. ⬜ Test with real users
10. ⬜ Deploy to production

**Ready to start implementation?** Let me know which option you prefer!

