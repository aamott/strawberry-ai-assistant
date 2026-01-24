---
description: Index for settings system design documents
---

# Settings System Design

This folder contains the comprehensive design for the Settings system, split into two main components:

## Documents

| Document | Description |
|----------|-------------|
| [settings-manager.md](./settings-manager.md) | Core SettingsManager - modular settings service with namespace isolation |
| [settings-ui.md](./settings-ui.md) | Settings UI - schema-driven interface for viewing and editing settings |

## Overview

The settings system has two decoupled parts:

### 1. SettingsManager (Backend)

The `SettingsManager` is a **service** that:
- Manages settings for multiple modules (SpokeCore, VoiceCore, STT backends, TTS backends, etc.)
- Provides **namespace isolation** so modules don't collide
- Handles **persistence** (YAML for config, .env for secrets)
- Supports **schema registration** for validation and UI generation
- Emits **change events** for reactive updates

### 2. Settings UI (Frontend)

The Settings UI is a **consumer** of the SettingsManager that:
- Queries registered schemas to build UI forms dynamically
- Groups settings by module/section
- Supports all field types (text, password, select, checkbox, action buttons)
- Handles provider sub-settings (e.g., when you select "Whisper" as STT, shows Whisper's settings)
- Sends updates back to SettingsManager

## Design Principles

1. **Decoupling**: The UI doesn't know about specific modules - it renders from schemas
2. **Modularity**: Each module owns its schema and can be added/removed independently
3. **Type Safety**: Pydantic models validate all settings
4. **Secrets Handling**: API keys and tokens stored separately in .env
5. **Discovery**: Provider backends self-describe their settings

## Migration Path

The current implementation has pieces scattered across:
- `spoke_core/settings_schema.py` - Schema definitions
- `config/settings.py` - Pydantic models
- `config/loader.py` - Loading/saving
- `SpokeCore` - Settings API

This design consolidates into:
- `shared/settings/` - SettingsManager package (see [settings-manager.md](./settings-manager.md))
- Provider base classes keep their `get_settings_schema()` method
- UIs use the new unified API

## Related Documents

- [../settings-design.md](../settings-design.md) - Original design sketch (superseded by this folder)
- [../folder-layout.md](../folder-layout.md) - Folder structure reference
- [../spoke-modules.md](../spoke-modules.md) - Module system overview
