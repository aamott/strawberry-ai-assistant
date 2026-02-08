# MCP Integration Plan

## Goal

Turn MCP servers (defined in `config/mcp_config.json`) into first-class Strawberry skills.
Each MCP server becomes its own `*Skill` class, and each MCP tool becomes a method on that class.

**Before:** `device.MCPSkill.github_create_issue(...)` (monolithic, unclear)
**After:** `device.GithubSkill.create_issue(...)` (one skill per server, clean)

## Architecture

```
config/mcp_config.json          # User configures MCP servers here
        ↓
skills/mcp_skill/skill.py       # Entrypoint: reads config, connects, builds classes
        ↓
SkillLoader discovers classes   # e.g. HomeAssistantSkill, FirebaseSkill, Context7Skill
        ↓
device.HomeAssistantSkill.turn_on_light(entity_id="light.kitchen")
```

### Key Design Decisions

1. **One `*Skill` class per MCP server** — dynamically generated at import time
2. **Each MCP tool → one method** — signature + docstring from MCP tool schema
3. **Server name → class name** — e.g. `"Home Assistant"` → `HomeAssistantSkill`
4. **Disabled servers are skipped** — respects `"disabled": true` in config
5. **`disabledTools` respected** — tools in this list are not exposed as methods
6. **Async MCP client** — uses `mcp` Python SDK (already in pyproject.toml)
7. **Errors fail loudly** — if a server can't connect, log error but continue with others

### mcp_config.json Format (existing)

```json
{
  "mcpServers": {
    "Server Name": {
      "command": "executable",
      "args": ["--flag", "value"],
      "env": {"KEY": "value"},
      "disabled": false,
      "disabledTools": ["tool_to_skip"]
    }
  }
}
```

Two transport types:
- **stdio**: has `command` + `args` → spawn subprocess
- **streamable HTTP**: has `serverUrl` → HTTP SSE connection

## Phases

### Phase 1: Multi-skill repo verification ✅
- Verify the loader already supports multiple `*Skill` classes per repo entrypoint
- Add a test for this specific scenario
- **Status: COMPLETE**

### Phase 2: MCP skill repo implementation ✅
- Create `skills/mcp_skill/skill.py` entrypoint
- Create `skills/mcp_skill/mcp_client.py` — thin wrapper around `mcp` SDK
- Create `skills/mcp_skill/class_builder.py` — dynamically builds `*Skill` classes
- At import time:
  1. Read `config/mcp_config.json`
  2. For each enabled server, connect via MCP client
  3. Call `tools/list` to discover tools
  4. Build a `*Skill` class with one method per tool
  5. Assign class to module scope so loader finds it
- 20 unit tests covering naming, class building, loader integration
- **Status: COMPLETE**

### Phase 3: Integration + loader tweaks ✅
- Dynamic classes pass through loader correctly (set `__module__` to match entrypoint)
- Tested with `test_cli --compact --offline` — FirebaseSkill loaded with 11 tools
- All pytest tests pass, ruff clean
- **Status: COMPLETE**

## Naming Convention

| MCP Server Name | Generated Class Name |
|-----------------|---------------------|
| `Home Assistant` | `HomeAssistantSkill` |
| `context7` | `Context7Skill` |
| `firebase` | `FirebaseSkill` |
| `my-custom-server` | `MyCustomServerSkill` |

Rule: strip non-alphanumeric, PascalCase, append `Skill`.

## Method Signature Generation

From MCP tool schema:
```json
{
  "name": "turn_on_light",
  "description": "Turn on a light entity",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entity_id": {"type": "string", "description": "HA entity ID"}
    },
    "required": ["entity_id"]
  }
}
```

Generated method:
```python
def turn_on_light(self, entity_id: str, **kwargs) -> Any:
    """Turn on a light entity.
    
    Args:
        entity_id: HA entity ID
    """
    # Calls MCP tools/call under the hood
```

## Files Created

- `skills/mcp_skill/skill.py` — entrypoint (reads config, runs async discovery, assigns classes to module scope)
- `skills/mcp_skill/mcp_client.py` — MCP SDK wrapper (stdio + streamable HTTP, returns sessions)
- `skills/mcp_skill/class_builder.py` — dynamic class generation (server → Skill class, tool → method)
- `tests/test_mcp_skill.py` — 20 unit tests

## Risk / Open Questions

- **Startup latency**: Connecting to MCP servers at import time could be slow.
  Mitigation: Use async init with timeout; lazy-connect on first call if needed.
- **Server availability**: MCP servers may not be running when skills load.
  Mitigation: Graceful degradation — log warning, skip unavailable servers.
- **Tool schema quality**: Some MCP servers have sparse schemas.
  Mitigation: Fall back to `**kwargs` when schema is incomplete.
