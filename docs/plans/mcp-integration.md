# MCP Integration Plan

## Implementation Status (2026-01-25)

**Phases 1-4 Complete.** Core MCP integration is implemented and tested.

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Client Foundation | ✅ Complete | `mcp/` module with client, config, registry, adapter |
| 2. Settings Integration | ✅ Complete | YAML config parsing from `settings.yaml` |
| 3. SkillService Integration | ✅ Complete | `load_skills_async()`, Gatekeeper MCP support |
| 4. Documentation Flow | ✅ Complete | MCP tools in `get_system_prompt()` |
| 5. UI Polish | ⏳ Pending | MCP Servers tab in Settings (future) |
| 6. Hub Integration | ⏳ Pending | Central MCP servers (future) |

**Files Created:**
- `ai-pc-spoke/src/strawberry/mcp/__init__.py`
- `ai-pc-spoke/src/strawberry/mcp/config.py` - `MCPServerConfig` dataclass
- `ai-pc-spoke/src/strawberry/mcp/client.py` - `MCPClient` wrapper
- `ai-pc-spoke/src/strawberry/mcp/registry.py` - `MCPRegistry` multi-server manager
- `ai-pc-spoke/src/strawberry/mcp/adapter.py` - `MCPSkillAdapter` (tool → SkillInfo)
- `ai-pc-spoke/src/strawberry/mcp/settings.py` - Settings loader
- `ai-pc-spoke/src/strawberry/mcp/settings_schema.py` - UI schema
- `ai-pc-spoke/tests/test_mcp.py` - 30 unit tests (all passing)

**Modified Files:**
- `ai-pc-spoke/pyproject.toml` - Added `mcp>=1.0` dependency
- `ai-pc-spoke/src/strawberry/skills/service.py` - MCP integration
- `ai-pc-spoke/src/strawberry/skills/sandbox/gatekeeper.py` - MCP skill allowlist

---

## Overview

Integrate **Model Context Protocol (MCP)** servers into Strawberry's skill system so that:
1. MCP tools are discoverable via `search_skills()` alongside regular skills
2. MCP tools are callable via the same pattern: `device.<mcp_name>.<tool_name>(<params>)`
3. Configuration is handled through the existing Settings system
4. Documentation flows into the LLM context the same way skill docstrings do

## Current Architecture Summary

### Skills Flow
```
SkillLoader.load_all()
    → discovers skills/<repo>/skill.py
    → extracts SkillInfo (class_name, methods, signatures, docstrings)
    → SkillService builds system prompt with skill descriptions
    → LLM calls: device.SkillName.method(args)
    → Gatekeeper validates → Proxy routes → method executes
```

### Key Integration Points
- **`SkillLoader`**: Discovers and loads skills from `skills/` directory
- **`SkillInfo` / `SkillMethod`**: Data classes holding skill metadata
- **`SkillService`**: Orchestrates loading, prompt building, code execution
- **`Gatekeeper`**: Validates that LLM code only calls allowed methods
- **`ProxyGenerator`**: Creates `device.*` proxy objects for sandbox
- **Settings schema**: Declarative config with auto-rendered UI

## Design Goals

1. **Unified Discovery**: MCP tools appear in `search_skills()` results
2. **Consistent Calling Convention**: `device.<mcp_name>.<tool_name>(...)` (not raw MCP calls)
3. **Transparent Documentation**: Tool schemas become docstrings the LLM can read
4. **Settings-Based Config**: Add MCP servers like any other skill setting
5. **Minimal Core Changes**: Wrap MCP as a "skill-like" adapter, not fork the loader

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SkillService                                │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────────┐    │
│  │ SkillLoader │    │ MCPRegistry │    │ UnifiedSkillRegistry │    │
│  │ (Python)    │    │ (MCP wrap)  │    │ (combines both)      │    │
│  └─────────────┘    └─────────────┘    └──────────────────────┘    │
│         │                  │                      │                 │
│         └──────────────────┴──────────────────────┘                 │
│                            ▼                                        │
│                   get_all_skills() → List[SkillInfo]                │
│                   call_method(skill, method, args)                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         MCPRegistry                                 │
│  ┌─────────────────┐                                                │
│  │ MCPServerConfig │ ← from settings.yaml                           │
│  │ - name          │                                                │
│  │ - command       │                                                │
│  │ - args          │                                                │
│  │ - env           │                                                │
│  └─────────────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐    ┌─────────────────┐                        │
│  │ MCPClientPool   │───▶│ mcp-python-sdk  │ (JSON-RPC stdio/SSE)   │
│  │ - start/stop    │    │ Client          │                        │
│  │ - tool listing  │    └─────────────────┘                        │
│  │ - tool calling  │                                                │
│  └─────────────────┘                                                │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                                │
│  │ MCPSkillAdapter │ → returns SkillInfo-compatible objects         │
│  │ - as_skill_info │    with methods derived from MCP tools         │
│  └─────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Naming Convention

