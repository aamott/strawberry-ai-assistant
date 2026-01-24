# Voice Subsystem Refactor Plan

## Problem Summary

The CLI `/voice` command gets stuck at "Listening..." indefinitely. Root causes identified:

1. **Blocking VAD model load**: Silero VAD loads model lazily on first `is_speech()` call, which happens inside the audio thread during LISTENING state. This blocks frame processing.

2. **Missing watchdog**: If audio stream dies or stops delivering frames, LISTENING state never exits (no timeout mechanism beyond the 30s max recording duration which requires frames to check).

3. **API key errors surface late**: Porcupine wakeword validates API key at init, but errors during `pvporcupine.create()` may not surface cleanly to the user.

4. **Duplicate code**: `voice_core.py` (745 lines) and `controller.py` (642 lines) are nearly identical implementations.

5. **Complex threading model**: Audio thread → subscriber callbacks → state transitions → background threads for STT/TTS. Hard to reason about.

## Core Components (Target Architecture)

Per user guidance, the voice subsystem should focus on three core concerns:

1. **Dynamic module loading** - TTS, STT, VAD, wakeword backends with ordered fallback
2. **Listening pipeline** - Wakeword → STT with event-based data return
3. **Speaking pipeline** - Queue-based TTS playback

## Refactoring Steps

### Phase 1: Fix Immediate Issues (Stuck Listening)

#### 1.1 Preload VAD model at start()
Move Silero model loading from lazy (first frame) to eager (during `VoiceCore.start()`).

**File**: `ai-pc-spoke/src/strawberry/voice/vad/backends/silero.py`
- Add `preload()` method
- Call it from VoiceCore._init_components()

#### 1.2 Add LISTENING watchdog
If no audio frames received for 5 seconds while in LISTENING, emit error and return to IDLE.

**File**: `ai-pc-spoke/src/strawberry/voice/voice_core.py`
- Track `_last_frame_time` in `_handle_listening()`
- Add watchdog check in a separate thread or asyncio task

#### 1.3 Improve API key error handling
Catch and surface backend initialization errors clearly.

**File**: `ai-pc-spoke/src/strawberry/voice/voice_core.py`
- Wrap backend init in try/except with user-friendly error messages
- Emit VoiceError event if init fails

### Phase 2: Remove Duplication

#### 2.1 Delete controller.py
Keep only `voice_core.py` as the canonical implementation.

**Files**:
- DELETE `ai-pc-spoke/src/strawberry/voice/controller.py`
- MODIFY `ai-pc-spoke/src/strawberry/voice/__init__.py` - remove controller imports

### Phase 3: Simplify Module Discovery

#### 3.1 Unified discovery with fallback
Create a single discovery utility that:
- Scans backend directories
- Returns backends in priority order
- Supports fallback chain (e.g., try leopard → whisper → mock)

**File**: `ai-pc-spoke/src/strawberry/voice/discovery.py` (new)

### Phase 4: Simplify Pipelines

#### 4.1 Listening pipeline refactor
Consolidate state transitions into clear, testable functions:
- `_enter_listening()` - called when wakeword detected
- `_process_speech(frame)` - VAD + buffer management
- `_exit_listening()` - called when speech ends or timeout

#### 4.2 Speaking pipeline refactor  
Add proper queue for TTS requests:
- `speak(text)` adds to queue
- Background task processes queue
- `stop_speaking()` clears queue and stops current playback

### Phase 5: Testing & Verification

#### 5.1 Add timeout/watchdog tests
Test that LISTENING state exits after timeout even without frames.

#### 5.2 Add integration tests
Test full voice flow with mock backends.

## Implementation Order

1. **[CRITICAL]** Fix Silero blocking (preload model)
2. **[CRITICAL]** Add LISTENING watchdog
3. **[HIGH]** Improve API key error messages
4. **[MEDIUM]** Delete controller.py duplicate
5. **[LOW]** Unified discovery with fallback
6. **[LOW]** Pipeline refactors

## Files to Modify

| File | Action | Priority |
|------|--------|----------|
| `voice/vad/backends/silero.py` | Add preload() | CRITICAL |
| `voice/voice_core.py` | Add watchdog, improve error handling | CRITICAL |
| `voice/controller.py` | DELETE | MEDIUM |
| `voice/__init__.py` | Update exports | MEDIUM |
| `voice/vad/base.py` | Add preload() to interface | CRITICAL |

## Success Criteria

1. `/voice` command no longer gets stuck at "Listening..."
2. Invalid API keys show clear error message at voice start
3. Tests pass: `pytest tests/test_voice_core.py -v`
4. No duplicate code between voice_core.py and controller.py

---

## Fix Applied (2026-01-23)

### Root Cause
**Silero VAD was blocking at 165ms per frame** when audio frames arrive every 30ms. This caused the audio processing thread to fall behind indefinitely, making the system appear "stuck" in LISTENING state.

### Solution
1. **JIT compilation** added to Silero VAD model (`torch.jit.script()`)
2. **Gradient computation disabled** (`torch.set_grad_enabled(False)`)
3. Result: VAD frame processing dropped from **165ms → 6ms average**

### Files Changed
- `ai-pc-spoke/src/strawberry/voice/vad/backends/silero.py` - Added JIT optimization
- `ai-pc-spoke/src/strawberry/voice/vad/base.py` - Added `preload()` interface
- `ai-pc-spoke/src/strawberry/voice/voice_core.py` - Calls `preload()` during init, added watchdog

### Tests Added
- `ai-pc-spoke/tests/test_voice_live.py` - Live integration tests with real audio + VAD

### Tests Removed (useless mock-only)
- `test_wake.py`, `test_tts.py`, `test_vad.py`, `test_stt.py`

### Verification
All 43 voice-related tests pass, including live tests that confirm:
- Audio stream delivers frames without hanging
- VAD processes at real-time speeds (6ms avg, <30ms required)
- VoiceCore LISTENING state properly exits to IDLE
