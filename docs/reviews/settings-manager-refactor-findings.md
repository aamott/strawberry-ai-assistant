# Settings Manager Refactor Findings

This document summarizes findings from the review and refactoring of `ai-pc-spoke/src/strawberry/shared/settings/manager.py` and related files.

## Changes Made

### High-Priority Bug Fixes

1. **`get()` treating `None` as unset** (manager.py)
   - Changed from `if value is None:` to `if key not in ns_values:`
   - Now correctly allows `None` as a valid stored value

2. **Env loading timing bug** (manager.py)
   - `_load()` was called in `__init__` before any namespaces were registered
   - `env_key_to_namespace()` returned `(None, "")` for all env keys because `known_namespaces` was empty
   - **Fix**: Added `_apply_env_overlay()` method called in `register()` to re-apply env values after namespace registration

3. **Fragile async detection** (manager.py)
   - Changed from `hasattr(result, "__await__")` to `inspect.isawaitable(result)`
   - More robust for all awaitable types

### Medium-Priority Improvements

4. **Schema field indexing** (manager.py)
   - Added `schema_by_key: Dict[str, SettingField]` to `RegisteredNamespace`
   - `get_field()` now uses O(1) dictionary lookup instead of O(n) list iteration
   - Index built once during `register()`

5. **Extracted `_apply_defaults()` helper** (manager.py)
   - Centralized default-application logic used in both `register()` and `reload()`
   - Reduces code duplication and drift risk

6. **Listener snapshot during emit** (manager.py, view_model.py)
   - Changed `for listener in self._listeners:` to `for listener in list(self._listeners):`
   - Prevents issues if a listener modifies the listener list during iteration

### Low-Priority Fixes

7. **Safer secrets serialization** (manager.py)
   - Changed from `str(value) if value else ""` to `"" if value is None else str(value)`
   - Now preserves `0`, `False`, and empty string correctly

8. **Documented `unregister()` behavior** (manager.py)
   - Added note that action handlers and option providers are not removed

9. **Fixed loop variable shadowing** (manager.py)
   - Renamed `field` loop variables to `schema_field` to avoid shadowing `dataclasses.field` import

---

## Critical Bug Fixes (Session 2)

These bugs were causing the hub token to be reset on every startup:

### manager.py

10. **`save()` and `_save_key()` overwrote .env with empty values**
    - Empty/None secrets were being saved to .env, overwriting existing tokens
    - **Fix**: Only save non-empty secrets (`if value is not None and value != ""`)

11. **`reload()` missing `_apply_env_overlay()` call**
    - After reload, secrets with custom `env_key` weren't loaded from os.environ
    - **Fix**: Added `_apply_env_overlay(ns.name)` call in reload loop

### storage.py

12. **`EnvStorage.save()` deleted keys not in data dict**
    - Keys in .env but not in `data` were removed instead of preserved
    - Combined with fix #10, this deleted the hub token entirely
    - **Fix**: Preserve existing keys that aren't in the data dict

### view_model.py

13. **`_on_external_change()` silently swallowed exceptions**
    - Errors in refresh callbacks were ignored with `except Exception: pass`
    - **Fix**: Added logging: `logger.warning(f"Settings refresh callback error: {e}")`

---

## Storage.py Refactors Implemented

These improvements were made to `storage.py`:

1. **EnvStorage.save() now preserves comments and ALL existing keys**
   - Reads existing file and preserves comments, blank lines, and existing keys
   - Only updates keys that are in the data dict; preserves everything else
   - New keys are appended at the end

2. **Added `exists()` method to both storage classes**
   - Convenient way to check if storage file exists

3. **Added debug logging for unmatched env keys**
   - `env_key_to_namespace()` now logs at debug level when env keys don't match any known namespace
   - Helps troubleshoot env loading issues

4. **Fixed edge case in quote parsing**
   - Added length check (`len(value) >= 2`) before attempting to strip quotes
   - Prevents index errors on single-character values

---

## Remaining Considerations

These items were identified but **not changed** to avoid breaking external interfaces or requiring larger architectural changes.

### storage.py

1. **YamlStorage.set() does load-modify-save cycle**
   - Each individual `set()` call reads and writes the entire file
   - Not a problem with `auto_save=True` (uses `_save_key`), but `save()` is efficient for batch updates
   - **Recommendation**: Could add batching support if performance becomes an issue

### Architecture Considerations

2. **Dual storage systems**
   - `config/env_file.py` and `config/yaml_file.py` exist alongside `shared/settings/storage.py`
   - Memory `6cfa79a5` notes these were added for UI persistence
   - **Recommendation**: Consider consolidating into a single storage abstraction

3. **Partial update atomicity in `update()`**
   - `update()` applies changes per-key; partial success is possible
   - This is documented but could be surprising
   - **Recommendation**: Add explicit docstring note: "Updates are applied per-key; partial success is possible."

4. **Options providers not removed on unregister**
   - `_action_handlers` and `_options_providers` remain after namespace unregistration
   - Not a bug (they use composite keys), but could cause memory leaks in long-running apps
   - **Recommendation**: If dynamic namespace registration/unregistration becomes common, add cleanup

---

## Files Modified

- `ai-pc-spoke/src/strawberry/shared/settings/manager.py` - Bug fixes and improvements
- `ai-pc-spoke/src/strawberry/shared/settings/view_model.py` - Listener snapshot fix
- `ai-pc-spoke/src/strawberry/shared/settings/storage.py` - Comment preservation, debug logging, edge case fixes

## Tests Verified

All settings-related tests pass:
- `tests/test_settings_manager.py` - 38 tests
- `tests/test_settings_schema.py` - Included in above
- `tests/test_core_settings.py` - 18 tests
- `tests/test_schema_settings_widget.py` - Included in above
