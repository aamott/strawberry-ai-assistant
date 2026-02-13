# Strawberry Skills

This document describes how to implement a Strawberry skill as a **repo-cloneable skill**.

A “skill repo” is any folder cloned into:

- `ai-pc-spoke/skills/<repo_name>/`

The Spoke discovers skills by importing a single entrypoint module from each repo.

## Safety / Trust Model

A skill is **Python code that runs on your machine**.

- Only install skills you trust.
- Treat skills like you would treat any Python project you run locally.

## Skill Repo Layout

Minimum working layout:

```
ai-pc-spoke/
  skills/
    my_skill_repo/
      skill.py
```

Recommended layout:

```
ai-pc-spoke/
  skills/
    my_skill_repo/
      skill.py
      README.md
      requirements.txt        # optional (manual install for now)
      strawberry_skill.json   # optional
      my_skill_repo/
        __init__.py
        helpers.py
```

### Entrypoint rules

For each repo folder `skills/<repo_name>/`, Strawberry loads the **first** file that exists from:

- `skill.py`
- `<repo_name>.py`
- `main.py`
- `__init__.py`

`skill.py` is recommended.

## Writing a Skill

### 1) Define a class ending in `Skill`

Skill classes are discovered by name:

- **Class name must end with** `Skill`

Examples:

- `WeatherSkill`
- `InternetSearchSkill`
- `MyRepoNameSkill`

### 2) Expose public methods

Methods are exposed to the LLM if:

- The method name **does not** start with `_`

### 3) Use docstrings and type hints

- The method signature and docstring are used for the LLM’s tool discovery.
- Keep docstrings short and action-oriented.

### Example `skill.py`

```python
class HelloWorldSkill:
    """Example skill."""

    def hello(self, name: str) -> str:
        """Return a greeting."""
        return f"Hello, {name}!"
```

## Calling Skills (what the LLM does)

In Strawberry, the model calls skills by generating Python and running it via `python_exec`.

- Local skills:

```python
print(device.WeatherSkill.get_current_weather("roy, ut"))
```

- When connected to the Hub (remote mode):

```python
print(devices.living_room_pc.MediaControlSkill.set_volume(level=20))
```

## Device-Agnostic Skills

Some skills produce the same result regardless of which device runs them (e.g. calculators, weather APIs, search engines). You can mark these as **device-agnostic** so the Hub auto-routes to the healthiest available device and retries on failure.

### How to declare

Add `device_agnostic = True` as a class attribute:

```python
class CalculatorSkill:
    """Basic math operations."""

    device_agnostic = True

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
```

### How the LLM calls it

For device-agnostic skills, `search_skills` returns call examples using `devices.any.`:

```python
print(devices.any.CalculatorSkill.add(a=5, b=3))
```

The Hub picks the device with the most recent heartbeat and tries the next one if it fails.

### When to use

- Pure functions (math, string processing, data conversion)
- API wrappers (weather, search, documentation lookups)
- Anything that doesn't depend on local hardware or files

### When NOT to use

- Skills that control local hardware (lights, speakers, cameras)
- Skills that read/write local files
- Skills with side effects that aren't safe to retry

> **⚠️ Side-effect warning:** If a device-agnostic skill partially executes on Device A and fails, the Hub retries on Device B. For skills with side effects (sending emails, making purchases), this could cause **duplicate actions**. Only mark a skill as `device_agnostic` if retrying on a different device is safe, or if the skill is idempotent.

## Configuration / Environment Variables

If your skill needs configuration:

- Read from environment variables (e.g. `os.environ.get("MY_API_KEY")`).
- Return a structured error when not configured.

The Spoke UI can manage env vars via Settings → Environment, which persists them into `.env` and applies them at runtime.

## Dependencies (current policy)

Right now, skills share the Spoke’s Python environment.

- Prefer stdlib when possible.
- If you need third-party dependencies, document them in `requirements.txt` and instruct users to install into the Spoke `.venv`.

Future: per-skill isolated environments.

## Testing your skill locally

### 1) Run unit tests

From `ai-pc-spoke/`:

- `strawberry-test`

### 2) Sanity-check discovery

If your repo is in `skills/<repo_name>/`, it should be discovered automatically when the Spoke loads skills.

### 3) Live LLM tests

There are live chat tests in:

- `ai-pc-spoke/tests/test_live_chat.py`

These require at least `GOOGLE_AI_STUDIO_API_KEY` configured (and optionally a running Hub or Ollama).
