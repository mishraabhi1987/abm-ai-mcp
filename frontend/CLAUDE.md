# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & commands

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # outputs to frontend/dist
npm run lint
```

The dev server proxies `/chat` and `/new` to `http://localhost:8000` (the FastAPI backend must be running separately). `generateLyrics` in `api/chat.js` hits `http://localhost:8000/api/lyrics` directly via a hardcoded `LYRICS_API_BASE` — the Vite proxy does not cover `/api/lyrics`.

## Stack

React 19 · Vite 8 · `@vitejs/plugin-react` · Chart.js 4 + react-chartjs-2 · marked (markdown rendering) · No TypeScript.

## Theme system (`src/theme.js`)

All colors, fonts, and spacing tokens live in `theme.js`. The active theme is exported as `theme` (currently `emberTheme`). Import it in every component — never hardcode brand values inline.

| Token | Value | Role |
|---|---|---|
| `theme.primary` | `#c70505` | ABM red — CTAs, accents, logo A |
| `theme.accent` | `#ffc83d` | Gold — highlights, logo B, h2/h3 |
| `theme.accentDeep` | `#e0a418` | Darker gold — active tab pill background |
| `theme.bg` | `#0a0a0b` | Page background |
| `theme.sora` | Sora, sans-serif | Headings, tab labels |
| `theme.inter` | Inter, system-ui | Body text |
| `theme.mono` | IBM Plex Mono | Code, tagline |

To add a new theme, define it in `theme.js` and add it to the `themes` registry. Do not change `ember` theme values without explicit intent.

## Layout architecture (`App.jsx`)

The page is a fixed-height flex column (`100vh`, no page scroll). Three zones:

1. **Top** (`flexShrink: 0`) — `<Header />` + `<TabBar />`. Never scrolls.
2. **Middle** (`flex: 1, minHeight: 0`) — the only scrollable region (`overflowY: auto`). Holds the message feed. `minHeight: 0` on both the flex parent and scroll child is required — removing it breaks overflow.
3. **Bottom** (`flexShrink: 0`) — `<ChatBox />`. Pinned, never scrolls.

When the Artifacts tab is active, the middle+bottom zone is replaced wholesale by `<Artifacts />`, which replicates the same flex column structure internally.

## Tab bar & routing (`TabBar.jsx`, `App.jsx`)

Tabs are defined in the `TABS` array in `TabBar.jsx`:

```js
const TABS = ["Chat Bot", "Artifacts", "Agents", "Career", "News / Social"];
```

`App.jsx` compares `activeTab` against the string `"Artifacts"` (via the `ARTIFACTS_TAB` constant). Only `Chat Bot` and `Artifacts` have distinct views — clicking `Agents`, `Career`, or `News / Social` highlights the tab but falls through to the Chat pane. These tabs are not wired.

Active tab styling: `theme.accentDeep` background pill. Tab font: Sora 600.

## Artifacts panel (`Artifacts.jsx`)

Internal sub-mode toggle: `"code"` | `"lyrics"`. Both modes are fully functional.

**Code mode** — maintains its own `artifactsSessionId` state for multi-turn refinement. Each generate call passes this session ID to `sendMessage` and updates it from the response. `CODE_INSTRUCTION` instructs the model to modify existing code incrementally (not rebuild) and default to a dark background. Mode switches via `switchMode()` which resets `artifactsSessionId`, `output`, and `error` — intentional so Code and Lyrics contexts don't bleed across switches. `extractCode` strips markdown fences if present; the cleaned HTML is passed to `<CodeArtifact />` for live iframe preview.

**Lyrics mode** — always stateless and one-shot. Calls `generateLyrics(prompt)` directly (no session ID). Output shown in `<CopyBlock />`. Do NOT add session memory to lyrics generation.

**`switchMode(next)`** is the only correct way to change mode — do not call `setMode` directly, as it would skip the session and output resets.

## Component conventions

- All styles are inline JS objects defined in a `styles` const at the top of each file. No CSS modules or Tailwind.
- Always import colors/fonts from `theme.js`. The `C` shorthand objects in `Artifacts.jsx` and `CodeArtifact.jsx` are a legacy pattern — do not add more.
- `Bubble.jsx` renders user messages as plain `pre-wrap` text and assistant messages as markdown via `marked.parse()` with a `<style>` block injected inline (`mdStyles`). Do not change the rendering path without updating `mdStyles`.
- `ChartWidget.jsx` requires all Chart.js primitives to be registered at module load — do not remove the `ChartJS.register(...)` call.
- File on disk is `Copyblock.jsx` (lowercase b) but imported everywhere as `CopyBlock`. Match the import casing, not the filename, when referencing it.

## API layer (`src/api/chat.js`)

`sessionId` is held in module-level scope for the main chat tab. Callers that manage their own session (e.g. Artifacts) pass it explicitly via the options argument. Three exports:

- `sendMessage(message, mode?, { sessionId?, attachments? }?)` — POST `/chat`. Returns `{ answer, chartData, sessionId }`. If `sessionId` is passed in options, the module-level session is not updated (caller owns that session). Attachments are `[{ filename, media_type, data_base64 }]`.
- `newChat()` — POST `/new`, nulls out the module-level `sessionId`.
- `generateLyrics(prompt)` — POST `http://localhost:8000/api/lyrics`, returns `{ lyrics }`. Always stateless — no session ID.

## ChatBox (`src/components/ChatBox.jsx`)

`onSend(text, attachments)` — both arguments are now required by callers. `attachments` is an array of `{ filename, media_type, data_base64 }` objects (empty array when no files attached). A hidden `<input type="file">` (PDF, images, `.txt`, `.md`) feeds an `attachments` state; selected files are read to base64 via `FileReader`. File chips (filename + × remove button) render above the textarea when files are present. The `⊕ Attach` button uses the same `secondaryBtn` style as `+ New Chat`. Clear attachments after send — already done in `handleSend`.
