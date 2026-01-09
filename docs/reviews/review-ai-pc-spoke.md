# AI-PC-Spoke Code Review

**Date**: 2026-01-08

## Scope
This review covers the ai-pc-spoke codebase, focusing on:
- Code simplification opportunities
- UI improvements
- Architecture concerns
- Easy wins for implementation

## Status Legend
- **Easy Win**: Simple fix, low risk, can implement now
- **Consider**: Good improvement but needs more work or has downstream impact
- **Question**: Needs clarification
- **OK**: Solid as-is

---

## Structure Overview
```
src/strawberry/
├── audio/      # Audio I/O (8 items)
├── config/     # Configuration management (6 items)
├── hub/        # Hub client connection (2 items)
├── llm/        # LLM integration (3 items)
├── pipeline/   # Conversation orchestration (3 items)
├── skills/     # Skill loading/execution (12 items)
├── storage/    # Data persistence (3 items)
├── stt/        # Speech-to-text (5 items)
├── terminal.py # Terminal UI (458 lines)
├── testing/    # Test framework (2 items)
├── tts/        # Text-to-speech (5 items)
├── ui/         # PySide6 GUI (19 items)
├── vad/        # Voice activity detection (6 items)
└── wake/       # Wake word detection (5 items)
```

---

## Findings

### 1) main_window.py is too large (1413 lines)
**Status: Consider**

The file handles:
- UI setup and theming
- Hub connection management
- TensorZero integration
- Session management (local + Hub)
- Voice controller integration
- Settings persistence
- Agent loop execution (2 similar implementations)

**Recommendation**: Extract into smaller modules:
- `chat_controller.py` - Agent loop logic (~200 lines)
- `session_controller.py` - Session CRUD (~150 lines)
- `hub_manager.py` - Hub connection lifecycle (~100 lines)

**Downstream impact**: Medium - needs careful refactoring to maintain signal/slot connections.

### 2) Duplicate agent loops: `_send_message` vs `_send_message_via_tensorzero`
**Status: Easy Win**

Both methods implement nearly identical agent loops (5 iterations, code block parsing, tool execution, UI updates). Only difference is the LLM client used.

**Lines**: 532-698 (`_send_message`) and 700-889 (`_send_message_via_tensorzero`)

**Recommendation**: Extract common agent loop logic into a single method that accepts an LLM client interface.

### 4) Duplicate `ChatResponse` classes with different fields
**Status: Consider**

- `hub/client.py:54-60` - has `content, model, finish_reason, raw`
- `llm/tensorzero_client.py:48-57` - has `content, model, variant, is_fallback, inference_id, tool_calls, raw`

**Recommendation**: Create a unified response type or clear inheritance. The TensorZero response is a superset.

### 5) service.py is large (1162 lines)
**Status: Consider**

Contains:
- `SkillService` class (~500 lines)
- `_DeviceProxy` class (~100 lines)
- `_SkillProxy` class (~20 lines)
- `_DeviceManagerProxy` class (~150 lines)
- Tool execution logic

**Recommendation**: Already has some separation. Could extract proxy classes to `proxies.py`.

### 6) Terminal mode doesn't use TensorZero
**Status: Question**

`terminal.py` only uses `HubClient` directly, missing TensorZero's fallback capabilities. Users running in terminal mode won't get local LLM fallback.

**Options**:
- Add TensorZero support to terminal mode
- Document limitation
- Keep simple for terminal use case

### 7) Hardcoded endpoint in voice response handler
**Status: Easy Win**

In `main_window.py:1138-1146`, the voice response uses a hardcoded HTTP client instead of the shared HubClient:

```python
response = await client.post(
    "/api/v1/chat/completions",
    ...
)
```

This duplicates the Hub API logic and bypasses retry/error handling.

**Recommendation**: Refactor to use shared client or add a note explaining the thread-safety requirement.

### 9) UI Widget organization is good
**Status: OK**

Widgets are well-organized in `ui/widgets/` with reasonable file sizes:
- `assistant_turn_widget.py` (9KB)
- `chat_area.py` (6KB)
- `chat_history.py` (10KB)
- etc.

### 10) Settings model is clean
**Status: OK**

`config/settings.py` uses Pydantic models effectively. Well-structured with clear defaults.

---

## High Priority Fix: Hub token saved but app stayed Offline

### Symptom
Entering a Hub token in the Settings dialog (and saving) still left the app in **Offline** mode and it did not register skills with the Hub.

### Root cause
`MainWindow._apply_settings_changes()` persisted settings using **relative paths**:
- `Path("config/config.yaml")`
- `Path(".env")`

When launching the GUI, the current working directory can differ from the `ai-pc-spoke` project root, which caused the token to be written to (or read from) the wrong `.env`. That meant `self.settings.hub.token` remained unset/old, so `_init_hub()` never created a `HubClient`, and the UI stayed Offline.

### Fix
Updated `MainWindow._apply_settings_changes()` to:
- Resolve `project_root = Path(__file__).resolve().parents[3]`
- Persist to:
  - `project_root / "config" / "config.yaml"`
  - `project_root / ".env"`
- Eagerly apply the token to `os.environ` (HUB_DEVICE_TOKEN/HUB_TOKEN) before reconnect so the reconnect works even if persistence fails.

### Verification
- `ruff check .` passes
- `.venv/bin/python -m strawberry.testing.runner` passes

### Manual test
1. Open Settings -> Hub Connection
2. Paste Hub token and Save
3. Confirm status changes to **Online** and skills are registered

---

## Simplification Opportunities Summary

### Open items (future work)
1. Split `main_window.py` into smaller modules
2. Extract agent loop logic to reduce duplication
3. Unify `ChatResponse` types
4. Extract proxy classes from `service.py`
5. Decide whether terminal mode should use TensorZero fallback
