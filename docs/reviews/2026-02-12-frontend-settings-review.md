# Frontend & Settings UI Code Review — 2026-02-12

## Scope
- `src/strawberry/ui/gui_v2/settings/` (field widgets, factory, base)
- `src/strawberry/ui/gui_v2/components/settings_window.py`
- `src/strawberry/ui/gui_v2/themes/base.py`
- `src/strawberry/ui/qt/settings/` (dialog, field widgets)
- `src/strawberry/ui/test_cli/` (settings CLI)
- Related: `shared/settings/schema.py`, `spoke_core/settings_schema.py`, `llm/tensorzero_settings.py`

---

## Findings

### Bug: Qt dialog hardcodes tab order, missing "LLM" tab
- [x] **Priority:** High
- **Difficulty:** Easy (1-line fix)
- **Type:** bug
- **File:** `src/strawberry/ui/qt/settings/dialog.py:128`
- **Description:** `tab_order = ["General", "Voice", "Skills"]` is hardcoded and doesn't include the new `"LLM"` tab. The `"LLM"` tab will sort after index 100 (alphabetically among unknowns) instead of between General and Voice. The gui_v2 `settings_window.py` uses dynamic ordering based on namespace `order` attribute — the Qt dialog should do the same.

### Cleanup: Duplicated `_INPUT_STYLE` constants across gui_v2 settings files
- [x] **Priority:** Low — **WON'T FIX**
- **Type:** refactor
- **Files:** `gui_v2/settings/field_simple.py`, `gui_v2/settings/field_advanced.py`
- **Description:** The two `_INPUT_STYLE` constants share base colors but target different widget sets (`QLineEdit/QSpinBox/QComboBox` vs `QLineEdit/QPlainTextEdit`). Extracting would require either a single bloated stylesheet or multiple partials — not worth the added complexity for the small overlap.

### Cleanup: Duplicated NoScroll widget classes across Qt and gui_v2
- [x] **Priority:** Low
- **Difficulty:** Easy
- **Type:** refactor
- **Files:** `gui_v2/settings/field_simple.py`, `qt/settings/field_widgets/simple.py`
- **Description:** Extracted `NoScrollComboBox`, `NoScrollSpinBox`, `NoScrollDoubleSpinBox` to `ui/common/widgets.py`. Both UI packages now import from the shared module.

### ~~Bug: Qt dialog `_validate_all` calls `field.validate()` which doesn't exist on `SettingField`~~
- [x] **Priority:** N/A — **INVALID FINDING**
- **Type:** false positive
- **Description:** `SettingField.validate()` does exist (line 132 of `schema.py`). It wraps numeric, select, list, and custom validation. No fix needed.

### Cleanup: gui_v2 `settings_window.py` uses f-string in `logger.exception()`
- [x] **Priority:** Low
- **Difficulty:** Easy (1-line fix)
- **Type:** logging
- **File:** `gui_v2/components/settings_window.py:435`
- **Description:** `logger.exception(f"Failed to create widget for {namespace}.{field.key}")` should use lazy formatting: `logger.exception("Failed to create widget for %s.%s", namespace, field.key)`.

### Cleanup: Qt dialog `_build_tabs` sorts by hardcoded list, gui_v2 sorts by namespace order
- [x] **Priority:** Medium
- **Difficulty:** Easy
- **Type:** consistency
- **File:** `qt/settings/dialog.py:127-131`
- **Description:** The Qt dialog uses a hardcoded `tab_order` list while gui_v2 dynamically sorts by `min(ns.order for ns in tabs[t])`. The Qt dialog should use the same dynamic approach for consistency and to automatically handle new tabs.

### Improvement: `SettingField.metadata` could have typed keys
- [ ] **Priority:** Low
- **Difficulty:** Medium
- **Type:** refactor
- **File:** `shared/settings/schema.py:112`
- **Description:** `metadata: Optional[dict[str, Any]]` is a grab-bag. Keys like `api_key_url`, `help_text`, `filter` are used by convention. A `TypedDict` or dedicated fields would improve discoverability. Low priority — the current approach is flexible and works.

### Cleanup: gui_v2 `SettingsWindow._apply_changes` uses `settings.update()` while Qt dialog uses `vm.set_value()` with batch mode
- [x] **Priority:** Low — **WON'T FIX**
- **Type:** consistency
- **File:** `gui_v2/components/settings_window.py:552-580` vs `qt/settings/dialog.py:350-362`
- **Description:** The gui_v2 dialog uses `settings.update()` which already handles multi-key updates with a single save. The Qt dialog uses `begin_batch()`/`end_batch()` with `SettingsViewModel`. Both achieve the same result — `update()` is arguably cleaner. No change needed.
