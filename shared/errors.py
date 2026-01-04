"""Shared error types for Hub and Spoke.

These exceptions provide consistent error handling across the system.
Each error type maps to specific HTTP status codes and error messages.
"""


class StrawberryError(Exception):
    """Base exception for all Strawberry errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SkillNotFoundError(StrawberryError):
    """Raised when a requested skill does not exist.

    HTTP: 404 Not Found
    """

    def __init__(self, skill_path: str, available_skills: list = None):
        message = f"Skill not found: {skill_path}"
        details = {"skill_path": skill_path}
        if available_skills:
            details["available_skills"] = available_skills
            message += f". Available: {', '.join(available_skills[:5])}"
            if len(available_skills) > 5:
                message += f" (+{len(available_skills) - 5} more)"
        super().__init__(message, details)
        self.skill_path = skill_path


class DeviceNotFoundError(StrawberryError):
    """Raised when a requested device does not exist.

    HTTP: 404 Not Found
    """

    def __init__(self, device_name: str, available_devices: list = None):
        message = f"Device not found: {device_name}"
        details = {"device_name": device_name}
        if available_devices:
            details["available_devices"] = available_devices
            message += f". Available: {', '.join(available_devices[:5])}"
            if len(available_devices) > 5:
                message += f" (+{len(available_devices) - 5} more)"
        super().__init__(message, details)
        self.device_name = device_name


class DeviceOfflineError(StrawberryError):
    """Raised when a device exists but is not currently connected.

    HTTP: 503 Service Unavailable
    """

    def __init__(self, device_name: str, last_seen: str = None):
        message = f"Device is offline: {device_name}"
        details = {"device_name": device_name}
        if last_seen:
            details["last_seen"] = last_seen
            message += f" (last seen: {last_seen})"
        message += ". Try a different device or wait for it to reconnect."
        super().__init__(message, details)
        self.device_name = device_name


class SkillExecutionError(StrawberryError):
    """Raised when skill execution fails.

    HTTP: 500 Internal Server Error (or 400 if user error)
    """

    def __init__(
        self,
        skill_path: str,
        error_type: str,
        error_message: str,
        traceback: str = None,
    ):
        message = f"Skill execution failed: {skill_path} - {error_type}: {error_message}"
        details = {
            "skill_path": skill_path,
            "error_type": error_type,
            "error_message": error_message,
        }
        if traceback:
            details["traceback"] = traceback
        super().__init__(message, details)
        self.skill_path = skill_path
        self.error_type = error_type


class TimeoutError(StrawberryError):
    """Raised when an operation times out.

    HTTP: 504 Gateway Timeout
    """

    def __init__(self, operation: str, timeout_seconds: float):
        message = f"Operation timed out after {timeout_seconds}s: {operation}"
        details = {"operation": operation, "timeout_seconds": timeout_seconds}
        super().__init__(message, details)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
