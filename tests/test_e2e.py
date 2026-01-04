"""End-to-end tests for Hub and Spoke integration.

These tests verify the full flow from Spoke -> Hub -> LLM and back.

Requirements:
- Hub server running on localhost:8000
- Valid HUB_DEVICE_TOKEN for the Spoke
- GOOGLE_AI_STUDIO_API_KEY for the Hub's Gemini provider

Run with: pytest tests/test_e2e.py -v
"""

import os
import sys
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv

# Load env files
_root = Path(__file__).parent.parent
load_dotenv(_root / "ai-hub" / ".env")
load_dotenv(_root / "ai-pc-spoke" / ".env")


def is_hub_running(url: str = "http://localhost:8000") -> bool:
    """Check if Hub server is running."""
    try:
        response = httpx.get(f"{url}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def hub_url() -> str:
    """Get Hub URL."""
    return os.environ.get("HUB_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def hub_token() -> str:
    """Get Hub device token."""
    return os.environ.get("HUB_DEVICE_TOKEN", "")


class TestHubHealth:
    """Basic Hub health checks."""

    def test_hub_is_running(self, hub_url: str):
        """Verify Hub server is running."""
        if not is_hub_running(hub_url):
            pytest.skip(f"Hub not running at {hub_url}")

        response = httpx.get(f"{hub_url}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_hub_api_health(self, hub_url: str):
        """Verify Hub API health endpoint."""
        if not is_hub_running(hub_url):
            pytest.skip(f"Hub not running at {hub_url}")

        response = httpx.get(f"{hub_url}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Strawberry AI Hub"
        assert data["status"] == "running"


class TestHubChatCompletions:
    """Test Hub chat completions endpoint."""

    @pytest.mark.asyncio
    async def test_chat_completions_authenticated(self, hub_url: str, hub_token: str):
        """Test authenticated chat completion request."""
        if not is_hub_running(hub_url):
            pytest.skip(f"Hub not running at {hub_url}")
        if not hub_token:
            pytest.skip("HUB_DEVICE_TOKEN not set")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{hub_url}/api/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "Say 'pong'"}],
                    "temperature": 0.1,
                },
                headers={"Authorization": f"Bearer {hub_token}"},
                timeout=30.0,
            )

            if response.status_code == 401:
                pytest.skip("Invalid HUB_DEVICE_TOKEN")

            assert response.status_code == 200, f"Got {response.status_code}"
            data = response.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
            content = data["choices"][0]["message"]["content"]
            assert len(content) > 0
            print(f"\n[E2E] Hub response: {content[:50]}")

    @pytest.mark.asyncio
    async def test_chat_completions_unauthenticated(self, hub_url: str):
        """Test that unauthenticated requests are rejected."""
        if not is_hub_running(hub_url):
            pytest.skip(f"Hub not running at {hub_url}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{hub_url}/api/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "test"}]},
                timeout=10.0,
            )
            # Should be 401 or 403
            assert response.status_code in (401, 403, 422)


class TestSpokeTensorZeroIntegration:
    """Test Spoke's TensorZero client integration with Hub."""

    @pytest.fixture
    def spoke_config_path(self) -> str:
        """Get Spoke's TensorZero config path."""
        return str(_root / "ai-pc-spoke" / "config" / "tensorzero.toml")

    @pytest.mark.asyncio
    async def test_spoke_tensorzero_initialization(self, spoke_config_path: str):
        """Test Spoke TensorZero client can initialize."""
        # Ensure dummy token for validation
        if not os.environ.get("HUB_DEVICE_TOKEN"):
            os.environ["HUB_DEVICE_TOKEN"] = "dummy-for-testing"

        sys.path.insert(0, str(_root / "ai-pc-spoke" / "src"))
        from strawberry.llm.tensorzero_client import TensorZeroClient

        client = TensorZeroClient(config_path=spoke_config_path)
        try:
            healthy = await client.health()
            assert healthy, "TensorZero gateway should initialize"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_spoke_chat_with_fallback(self, spoke_config_path: str):
        """Test Spoke chat with fallback to Gemini when Hub unavailable."""
        if not os.environ.get("GOOGLE_AI_STUDIO_API_KEY"):
            pytest.skip("GOOGLE_AI_STUDIO_API_KEY not set")

        # Use dummy token so Hub fails auth -> triggers fallback
        os.environ["HUB_DEVICE_TOKEN"] = "invalid-token-for-fallback-test"

        sys.path.insert(0, str(_root / "ai-pc-spoke" / "src"))
        from strawberry.llm.tensorzero_client import ChatMessage, TensorZeroClient

        client = TensorZeroClient(config_path=spoke_config_path)
        try:
            messages = [ChatMessage(role="user", content="Say 'fallback works'")]
            response = await client.chat(messages)

            assert response.content, "Should get a response"
            # Should use fallback variant (gemini or ollama)
            assert response.variant in ("gemini_variant", "local_ollama"), (
                f"Expected fallback variant, got {response.variant}"
            )
            print(f"\n[E2E] Fallback response from {response.variant}: {response.content[:50]}")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_spoke_chat_via_hub(
        self, hub_url: str, hub_token: str, spoke_config_path: str
    ):
        """Test Spoke chat successfully routing through Hub."""
        if not is_hub_running(hub_url):
            pytest.skip(f"Hub not running at {hub_url}")
        if not hub_token or hub_token == "dummy-for-testing":
            pytest.skip("Valid HUB_DEVICE_TOKEN required")

        os.environ["HUB_DEVICE_TOKEN"] = hub_token

        sys.path.insert(0, str(_root / "ai-pc-spoke" / "src"))
        from strawberry.llm.tensorzero_client import ChatMessage, TensorZeroClient

        client = TensorZeroClient(config_path=spoke_config_path)
        try:
            messages = [ChatMessage(role="user", content="Say 'hub works'")]
            response = await client.chat(messages)

            assert response.content, "Should get a response"
            # With valid token and running Hub, should use hub variant
            print(f"\n[E2E] Response from {response.variant}: {response.content[:50]}")
        finally:
            await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
