# SettingsManager Improvements Plan

Review findings from 2026-02-03 session. Each item addresses a bug or improvement identified in `ai-pc-spoke/src/strawberry/shared/settings/`.

## TODO

- [x] **High: Fix save() secret serialization** — `str(value) if value else ""` collapses `0`, `False`, `""` into `""` ✅ Fixed 2026-02-03
- [x] **Medium: Index schema fields by key** — `get_field()` is O(n); add `schema_by_key` dict ✅ Fixed 2026-02-03
- [x] **Medium: Snapshot listener list during emit** — `_emit_change()` / `end_batch()` iterate directly ✅ Fixed 2026-02-03
- [x] **Low: Log exceptions in SettingsViewModel._on_external_change** — currently swallowed silently ✅ Fixed 2026-02-03

---

## 1. High: save() secret serialization

**File:** `manager.py` → `save()`

**Problem:**
```python
env_values[env_key] = str(value) if value else ""
```
This treats `0`, `False`, and empty string as falsey, collapsing them all to `""`.

**Fix:**
```python
env_values[env_key] = "" if value is None else str(value)
```

---

## 2. Medium: Index schema fields by key

**File:** `manager.py` → `register()`, `get_field()`

**Problem:**
`get_field()` iterates the schema list on every call — O(n) per lookup.

**Fix:**
- Add `schema_by_key: Dict[str, SettingField]` to `RegisteredNamespace`
- Build index once in `register()`
- Use dict lookup in `get_field()`

---

## 3. Medium: Snapshot listener list during emit

**File:** `manager.py` → `_emit_change()`, `end_batch()`

**Problem:**
If a listener mutates `self._listeners` during iteration, behavior is undefined.

**Fix:**
```python
for listener in list(self._listeners):
```

---

## 4. Low: Log exceptions in SettingsViewModel

**File:** `view_model.py` → `_on_external_change()`

**Problem:**
Exceptions are swallowed with `except Exception: pass`.

**Fix:**
```python
except Exception as e:
    logger.warning(f"Settings refresh callback error: {e}")
```

---

## Verification

After each fix:
1. `ruff check --fix .`
2. `pytest -qq`
3. Manual: `test_cli` interaction
4. Manual: `voice_interface.py` VoiceCore load
