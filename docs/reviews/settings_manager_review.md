# Settings Manager Review

Review of `ai-pc-spoke/src/strawberry/shared/settings/manager.py`.

## High Priority (Real Issues)

- [x] **Bug: `get()` treats `None` as "unset"** - If a valid setting value is `None`, it will incorrectly fall back to schema/default. Fix: use `if key not in ns_values` instead of `if value is None`.

- [x] **Bug: env overlay happens before namespaces are registered** - In `__init__`, `_load()` uses `env_key_to_namespace` with an empty `_namespaces`. Secrets from `.env` may be ignored until `reload()`. Fix: Re-apply env overlay inside `register()`.

- [x] **Bug: async detection is fragile** - `hasattr(result, "__await__")` is not correct for all awaitables. Fix: Use `inspect.isawaitable(result)` instead.

## Medium Priority (Safe Improvements)

- [ ] **Index schema fields by key** - Repeatedly doing O(n) lookups via `for field in schema; if field.key == key`. Add `schema_by_key: Dict[str, SettingField]` to `RegisteredNamespace` for O(1) lookups.

- [ ] **Extract "apply defaults" into a helper** - Duplicated logic for applying defaults in `register()` and `reload()`. Extract to `_apply_defaults()` method.

- [ ] **Snapshot listeners during emit** - Currently iterating over `self._listeners` directly. If a listener mutates the list, behavior is undefined. Fix: `for listener in list(self._listeners)`.

## Low Priority / Optional

- [ ] **Safer env value serialization** - `str(value) if value else ""` collapses `None`, `""`, `0`, `False` into `""`. Fix: `"" if value is None else str(value)`.

- [ ] **Comment around `unregister()` behavior** - Note that action handlers and option providers are not removed.

- [ ] **Centralize "namespace:key" string construction** - Extract `_action_key()` helper for consistency.

## Notes for Larger Refactors

Document any findings here that require changes to modules outside of `manager.py`.
