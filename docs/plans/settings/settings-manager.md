---
description: SettingsManager - modular settings service with namespace isolation
related: [settings-ui.md, ../folder-layout.md]
---

# SettingsManager Design

The `SettingsManager` is a centralized service for managing settings across the application. It provides namespace isolation so modules like SpokeCore, VoiceCore, and individual backends can manage their own settings without conflicts.

## Design Goals

1. **Namespace Isolation**: Each module has its own settings namespace (e.g., `spoke_core`, `voice.stt.whisper`)
2. **Schema-Driven**: Modules register schemas for validation and UI generation
3. **Type-Safe**: Pydantic models validate all settings
4. **Secrets Separation**: API keys and tokens stored in `.env`, not config files
5. **Reactive**: Emit events when settings change so UIs can update
6. **Discoverable**: Provider backends can self-register their schemas

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SettingsManager                              │
├─────────────────────────────────────────────────────────────────────┤
│  Namespaces:                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────────────────────┐   │
│  │ spoke_core  │ │ voice_core  │ │ voice.stt.whisper           │   │
│  │  - hub.url  │ │  - stt.order│ │  - model_size: base         │   │
│  │  - hub.token│ │  - tts.order│ │  - language: auto           │   │
│  │  - device...│ │  - vad...   │ │  - device: cpu              │   │
│  └─────────────┘ └─────────────┘ └──────────────────────────────┘   │
│                                                                      │
│  Storage:                                                            │
│  ┌───────────────────────────┐  ┌─────────────────────────────────┐ │
│  │ config/settings.yaml      │  │ config/.env                     │ │
│  │ (nested YAML, all ns)     │  │ (secrets only, flat keys)       │ │
│  └───────────────────────────┘  └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Namespace** | Unique identifier for a module's settings (e.g., `spoke_core`, `voice.stt.whisper`) |
| **Schema** | List of `SettingField` objects describing the module's settings |
| **Values** | Current settings values as a flat dict (keys relative to namespace) |
| **Secrets** | Settings with `secret=True` stored in `.env` instead of YAML |

---

## File Structure

```
ai-pc-spoke/src/strawberry/
├── shared/
│   └── settings/
│       ├── __init__.py          # Public exports
│       ├── manager.py           # SettingsManager class
│       ├── schema.py            # SettingField, FieldType, ActionResult
│       ├── storage.py           # YamlStorage, EnvStorage classes
│       └── events.py            # SettingsChanged event
├── config/
│   ├── settings.yaml            # All non-secret settings (replaces config.yaml)
│   └── .env                     # Secrets (API keys, tokens)
└── ...
```

---

## Core API

### SettingsManager Class

