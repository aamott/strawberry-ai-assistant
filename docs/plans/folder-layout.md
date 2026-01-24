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
│   ├── shared/         # Shared code
│   │   └── settings/   # SettingsManager (see docs/plans/settings/)
│   └── config/         # Pydantic settings models (DEPRECATED - use shared/settings/)
├── config/             # Config files (settings.yaml, .env)
├── skills/             # User skill files (registered in spoke_core)
└── tests/              # Test suite
```


**Shared (Settings)**
```
ai-pc-spoke/src/strawberry/shared/
└── settings/
    ├── __init__.py          # Public exports
    ├── manager.py           # SettingsManager class
    ├── schema.py            # SettingField, FieldType, ActionResult
    ├── storage.py           # YamlStorage, EnvStorage classes
    ├── view_model.py        # SettingsViewModel for UI
    └── events.py            # SettingsChanged event
```
See [settings/README.md](./settings/README.md) for design details.


**SpokeCore**
```
ai-pc-spoke/src/strawberry/spoke_core/
├── app.py # SpokeCore - Importable LLM, chat, and skill service
├── events.py # Event stream for SpokeCore
├── session.py # Chat session management
├── settings_schema.py # Settings schema for SpokeCore (SPOKE_CORE_SCHEMA)
└── skills/ # Skills management classes (not the skills themselves)
    └── ...
```


**Voice Processing**
```
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


**Config Files**
```
ai-pc-spoke/
├── .env                     # Secrets (API keys, tokens) - at project root
└── config/
    ├── settings.yaml        # All non-secret settings (organized by namespace)
    └── tensorzero.toml      # TensorZero LLM gateway configuration
```

Note: The legacy `src/config/config.yaml` is deprecated in favor of `config/settings.yaml`.


**Qt Settings UI**
```
ai-pc-spoke/src/strawberry/ui/qt/widgets/settings/
├── settings_dialog.py       # Main settings window with tabs
├── namespace_widget.py      # Renders one namespace section
├── schema_field_widget.py   # Auto-renders single SettingField
└── provider_widget.py       # Provider selection + sub-settings
```


**Skills Repo**
A folder where the skills themselves are stored. Each skill is a git repository. New skills are added by cloning a git repository into this folder.

```
ai-pc-spoke/skills/
├── WeatherSkill/ # WeatherSkill skill repository
│   ├── __init__.py
│   └── weather_skill.py
├── ... # Other skill repositories
```