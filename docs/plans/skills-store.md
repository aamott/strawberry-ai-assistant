# Skills Store Plan (Repo-cloneable skills)

## Decisions (2026-01-10)

- **Default country**: Inputs like `"city, state"` default to **US**.
- **Store rollout**: Start with **curated repos**; long-term goal is to safely support **third-party/community repos**.

## Problem Statement

Enable “skills as git repos” by allowing users to clone a skill repository into:

- `ai-pc-spoke/skills/<repo_name>/`

…and have Strawberry automatically discover and load the skill(s) from that repo.

This must remain compatible with the current skills system:

- `SkillLoader` currently loads `skills/*.py`.
- Skill methods are exposed to the LLM via the sandbox proxy (`device.<SkillName>.<method>()`).
- The `Gatekeeper` allow-lists methods based on the loader’s registered skills.

## Constraints / Honest Notes

- **Security**: Skill implementations execute as normal Python in the host process today. Auto-loading arbitrary repos is equivalent to running arbitrary code on the machine.
- **Dependencies**: If skills bring their own dependencies, we need a strategy (shared venv vs per-skill isolation).
- **Sandbox scope**: The Pyodide/Deno sandbox protects *LLM-generated code execution*, not the Python skill implementation.

## Skill Repo Contract (V1: trusted local plugin)

### Folder Layout (cloned into `skills/`)

Example:

- `ai-pc-spoke/skills/`
  - `weather_skill.py` (still supported; backwards compatible)
  - `my_cool_skill/` (cloned repo folder)
    - `skill.py` (required entrypoint in practice; see entrypoint rules)
    - `README.md`
    - `requirements.txt` (optional)
    - `strawberry_skill.json` (optional manifest; recommended)
    - `my_cool_skill/` (optional package folder for helpers)
      - `__init__.py`
      - `utils.py`

### Entrypoint Rule (single file inside repo)

Inside each repo folder, support exactly one entry module, searched in priority order:

1. `skill.py` (recommended, explicit)
2. `<repo_name>.py` (nice convention)
3. `main.py` (common)
4. `__init__.py` (package-style)

This keeps “single entry file” while allowing it to live inside the repo folder.

### Skill Class Contract

Current system recognizes skills by:

- Class name ends with `Skill`
- Public methods (non-underscore) are callable

Recommendation:

- Add a small optional base class (e.g. `strawberry.skills.api.SkillBase`) for metadata and lifecycle.
- **Do not hard-require** inheritance in V1 (retain backward compatibility):
  - **Preferred**: inherit from `SkillBase`
  - **Allowed**: plain `*Skill` class

### Optional Manifest (recommended)

`strawberry_skill.json` example:

```json
{
  "skill_id": "my_cool_skill",
  "entrypoint": "skill.py",
  "min_strawberry_version": "0.1",
  "description": "Does X",
  "env": ["SOME_API_KEY"],
  "permissions": ["network"]
}
```

In V1, `permissions` can be informational; in V2 they become enforceable.

## Loader Changes (to support repo folders cleanly)

### Current behavior

- Scans `skills/*.py` only
- Dynamic import naming: `skills.<stem>`
- Only accepts skill classes where `obj.__module__ == module_name`

### New discovery algorithm (backwards compatible)

- **Step 1**: Load existing `skills/*.py` (unchanged)
- **Step 2**: For each subdirectory `skills/<repo>/`:
  - Skip hidden dirs, `__pycache__`, etc.
  - Determine entrypoint file via:
    - manifest `entrypoint` if present, else
    - priority list (`skill.py`, `<repo>.py`, `main.py`, `__init__.py`)
  - Load only that module as the repo’s entry module

### Imports / module namespace (critical)

Two approaches:

- **Option A (simplest)**: temporarily add repo folder to `sys.path` during import.
  - Pros: easy
  - Cons: import collisions across repos; global `sys.path` mutation risk

- **Option B (cleaner; recommended)**: load each repo under a unique namespace.
  - Example namespace: `strawberry_skillrepos.<repo_name>`
  - Configure submodule search locations so helper imports work within that namespace
  - Pros: avoids collisions, cleaner long-term
  - Cons: slightly more complex implementation

**Recommendation: Option B**.

### Name collisions (Skill class names)

Since calls are `device.<SkillName>.<method>()`, collisions are fatal.

Plan:

- Enforce unique skill class names across all loaded skills.
- On collision:
  - Log a clear error with both source repo paths.
  - Skip the later one (or require user resolution).

Author guidance:

- Prefer unique class names like `<RepoName>Skill`.

## Dependencies Strategy

### V1 (fast): shared venv only

Rule:

- Skills may only use Python stdlib and packages already installed in the main `.venv`.
- If a skill needs extra dependencies, user installs them manually into `.venv`.

Pros:

- Fast implementation

Cons:

- Not truly “plug-and-play”
- Dependency conflicts over time

### V2 (store-grade): per-skill isolation

- Each repo may ship `requirements.txt` or `pyproject.toml`.
- Create per-skill venv at `.skill_venvs/<repo_name>/`.
- Run skill in a subprocess using that interpreter.
- Communicate via JSON-RPC over stdin/stdout between host and skill-runner.

Pros:

- Avoids dependency conflicts
- Sets foundation for enforcing permissions later

Cons:

- More code and operational complexity
- OS-level sandboxing still non-trivial

## Security Model (explicit)

- **Trusted mode (V1)**:
  - Cloned repos are treated like local plugins.
  - UI should show a warning: enabling a skill runs code on your machine.

- **Hardened mode (V2+)**:
  - Skills run out-of-process.
  - Allowlisted capabilities (eventually).
  - Optional signature verification (signed tags/releases).

## Weather Improvements (informed by `city + state` behavior)

### Location parsing policy

Accept:

- `"Seattle"`
- `"Seattle,US"`
- `"Portland,OR"` → auto-convert to `"Portland,OR,US"`
- `"Portland,OR,US"` (preferred explicit)

Then:

- Geocode to lat/lon → fetch weather via lat/lon (removes ambiguity and reduces 404s).

Also:

- Avoid caching `WEATHER_API_KEY` only at skill init; allow runtime changes.

## Milestones

### Milestone A — Spec + docs (no code yet)

- Define skill repo layout + entrypoint priority.
- Define naming guidelines to avoid class collisions.
- Define trusted-plugin warning language.
- Draft docs describing:
  - authoring a repo
  - helper modules layout
  - local testing
  - dependency rules

### Milestone B — Loader upgrade (V1)

- Update `SkillLoader` to:
  - scan `skills/*.py` (unchanged)
  - scan `skills/*/` for entrypoints
  - import entrypoint with unique namespace (Option B)
  - load skill classes from entrypoint
  - detect collisions and report clearly
- Add tests that create a temporary `skills/<repo>/skill.py` layout.

### Milestone C — Weather fix

- Add location normalization (`city,state` ⇒ `city,state,US`).
- Add geocoding step + lat/lon weather fetch.
- Stop caching API key at init (or add refresh logic).

### Milestone D (optional, later) — Store-grade isolation

- Per-skill venv + subprocess runner + RPC.
- Optional enable/disable + allowlist + signature pinning.
