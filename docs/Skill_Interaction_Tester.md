# Skill Interaction Tester

An interactive CLI tool that lets you **"be" the LLM** — see the exact system prompt, tool schemas, and issue tool calls (`search_skills`, `describe_function`, `python_exec`) against real loaded skills. Shows raw results exactly as the LLM would receive them.

## Why This Exists

When the LLM interacts with skills, it sees a system prompt, tool definitions, and tool results in specific formats. If any of these are unintuitive — confusing search output, unexpected JSON wrapping, awkward code requirements — the LLM will struggle. This tool lets a human step into the LLM's shoes and audit the experience firsthand.

**Things to look for:**
- Can you find the right skill from `search_skills` output alone?
- Does `python_exec` output match what the Python function actually returns?
- Is multi-line code easy to write, or does the format fight you?
- Are error messages clear enough to self-correct?

## Quick Start

```bash
cd ai-pc-spoke

# Via the unified CLI (recommended)
strawberry-cli skill-tester

# With a custom skills directory
strawberry-cli skill-tester --skills-dir /path/to/skills

# Or directly via module entrypoint
.venv/bin/python -m strawberry.testing.skill_tester
```

---

## Agent Mode (for AI coding agents)

A machine-parseable JSON-line interface designed for AI coding agents to
experiment with skills programmatically. No ANSI, no prompts — just
structured JSON on stdin/stdout.

### Quick Start

```bash
# Start agent mode (loads skills once, reads commands from stdin)
strawberry-cli skill-tester --agent

# With a custom skills directory
strawberry-cli skill-tester --agent --skills-dir /path/to/skills

# Resume a previous session
strawberry-cli skill-tester --agent --session session.json
```

### Protocol

- **stdin**: One JSON object per line (command).
- **stdout**: One JSON object per line (response).
- **stderr**: Human-readable status messages during startup only.

On startup, the first stdout line is a `ready` response:
```json
{"status": "ok", "type": "ready", "data": {"skills_count": 12, "tool_schemas": ["search_skills", "describe_function", "python_exec"], "session_entries": 0, "commands": [...]}}
```

### Commands

| Command | Description |
|---------|-------------|
| `{"command": "get_system_prompt"}` | Exact system prompt the LLM receives |
| `{"command": "get_tool_schemas"}` | Tool JSON schemas as sent to the LLM |
| `{"command": "get_skills"}` | Structured list of loaded skills + methods |
| `{"command": "tool_call", "tool": "<name>", "arguments": {...}}` | Execute a tool call (search_skills, describe_function, python_exec) |
| `{"command": "get_history"}` | Full conversation history (tool calls + results) |
| `{"command": "clear_history"}` | Clear conversation history |
| `{"command": "save_session", "path": "file.json"}` | Save session for later continuation |
| `{"command": "load_session", "path": "file.json"}` | Load a previous session |
| `{"command": "reload"}` | Reload skills from disk |
| `{"command": "shutdown"}` | Exit cleanly |

### Example: Full agent workflow

```bash
# Start the agent tester as a background process
strawberry-cli skill-tester --agent &

# 1. See what the LLM sees
echo '{"command": "get_system_prompt"}' 
echo '{"command": "get_tool_schemas"}'

# 2. Search for skills (exactly as the LLM would)
echo '{"command": "tool_call", "tool": "search_skills", "arguments": {"query": "weather"}}'

# 3. Get details about a skill
echo '{"command": "tool_call", "tool": "describe_function", "arguments": {"path": "WeatherSkill.get_current_weather"}}'

# 4. Execute code (exactly as the LLM would)
echo '{"command": "tool_call", "tool": "python_exec", "arguments": {"code": "print(device.WeatherSkill.get_current_weather(location=\"Seattle\"))"}}'

# 5. Save session to continue later
echo '{"command": "save_session", "path": "my_session.json"}'

# 6. Shut down
echo '{"command": "shutdown"}'
```

### Session Continuity

Sessions let you save and resume a conversation:

1. **Save**: `{"command": "save_session", "path": "session.json"}` writes the full history.
2. **Resume**: Start with `--session session.json` to auto-load history on startup.
3. **Continue**: New tool calls append to the restored history.

This is useful for iterative experimentation — make some calls, save,
adjust your approach, resume where you left off.

### Response Format

Success:
```json
{"status": "ok", "type": "tool_result", "data": {"tool": "search_skills", "arguments": {"query": "calc"}, "result": "Found 2 results:\n  CalcSkill.add(a: int, b: int) -> int — Add two numbers.\n  CalcSkill.multiply(a: int, b: int) -> int — Multiply two numbers.", "elapsed_ms": 1.23}}
```

