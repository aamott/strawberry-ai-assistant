# Architecture Review

## Scope
This review focuses on system-level concerns across Hub/Spoke/Sandbox, including boundaries, responsibilities, data flow, security model, and operational concerns.

## Status Legend
- **Status: Needs-fix**: A likely bug, security concern, or architectural mismatch that should be addressed.
- **Status: Consider**: Not required for correctness, but would improve maintainability/clarity/scale.
- **Status: Question**: Ambiguity between docs and implementation; needs confirmation.
- **Status: OK**: Looks solid as designed.

## Review Plan (write findings as we go)
### A. Boundaries & Responsibilities
- Hub vs Spoke ownership of:
  - Session storage
  - Skill discovery metadata
  - Tool calling / agent loop orchestration
  - Multi-device routing

### B. Data Flow & Contracts
- Spoke → Hub → LLM routing contracts
- Tool-call payload formats and error semantics
- Versioning strategy (how Spoke and Hub evolve safely)

### C. Security Model
- JWT scope and least privilege
- Sandbox isolation guarantees and bridge allow-list enforcement
- Multi-device authorization (user_id / device_id)

### D. Reliability & Ops
- WebSocket liveness and reconnection behavior
- Timeouts / retries / backpressure
- Persistence choices (SQLite vs Postgres)

### E. Simplification Opportunities
- Reduce duplicate orchestration layers
- Collapse redundant “online/offline mode” plumbing

---

## Initial Findings (from `SUMMARY.md` and `DESIGN.md`)

### 1) Hub vs Spoke: duplicated TensorZero gateways - INTENTIONAL
**REDACTED - This is intentional to allow the spoke to run without the hub.**

### 2) Session ownership appears Hub-centric, but offline mode exists
**Check this** since offline mode needs to be able to track its own session and chat history. The user can still reopen previous chats if they are synced in offline mode. When they open the hub their chats should be synced with the hub.

### 3) Remote mode routing spec conflicts with roadmap
**Observation:** Docs describe remote skill call routing via WebSocket (`ws://{hub}/ws/device?token={jwt}`) and `POST /skills/execute`. Roadmap later says Hub still needs “remote skill call routing (HTTP)” and “Spoke callback endpoint”.

- **Action** - update the roadmap

### 4) Sandbox isolation model is strong, but bridge transport is not pinned down
**Observation:** Bridge mentions “secure memory bridge or stdio”.

- **Risk:** Security and reliability depend heavily on this choice (framing, size limits, timeouts, message authentication).
- **Status:** Needs-fix
- **Recommendation:** Specify:
  - Transport mechanism (stdio JSON-RPC? length-prefixed frames?)
  - Max payload sizes
  - Correlation IDs for request/response
  - Sanitization rules for errors returned to LLM

- **Action** - Look at the current bridge implementation, then update the docs.

### 5) Allow-list gatekeeper is a critical security boundary
**Observation:** Design relies on “only registered skills permitted” and blocking imports/network/FS inside guest.

- **Status:** OK (conceptually)
- **Follow-up:** During code review, verify:
  - Guest actually cannot import `os`, `sys`, `socket`, etc.
  - Host gatekeeper validates both skill + method + args schema (not just “string contains”).
  - Device name normalization collision handling is implemented.

### 6) Timeouts: hard-kill sandbox and 30s skill routing
**Observation:** Sandbox timeout default 5s hard-kill; skill routing timeout 30s.

- **Risk:** Long-running or slow skills may be unusable; cancellation semantics unclear.
- **Status:** ✅ Fixed
- **Action taken:** Created `shared/timeouts.py` with unified `Timeouts` class:
  - `SANDBOX_EXECUTION` = 5s (hard-kill)
  - `LOCAL_SKILL_CALL` = 10s
  - `REMOTE_SKILL_CALL` = 30s
  - `UI_RESPONSE` = 60s
  - Includes `validate()` method to verify timeout hierarchy (SANDBOX < LOCAL < REMOTE < UI)
  - SandboxConfig now defaults to `Timeouts.SANDBOX_EXECUTION`

---

## Next Architecture Review Steps (implementation verification)
- Verify actual Hub WebSocket connection manager and routing implementation.
- Verify how sessions are persisted and fetched.
- Verify sandbox host/guest boundary and the bridge framing.
- Verify auth scopes/claims for device vs user actions.

