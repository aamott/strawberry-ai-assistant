# Spoke Architecture Review

Observations gathered during the McCabe complexity reduction effort (C901 refactoring).
Each finding includes a priority, difficulty estimate, and suggested action.

---

## Getting Started

### Context

This review was created after refactoring the `ai-pc-spoke` codebase to reduce McCabe complexity (C901 errors). During that work, several architectural patterns emerged that warrant attention — primarily around code duplication, god classes, and inconsistent abstractions. Hopefully while implementing this we can reduce lines of code and improve maintainability.

### Key Files to Review First

Before tackling any finding, familiarize yourself with these core modules:

1. **[SUMMARY.md](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/SUMMARY.md)** — High-level architecture overview of the entire project (Hub + Spoke)
2. **[ai-pc-spoke/README.md](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/README.md)** — Spoke-specific quick start, structure, and testing
3. **[skills/service.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/skills/service.py)** (1820 lines) — The largest module, central to findings #1 and #2
4. **[spoke_core/app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/spoke_core/app.py)** (664 lines) — Main UI entrypoint, relevant to finding #6

### Workflow for Implementing Findings

1. **Pick a finding** — Start with High priority items or Low difficulty ones for quick wins
2. **Read the applicable files** — Use `view_file_outline` to understand structure before diving into details
3. **Create an implementation plan** — Document your approach in `docs/plans/` before making changes
4. **Run tests** — Use `pytest -qq` to verify no regressions after changes
5. **Run ruff** — Use `.venv/bin/ruff check --fix` to maintain code quality

### Testing

- **Run all tests:** `pytest tests/ -qq`
- **Run specific test:** `pytest tests/test_skills.py -qq`
- **Check complexity:** `ruff check --select C901 src/strawberry/`

### Project Structure

```
ai-pc-spoke/src/strawberry/
├── skills/          # Skill loading, sandbox, proxies (findings #1, #2, #3)
├── spoke_core/      # SpokeCore entrypoint (finding #6)
├── ui/              # CLI, Qt, test_cli (finding #4)
├── shared/settings/ # Settings manager, schema, view model (finding #4)
├── testing/         # Test runner (finding #5)
└── voice/           # Voice processing (finding #7)
```

---

## 1. `service.py` is a God Class (1820 lines, 85 symbols)

- [x] **Title:** Split `SkillService` and proxy classes out of `skills/service.py`
  - **Priority:** High
  - **Difficulty:** Medium
  - **Applicable Filepaths:** `ai-pc-spoke/src/strawberry/skills/service.py`
  - **Status:** ✅ Complete
  - **What was done:**
    - Created `skills/proxies.py` — All proxy classes (`DeviceProxy`, `SkillProxy`, `DeviceManagerProxy`, `LocalDeviceSkillsProxy`, `RemoteDeviceProxy`, `RemoteSkillProxy`), `SkillCallResult`, `normalize_device_name`, `_SEARCH_STOP_WORDS`
    - Created `skills/prompt.py` — `DEFAULT_SYSTEM_PROMPT_TEMPLATE`, `build_system_prompt()`, `build_example_call()`, `_placeholder_for_type()`
    - Created `skills/tool_dispatch.py` — `_ERROR_HINTS`, `enrich_exec_error()`, `format_search_results()`
    - Slimmed `skills/service.py` from ~1820 lines to ~1020 lines — now lifecycle + orchestration only, imports from new modules
    - Backward compatibility preserved via re-exports in `service.py` (`SkillCallResult`, `normalize_device_name`, `DEFAULT_SYSTEM_PROMPT_TEMPLATE`)
    - All tests pass, ruff clean

---

## 2. Duplicated Proxy Hierarchies Across Three Modules

- [x] **Title:** Unify the proxy class hierarchy for skill access
  - **Priority:** High
  - **Difficulty:** Medium-High
  - **Applicable Filepaths:**
    - `skills/proxies.py` — canonical `DeviceProxy`, `SkillProxy` (local device access)
    - `skills/sandbox/executor.py` — now imports `DeviceProxy` from proxies.py
    - `skills/remote.py` — canonical `DeviceManager` hierarchy (remote/Hub access)
  - **Status:** ✅ Complete
  - **What was done:**
    - Eliminated `_DirectSkillProxy` and `_DirectDeviceProxy` from `executor.py` — sandbox fallback now uses `DeviceProxy` from `proxies.py`
    - Removed orphaned `DeviceManagerProxy`, `LocalDeviceSkillsProxy`, `RemoteDeviceProxy`, `RemoteSkillProxy` from `proxies.py` — these duplicated `remote.py`'s `DeviceManager` hierarchy and were never used at runtime
    - Result: two canonical proxy paths — `proxies.DeviceProxy` (local) and `remote.DeviceManager` (Hub/remote)
    - Updated test mock fixtures to wire `call_method` for the unified `SkillProxy`
    - All tests pass, ruff clean, live test_cli verified

