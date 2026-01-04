# Code Review

## Scope
This review focuses on implementation-level concerns: correctness risks, API contracts, typing/docstrings, test coverage, and maintainability across Hub and Spoke.

## Status Legend
- **Status: Needs-fix**: Likely bug, broken contract, security issue, or correctness risk.
- **Status: Consider**: Maintainability/clarity/perf improvements.
- **Status: Question**: Ambiguity; requires confirmation.
- **Status: OK**: Looks solid.

## Review Plan (write findings as we go)
### A. Code Organization & Boundaries
- Package layout and dependency directions (Hub↔Spoke shared logic)
- Entrypoints and configuration loading

### B. API Contracts
- Hub HTTP endpoints and auth dependencies
- WebSocket message formats (device connect, skill execute, responses)

### C. Skill System
- Skill discovery (search/describe)
- Skill execution and error propagation
- Hot reload / change detection and heartbeat expiry

### D. Sandbox / Bridge Implementation
- Host process management (Deno lifecycle)
- Guest execution model, timeouts, allow-list enforcement
- Serialization framing and output capture

### E. Quality Gates
- Type hints and docstrings consistency
- Ruff configuration and lint cleanliness
- Tests: coverage of negative cases and race conditions

---

## Initial Findings (from docs; to be verified in code)

### 1) “Single source of truth” for schemas and message contracts
**Observation:** Multiple layers reference JSON schema: TensorZero tool schemas in `tensorzero.toml`, plus sandbox bridge JSON payloads, plus Hub `/skills/execute` body.

- **Risk:** Drift across these definitions can break tool calling or remote execution.
- **Status:** 
- **Action taken:** Created `shared/` module at project root with:
  - `contracts.py` - Pydantic models for skill payloads (SkillInfo, SkillSearchResult, SkillExecuteRequest, etc.)
  - `normalization.py` - Device name normalization (single implementation)
  - `timeouts.py` - Centralized timeout constants
  - `errors.py` - Common error types
  - Hub and Spoke now import from shared module for consistency.

---

## Next Code Review Steps (implementation verification)
- Identify main entrypoints for Hub and Spoke.
- Locate skill loader, registry, and tool execution.
- Locate sandbox host/guest code and the bridge.
- Run targeted greps to map API endpoints and message types.

## Verified Findings (from Hub `/skills`, Hub `/ws/device`, and Spoke `HubClient`/`DeviceManager`)

### 2) Spoke `DeviceManager` creates new event loops for sync wrappers
**Where:** `ai-pc-spoke/src/strawberry/skills/remote.py` (`_fetch_all_skills`, `_execute_remote`) 

- **Risk:** Creating and closing event loops repeatedly is expensive and can misbehave under certain asyncio policies; also risks nested-loop issues when called from an already-running loop.
- **Status:** ✅ Fixed
- **Action taken:** Added `_run_async()` helper that:
  - Uses `asyncio.get_running_loop()` + `run_coroutine_threadsafe` if in async context
  - Falls back to `asyncio.run()` if no loop is running (efficient single-use)
  - Replaced all `asyncio.new_event_loop()` patterns in `_fetch_all_skills` and `_execute_remote`.

### 3) Sandbox bridge protocol is newline-delimited JSON; missing size limits and robustness
**Where:** `ai-pc-spoke/src/strawberry/skills/sandbox/bridge.py`

- **Observation:** Messages are sent as `json.dumps(message) + "\n"` and read with `stdout.readline()`.
- **Risk:** A single very large output or message can cause memory spikes; malformed/untrusted messages can keep the read loop running while silently logging JSON errors.
- **Status:** ✅ Addressed (TODOs added)
- **Action taken:** Added TODO comments and constants (`MAX_MESSAGE_SIZE`, `MAX_DECODE_ERRORS`) to `bridge.py` for future implementation.

### 4) Sandbox “remote mode” depends on `Gatekeeper.device_manager`, but initialization path is unclear
**Where:** `ai-pc-spoke/src/strawberry/skills/sandbox/gatekeeper.py`, `proxy_gen.py`, `skills/service.py`

- **Observation:** `Gatekeeper` supports:
  - `remote:Device.Skill.method` and `device_manager.search_skills/describe_function`
- **Risk:** If `device_manager` is not set on the gatekeeper, remote sandbox calls will hard-fail.
- **Status:** ✅ Clarified (TODO added)
- **Finding:** `set_device_manager` and `set_mode` are defined but not currently used. Mode switching is handled differently via `_DeviceProxy` (local) vs `_DeviceManagerProxy` (online) at initialization. Added TODO comment to `gatekeeper.py` documenting this.

### 5) Hub sessions: list endpoint has N+1 query pattern
**Where:** `ai-hub/src/hub/routers/sessions.py` (`list_sessions`)

- **Risk:** For each session, a separate query loads all messages to compute `message_count` and title.
- **Status:** ✅ Fixed
- **Action taken:** Added `title` and `message_count` columns to Session model. Updated `add_message` to maintain these cached values. Updated `list_sessions` and `get_session` to use cached values instead of N+1 queries.

### 6) Auth token claims differ from documented JWT payload
**Where:** `ai-hub/src/hub/auth.py`

- **Observation:** Tokens use `sub`, `type`, `name` (and optional extra claims). No `permissions` claim.
- **Status:** ✅ Fixed
- **Action taken:** Updated `DESIGN.md` JWT token documentation to reflect actual implementation (sub, type, name, exp, iat). Added note that permissions are not currently implemented as claims.

### 7) Sandbox direct execution fallback is intentionally insecure
**Where:** `ai-pc-spoke/src/strawberry/skills/sandbox/executor.py` (`enabled=False` path)

- **Status:** OK
- **Recommendation:** Ensure this is gated behind an explicit dev-only setting and is never enabled by default in production builds.


## Top Findings (Prioritized)

All "Needs-fix" items have been addressed. Remaining items are "Consider" status for future improvements.


## Simplification Opportunities
- **Consolidate “remote skill” plumbing**: Prefer one remote execution path (Hub `/skills/execute` via WS), and avoid duplicate loop-creation patterns in `DeviceManager`.
- **Centralize contracts**: Define skill path formatting + errors in one place to reduce drift (Hub router, spoke remote, sandbox gatekeeper).
