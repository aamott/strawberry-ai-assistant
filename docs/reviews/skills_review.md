# Skills Review

## Overview

The `skills` directory contains the capability modules for the Strawberry AI Spoke. Each skill is typically a directory containing a `skill.py` file with one or more classes.

## Reviewed Skills

### 1. WeatherSkill (`skills/weather_skill/skill.py`)
- **Quality**: High.
- **Features**: Current weather and forecast.
- **Implementation**:
  - Uses `requests` to fetch data from OpenWeatherMap.
  - robust error handling (checking API key, network errors).
  - Input validation for location strings.
  - Returns structured dictionaries, making it easy for the LLM to parse.
- **Security**: Reads API key from environment variable `WEATHER_API_KEY`.

### 2. MediaControlSkill (`skills/media_control_skill/skill.py`)
- **Quality**: Medium/Proof-of-Concept.
- **Features**: Play, pause, next/prev track, volume (simulated).
- **Implementation**:
  - Uses `platform` to detect OS.
  - **Linux**: Relies on `playerctl` (external dependency).
  - **Windows**: Uses PowerShell to send keypresses.
  - **macOS**: Hardcoded to control "Spotify" via AppleScript.
- **Issues**:
  - Fragile cross-platform support. The macOS implementation assumes Spotify.
  - Volume control is simulated or empty for some platforms.

## General Observations
- **Structure**: Consistent use of classes and docstrings.
- **Discovery**: `SkillLoader` (in `src`) likely relies on inspecting these classes and their methods.
- **Dependencies**: Some skills introduce system-level dependencies (`playerctl`) that aren't managed by `pip`.

## Recommendations
- **Media Control**: Abstract the media player backend logic. Allow configuration for the preferred media player on macOS (Music vs Spotify).
- **Dependency Checks**: functionality should degrade gracefully if system dependencies (like `playerctl`) are missing.
- **Testing**: Add unit tests for skills, mocking the external calls (requests, subprocess).
