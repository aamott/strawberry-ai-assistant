# Strawberry AI - Testing Documentation

This document describes the testing strategy, structure, and guidelines for the Strawberry AI platform.

---

## Table of Contents

1. [Overview](#overview)
2. [Test Organization](#test-organization)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [Test Patterns](#test-patterns)
6. [Fixtures and Utilities](#fixtures-and-utilities)
7. [End-to-End Testing](#end-to-end-testing)
8. [Future Improvements](#future-improvements)

---

## Overview

### Test Statistics

- **Spoke Tests**: 18 test files, ~259 test cases
- **Hub Tests**: 3 test files, ~8 test cases
- **Test Framework**: `pytest` with `pytest-asyncio` for async support
- **Coverage**: Unit tests, integration tests, and E2E tests

### Testing Philosophy

1. **Isolated Unit Tests**: Each component tested in isolation with mocks
2. **Minimal Output**: Tests provide compact, helpful output (not massive stack traces)
3. **Fast Execution**: Tests run quickly using mocks for external dependencies
4. **Async Support**: Full support for testing async code with `pytest-asyncio`
5. **Real Backends Optional**: Tests use mocks by default; real backends can be tested separately

---

## Test Organization

### Spoke Tests (`ai-pc-spoke/tests/`)

```
tests/
├── __init__.py
├── test_audio.py              # Audio stream and backends
├── test_audio_feedback.py     # Audio feedback system
├── test_config.py             # Configuration loading and validation
├── test_hub_client.py         # Hub communication client
├── test_new_skills.py         # Skill integration tests
├── test_pipeline.py           # Conversation pipeline orchestration
├── test_remote.py             # Remote mode (DeviceManager, proxies)
├── test_sandbox.py            # Sandbox execution (Deno/Pyodide)
├── test_skills.py             # Skill loading and service
├── test_stt.py                # Speech-to-text engines
├── test_tts.py                # Text-to-speech engines
├── test_vad.py                # Voice Activity Detection
└── test_wake.py               # Wake word detection
```

### Hub Tests (`ai-hub/tests/`)

```
tests/
├── __init__.py
├── conftest.py                # Shared fixtures and setup
├── test_auth.py               # Authentication and JWT
└── test_skills.py             # Skill registry and management
```

---

## Running Tests

### Prerequisites

```bash
# Install development dependencies
cd ai-pc-spoke
pip install -e ".[dev]"

cd ai-hub
pip install -e ".[dev]"
```

### Run All Tests

```bash
# Spoke tests
cd ai-pc-spoke
pytest tests/

# Hub tests
cd ai-hub
pytest tests/
```

### Run Specific Test Files

```bash
# Test configuration system
pytest tests/test_config.py

# Test skill loading
pytest tests/test_skills.py

# Test sandbox
pytest tests/test_sandbox.py
```

### Run Specific Test Classes or Functions

```bash
# Run all tests in a class
pytest tests/test_skills.py::TestSkillLoader

# Run a specific test
pytest tests/test_config.py::test_default_settings
```

### Verbose Output

```bash
# Show test names and status
pytest -v tests/

# Show print statements
pytest -s tests/

# Show both
pytest -v -s tests/
```

### Parallel Execution

```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4 tests/
```

### Test Timeouts

Hub tests have a 10-second timeout per test (configured in `pyproject.toml`):

```toml
[tool.pytest.ini_options]
timeout = 10
timeout_method = "thread"
```

For Spoke tests, you can add timeout manually:

```bash
# Install pytest-timeout
pip install pytest-timeout

# Run with timeout
pytest --timeout=30 tests/
```

---

## Test Coverage

### Spoke Test Coverage

#### Audio System (`test_audio.py`)
- ✅ Audio stream management (continuous stream, subscribers)
- ✅ Frame distribution to multiple consumers
- ✅ Rolling buffer for lookback
- ✅ Backend abstraction (sounddevice, pvrecorder)

#### Configuration (`test_config.py`)
- ✅ Default settings validation
- ✅ YAML config loading
- ✅ Environment variable expansion
- ✅ Settings override behavior
- ✅ LLM, Conversation, and Sandbox configs

#### Skills (`test_skills.py`)
- ✅ Skill loading from Python files
- ✅ Method extraction (signatures, docstrings)
- ✅ Private method filtering
- ✅ Skill discovery (`search_skills`, `describe_function`)
- ✅ Code parsing (fenced blocks, bare code)
- ✅ Multiple fence type support (`python`, `tool_code`, `code`, `py`)

#### Sandbox (`test_sandbox.py`)
- ✅ Proxy generation (local and remote modes)
- ✅ Gatekeeper validation and routing
- ✅ Bridge communication (JSON serialization)
- ✅ Deno process management
- ✅ Error sanitization
- ✅ Timeout handling

#### Remote Mode (`test_remote.py`)
- ✅ DeviceManager proxy structure
- ✅ Remote skill search and discovery
- ✅ Remote skill execution via proxies
- ✅ Mode switching prompts

#### Hub Client (`test_hub_client.py`)
- ✅ Health checks
- ✅ Chat completions
- ✅ Skill registration
- ✅ Skill search
- ✅ Retry logic for transient failures
- ✅ JWT authentication

#### Voice Pipeline (`test_pipeline.py`, `test_vad.py`, `test_wake.py`, `test_stt.py`, `test_tts.py`)
- ✅ VAD weighted counter algorithm
- ✅ Wake word detection
- ✅ STT transcription
- ✅ TTS synthesis
- ✅ Pipeline state machine

#### Audio Feedback (`test_audio_feedback.py`)
- ✅ Tone generation
- ✅ Volume application
- ✅ Sound configuration validation
- ✅ Enable/disable functionality

### Hub Test Coverage

#### Authentication (`test_auth.py`)
- ✅ Device registration
- ✅ JWT token generation
- ✅ Token validation
- ✅ Unauthorized access rejection
- ✅ Token refresh

#### Skills (`test_skills.py`)
- ✅ Skill registration
- ✅ Skill listing
- ✅ Skill search
- ✅ Device association

---

## Test Patterns

### Mock-Based Testing

Most tests use mocks to isolate components:

```python
from unittest.mock import Mock, AsyncMock, patch

@pytest.fixture
def mock_hub_client():
    """Mock Hub client for testing."""
    client = AsyncMock()
    client.chat.return_value = ChatResponse(
        content="Hello!",
        model="test",
        finish_reason="stop"
    )
    return client

def test_skill_execution(mock_hub_client):
    """Test skill execution with mocked Hub."""
    service = SkillService(hub_client=mock_hub_client)
    result = service.execute_code("print(device.TimeSkill.get_time())")
    assert result.success
```

### Async Testing

Use `pytest-asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async function."""
    result = await some_async_function()
    assert result == expected
```

### Fixture-Based Setup

Use fixtures for common setup:

```python
@pytest.fixture
def skills_dir():
    """Create temporary skills directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test skill files
        skill_file = Path(tmpdir) / "test_skill.py"
        skill_file.write_text("class TestSkill: ...")
        yield Path(tmpdir)
```

### Clean Output

Tests are designed to produce minimal, helpful output:

```python
# Good: Clear assertion with helpful message
assert result.success, f"Skill call failed: {result.error}"

# Avoid: Massive stack traces (unless debugging)
# Use pytest -v for more details
```

---

## Fixtures and Utilities

### Hub Test Fixtures (`ai-hub/tests/conftest.py`)

#### `setup_test_db` (autouse)
- **Scope**: Function
- **Purpose**: Sets up and tears down test database for each test
- **Creates**: SQLite test database at `tests/test.db`
- **Auto-cleanup**: Removes database after each test

#### `client`
- **Scope**: Function
- **Purpose**: Creates FastAPI test client
- **Returns**: `httpx.AsyncClient` with ASGI transport

#### `auth_client`
- **Scope**: Function
- **Purpose**: Creates authenticated test client
- **Setup**: Registers test device, sets Authorization header
- **Returns**: `httpx.AsyncClient` with JWT token

### Common Patterns

#### Temporary Directories

```python
@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
```

#### Mock Skills

```python
@pytest.fixture
def mock_skill_info():
    """Create mock skill for testing."""
    class MockSkill:
        def test_method(self):
            return "result"
    
    return SkillInfo(
        name="MockSkill",
        class_obj=MockSkill,
        methods=[...],
        module_path=Path("test.py")
    )
```

---

## End-to-End Testing

### E2E Test Script (`scripts/test_e2e.sh`)

The E2E test script validates the full flow: Spoke → Hub → LLM → Spoke.

#### Prerequisites

1. Hub must be running on `http://localhost:8000`
2. Start Hub: `cd ai-hub && strawberry-hub`

#### Running E2E Tests

```bash
./scripts/test_e2e.sh
```

#### What It Tests

1. **Hub Health Check**: Verifies Hub is running and healthy
2. **Device Registration**: Registers a test device with the Hub
3. **Authentication**: Verifies JWT token generation and validation
4. **Chat Endpoint**: Tests LLM communication (if configured)
5. **Skill Registration**: Tests skill registration with Hub
6. **Skill Listing**: Verifies skill discovery

#### Expected Output

```
=== Strawberry AI End-to-End Test ===

Step 1: Check Hub status
✓ Hub is running

Step 2: Register test device
✓ Device registered
  Token: eyJhbGciOiJIUzI1NiIs...

Step 3: Verify authentication
✓ Authentication working

Step 4: Test chat endpoint
✓ Chat endpoint working
  Response: Hello! How can I help...

Step 5: Test skill registration
✓ Skill registration working

Step 6: List skills
✓ Skill listing working (3 skills)

=== All Tests Passed ===
```

### Manual E2E Testing

For testing the full voice pipeline:

1. **Start Hub**:
   ```bash
   cd ai-hub
   source .venv/bin/activate
   strawberry-hub
   ```

2. **Start Spoke** (terminal mode):
   ```bash
   cd ai-pc-spoke
   source .venv/bin/activate
   python -m strawberry.main
   ```

3. **Start Spoke** (UI mode):
   ```bash
   strawberry-gui
   ```

4. **Test Flow**:
   - Wake word: "Hey Jarvis" or "Hey Strawberry"
   - Say: "What time is it?"
   - Verify: LLM responds, skill executes, TTS plays response

---

## Future Improvements

### Test Coverage Gaps

1. **UI Tests**: No automated tests for PySide6 UI components
   - Need: Widget testing, event handling, visual regression

2. **Integration Tests**: Limited integration between components
   - Need: Full pipeline tests (wake → STT → LLM → TTS)
   - Need: Real backend testing (with actual Picovoice/Google APIs)

3. **Remote Skill Execution**: HTTP routing not yet tested
   - Need: Tests for `/skills/execute` endpoint
   - Need: Tests for Spoke callback endpoint
   - Need: Multi-device E2E tests

4. **Error Handling**: Some error paths not fully covered
   - Need: Network failure scenarios
   - Need: Sandbox crash recovery
   - Need: Hub unavailability handling

5. **Performance Tests**: No performance benchmarks
   - Need: Latency measurements (STT, LLM, TTS)
   - Need: Memory usage profiling
   - Need: Concurrent request handling

### Recommended Additions

#### Test Utilities

```python
# tests/utils.py
def create_mock_audio_frame(sample_rate=16000, duration_ms=30):
    """Generate mock audio frame for testing."""
    samples = int(sample_rate * duration_ms / 1000)
    return np.zeros(samples, dtype=np.int16)
```

#### Integration Test Fixtures

```python
@pytest.fixture
async def hub_and_spoke():
    """Start Hub and Spoke for integration tests."""
    # Start Hub in background
    hub_process = subprocess.Popen(["strawberry-hub"])
    # Wait for ready
    await wait_for_hub()
    yield
    # Cleanup
    hub_process.terminate()
```

#### Coverage Reports

```bash
# Install coverage
pip install pytest-cov

# Run with coverage
pytest --cov=strawberry --cov-report=html tests/
```

#### Continuous Integration

Set up CI/CD pipeline:
- Run tests on every PR
- Enforce minimum coverage threshold
- Run E2E tests on merge to main

---

## Test Best Practices

### ✅ Do

- **Mock external dependencies**: Don't make real API calls in unit tests
- **Use descriptive test names**: `test_vad_ends_on_silence()` not `test_vad()`
- **Keep tests fast**: Use mocks, avoid I/O where possible
- **Test edge cases**: Empty inputs, None values, timeouts
- **Use fixtures**: Reuse common setup code
- **Clean up**: Remove temporary files, close connections

### ❌ Don't

- **Don't test implementation details**: Test behavior, not internals
- **Don't share state**: Each test should be independent
- **Don't make tests flaky**: Avoid sleeps, use deterministic mocks
- **Don't skip assertions**: Verify expected behavior explicitly
- **Don't hardcode paths**: Use temp directories and relative paths

---

## Troubleshooting

### Tests Hang

If tests hang indefinitely:

1. **Check for async issues**: Ensure async functions are awaited
2. **Check timeouts**: Hub tests have 10s timeout; increase if needed
3. **Check for blocking calls**: Replace with async alternatives

### Import Errors

If you see `ModuleNotFoundError`:

1. **Install in development mode**: `pip install -e .`
2. **Check Python path**: Tests may need `sys.path` adjustments
3. **Verify package structure**: Ensure `__init__.py` files exist

### Database Errors (Hub Tests)

If you see `no such table`:

1. **Check conftest.py**: Database should be set up automatically
2. **Check test isolation**: Each test gets a fresh database
3. **Check migrations**: Ensure tables are created in `database.init_db()`

---

## Summary

The Strawberry AI test suite provides comprehensive coverage of core functionality:

- ✅ **259+ Spoke tests** covering audio, skills, sandbox, and voice pipeline
- ✅ **8+ Hub tests** covering authentication and skill registry
- ✅ **E2E script** for full system validation
- ✅ **Async support** for testing concurrent operations
- ✅ **Mock-based isolation** for fast, reliable tests

For questions or improvements, see `DESIGN.md` and `IMPLEMENTATION.md`.

