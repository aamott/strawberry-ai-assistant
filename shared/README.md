# Shared Contracts

Common contracts, utilities, and constants shared between Hub and Spoke.

## Purpose

This module provides a **single source of truth** for:
- API payload schemas (Pydantic models)
- Device name normalization
- Timeout constants
- Error types

By importing from `shared`, both Hub and Spoke guarantee compatible contracts.

## Usage

```python
# In Hub or Spoke code
import sys
sys.path.insert(0, "/path/to/capstone-v2")  # Or configure PYTHONPATH

from shared import (
    SkillSearchResult,
    SkillExecuteRequest,
    normalize_device_name,
    Timeouts,
    DeviceOfflineError,
)

# Use shared models
result = SkillSearchResult(
    path="MusicSkill.play",
    signature="play(song: str) -> bool",
    summary="Play a song",
    devices=["living_room_pc"],
    device_count=1,
)

# Use shared normalization
normalized = normalize_device_name("Living Room PC")  # -> "living_room_pc"

# Use shared timeouts
timeout = Timeouts.REMOTE_SKILL_CALL  # 30.0 seconds

# Validate timeout hierarchy
assert Timeouts.validate()  # Ensures SANDBOX < LOCAL < REMOTE < UI
```

## Modules

### `contracts.py`
Pydantic models for API payloads:
- `SkillInfo` - Skill registration
- `SkillSearchResult` - Grouped skill search results
- `SkillExecuteRequest` - Remote skill execution request
- `SkillExecuteResponse` - Execution result
- `DeviceInfo` - Device information

### `normalization.py`
- `normalize_device_name(name)` - Convert display name to routing name

### `timeouts.py`
- `Timeouts` - Centralized timeout configuration
  - `SANDBOX_EXECUTION` - 5s (hard-kill)
  - `LOCAL_SKILL_CALL` - 10s
  - `REMOTE_SKILL_CALL` - 30s
  - `UI_RESPONSE` - 60s
  - And more...

### `errors.py`
Custom exception types:
- `SkillNotFoundError` - 404
- `DeviceNotFoundError` - 404
- `DeviceOfflineError` - 503
- `SkillExecutionError` - 500
- `TimeoutError` - 504

## Integration

Both `ai-hub` and `ai-pc-spoke` should add the project root to their Python path
to import from `shared`. This can be done via:

1. **pyproject.toml** - Add `shared` as a local dependency
2. **PYTHONPATH** - Set environment variable
3. **sys.path** - Programmatically at runtime
