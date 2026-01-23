---
description: CLI UI design for the spoke (nanocode adaptation)
---

# CLI UI Design (nanocode adaptation)

**Status**: ✅ Implemented in `ai-pc-spoke/src/strawberry/ui/cli/` (CLI V1)

Follow nanocode's design and implementation, but use `SpokeCore` instead of nanocode's API calls. (See `nanocode/nanocode.py`)

## Scope
- Replace nanocode's LLM and tool plumbing with `SpokeCore`.
- Preserve the **streaming chat UX** and **tool-call visibility**.
- **Deferred**: Shift+Tab expand/collapse, `/voice` toggle.
- Send all logs made by SpokeCore (including those made by its tensorzero backend) to a log file instead of to the console. 

---

## Slash Commands

| Command | Action |
|---------|--------|
| `/help` | Show help |
| `/quit` or `/q` | Quit |
| `/clear` | Clear conversation |
| `/last` | Show the full output of the most recent tool call |

---

## Tool Call Rendering

### Summary-only (default)
```
* tool_name(arg_preview...) → <result_preview>
```
- Shows a single-line summary with arg preview (max 40 chars) and result preview.
- Use `/last` to show the full output for the most recent tool call.

---

## Voice UI

- /voice to start voice mode. 
- `>` is blue while voice mode is inactive. Green when active.
- When a wakeword is detected and the user's prompt is recorded, the prompt is sent as a user message.
- The next response is read out loud, top to bottom (filtering tool calls). 

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