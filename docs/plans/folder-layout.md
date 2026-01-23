---
description: Folder layout overview
---

# Folder Layout

**Overview**
```
ai-pc-spoke/
├── src/strawberry/     # Main package
│   ├── spoke_core/     # SpokeCore - Importable LLM, chat, and skill service
|   │   ├── skills/     # Skills (registered in spoke_core)
|   │   └── ...
│   ├── ui/             # User interfaces
|   │   ├── qt/           # Qt-based UI
|   │   ├── cli/          # CLI-based UI
|   │   └── voice_interface/  # Voice-only interface
│   ├── voice/          # Voice processing
│   └── shared/         # Shared code (SettingsManager, logging)
├── config/             # Config files
├── skills/             # User skill files (registered in spoke_core)
└── tests/              # Test suite
```


**SpokeCore**
ai-pc-spoke/src/strawberry/spoke_core/
├── app.py # SpokeCore - Importable LLM, chat, and skill service
├── events.py # Event stream for SpokeCore
├── session.py # Chat session management
├── settings_schema.py # Settings schema for SpokeCore
└── skills/ # Skills management classes (not the skills themselves)
    └── ...


**Voice Processing**
ai-pc-spoke/src/strawberry/voice/
├── voice_core.py # VoiceCore - Importable voice processing (used by UIs)
├── stt/
│   ├── base.py
│   ├── discovery.py
│   └── backends/
│       ├── stt_google.py
│       ├── stt_leopard.py
│       └── ...
├── tts/
│   ├── base.py
│   ├── discovery.py
│   └── backends/
│       ├── tts_google.py
│       ├── tts_orca.py
│       ├── tts_pocket.py
│       └── ...
├── wakeword/
│   ├── base.py
│   ├── discovery.py
│   └── backends/
│       ├── wakeword_porcupine.py
│       └── ...
├── audio/
│   ├── base.py
│   ├── discovery.py
│   └── backends/
│       ├── audio_sounddevice.py
│       └── ...
├── vad/
│   ├── base.py
│   ├── discovery.py
│   └── backends/
│       ├── vad_silero.py
│       ├── vad_ten.py
│       └── ...
└── ...
```


**Skills Repo**
A folder where the skills themselves are stored. Each skill is a git repository. New skills are added by cloning a git repository into this folder.

ai-pc-spoke/skills/
├── WeatherSkill/ # WeatherSkill skill repository
│   ├── __init__.py
│   └── weather_skill.py
├── ... # Other skill repositories