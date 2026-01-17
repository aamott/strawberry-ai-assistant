---
description: CLI UI design for the spoke (nanocode adaptation)
---

# CLI UI Design (nanocode adaptation)

**Status**: ✅ Implemented in `ai-pc-spoke/src/strawberry/ui/cli/`

## Scope
- Replace nanocode's LLM and tool plumbing with `SpokeCore`.
- Preserve the **streaming chat UX** and **tool-call visibility**.
- **Deferred**: Shift+Tab expand/collapse, `/voice` toggle (not needed for test UI).

---

## Layout

```
┌─────────────────────────────────────────────────────┐
│ strawberry-cli | offline | gemma:7b | ~/projects   │  ← header
├─────────────────────────────────────────────────────┤
│ > What's the weather?                               │  ← user
│ * Searching skills...                               │  ← assistant
│ ▸ search_skills("weather")  [3 results]             │  ← collapsed
│ * Running python_exec                               │
│ ▾ python_exec(code="...")                           │  ← expanded
│   │ Fetching weather for Salt Lake City...          │
│   │ Temperature: 72°F                               │
│   └─ returned: {"temp": 72, "condition": "sunny"}   │
│ * It's 72°F and sunny in Salt Lake City.            │  ← final
├─────────────────────────────────────────────────────┤
│ Shift+Tab: expand | /voice | /help      ● Waiting  │  ← status bar
└─────────────────────────────────────────────────────┘
```

---

## Keybindings

| Key | Action |
|-----|--------|
| **Shift+Tab** | Toggle expand/collapse on the *focused* tool call |
| `/voice` | Start/stop voice pipeline |
| `/clear` | Clear conversation |
| `/help` | Show help |
| `/quit` or `/q` | Quit |

---

## Tool Call Rendering

### Collapsed (default)
```
▸ tool_name(arg_preview...)  [N lines]
```
- Shows first arg value truncated to 40 chars.
- `[N lines]` shows hidden output line count.

### Expanded
```
▾ tool_name(arg_preview...)
  │ output line 1
  │ output line 2
  └─ returned: <result_preview>
```

### Focus & Navigation
- **Arrow keys** move focus between tool calls.
- **Shift+Tab** toggles expand on focused call.
- Focus is indicated by **bold** tool name.

---

## Voice Status Bar

Right side of the bottom bar shows:

| State | Display |
|-------|---------|
| Off | `○ Off` (gray) |
| Waiting | `● Waiting` (blue) |
| Listening | `● Listening` (green) |
| Processing | `● Processing` (orange) |

Controlled via `/voice` command.

---

## Async Input Handling

The CLI runs in a single asyncio loop:

1. **Input task**: Uses `aioconsole.ainput()` for non-blocking input.
2. **Event task**: Listens to `SpokeCore` event stream.
3. Both tasks run concurrently via `asyncio.gather()`.

When an event arrives mid-input:
- Render above the input line (ANSI cursor manipulation).
- Restore input prompt after rendering.

---

## SpokeCore Integration

| nanocode | CLI replacement |
|----------|-----------------|
| `call_api()` | `core.send_user_message(session_id, text)` |
| `run_tool()` | Agent loop inside SpokeCore |
| `TOOLS` dict | `core.skills_registry` + tool events |
| Response loop | `CoreEvent` async stream |

---

## Implemented Modules

```
strawberry/ui/cli/
├── __init__.py      # Exports main()
├── main.py          # Entrypoint, asyncio loop, command dispatch, event handling
└── renderer.py      # ANSI terminal output formatting
```

**Simplified from original plan**: `input.py` and `events.py` were not needed. Event handling is simple enough to inline in `main.py`, and blocking `input()` works with a yield.

---

## Events Handled

| Event | Render Action |
|-------|---------------|
| `CoreReady` | (silent) |
| `CoreError` | Show red error line |
| `MessageAdded` | Append assistant messages to transcript |
| `ToolCallStarted` | Show tool name + arg preview |
| `ToolCallResult` | Show result preview or error |

---

## Running

```bash
# From ai-pc-spoke directory
.venv/bin/python -m strawberry.ui.cli.main

# Or via installed entrypoint
strawberry-cli
```

## Tests

Keep tests inside the ui/cli/tests/ directory.