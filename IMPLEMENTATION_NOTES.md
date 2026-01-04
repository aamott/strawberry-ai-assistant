# Implementation Notes - API Unification & Session Persistence

## Decisions Made

### 1. API Path Unification & Spoke-User Ownership

**Problem:** Hub currently has two auth flows:
- `/auth/*` - device-token based (device auth endpoints)
- `/api/*` - user-token based, requires login

**Decision:** Spokes are owned by users. The flow should be:

1. **First launch:** Spoke starts in "offline mode" with local-only skills
2. **Connect button:** User clicks "Connect to Hub" in the UI
3. **Hub URL prompt:** User enters hub URL (e.g., `http://192.168.1.10:8000`)
4. **Browser opens:** Spoke opens browser to Hub's web UI for login
5. **Device pairing:** After user logs in, Hub shows "Add Device" flow which generates a device token
6. **Token entry:** User copies token back to Spoke (or we use a pairing code flow)
7. **Connected:** Spoke stores token locally and reconnects automatically on future launches

**API changes needed:**
- Keep `/api/devices/token` (user-authenticated device creation) as primary path
- Remove open device registration endpoint (done)
- Spoke's `HubClient` should call `/api/devices` not `/devices`

### 2. Session + Message Persistence

**Where:** Hub stores sessions/messages (DB already has tables)

**Changes needed:**
- Hub `/v1/chat/completions` should create/use sessions
- Add `session_id` parameter to chat request
- Store messages to DB
- Add endpoints: `GET /sessions`, `GET /sessions/{id}/messages`
- Spoke UI: sidebar with chat list, ability to create new chat, load old chats

### 3. Skill Injection Ownership

**Decision:** Spoke injects skills into system prompt (current behavior).

**Rationale:** This is simpler - Spoke knows its own skills best, and remote mode already handles cross-device discovery via `device_manager`. Hub doesn't need to know about prompt engineering.

**Doc updates:** Remove Hub skill injection from plans, clarify Spoke handles it.

---

## Implementation Order

1. Update docs first (quick win, clarifies architecture)
2. Fix Hub API paths for consistency
3. Add session persistence to Hub chat endpoint
4. Add session list endpoints
5. Update Spoke HubClient to match new paths
6. Add chat history sidebar to Spoke UI
7. Run tests throughout

---

## Files to Modify

### Docs
- `HUB_IMPLEMENTATION.md` - remove skill injection plans, update phase checklist
- `DESIGN.md` - clarify spoke handles skill prompts

### Hub
- `routers/chat.py` - add session handling
- `routers/sessions.py` - new file for session endpoints
- `routers/__init__.py` - include sessions router
- `main.py` - include sessions router
- `routers/auth.py` - consider restricting open registration

### Spoke
- `hub/client.py` - fix endpoint paths (`/api/devices` etc.)
- `ui/main_window.py` - add chat history sidebar
- Possibly new `ui/widgets/chat_list.py`

### Tests
- `ai-hub/tests/test_sessions.py` - new
- `ai-hub/tests/test_chat.py` - add with session tests
