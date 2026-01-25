---
description: Plan for completing migration from old config/ module to SettingsManager
---

# Settings Migration: Phase 5 - Complete Removal

This document outlines the remaining work to fully remove the deprecated `config/` module and migrate all components to use `SettingsManager` exclusively.

## Current State

The old `config/` module has been deprecated with runtime warnings, but several files still import from it for backward compatibility.

### Files Still Using Old Config

| File | Import | Usage |
|------|--------|-------|
| [spoke_core/app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/spoke_core/app.py) | `get_settings` | Fallback when no SettingsManager provided |
| [ui/qt/app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/app.py) | `Settings, load_config` | Loads legacy config, passes to MainWindow |
| [ui/qt/main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py) | `Settings` | Type hint, extensive field access |
| [ui/qt/settings_dialog.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/settings_dialog.py) | `Settings` | Legacy settings dialog |
| [ui/voice_interface/voice_interface.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/voice_interface/voice_interface.py) | `get_settings` | Loads hub config for voice interface |

### What Doesn't Need Migration

- **CLI UI** (`ui/cli/`) - Already uses SettingsManager only ✅
- **Skills** (`skills/`) - Doesn't use the config module directly ✅
- **Voice Backends** - Already migrated to SettingsManager ✅
- **VoiceCore** - Already uses SettingsManager ✅

---

## Migration Tasks

### 1. SpokeCore Migration

**File:** [spoke_core/app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/spoke_core/app.py)

**Current:** Falls back to `get_settings()` when no SettingsManager is provided.

**Change:**
- Require SettingsManager in constructor (no fallback to old config)
- Or create SettingsManager internally if not provided
- Remove `from ..config import get_settings`

---

### 2. Qt App Migration

**File:** [ui/qt/app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/app.py)

**Current:** Loads old Settings via `load_config()`, passes to MainWindow.

**Change:**
- Remove `load_config()` call
- Pass only SettingsManager to MainWindow
- Remove `from ...config import Settings, load_config`

---

### 3. MainWindow Migration (Largest Task)

**File:** [ui/qt/main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py)

**Current:** Uses `self.settings` extensively for:
- `settings.device.name` - Device name display
- `settings.storage.db_path` - Database path
- `settings.tensorzero.enabled` - TensorZero toggle
- `settings.local_llm.model` - Local LLM model name
- `settings.hub.url`, `settings.hub.token` - Hub connection
- `settings.llm.temperature` - LLM temperature
- `settings.conversation.max_history` - History limit
- `settings.ui.*` - Theme, start_minimized, show_waveform
- `settings.skills.path` - Skills directory

**Change:**
- Create helper method `_get_setting(namespace, key, default)`
- Replace all `self.settings.X.Y` with SettingsManager calls
- Add settings to SettingsManager schemas if missing (device, storage, tensorzero, local_llm, conversation, skills)
- Remove `settings: Settings` constructor parameter

**Estimated Effort:** High (30+ accessor replacements)

---

### 4. Legacy Settings Dialog

**File:** [ui/qt/settings_dialog.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/settings_dialog.py)

**Change:**
- Delete file if new schema-driven SettingsDialog is complete
- Or migrate to use SettingsManager

---

### 5. Voice Interface Migration

**File:** [ui/voice_interface/voice_interface.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/voice_interface/voice_interface.py)

**Current:** Uses `get_settings()` for hub config.

**Change:**
- Accept SettingsManager in constructor
- Replace `get_settings()` calls with SettingsManager lookups
- Remove `from ...config import get_settings`

---

## Schema Additions Required

Before MainWindow can be migrated, these namespaces need schemas:

| Namespace | Fields Needed |
|-----------|---------------|
| `device` | `name` |
| `storage` | `db_path` |
| `tensorzero` | `enabled` |
| `local_llm` | `model` |
| `conversation` | `max_history` |
| `ui` | `theme`, `start_minimized`, `show_waveform` |
| `skills` | `path` |

> **Note:** Some of these may already exist in `spoke_core` namespace - check [settings_schema.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/spoke_core/settings_schema.py) first.

---

## Suggested Order

1. **Add missing schemas** to `spoke_core/settings_schema.py`
2. **Migrate VoiceInterface** (small, self-contained)
3. **Migrate SpokeCore** (remove fallback)
4. **Delete legacy settings_dialog.py** if unused
5. **Migrate MainWindow** (largest, most complex)
6. **Migrate Qt App** (final step, removes load_config)
7. **Delete config/ package** or leave as empty deprecated stub

---

## Reference Documents

- [SUMMARY.md](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/SUMMARY.md) - System architecture overview
- [folder-layout.md](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/docs/plans/folder-layout.md) - Folder structure reference
- [settings/README.md](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/docs/plans/settings/README.md) - SettingsManager design
- [settings/settings-manager.md](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/docs/plans/settings/settings-manager.md) - SettingsManager API details
- [settings/settings-ui.md](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/docs/plans/settings/settings-ui.md) - Settings UI patterns

---

## Testing Strategy

After each migration step:
1. Run `strawberry-test -qq` 
2. Run `ruff check --fix`
3. Manual test affected UI (Qt app, CLI, or voice interface)

Final verification:
- Ensure no remaining imports from `strawberry.config`
- All tests pass
- Qt, CLI, and VoiceInterface all work correctly
