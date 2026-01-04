"""Unified timeout policy for Hub, Spoke, and Sandbox.

Provides a single source of truth for all timeout values to ensure
consistent behavior across the system.

Timeout Hierarchy:
- UI timeout > Remote skill timeout > Sandbox timeout
- Each layer should have slightly shorter timeouts than its caller
  to allow proper error propagation.
"""


class Timeouts:
    """Centralized timeout configuration.

    All timeouts are in seconds.

    Usage:
        from shared import Timeouts

        # In sandbox executor
        timeout = Timeouts.SANDBOX_EXECUTION

        # In Hub skill routing
        timeout = Timeouts.REMOTE_SKILL_CALL
    """

    # Sandbox execution (LLM-generated code)
    # Hard-kill with no cleanup grace period
    SANDBOX_EXECUTION: float = 5.0

    # Individual skill call timeout (local execution)
    LOCAL_SKILL_CALL: float = 10.0

    # Remote skill call via Hub WebSocket
    # Must be > SANDBOX_EXECUTION to allow sandbox to complete
    REMOTE_SKILL_CALL: float = 30.0

    # Hub WebSocket connection timeout
    WEBSOCKET_CONNECT: float = 10.0

    # Hub WebSocket message timeout (waiting for response)
    WEBSOCKET_MESSAGE: float = 30.0

    # HTTP request timeout for Hub API calls
    HTTP_REQUEST: float = 30.0

    # Skill heartbeat interval (how often Spoke pings Hub)
    HEARTBEAT_INTERVAL: float = 60.0

    # Skill expiry (how long until Hub considers skill stale)
    # Should be > HEARTBEAT_INTERVAL * 2 to allow for missed heartbeats
    SKILL_EXPIRY: float = 180.0

    # UI response timeout (what user experiences)
    # Must be > REMOTE_SKILL_CALL to allow remote calls to complete
    UI_RESPONSE: float = 60.0

    # Bridge readline timeout (waiting for sandbox response)
    BRIDGE_READLINE: float = 60.0

    # Reconnection backoff limits
    RECONNECT_MIN_DELAY: float = 1.0
    RECONNECT_MAX_DELAY: float = 60.0

    @classmethod
    def validate(cls) -> bool:
        """Validate timeout hierarchy is correct.

        Returns True if timeouts are properly ordered:
        SANDBOX < LOCAL < REMOTE < UI
        """
        return (
            cls.SANDBOX_EXECUTION < cls.LOCAL_SKILL_CALL
            and cls.LOCAL_SKILL_CALL < cls.REMOTE_SKILL_CALL
            and cls.REMOTE_SKILL_CALL < cls.UI_RESPONSE
            and cls.HEARTBEAT_INTERVAL * 2 < cls.SKILL_EXPIRY
        )