---

## 3. Dead / Unreachable Code in `_RemoteSkillProxy`

- [x] **Title:** Remove dead code and fix inconsistent async handling in `_RemoteSkillProxy`
  - **Priority:** Medium
  - **Difficulty:** Low
  - **Applicable Filepaths:** `skills/proxies.py` (formerly `skills/service.py`)
  - **Status:** ✅ Complete (resolved as part of Finding #2)
  - **What was done:**
    - The entire `RemoteSkillProxy` class (with its dead `if False:` block and `NotImplementedError`) was removed from `proxies.py` during Finding #2's cleanup of orphaned proxy classes
    - Remote skill calls now exclusively use `remote.py`'s `DeviceManager` → `RemoteDeviceProxy` → `RemoteSkillClassProxy` → `RemoteSkillProxy` chain, which has proper sync/async bridging via `_run_async()`

---

## 4. Settings UI Implemented Three Times in Parallel

- [x] **Title:** Extract a shared settings editing controller
  - **Priority:** Medium
  - **Difficulty:** Medium
  - **Applicable Filepaths:**
    - `shared/settings/editor.py` (new)
    - `ui/cli/settings_menu.py`
    - `ui/test_cli/settings_cli.py`
  - **Status:** ✅ Complete
  - **What was done:**
    - Created `shared/settings/editor.py` with:
      - `format_field_value(field, value)` — single source of truth for value rendering across all UIs
      - `PendingChangeController` — manages buffered changes with validate/apply/discard/reset
      - List helpers: `list_add`, `list_remove`, `list_move_up`, `list_move_down`
      - `get_available_options(settings, field, current_items)` — shared option discovery
    - Refactored `settings_cli.py` (567→452 lines): replaced duplicated `_render_field_value`, `_format_range`, `set_value`/`apply_changes`/`discard_changes`/`reset_field`/`has_pending_changes`/`get_pending_count`/`_get_available_options` with shared editor
    - Refactored `settings_menu.py`: `_format_value` now delegates to shared `format_field_value`
    - Exported new symbols from `shared/settings/__init__.py`
    - All settings tests pass, ruff clean, live test_cli verified

---

## 5. `testing/runner.py` Mixes CLI Argument Parsing with Execution Logic

- [x] **Title:** Separate argument parsing from execution in `runner.py`
  - **Priority:** Low
  - **Difficulty:** Low
  - **Applicable Filepaths:** `ai-pc-spoke/src/strawberry/testing/runner.py`
  - **Status:** ✅ Complete
  - **What was done:**
    - Created `@dataclass RunnerConfig` with typed fields for all CLI options (log reader, search, test-run)
    - `main()` populates `RunnerConfig` once from argparse, then passes it to all `_cmd_*` handlers
    - Eliminated all inline `int()`/`bool()` casts from `_cmd_failures`, `_cmd_show_failure`, `_cmd_tail_log`, `_cmd_test`, `_cmd_grep`, `_cmd_run_tests`
    - `from_line`/`to_line` converted to `Optional[int]` in config (removed `_parse_line_range` helper)
    - Ruff clean

---

## 6. `SpokeCore` Owns Too Many Responsibilities

- [x] **Title:** Extract event routing and skill management from `SpokeCore`
  - **Priority:** Medium
  - **Difficulty:** Medium
  - **Applicable Filepaths:**
    - `spoke_core/skill_manager.py` (new)
    - `spoke_core/app.py`
  - **Status:** ✅ Complete
  - **What was done:**
    - Created `spoke_core/skill_manager.py` — `SkillManager` facade wrapping `SkillService` with event emission
      - Owns: skill loading (`load_and_emit`), shutdown, summaries, load failures, enable/disable with event broadcast, system prompt access
      - Owns: deterministic tool hooks (`run_deterministic_hooks`, `_run_search_skills_hook`, `_run_python_exec_hook`) — extracted from the 130-line `send_message`
    - Refactored `app.py`:
      - `self._skills: SkillService` → `self._skill_mgr: SkillManager`
      - `send_message` reduced from ~130 lines to ~30 lines — deterministic hooks delegated to `SkillManager`
      - Skill query methods (`get_skill_summaries`, `get_skill_load_failures`, `set_skill_enabled`, `get_system_prompt`) now delegate to `SkillManager`
      - Backward-compatible `skill_service` property returns `skill_mgr.service`
    - All tests pass, ruff clean, live test_cli verified

---

## 7. Inconsistent Event Loop Bridging Patterns

- [x] **Title:** Standardize async-to-sync bridging across modules
  - **Priority:** Low
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - `utils/async_bridge.py` (new)
    - `skills/remote.py`
    - `voice/voice_core.py`
  - **Status:** ✅ Complete
  - **What was done:**
    - Created `utils/async_bridge.py` with two shared utilities:
      - `run_sync(coro, timeout=30)` — run async from sync; auto-detects loop, offloads to thread pool if needed
      - `schedule_on_loop(coro, loop, timeout=None)` — schedule on a specific loop from a worker thread
    - Refactored `skills/remote.py`: replaced private `_run_async()` + local `_executor` + `TypeVar` with `run_sync` import
    - Refactored `voice/voice_core.py`: replaced two inline `asyncio.run_coroutine_threadsafe()` calls with `schedule_on_loop`
    - The third pattern (`_RemoteSkillProxy.method_wrapper` in old `service.py`) was already removed in Finding #2/#3
    - All tests pass, ruff clean, live test_cli verified

---

## 8. Long Literal Blocks Driving Lint Noise

- [x] **Title:** Centralize long literal data to avoid E501 churn
  - **Priority:** Low
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - `skills/internet_skill/skill.py` and `skills/_legacy/internet_skill.py`
    - Tests with long f-strings and comments
  - **Status:** ✅ Already resolved
  - **What was done:**
    - All E501 violations were already fixed in a prior refactoring pass (Ruff E501 + C901 cleanup)
    - `ruff check --select E501 src/ tests/` passes clean — no remaining long-literal issues
    - No further action needed

---

## 9. Media Control Dispatch Duplicated and Imperative

- [x] **Title:** Share a small media-command dispatcher across platforms and legacy
  - **Priority:** Medium
  - **Difficulty:** Low-Medium
  - **Applicable Filepaths:**
    - `skills/media_control_skill/media_dispatch.py` (new)
    - `skills/media_control_skill/skill.py`
    - `skills/_legacy/media_control_skill.py`
  - **Status:** ✅ Complete
  - **What was done:**
    - Created `skills/media_control_skill/media_dispatch.py` — shared dispatcher with:
      - `send_media_command(command, macos_app="Spotify")` — routes to platform adapter
      - Platform adapters: `_send_windows`, `_send_macos`, `_send_linux`
      - Volume adapters: `set_system_volume`, `get_system_volume` with Linux (wpctl/pactl/amixer) and Windows (CoreAudio PowerShell) support
      - Dispatch tables: `WIN_MEDIA_KEYS`, `MAC_MEDIA_VERBS`
    - Refactored repo `skill.py` (372→120 lines): removed all platform-specific methods, delegates to `media_dispatch`
    - Refactored legacy `media_control_skill.py` (161→110 lines): removed duplicated dispatch tables and `_send_media_command`, imports from shared module; `get_volume` now uses real `get_system_volume` instead of hardcoded 75
    - All tests pass, ruff clean, live test_cli verified


- [x] Hanging Tests
  - **Priority:** Medium
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - `src/strawberry/llm/tensorzero_client.py`
    - `tests/test_cli_live.py`
    - `tests/test_live_chat.py`
    - `tests/test_voice_live.py`
  - **Status:** ✅ Complete
  - **Root cause:** `TensorZeroClient.close()` called `__aexit__` on the embedded Rust gateway with no timeout — the Rust runtime sometimes never exits, blocking the Python event loop indefinitely. The `core` fixture teardown in `test_cli_live.py` called `core.stop()` which cascaded through `_llm.close()`.
  - **What was done:**
    - `TensorZeroClient.close()`: added `asyncio.wait_for(..., timeout=5.0)` around the gateway `__aexit__` call; logs a warning on timeout instead of hanging
    - `test_cli_live.py`: fixture teardown now force-closes each component (`_llm`, `_skill_mgr`) individually with its own timeout; added `@pytest.mark.timeout(30-45)` to all async tests
    - `test_live_chat.py`: added `@pytest.mark.timeout(15-60)` to all async tests
    - `test_voice_live.py`: already had `@pytest.mark.timeout` — no changes needed
    - Full suite now completes without hanging: all tests pass, 8 skipped (voice + env-gated)
---

## Summary

| # | Finding | Priority | Difficulty |
|---|---|---|---|
| 1 | `service.py` god class (1820 lines) | High | Medium |
| 2 | 3× duplicated proxy hierarchies | High | Medium-High |
| 3 | Dead/unreachable code in `_RemoteSkillProxy` | Medium | Low |
| 4 | Settings UI logic implemented 3× | Medium | Medium |
| 5 | `runner.py` arg parsing mixed with execution | Low | Low |
| 6 | `SpokeCore` owns too many responsibilities | Medium | Medium |
| 7 | Inconsistent async-to-sync bridging | Low | Low |
| 8 | Long literal blocks driving lint noise | Low | Low |
| 9 | Media control dispatch duplicated/imperative | Medium | Low-Medium |
