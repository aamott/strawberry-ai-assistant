# Voice UI Implementation Review

> **Focus Areas**: Implementation quality, simplicity, maintainability, user experience

---

## Critical Bugs

- [x] **Voice and text chat don't share conversation history** ✅ FIXED
  - **Priority:** HIGH
  - **Difficulty:** Medium
  - **Applicable Filepaths:**
    - [app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/core/app.py#L222-L224)
    - [main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py#L75)
  - **Description:** `SpokeCore._voice_agent_response` creates a **new temporary session** for each voice utterance (line 223). This means voice interactions don't see prior text chat history, and vice versa. The user expects: type → response → say "jarvis..." + followup → spoken response (visible in UI) → type again, all in one continuous conversation.
  - **Fix:** 
    1. Add a `voice_session_id` property to `SpokeCore` that can be set by the UI
    2. Have voice use the active session instead of creating a new one
    3. Alternatively, have `MainWindow` pass its `_conversation_history` to SpokeCore or inject voice messages into the shared history when events are emitted

- [x] **Voice UI fails in local/offline mode** ✅ FIXED
  - **Priority:** HIGH
  - **Difficulty:** Medium
  - **Applicable Filepaths:**
    - [main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py#L1405-L1427)
    - [app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/core/app.py#L171-L234)
  - **Description:** The Qt UI creates a standalone `VoiceController` with a custom `_handle_voice_transcription` that short-circuits with `"Hub not connected. You said: {text}"` when disconnected (line 1411-1412). This bypasses `SpokeCore`'s `_handle_voice_transcription` which properly runs the local agent loop and handles offline mode gracefully.
  - **Fix:** Pass `SpokeCore` instance to `QtVoiceAdapter` (it already supports `core` parameter) instead of using standalone mode with a custom response handler.

---

## Architecture Issues

- [ ] **QtVoiceAdapter not integrated with SpokeCore in MainWindow**
  - **Priority:** HIGH
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - [main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py#L1366-L1394)
    - [qt_voice_adapter.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/qt_voice_adapter.py#L75-L146)
  - **Description:** `QtVoiceAdapter` supports two modes: standalone (creates own controller) and SpokeCore-managed. `MainWindow._enable_voice()` uses standalone mode, creating a `VoiceController` directly. This violates the modular design from `spoke-modules.md` where `SpokeCore` should own the voice lifecycle.
  - **Fix:** `MainWindow` should pass its `SpokeCore` instance to `QtVoiceAdapter` using the `core=` parameter.

- [ ] **Duplicate response handler logic**
  - **Priority:** Medium
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - [main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py#L1405-L1474)
    - [app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/core/app.py#L171-L234)
  - **Description:** `MainWindow._handle_voice_transcription` duplicates logic that `SpokeCore._handle_voice_transcription` already provides (asyncio management, agent loop). The Qt version is also broken (Hub-only) while the SpokeCore version works offline.
  - **Fix:** Remove `MainWindow._handle_voice_transcription` and use SpokeCore's integrated handler.

---

## Implementation Quality

- [ ] **MainWindow doesn't use SpokeCore for chat**
  - **Priority:** Medium
  - **Difficulty:** High
  - **Applicable Filepaths:**
    - [main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py#L800-L1215)
    - [app.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/core/app.py)
  - **Description:** `MainWindow` has its own agent loop implementation (`_send_message_to_tensorzero`) instead of using `SpokeCore.send_message()`. This leads to code duplication and divergent behavior between voice (when fixed) and text chat.
  - **Fix:** Migrate text chat to use `SpokeCore.send_message()` and subscribe to events for UI updates.

- [ ] **VoiceController uses blocking operations in audio thread**
  - **Priority:** Low
  - **Difficulty:** Medium
  - **Applicable Filepaths:**
    - [controller.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/voice/controller.py#L489-L531)
  - **Description:** `_process_audio_sync` runs in a daemon thread and uses `threading.Thread` to call the response handler. While this works, mixing `asyncio.run()` with threading can be fragile.
  - **Fix:** Consider using a dedicated asyncio event loop thread or ThreadPoolExecutor for cleaner async/sync bridging.

---

## Maintainability

- [ ] **Large MainWindow class (1700+ lines)**
  - **Priority:** LOW
  - **Difficulty:** Medium
  - **Applicable Filepaths:**
    - [main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py)
  - **Description:** `MainWindow` handles too many concerns: chat UI, session management, settings, voice control, Hub connection. This makes it hard to test and maintain.
  - **Fix:** Extract voice, settings, and session management into dedicated controller classes that `MainWindow` orchestrates.

- [ ] **Missing integration test for voice + SpokeCore**
  - **Priority:** Medium
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - [test_voice_controller.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/tests/test_voice_controller.py)
  - **Description:** Tests exist for `VoiceController` state machine but not for the integration between `SpokeCore.start_voice()` and the voice response handler. The offline fallback path is untested.
  - **Fix:** Add an integration test that mocks the LLM client and verifies `SpokeCore._handle_voice_transcription` returns a response when offline.

---

## User Experience

- [ ] **Unhelpful error message in offline mode**
  - **Priority:** HIGH
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - [main_window.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/main_window.py#L1411-L1412)
  - **Description:** When voice is used offline, the message `"Hub not connected. You said: {text}"` gives no indication that local mode should work. Users expect voice to work offline since text chat does.
  - **Fix:** Use SpokeCore's handler which runs the local agent loop and provides actual responses.

- [ ] **No visual feedback for offline/online voice mode**
  - **Priority:** LOW
  - **Difficulty:** Low
  - **Applicable Filepaths:**
    - [voice_indicator.py](file:///mnt/A0FCD2A8FCD2784C/Documents%20Offline/capstone%20v2/ai-pc-spoke/src/strawberry/ui/qt/widgets/voice_indicator.py)
  - **Description:** The voice indicator shows state (idle/listening/etc) but doesn't indicate whether responses are coming from Hub or local LLM. Users may be confused about why responses differ.
  - **Fix:** Add subtle indicator (e.g., badge or tooltip) showing "Local" or "Hub" mode.

---

## Summary

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| **Bugs** | 2 | - | - | - |
| **Architecture** | - | 1 | 1 | - |
| **Quality** | - | - | 1 | 1 |
| **Maintainability** | - | - | 1 | 1 |
| **UX** | - | 1 | - | 1 |

**Recommended Fix Order:**
1. **Shared conversation history**: Add `set_voice_session()` to SpokeCore or inject voice into MainWindow's history
2. **SpokeCore integration**: Pass `SpokeCore` to `QtVoiceAdapter` (fixes offline bug)
3. Remove duplicate `_handle_voice_transcription` from `MainWindow`
4. Add integration test for voice + SpokeCore
5. (Future) Migrate text chat to SpokeCore
