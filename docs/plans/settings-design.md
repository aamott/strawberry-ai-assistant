---
description: Original settings design sketch (superseded by settings/ folder)
status: superseded
superseded_by: settings/README.md
---

# Settings System Design (Original Sketch)

> **Note:** This document has been superseded by the comprehensive design in [`settings/`](./settings/README.md):
> - [settings/settings-manager.md](./settings/settings-manager.md) - SettingsManager backend design
> - [settings/settings-ui.md](./settings/settings-ui.md) - Settings UI design
>
> The content below is preserved for historical reference.

---

## Overview

Settings are organized into three tiers:

| Tier | Scope | Storage | Example |
|------|-------|---------|---------|
| **Core** | All UIs share | `config.yaml` + `.env` | Device name, hub token, offline model |
| **UI-specific** | One UI only | `ui/<name>/config.yaml` | Qt theme, CLI colors |
| **Module** | Per-provider | `modules/<type>/<name>/config.yaml` | Whisper model size, Google Cloud API key |

```
config/
├── config.yaml              # Core settings (all UIs)
├── .env                     # Core secrets (hub token, API keys)
└── ui/
    ├── qt/config.yaml       # Qt-specific (theme, window size)
    ├── cli/config.yaml      # CLI-specific (colors)
    └── voice/config.yaml    # Voice-specific (selected STT/TTS, voice name)

voice/stt/
├── whisper/
│   ├── __init__.py          # STTProvider class
│   └── schema.py            # SettingsSchema for this module
├── google_cloud/
│   ├── __init__.py
│   └── schema.py
└── ...
```

---

## 1. Core Settings (Shared)

Owned by `SpokeCore`. UIs read/write via `core.settings()` and `core.update_settings()`.

### Schema Definition

```python
# core/settings_schema.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class FieldType(Enum):
    TEXT = "text"
    PASSWORD = "password"    # masked, stored in .env
    NUMBER = "number"
    CHECKBOX = "checkbox"
    SELECT = "select"        # static dropdown
    DYNAMIC_SELECT = "dynamic_select"  # populated at runtime
    ACTION = "action"        # triggers a flow (e.g., OAuth)

@dataclass
class SettingField:
    key: str                          # e.g., "hub.device_name"
    label: str                        # e.g., "Device Name"
    type: FieldType
    default: Any = None
    description: str = ""
    options: list[str] | None = None  # for SELECT
    options_provider: str | None = None  # for DYNAMIC_SELECT (method name)
    action: str | None = None         # for ACTION (method name)
    secret: bool = False              # store in .env instead of config.yaml
    group: str = "general"            # UI grouping
    depends_on: str | None = None     # only show if this key has a truthy value

CORE_SETTINGS_SCHEMA = [
    # General
    SettingField("device_name", "Device Name", FieldType.TEXT, 
                 default="My PC", group="general"),
    
    # Hub
    SettingField("hub.url", "Hub URL", FieldType.TEXT, 
                 default="", group="hub"),
    SettingField("hub.token", "Hub Token", FieldType.PASSWORD, 
                 secret=True, group="hub"),
    SettingField("hub.connect", "Connect to Hub", FieldType.ACTION, 
                 action="hub_oauth", group="hub"),
    
    # Offline
    SettingField("offline.model", "Offline Model", FieldType.DYNAMIC_SELECT,
                 options_provider="get_available_models", group="offline"),
    SettingField("offline.max_iterations", "Max Agent Iterations", FieldType.NUMBER,
                 default=10, group="offline"),
]
```

### Dynamic Options

For `DYNAMIC_SELECT`, the UI calls a method on `SpokeCore` to get options:

```python
class SpokeCore:
    def get_settings_options(self, provider: str) -> list[str]:
        """Return available options for a dynamic select field."""
        if provider == "get_available_models":
            return self._ollama_client.list_models()  # ["gemma:7b", "llama3:8b", ...]
        raise ValueError(f"Unknown options provider: {provider}")
```

---

## 2. UI-Specific Settings

Each UI owns its own config file. The schema lives in the UI module.

### Qt UI Example

```python
# ui/qt/settings_schema.py
QT_SETTINGS_SCHEMA = [
    SettingField("theme", "Theme", FieldType.SELECT, 
                 options=["light", "dark", "system"], default="system"),
    SettingField("window.width", "Window Width", FieldType.NUMBER, default=1200),
    SettingField("window.height", "Window Height", FieldType.NUMBER, default=800),
    SettingField("font_size", "Font Size", FieldType.NUMBER, default=14),
]
```

### CLI UI Example

```python
# ui/cli/settings_schema.py
CLI_SETTINGS_SCHEMA = [
    SettingField("colors.user", "User Message Color", FieldType.SELECT,
                 options=["blue", "cyan", "white"], default="blue"),
    SettingField("colors.assistant", "Assistant Color", FieldType.SELECT,
                 options=["cyan", "green", "white"], default="cyan"),
]
```

