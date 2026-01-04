# Code Review: Hub API Changes

## Overview
This review covers the new Hub API endpoints for device discovery and session management.

## Files to Review

### 1. Device Discovery Router
**File:** `ai-hub/src/hub/routers/device_discovery.py` (new file)

**Purpose:** Allows devices to discover sibling devices (same user) for remote skill calls.

**Key Points:**
- Uses device authentication (not user auth)
- Returns devices belonging to the same `user_id` as the requesting device
- Endpoints: `GET /devices`, `GET /devices/me`

**Review Focus:**
- [ ] Security: Is it appropriate for devices to see other devices?
- [ ] Response model completeness
- [ ] Error handling

---

### 2. Sessions Router
**File:** `ai-hub/src/hub/routers/sessions.py` (new file)

**Purpose:** CRUD operations for chat sessions and messages.

**Endpoints:**
- `POST /sessions` - Create session
- `GET /sessions` - List sessions for user
- `GET /sessions/{id}` - Get session
- `GET /sessions/{id}/messages` - Get messages
- `POST /sessions/{id}/messages` - Add message
- `DELETE /sessions/{id}` - Delete session

**Key Points:**
- Sessions belong to users, accessible from any of their devices
- Title auto-generated from first user message
- Messages ordered by creation time

**Review Focus:**
- [ ] Session isolation (user can only access own sessions)
- [ ] Pagination for large message lists
- [ ] Title generation logic
- [ ] Cascade delete of messages when session deleted

---

### 3. Router Registration
**Files:**
- `ai-hub/src/hub/routers/__init__.py`
- `ai-hub/src/hub/main.py`

**Changes:** Added imports and registration for new routers.

---

### 4. Tests
**Files:**
- `ai-hub/tests/test_devices.py` (new)
- `ai-hub/tests/test_sessions.py` (new)

**Coverage:**
- Device listing and auth requirements
- Session CRUD operations
- Message operations
- Title generation from first message

**Review Focus:**
- [ ] Edge case coverage
- [ ] Negative test cases
- [ ] Test isolation

---

## Questions for Reviewer

1. Should session listing support cursor-based pagination for large histories?
2. Should we add a max message limit per session?
3. Is the auto-title logic (first 50 chars of first user message) sufficient?