```python
# shared/settings/manager.py
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from .schema import SettingField, ActionResult
from .storage import YamlStorage, EnvStorage
from .events import SettingsChanged


@dataclass
class RegisteredNamespace:
    """Metadata for a registered settings namespace."""
    name: str
    display_name: str
    schema: List[SettingField]
    order: int = 100  # For UI ordering (lower = first)


class SettingsManager:
    """Centralized settings service with namespace isolation.
    
    Provides a single point of access for all application settings,
    organized by namespace. Each module (SpokeCore, VoiceCore, backends)
    registers its own namespace with schema.
    
    Usage:
        # Initialize once at app startup
        settings = SettingsManager(config_dir=Path("config"))
        
        # Register namespaces
        settings.register("spoke_core", "Spoke Core", SPOKE_CORE_SCHEMA, order=10)
        settings.register("voice_core", "Voice", VOICE_CORE_SCHEMA, order=20)
        
        # Get/set values
        hub_url = settings.get("spoke_core", "hub.url")
        settings.set("spoke_core", "hub.url", "https://my-hub.com")
        
        # Listen for changes
        settings.on_change(lambda ns, key, val: print(f"{ns}.{key} = {val}"))
    """
    
    def __init__(
        self,
        config_dir: Path,
        auto_save: bool = True,
    ):
        """Initialize the settings manager.
        
        Args:
            config_dir: Directory containing settings.yaml and .env
            auto_save: If True, persist changes immediately
        """
        self._config_dir = config_dir
        self._auto_save = auto_save
        
        # Storage backends
        self._yaml_storage = YamlStorage(config_dir / "settings.yaml")
        self._env_storage = EnvStorage(config_dir / ".env")
        
        # Registered namespaces and their schemas
        self._namespaces: Dict[str, RegisteredNamespace] = {}
        
        # In-memory values (namespace -> {key: value})
        self._values: Dict[str, Dict[str, Any]] = {}
        
        # Change listeners
        self._listeners: List[Callable[[str, str, Any], None]] = []
        
        # Load existing values
        self._load()
    
    # ─────────────────────────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────────────────────────
    
    def register(
        self,
        namespace: str,
        display_name: str,
        schema: List[SettingField],
        order: int = 100,
    ) -> None:
        """Register a settings namespace with its schema.
        
        Args:
            namespace: Unique identifier (e.g., "spoke_core", "voice.stt.whisper")
            display_name: Human-readable name for UI (e.g., "Spoke Core")
            schema: List of SettingField definitions
            order: Display order in UI (lower = first)
        
        Raises:
            ValueError: If namespace is already registered
        """
        if namespace in self._namespaces:
            raise ValueError(f"Namespace '{namespace}' already registered")
        
        self._namespaces[namespace] = RegisteredNamespace(
            name=namespace,
            display_name=display_name,
            schema=schema,
            order=order,
        )
        
        # Initialize values with defaults if not already loaded
        if namespace not in self._values:
            self._values[namespace] = {}
        
        for field in schema:
            if field.key not in self._values[namespace]:
                self._values[namespace][field.key] = field.default
    
    def unregister(self, namespace: str) -> None:
        """Remove a registered namespace.
        
        Args:
            namespace: The namespace to remove
        """
        self._namespaces.pop(namespace, None)
        # Keep values in memory but they won't be schema-validated
    
    # ─────────────────────────────────────────────────────────────────
    # Value Access
    # ─────────────────────────────────────────────────────────────────
    
    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """Get a setting value.
        
        Args:
            namespace: The namespace (e.g., "spoke_core")
            key: The setting key within namespace (e.g., "hub.url")
            default: Value to return if not set
        
        Returns:
            The setting value or default
        """
        ns_values = self._values.get(namespace, {})
        return ns_values.get(key, default)
    
    def get_all(self, namespace: str) -> Dict[str, Any]:
        """Get all settings for a namespace.
        
        Args:
            namespace: The namespace
        
        Returns:
            Dict of all settings in the namespace
        """
        return dict(self._values.get(namespace, {}))
    
    def set(self, namespace: str, key: str, value: Any) -> None:
        """Set a setting value.
        
        Args:
            namespace: The namespace
            key: The setting key
            value: The new value
        """
        if namespace not in self._values:
            self._values[namespace] = {}
        
        old_value = self._values[namespace].get(key)
        self._values[namespace][key] = value
        
        # Persist if auto-save enabled
        if self._auto_save:
            self._save_key(namespace, key, value)
        
        # Notify listeners if value changed
        if old_value != value:
            self._emit_change(namespace, key, value)
    
    def update(self, namespace: str, values: Dict[str, Any]) -> None:
        """Update multiple settings at once.
        
        Args:
            namespace: The namespace
            values: Dict of key-value pairs to update
        """
        for key, value in values.items():
            self.set(namespace, key, value)
    
    # ─────────────────────────────────────────────────────────────────
    # Schema Access (for UI)
    # ─────────────────────────────────────────────────────────────────
    
    def get_namespaces(self) -> List[RegisteredNamespace]:
        """Get all registered namespaces, sorted by order.
        
        Returns:
            List of RegisteredNamespace sorted by order
        """
        return sorted(self._namespaces.values(), key=lambda ns: ns.order)
    
    def get_schema(self, namespace: str) -> List[SettingField]:
        """Get the schema for a namespace.
        
        Args:
            namespace: The namespace
        
        Returns:
            List of SettingField definitions
        
        Raises:
            KeyError: If namespace not registered
        """
        if namespace not in self._namespaces:
            raise KeyError(f"Namespace '{namespace}' not registered")
        return self._namespaces[namespace].schema
    
    def get_field(self, namespace: str, key: str) -> Optional[SettingField]:
        """Get a specific field definition.
        
        Args:
            namespace: The namespace
            key: The field key
        
        Returns:
            The SettingField or None
        """
        if namespace not in self._namespaces:
            return None
        for field in self._namespaces[namespace].schema:
            if field.key == key:
                return field
        return None
    
    def is_secret(self, namespace: str, key: str) -> bool:
        """Check if a field is marked as secret.
        
        Args:
            namespace: The namespace
            key: The field key
        
        Returns:
            True if field has secret=True
        """
        field = self.get_field(namespace, key)
        return field.secret if field else False
    
    # ─────────────────────────────────────────────────────────────────
    # Events
    # ─────────────────────────────────────────────────────────────────
    
    def on_change(self, callback: Callable[[str, str, Any], None]) -> None:
        """Register a callback for setting changes.
        
        Args:
            callback: Function(namespace, key, value) called on changes
        """
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[str, str, Any], None]) -> None:
        """Remove a change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _emit_change(self, namespace: str, key: str, value: Any) -> None:
        """Notify all listeners of a change."""
        for listener in self._listeners:
            try:
                listener(namespace, key, value)
            except Exception:
                pass  # Don't let listener errors break settings
    
    # ─────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────
    
    def _load(self) -> None:
        """Load all values from storage."""
        # Load YAML values
        yaml_data = self._yaml_storage.load()
        for namespace, ns_values in yaml_data.items():
            if isinstance(ns_values, dict):
                self._values[namespace] = ns_values
        
        # Load env values (overlay secrets)
        env_data = self._env_storage.load()
        # Env keys are like SPOKE_CORE__HUB__TOKEN -> spoke_core.hub.token
        for env_key, value in env_data.items():
            namespace, key = self._env_key_to_namespace(env_key)
            if namespace:
                if namespace not in self._values:
                    self._values[namespace] = {}
                self._values[namespace][key] = value
    
    def _save_key(self, namespace: str, key: str, value: Any) -> None:
        """Save a single key to appropriate storage."""
        if self.is_secret(namespace, key):
            env_key = self._namespace_to_env_key(namespace, key)
            self._env_storage.set(env_key, value)
        else:
            self._yaml_storage.set(namespace, key, value)
    
    def save(self) -> None:
        """Persist all values to storage (useful if auto_save=False)."""
        # Separate secrets from regular values
        yaml_values: Dict[str, Dict[str, Any]] = {}
        env_values: Dict[str, str] = {}
        
        for namespace, ns_values in self._values.items():
            yaml_values[namespace] = {}
            for key, value in ns_values.items():
                if self.is_secret(namespace, key):
                    env_key = self._namespace_to_env_key(namespace, key)
                    env_values[env_key] = str(value) if value else ""
                else:
                    yaml_values[namespace][key] = value
        
        self._yaml_storage.save(yaml_values)
        self._env_storage.save(env_values)
    
    def _namespace_to_env_key(self, namespace: str, key: str) -> str:
        """Convert namespace.key to ENV_VAR format.
        
        Example: ("voice.stt.whisper", "access_key") -> "VOICE_STT_WHISPER__ACCESS_KEY"
        """
        ns_part = namespace.upper().replace(".", "_")
        key_part = key.upper().replace(".", "__")
        return f"{ns_part}__{key_part}"
    
    def _env_key_to_namespace(self, env_key: str) -> tuple[Optional[str], str]:
        """Convert ENV_VAR format back to namespace and key.
        
        Example: "VOICE_STT_WHISPER__ACCESS_KEY" -> ("voice.stt.whisper", "access_key")
        
        Returns:
            (namespace, key) or (None, "") if can't parse
        """
        # Find registered namespace that matches prefix
        for namespace in self._namespaces:
            prefix = namespace.upper().replace(".", "_") + "__"
            if env_key.startswith(prefix):
                key = env_key[len(prefix):].lower().replace("__", ".")
                return namespace, key
        return None, ""
    
    # ─────────────────────────────────────────────────────────────────
    # Actions (for UI buttons)
    # ─────────────────────────────────────────────────────────────────
    
    async def execute_action(
        self,
        namespace: str,
        action: str,
        action_handler: Callable[[str, str], Any],
    ) -> ActionResult:
        """Execute a settings action.
        
        Args:
            namespace: The namespace
            action: The action name (from SettingField.action)
            action_handler: Callback to handle the action
        
        Returns:
            ActionResult with instructions for UI
        """
        return await action_handler(namespace, action)
```