---

## 3. Module Settings (Discoverable)

For Voice UI's STT/TTS modules, each module **self-describes** its settings.

### Module Structure

```
voice/stt/whisper/
├── __init__.py      # WhisperSTT class (implements STTProvider)
├── schema.py        # SETTINGS_SCHEMA for this module
└── config.yaml      # User's saved settings for this module
```

### Module Interface

```python
# voice/stt/base.py
from abc import ABC, abstractmethod

class STTProvider(ABC):
    """Base class for all STT providers."""
    
    # Metadata for discovery
    name: str = "Unnamed"
    description: str = ""
    
    @classmethod
    @abstractmethod
    def get_settings_schema(cls) -> list[SettingField]:
        """Return the settings schema for this provider."""
        ...
    
    @abstractmethod
    async def transcribe(self, audio: bytes) -> str:
        """Transcribe audio to text."""
        ...
```

### Example: Whisper Module

```python
# voice/stt/whisper/__init__.py
from voice.stt.base import STTProvider

class WhisperSTT(STTProvider):
    name = "Whisper (Local)"
    description = "OpenAI Whisper running locally via whisper.cpp"
    
    @classmethod
    def get_settings_schema(cls) -> list[SettingField]:
        return [
            SettingField("model_size", "Model Size", FieldType.SELECT,
                         options=["tiny", "base", "small", "medium", "large"],
                         default="base"),
            SettingField("language", "Language", FieldType.SELECT,
                         options=["auto", "en", "es", "fr", "de", "zh"],
                         default="auto"),
            SettingField("device", "Device", FieldType.SELECT,
                         options=["cpu", "cuda"],
                         default="cpu"),
        ]
    
    async def transcribe(self, audio: bytes) -> str:
        # Use self.config["model_size"], etc.
        ...
```

### Example: Google Cloud STT Module

```python
# voice/stt/google_cloud/__init__.py
class GoogleCloudSTT(STTProvider):
    name = "Google Cloud Speech"
    description = "Google Cloud Speech-to-Text API"
    
    @classmethod
    def get_settings_schema(cls) -> list[SettingField]:
        return [
            SettingField("api_key", "API Key", FieldType.PASSWORD, secret=True),
            SettingField("model", "Model", FieldType.SELECT,
                         options=["default", "phone_call", "video", "command_and_search"],
                         default="default"),
            SettingField("language_code", "Language", FieldType.TEXT,
                         default="en-US"),
        ]
```

### Module Discovery

```python
# voice/module_registry.py
import importlib
import pkgutil
from pathlib import Path

def discover_stt_modules() -> dict[str, type[STTProvider]]:
    """Scan voice/stt/ for STTProvider subclasses."""
    modules = {}
    stt_path = Path(__file__).parent / "stt"
    
    for finder, name, ispkg in pkgutil.iter_modules([str(stt_path)]):
        if ispkg:
            try:
                module = importlib.import_module(f"voice.stt.{name}")
                for attr in dir(module):
                    obj = getattr(module, attr)
                    if isinstance(obj, type) and issubclass(obj, STTProvider) and obj is not STTProvider:
                        modules[name] = obj
            except ImportError:
                pass
    
    return modules  # {"whisper": WhisperSTT, "google_cloud": GoogleCloudSTT, ...}
```

---

## 4. UI Rendering Pattern

### Combined Schema for Voice UI Settings Page

The Voice UI builds a combined schema:

```python
# ui/voice_settings.py
def get_voice_settings_schema(voice_controller) -> list[SettingField]:
    stt_modules = voice_controller.discover_stt_modules()
    tts_modules = voice_controller.discover_tts_modules()
    
    return [
        # Provider selection (populated dynamically)
        SettingField("stt.provider", "Speech-to-Text", FieldType.SELECT,
                     options=list(stt_modules.keys()), default="whisper"),
        
        # Provider-specific settings are injected dynamically
        # (see "Conditional Rendering" below)
        
        SettingField("tts.provider", "Text-to-Speech", FieldType.SELECT,
                     options=list(tts_modules.keys()), default="piper"),
        
        # General voice settings
        SettingField("wakeword.phrase", "Wake Word", FieldType.TEXT,
                     default="hey strawberry"),
        SettingField("auto_start", "Start on Launch", FieldType.CHECKBOX,
                     default=False),
    ]
```

### Conditional Rendering

When user selects an STT provider, the UI:

1. Reads `stt.provider` value (e.g., `"whisper"`)
2. Calls `stt_modules["whisper"].get_settings_schema()`
3. Renders those fields **indented/grouped** below the dropdown

