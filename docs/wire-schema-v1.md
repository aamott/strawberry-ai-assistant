# Wire Schema v1 — Hub ↔ Spoke API Contract

> **Version:** v1
> **Owner:** Hub (the server defines the contract; Spoke adapts)
> **Transport:** HTTPS + WebSocket (JSON payloads)

This document is the **single source of truth** for the message shapes exchanged
between Hub and Spoke. Each side maintains its own models/DTOs internally and
translates at the boundary. Neither side imports code from the other.

---

## Protocol Version Header

All HTTP requests from Spoke include:

```
X-Protocol-Version: v1
```

Hub rejects requests with an unsupported version (HTTP 400).

WebSocket messages include a top-level `"v"` field:

```json
{"v": 1, "type": "skill_request", ...}
```

---

## Endpoints & Payloads

### POST /skills/register

Spoke registers its available skills with the Hub.

**Request:**
```json
{
  "skills": [
    {
      "class_name": "WeatherSkill",
      "function_name": "get_current_weather",
      "signature": "get_current_weather(location: str) -> Dict",
      "docstring": "Get current weather for a location."
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skills` | array | yes | List of skill descriptors |
| `skills[].class_name` | string | yes | Skill class name |
| `skills[].function_name` | string | yes | Method name |
| `skills[].signature` | string | yes | Full Python signature |
| `skills[].docstring` | string | no | Method docstring |

**Response:** `200 OK` with `{"registered": <count>}`

---

### POST /skills/execute

Hub asks Spoke to run a skill method (routed via WebSocket).

**Request:**
```json
{
  "device_name": "living_room_pc",
  "skill_name": "WeatherSkill",
  "method_name": "get_current_weather",
  "args": [],
  "kwargs": {"location": "Seattle"}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_name` | string | yes | Normalized target device name |
| `skill_name` | string | yes | Skill class name |
| `method_name` | string | yes | Method to invoke |
| `args` | array | no | Positional arguments (default `[]`) |
| `kwargs` | object | no | Keyword arguments (default `{}`) |

**Response:**
```json
{
  "success": true,
  "result": {"temp": 55, "unit": "F", "condition": "Cloudy"},
  "error": null,
  "device": "living_room_pc"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether execution succeeded |
| `result` | any | Return value (null on failure) |
| `error` | string | Error message (null on success) |
| `device` | string | Device that executed the skill |

---

### GET /skills/search?q=weather

Hub searches registered skills across all connected devices.

**Response:**
```json
{
  "results": [
    {
      "path": "WeatherSkill.get_current_weather",
      "signature": "get_current_weather(location: str) -> Dict",
      "summary": "Get current weather for a location.",
      "docstring": "Get current weather for a location.\n\nArgs:\n    location: City name.",
      "devices": ["living_room_pc"],
      "device_names": ["Living Room PC"],
      "device_count": 1,
      "is_local": false
    }
  ],
  "total": 1
}
```

---

### WebSocket Messages

#### skill_request (Hub → Spoke)
```json
{
  "v": 1,
  "type": "skill_request",
  "id": "uuid-1234",
  "skill_name": "WeatherSkill",
  "method_name": "get_current_weather",
  "args": [],
  "kwargs": {"location": "Seattle"}
}
```

#### skill_response (Spoke → Hub)
```json
{
  "v": 1,
  "type": "skill_response",
  "id": "uuid-1234",
  "success": true,
  "result": {"temp": 55},
  "error": null
}
```

---

## Device Name Normalization

Both Hub and Spoke normalize device names independently using the same algorithm:

1. NFKD unicode normalization → strip to ASCII
2. Lowercase
3. Spaces/hyphens → underscores
4. Remove non-alphanumeric (except `_`)
5. Collapse multiple underscores
6. Strip leading/trailing underscores

Example: `"Living Room PC"` → `"living_room_pc"`

> **Note:** Each repo owns its own implementation of this algorithm.
> They must produce identical output for the same input.
> Consider adding cross-repo contract tests if normalization rules evolve.

---

## Evolution Rules

1. **Additive only:** New fields may be added with defaults; existing fields must not be removed or renamed.
2. **Version bump:** Breaking changes require incrementing `X-Protocol-Version` / `"v"`.
3. **Capability negotiation:** Future versions may add a handshake where Spoke announces supported features.
4. **Schema owner:** Hub defines the contract. Spoke adapts to it.