Error:
```json
{"status": "error", "message": "Missing 'tool' field in tool_call command"}
```

### Files

| File | Purpose |
|------|---------|
| `src/strawberry/testing/skill_tester_agent.py` | Agent-mode implementation |
| `tests/test_skill_tester_agent.py` | 36 automated tests |

---

## Interactive Mode (for humans)

## Commands

| Command | Description |
|---------|-------------|
| `/prompt` | Show the full system prompt the LLM sees |
| `/tools` | Show tool definitions (JSON schemas from `config/tools/`) |
| `/skills` | List all loaded skills and their methods |
| `/reload` | Reload skills from disk (pick up changes without restarting) |
| `/history` | Show tool call history for this session |
| `/clear` | Clear tool call history |
| `/call SkillName.method arg=val` | Call a skill directly for comparison |
| `/help` | Show help |
| `/quit` | Exit |

## Tool Calls

Type tool calls directly at the `llm>` prompt, just like the LLM would issue them:

```
llm> search_skills
llm> search_skills weather
llm> describe_function WeatherSkill.get_current_weather
llm> python_exec print(device.CalculatorSkill.add(a=5, b=3))
llm> exec                          # Opens multi-line code editor
```

### Multi-Line Code Editor

Type `exec` to open the multi-line editor. Write Python code line by line and type `END` on its own line to execute:

```
llm> exec
Enter Python code (type END on its own line to finish):
... result = device.CalculatorSkill.add(a=10, b=20)
... print(f"The answer is {result}")
... END
```

### Direct Comparison Mode

Use `/call` to call a skill method directly (bypassing `python_exec`) and see a side-by-side comparison of the direct return value vs. what `python_exec` would show the LLM:

```
llm> /call CalculatorSkill.add a=5 b=3
```

This shows:
1. The direct Python return value (`repr()`)
2. The equivalent `python_exec` code
3. What `python_exec` would return to the LLM
4. Whether the outputs match or differ

## What Each Display Shows

### `/prompt` — System Prompt
The exact string sent as the system message to the LLM, including the `{skill_descriptions}` section filled in with all loaded skills. This is what shapes the LLM's understanding of what tools are available and how to use them.

### `/tools` — Tool Schemas
The JSON schemas from `config/tools/*.json` that define the parameters for each tool. These are what TensorZero sends to the LLM as the tool definitions.

### Tool Results
Every tool result is displayed with:
- **Raw output** — the exact string the LLM receives back
- **Timing** — how long the call took in milliseconds
- **Type and length** — the Python type and character count of the result

## Files

| File | Purpose |
|------|---------|
| `src/strawberry/testing/skill_tester.py` | Main implementation |
| `src/strawberry/testing/skill_tester_main.py` | Module entrypoint |
| `tests/test_skill_tester.py` | Automated tests (24 tests) |

## Architecture

The tester reuses the existing `SkillService` and `SkillLoader` infrastructure. It creates a `SkillService` with `use_sandbox=False` and `allow_unsafe_exec=True` for direct execution, then calls `execute_tool()` — the same method the agent runner uses. This ensures the tester shows exactly the same behavior the LLM experiences.

```
SkillTester
  └── SkillService (use_sandbox=False)
        ├── SkillLoader (loads skills from disk)
        ├── _DeviceProxy (exposes device.SkillName.method())
        └── execute_tool() (handles search_skills, describe_function, python_exec)
```

---

# Suggestions for Improving Skill Interaction Formats

After building and testing this tool, here are concrete suggestions for improving how the LLM interacts with skills. These are issues that became apparent when stepping into the LLM's perspective.

## 1. `search_skills` Returns Raw JSON — Should Be Human/LLM-Readable Text

**Current behavior:** `_execute_search_skills()` returns `json.dumps(results, indent=2)`, producing output like:
```json
[
  {
    "path": "CalculatorSkill.add",
    "signature": "add(a: int, b: int) -> int",
    "summary": "Add two numbers."
  },
  ...
]
```

**Problem:** This is verbose and wastes tokens. The LLM doesn't need JSON structure — it needs to quickly scan for the right skill. The JSON keys (`"path"`, `"signature"`, `"summary"`) are redundant noise.

**Suggestion:** Return a compact text table instead:
```
Found 3 results:
  CalculatorSkill.add(a: int, b: int) -> int — Add two numbers.
  CalculatorSkill.multiply(a: int, b: int) -> int — Multiply two numbers.
  WeatherSkill.get_current_weather(location: str) -> Dict — Get current weather.
```