| MCP Server Name | Skill Name (device proxy) | Tool Call |
|-----------------|---------------------------|-----------|
| `filesystem`    | `FilesystemMCP`           | `device.FilesystemMCP.read_file(path="/tmp/x")` |
| `brave-search`  | `BraveSearchMCP`          | `device.BraveSearchMCP.search(query="...")` |
| `context7`      | `Context7MCP`             | `device.Context7MCP.resolve(libraryName="react")` |

Rule: `<ServerName>MCP` suffix makes it clear this is an MCP wrapper while keeping the `*Skill` pattern familiar.

### Data Flow: Tool Discovery

```
1. SkillService.load_skills()
   ├─ SkillLoader.load_all() → List[SkillInfo] (Python skills)
   └─ MCPRegistry.load_all() → List[SkillInfo] (MCP adapters)
   
2. MCPRegistry.load_all():
   a. Read mcp_servers from settings
   b. For each server config:
      - Start MCP client (stdio subprocess or SSE connection)
      - Call tools/list to get tool schemas
      - Convert each tool → SkillMethod
      - Wrap in SkillInfo(name="<ServerName>MCP", methods=[...])
   c. Return list of SkillInfo

3. Combined skills used for:
   - search_skills() responses
   - System prompt generation
   - Gatekeeper allowlist
```

### Data Flow: Tool Execution

```
LLM generates: device.BraveSearchMCP.search(query="weather")

1. Gatekeeper.validate() → allowed (BraveSearchMCP.search in allowlist)

2. Proxy intercepts: device.BraveSearchMCP.search(query="weather")

3. SkillService.call_method("BraveSearchMCP", "search", query="weather")
   ├─ Is "BraveSearchMCP" a Python skill? No
   └─ Is "BraveSearchMCP" an MCP adapter? Yes
       → MCPRegistry.call_tool("brave-search", "search", {"query": "weather"})

4. MCPRegistry.call_tool():
   a. Get client for "brave-search" server
   b. Send tools/call JSON-RPC request
   c. Return result (text/blob/error)

5. Result flows back through proxy → sandbox → LLM
```

---

## Implementation Phases

### Phase 1: MCP Client Foundation

**Goal**: Establish MCP client infrastructure using `mcp` Python SDK.

**Files to create**:
```
ai-pc-spoke/src/strawberry/mcp/
├── __init__.py
├── client.py        # MCPClient wrapper (start, stop, list_tools, call_tool)
├── config.py        # MCPServerConfig dataclass
├── registry.py      # MCPRegistry (manages multiple servers)
└── adapter.py       # MCPSkillAdapter (converts tools → SkillInfo)
```

**Key classes**:

```python
# config.py
@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str                      # e.g., "brave-search"
    command: str                   # e.g., "npx"
    args: List[str]                # e.g., ["-y", "@anthropic/mcp-brave-search"]
    env: Dict[str, str] = field(default_factory=dict)  # e.g., {"BRAVE_API_KEY": "..."}
    enabled: bool = True
    transport: Literal["stdio", "sse"] = "stdio"
    url: Optional[str] = None      # For SSE transport

# client.py
class MCPClient:
    """Wrapper around mcp.ClientSession for a single server."""
    
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def list_tools(self) -> List[MCPTool]: ...
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any: ...

# registry.py
class MCPRegistry:
    """Manages multiple MCP server connections."""
    
    def __init__(self, configs: List[MCPServerConfig]): ...
    async def start_all(self) -> None: ...
    async def stop_all(self) -> None: ...
    def get_all_skills(self) -> List[SkillInfo]: ...
    async def call_tool(self, server_name: str, tool_name: str, args: Dict) -> Any: ...
```

