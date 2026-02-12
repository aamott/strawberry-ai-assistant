# TensorZero Settings Management Plan

> **Status:** In Progress

## Goal

Move TensorZero LLM provider configuration from a static TOML file into the
SettingsManager so users can add/remove/reorder fallback LLMs through the
settings UI without hand-editing TOML.

**Before:** User edits `config/tensorzero.toml` manually to add providers.
**After:** User configures providers and fallback order in Settings; TOML is
generated automatically.

## Design: Hybrid Catalog + Ordered Fallback List (Approach C)

### Concept

Two layers of configuration:

1. **Provider Catalog** — individual settings groups for each supported LLM
   provider (API key, model name, enabled toggle). Registered as a
   `tensorzero` namespace in SettingsManager.
2. **Fallback Order** — a single ordered list (`llm.fallback_order`) that
   controls the priority chain. Only enabled providers with valid config
   appear in the generated TOML.

### Provider Catalog

Pre-defined provider groups. Each gets its own settings fields:

| Provider ID | Type (TZ)                  | Fields                          | Default Model           |
|-------------|----------------------------|---------------------------------|-------------------------|
| `hub`       | `openai` (Hub gateway)     | *(auto-configured from hub.url/hub.token)* | `strawberry-chat` |
| `google`    | `google_ai_studio_gemini`  | api_key (secret), model_name    | `gemini-2.5-flash-lite` |
| `openai`    | `openai`                   | api_key (secret), model_name    | `gpt-4o-mini`           |
| `anthropic` | `anthropic`                | api_key (secret), model_name    | `claude-sonnet-4-20250514` |
| `ollama`    | `openai` (local)           | url, model_name                 | `llama3.2:3b`           |
| `custom`    | `openai` (compatible)      | api_key (secret), api_base, model_name | *(none)* |

- `hub` is always available — its URL/token come from the existing `hub.*`
  settings. No separate enable toggle; it participates when the spoke is
  online.
- `ollama` reuses the existing `local_llm.url` / `local_llm.model` settings.
  Always enabled as the local safety net.
- Cloud providers (`google`, `openai`, `anthropic`) are enabled when their
  API key is non-empty.
- `custom` allows any OpenAI-compatible endpoint (LM Studio, Together, Groq,
  etc.).

### Fallback Order

A single `llm.fallback_order` field (LIST type) controls priority:

```
Default: ["hub", "google", "ollama"]
```

- When **online mode**: `hub` is the primary candidate variant; the rest are
  fallback variants in list order.
- When **offline mode** (`local_llm.enabled` unchecked or Hub unreachable on
  purpose): `hub` is skipped; the first non-hub entry becomes primary.
- Providers not in the list (or with missing API keys) are excluded from the
  generated TOML.

### TOML Generation

A new module `src/strawberry/llm/tensorzero_config.py` generates the TOML
from settings:

1. Read provider catalog + fallback order from SettingsManager.
2. Filter to only enabled providers (non-empty API key or local).
3. Build TOML sections:
   - `[gateway]` — static (observability off).
   - `[models.*]` — one per enabled provider.
   - `[tools.*]` — static (search_skills, describe_function, python_exec).
   - `[functions.chat]` — online function with Hub as candidate, rest as
     fallbacks.
   - `[functions.chat_local]` — offline function excluding Hub.
4. Write to `config/tensorzero.generated.toml`.
5. Return the path for `TensorZeroClient` to use.

The original `config/tensorzero.toml` is preserved as a reference/backup.
The generated file is `.gitignore`d.

### Gateway Restart on Settings Change

When any `tensorzero.*` or `llm.fallback_order` setting changes:

1. Regenerate TOML.
2. Close existing TensorZero gateway (`await self._llm.close()`).
3. Reinitialize gateway with new config (`await self._llm.start()`).

This happens in `SpokeCore._on_settings_changed()`.

### Agent Runner Changes

The current `LocalAgentRunner._select_function_name()` probes Ollama and
checks for a Gemini key to pick between `chat_local` / `chat_local_gemini`.
This is replaced:

- **Online mode** → function name `"chat"` (Hub is candidate, fallbacks
  follow).
- **Offline mode** → function name `"chat_local"` (no Hub in the chain).

The TOML generator ensures both functions always exist with the correct
variant lists, so the agent runner no longer needs to probe providers.

## Files Changed

| File | Change |
|------|--------|
| `src/strawberry/llm/tensorzero_config.py` | **New.** TOML generation from settings. |
| `src/strawberry/spoke_core/settings_schema.py` | Add `tensorzero.*` provider fields + `llm.fallback_order`. |
| `src/strawberry/llm/tensorzero_client.py` | Use generated TOML path. Add `restart()` method. |
| `src/strawberry/spoke_core/app.py` | Wire settings change → TOML regen → gateway restart. |
| `src/strawberry/spoke_core/agent_runner.py` | Simplify `_select_function_name()`. |
| `config/.gitignore` | Add `tensorzero.generated.toml`. |
| `tests/test_tensorzero_config.py` | Tests for TOML generation logic. |

## What Stays in TOML

Complex/rarely-changed settings remain in the static TOML and are **not**
exposed in the settings UI:

- Tool definitions (`[tools.*]` + JSON parameter files)
- Retry counts and delays per variant
- Timeout configuration per provider
- Gateway observability settings
- Experimentation type (always `uniform`)

## Out of Scope

- Drag-to-reorder UI (list order is managed via CLI `move` or by editing
  the list; GUI can add this later).
- Per-provider retry/timeout tuning from settings (stays in TOML).
- Streaming timeout configuration.