---

## Storage Classes

### YamlStorage

```python
# shared/settings/storage.py
from pathlib import Path
from typing import Any, Dict
import yaml


class YamlStorage:
    """YAML file storage for settings."""
    
    def __init__(self, path: Path):
        self._path = path
    
    def load(self) -> Dict[str, Dict[str, Any]]:
        """Load all settings from YAML."""
        if not self._path.exists():
            return {}
        
        with open(self._path) as f:
            data = yaml.safe_load(f) or {}
        
        return data
    
    def save(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Save all settings to YAML."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def set(self, namespace: str, key: str, value: Any) -> None:
        """Set a single value (loads, modifies, saves)."""
        data = self.load()
        if namespace not in data:
            data[namespace] = {}
        
        # Handle nested keys like "hub.url"
        keys = key.split(".")
        target = data[namespace]
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        
        self.save(data)
```

### EnvStorage

```python
# shared/settings/storage.py (continued)
import os
from dotenv import load_dotenv, set_key


class EnvStorage:
    """Environment file storage for secrets."""
    
    def __init__(self, path: Path):
        self._path = path
        if path.exists():
            load_dotenv(path)
    
    def load(self) -> Dict[str, str]:
        """Load all values from .env file."""
        if not self._path.exists():
            return {}
        
        values = {}
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    values[key.strip()] = value.strip().strip('"').strip("'")
        return values
    
    def save(self, data: Dict[str, str]) -> None:
        """Save all secrets to .env file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        lines = []
        for key, value in data.items():
            # Quote values with spaces
            if " " in str(value):
                value = f'"{value}"'
            lines.append(f"{key}={value}")
        
        with open(self._path, "w") as f:
            f.write("\n".join(lines) + "\n")
    
    def set(self, key: str, value: Any) -> None:
        """Set a single value."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        set_key(str(self._path), key, str(value) if value else "")
        os.environ[key] = str(value) if value else ""
```

