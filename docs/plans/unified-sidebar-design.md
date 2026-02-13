# Unified Sidebar Design

## Problem Statement

The current UI has **two separate sidebars** — a Dashboard navigation sidebar and a Chat
history sidebar — each with their own toggle. On mobile, this creates two hamburger menus
and a confusing experience. The navigation and chat history feel disconnected.

**Goal:** Merge everything into a single, Gemini-style popup drawer that provides search,
navigation, chat management, and settings in one place.

---

## Design Options

### Design A: Unified Vertical Drawer (Recommended)

Single drawer with all sections stacked vertically. Closest to the Gemini reference.

```
┌───────────────────────────────────────────────────┐
│ ☰   🍓 Strawberry AI      [Chat Title]      (👤) │  ← Fixed header
├───────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────────────────┐                         │
│  │ 🔍 Search chats...   │                         │
│  ├──────────────────────┤                         │
│  │ 📊 Overview          │  ← Navigation           │
│  │ 💬 Chat              │                         │
│  │ 🖥️ My Devices        │                         │
│  │ 👥 Users      (admin)│                         │
│  ├──────────────────────┤                         │
│  │ Chats    [+ New] [⋮] │  ← Section header       │
│  │ ┄┄┄ Pinned ┄┄┄┄┄┄┄  │                         │
│  │ 📌 Important Chat     │                         │
│  │ ┄┄┄ Recent ┄┄┄┄┄┄┄  │                         │
│  │ 💬 Yesterday's Chat   │                         │
│  │ 💬 Older Chat         │                         │
│  │ 💬 ...        (scroll)│                         │
│  ├──────────────────────┤                         │
│  │ ⚙️ Settings    ☀/🌙   │  ← Footer              │
│  └──────────────────────┘                         │
│                                                   │
└───────────────────────────────────────────────────┘
```

**Pros:**
- Matches the Gemini reference the closest
- Everything accessible in one place with one toggle
- Clear visual hierarchy: search → navigate → chats → settings
- Chat list gets the most vertical space (scrollable middle section)
- Familiar pattern — users already know this from Gemini, ChatGPT, Claude

**Cons:**
- Navigation items take ~5 rows of vertical space
- When on non-chat pages, the chat list is less relevant (but still useful for quick access)

---

### Design B: Segmented Drawer with Collapsible Sections

Same drawer but with accordion-style collapsible sections.

```
┌──────────────────────┐
│ 🔍 Search chats...   │
├──────────────────────┤
│ ▾ Navigation         │  ← Collapsible
│   📊 Overview        │
│   💬 Chat            │
│   🖥️ My Devices      │
│   👥 Users           │
├──────────────────────┤
│ ▾ Chats     [+] [⋮] │  ← Collapsible
│   📌 Pinned Chat     │
│   💬 Recent Chat     │
│   ...                │
├──────────────────────┤
│ ⚙️ Settings    ☀/🌙  │
└──────────────────────┘
```

**Pros:** Sections can be collapsed to show more chats.
**Cons:** Extra clicks, accordion UI adds visual noise, not standard for chat apps.

---

### Design C: Icon Nav Rail + Chat Panel

Navigation as a horizontal icon bar at the top, rest is chat-focused.

```
┌───────────────────────┐
│ 📊  💬  🖥️  👥  ⚙️    │  ← Horizontal icon rail
├───────────────────────┤
│ 🔍 Search chats...    │
├───────────────────────┤
│ Chats       [+] [⋮]  │
│ 📌 Pinned Chat        │
│ 💬 Recent Chat 1      │
│ 💬 Recent Chat 2      │
│ ...                   │
├───────────────────────┤
│ ☀ Theme    │  Logout  │
└───────────────────────┘
```

**Pros:** Maximizes chat list space, nav is compact.
**Cons:** Icon-only nav is harder to learn, less accessible, no labels.

---

## Chosen Design: A — Unified Vertical Drawer

**Why Design A wins:**

1. **Matches the user's description exactly** — search at top, navigation below, chats below
   that, settings at bottom.
2. **Proven pattern** — Gemini, ChatGPT, and Claude all use this layout. Users already
   understand it.
3. **Accessibility** — Full text labels on navigation items. No icon-guessing.
4. **One mental model** — Single hamburger menu, one drawer, everything is there.
5. **Mobile-first** — Works identically on all screen sizes since it's always a popup overlay.

---

## Detailed Specification

### 1. Global Header Bar

A fixed top bar present on every page.

| Position | Element | Behavior |
|----------|---------|----------|
| Left | Hamburger icon (☰) | Opens the unified drawer. Always visible. `cursor: pointer`. |
| Center-left | "🍓 Strawberry AI" | Brand text. On `/chat`, shows the active chat title instead. |
| Right | Account avatar circle | Shows first letter of username. Click opens a dropdown: username, role, dark/light toggle, logout. |

- Height: ~56px
- Background: `bg-background/95 backdrop-blur`
- Border: `border-b`
- Z-index: 40 (above drawer overlay)

### 2. Unified Drawer (Sheet from left)

Opens as a Radix Sheet overlay. Width: `w-80` (320px) on mobile, `sm:w-96` (384px) on
larger screens.

#### 2a. Search (top of drawer)

- Full-width search input with magnifying glass icon
- Filters the chat list below in real-time by title
- Clear (✕) button appears when query is non-empty
- Placeholder: "Search chats..."

#### 2b. Navigation Section

Vertical list of page links, directly below search. Each item:
- Icon + label
- Active state: `bg-primary/10 text-primary` with left accent bar (3px rounded)
- Hover state: `bg-accent text-accent-foreground`
- `cursor: pointer` on all items
- Clicking navigates to the page AND closes the drawer

