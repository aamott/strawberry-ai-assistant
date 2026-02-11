# MCP Tool Search Improvement Plan

## Problem

When a user says "Set the short lamp to red", the LLM searches for skills using terms like "color", "light", "light color". Despite Home Assistant MCP tools like `HassLightSet` being available, the LLM often fails to find them — resulting in "empty content blocks" errors. The core issue is that MCP tool names (e.g. `HassTurnOn`, `HassLightSet`) and their terse descriptions don't contain the everyday words users naturally use ("lamp", "color", "brightness", "smart home").

## Root Cause Analysis

The search pipeline matches query words against:
- `function_name` (e.g. `HassTurnOn`)
- `class_name` (e.g. `HomeAssistantSkill`)
- `docstring` (e.g. "Turn on a device in Home Assistant")

A query like "color" doesn't appear in any of those fields for `HassLightSet`. The word "color" only exists deep in the tool's `inputSchema` property descriptions — which the search never sees.

## Inspiration: Claude's Tool Search Tool

Claude AI recently released a [tool search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) standard (saved in `docs/reference/Claude Tool search tool.md`). Key ideas:

- **Deferred loading**: Only 3-5 core tools are loaded upfront; the rest are discovered on demand via search. We already do this — `search_skills`, `describe_function`, and `python_exec` are the only tools the LLM sees.
- **Search across all metadata**: Claude's tool search searches tool names, descriptions, **argument names**, and **argument descriptions**. Our search only covers names and docstrings.
- **Category hints in system prompt**: Claude recommends adding "You can search for tools to interact with Slack, GitHub, and Jira" to the system prompt. We have examples in the prompt but no dynamic category listing.

## What's Already Built

Investigation reveals that most of the infrastructure is already in place:

### Spoke side (ai-pc-spoke)

1. **`class_builder.py` → `_build_class_summary()`** — Already aggregates all tool descriptions + parameter names + parameter descriptions into a single keyword string per MCP server. Stored as `__class_summary__` on the generated class.

2. **`class_builder.py` → `build_skill_class()`** — Already accepts a `user_description` parameter and passes it to `_build_class_summary()`.

3. **`skill.py` → `_discover_and_build()`** — Already reads an optional `"description"` field from each server entry in `mcp_config.json` and passes it through as `user_descriptions`.

4. **`loader.py` → `SkillInfo.get_registration_data()`** — Already prepends `[__class_summary__]` to each method's docstring before sending to the Hub, so the Hub's keyword search can match class-level terms.

5. **`service.py` → `_DeviceProxy.search_skills()`** — Already includes `__class_summary__` in the searchable text alongside method name, skill name, signature, and docstring.

### Hub side (ai-hub)

6. **`skill_service.py` → `DevicesProxy.search_skills()`** — Searches against `s.docstring`, which includes the prepended `[class_summary]` from registration. So Hub-side search should already benefit from the enriched docstrings.

7. **`database.py` → `Skill.docstring`** — Text column that stores the enriched docstring (with class summary prefix).

## What's Missing / Needs Verification

Despite the infrastructure being in place, the search still fails for "set the short lamp to red". Possible reasons:

### A. The `mcp_config.json` may lack a `"description"` field

The `_build_class_summary()` function aggregates tool descriptions and param metadata automatically, but a user-provided `"description"` like `"Smart home control: lights, switches, locks, climate, color, brightness, temperature"` would dramatically improve search hits. This is optional and may not be configured.

### B. The auto-generated summary may not contain the right keywords

`_build_class_summary()` concatenates raw tool descriptions and parameter names. For Home Assistant, this might produce something like:
```
Turn on a device in Home Assistant. name area floor domain Turn off a device...
HassLightSet Set light attributes. name color_name brightness color_temp...
```

The word "color" might appear as `color_name` or `color_temp` — but "lamp" and "red" won't appear at all. The summary is only as good as the MCP tool schemas.

### C. Stop-word filtering may be too aggressive

The current stop words include `"set"` and `"on"`. So "set the short lamp to red" becomes `["short", "lamp", "red"]` after filtering. None of those words appear in HA tool metadata.

### D. The system prompt searching tips may not guide the LLM well enough

The prompt says "search by action or verb, not by specific entity/object names" and gives examples like "search 'turn on' not 'lamp'". But the LLM still searches "color" and "light color" — which are reasonable queries that should work.

### E. No dynamic category listing in system prompt

The system prompt has hardcoded examples for HomeAssistant, Weather, Calculator, and Context7. But it doesn't dynamically list what MCP servers are available and what categories they cover.

## Implementation Plan

### Phase 1: Verify and fix the existing pipeline

**Goal**: Confirm that `__class_summary__` actually flows through to the Hub and that search works end-to-end.

1. **Add a `"description"` to Home Assistant in `mcp_config.json`** — e.g. `"description": "Smart home control: lights, switches, locks, climate, scenes, color, brightness, temperature, media"`. This is a config change, not a code change.

2. **Verify the class summary content** — Use the Skill Interaction Tester (see "Getting Started" below) to inspect what `__class_summary__` actually contains for HomeAssistantSkill. Run `search_skills color` and `search_skills light` and check if results appear.

3. **Verify Hub-side registration** — Check that the enriched docstring (with `[class_summary]` prefix) is stored in the Hub's `skills` table. Query the DB or add temporary logging.

4. **Fix any gaps found** — If the summary doesn't contain useful keywords, or if the registration doesn't preserve them, fix the pipeline.

### Phase 2: Improve search quality

