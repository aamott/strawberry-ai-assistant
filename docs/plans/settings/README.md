---
description: Index for settings system design documents. When working with the Settings Manager, start here. 
---

# Settings System Design

This folder contains the comprehensive design for the Settings system, split into two main components:

## Documents

| Document | Description |
|----------|-------------|
| [settings-manager.md](./settings-manager.md) | Core SettingsManager - modular settings service with namespace isolation |
| [settings-ui.md](./settings-ui.md) | Settings UI - schema-driven interface for viewing and editing settings |

## TODO
- [ ] How do we add a health status? If a user needs to update an API key, they should see that the skill is unhealthy and a message about it. If an MCP server is down, they should see that it is unhealthy and a message about it. 
    - [ ] a red outline around the setting should indicate that it is unhealthy
- [ ] How do we integrate setting descriptions? The QT UI can display them as tooltips, but the schema needs a way to include them. 

## Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| SettingsManager | ✅ Complete | `shared/settings/manager.py` |
| SettingsViewModel | ✅ Complete | `shared/settings/view_model.py` |
| Storage (YAML/Env) | ✅ Complete | `shared/settings/storage.py` |
| Schema types | ✅ Complete | `shared/settings/schema.py` |
| Qt Settings UI | ✅ Complete | `ui/qt/widgets/settings/` |
| CLI Settings UI | ✅ Complete | `ui/cli/settings_menu.py` |
| SpokeCore integration | ✅ Complete | `spoke_core/app.py` |
| VoiceCore integration | ✅ Complete | `voice/voice_core.py` |
| Backend schemas | ✅ Complete | Leopard, Orca, Pocket, Porcupine, FasterWhisper |
| Old config deprecation | ✅ Complete | `config/` package deprecated with warnings |

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

### Old System (Deprecated)
- `config/settings.py` - Pydantic models
- `config/loader.py` - Loading from config.yaml
- `config/persistence.py` - Saving changes

### New System (Active)
- `shared/settings/` - SettingsManager package
- `config/settings.yaml` - New YAML format (namespaced)
- `.env` - Secrets (API keys, tokens)

### Backward Compatibility
The old `config/` package is still used for backward compatibility during transition.
Components that have been updated:
- Qt App creates `SettingsManager` and passes to `MainWindow`
- `SpokeCore` accepts optional `SettingsManager`, syncs with Pydantic model
- `VoiceCore` accepts optional `SettingsManager`, registers backend namespaces
- Qt Settings Dialog uses new schema-driven UI when `SettingsManager` available

## Related Documents

- [../settings-design.md](../settings-design.md) - Original design sketch (superseded by this folder)
- [../folder-layout.md](../folder-layout.md) - Folder structure reference
- [../spoke-modules.md](../spoke-modules.md) - Module system overview
