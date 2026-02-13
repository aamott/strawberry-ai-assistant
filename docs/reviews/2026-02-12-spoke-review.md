# Spoke Review (2026-02-12)

## Findings

- [ ] Title: Persisted device ID uses incorrect config directory  
  Type: bug  
  Priority: high  
  Difficulty: medium  
  Applicable: ai-pc-spoke/src/strawberry/spoke_core/hub_connection_manager.py  
  Description: `_config_dir()` derives the config path using `Path(__file__).resolve().parents[3] / "config"`, which resolves to `.../src/config` instead of the real `ai-pc-spoke/config` directory. This means `.device_id` persistence writes to the wrong folder, so device IDs are not reused across restarts (or are reused inconsistently). Use the project root (parents[4]) or `get_project_root()` to ensure the file lands in `ai-pc-spoke/config`.

- [ ] Title: Settings migrations mark schema version as updated even after a failure  
  Type: bug  
  Priority: medium  
  Difficulty: medium  
  Applicable: ai-pc-spoke/src/strawberry/shared/settings/manager.py  
  Description: `_run_migrations()` sets the stored schema version to the target version unconditionally even if a migration raises and the loop breaks. This can leave settings in a partially migrated state while preventing retries on the next startup. Track migration success and only update the stored version when all steps succeed (or persist the last successful version).

- [ ] Title: GUI settings window reaches into private SettingsManager internals  
  Type: refactor  
  Priority: low  
  Difficulty: medium  
  Applicable: ai-pc-spoke/src/strawberry/ui/gui_v2/components/settings_window.py  
  Description: `_build_field_widget()` accesses `self._settings._action_handlers` directly to wire ACTION handlers. This bypasses the SettingsManager API and risks breakage if internals change. Add a public accessor (e.g., `get_action_handler(namespace, action)`) and update the GUI settings window to use it.

