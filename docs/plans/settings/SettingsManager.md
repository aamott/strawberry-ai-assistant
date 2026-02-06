---
description: Index for settings system design documents. When working with the Settings Manager, start here.
---

# Settings System Design

This folder contains the comprehensive design for the Settings system.

## Documents

| Document | Description |
|----------|-------------|
| [settings-manager.md](./settings-manager.md) | Core SettingsManager - modular settings service with namespace isolation |
| [settings-ui.md](./settings-ui.md) | Settings UI - schema-driven interface for viewing and editing settings |

## Recent Enhancements

- **List Support**: A new `FieldType.LIST` allows managing lists of strings (e.g., for ordering providers or JSON payloads).
- **External Validation**: The `SettingsManager` now supports registering external validation callbacks, enabling complex cross-field or system-state validation (e.g., verifying a TTS backend is actually installed).

## Overview

The settings system has two decoupled parts:

### 1. SettingsManager (Backend)

The `SettingsManager` is a **service** that:
- Manages settings for multiple modules (SpokeCore, VoiceCore, backends, etc.)
- Provides **namespace isolation** so modules don't collide
- Handles **persistence** (YAML for config, .env for secrets)
- Supports **schema registration** with validation
- Emits **change events** for reactive updates
- Supports **external validation** via callbacks

### 2. Settings UI (Frontend)

The Settings UI is a **consumer** of the SettingsManager that:
- Queries registered schemas to build UI forms dynamically
- Groups settings by module/section
- Supports field types: text, password, select, checkbox, action buttons, and **lists**
- Handles provider sub-settings using the **Template Pattern** (no hardcoded "voice" logic)
- Sends updates back to SettingsManager

## usage Example

```python
# 1. Define Schema
schema = [
    SettingField("api_key", "API Key", FieldType.PASSWORD, secret=True),
    SettingField("backends", "Active Backends", FieldType.LIST),
]

# 2. Register Namespace
settings.register("my_module", "My Module", schema)

# 3. Register Validation (Optional)
def validate_backends(value):
    if "legacy" in value:
        return "Legacy backend deprecated"
    return None

settings.register_validator("my_module", "backends", validate_backends)
```

## Design Principles

1. **Decoupling**: The UI uses templates and schemas, identifying providers generically.
2. **Modularity**: Each module owns its schema and can be added/removed independently.
3. **Type Safety**: Pydantic models (where used) and schema validation ensure correctness.
4. **Secrets Handling**: API keys and tokens stored separately in .env.
5. **Discovery**: Provider backends self-describe their settings.
