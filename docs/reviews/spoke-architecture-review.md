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

- [ ] **Title:** Extract a shared settings editing controller
  - **Priority:** Medium
  - **Difficulty:** Medium
  - **Applicable Filepaths:**
    - `ui/cli/settings_menu.py` (408 lines)
    - `ui/test_cli/settings_cli.py` (567 lines)
    - `ui/gui_v2/components/settings_window.py` (598 lines)
    - `shared/settings/view_model.py` (568 lines)
  - **Description:** Three UIs (CLI, test CLI, Qt GUI) each implement their own field-editing logic — type dispatching (string/int/bool/list/backend-order), validation, add/remove/reorder for lists, and rendering. The `view_model.py` in `shared/settings` was created to centralize some of this, but `settings_menu.py` and `settings_cli.py` still duplicate the core editing logic rather than deferring to it.

    **Suggested fix:** Move the "edit field by type" decision tree and list-manipulation commands into `view_model.py` (or a new `shared/settings/editor.py`). Each UI frontend then only needs to provide I/O adapters (`prompt()`, `print()`, `show_dialog()`), making the field editing logic testable independently of any UI.

---

## 5. `testing/runner.py` Mixes CLI Argument Parsing with Execution Logic

- [ ] **Title:** Separate argument parsing from execution in `runner.py`
  - **Priority:** Low
  - **Difficulty:** Low
  - **Applicable Filepaths:** `ai-pc-spoke/src/strawberry/testing/runner.py` (744 lines)
  - **Description:** After the C901 refactoring, `main()` is now cleaner, but still contains ~150 lines of `argparse` setup interleaved with dispatch logic. The subcommand handlers (`_cmd_failures`, `_cmd_grep`, etc.) accept a raw `args` namespace and type-cast fields inline (`int(args.before)`, `bool(args.fixed_strings)`). This means:
    - Every handler re-validates the same fields
    - Adding a new subcommand requires editing the monolithic `main()` parser

    **Suggested fix:** Either adopt `argparse` subcommands (one sub-parser per mode) or create a `@dataclass RunnerConfig` that `main()` populates once and passes to handlers — removing inline `int()`/`bool()` casts from every handler.

---

## 6. `SpokeCore` Owns Too Many Responsibilities

- [ ] **Title:** Extract event routing and skill management from `SpokeCore`
  - **Priority:** Medium
  - **Difficulty:** Medium
  - **Applicable Filepaths:** `spoke_core/app.py` (664 lines, 34 methods)
  - **Description:** `SpokeCore` is the "single entrypoint for all UIs" and currently handles:
    - Settings loading and change propagation
    - Hub connection management (delegated to `HubConnectionManager`, but still has `connect_hub`, `disconnect_hub`, `_schedule_hub_reconnection`)
    - Skill loading, enabling/disabling, summaries, and load failures
    - Session management (`new_session`, `get_session`)
    - The full `send_message` → agent loop pipeline (130 lines in `send_message`)
    - Event emission to listeners
    - Model info, Ollama models lookup, OAuth actions

    The `send_message` method (lines 321–449) is particularly dense — it builds system prompt, selects agent runner, runs the agent loop, handles errors, and emits events all in one chain.

    **Suggested fix:** Extract skill-related methods into a `SkillManager` facade that `SpokeCore` delegates to. Consider also moving the `send_message` → `_agent_loop` pipeline into the `AgentRunner` layer (which already exists and could own more of this flow).

---

## 7. Inconsistent Event Loop Bridging Patterns

- [ ] **Title:** Standardize async-to-sync bridging across modules
  - **Priority:** Low
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - `skills/remote.py` (`_run_async`)
    - `skills/service.py` (`_RemoteSkillProxy.method_wrapper`)
    - `voice/voice_core.py` (`asyncio.run_coroutine_threadsafe`)
  - **Description:** Three different patterns are used to call async code from sync contexts:
    1. `remote.py` has `_run_async()` which uses `run_coroutine_threadsafe` or `asyncio.run()`
    2. `service.py`'s `_RemoteSkillProxy` uses `asyncio.run()` directly (and raises `NotImplementedError` for the in-loop case)
    3. `voice_core.py` uses `asyncio.run_coroutine_threadsafe(..., loop).result()`

    Each has different error handling and thread-safety guarantees. A shared `run_sync(coro)` utility would centralize the decision and make the behavior consistent.

---

## 8. Long Literal Blocks Driving Lint Noise

- [ ] **Title:** Centralize long literal data to avoid E501 churn
  - **Priority:** Low
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - `skills/internet_skill/skill.py` and `skills/_legacy/internet_skill.py`
    - Tests with long f-strings and comments (e.g., `tests/test_voice_core.py`, `tests/test_live_chat.py`)
  - **Description:** Large inline snippets (sample search results, long URLs, verbose comments) routinely breach the 90-char limit and create recurring Ruff E501 noise. Moving these literals into small fixtures/constants (e.g., `data/` or module-level tuples) keeps code readable, shrinks functions, and prevents repeated lint fixes.

---

## 9. Media Control Dispatch Duplicated and Imperative

- [ ] **Title:** Share a small media-command dispatcher across platforms and legacy
  - **Priority:** Medium
  - **Difficulty:** Low-Medium
  - **Applicable Filepaths:**
    - `skills/media_control_skill/skill.py`
    - `skills/_legacy/media_control_skill.py`
  - **Description:** Media command handling is currently hard-coded with platform-specific branches (Windows SendKeys, macOS AppleScript, Linux playerctl) and duplicated between repo and legacy skills. Extract a shared dispatcher with per-platform adapters and typed command enums to reduce branching, improve testability, and keep legacy in sync with the primary implementation.


- [ ] Hanging Tests
  - **Priority:** Medium
  - **Difficulty:** Low
  - **Applicable Filepaths:** `test_cli_live.py`, `test_live_chat.py`, `test_voice_live.py`
  - **Description:** Some tests hang indefinitely
  - **Notes:** All tests pass. The remaining files (test_cli_live.py, test_live_chat.py, test_voice_live.py) are likely the hangers — they need live services. They should be able to skip or warn the user instead of hanging. 
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
