---
description: Spoke core/backend and UI separation plan
---

# Spoke core/backend + UI separation plan

**Status**: CLI UI implemented, core/ module created (minimal version).

## Goals
- Provide a **single backend interface** that all UIs can use (CLI, PyQt6, Voice).
- Allow each UI to run standalone, while enabling **UI-to-UI orchestration** (CLI/Qt can start/stop Voice).
- Standardize **settings ownership** and **chat event streaming** with tool-call visibility.
- Eliminate async/race conditions in voice/agent pipelines.

## Implemented module layout

```
ai-pc-spoke/src/strawberry/
├── core/                       # ✅ IMPLEMENTED (minimal)
│   ├── __init__.py             # Exports SpokeCore, events, session
│   ├── app.py                  # SpokeCore + agent loop
│   ├── events.py               # Typed event models
│   └── session.py              # ChatSession state
├── voice/                      # TODO: Refactor from ui/voice_controller.py
│   └── ...
├── ui/
│   ├── qt/                     # Existing PyQt6 UI (needs migration)
│   └── cli/                    # ✅ IMPLEMENTED
│       ├── __init__.py
│       ├── main.py             # Entrypoint + async loop
│       └── renderer.py         # ANSI terminal output
├── skills/                     # Existing SkillService (reused by core)
├── llm/                        # Existing TensorZeroClient (reused by core)
└── config/                     # Existing config/.env loaders (reused)
```

**Note**: Separate `agent.py`, `skills_registry.py`, `settings.py`, `lifecycle.py` files were NOT needed. The agent loop is simple enough to live in `app.py`, and existing modules (`SkillService`, `config/`) handle skills and settings.

## 1) Backend/core interface (single class)

### **SpokeCore** (primary entrypoint)
- Responsible for:
  - Loading settings + config (config.yaml + .env).
  - Wiring skills + tool schemas.
  - Exposing a **chat session** abstraction.
  - Managing VoiceController lifecycle.
  - Abstracting online/offline agent loop decisions.

### Implemented API (v1)
```python
class SpokeCore:
    def __init__(self, settings_path: str | None = None) -> None: ...

    # lifecycle
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    # session + messages
    def new_session(self) -> ChatSession: ...
    def get_session(self, session_id: str) -> ChatSession | None: ...
    async def send_message(self, session_id: str, text: str) -> None: ...

    # info helpers
    def get_system_prompt(self) -> str: ...
    def get_model_info(self) -> str: ...
    def is_online(self) -> bool: ...

    # events
    def subscribe(self, handler: Callable[[CoreEvent], None]) -> Subscription: ...
    async def events(self) -> AsyncIterator[CoreEvent]: ...  # Alternative async-for API

    # TODO: voice integration (not yet implemented)
    # async def start_voice(self) -> None: ...
    # async def stop_voice(self) -> None: ...
    # def voice_status(self) -> VoiceStatus: ...

    # TODO: settings management (using existing config/ module for now)
    # def settings(self) -> SettingsSnapshot: ...
    # async def update_settings(self, patch: SettingsPatch) -> SettingsSnapshot: ...
```

**Changes from original plan**:
- `send_user_message` → `send_message` (simpler name)
- Added `get_session()`, `get_system_prompt()`, `get_model_info()`, `is_online()` helpers
- Added `events()` async iterator as alternative to callback-based `subscribe()`
- Voice and settings methods deferred (existing modules work for now)

### Why single class
- UI code stays simple (one entrypoint).
- Allows easy mock/stub for tests.
- Avoids leaking internal services (skills, agent loop, wake word engines).

## 2) Event model for UI updates + tool calls

UIs listen to **CoreEvent**s instead of poking internals.

### CoreEvent types (minimal starter set)
- `CoreReady`
- `CoreError`
- `SessionCreated(session_id)`
- `MessageAdded(session_id, message)`
- `ToolCallStarted(session_id, tool_call)`
- `ToolCallResult(session_id, tool_result)`
- `VoiceStatusChanged(status)`

### Message model (for CLI + Qt)
- `Message(role, text, metadata)`
- `metadata` includes optional `tool_name`, `tool_args`, `tool_result`, timing.

### Tool calls visibility
- Mirror the current **TensorZero tool-call** shape.
- UI should receive:
  - Tool call started (with args)
  - Tool result (with summary + full payload)

## 3) Settings ownership + UI changes

**Core owns config.yaml and .env.**

### Settings flow
1. UI requests `core.settings()` → returns a `SettingsSnapshot`.
2. UI edits fields and submits a `SettingsPatch`.
3. Core validates, writes config.yaml + .env, and emits `SettingsChanged` event.
4. Core **reinitializes** dependent services (voice pipeline, TensorZero, skills).

### Notes
- UI must never write config files directly.
- Core should preserve unknown keys/comments (already supported by persistence layer).

## 4) Async & race-condition plan

### Issues to prevent
- Starting voice while core not ready.
- Multiple overlapping voice sessions.
- STT finishing after session closed.
- UI sending message while agent loop not idle.

### Proposed fixes
- **State machine** inside `VoiceController`:
  - `STOPPED → IDLE → LISTENING → PROCESSING → IDLE`
- **Single-threaded async queue** for events → prevents reordering.
- `asyncio.Lock` around voice start/stop + agent loop.
- Each voice/agent request has a **request_id**; ignore late results for stale IDs.

## 5) Session/Chat handling for UIs

- `ChatSession` holds:
  - `session_id`
  - ordered list of messages (user/assistant/tool)
  - agent loop state (busy/idle)

UIs should render the session from events, and can rehydrate from `session.messages`.

## 6) UI-to-UI orchestration

- **CLI and Qt** can call `core.start_voice()` and `core.stop_voice()`.
- Voice UI can run standalone (uses `SpokeCore` only).
- A UI can subscribe to events to reflect **voice status**.

## 7) Implementation steps

1. ✅ Create `core/` module with `SpokeCore`, `events`, `session`.
2. ✅ Wrap existing agent loop + skills loader inside `SpokeCore`.
3. ✅ Create CLI UI using `SpokeCore`.
4. ⬜ Create `voice/` controller wrapper that emits status events.
5. ⬜ Refactor Qt UI to use `SpokeCore` only.
6. ⬜ Add unit tests for:
   - voice lifecycle state transitions
   - event ordering
   - settings update flow

## Resolved questions

| Question | Decision |
|----------|----------|
| Async vs sync core? | **Async core** with `asyncio.run()` for CLI. |
| Separate process for voice? | **Same process**, modular controller. |
| Separate agent.py file? | **No** - agent loop is simple, lives in `app.py`. |
| CLI needs aioconsole? | **No** - blocking `input()` + yield works fine. |

## Lessons from CLI implementation

1. **Keep it minimal**: The CLI only needed 2 files (~150 lines total). Don't over-engineer.
2. **Reuse existing modules**: `SkillService`, `TensorZeroClient`, and `config/` already do the heavy lifting.
3. **Event timing**: Blocking `input()` requires `await asyncio.sleep(0)` after `send_message()` to process queued events.
4. **Error propagation**: The event system handles errors well when exceptions are caught and emitted as `CoreError`.
