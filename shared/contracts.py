"""Shared Pydantic models for Hub/Spoke API contracts.

These models define the canonical schema for:
- Skill registration and discovery
- Remote skill execution
- Device information

Both Hub and Spoke should use these models to ensure payload compatibility.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SkillInfo(BaseModel):
    """Skill information for registration.

    Used when Spoke registers its skills with the Hub.
    """

    class_name: str
    function_name: str
    signature: str
    docstring: Optional[str] = None


class SkillSearchResult(BaseModel):
    """Result from skill search, grouped by (class, method, signature).

    Skills are grouped so the LLM sees one entry per unique skill,
    with a list of devices that have that skill.
    """

    path: str = Field(description="SkillClass.method (without device prefix)")
    signature: str = Field(description="Full function signature")
    summary: str = Field(description="First line of docstring")
    docstring: str = Field(default="", description="Full docstring")
    devices: List[str] = Field(
        default_factory=list, description="Normalized device names (sample)"
    )
    device_names: List[str] = Field(
        default_factory=list, description="Display names (sample)"
    )
    device_count: int = Field(default=0, description="Total devices with this skill")
    is_local: bool = Field(default=False, description="True if on local device")


class SkillExecuteRequest(BaseModel):
    """Request to execute a skill on a remote device.

    Used for Hub POST /skills/execute and WebSocket skill_request messages.
    """

    device_name: str = Field(description="Target device (normalized name)")
    skill_name: str = Field(description="Skill class name")
    method_name: str = Field(description="Method to call")
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)


class SkillExecuteResponse(BaseModel):
    """Response from remote skill execution.

    Used for Hub skill execution responses and WebSocket skill_response messages.
    """

    success: bool
    result: Any = None
    error: Optional[str] = None
    device: Optional[str] = None


class DeviceInfo(BaseModel):
    """Public device information for discovery.

    Used in device list responses and skill search results.
    """

    id: str
    name: str
    normalized_name: str = Field(description="Normalized name for routing")
    is_active: bool = True
    last_seen: Optional[datetime] = None


class SkillRegisterRequest(BaseModel):
    """Request to register skills from a device."""

    skills: List[SkillInfo]


class SkillSearchResponse(BaseModel):
    """Response from skill search endpoint."""

    results: List[SkillSearchResult]
    total: int