## Verified Findings (from `ai-hub/src/hub/routers/{skills,websocket}.py` and Spoke `HubClient`)

### 7) Remote skill routing is now implemented (docs/roadmap need alignment)
**Observation:** Hub has `POST /skills/execute` and `ws://.../ws/device` plus request/response message types (`skill_request`/`skill_response`).

- **Impact:** Roadmap and some docs still frame this as pending.
- **Status:** Consider
- **Recommendation:** Update the roadmap/status text in docs to reflect what is implemented vs what remains (e.g. sandbox remote bridge integration).

### 8) Sandbox bridge transport is concretely stdin/stdout JSON lines (good), but needs framing limits
**Observation:** The sandbox uses JSON-over-stdio, newline-delimited messages (`BridgeClient`), with request IDs.

- **Status:** OK
- **Status (follow-up):** Consider
- **Recommendation:** Add explicit constraints:
  - Maximum line size / payload size to prevent memory blow-ups.
  - Handling for multi-line JSON (currently unsupported by design, but should be documented).

### 9) Sandbox isolation is partly enforced at the Deno layer, not the Pyodide layer
**Observation:** The Deno process is started with strict Deno permissions (`--deny-net`, `--deny-env`, `--deny-run`, `--deny-write`, and restrictive `--allow-read`).

- **Impact:** This is strong for the host runtime, but it does not by itself guarantee Pyodide cannot reach capabilities *within* the wasm runtime. The security boundary still primarily relies on the proxy/bridge/gatekeeper pattern. This is probably fine. 
- **Status:** OK
- **Follow-up:** Verify `host.ts` does not expose additional JS globals to Pyodide beyond `_js_bridge_call`.

### 10) Session model is Hub-backed and user-scoped; offline behavior still unspecified
**Observation:** Hub has full session CRUD under `/sessions`, scoped by `device.user_id`.

- **Impact:** This confirms Hub-central session storage for online mode.
- **Status:** OK (decision made)
- **Decision:** Local-first with sync-on-reconnect:
  - Offline: Store sessions locally in SQLite on the Spoke
  - Online: Sync sessions to Hub when connected (background upload)
  - Reconnect: Merge local sessions into Hub (by timestamp, avoiding duplicates)

### 11) Token claim contract differs from `DESIGN.md`
**Observation:** Actual JWT payload uses `{"sub": <id>, "type": "device"|"user", "name": <name>, ...}` (see `ai-hub/src/hub/auth.py`). `DESIGN.md` describes claims like `user_id`, `device_id`, `permissions`.

- **Impact:** Documentation drift; also affects any future authorization decisions (permissions are not implemented as claims).
- **Status:** ✅ Fixed
- **Action taken:** Updated `DESIGN.md` JWT token documentation to reflect actual implementation.

### 12) Sessions list endpoint is potentially N+1 heavy
**Observation:** `/sessions` loads sessions, then for each session performs an additional query for its messages to compute counts and the auto-title.

- **Impact:** With many sessions, this becomes slow and DB-heavy.
- **Status:** ✅ Fixed
- **Action taken:** Added `title` and `message_count` columns to Session model. Updated `add_message` to maintain these values. Updated `list_sessions` and `get_session` to use cached values.

## Top Findings (Prioritized)

Most "Needs-fix" items have been addressed:
- Device naming/normalization: Fixed - Hub now uses `normalize_device_name()` for skill paths
- Hub WebSocket concurrency: Fixed - `future.done()` check added
- Error semantics: Fixed - now uses HTTPException consistently

Remaining items:
1. **Status: OK — Offline session policy** - Decision: local-first with sync-on-reconnect
2. **Status: OK — Search response grouping** - Implemented: grouped by skill with `devices` list and `device_count` (handles 100+ devices efficiently)

## Simplification Opportunities (without reducing functionality)
- **Unify contracts and naming**: Introduce a shared “contract” module for:
  - Device name normalization
  - Skill path parsing/formatting
  - Error types
- **Pick one canonical error transport**: Prefer HTTP status codes + typed body; remove parallel `success` patterns.
- **Reduce duplicate discovery paths**: Decide whether skill discovery comes from Hub (`/skills/search`) or from a local cache—avoid having both “Hub list skills” and separate remote cache layers drift.
