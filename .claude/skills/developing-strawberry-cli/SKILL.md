---
name: developing-strawberry-cli
description: Guide for developing with the Strawberry CLI repository - understanding architecture, adding skills, using CLI features, and testing workflows.
---

# Developing Strawberry CLI Guide

You are helping with development in the Strawberry CLI repository. This is a Python-based AI agent system with a spoke/hub architecture.

## Repository Structure

<structure>
- `ai-pc-spoke/` - Main CLI application (Spoke)
  - `src/strawberry/ui/cli/` - CLI entrypoints (__main__.py, runner.py, interactive.py)
  - `src/strawberry/skills/` - Skill system (loader.py, service.py, proxies.py)
  - `src/strawberry/spoke_core/` - Core application (app.py, skill_manager.py)
  - `skills/` - Built-in skill implementations (calculator_skill/, weather_skill/, etc.)
- `ai-hub/` - Central server for multi-device coordination
- `docs/` - Documentation including plans and architecture
</structure>

## Key Development Tasks

### Adding a New Skill

<instructions>
1. Create directory in `ai-pc-spoke/skills/<skill_name>/`
2. Create `skill.py` with class ending in "Skill"
3. Follow this pattern:
```python
class MySkill:
    """Brief description of what this skill does."""
    
    def method_name(self, param: type) -> return_type:
        """Method description.
        
        Args:
            param: Description of parameter
            
        Returns:
            Description of return value
        """
        # Implementation
        return result
```
4. Test with: `strawberry-cli --offline "device.MySkill.method_name(...)"`
5. Skills auto-discover on next CLI start
</instructions>

### CLI Development

<instructions>
The CLI has multiple modes:
- **On-demand** (default): Single messages, great for scripts
- **Interactive** (-i): REPL with session context
- **Settings** (--settings): Configuration management
- **Skill tester**: Interactive skill experimentation

Key flags:
- `-v/--verbose`: Shows skill loading timing, full tool calls, system prompts
- `-q/--quiet`: Only final answer
- `-j/--json`: Machine-readable output
- `--offline`: Force local mode (no Hub)

When modifying CLI:
1. Check `ui/cli/__main__.py` for argument parsing
2. Modify `runner.py` for on-demand changes
3. Modify `interactive.py` for interactive changes
4. Always test with `ruff check` and `pytest -qq`
</instructions>

### Testing Workflow

<instructions>
1. **Unit tests**: `pytest ai-pc-spoke/tests/ -qq`
2. **Ruff linting**: `ruff check ai-pc-spoke/src/strawberry/`
3. **CLI smoke tests**:
   - Normal: `strawberry-cli --offline "test"`
   - Verbose: `strawberry-cli -v --offline "test"`
   - JSON: `strawberry-cli --json --offline "test"`
   - Interactive: `strawberry-cli -i` (then type test message)
4. **Skill testing**: `strawberry-cli skill-tester` or `strawberry-cli skill-tester --agent`
</instructions>

## Architecture Understanding

### Skill System Flow

<architecture>
1. SkillLoader discovers skills in `skills/` directory
2. SkillService manages registration and search
3. In online mode: Hub routes skill calls via WebSocket
4. In offline mode: Spoke executes skills locally
5. Skills accessed via `device.SkillName.method()` (offline) or `devices.device_name.SkillName.method()` (online)
</architecture>

### Core Components

<components>
- **SpokeCore**: Main application orchestrator
- **SkillManager**: Facade over SkillService
- **SkillService**: Skill lifecycle management
- **SkillLoader**: Discovery and loading
- **DeviceProxy**: Local skill execution (offline)
- **HubClient**: Communication with central Hub
</components>

## Common Development Patterns

### Adding CLI Features

<examples>
To add a new CLI flag:
1. Add argument in `_build_parser()` in `ui/cli/__main__.py`
2. Pass the flag through to `run_one_shot()` or `run_interactive()`
3. Implement logic in the appropriate runner
4. Test with all combinations (verbose, quiet, json)

Example: Adding `--my-flag`:
```python
parser.add_argument(
    "--my-flag",
    action="store_true",
    help="Description of what this flag does"
)
```
</examples>

### Debugging Skills

<examples>
When a skill doesn't work:
1. Check skill discovery: `strawberry-cli -v "search_skills('')"`
2. Test directly: `strawberry-cli -v "device.MySkill.method()"`
3. Check logs: `.cli-logs/cli.log`
4. Verify skill class name ends with "Skill"
5. Ensure methods are public (no underscore prefix)
</examples>

### Working with Verbose Mode

<examples>
Verbose mode shows:
- Per-skill loading timing
- Full system prompt
- Complete tool calls and results
- Error details

Use verbose for:
- Debugging skill discovery issues
- Understanding tool execution
- Performance analysis
- Learning available skills
</examples>

## Important Files to Know

<files>
- `ai-pc-spoke/src/strawberry/ui/cli/__main__.py` - CLI entrypoint and argument parsing
- `ai-pc-spoke/src/strawberry/ui/cli/runner.py` - On-demand mode implementation
- `ai-pc-spoke/src/strawberry/ui/cli/interactive.py` - Interactive mode implementation
- `ai-pc-spoke/src/strawberry/skills/loader.py` - Skill discovery and loading
- `ai-pc-spoke/src/strawberry/skills/service.py` - Skill management
- `ai-pc-spoke/src/strawberry/spoke_core/app.py` - Core application
- `ai-pc-spoke/pyproject.toml` - Dependencies and project config
- `docs/SKILL_SYSTEM.md` - Detailed skill architecture
</files>

## Development Commands

<commands>
- Setup: `cd ai-pc-spoke && python -m venv .venv && source .venv/bin/activate && pip install -e .`
- Lint: `ruff check src/strawberry/`
- Test: `pytest tests/ -qq`
- CLI test: `strawberry-cli --offline "test message"`
- Interactive: `strawberry-cli -i`
- Skill test: `strawberry-cli skill-tester`
</commands>

## Rules and Constraints

<rules>
- ALWAYS run `ruff check` after changes
- ALWAYS run `pytest -qq` before claiming something works
- Skills must be classes ending with "Skill"
- CLI changes should support all modes (normal, verbose, quiet, json)
- Use Google-style docstrings for methods
- Check `.cli-logs/cli.log` for debugging
- Test both online and offline modes when relevant
- Never break the `--help` output
</rules>

## When to Use This Skill

<triggers>
Use this skill when:
- Adding new features to the CLI
- Creating new skills
- Debugging skill discovery issues
- Understanding the codebase architecture
- Modifying CLI behavior or flags
- Testing changes to the system
- Working with the spoke/hub architecture
</triggers>
