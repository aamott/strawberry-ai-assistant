# Architecture Review: AI PC Spoke

## Overview

The AI PC Spoke is a modular voice assistant application designed to run on various platforms (Linux, etc.). It can operate in a standalone "local" mode or connect to a central "Hub" for enhanced capabilities (remote skills, shared context).

## Core Components

### 1. Entry Points
- **CLI (`TerminalApp`)**: Located in `src/strawberry/terminal.py`. Provides a text and voice interface in the terminal.
- **GUI (`StrawberryApp`)**: Located in `src/strawberry/ui/app.py`. Uses PySide6 for a system tray application with a chat window.
- **Main Wrapper**: `src/strawberry/main.py` serves as the CLI entry point.

### 2. Voice Pipeline
The `ConversationPipeline` (`src/strawberry/pipeline/conversation.py`) is the heart of the voice interaction. It implements a state machine:
- `IDLE` -> `LISTENING` (Wake Word) -> `RECORDING` (VAD) -> `PROCESSING` (STT + LLM) -> `SPEAKING` (TTS).
- It runs in its own thread/async loop management to ensure responsiveness.
- It is event-driven (`events.py`) allowing the UI to react to state changes (e.g., "Listening", "Speaking").

### 3. Skill System
The skill system (`src/strawberry/skills/`) is robust and allows for dynamic extension.
- **Service**: `SkillService` manages the lifecycle, loading, and execution of skills.
- **Execution**: Supports a secure sandbox (using Deno/Pyodide patterns, likely) with a fallback to direct Python execution (`exec`).
- **Discovery**: Skills are loaded from `src/skills` (or configured paths) and can be registered with the Hub.
- **LLM Integration**: The service generates system prompts that expose available skills to the LLM and parses "tool calls" (specifically `python_exec`) from the LLM's response.

### 4. Hub Integration
- **Client**: `HubClient` (`src/strawberry/hub/client.py`) handles communication with the central server.
- **Features**: Registration of device skills, heartbeat, and remote skill execution (allowing one device to control another).

### 5. Configuration
- Uses `pydantic` settings or similar (referenced as `Settings` in `config`).

## Architectural Strengths
- **Modularity**: Clear separation between Audio, Pipeline, Skills, and UI.
- **Flexibility**: Supports both local-only and hub-connected modes.
- **Safety**: Attempts to use a sandbox for skill execution, reducing the risk of executing arbitrary code from the LLM.
- **Event-Driven**: The pipeline's event system decouples the core logic from the presentation layer (CLI/GUI).

## Areas for Improvement (Preliminary)
- **Complexity in Skill Service**: `SkillService` handles a lot of responsibilities (loading, executing, parsing, hub comms). It might benefit from further decomposition.
- **Direct Execution Fallback**: The fallback to `exec()` in `SkillService.execute_code` is permissive. While necessary for local dev/legacy, it presents a security risk if not carefully monitored.
- **Dependency Management**: Voice features require heavy dependencies (PyTorch, etc.) which are optional, but managing them might be tricky for end-users.

## Next Steps
- Deep dive into `HubClient` to understand protocol and error handling.
- Review specific skills in `src/skills` for code quality and security.
- Audit `SkillService`'s sandbox implementation.
