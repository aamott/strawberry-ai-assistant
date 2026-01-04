"""Shared contracts and utilities for Hub and Spoke.

This module provides:
- Common Pydantic models for API payloads
- Device name normalization
- Timeout constants
- Error types

Both Hub (ai-hub) and Spoke (ai-pc-spoke) should import from this module
to ensure consistent contracts.
"""

from .contracts import (
    SkillInfo,
    SkillSearchResult,
    SkillExecuteRequest,
    SkillExecuteResponse,
    DeviceInfo,
)
from .normalization import normalize_device_name
from .timeouts import Timeouts
from .errors import (
    SkillNotFoundError,
    DeviceNotFoundError,
    SkillExecutionError,
    DeviceOfflineError,
)

__all__ = [
    # Contracts
    "SkillInfo",
    "SkillSearchResult",
    "SkillExecuteRequest",
    "SkillExecuteResponse",
    "DeviceInfo",
    # Normalization
    "normalize_device_name",
    # Timeouts
    "Timeouts",
    # Errors
    "SkillNotFoundError",
    "DeviceNotFoundError",
    "SkillExecutionError",
    "DeviceOfflineError",
]
