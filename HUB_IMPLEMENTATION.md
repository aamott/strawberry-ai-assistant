# Strawberry AI Hub — Implementation Plan

This document details the technical implementation of the Hub server, focusing on authentication, LLM routing, skill registry, and Spoke integration.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
   - [Authentication & Authorization](#authentication--authorization)
   - [LLM Gateway](#llm-gateway)
   - [Skill Registry](#skill-registry)
   - [Session Management](#session-management)
   - [MQTT Broker (Future)](#mqtt-broker-future)
4. [API Specification](#api-specification)
5. [Database Schema](#database-schema)
6. [Spoke Integration](#spoke-integration)
7. [Configuration](#configuration)
8. [Development Phases](#development-phases)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STRAWBERRY HUB                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Application                          │   │
│  │                                                                      │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │   │    Auth      │  │    Chat      │  │   Skills     │             │   │
│  │   │   Router     │  │   Router     │  │   Router     │             │   │
│  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │   │
│  │          │                 │                 │                       │   │
│  │   ┌──────▼─────────────────▼─────────────────▼───────┐             │   │
│  │   │                  Services Layer                   │             │   │
│  │   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │             │   │
│  │   │  │  AuthService│ │ LLMService  │ │SkillRegistry│ │             │   │
│  │   │  └─────────────┘ └─────────────┘ └─────────────┘ │             │   │
│  │   └──────────────────────────────────────────────────┘             │   │
│  │                              │                                       │   │
│  │   ┌──────────────────────────▼───────────────────────┐             │   │
│  │   │                   Database Layer                  │             │   │
│  │   │     SQLAlchemy + SQLite (dev) / PostgreSQL        │             │   │
│  │   └──────────────────────────────────────────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    External Services                                 │   │
│  │                                                                      │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │   │  OpenAI API  │  │  Google AI   │  │  MQTT Broker │             │   │
│  │   │              │  │   Studio     │  │   (Future)   │             │   │
│  │   └──────────────┘  └──────────────┘  └──────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow

```mermaid
sequenceDiagram
    participant Spoke
    participant Hub as Hub API
    participant Auth as AuthService
    participant LLM as LLMService
    participant Skills as SkillRegistry
    participant DB as Database
    participant Provider as LLM Provider

    Spoke->>Hub: POST /v1/chat/completions
    Hub->>Auth: Validate JWT
    Auth->>DB: Get device
    Auth-->>Hub: Device authenticated
    
    Hub->>Skills: Get available skills
    Skills->>DB: Query skills for user
    Skills-->>Hub: Skill definitions
    
    Hub->>LLM: Format request with skills
    LLM->>Provider: Call LLM API
    Provider-->>LLM: Response
    LLM-->>Hub: Parsed response
    
    Hub->>DB: Save message to session
    Hub-->>Spoke: Response
```

---

## Project Structure

```
ai-hub/
├── pyproject.toml
├── README.md
├── .env.example
│
├── src/hub/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + entrypoint
│   ├── config.py               # Settings (pydantic-settings)
│   │
│   ├── database.py             # SQLAlchemy models + engine
│   ├── auth.py                 # JWT utilities
│   │
│   ├── routers/                # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py             # /auth/* endpoints
│   │   ├── chat.py             # /v1/chat/completions
│   │   ├── skills.py           # /skills/* endpoints
│   │   └── devices.py          # /devices/* endpoints
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── llm.py              # LLM provider abstraction
│   │   ├── skills.py           # Skill registry logic
│   │   └── sessions.py         # Session management
│   │
│   └── schemas/                # Pydantic models (if separated)
│       ├── __init__.py
│       ├── auth.py
│       ├── chat.py
│       └── skills.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── test_auth.py
│   ├── test_chat.py
│   └── test_skills.py
│
└── alembic/                    # Database migrations (future)
    └── ...
```

---

## Core Components

### Authentication & Authorization

#### JWT Token Structure

```json
{
    "sub": "device_id",          // Device identifier
    "user_id": "user_123",       // Owner of the device
    "device_name": "Living Room Speaker",
    "iat": 1704067200,           // Issued at
    "exp": 1706659200            // Expires (30 days default)
}
```

#### Device Registration Flow

```mermaid
sequenceDiagram
    participant User as User/Admin
    participant Hub as Hub API
    participant DB as Database

    User->>Hub: POST /auth/register
    Note right of Hub: {name, user_id}
    
    Hub->>Hub: Generate device_id (UUID)
    Hub->>Hub: Generate access_token (JWT)
    Hub->>Hub: Hash token for storage
    
    Hub->>DB: Create Device record
    DB-->>Hub: OK
    
    Hub-->>User: {device_id, access_token}
    
    Note over User: Store token in Spoke config
```

#### AuthService Implementation

```python
# src/hub/services/auth.py

from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import Device

class AuthService:
    """Authentication service for device management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"])
    
    async def register_device(
        self,
        name: str,
        user_id: str,
    ) -> tuple[Device, str]:
        """Register a new device and return (device, access_token)."""
        device_id = self._generate_device_id()
        
        device = Device(
            id=device_id,
            name=name,
            user_id=user_id,
            is_active=True,
        )
        self.db.add(device)
        await self.db.commit()
        
        token = self._create_token(device)
        return device, token
    
    async def authenticate(self, token: str) -> Device:
        """Validate token and return device."""
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        
        device = await self.db.get(Device, payload["sub"])
        if not device or not device.is_active:
            raise AuthenticationError("Invalid device")
        
        # Update last seen
        device.last_seen = datetime.utcnow()
        await self.db.commit()
        
        return device
    
    def _create_token(self, device: Device) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
        
        return jwt.encode(
            {
                "sub": device.id,
                "user_id": device.user_id,
                "device_name": device.name,
                "exp": expire,
            },
            settings.secret_key,
            algorithm="HS256",
        )
```

---

### LLM Gateway

The Hub acts as a unified gateway to multiple LLM providers, translating between them and providing fallback capabilities.

#### Provider Abstraction

```python
# src/hub/services/llm.py

from abc import ABC, abstractmethod
from typing import List, AsyncIterator
from dataclasses import dataclass

@dataclass
class ChatMessage:
    role: str  # system, user, assistant
    content: str

@dataclass
class ChatResponse:
    content: str
    model: str
    finish_reason: str
    usage: dict | None = None

class LLMProvider(ABC):
    """Abstract base for LLM providers."""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        """Send chat request to provider."""
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream chat response."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def chat(self, messages, model="gpt-4o-mini", **kwargs):
        # Implementation using httpx
        ...


class GoogleAIProvider(LLMProvider):
    """Google AI Studio (Gemini) provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def chat(self, messages, model="gemini-2.0-flash", **kwargs):
        # Convert OpenAI format to Gemini format
        ...


class LLMService:
    """LLM gateway with provider selection and fallback."""
    
    def __init__(self, providers: List[LLMProvider]):
        self.providers = providers
    
    async def chat(self, messages: List[ChatMessage], **kwargs) -> ChatResponse:
        """Try providers in order until one succeeds."""
        last_error = None
        
        for provider in self.providers:
            try:
                return await provider.chat(messages, **kwargs)
            except Exception as e:
                last_error = e
                continue
        
        raise LLMError(f"All providers failed: {last_error}")
```

#### Skill Injection

Before sending to the LLM, the Hub injects available skills into the system prompt:

```python
def inject_skills_prompt(
    messages: List[ChatMessage],
    skills: List[SkillInfo],
    device_name: str,
) -> List[ChatMessage]:
    """Inject skill information into the system prompt."""
    
    skills_prompt = format_skills_as_python(skills, device_name)
    
    system_content = f"""You are a helpful voice assistant called Strawberry AI.

You have access to the following skills that you can call by writing Python code:

```python
{skills_prompt}
```

When you need to perform an action, write Python code to call the appropriate skill.
The code will be executed and the result returned to you.

Important:
- If no device is specified, assume the current device ({device_name}).
- Search for skills before assuming they don't exist.
- Handle errors gracefully and inform the user.
"""
    
    # Prepend system message or merge with existing
    if messages and messages[0].role == "system":
        messages[0].content = system_content + "\n\n" + messages[0].content
    else:
        messages.insert(0, ChatMessage(role="system", content=system_content))
    
    return messages
```

---

### Skill Registry

#### Skill Model

```python
# From database.py

class Skill(Base):
    __tablename__ = "skills"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    
    # Identification
    class_name: Mapped[str]       # e.g., "MusicControlSkill"
    function_name: Mapped[str]    # e.g., "play_song"
    
    # Documentation
    signature: Mapped[str]        # e.g., "play_song(name: str) -> bool"
    docstring: Mapped[str | None]
    
    # Health
    last_heartbeat: Mapped[datetime]
    
    # Relationships
    device: Mapped["Device"] = relationship(back_populates="skills")
```

#### SkillRegistry Service

```python
# src/hub/services/skills.py

from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import Skill, Device

class SkillRegistry:
    """Manages skill registration and discovery."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.expiry = timedelta(seconds=settings.skill_expiry_seconds)
    
    async def register_skills(
        self,
        device: Device,
        skills: List[SkillInfo],
    ) -> int:
        """Register skills for a device (replaces existing)."""
        # Delete existing
        await self.db.execute(
            delete(Skill).where(Skill.device_id == device.id)
        )
        
        # Add new
        now = datetime.utcnow()
        for info in skills:
            skill = Skill(
                device_id=device.id,
                class_name=info.class_name,
                function_name=info.function_name,
                signature=info.signature,
                docstring=info.docstring,
                last_heartbeat=now,
            )
            self.db.add(skill)
        
        await self.db.commit()
        return len(skills)
    
    async def get_skills_for_user(
        self,
        user_id: str,
        include_expired: bool = False,
    ) -> List[Skill]:
        """Get all skills visible to a user."""
        query = (
            select(Skill)
            .join(Device)
            .where(Device.user_id == user_id)
        )
        
        if not include_expired:
            cutoff = datetime.utcnow() - self.expiry
            query = query.where(Skill.last_heartbeat > cutoff)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search_skills(
        self,
        user_id: str,
        query: str,
        current_device_id: str | None = None,
    ) -> List[dict]:
        """Search skills, prioritizing current device."""
        skills = await self.get_skills_for_user(user_id)
        
        # Filter by query
        if query:
            query_lower = query.lower()
            skills = [
                s for s in skills
                if query_lower in s.function_name.lower()
                or query_lower in s.class_name.lower()
                or (s.docstring and query_lower in s.docstring.lower())
            ]
        
        # Sort: current device first
        skills.sort(key=lambda s: (
            s.device_id != current_device_id,
            s.class_name,
            s.function_name,
        ))
        
        return [self._format_skill(s) for s in skills]
    
    async def heartbeat(self, device_id: str) -> int:
        """Update heartbeat for all skills on a device."""
        now = datetime.utcnow()
        result = await self.db.execute(
            update(Skill)
            .where(Skill.device_id == device_id)
            .values(last_heartbeat=now)
        )
        await self.db.commit()
        return result.rowcount
```

---

### Session Management

Sessions track conversation history and expire after inactivity.

```python
# src/hub/services/sessions.py

from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ..database import Session, Message

class SessionService:
    """Manages conversation sessions."""
    
    SESSION_TIMEOUT = timedelta(minutes=15)
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_session(
        self,
        device_id: str,
        user_id: str,
        session_id: str | None = None,
    ) -> Session:
        """Get existing session or create new one."""
        if session_id:
            session = await self.db.get(Session, session_id)
            if session and session.is_active:
                # Check timeout
                if datetime.utcnow() - session.last_activity < self.SESSION_TIMEOUT:
                    session.last_activity = datetime.utcnow()
                    await self.db.commit()
                    return session
                else:
                    # Expired - create new
                    session.is_active = False
                    await self.db.commit()
        
        # Create new session
        session = Session(
            id=str(uuid.uuid4()),
            device_id=device_id,
            user_id=user_id,
            is_active=True,
        )
        self.db.add(session)
        await self.db.commit()
        return session
    
    async def add_message(
        self,
        session: Session,
        role: str,
        content: str,
    ) -> Message:
        """Add message to session."""
        message = Message(
            session_id=session.id,
            role=role,
            content=content,
        )
        self.db.add(message)
        
        session.last_activity = datetime.utcnow()
        await self.db.commit()
        
        return message
    
    async def get_history(
        self,
        session: Session,
        limit: int = 50,
    ) -> List[Message]:
        """Get conversation history."""
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))
```

---

### MQTT Broker (Future)

For remote skill calls between devices, we'll use MQTT with a request/response pattern:

```
Topics:
    skills/{device_id}/request    # Skill call requests to device
    skills/{device_id}/response   # Responses from device
    devices/{device_id}/status    # Device online/offline

Message format (request):
{
    "correlation_id": "uuid",
    "caller_device_id": "abc123",
    "skill_path": "MusicControlSkill.play_song",
    "args": ["Never Gonna Give You Up"],
    "kwargs": {},
    "timeout_ms": 5000
}

Message format (response):
{
    "correlation_id": "uuid",
    "success": true,
    "result": {"playing": true},
    "error": null
}
```

This is deferred to Phase 2.

---

## API Specification

### Authentication Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/auth/register` | Register new device | No |
| GET | `/auth/me` | Get current device info | Yes |
| POST | `/auth/refresh` | Refresh access token | Yes |

### Chat Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/v1/chat/completions` | OpenAI-compatible chat | Yes |
| POST | `/inference` | TensorZero-style inference | Yes |

### Skill Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/skills` | List all skills | Yes |
| GET | `/skills/search` | Search skills | Yes |
| POST | `/skills/register` | Register device skills | Yes |
| POST | `/skills/heartbeat` | Update skill heartbeat | Yes |

### Device Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/devices` | List user's devices | Yes |
| GET | `/devices/{id}` | Get device details | Yes |

---

## Database Schema

```
┌──────────────────────────────────────────────────────────────────┐
│                          devices                                  │
├──────────────────────────────────────────────────────────────────┤
│ id          VARCHAR(64)  PK                                      │
│ name        VARCHAR(255) NOT NULL                                │
│ user_id     VARCHAR(64)  NOT NULL  INDEX                         │
│ hashed_token VARCHAR(255) NOT NULL                               │
│ is_active   BOOLEAN      DEFAULT TRUE                            │
│ last_seen   DATETIME     NULLABLE                                │
│ created_at  DATETIME     DEFAULT NOW                             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                           skills                                  │
├──────────────────────────────────────────────────────────────────┤
│ id            INTEGER     PK AUTOINCREMENT                       │
│ device_id     VARCHAR(64) FK → devices.id  INDEX                 │
│ class_name    VARCHAR(255) NOT NULL                              │
│ function_name VARCHAR(255) NOT NULL                              │
│ signature     TEXT        NOT NULL                               │
│ docstring     TEXT        NULLABLE                               │
│ last_heartbeat DATETIME   DEFAULT NOW                            │
│ created_at    DATETIME    DEFAULT NOW                            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                          sessions                                 │
├──────────────────────────────────────────────────────────────────┤
│ id            VARCHAR(64) PK                                     │
│ device_id     VARCHAR(64) FK → devices.id  INDEX                 │
│ user_id       VARCHAR(64) NOT NULL  INDEX                        │
│ is_active     BOOLEAN     DEFAULT TRUE                           │
│ created_at    DATETIME    DEFAULT NOW                            │
│ last_activity DATETIME    DEFAULT NOW                            │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                          messages                                 │
├──────────────────────────────────────────────────────────────────┤
│ id            INTEGER     PK AUTOINCREMENT                       │
│ session_id    VARCHAR(64) FK → sessions.id  INDEX                │
│ role          VARCHAR(32) NOT NULL  (system/user/assistant)      │
│ content       TEXT        NOT NULL                               │
│ created_at    DATETIME    DEFAULT NOW                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## Spoke Integration

### Connecting Spoke to Hub

The Spoke needs a Hub client to register and communicate:

```python
# ai-pc-spoke/src/strawberry/hub/client.py

import httpx
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class HubConfig:
    url: str
    token: str
    timeout: float = 30.0

class HubClient:
    """Client for communicating with the Hub."""
    
    def __init__(self, config: HubConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.url,
            headers={"Authorization": f"Bearer {config.token}"},
            timeout=config.timeout,
        )
    
    async def chat(
        self,
        messages: List[dict],
        model: Optional[str] = None,
    ) -> dict:
        """Send chat request to Hub."""
        response = await self.client.post(
            "/v1/chat/completions",
            json={
                "messages": messages,
                "model": model or "gpt-4o-mini",
            },
        )
        response.raise_for_status()
        return response.json()
    
    async def register_skills(self, skills: List[dict]) -> dict:
        """Register local skills with Hub."""
        response = await self.client.post(
            "/skills/register",
            json={"skills": skills},
        )
        response.raise_for_status()
        return response.json()
    
    async def heartbeat(self) -> dict:
        """Send heartbeat to keep skills alive."""
        response = await self.client.post("/skills/heartbeat")
        response.raise_for_status()
        return response.json()
    
    async def search_skills(self, query: str = "") -> List[dict]:
        """Search for skills across all devices."""
        response = await self.client.get(
            "/skills/search",
            params={"query": query},
        )
        response.raise_for_status()
        return response.json()["results"]
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()
```

### Skill Registration from Spoke

```python
# ai-pc-spoke/src/strawberry/skills/loader.py

import inspect
from pathlib import Path
from typing import List
import importlib.util

def load_skills_from_folder(skills_path: Path) -> List[dict]:
    """Load skill classes from Python files and extract metadata."""
    skills = []
    
    for py_file in skills_path.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        
        # Load module
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find skill classes
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.endswith("Skill"):
                skills.extend(extract_skill_methods(name, obj))
    
    return skills

def extract_skill_methods(class_name: str, cls) -> List[dict]:
    """Extract method signatures and docstrings from a skill class."""
    methods = []
    
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if name.startswith("_"):
            continue
        
        sig = inspect.signature(method)
        docstring = inspect.getdoc(method) or ""
        
        methods.append({
            "class_name": class_name,
            "function_name": name,
            "signature": f"{name}{sig}",
            "docstring": docstring,
        })
    
    return methods
```

---

## Configuration

### Hub .env

```bash
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Security
SECRET_KEY=your-very-long-random-secret-key-here

# Database
DATABASE_URL=sqlite+aiosqlite:///./hub.db
# For production:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/strawberry

# LLM Providers (configure at least one)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

GOOGLE_AI_STUDIO_API_KEY=...

# Skill Registry
SKILL_EXPIRY_SECONDS=1800  # 30 minutes
```

### Spoke config.yaml update

```yaml
hub:
  url: "http://localhost:8000"
  token: "${HUB_TOKEN}"  # From device registration
  timeout_seconds: 30
  
  # Heartbeat interval for skill registration
  heartbeat_interval_seconds: 300  # 5 minutes
```

---

## Development Phases

### Phase 1: Minimal Hub (Current)

```
[x] Project skeleton (FastAPI, SQLAlchemy)
[x] Configuration system
[x] Database models (Device, Skill, Session, Message)
[x] JWT authentication
[x] Device registration endpoint
[ ] Chat endpoint with Google AI Studio
[ ] Basic skill registry (register, list, heartbeat)
[ ] Tests for all endpoints
```

**Deliverable:** Spoke can authenticate and get LLM responses through Hub.

---

### Phase 2: Full Skill Registry

```
[ ] Skill search endpoint
[ ] Skill injection into LLM prompts
[ ] Session management
[ ] Conversation history
[ ] Device management endpoints
[ ] Spoke Hub client implementation
[ ] Spoke skill loader
```

**Deliverable:** Spoke registers skills with Hub, Hub provides skill context to LLM.

---

### Phase 3: Multi-Device

```
[ ] MQTT broker integration
[ ] Remote skill call routing
[ ] Device presence tracking
[ ] Cross-device skill calls
[ ] Error handling for offline devices
```

**Deliverable:** Multiple Spokes can call skills on each other.

---

### Phase 4: Production Hardening

```
[ ] PostgreSQL support
[ ] Database migrations (Alembic)
[ ] Rate limiting
[ ] Request logging
[ ] Metrics/monitoring
[ ] Admin web UI
[ ] User management
```

---

## Testing Strategy

### Unit Tests

```python
# tests/conftest.py

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from hub.main import app
from hub.database import Base

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(db_engine):
    """Create test client with isolated database."""
    # Override database dependency
    ...
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_client(client):
    """Create authenticated test client."""
    response = await client.post(
        "/auth/register",
        json={"name": "Test Device", "user_id": "test_user"},
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
```

### Integration Tests

```python
# tests/test_chat.py

@pytest.mark.asyncio
async def test_chat_endpoint(auth_client):
    """Test chat completion with mocked LLM."""
    response = await auth_client.post(
        "/v1/chat/completions",
        json={
            "messages": [
                {"role": "user", "content": "Hello!"}
            ],
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
```

---

## Next Steps

1. **Fix test fixtures** - Proper database isolation for tests
2. **Complete chat endpoint** - Integrate with Google AI Studio API
3. **Add skill registration tests** - Verify skill lifecycle
4. **Build Spoke HubClient** - Connect Spoke to Hub
5. **End-to-end test** - Spoke → Hub → LLM → Spoke

