# Hub
- Central coordinator for all devices/spokes
- Manages LLM orchestration via TensorZero embedded gateway with fallback support
- **Executes tool calls when online** - runs the agent loop with `devices` object for cross-device skill access
- Routes skill calls to target devices via WebSocket
- Manages sessions, user accounts, and device authentication

# Spoke
- Client installed on Windows/Linux PC
- Houses skills (Python scripts) that can be executed locally or remotely by the hub (via websockets)
    - When connected to the Hub, it can register its skills to the Hub
    - The Hub can then execute these skills on the Spoke
    - The skills registered to the Hub are available to all devices/spokes owned by the user
    - If the Spoke is not connected to the Hub, it can still execute its own skills
- Registers skills to Hub and maintains heartbeat
- **When online**: Routes LLM requests to Hub; Hub executes tools; Spoke only receives final responses
- **When offline**: Runs full agent loop locally with TensorZero fallback to local Ollama
- Has its own TensorZero for offline operation (separate from Hub's) and runs all hub chats through its own TensorZero.

## Auth & Tokens
- Spoke authenticates to the Hub using a device JWT token provided by the Hub UI.
- Environment variable used by the Spoke TensorZero config: `HUB_DEVICE_TOKEN`.

## Sandbox Manager
```
Python (Spoke) → Deno (Host) → Pyodide (Wasm Guest)
                     ↑                    ↓
                     └── JSON Bridge ─────┘
```

Use Deno as the host and Pyodide as the guest to create a sandbox environment for the Spoke. The sandbox will be used to execute LLM-generated code. User written code will be executed in a full python environment, but can be called by the LLM-generated code through the sandbox. This way the user can write skills that interact with the Spoke's hardware or other skills but the LLM-generated code will still be sandboxed. 

- Manages the sandbox environment for the Spoke. 
- Holds user code as "skills" and presents them to the LLM as standard python classes and functions. 

### Skills
- Skills are each contained in a class that inherits from a base class. They are stored in files like `skills/WeatherSkill/__init__.py` or `skills/WeatherSkill/weather_skill.py`. 
- The base class is accessible so users can import it and inherit from it easily. A readme is stored in the `skills` directory to help users understand how to create skills.
- When the skill is loaded, only the public (non-underscored) methods *in the inherited class* are exposed to the LLM.

### Sandbox
- **When Connected to the Hub:** The sandbox presents the LLM with a `device_manager` object that provides access to skills across all connected devices (spokes). Search returns skills with their associated device lists. Skills are called via `device_manager.device_name.SkillName.method()`. The Hub routes calls to the target device, executes the real (non-sandboxed) skill code, and returns results as if executed locally.
- **When Not Connected to the Hub:** The sandbox presents the LLM with a `device` object containing only local skills. Skills are called via `device.SkillName.method()`. All execution happens locally.

### Tool Call System

TensorZero provides native tool calling support. Tools are defined in `tensorzero.toml` on both Hub and Spoke.

**Available Tools:**
- `search_skills(query: str = "")` - Returns grouped skills with signatures, summaries, sample devices
- `describe_function(path: str)` - Returns full function signature with docstring
- `python_exec(code: str)` - Executes Python code in sandbox with access to `device` (offline) or `devices` (online)

**Execution Location:**
- **Online mode**: Hub runs the agent loop and executes tools via `devices` object
- **Offline mode**: Spoke runs the agent loop locally and executes tools via `device` object
- Tools are disabled on the non-executing side to prevent duplicate execution

**Agent Loop Flow:**
1. User sends message
2. LLM responds with `ToolCall` objects (parsed by TensorZero)
3. Executor (Hub or Spoke) runs tools, returns results as `tool_result` messages
4. LLM continues (more tool calls or final text response)
5. Loop ends when LLM responds without tool calls (max iterations configurable)

**Offline Mode Example (Spoke executes):**
```
User: Turn on all lights
→ Spoke agent loop executes python_exec locally
→ Code: device.HomeAssistantSkill.turn_on_light(...)
→ Output: "Turned on Kitchen Light..."
```

**Online Mode Example (Hub executes):**
```
User: Turn up volume on the living room PC
→ Hub agent loop executes search_skills, then python_exec
→ Code: devices.living_room_pc.MusicControlSkill.set_volume(change_by=30)
→ Hub routes call to living_room_pc via WebSocket
→ Output: "Volume increased by 30"
```

**Error Handling:**
- Tool errors return as `tool_result` with error details
- Device offline errors include device name and suggestion to try alternatives

**Sandbox-to-Skill Bridge:**
LLM code runs in Pyodide (Wasm) sandbox → Proxy intercepts calls → Validates against allow-list → Routes to target device (via Hub when online, local when offline) → Executes real Python → Returns result.