Items:
- 📊 Overview (`/`)
- 💬 Chat (`/chat`)
- 🖥️ My Devices (`/devices`)
- 👥 Users (`/users`) — admin only
- ⚙️ Settings (`/settings`) — admin only

Separated from chats section by a subtle `border-b`.

#### 2c. Chats Section Header

A row between the navigation and chat list:

```
Chats                    [+ New Chat]  [⋮]
```

- "Chats" label (text-xs uppercase tracking-wide, muted)
- **+ New Chat** button (ghost variant, icon + text)
- **⋮ overflow menu** (Popover or DropdownMenu):
  - Sort by: Last activity | Created date | A–Z
  - Show: All | Pinned only
  - Select mode (for bulk delete)

#### 2d. Chat List (scrollable)

The main scrollable area. Two sub-sections:

**Pinned chats** (if any):
- Preceded by a small "Pinned" label (text-[10px] uppercase muted)
- Pin icon (📌) replaces the chat bubble icon
- Sorted within pinned by last activity

**Recent chats** (remaining):
- Preceded by "Recent" label if pinned chats exist, otherwise no label
- Each chat row shows:
  - Chat icon (💬) or pin icon (📌)
  - Title (truncated) — defaults to "New Chat"
  - Relative time ("2h ago") and message count ("· 5 msgs")
- **Active chat**: `bg-primary/10 text-primary` highlight
- **Hover**: `bg-accent`, shows action icons
- **Hover action icons** (right side, appear on hover):
  - 📌 Pin/Unpin
  - ✏️ Rename
  - 🗑️ Delete
- **Click**: Navigates to `/chat`, sets active session, closes drawer
- **Double-click title**: Inline rename mode

**Empty state**: "No chats yet. Start a new conversation!" centered.
**No search results**: "No matching chats." centered.

#### 2e. Footer (pinned to bottom)

For non-admin users, settings link goes here instead of navigation.

- **Settings** link (if not admin — admins see it in nav): ⚙️ Settings
- **Dark/light toggle**: Sun/Moon icon button
- Separated from chat list by `border-t`

### 3. Account Dropdown (top-right of header)

Clicking the avatar circle opens a Popover/DropdownMenu:
- **Username** (bold) + role ("Administrator" or "User") — display only
- **Divider**
- **Dark mode toggle** — "Dark mode" label + switch/toggle
- **Logout** — destructive action

### 4. Pin Chats Feature

**Storage:** Client-side, in `localStorage` key `pinned_chats` as a JSON array of
session IDs.

**Behavior:**
- Toggle pin via hover action icon on each chat row
- Pinned chats always appear at the top of the list, separated by a "Pinned" / "Recent"
  divider
- Pins persist across sessions (localStorage)
- If a pinned session is deleted, its ID is silently removed from the pin list
- Maximum pins: No hard limit (but UI naturally discourages pinning too many)

**Future:** Consider server-side pin storage for cross-device sync.

### 5. Interaction States

Every interactive element must have:
- `cursor: pointer` — the hand cursor on hover
- **Hover background** — subtle background color change (`bg-accent` or similar)
- **Active/pressed** — slightly darker than hover
- **Focus ring** — for keyboard accessibility (`focus-visible:ring-2`)
- **Transition** — `transition-colors` for smooth hover/active transitions

### 6. Architectural Changes

The key refactor is **lifting chat session state** out of `Chat.tsx` and into a shared
context so the drawer (in `Dashboard.tsx`) can display and manage chat sessions.

#### New: `ChatSessionProvider` (React Context)

Provides:
- `sessions: Session[]` — all sessions
- `activeSessionId: string | undefined`
- `setActiveSessionId(id)` — sets active chat
- `fetchSessions()` — refreshes session list
- `createSession()` → returns new session ID
- `deleteSession(id)` / `deleteSessions(ids[])`
- `renameSession(id, title)`
- `pinnedIds: Set<string>` + `togglePin(id)`
- `sortBy` / `filterBy` state + setters

#### Modified: `Dashboard.tsx`

- Remove the old collapsible desktop sidebar and mobile-only header
- Replace with: fixed top header bar + Sheet drawer
- Drawer renders: search → nav → chats → footer
- Wraps children with `ChatSessionProvider`

#### Modified: `Chat.tsx`

- Remove all session management (moved to context)
- Remove its own Sheet sidebar
- Consume `ChatSessionProvider` for activeSessionId and sessions
- Only manages: messages, streaming, send

#### Modified: `ChatSidebar.tsx` → `DrawerChatList.tsx` (or inline)

- Becomes the chat list portion of the unified drawer
- Receives sessions/pins/actions from context
- Search, sort, filter handled by the drawer

### 7. Responsive Behavior

The design is identical on all screen sizes:
- **Header**: Always visible, fixed at top
- **Drawer**: Always a Sheet overlay (never inline/pushing)
- **Content**: Full width below header, `pt-14` to clear header

No breakpoint-specific layouts for the sidebar/drawer. True mobile-first.

---

## File Changes Summary

| File | Change |
|------|--------|
| `src/contexts/ChatSessionContext.tsx` | **New** — shared session state + pin logic |
| `src/pages/Dashboard.tsx` | **Rewrite** — header bar + unified drawer |
| `src/pages/Chat.tsx` | **Simplify** — consume context, render messages only |
| `src/components/chat/ChatSidebar.tsx` | **Delete or inline** — merged into drawer |
| `src/components/chat/ChatArea.tsx` | No change |
| `src/components/chat/ChatInput.tsx` | No change |
| `src/components/chat/MessageList.tsx` | No change |
| `src/components/chat/MessageBubble.tsx` | No change |
| `src/lib/useTheme.ts` | No change |
| `src/index.css` | Minor — ensure `cursor-pointer` on interactive base styles |