---

## Module Integration

### SpokeCore Example

```python
# spoke_core/app.py
from strawberry.shared.settings import SettingsManager
from .settings_schema import SPOKE_CORE_SCHEMA


class SpokeCore:
    """The spoke core application."""
    
    def __init__(self, settings_manager: SettingsManager):
        self._settings = settings_manager
        
        # Register our namespace
        self._settings.register(
            namespace="spoke_core",
            display_name="Spoke Core",
            schema=SPOKE_CORE_SCHEMA,
            order=10,
        )
        
        # Listen for changes
        self._settings.on_change(self._on_settings_changed)
    
    @property
    def hub_url(self) -> str:
        return self._settings.get("spoke_core", "hub.url", "")
    
    @property
    def hub_token(self) -> str:
        return self._settings.get("spoke_core", "hub.token", "")
    
    def _on_settings_changed(self, namespace: str, key: str, value: Any) -> None:
        """React to settings changes."""
        if namespace != "spoke_core":
            return
        
        if key == "hub.url":
            self._reconnect_hub()
        elif key == "hub.token":
            self._reauthenticate()
```

### VoiceCore Example

```python
# voice/voice_core.py
from strawberry.shared.settings import SettingsManager
from .settings_schema import VOICE_CORE_SCHEMA


class VoiceCore:
    """Voice processing engine."""
    
    def __init__(self, settings_manager: SettingsManager, ...):
        self._settings = settings_manager
        
        # Register our namespace
        self._settings.register(
            namespace="voice_core",
            display_name="Voice",
            schema=VOICE_CORE_SCHEMA,
            order=20,
        )
        
        # Also register each discovered backend
        self._register_backend_settings()
    
    def _register_backend_settings(self) -> None:
        """Register settings for all discovered backends."""
        from .stt.discovery import discover_stt_modules
        from .tts.discovery import discover_tts_modules
        
        # Register STT backends
        for name, cls in discover_stt_modules().items():
            schema = cls.get_settings_schema()
            if schema:
                self._settings.register(
                    namespace=f"voice.stt.{name}",
                    display_name=f"STT: {cls.name}",
                    schema=schema,
                    order=100,  # Backends come after core settings
                )
        
        # Register TTS backends
        for name, cls in discover_tts_modules().items():
            schema = cls.get_settings_schema()
            if schema:
                self._settings.register(
                    namespace=f"voice.tts.{name}",
                    display_name=f"TTS: {cls.name}",
                    schema=schema,
                    order=100,
                )
```

### VoiceCore Settings Schema

```python
# voice/settings_schema.py
from strawberry.shared.settings import SettingField, FieldType

VOICE_CORE_SCHEMA = [
    # Fallback order for STT
    SettingField(
        key="stt.order",
        label="STT Fallback Order",
        type=FieldType.TEXT,
        default="leopard,whisper,google",
        description="Comma-separated list of STT backends to try in order",
        group="stt",
    ),
    SettingField(
        key="stt.enabled",
        label="Enable STT",
        type=FieldType.CHECKBOX,
        default=True,
        group="stt",
    ),
    
    # Fallback order for TTS
    SettingField(
        key="tts.order",
        label="TTS Fallback Order",
        type=FieldType.TEXT,
        default="orca,piper,google",
        description="Comma-separated list of TTS backends to try in order",
        group="tts",
    ),
    SettingField(
        key="tts.enabled",
        label="Enable TTS",
        type=FieldType.CHECKBOX,
        default=True,
        group="tts",
    ),
    
    # Wake word
    SettingField(
        key="wakeword.phrase",
        label="Wake Word",
        type=FieldType.TEXT,
        default="hey strawberry",
        group="wakeword",
    ),
    SettingField(
        key="wakeword.enabled",
        label="Enable Wake Word",
        type=FieldType.CHECKBOX,
        default=True,
        group="wakeword",
    ),
]
```