This is ~60% fewer tokens, easier to scan, and the LLM can immediately pick a path for `describe_function` or write `python_exec` code. The JSON format is only needed for the Hub's remote API — local results should be text.

## 2. `python_exec` Auto-Wraps Last Expression in `repr()` — Can Be Confusing

**Current behavior:** `_prepare_python_exec_code()` rewrites bare expressions to `print(repr(last_expr))`. So `device.CalculatorSkill.add(a=5, b=3)` becomes `print(repr(strawberry_last))`, which outputs `8` (the repr of the int).

**Problem:** For simple types this is fine, but for dicts/lists the `repr()` output differs from what `str()` or `print()` would show. For example, a weather skill returning a dict would show `repr()` output with single quotes and Python-specific formatting, which can confuse the LLM into thinking the result is a string literal rather than structured data.

**Suggestion:** Use `str()` instead of `repr()` for the auto-print, or better yet, use a custom formatter:
```python
# Instead of repr(), use a smarter formatter
if isinstance(result, (dict, list)):
    print(json.dumps(result, indent=2, default=str))
else:
    print(str(result))
```

This gives the LLM clean, predictable output regardless of return type.

## 3. `search_skills` Matching Strategy Could Surface Better Results

**Current behavior:** All-words match first, then falls back to any-word match. This is good for precision, but the LLM often searches with natural language phrases like "get the weather" or "turn on lights."

**Problem:** Searching "get the weather" matches on "get", "the", and "weather" — but "the" matches almost everything, diluting results. Common stop words pollute the search.

**Suggestion:** Strip common stop words (`the`, `a`, `an`, `is`, `to`, `for`, `of`, `in`, `on`, `it`) before matching:
```python
STOP_WORDS = {"the", "a", "an", "is", "to", "for", "of", "in", "on", "it", "and", "or"}
query_words = [w for w in query.lower().split() if w not in STOP_WORDS]
```

## 4. Error Messages from `python_exec` Could Include Fix Hints

**Current behavior:** Errors return the raw exception message, e.g., `"Execution error: name 'import' is not defined"`.

**Problem:** The LLM doesn't know *why* `import` failed (it's blocked by RestrictedPython). It may retry the same approach.

**Suggestion:** Wrap common errors with actionable hints:
```python
HINTS = {
    "import": "Imports are not allowed in python_exec. All skill methods are available via device.<SkillName>.<method>().",
    "open": "File I/O is not allowed in python_exec.",
    "NameError": "This name is not available. Use device.<SkillName>.<method>() to call skills.",
}
```

## 5. `describe_function` Output Could Include Usage Examples

**Current behavior:** Returns the function signature and docstring:
```
def add(a: int, b: int) -> int:
    """Add two numbers."""
```

**Problem:** The LLM still has to figure out how to call this via `python_exec`. It needs to construct `device.CalculatorSkill.add(a=5, b=3)` from the signature, which is an extra reasoning step.

**Suggestion:** Append a ready-to-use example:
```
def add(a: int, b: int) -> int:
    """Add two numbers."""

Example:
  python_exec(code="print(device.CalculatorSkill.add(a=5, b=3))")
```

This eliminates a reasoning step and reduces tool-call errors.

## 6. MCP Skills Show `**kwargs` Signatures — Not Useful

**Current behavior:** MCP skills built via `class_builder.py` have methods with `(**kwargs) -> Any` signatures because the actual parameters come from the MCP tool schema.

**Problem:** When the LLM sees `HassTurnOn(**kwargs) -> Any`, it has no idea what arguments to pass. It must call `describe_function` first every time, adding an extra round-trip.

**Suggestion:** Inject the MCP tool's `inputSchema` properties into the generated method signature so the LLM sees real parameter names:
```python
# Instead of: HassTurnOn(**kwargs) -> Any
# Generate:   HassTurnOn(name: str, area: str = None) -> Any
```

This would require `class_builder.py` to parse the MCP tool's JSON schema and build a proper signature string, even if the underlying implementation still uses `**kwargs`.

## Priority Order

| # | Suggestion | Impact | Effort |
|---|-----------|--------|--------|
| 1 | Text search results instead of JSON | High — saves tokens, faster LLM reasoning | Low |
| 6 | MCP skill signatures | High — eliminates blind `describe_function` calls | Medium |
| 5 | Usage examples in `describe_function` | Medium — fewer tool-call errors | Low |
| 4 | Error hints in `python_exec` | Medium — faster error recovery | Low |
| 2 | Smarter auto-print formatting | Medium — cleaner output for complex types | Low |
| 3 | Stop-word filtering in search | Low-Medium — marginal improvement | Low |
