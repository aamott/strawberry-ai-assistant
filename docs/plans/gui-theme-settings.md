# GUI Theme & Appearance Settings Plan

## Design Decisions

**Theme file format:** YAML — consistent with `config/config.yaml`, human-readable, easy for users to edit. Each `.yaml` file in the themes folder is one theme.

**Themes directory:** `config/themes/` — next to `config.yaml` and `.env`. Built-in themes are shipped here on first run (or if missing). A `_template.yaml` file with detailed comments serves as the starting point for custom themes.

**Hot-reload:** Theme changes apply immediately when the user changes the setting — no restart required. The settings dialog uses `DYNAMIC_SELECT` populated by scanning the themes folder.

**"Open Themes Folder" button:** An ACTION field in the settings schema that opens the themes directory in the system file manager. This is how users "import" new themes — they just drop a YAML file in the folder.

**Built-in themes (4):**
- `dark.yaml` — current default (deep navy/pink accent)
- `light.yaml` — current light theme
- `midnight.yaml` — darker, muted blue tones
- `solarized_dark.yaml` — solarized color palette

**Additional UI settings to include:**
- `font_size` (NUMBER, 10–20, default 14) — base font size in px
- `start_maximized` (CHECKBOX, default false) — start the window maximized

**Settings namespace:** `gui` registered on "General" tab.

---

## Implementation Checklist

### Core theme infrastructure
- [x] Create `src/strawberry/ui/gui_v2/themes/loader.py` — YAML theme loader
  - `load_theme_from_yaml(path) -> Theme`
  - `discover_themes(themes_dir) -> dict[str, Theme]`
  - `ensure_builtin_themes(themes_dir)` — copy built-ins if missing
- [x] Create built-in YAML themes in `src/strawberry/ui/gui_v2/themes/builtin/`
  - [x] `dark.yaml`
  - [x] `light.yaml`
  - [x] `midnight.yaml`
  - [x] `solarized_dark.yaml`
  - [x] `_template.yaml` — annotated template with all fields explained

### Settings schema
- [x] Create `src/strawberry/ui/gui_v2/settings_schema.py` — GUI settings
  - `theme` — DYNAMIC_SELECT (populated from themes dir)
  - `font_size` — NUMBER (10–20, default 14)
  - `start_maximized` — CHECKBOX (default false)
  - `open_themes_folder` — ACTION (opens themes dir)
  - Register as `gui` namespace on "General" tab

### Wiring
- [x] Update `MainWindow.__init__` to read `gui.theme` and `gui.font_size` from SettingsManager
- [x] Update `MainWindow` to listen for `gui.*` setting changes and apply immediately
- [x] Register GUI schema in `app.py` entry points
- [x] Register GUI schema in CLI `__main__.py` for `--settings` mode
- [x] Populate theme options via `options_provider` (list of discovered theme names)
- [x] Wire ACTION handlers in both gui_v2 and Qt settings dialogs

### Testing & cleanup
- [x] Run ruff check — all clean
- [x] Run pytest — all pass (including 13 new theme loader tests)
- [x] Unit test: `tests/test_theme_loader.py` (13 tests)
- [x] CLI validation: `--settings list` shows gui namespace, `--settings show gui` shows all 4 fields