5. **Expand the class summary with semantic keywords** — In `_build_class_summary()`, consider extracting additional keywords from tool names by splitting camelCase/PascalCase (e.g. `HassLightSet` → `hass light set`, `HassTurnOn` → `hass turn on`). This makes tool name fragments searchable.

6. **Add enum values to the summary** — MCP tool schemas sometimes have `enum` constraints on parameters (e.g. `color_name` might list `"red"`, `"blue"`, `"green"`). Including these in the summary would let "red" match `HassLightSet`.

7. **Consider relaxing stop-word filtering** — `"set"` is currently a stop word, but "set light" is a valid search. Consider removing `"set"` from the stop words, or only filtering stop words when the query has 3+ words.

### Phase 3: Dynamic system prompt enrichment

8. **Add a dynamic "Available Skill Categories" section to the system prompt** — Instead of hardcoded examples, generate a section like:
   ```
   Available skill categories:
   - HomeAssistantSkill: Smart home control (lights, switches, locks, climate, color, brightness)
   - WeatherSkill: Weather forecasts and conditions
   - Context7Skill: Documentation lookup
   - CalculatorSkill: Math operations
   ```
   This helps the LLM know what to search for without consuming excessive tokens.

9. **Source category info from `__class_summary__`** or `__doc__` — The spoke already has this data; it just needs to be surfaced in the prompt.

### Phase 4: Test and verify

10. **Run all tests** — `pytest` for both spoke and hub, `ruff check --fix`.

11. **Live test the target scenario** — "Set the short lamp to red" should find `HassLightSet` on the first search and execute successfully.

12. **Test edge cases** — "Turn on the lamp", "What color is the light?", "Set brightness to 50%", "Lock the front door".

## Getting Started

### Skill Interaction Tester (offline mode)

The Skill Interaction Tester lets you "be" the LLM and see exactly what it sees. Use it to debug search results and verify the class summary content.

```bash
cd ai-pc-spoke

# Run the tester
PYTHONPATH=src .venv/bin/python -m strawberry.testing.skill_tester_main
```

Commands to try:
```
llm> search_skills color
llm> search_skills light
llm> search_skills turn on
llm> search_skills smart home
llm> /skills                    # List all loaded skills and methods
llm> /prompt                    # See the full system prompt
```

See `docs/Skill_Interaction_Tester.md` for full documentation.

### Test CLI (offline + online modes)

The test CLI runs the full agent loop with a real LLM. Use it to verify end-to-end behavior.

```bash
cd ai-pc-spoke

# Offline mode (local LLM via Ollama or Gemini)
PYTHONPATH=src .venv/bin/python -m strawberry.ui.test_cli --compact --offline

# Online mode (via Hub)
PYTHONPATH=src .venv/bin/python -m strawberry.ui.test_cli --compact
```

Test prompts:
```
> Set the short lamp to red
> Turn on the short lamp
> Set brightness to 50%
> What's the weather in Roy, UT?
```

### Hub (for online mode testing)

```bash
cd ai-hub
.venv/bin/python -m uvicorn hub.main:app --host 0.0.0.0 --port 8000
```

### Running tests

```bash
# Spoke tests
cd ai-pc-spoke
.venv/bin/python -m pytest -qq

# Hub tests
cd ai-hub
.venv/bin/python -m pytest -qq

# Ruff
cd ai-pc-spoke && .venv/bin/ruff check --fix src/ skills/ tests/
cd ai-hub && .venv/bin/ruff check --fix src/ tests/
```

## Files to Modify

| File | What | Phase |
|------|------|-------|
| `config/mcp_config.json` | Add `"description"` to HA server entry | 1 |
| `ai-pc-spoke/skills/mcp_skill/class_builder.py` | Expand `_build_class_summary()` with camelCase splitting + enum values | 2 |
| `ai-hub/src/hub/skill_service.py` | Possibly adjust stop words; add dynamic categories to prompt | 2-3 |
| `ai-pc-spoke/src/strawberry/skills/service.py` | Possibly adjust stop words; add dynamic categories to prompt | 2-3 |

## Files for Reference (read-only)

| File | What it does |
|------|-------------|
| `ai-pc-spoke/skills/mcp_skill/skill.py` | MCP entrypoint: reads config, connects, discovers, builds classes |
| `ai-pc-spoke/skills/mcp_skill/mcp_client.py` | Thin async wrapper around MCP SDK |
| `ai-pc-spoke/src/strawberry/skills/loader.py` | Skill loading + `get_registration_data()` with `__class_summary__` |
| `ai-pc-spoke/src/strawberry/skills/registry.py` | Skill registration with Hub |
| `ai-hub/src/hub/database.py` | Hub DB schema (Skill table with docstring column) |
| `ai-hub/src/hub/routers/chat.py` | Hub agent loop |
| `ai-hub/config/tensorzero.toml` | Hub tool definitions for TensorZero |
| `docs/reference/Claude Tool search tool.md` | Claude's tool search standard (inspiration) |
| `docs/Skill_Interaction_Tester.md` | Tester documentation |

## Risk / Open Questions

- **MCP schema quality varies** — Some MCP servers have minimal tool descriptions. The auto-generated summary is only as good as the upstream schemas. User-provided `"description"` in `mcp_config.json` is the escape hatch.
- **Token budget for dynamic categories** — Adding a category listing to the system prompt uses tokens. Keep it compact (one line per skill class, ~50 tokens total for 5 classes).
- **Stop-word tuning** — Removing `"set"` from stop words could cause false positives in other contexts. Test carefully.
- **Hub DB migration** — If we add a dedicated `class_summary` column to the `Skill` table (instead of embedding it in `docstring`), we need an ALTER TABLE migration. The current approach of prepending to `docstring` avoids this.