**Dependencies**:
- Add `mcp>=1.0` to requirements.txt (Anthropic's official Python SDK)

**Tests**:
- Unit tests with mock MCP responses
- Integration test with a simple local MCP server (e.g., filesystem)

---

### Phase 2: Settings Integration

**Goal**: Configure MCP servers through the Settings system.

**Settings schema addition** (in `spoke_core/settings_schema.py` or new namespace):

```python
MCP_SETTINGS_SCHEMA = [
    SettingField(
        key="mcp.servers",
        label="MCP Servers",
        type=FieldType.MULTILINE,  # JSON array for now; UI can improve later
        default="[]",
        description="JSON array of MCP server configurations",
        group="mcp",
    ),
]
```

**Config file format** (`config/settings.yaml`):

```yaml
mcp:
  servers:
    - name: brave-search
      command: npx
      args: ["-y", "@anthropic/mcp-brave-search"]
      env:
        BRAVE_API_KEY: "${BRAVE_API_KEY}"  # Resolved from .env
      enabled: true
    
    - name: filesystem
      command: npx
      args: ["-y", "@anthropic/mcp-filesystem", "/home/user/documents"]
      enabled: true
    
    - name: context7
      command: npx
      args: ["-y", "@anthropic/mcp-context7"]
      enabled: false  # Disabled by default
```

**Environment variable handling**:
- Secrets like `BRAVE_API_KEY` stored in `.env`
- Settings UI shows password field for each server's env vars
- MCPRegistry resolves `${VAR}` syntax at startup

---

### Phase 3: Skill System Integration

**Goal**: MCP tools appear alongside Python skills in discovery and execution.

**Changes to SkillService**:

```python
class SkillService:
    def __init__(self, ...):
        self._loader = SkillLoader(skills_path)
        self._mcp_registry: Optional[MCPRegistry] = None  # NEW
    
    async def load_skills(self) -> List[SkillInfo]:
        """Load Python skills and MCP tools."""
        python_skills = self._loader.load_all()
        
        # Load MCP servers from settings
        mcp_configs = self._load_mcp_configs()
        if mcp_configs:
            self._mcp_registry = MCPRegistry(mcp_configs)
            await self._mcp_registry.start_all()
            mcp_skills = self._mcp_registry.get_all_skills()
        else:
            mcp_skills = []
        
        # Combine and check for name collisions
        all_skills = python_skills + mcp_skills
        self._validate_no_collisions(all_skills)
        
        return all_skills
    
    def call_method(self, skill_name: str, method_name: str, *args, **kwargs) -> Any:
        """Route to Python skill or MCP tool."""
        # Check Python skills first
        if self._loader.get_skill(skill_name):
            return self._loader.call_method(skill_name, method_name, *args, **kwargs)
        
        # Check MCP adapters
        if self._mcp_registry and self._mcp_registry.has_skill(skill_name):
            return self._mcp_registry.call_method(skill_name, method_name, **kwargs)
        
        raise ValueError(f"Skill not found: {skill_name}")
```

**Gatekeeper changes**:
- Accept MCP skill names in allowlist
- No structural changes needed (already uses skill names)

**ProxyGenerator changes**:
- Generate proxy objects for MCP skills same as Python skills
- Route calls through `SkillService.call_method()`

---

### Phase 4: Documentation & System Prompt

**Goal**: MCP tool schemas flow into LLM context like skill docstrings.

**MCPSkillAdapter.as_skill_info()**:

```python
def as_skill_info(self, server_name: str, tools: List[MCPTool]) -> SkillInfo:
    """Convert MCP tools to SkillInfo format."""
    skill_name = f"{self._to_pascal_case(server_name)}MCP"
    
    methods = []
    for tool in tools:
        # Build signature from JSON schema
        sig = self._schema_to_signature(tool.name, tool.input_schema)
        
        # Use MCP description as docstring
        docstring = tool.description or f"MCP tool: {tool.name}"
        
        methods.append(SkillMethod(
            name=tool.name,
            signature=sig,
            docstring=docstring,
            callable=None,  # Not a real Python callable
        ))
    
    return SkillInfo(
        name=skill_name,
        class_obj=None,  # No Python class
        methods=methods,
        module_path=None,
        instance=None,
    )

def _schema_to_signature(self, name: str, schema: dict) -> str:
    """Convert JSON Schema to Python-like signature.
    
    Example:
        {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        → "search(query: str)"
    """
    params = []
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    
    for prop_name, prop_schema in properties.items():
        py_type = self._json_type_to_python(prop_schema.get("type", "any"))
        if prop_name in required:
            params.append(f"{prop_name}: {py_type}")
        else:
            default = prop_schema.get("default", "None")
            params.append(f"{prop_name}: {py_type} = {repr(default)}")
    
    return f"{name}({', '.join(params)})"
```

**System prompt output** (example):

```
### BraveSearchMCP
MCP server for web search via Brave Search API.

- `device.BraveSearchMCP.search(query: str, count: int = 10)`
  Search the web using Brave Search.

- `device.BraveSearchMCP.local_search(query: str, location: str)`
  Search for local businesses and places.
```

---

### Phase 5: UI & Polish

**Goal**: User-friendly MCP server management.

**Settings UI enhancements**:
1. **MCP Servers tab** in Settings dialog
2. **Add Server button** → dialog with fields:
   - Name (text)
   - Command (text, e.g., "npx")
   - Arguments (text, space-separated)
   - Environment variables (key-value pairs, secrets masked)
   - Enabled (checkbox)
3. **Test Connection button** → starts server, lists tools, shows result
4. **Remove Server button** with confirmation

**Status indicators**:
- Show connection status (connected/disconnected/error) per server
- Show tool count per server

---

### Phase 6: Hub Integration (Future)

**Goal**: MCP servers configured on Hub available to all devices.

**Considerations**:
- Hub could run MCP servers centrally
- Spoke calls `devices.hub.MCPServerName.tool()` 
- Hub routes to its local MCP client
- Or: Hub distributes MCP configs to Spokes (each Spoke runs its own)

**Decision**: Defer to after Phase 5. Start with per-Spoke MCP only.

---

## Error Handling

| Error | Handling |
|-------|----------|
| MCP server fails to start | Log error, skip server, continue with others |
| MCP server crashes mid-session | Detect disconnect, attempt restart, return error to LLM |
| Tool call fails | Return structured error: `{"error": "...", "tool": "...", "server": "..."}` |
| Server not found | `ValueError: MCP server not found: {name}` |
| Tool not found | `ValueError: Tool not found: {server}.{tool}` |
| Timeout | Configurable per-server timeout, default 30s |

---

## Security Considerations

1. **MCP servers run as subprocesses** with user permissions
2. **No automatic installation**: User must have `npx` or the server command available
3. **Environment variables**: Secrets in `.env`, not in `settings.yaml`
4. **Trust model**: Same as skills—only enable MCP servers you trust
5. **Future**: Consider subprocess sandboxing (e.g., `firejail`, containers)

---

## File Structure (Final)

```
ai-pc-spoke/src/strawberry/
├── mcp/
│   ├── __init__.py
│   ├── client.py           # MCPClient class
│   ├── config.py           # MCPServerConfig dataclass
│   ├── registry.py         # MCPRegistry (multi-server manager)
│   ├── adapter.py          # MCPSkillAdapter (tool → SkillInfo)
│   └── settings_schema.py  # MCP_SETTINGS_SCHEMA
├── skills/
│   ├── loader.py           # (unchanged)
│   ├── service.py          # (modified: integrate MCPRegistry)
│   └── ...
└── shared/settings/
    └── ...                  # (unchanged, MCP uses same system)
```

---

## Milestones

### Milestone A: MCP Client Foundation (Phase 1)
- [ ] Create `mcp/` module structure
- [ ] Implement `MCPClient` with start/stop/list_tools/call_tool
- [ ] Implement `MCPServerConfig` dataclass
- [ ] Add `mcp` dependency to requirements.txt
- [ ] Unit tests with mocked MCP responses

### Milestone B: Settings & Registry (Phases 2-3)
- [ ] Implement `MCPRegistry` managing multiple servers
- [ ] Add MCP settings schema
- [ ] Implement config file parsing (YAML → MCPServerConfig)
- [ ] Integrate into `SkillService.load_skills()`
- [ ] Route `call_method()` to MCP when appropriate

### Milestone C: Documentation Flow (Phase 4)
- [ ] Implement `MCPSkillAdapter.as_skill_info()`
- [ ] Schema-to-signature conversion
- [ ] MCP tools appear in `search_skills()` results
- [ ] MCP tools appear in system prompt

### Milestone D: Proxy & Execution (Phase 3 cont.)
- [ ] Update `Gatekeeper` to allow MCP skill names
- [ ] Update `ProxyGenerator` to handle MCP calls
- [ ] End-to-end test: LLM calls MCP tool via `device.XyzMCP.tool()`

### Milestone E: UI Polish (Phase 5)
- [ ] MCP Servers tab in Qt Settings
- [ ] Add/Edit/Remove server dialogs
- [ ] Test Connection functionality
- [ ] Status indicators

---

## Open Questions

1. **Async vs Sync**: MCP SDK is async. Current `call_method` in loader is sync. Options:
   - Make `SkillService.call_method()` async (preferred, aligns with sandbox)
   - Run MCP calls in thread pool for sync compatibility

2. **Tool name collisions**: Two MCP servers with same tool name?
   - Scoped by server: `device.ServerAMCP.read_file()` vs `device.ServerBMCP.read_file()`
   - No global collision since each server is a separate "skill"

3. **Resource/Prompt support**: MCP also has resources and prompts. Include in V1?
   - Recommendation: Defer. Focus on tools first.

4. **npx requirement**: Most MCP servers are Node.js. Require Node.js installed?
   - Yes, document as prerequisite for MCP features
   - Consider bundling popular servers as standalone binaries (future)

---

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Anthropic MCP Servers](https://github.com/modelcontextprotocol/servers)
- Current skill system: `ai-pc-spoke/src/strawberry/skills/`
- Settings system: `ai-pc-spoke/src/strawberry/shared/settings/`
