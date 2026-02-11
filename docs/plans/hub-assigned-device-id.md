# Hub-Assigned Device ID — Implementation Plan

> **Goal**: Replace name-based device identity with a Hub-assigned UUID so
> multiple Spokes can share one token without collisions.  Display names
> become cosmetic (auto-suffixed on collision).

---

## Context files to read first

| Purpose | Path |
|---------|------|
| Repo overview | `SUMMARY.md` |
| Wire schema (current contract) | `docs/wire-schema-v1.md` |
| Hub device router | `ai-hub/src/hub/routers/devices.py` |
| Hub device discovery | `ai-hub/src/hub/routers/device_discovery.py` |
| Hub WebSocket router | `ai-hub/src/hub/routers/websocket.py` |
| Hub database models | `ai-hub/src/hub/database.py` |
| Hub protocol middleware | `ai-hub/src/hub/protocol.py` |
| Spoke HubClient | `ai-pc-spoke/src/strawberry/hub/client.py` |
| Spoke hub_connection_manager | `ai-pc-spoke/src/strawberry/spoke_core/hub_connection_manager.py` |
| Spoke config/settings | `ai-pc-spoke/src/strawberry/spoke_core/config.py` or `settings_schema.py` |
| Normalization parity fixture | `docs/test-fixtures/normalize_device_name.json` |
| Wire schema fixture | `docs/test-fixtures/wire_schema_v1.json` |
| Existing Hub tests | `ai-hub/tests/` (especially `test_devices.py`, `test_protocol.py`) |
| Existing Spoke tests | `ai-pc-spoke/tests/` (especially `test_protocol.py`, `test_hub_client.py`) |

---

## Design decisions

1. **Device identity** = Hub-assigned UUID (`device_id`), stored in Hub DB
   and persisted on Spoke in `config/.device_id`.
2. **Display name** = user-chosen string (e.g. "Kitchen PC").  Cosmetic only.
   Auto-suffixed by Hub on collision within the same token scope
   (`kitchen_pc` → `kitchen_pc_2`).
3. **Routing** uses `device_id` everywhere internally.  Display names are
   only used in user-facing output (LLM prompts, UI, search results).
4. **Wire schema v1 stays compatible**: the `device_name` field in existing
   payloads becomes the display name; a new `device_id` field is added.
   Hub accepts either for a transition period.

---

## Implementation steps

### Phase 1 — Hub: device ID in the database

1. **Add `device_id` column** (UUID, unique, non-null with default) to the
   devices table in `database.py`.  Use `ALTER TABLE` migration pattern
   already established (see `init_db()` column-add pattern for sessions).
2. **Backfill**: on startup, any device row without a `device_id` gets one
   generated.
3. **Update device CRUD** in `routers/devices.py` and
   `routers/device_discovery.py` to read/write `device_id`.

### Phase 2 — Hub: registration handshake

4. **Modify `/devices/register`** (or equivalent endpoint):
   - Accept optional `device_id` in the request body.
   - If `device_id` is provided and matches an existing device → update
     (reconnect).  Return the same `device_id`.
   - If `device_id` is absent or unknown → create new device, generate UUID,
     return it in the response body.
5. **Display name collision handling**:
   - On register, normalize the display name.
   - If another device *under the same token* already has that normalized
     name, auto-suffix: `name_2`, `name_3`, etc.
   - Return the resolved display name in the registration response so the
     Spoke knows what it's called.
6. **Update WebSocket handshake** in `routers/websocket.py`:
   - Accept `device_id` as the primary identifier (query param or first
     message field).
   - Fall back to token+name lookup for backward compat during transition.

### Phase 3 — Hub: routing by device_id

7. **Skill registry**: key skills by `device_id` instead of normalized name.
   Update `routers/skills.py` — registration, search, and execution
   endpoints.
8. **Skill execution routing**: when the LLM emits
   `devices.<display_name>.Skill.method`, resolve `display_name` →
   `device_id` via a Hub-side lookup, then route to the correct WebSocket.
9. **Search results**: continue returning `display_name` in search results
   (for LLM/user consumption) but internally track `device_id`.

### Phase 4 — Spoke: persist and send device_id

10. **On first connect**: Spoke sends registration *without* `device_id`.
    Hub returns one.  Spoke writes it to `config/.device_id`.
11. **On subsequent connects**: Spoke reads `config/.device_id` and includes
    it in the registration request.  Hub recognizes it and updates
    (reconnect) rather than creating a new device.
12. **HubClient changes** (`client.py`):
    - Add `device_id` to registration payload.
    - Store the Hub-returned `device_id` and resolved display name.
    - Include `device_id` in WebSocket connect params.
13. **hub_connection_manager changes**:
    - Read/write `config/.device_id` file.
    - Pass `device_id` through to HubClient registration calls.

### Phase 5 — Wire schema update

14. **Update `docs/wire-schema-v1.md`**:
    - Document `device_id` field in registration request/response.
    - Document `device_id` in skill execution request.
    - Document display name collision resolution behavior.
    - Note backward compat: `device_name` still accepted, `device_id`
      preferred.
15. **Update test fixtures**:
    - `wire_schema_v1.json`: add `device_id` fields to sample payloads.
    - Add new fixture for registration handshake (request without
      `device_id` → response with `device_id`).

### Phase 6 — Tests

16. **Hub tests**:
    - Registration without `device_id` → Hub assigns one, returns it.
    - Registration with known `device_id` → reconnect, same device.
    - Registration with unknown `device_id` → new device created.
    - Display name collision → auto-suffix applied.
    - Skill routing uses `device_id`, not display name.
    - WebSocket connects by `device_id`.
17. **Spoke tests**:
    - First connect persists `device_id` to file.
    - Subsequent connect sends persisted `device_id`.
    - Resolved display name is stored and used.
18. **Contract tests**: update `test_wire_contract.py` with new fixture
    payloads.
19. **Run full test suites** in both repos.

### Phase 7 — Cleanup

20. **Remove name-based device lookup** code paths once transition is
    complete (can be deferred to a later PR).
21. **Update README** if the device setup flow changes.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Existing devices lose identity on upgrade | Backfill generates IDs; name-based fallback during transition |
| `.device_id` file lost on Spoke | Hub creates a new device; old one becomes stale (add TTL/cleanup later) |
| LLM uses display names in code | Hub resolves display name → device_id at execution time |
| Wire schema backward compat | Accept both `device_name` and `device_id`; prefer `device_id` |

---

## Out of scope (future)

- Per-token device slot limits
- Device transfer between tokens
- Hub UI for device management
- Device groups / rooms