---

## Configuration File Format

### settings.yaml

```yaml
# config/settings.yaml
# All non-secret settings organized by namespace

spoke_core:
  device:
    name: "My PC"
  hub:
    url: "https://hub.example.com"
  local_llm:
    model: "llama3.2:3b"
    enabled: true
  skills:
    allow_unsafe_exec: false

voice_core:
  stt:
    order: "leopard,whisper,google"
    enabled: true
  tts:
    order: "orca,piper,google"
    enabled: true
  wakeword:
    phrase: "hey strawberry"
    enabled: true

voice.stt.whisper:
  model_size: "base"
  language: "auto"
  device: "cpu"

voice.stt.leopard:
  # access_key is in .env

voice.tts.orca:
  # access_key is in .env
  voice: "female"
```

### .env

```bash
# config/.env
# Secrets only - API keys and tokens

SPOKE_CORE__HUB__TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
VOICE_STT_LEOPARD__ACCESS_KEY=abc123...
VOICE_STT_GOOGLE__API_KEY=AIza...
VOICE_TTS_ORCA__ACCESS_KEY=xyz789...
```

---

## Dynamic Options Provider

For `DYNAMIC_SELECT` fields, the SettingsManager can call providers:

```python
class SettingsManager:
    """..."""
    
    def __init__(self, ...):
        # ...
        self._options_providers: Dict[str, Callable[[], List[str]]] = {}
    
    def register_options_provider(
        self,
        name: str,
        provider: Callable[[], List[str]],
    ) -> None:
        """Register a callback for dynamic options.
        
        Args:
            name: Provider name (matches SettingField.options_provider)
            provider: Callable returning list of options
        """
        self._options_providers[name] = provider
    
    def get_options(self, provider_name: str) -> List[str]:
        """Get options from a registered provider.
        
        Args:
            provider_name: The provider name
        
        Returns:
            List of options or empty list if provider not found
        """
        provider = self._options_providers.get(provider_name)
        if provider:
            try:
                return provider()
            except Exception:
                return []
        return []


# Usage in SpokeCore
class SpokeCore:
    def __init__(self, settings_manager: SettingsManager):
        # ...
        settings_manager.register_options_provider(
            "get_available_models",
            self._get_ollama_models,
        )
    
    def _get_ollama_models(self) -> List[str]:
        """Return available Ollama models."""
        try:
            return self._ollama_client.list_models()
        except Exception:
            return ["llama3.2:3b", "gemma:7b"]  # Fallback
```

---

## App Initialization

```python
# main.py or app factory
from pathlib import Path
from strawberry.shared.settings import SettingsManager
from strawberry.spoke_core import SpokeCore
from strawberry.voice import VoiceCore


def create_app() -> tuple[SpokeCore, VoiceCore]:
    """Create and wire up the application."""
    
    # Create shared settings manager
    config_dir = Path(__file__).parent / "config"
    settings = SettingsManager(config_dir=config_dir)
    
    # Create components - they register their namespaces
    spoke_core = SpokeCore(settings_manager=settings)
    voice_core = VoiceCore(settings_manager=settings)
    
    return spoke_core, voice_core
```

---

## Implementation Steps

1. [ ] Create `shared/settings/` package structure
2. [ ] Implement `SettingField`, `FieldType`, `ActionResult` (move from spoke_core)
3. [ ] Implement `YamlStorage` and `EnvStorage` classes
4. [ ] Implement `SettingsManager` class
5. [ ] Create `SPOKE_CORE_SCHEMA` (migrate existing)
6. [ ] Create `VOICE_CORE_SCHEMA` (new)
7. [ ] Update `SpokeCore` to use SettingsManager
8. [ ] Update `VoiceCore` to use SettingsManager
9. [ ] Update provider base classes to self-register
10. [ ] Migrate existing config loading
11. [ ] Update tests

---

## Related Documents

- [settings-ui.md](./settings-ui.md) - UI design for rendering settings
- [../folder-layout.md](../folder-layout.md) - Overall folder structure
- [../settings-design.md](../settings-design.md) - Original design sketch
