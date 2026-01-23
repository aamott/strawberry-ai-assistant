---
description: Spoke core/backend and UI separation plan
---

# Spoke Core + UI Separation Plan

**Status**: Core and CLI implemented. Voice UI is a separate, independent module.

## Goals
- Provide a **single backend interface** (`SpokeCore`) for chat/skills/agents.
- Voice UI is an **independent module** that UIs can launch and control (see [voice_ui.md](voice_ui.md)).
- Standardize **settings ownership** and **chat event streaming** with tool-call visibility.

## Module layout

```
ai-pc-spoke/src/strawberry/
├── core/                       # ✅ Chat, skills, agent loop
│   ├── app.py                  # SpokeCore
│   ├── events.py               # Typed event models
│   └── session.py              # ChatSession state
├── voice/                      # ✅ Independent Voice UI module
│   └── ...                     # (see voice_ui.md for design)
├── ui/
│   ├── qt/                     # PyQt6 UI
│   └── cli/                    # ✅ CLI UI
├── skills/                     # SkillService
├── llm/                        # TensorZeroClient
└── config/                     # Config loaders
```

TODO: Include hub skill registration in the core. Currently only implemented in the QT UI.

## SpokeCore API

```python
class SpokeCore:
    # lifecycle
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    # chat sessions
    def new_session(self) -> ChatSession: ...
    def get_session(self, session_id: str) -> ChatSession | None: ...
    async def send_message(self, session_id: str, text: str) -> None: ...

    # info
    def get_system_prompt(self) -> str: ...
    def is_online(self) -> bool: ...

    # events
    def subscribe(self, handler: Callable[[CoreEvent], None]) -> Subscription: ...
```

**SpokeCore does NOT manage voice.** UIs that want voice control launch/control the Voice UI module directly.

## CoreEvent types

- `CoreReady`, `CoreError`
- `SessionCreated(session_id)`
- `MessageAdded(session_id, message)`
- `ToolCallStarted`, `ToolCallResult`

## Settings ownership

Core owns `config.yaml` and `.env`. UIs request settings via `core.settings()`, submit changes via `SettingsPatch`, and core emits `SettingsChanged`.

## Voice UI integration

Voice UI is a **standalone module** (see [voice_ui.md](voice_ui.md)). UIs interact with it directly:

```python
# Qt or CLI calls Voice UI module directly
voice_ui.start()           # Start listening pipeline
voice_ui.stop()            # Stop listening
voice_ui.trigger_listen()  # Skip wakeword
voice_ui.speak(text)       # TTS
voice_ui.state             # Current state (waiting, listening, processing, speaking)
```

When Voice UI transcribes speech, it emits events. The calling UI can forward transcribed text to `SpokeCore.send_message()` and speak responses via `voice_ui.speak()`.

## Implementation status

| Step | Status |
|------|--------|
| `core/` module (SpokeCore, events, session) | ✅ |
| CLI UI using SpokeCore | ✅ |
| Settings schema + SchemaSettingsWidget | ✅ |
| Voice module with state machine | ✅ |
| Modular voice backends (STT, TTS, VAD, Wake) | ✅ |
| Qt UI integration | ✅ |

## Design notes

- **No voice methods on SpokeCore**: Keeps core focused on chat/skills. Voice is orthogonal.
- **Loose coupling**: Voice UI emits events; UIs bridge them to SpokeCore as needed.
- **Reuse existing modules**: `SkillService`, `TensorZeroClient`, and `config/` handle heavy lifting.
