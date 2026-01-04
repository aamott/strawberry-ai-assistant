# Tool Call System Implementation Plan

**Status:** COMPLETED ✅  
**Created:** 2026-01-03  
**Last Updated:** 2026-01-03

## Summary

Implement TensorZero native tool calling to replace the current markdown code block parsing approach. This provides structured tool execution, dual availability of search/describe functions, and proper error handling.

## Research Findings

### TensorZero Tool Calling (from docs)
- Tools defined in `tensorzero.toml` with JSON Schema parameters
- LLM returns `ToolCall` objects parsed by TensorZero
- Tool results returned as `tool_result` messages
- No custom XML/markdown parsing needed

### Current Implementation
- `main_window.py:_send_message()` - Agent loop using markdown code blocks
- `skills/service.py` - `parse_skill_calls()` uses regex for ```python blocks
- `_DeviceProxy` class provides `device.SkillName.method()` access
- No `device_manager` for online mode yet

## Implementation Tasks

### Phase 1: TensorZero Tool Configuration
- [ ] Create JSON Schema files for tools in `config/tools/`
  - `search_skills.json`
  - `describe_function.json`
  - `python_exec.json`
- [ ] Update `tensorzero.toml` to define tools and link to schemas
- [ ] Add tools to the chat function definition

### Phase 2: Skill Service Updates
- [ ] Add `DeviceManagerProxy` class with `__getattr__` for dynamic device access
- [ ] Add `search_skills()` and `describe_function()` as methods on both proxies
- [ ] Update search result format to include `devices` list for online mode
- [ ] Add device name normalization function
- [ ] Implement dual availability (tool call + method inside python_exec)

### Phase 3: Agent Loop Updates
- [ ] Update `_send_message_via_tensorzero()` to handle `ToolCall` objects
- [ ] Add tool execution dispatcher for `search_skills`, `describe_function`, `python_exec`
- [ ] Format tool results as `tool_result` messages per TensorZero spec
- [ ] Update error handling to return traceback for `python_exec` errors

### Phase 4: Testing
- [ ] Add tests for TensorZero tool call parsing
- [ ] Add tests for `DeviceManagerProxy` with `__getattr__`
- [ ] Add tests for device name normalization
- [ ] Add tests for dual availability
- [ ] Run full test suite

## Files to Modify

1. `ai-pc-spoke/config/tensorzero.toml` - Add tool definitions
2. `ai-pc-spoke/config/tools/` - Create JSON Schema files (new directory)
3. `ai-pc-spoke/src/strawberry/skills/service.py` - Add DeviceManagerProxy, update proxies
4. `ai-pc-spoke/src/strawberry/ui/main_window.py` - Update agent loop for TensorZero tools
5. `ai-pc-spoke/tests/test_skill_service.py` - Add tests

## Design Decisions

1. **Tool name**: Use `python_exec` (underscore) to be a valid identifier
2. **Device proxy**: Use `__getattr__` for dynamic device access (devices connect/disconnect)
3. **Dual availability**: `search_skills`/`describe_function` available as both tools and methods
4. **Error format**: Python traceback for `python_exec`, structured JSON for other tool errors
5. **Device name normalization**: lowercase + underscores, collision detection on registration

## Notes

- Keep backward compatibility with existing markdown code block parsing during transition
- TensorZero's embedded gateway handles tool call parsing automatically
- The sandbox execution path (`execute_code_async`) remains the same for `python_exec`
