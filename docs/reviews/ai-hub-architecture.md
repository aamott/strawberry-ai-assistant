# ai-hub architecture simplification review

- [ ] **Title:** Consolidate admin config file access into a reusable helper
  - **Priority:** Medium
  - **Difficulty:** Low
  - **Applicable Folders/Filepaths:** `ai-hub/src/hub/routers/admin.py`
  - **Description:** The admin router repeats file open/read/write logic for `.env` and `tensorzero.toml`. Extract a shared helper that resolves the file path and handles missing files consistently to keep the router focused on authorization + response formatting.

- [ ] **Title:** Introduce a shared hub service module for device/session accessors
  - **Priority:** Medium
  - **Difficulty:** Medium
  - **Applicable Folders/Filepaths:** `ai-hub/src/hub/routers/*`, `ai-hub/src/hub/services/`
  - **Description:** Multiple routers need “current user’s devices” or “session by user + id” logic. A small service layer (or utilities module) can host these queries so routers stay thin and testing is easier.

- [ ] **Title:** Split chat agent loop helpers into a dedicated module
  - **Priority:** Low
  - **Difficulty:** Medium
  - **Applicable Folders/Filepaths:** `ai-hub/src/hub/routers/chat.py`, `ai-hub/src/hub/agent/`
  - **Description:** The chat router blends HTTP layer with agent-loop utilities (tool call parsing, caching, loop controls). Move loop helpers into a dedicated module so the router focuses on request/response wiring and the agent logic is easier to test.
