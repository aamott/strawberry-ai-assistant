# VoiceCore Implementation Plan

## Context Files to Read
Before starting implementation, read these files to understand the architecture:
1. **[SUMMARY.md](../SUMMARY.md)** - Project overview (Hub, Spoke, Skills, etc.)
2. **[ai-pc-spoke/README.md](../ai-pc-spoke/README.md)** - Spoke quick start and structure
3. **[docs/plans/voice_ui.md](./voice_ui.md)** - VoiceCore API design spec
4. **[docs/plans/folder-layout.md](./folder-layout.md)** - Target folder structure

## Goal
Refactor the existing `VoiceController` into a cleaner `VoiceCore` API and create a standalone `VoiceInterface` example.

## Current State
- `VoiceController` (in `voice/controller.py`) is 600+ lines mixing low-level pipeline management with high-level voice interface concerns
- The Qt UI and CLI directly instantiate and manage `VoiceController`
- Wake word, VAD, STT, and TTS are correctly abstracted as backends

## Target Architecture

### VoiceCore (`voice/voice_core.py`)
A clean, importable class for voice processing that can be used by any UI:

```python
class VoiceCore:
    """Voice processing engine - manages STT/TTS/VAD/WakeWord pipelines."""
    
    # Lifecycle
    def start() -> None
    def stop() -> None
    
    # Listening pipeline control
    def start_listening() -> None          # Start wake word detection
    def stop_listening() -> None           # Stop wake word detection
    def trigger_wakeword() -> None         # Skip wake word, go straight to STT
    
    # Speaking pipeline control  
    def speak(text: str) -> None           # Queue text for TTS
    def stop_speaking() -> None            # Interrupt current TTS
    
    # State
    def get_state() -> VoiceState          # Current state
    
    # Events (callback-based)
    def add_listener(callback: Callable[[VoiceEvent], None]) -> None
    def remove_listener(callback: Callable[[VoiceEvent], None]) -> None
```

### VoiceInterface (`ui/voice_interface/voice_interface.py`)
Example voice-only app that wires VoiceCore to SpokeCore:

```python
class VoiceInterface:
    """Voice-only interface - wires VoiceCore events to SpokeCore."""
    
    def __init__(self, spoke_core: SpokeCore, voice_core: VoiceCore):
        self._spoke_core = spoke_core
        self._voice_core = voice_core
        self._wire_events()
    
    def _wire_events(self):
        # When STT transcription completes → send to SpokeCore
        # When SpokeCore responds → send to VoiceCore.speak()
        pass
    
    def start(self): ...
    def stop(self): ...
```

---

## Implementation Steps

### Phase 1: Create VoiceCore (refactor from VoiceController)

#### Step 1.1: Create `voice/voice_core.py`
- Extract the core voice pipeline logic from `controller.py`
- Implement the clean public API defined above
- Keep internal state machine (STOPPED, WAITING, LISTENING, PROCESSING, SPEAKING)
- Use composition for pipeline components (STT, TTS, VAD, WakeWord, Audio)

**Files to modify:**
- [NEW] `ai-pc-spoke/src/strawberry/voice/voice_core.py`
- [MODIFY] `ai-pc-spoke/src/strawberry/voice/__init__.py` - export VoiceCore

#### Step 1.2: Define VoiceEvent types
Ensure `voice/events.py` has all needed event types:
```python
@dataclass
class VoiceTranscription:
    text: str
    confidence: float

@dataclass  
class VoiceStateChanged:
    old_state: VoiceState
    new_state: VoiceState

@dataclass
class VoiceError:
    error: str
    
# etc.
```

**Files to modify:**
- [MODIFY] `ai-pc-spoke/src/strawberry/voice/events.py` (if needed)

#### Step 1.3: Migrate existing tests
Update tests to use VoiceCore instead of VoiceController.

**Files to modify:**
- [MODIFY] `ai-pc-spoke/tests/test_voice_controller.py` → `test_voice_core.py`
- [MODIFY] `ai-pc-spoke/tests/test_voice_integration.py`

### Phase 2: Update Existing UIs

#### Step 2.1: Update Qt UI to use VoiceCore
The `main_window.py` should use the new VoiceCore API.

**Files to modify:**
- [MODIFY] `ai-pc-spoke/src/strawberry/ui/qt/main_window.py`

#### Step 2.2: Update CLI to use VoiceCore
The CLI should also use the new VoiceCore API.

**Files to modify:**
- [MODIFY] `ai-pc-spoke/src/strawberry/ui/cli/main.py`

### Phase 3: Create VoiceInterface Example

#### Step 3.1: Create VoiceInterface class
A minimal example showing how to wire VoiceCore + SpokeCore for voice-only interaction.

**Files to create:**
- [NEW] `ai-pc-spoke/src/strawberry/ui/voice_interface/__init__.py`
- [NEW] `ai-pc-spoke/src/strawberry/ui/voice_interface/voice_interface.py`
- [NEW] `ai-pc-spoke/src/strawberry/ui/voice_interface/__main__.py` (CLI entry point)

#### Step 3.2: Add entry point
Add a console script entry point for the voice interface.

**Files to modify:**
- [MODIFY] `ai-pc-spoke/pyproject.toml` - add `strawberry-voice` entry point

#### Step 3.3: Add tests
Add tests for VoiceInterface.

**Files to create:**
- [NEW] `ai-pc-spoke/tests/test_voice_interface.py`

### Phase 4: Cleanup

#### Step 4.1: Deprecate VoiceController  
Keep VoiceController as an alias for backwards compatibility, or remove if UIs are updated.

**Files to modify:**
- [MODIFY] `ai-pc-spoke/src/strawberry/voice/controller.py` - add deprecation warning or delete
- [MODIFY] `ai-pc-spoke/src/strawberry/voice/__init__.py` - update exports

#### Step 4.2: Update documentation
- [MODIFY] `ai-pc-spoke/README.md` - document VoiceCore and VoiceInterface

---

## State Machine Reference

From `voice_ui.md`:

```
States:
- STOPPED: Not listening for wakeword
- WAITING: Waiting for wakeword
- LISTENING: Running STT
- PROCESSING: Processing chat and TTS (wakeword can interrupt)
- SPEAKING: Speaking text (wakeword can interrupt)

Transitions:
- STOPPED → WAITING: on start_listening()
- WAITING → LISTENING: on wakeword detect or trigger_wakeword()
- LISTENING → PROCESSING: after STT completes
- PROCESSING → SPEAKING: when TTS begins playback
- SPEAKING → WAITING: when TTS finishes (or PROCESSING if another wakeword)
- Any → STOPPED: on stop_listening()
```

---

## Verification Plan

### Automated Tests
```bash
# Run all voice-related tests
strawberry-test -k voice

# Run specific test files
pytest tests/test_voice_core.py -v
pytest tests/test_voice_interface.py -v
```

### Manual Verification
1. Run `strawberry-voice` and verify wake word detection works
2. Speak a query and verify it transcribes and gets a response  
3. Verify response is spoken back via TTS
4. Test PTT (push-to-talk) mode by calling `trigger_wakeword()`
5. Test interrupt behavior during TTS playback

---

## Notes

- The listening pipeline runs independently of the speaking pipeline
- When wake word is detected during speaking, it interrupts and starts listening
- VAD runs only during STT to detect speech end
- A single audio stream is shared between wake word and STT
