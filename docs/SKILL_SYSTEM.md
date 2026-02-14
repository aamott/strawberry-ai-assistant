# Skill System (Developer Overview)

This document is for developers working on Strawberry core (Spoke/Hub internals).
It summarizes the skill lifecycle, data contracts, and routing behavior.

## Core Concepts

- **Spoke** owns skill code and executes skill methods locally.
- **Hub** is a coordinator that indexes skill methods across user devices and routes calls.
- **LLM tool loop** uses three tools:
  - `search_skills(query)`
  - `describe_function(path)`
  - `python_exec(code)`

The model does not execute skill methods directly; it generates Python that calls proxy
objects (`device` or `devices`) and runs that code through `python_exec`.

## Main Components

- Spoke loader: `ai-pc-spoke/src/strawberry/skills/loader.py`
  - Discovers classes ending in `Skill`
  - Exposes public methods (non-underscore)
  - Builds registration payload for Hub
- Spoke service: `ai-pc-spoke/src/strawberry/skills/service.py`
  - Registers skill methods with Hub
  - Maintains heartbeat loop
- Hub endpoints: `ai-hub/src/hub/routers/skills.py`
  - Register, heartbeat, list, search, execute APIs
- Hub routing/proxy: `ai-hub/src/hub/skill_service.py`
  - Implements `search_skills`, `describe_function`, and skill execution routing
- Hub persistence: `ai-hub/src/hub/database.py`
  - `Skill` rows are the canonical cross-device index

## Lifecycle

1. **Discover** (Spoke startup)
   - Loader scans skill files/repo entrypoints.
   - Builds `SkillInfo` + method signatures/docstrings.
2. **Register** (Spoke -> Hub)
   - Spoke posts flattened method rows to `/skills/register`.
   - Hub replaces existing rows for that device.
3. **Heartbeat**
   - Spoke posts `/skills/heartbeat` periodically.
   - Hub updates `last_heartbeat` for that device's skill rows.
4. **Search / Describe**
   - Hub reads non-expired rows and returns grouped skill metadata.
5. **Execute**
   - `python_exec` code calls `devices.<key>.<Skill>.<method>(...)`.
   - Hub routes via WebSocket to a target spoke and returns the result.

## Data Contract (Hub Skill Row)

Each registered method row stores:

- `device_id`
- `class_name`
- `function_name`
- `signature`
- `docstring`
- `device_agnostic` (bool)
- `last_heartbeat`

`device_agnostic` is declared by skill authors as a class attribute on the spoke skill
class and forwarded in registration payloads.

## Namespaces Seen by the LLM

- **Local mode (no hub):** `device.<SkillClass>.<method>(...)`
- **Online mode (hub):** `devices.<device_key>.<SkillClass>.<method>(...)`
- **Device-agnostic virtual key:** `devices.hub.<SkillClass>.<method>(...)`

For device-agnostic skills, `search_skills` intentionally surfaces only `hub` as the
device key, so device selection stays internal to hub routing.

## Device-Agnostic Routing

When executing `devices.hub.<Skill>.<method>`:

1. Hub queries matching `Skill` rows with `device_agnostic=True` and non-expired heartbeat.
2. Candidates are sorted by most recent `last_heartbeat`.
3. Only connected devices are attempted.
4. Hub tries devices sequentially until one succeeds.
5. If all fail, a combined error is returned.

Non-device-agnostic calls still route to an explicit device key.

## Expiry and Connectivity

- Skill rows are filtered by `skill_expiry_seconds` (config).
- Connected status comes from active WebSocket device sessions.
- Heartbeat freshness determines selection order for device-agnostic failover.

## Security Model

- Skill implementations are trusted local Python code (not sandboxed by Pyodide).
- Pyodide/Deno sandbox protects LLM-generated Python execution, not skill code.
- Installing a skill is equivalent to running local plugin code.

## Common Extension Points

- Add metadata to registration payload:
  - Spoke `SkillInfo` / `get_registration_data()`
  - Hub `SkillInfo` pydantic model + DB column
- Change search ranking/grouping:
  - `DevicesProxy.search_skills()` in hub skill service
- Change failover policy:
  - `DevicesProxy.execute_skill()` and `_execute_device_agnostic_skill()`
