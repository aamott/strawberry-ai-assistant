# Strawberry AI

A voice assistant platform using a hub-and-spoke architecture.

## Overview

**Hub**: Handles AI interaction, chat history, user accounts, sessions, LLM orchestration, skill registry, and MQTT broker.

**Spokes**: Devices that provide voice and text/chat interaction and run skill code. Each spoke can operate in local mode (offline) or remote mode (connected to Hub).

## Data Flow

```
User Prompt 
    → Spoke TensorZero 
    → Hub TensorZero 
    → LLM (e.g., OpenAI, Claude, etc.) 
    → Hub TensorZero 
    → Spoke TensorZero 
    → Spoke handles response (text output + skill calls)
```

### TensorZero's Role

TensorZero uses the **[Embedded Gateway](https://www.tensorzero.com/docs/gateway/clients#embedded-gateway)** on both Hub and Spoke—no separate gateway service required.

- **On the Hub**: Acts as a unifier for multiple LLMs. Handles fallback logic, authentication, and routing. Configured once; all Spokes benefit.
- **On the Spoke**: Routes requests to the Hub as if it were an LLM server. Can be configured to use a different LLM server if needed.

**Spoke TensorZero Example:**
```python
from tensorzero import AsyncTensorZeroGateway

async with await AsyncTensorZeroGateway.build_embedded(
    config_file="config/tensorzero.toml",
) as gateway:
    response = await gateway.inference(
        function_name="chat",
        input={
            "messages": [{"role": "user", "content": user_input}]
        },
    )
```

**Configuration Files:**
- `tensorzero.toml` — TensorZero function definitions, model routing, variants
- `config.yaml` — Spoke-specific settings (device name, Hub URL, skills path)
- `.env` — API keys and secrets

### Response Handling

A single user prompt can result in multiple responses from the LLM:
1. Text responses (displayed to the user)
2. Skill calls (executed by the sandbox)

All responses are processed in order. After each skill call, the LLM can decide to continue (more text/skills) or stop.

## The Sandbox

The sandbox provides a secure execution environment for LLM-generated code. To maintain low resource overhead on Spoke devices (laptops and edge devices), the system uses **WebAssembly (Wasm)** rather than heavy containerization like Docker.

**Implementation:** Pyodide (Python in Wasm) + Deno (Wasm host)

**Spoke Architecture:**
```
┌────────────────────────────────────────┐
│           SPOKE (Python)               │
│  ┌──────────────────────────────────┐  │
│  │ Skill Runner Service             │  │
│  │ TensorZero Client                │  │
│  │ Real Skill Implementations       │  │
│  └──────────────┬───────────────────┘  │
│                 │ spawns/manages       │
│                 ▼                      │
│  ┌──────────────────────────────────┐  │
│  │ Deno Process (Sandbox Host)      │  │
│  │   └─ Pyodide (Wasm)              │  │
│  │       └─ LLM Code Execution      │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

The Spoke application is Python. Deno's **only job** is hosting the Pyodide Wasm sandbox—it doesn't handle any other Spoke logic.

### Execution Flow

1. User types a prompt into the Spoke
2. Spoke sends prompt to Hub
3. Hub returns response(s) to Spoke (text and/or skill calls)
4. If skill call: Spoke runs the LLM's code in sandbox
5. Sandbox executes skill via Proxy Bridge, returns results to Spoke's LLM agent
6. LLM agent decides whether to continue or stop
7. Repeat steps 3-6 as needed

### Core Architecture: Wasm Isolation

The sandbox creates a strict boundary between "Untrusted" LLM code and the "Trusted" Host system:

| Component | Environment | Access Level |
|-----------|-------------|--------------|
| **Guest (Untrusted)** | Lightweight Wasm with stripped-down Python (Pyodide) | No network, no filesystem, limited CPU/RAM |
| **Host (Trusted)** | Full Python environment (Spoke application) | Full system access, credentials, skill implementations |

### The Bridge Pattern

Since the Guest cannot access system hardware directly, it interacts with the Host via a **Proxy Bridge**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     SPOKE DEVICE (HOST)                         │
│  ┌──────────────────┐    ┌─────────────────────────────────┐   │
│  │ Skill Runner     │───▶│ Real Skill Implementations      │   │
│  │ Service          │    │ (Full Python + System Access)   │   │
│  └────────┬─────────┘    └─────────────────────────────────┘   │
│           │                                                     │
│           │ Manages                                             │
│           ▼                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 WASM RUNTIME (Pyodide)                   │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │              THE SANDBOX (GUEST)                 │    │   │
│  │  │                                                  │    │   │
│  │  │   LLM Generated Code                             │    │   │
│  │  │         │                                        │    │   │
│  │  │         ▼                                        │    │   │
│  │  │   Proxy Objects (device / device_manager)        │    │   │
│  │  │         │                                        │    │   │
│  │  └─────────┼────────────────────────────────────────┘    │   │
│  │            │ Serialized Request                          │   │
│  │            ▼                                             │   │
│  │   ┌─────────────────┐                                    │   │
│  │   │ Gatekeeper      │◀── Validates against Allow-List    │   │
│  │   │ Bridge          │                                    │   │
│  │   └─────────────────┘                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Proxy Generation

Proxy Objects are generated **at skill registration time**, not dynamically:

1. When a skill is registered (or updated), the Skill Runner generates Proxy code
2. Proxy code is cached and ready for injection
3. On sandbox init, pre-generated Proxies are injected immediately

This ensures fast sandbox startup since skills rarely change at runtime.

### Bridge Communication Flow

1. **Injection:** When the sandbox initializes, the Host injects pre-generated Proxy Objects that mirror available skills (`device` or `device_manager`).

2. **Interception:** When LLM code calls `device.lights.turn_on()`, the Proxy Object intercepts the call inside Wasm.

3. **Serialization:** The Proxy serializes the function name and arguments:
   ```json
   {"call": "lights.turn_on", "args": [], "kwargs": {}}
   ```

4. **Transport:** Serialized request sent across Wasm boundary via secure memory bridge or stdio.

5. **Gatekeeper Validation:** Host verifies the function is in the `Allowed_Skills` registry. If valid, executes the real Python function.

6. **Return:** Result serialized and sent back to Guest. Proxy returns it to LLM code.

### Security Constraints

| Constraint | Description |
|------------|-------------|
| **Network Air-Gap** | Wasm environment has no network interfaces. All external data must come from skill arguments or return values. |
| **Import Restrictions** | Guest Python limited to safe stdlib (`json`, `math`, `datetime`, etc.). Blocked: `os`, `sys`, `socket`, `subprocess`, `importlib`. |
| **Execution Timeout** | Every execution wrapped in strict timeout (default: 5 seconds). **Hard-kill on timeout**—no cleanup grace period. |
| **Allow-List Gating** | Gatekeeper only permits calls to functions registered by Skill Runner. Internal Host methods rejected. |
| **Resource Limits** | Memory and CPU caps enforced by Wasm runtime. |

### Failure Handling

The sandbox must be defensive—assume anything can fail:

| Failure Mode | Response |
|--------------|----------|
| **Timeout exceeded** | Hard-kill Wasm instance immediately. Return timeout error to LLM. |
| **Wasm crash** | Catch exception, log details, return sanitized error to LLM. |
| **Serialization failure** | Return error indicating malformed skill call. |
| **Skill not in allow-list** | Return "skill not found" error. Do not reveal internal structure. |
| **Bridge communication error** | Kill sandbox, return connection error to LLM. |
| **Out of memory** | Wasm runtime terminates Guest. Return resource limit error. |

**Recovery:** After any sandbox failure, the Skill Runner should be able to spin up a fresh Wasm instance for the next execution. Sandbox state is ephemeral—nothing persists between executions.

### Example: Sandbox Execution

**LLM generates this code:**
```python
# Turn off all the lights in the house
lights = device_manager.search_skills("light")
for light in lights:
    if "turn_off" in light["path"]:
        device_name = light["device"]
        getattr(device_manager, device_name).SmartHomeSkill.turn_off()
```

**What happens:**
1. `search_skills("light")` → Proxy serializes → Gatekeeper validates → Real function executes → Result returned
2. Loop iterates, each `turn_off()` call goes through the same bridge
3. LLM code never directly accesses network or hardware—all mediated by trusted Host

## The Skill Runner

The skill runner manages skill discovery, presentation to the LLM, and execution. It operates in two modes based on Hub connectivity.

### Local Mode

When the Hub is offline, skills are loaded from local Python files on the device.

**Available Functions:**
```python
device: Device  # Container for all local skills

device.search_skills(query: str = "") -> List[SkillResult]
# Search for skills using natural language

device.describe_function(path: str) -> str
# Get function signature + full docstring
# Path format: "ClassName.function_name"

device.SkillClassName.function_name(...)
# Call a skill function directly
```

**Example: `device.search_skills("music")`**
```python
[
    {
        "path": "MusicControlSkill.search_songs",
        "signature": "search_songs(query: str, max_results: int = 10, include_lyrics: bool = False) -> List[Song]",
        "summary": "Searches for songs in the music library"
    },
    {
        "path": "MusicControlSkill.set_volume", 
        "signature": "set_volume(volume: int) -> None",
        "summary": "Sets the playback volume (0-100)"
    }
]
```

**Example: `device.describe_function("MusicControlSkill.search_songs")`**
```python
"""
def search_songs(query: str, max_results: int = 10, include_lyrics: bool = False) -> List[Song]:
    \"\"\"
    Searches for songs in the music library.
    
    Args:
        query: The search query.
        max_results: Maximum number of results to return.
        include_lyrics: Whether to include lyrics in results.
    
    Returns:
        A list of Song objects matching the query.
    \"\"\"
"""
```

### Remote Mode

When the Hub is online, skills are shared across all devices via the Skill Registry.

**Available Functions:**
```python
device_manager: DeviceManager  # Manages all connected devices

device_manager.search_skills(query: str = "") -> List[RemoteSkillResult]
# Search for skills across all devices (current device prioritized)

device_manager.describe_function(path: str) -> str
# Get function signature + full docstring
# Path format: "DeviceName.ClassName.function_name"

device_manager.DeviceName.SkillClassName.function_name(...)
# Call a skill on a specific device
```

**Example: `device_manager.search_skills("volume")`**
```python
[
    {
        "path": "TV.MediaControlSkill.set_volume",
        "signature": "set_volume(volume: int) -> None",
        "summary": "Sets the TV volume",
        "device": "TV"
    },
    {
        "path": "Speaker.MediaControlSkill.set_volume",
        "signature": "set_volume(volume: int) -> None", 
        "summary": "Sets the speaker volume",
        "device": "Speaker"
    }
]
```

**Multi-Device Execution:**
Each device is exposed as an attribute on `device_manager`:
```python
device_manager.TV.MediaControlSkill.set_volume(50)
device_manager.Speaker.MediaControlSkill.set_volume(75)
device_manager.Bedroom_Light.SmartHomeSkill.turn_on()
```

### Remote Skill Call Flow

All remote skill calls route through the Hub, regardless of target device:

```
Spoke A calls skill on Spoke B:
    Spoke A → Hub MQTT → Spoke B Skill Service → Hub MQTT → Spoke A

Spoke A calls skill on itself (remote mode):
    Spoke A → Hub MQTT → Spoke A Skill Service → Hub MQTT → Spoke A
```

This uniform routing simplifies the architecture—all skill calls are treated identically.

**Error Handling:**
- If target device is offline: Returns error message for LLM to handle
- If skill throws exception: Exception message returned to LLM
- LLM can retry, try alternative device, or inform user

### Mode Switching

If connectivity changes mid-conversation, the LLM receives a system prompt:

**Switching to Remote Mode:**
```markdown
<system>
Automated Message: The device switched to online mode and now has access to 
skills on other devices. The available tools have changed:

device_manager: DeviceManager  # Manages all connected devices
device_manager.search_skills(query: str = "")  # Search skills across devices
device_manager.describe_function(path: str)  # Get function details
</system>
```

**Switching to Local Mode:**
```markdown
<system>
Automated Message: The device switched to offline mode. Only local skills 
are available:

device: Device  # Local skills only
device.search_skills(query: str = "")  # Search local skills
device.describe_function(path: str)  # Get function details
</system>
```

These prompts are stored in the skill runner class:
- `SkillRunner.remote_mode_prompt`
- `SkillRunner.local_mode_prompt`
- `SkillRunner.switched_to_remote_prompt`
- `SkillRunner.switched_to_local_prompt`

### Async/Long-Running Skills

For skills that take longer than a reasonable timeout:

```python
# Skill declares itself as long-running
@long_running(timeout=300)  # 5 minute max
def download_playlist(playlist_id: str) -> List[Song]:
    ...

# Execution returns a task handle if timeout exceeded
result = device_manager.TV.MediaSkill.download_playlist("xyz")
# Returns: {"status": "pending", "task_id": "abc123"}

# LLM can poll for status
status = device_manager.get_task_status(task_id="abc123")
# Returns: {"status": "running", "progress": 0.6}
# Or: {"status": "completed", "result": [...]}
# Or: {"status": "failed", "error": "..."}
```

## The Hub

### Skill Registry

The Hub maintains a database of all registered skills:
- Function signatures and docstrings
- Which device hosts each skill
- Skill health status

**Skill Registration:**
- Spokes register skills on startup and when skills change
- Skills expire after 30 minutes without a heartbeat
- If a skill is updated, the Spoke re-registers with new definition

**Duplicate Skill Handling:**
When multiple devices have the same skill (e.g., `set_volume`), the registry tracks all instances. The LLM can target a specific device or let it default to the current device.

### MQTT Broker

Handles all skill call routing between Spokes:
- Request/response pattern with correlation IDs
- Timeout handling (configurable per-skill)
- Device presence tracking

### Session Management

Following TensorZero's session model:
- Sessions expire after 15 minutes of inactivity
- Conversation history stored on Hub
- Users can resume previous conversations
- If Hub goes down mid-conversation, Spoke can cache and retry

## Authentication & Security

**Architecture:** FastAPI-based Hub with JWT authentication.

**Device Registration Flow:**
1. User logs into Hub web UI
2. User generates a device token (long-lived JWT)
3. Token stored in Spoke's configuration
4. All Spoke→Hub requests include `Authorization: Bearer <token>`

**JWT Token Contents:**
```json
{
    "user_id": "user_123",
    "device_id": "living_room_speaker",
    "device_name": "Living Room Speaker",
    "permissions": ["skill_call", "skill_register"],
    "exp": 1735689600
}
```

**Access Control:**
- Spokes can only access skills registered by the same user account
- Local network only—no external exposure required
- Standard HTTPS for Hub API, TLS for MQTT

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **TensorZero deployment** | Embedded Gateway | No separate service; simpler deployment on edge devices |
| **Multi-device commands** | LLM generates multiple calls | Keeps skill functions simple; LLM handles orchestration logic |
| **Sandbox technology** | Pyodide + Deno (Wasm) | Low resource overhead for edge devices; strong isolation |
| **Deno's role** | Sandbox host only | Spoke application remains Python; Deno only orchestrates Wasm runtime |
| **Proxy generation** | At registration time | Skills rarely change at runtime; faster sandbox startup |
| **Timeout behavior** | Hard-kill | No cleanup grace period; prevents hung processes from blocking system |
| **Skill dependencies** | Deferred | Focus on core skill runner first |

## Open Questions

1. **Skill Dependencies**: Can skills call other skills? (Deferred for now)

---

## Development Roadmap

### Phase 1: Terminal MVP ✅
**Goal:** End-to-end proof of concept with minimal UI.

#### Spoke
- [x] Terminal-based chat interface (print outputs, accept input)
- [x] Hub client integration (routes through Hub to LLM)
- [ ] Basic skill loader (load Python files from `skills/` folder)
- [ ] Sandbox prototype (Deno + Pyodide)
- [x] Configuration files:
  - `config.yaml` — Device settings
  - `.env` — API keys

**Deliverable:** User can chat with LLM through Hub. ✅

#### Hub (Minimal)
- [x] FastAPI skeleton
- [x] JWT authentication
- [x] Basic skill registry (SQLite)
- [x] OpenAI-compatible endpoint for Spoke routing
- [x] Google AI Studio (Gemini) integration

**Deliverable:** Spoke can route requests through Hub to LLM. ✅

---

### Phase 2: Desktop UI 🔄
**Goal:** Usable desktop application with basic settings.

#### Spoke
- [x] Desktop UI (chat window) — PySide6 (Qt for Python)
  - [x] Send/receive messages
  - [x] Display conversation history
  - [x] Display tool calls and results
  - [x] Markdown rendering with syntax highlighting
- [x] System tray integration
  - [x] Minimize to tray
  - [x] Quick access menu
  - [x] Status indicator
- [x] Settings panel
  - [x] Device name
  - [x] Hub URL & token
  - [x] Theme selection (dark/light)
  - [x] Skills folder path
- [x] Remote mode support (connect to Hub)
- [x] Skill loader (load Python files from skills/)
- [ ] Skill registration with Hub (heartbeat)

**Deliverable:** Desktop app with chat UI, system tray, and basic configuration.

#### Hub
- [ ] PostgreSQL for persistent storage
- [ ] MQTT broker integration
- [ ] Remote skill call routing
- [ ] Device management API
- [ ] Basic web UI for device tokens

**Deliverable:** Multiple Spokes can connect, share skills, and call skills across devices.

---

### Phase 3: Voice Interaction
**Goal:** Full voice assistant experience.

#### Spoke
- [ ] Wake word detection ("Hey Strawberry" or custom)
- [ ] Speech-to-text (local or cloud)
- [ ] Text-to-speech for responses
- [ ] Audio feedback (chimes, confirmation sounds)
- [ ] Push-to-talk mode
- [ ] Continuous listening mode
- [ ] UI updates:
  - Voice activity indicator
  - Waveform visualization
  - Transcript display

**Deliverable:** Hands-free voice interaction with visual feedback.

#### Hub
- [ ] Session management improvements
- [ ] Conversation history UI
- [ ] User preferences sync across devices
- [ ] Analytics dashboard (optional)

**Deliverable:** Production-ready Hub with full feature set.

---

### Phase 4: Polish & Ecosystem
**Goal:** Refinement and extensibility.

- [ ] Skill marketplace / sharing
- [ ] Plugin system for UI extensions
- [ ] Mobile companion app (optional)
- [ ] Multi-user household support
- [ ] Offline LLM support (local models)
- [ ] Performance optimization
- [ ] Documentation & tutorials

---

## Current Status

**Phase:** 2 — Desktop UI

**Completed:**
- Phase 1 Terminal MVP (99 Spoke tests, 8 Hub tests passing)
- Spoke → Hub → LLM (Gemini) → Hub → Spoke flow working
- JWT authentication and skill registry

**Next Steps:**
1. Build PySide6 desktop UI for Spoke
2. Implement system tray integration
3. Add settings panel
4. Skill loader and registration
