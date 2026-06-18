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

**Code mode** — prepends `CODE_INSTRUCTION` to the user prompt, calls `sendMessage`, extracts raw HTML from the response with `extractCode` (strips markdown fences if present), and passes it to `<CodeArtifact />`. `CodeArtifact` provides an editable textarea (Code view) and a sandboxed live iframe (Preview view), toggled via a tab strip. A `wrapForPreview` harness is defined in `CodeArtifact.jsx` but deliberately bypassed — the iframe uses `srcDoc={code}` directly.

**Lyrics mode** — calls `generateLyrics(prompt)` which hits `/api/lyrics`. Output is shown in `<CopyBlock />` with a one-click copy button (clipboard API with `execCommand` fallback).

Mode state resets output and error on toggle — intentional.

## Component conventions

- All styles are inline JS objects defined in a `styles` const at the top of each file. No CSS modules or Tailwind.
- Always import colors/fonts from `theme.js`. The `C` shorthand objects in `Artifacts.jsx` and `CodeArtifact.jsx` are a legacy pattern — do not add more.
- `Bubble.jsx` renders user messages as plain `pre-wrap` text and assistant messages as markdown via `marked.parse()` with a `<style>` block injected inline (`mdStyles`). Do not change the rendering path without updating `mdStyles`.
- `ChartWidget.jsx` requires all Chart.js primitives to be registered at module load — do not remove the `ChartJS.register(...)` call.
- File on disk is `Copyblock.jsx` (lowercase b) but imported everywhere as `CopyBlock`. Match the import casing, not the filename, when referencing it.

## API layer (`src/api/chat.js`)

`sessionId` is held in module-level scope (persists across renders, resets on `newChat()`). Three exports:

- `sendMessage(message, mode?)` — POST `/chat`, returns `{ answer, chartData }`.
- `newChat()` — POST `/new`, nulls out `sessionId`.
- `generateLyrics(prompt)` — POST `http://localhost:8000/api/lyrics`, returns `{ lyrics }`. The whole input is passed as the `mood` field.
