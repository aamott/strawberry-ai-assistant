# Multi-Turn Agent Loop Design

## Overview

The LLM operates as an **agent** that can:
1. Search for available skills
2. Inspect skill signatures
3. Call skills and see results
4. Continue reasoning based on results
5. Make more calls or provide final response

## Flow Diagram

```
User: "Play some relaxing music"
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  AGENT LOOP (max 5 iterations)                                │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Iteration 1: LLM Response                               │  │
│  │                                                         │  │
│  │ "Let me find music-related skills..."                   │  │
│  │ ```python                                               │  │
│  │ results = device.search_skills("music")                 │  │
│  │ print(results)                                          │  │
│  │ ```                                                     │  │
│  └─────────────────────────────────────────────────────────┘  │
│        │                                                      │
│        ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Execute code, capture output                            │  │
│  │                                                         │  │
│  │ Output:                                                 │  │
│  │ [{"path": "MusicSkill.play", "summary": "Play music"}]  │  │
│  └─────────────────────────────────────────────────────────┘  │
│        │                                                      │
│        ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Send output back to LLM as "tool" message               │  │
│  │                                                         │  │
│  │ {"role": "tool", "content": "[{...}]"}                  │  │
│  └─────────────────────────────────────────────────────────┘  │
│        │                                                      │
│        ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Iteration 2: LLM Response                               │  │
│  │                                                         │  │
│  │ "Found it! Let me get more details..."                  │  │
│  │ ```python                                               │  │
│  │ info = device.describe_function("MusicSkill.play")      │  │
│  │ print(info)                                             │  │
│  │ ```                                                     │  │
│  └─────────────────────────────────────────────────────────┘  │
│        │                                                      │
│        ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Execute, send result back...                            │  │
│  └─────────────────────────────────────────────────────────┘  │
│        │                                                      │
│        ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Iteration 3: LLM Response                               │  │
│  │                                                         │  │
│  │ "Now I'll play the music..."                            │  │
│  │ ```python                                               │  │
│  │ result = device.MusicSkill.play(genre="relaxing")       │  │
│  │ print(result)                                           │  │
│  │ ```                                                     │  │
│  └─────────────────────────────────────────────────────────┘  │
│        │                                                      │
│        ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Iteration 4: LLM Response (no code blocks)              │  │
│  │                                                         │  │
│  │ "I've started playing some relaxing music for you! 🎵"  │  │
│  │                                                         │  │
│  │ [NO CODE BLOCKS = AGENT LOOP ENDS]                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
Display final response to user
```

## Device Proxy API

The `device` object provides these discovery methods:

```python
# Search for skills by keyword
device.search_skills(query: str = "") -> List[dict]
# Returns: [{"path": "SkillName.method", "signature": "...", "summary": "..."}]

# Get full function details
device.describe_function(path: str) -> str
# Returns: Full function signature with docstring

# Call a skill directly
device.SkillName.method_name(args...)
# Returns: Method result
```

## Message Format

### System Prompt
```
You are Strawberry, a helpful AI assistant with access to skills.

## Available Commands

You can discover and call skills using Python code blocks:

```python
# Find skills by keyword
results = device.search_skills("lights")
print(results)

# Get details about a specific function
info = device.describe_function("SmartHomeSkill.turn_on")
print(info)

# Call a skill
result = device.SmartHomeSkill.turn_on(device="Living Room")
print(result)
```

## How It Works

1. When you write a ```python block, I will execute it
2. The output will be shown to you
3. You can then continue your response or make more calls
4. When you're done, just respond without code blocks

## Important Rules

- Always use print() to see output
- Search for skills before calling them if unsure
- Handle errors gracefully
- Respond naturally after skill calls complete
```

### Conversation Flow

```json
[
  {"role": "system", "content": "You are Strawberry..."},
  {"role": "user", "content": "Turn on the lights"},
  {"role": "assistant", "content": "Let me find...\n```python\nresults = device.search_skills(\"lights\")\nprint(results)\n```"},
  {"role": "tool", "content": "[{\"path\": \"SmartHomeSkill.turn_on\", ...}]"},
  {"role": "assistant", "content": "Found it!\n```python\ndevice.SmartHomeSkill.turn_on()\nprint(\"Done\")\n```"},
  {"role": "tool", "content": "Done"},
  {"role": "assistant", "content": "I've turned on the lights! 💡"}
]
```

## Implementation

### Agent Loop (Pseudocode)

```python
async def run_agent(user_message: str, max_iterations: int = 5):
    messages = [system_prompt] + conversation_history + [user_message]
    
    for i in range(max_iterations):
        # Get LLM response
        response = await hub.chat(messages)
        
        # Parse for code blocks
        code_blocks = parse_python_blocks(response.content)
        
        if not code_blocks:
            # No code = agent is done
            return response.content
        
        # Execute code blocks
        outputs = []
        for code in code_blocks:
            result = execute_in_sandbox(code)
            outputs.append(result)
        
        # Add assistant message and tool results
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "tool", "content": "\n".join(outputs)})
    
    # Max iterations reached
    return response.content + "\n\n(Reached maximum iterations)"
```

### Safety Limits

| Limit | Value | Rationale |
|-------|-------|-----------|
| Max iterations | 5 | Prevent infinite loops |
| Code execution timeout | 5s | Prevent hung skills |
| Max code blocks per response | 3 | Limit complexity |
| Total response time | 60s | User experience |

## UI Display

```
┌─────────────────────────────────────────────────────────────────┐
│ 👤 Turn on the lights                                           │
├─────────────────────────────────────────────────────────────────┤
│ 🤖 Let me find the right skill...                               │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🔍 Skill Search: "lights"                                   │ │
│ │    Found: SmartHomeSkill.turn_on, SmartHomeSkill.turn_off   │ │
│ │    ✅ Complete                                               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ⚡ Skill Call: SmartHomeSkill.turn_on()                     │ │
│ │    ✅ Success: Lights turned on                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Done! I've turned on the lights for you. 💡                     │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling

If a skill fails:
```python
# LLM sees:
{"role": "tool", "content": "Error: Device 'Kitchen' not found"}

# LLM can respond:
"I couldn't find a device called 'Kitchen'. Let me search for available devices..."
```

The LLM can recover by:
1. Searching for alternatives
2. Asking the user for clarification
3. Trying a different approach