```
┌───────────────────────────────────────────────────────────┐
│ Speech-to-Text:  [▼ Whisper (Local)    ]                  │
│   ┌─────────────────────────────────────────────────────┐ │
│   │ Model Size:  [▼ base               ]                │ │
│   │ Language:    [▼ auto               ]                │ │
│   │ Device:      [▼ cpu                ]                │ │
│   └─────────────────────────────────────────────────────┘ │
│                                                           │
│ Text-to-Speech:  [▼ Piper (Local)      ]                  │
│   ┌─────────────────────────────────────────────────────┐ │
│   │ Voice:       [▼ en_US-lessac-medium]                │ │
│   │ Speed:       [1.0                  ]                │ │
│   └─────────────────────────────────────────────────────┘ │
│                                                           │
│ Wake Word:       [hey strawberry       ]                  │
│ Start on Launch: [✓]                                      │
└───────────────────────────────────────────────────────────┘
```

---

## 5. Storage Architecture

### Where Settings Are Saved

| Setting Type | Location | Format |
|--------------|----------|--------|
| Core (non-secret) | `config/config.yaml` | YAML |
| Core (secret) | `config/.env` | dotenv |
| Qt UI | `config/ui/qt/config.yaml` | YAML |
| CLI UI | `config/ui/cli/config.yaml` | YAML |
| Voice UI | `config/ui/voice/config.yaml` | YAML |
| Whisper module | `config/modules/stt/whisper.yaml` | YAML |
| Google Cloud module | `config/modules/stt/google_cloud.yaml` | YAML |

### Module Settings Namespace

Module settings are prefixed with the module type and name:

```yaml
# config/ui/voice/config.yaml
stt:
  provider: whisper
tts:
  provider: piper
wakeword:
  phrase: "hey strawberry"
auto_start: false

# config/modules/stt/whisper.yaml
model_size: base
language: auto
device: cpu

# config/modules/stt/google_cloud.yaml
api_key: ""  # or in .env as GOOGLE_CLOUD_STT_API_KEY
model: default
language_code: en-US
```

---

## 6. Complex Flows (Actions)

### Hub OAuth Flow

```python
class SpokeCore:
    async def execute_settings_action(self, action: str) -> ActionResult:
        if action == "hub_oauth":
            return await self._hub_oauth_flow()
        raise ValueError(f"Unknown action: {action}")
    
    async def _hub_oauth_flow(self) -> ActionResult:
        # 1. Start local callback server on random port
        callback_port = await self._start_callback_server()
        
        # 2. Build auth URL
        state = secrets.token_urlsafe(32)
        auth_url = f"{self.settings.hub_url}/auth/device?state={state}&callback=http://localhost:{callback_port}/callback"
        
        # 3. Return action for UI to execute
        return ActionResult(
            type="open_browser",
            url=auth_url,
            message="A browser window will open. Log in to connect this device.",
            pending=True  # UI should show spinner until SettingsChanged event
        )
    
    # Callback server receives token, saves to .env, emits SettingsChanged
```

### ActionResult Types

```python
@dataclass
class ActionResult:
    type: Literal["open_browser", "show_dialog", "success", "error"]
    url: str | None = None
    message: str = ""
    pending: bool = False  # if True, UI waits for SettingsChanged event
```

---

## 7. API Summary

### SpokeCore Settings API

```python
class SpokeCore:
    # Core settings
    def get_settings_schema(self) -> list[SettingField]: ...
    def get_settings(self) -> dict[str, Any]: ...
    async def update_settings(self, patch: dict[str, Any]) -> None: ...
    
    # Dynamic options
    def get_settings_options(self, provider: str) -> list[str]: ...
    
    # Actions
    async def execute_settings_action(self, action: str) -> ActionResult: ...
```

### UI Settings API

Each UI manages its own settings:

```python
class QtSettingsManager:
    def get_schema(self) -> list[SettingField]: ...
    def get_settings(self) -> dict[str, Any]: ...
    def update_settings(self, patch: dict[str, Any]) -> None: ...
```

### Module Settings API

```python
class VoiceController:
    # Module discovery
    def discover_stt_modules(self) -> dict[str, type[STTProvider]]: ...
    def discover_tts_modules(self) -> dict[str, type[TTSProvider]]: ...
    
    # Module settings
    def get_module_settings(self, type: str, name: str) -> dict[str, Any]: ...
    def update_module_settings(self, type: str, name: str, patch: dict[str, Any]) -> None: ...
```

---

## 8. Implementation Steps

1. ✅ Create `core/settings_schema.py` with `SettingField`, `FieldType`, `ActionResult`, `CORE_SETTINGS_SCHEMA`
2. ✅ Add `get_settings_schema()`, `get_settings()`, `update_settings()` to `SpokeCore`
3. ✅ Update `stt/base.py` with `name`, `description`, `get_settings_schema()` support
4. ✅ Implement module discovery in `stt/discovery.py` and `tts/discovery.py`
5. ✅ Add metadata + `get_settings_schema()` to LeopardSTT and OrcaTTS
6. ✅ Create `ui/widgets/schema_settings.py` (`SchemaSettingsWidget`) for auto-rendering from schema
7. ⬜ Integrate `SchemaSettingsWidget` into existing settings dialog for module-specific settings
