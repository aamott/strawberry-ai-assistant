---
description: Plan for completing migration from old config/ module to SettingsManager
---

# Settings Migration: Phase 5 - ✅ COMPLETE

> **Status:** Migration complete as of 2025-01-24. All core files now use SettingsManager exclusively.

## Completed Work

| Task | Status |
|------|--------|
| Add missing schemas to `spoke_core/settings_schema.py` | ✅ Done |
| Migrate VoiceInterface | ✅ Done |
| Migrate SpokeCore (remove fallback) | ✅ Done |  
| Migrate MainWindow | ✅ Done |
| Migrate Qt App (remove load_config) | ✅ Done |

### Files Migrated

- [spoke_core/app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/spoke_core/app.py) - No longer imports from `config`, creates SettingsManager internally
- [ui/qt/app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/app.py) - Removed `load_config()`, uses SettingsManager only
- [ui/qt/main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py) - Added `_get_setting()` helper, replaced all `self.settings` refs
- [ui/voice_interface/voice_interface.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/voice_interface/voice_interface.py) - Removed `get_settings()` fallback

## Schema Additions Made

Added 9 fields to `SPOKE_CORE_SCHEMA`:
- `skills.path`, `storage.db_path`, `tensorzero.enabled`
- `llm.temperature`, `conversation.max_history`
- `ui.theme`, `ui.start_minimized`, `ui.show_waveform`

## Deprecated (Still Present)

| File | Status |
|------|--------|
| `ui/qt/settings_dialog.py` | No longer imported - can be deleted |
| `config/` package | Deprecated with runtime warnings |

## Verification

All tests pass:
- `pytest tests/test_settings_manager.py` ✅
- `pytest tests/test_core_settings.py` ✅
- `ruff check --fix` ✅

