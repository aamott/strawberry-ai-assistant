# Review Plan for AI PC Spoke

This document tracks the comprehensive review of the `@ai-pc-spoke` directory.

## Findings Summary

Detailed findings are available in the following documents:
- **[Architecture Review](architecture_review.md)**: Analysis of the system design, core components, and data flow.
- **[Code Quality Review](code_quality_review.md)**: Assessment of code style, patterns, and maintainability.
- **[Security Review](security_review.md)**: Critical analysis of the sandbox execution model and API key handling.
- **[Skills Review](skills_review.md)**: detailed look at the implemented skills (`WeatherSkill`, `MediaControlSkill`).
- **[Testing Review](testing_review.md)**: Overview of the test suite coverage and structure.

## Actionable Task List

### Priority: High (Critical Stability & Security)

- [ ] [Priority: High] [Difficulty: Easy] **Fix macOS Media Control**: `MediaControlSkill` assumes Spotify on macOS.
    - *Action*: Add configuration to select the media player (Spotify vs Apple Music).
- [ ] [Priority: High] [Difficulty: Medium] **Refactor HubClient Error Handling**: Ensure network timeouts and connection errors are gracefully handled in the UI (prevent freezing).

### Priority: Medium (Feature Completeness)
- [ ] [Priority: Medium] [Difficulty: Hard] **Volume Control Implementation**: `MediaControlSkill.get_volume` is simulated. Implement real volume control for Linux (PulseAudio/PipeWire) and Windows (CoreAudio APIs).
- [ ] [Priority: Medium] [Difficulty: Medium] **Dependency Management**: `playerctl` is required for Linux media control but not checked.
    - *Action*: Add a startup check in `TerminalApp` / `StrawberryApp` to warn if external dependencies are missing.
- [ ] [Priority: Medium] [Difficulty: Medium] **UI Async Integration**: Verify `qasync` integration in `StrawberryApp` covers all long-running tasks to prevent UI blocking.

### Priority: Low (Polish & Documentation)
- [ ] [Priority: Low] [Difficulty: Easy] **Docstring Completeness**: Add docstrings to `GenericSkill` methods/bases if they are missing, to help the LLM.
- [ ] [Priority: Low] [Difficulty: Easy] **Logging**: Increase logging granularity in `ConversationPipeline` to debug VAD/Wake word false positives.

## Completed Review Steps
- [x] Initial Exploration & Architecture Review
- [x] Core Logic Review (`TerminalApp`, `StrawberryApp`, `ConversationPipeline`)
- [x] Skills Review (`WeatherSkill`, `MediaControlSkill`)
- [x] Testing & QA Review
- [x] Security & Configuration Review
