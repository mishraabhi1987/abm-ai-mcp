# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

Both backend servers must be running. Start them in separate terminals (or as background tasks):

```bash
source venv/bin/activate
uvicorn main:app --reload           # Main app  → http://localhost:8000
uvicorn agent_server:app --reload --port 8001  # Agent server → http://localhost:8001
```

`main.py` serves the UI and chat API at `http://localhost:8000`. `agent_server.py` serves the Finance agent endpoint (`POST /api/agent/finance`) at `http://localhost:8001`. The Vite dev proxy routes `/api/agent` to port 8001 and `/chat`, `/new` to port 8000.

To test the MCP server directly via the Inspector:

```bash
mcp dev server.py
```

## Required environment variables (`.env`)

```
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...
LITELLM_API_KEY=...
GOOGLE_API_KEY=...
```

`LITELLM_API_KEY` is used to connect to the remote LiteLLM MCP gateway at `https://litellm.tfscreener.com/mcp/`. `GOOGLE_API_KEY` is used by `run_gemini` to call Google AI Studio (not Vertex AI).

## Architecture

The system has three Python server files and two legacy standalone clients:

**`server.py`** — Local MCP server (FastMCP). Runs as a subprocess via stdio. Provides tools: `calculate`, `fetch_url`, `web_search`, `get_chart_data`, `get_historical_chart`. Also exposes MCP resources (`resource://abm/*`) and a prompt (`lyrics_brief`) used by the lyrics feature. Note: `get_stock_price` and `get_weather` are defined but commented out (`#@mcp.tool()`). `fetch_stock_price` and `fetch_stock_news` are plain Python functions (not MCP tools) imported directly by `agent_server.py`.

**`agent_server.py`** — Separate FastAPI app on port 8001. Exposes `POST /api/agent/finance`. Calls `fetch_stock_price` and `fetch_stock_news` directly from `server.py` (not via MCP), then sends the result to Claude (`claude-sonnet-4-6`) for grounded analysis. No agentic loop — single Claude call per request. The Vite proxy routes `/api/agent` to this server.

**`main.py`** — FastAPI app and agentic loop. On each `/chat` POST it:

1. Validates attachment size (≤ 15 MB decoded; `ATTACH_LIMIT_BYTES` constant); raises 413 on violation.
2. Builds a content-block list for the user turn: text block for the message, `document` blocks for PDFs, `image` blocks for images, inline `text` blocks (truncated at 4 000 chars) for `.txt`/`.md`. User content is always a block list, never a bare string.
3. Branches on `req.model` (`Literal["claude-haiku", "qwen-3.5", "gemini"]`, default `"claude-haiku"`):
   - `"qwen-3.5"` → calls `run_ollama(req.message)` directly; **stateless** (no session history stored or read).
   - `"gemini"` → calls `run_gemini(req.message)` directly; **stateless** (no session history stored or read).
   - anything else → retrieves session history from `SessionStore`, appends the user turn, calls `run_agent`, saves history back.
4. Connects to the local stdio MCP server (mandatory) via `AsyncExitStack`.
5. Attempts to connect to the remote LiteLLM MCP server with a 5 s `asyncio.wait_for` timeout; any failure logs a warning and continues with local tools only — the request never 500s when LiteLLM is down.
6. Builds a `tool_routing` dict (`tool_name → session`) with `LOCAL_PRIORITY = True` so local tools win on name collision.
7. Deduplicates the merged tool list before sending to Claude — the Anthropic API never receives two tools with the same name.
8. Runs an agentic loop calling `claude-haiku-4-5` (via `AsyncAnthropic`) with the deduplicated tool set.
9. Routes each `tool_use` block through `tool_routing`; unknown tool names return an empty result.
10. Parses MCP result content into Anthropic's strict schema (text/image) before appending as `tool_result`.
11. Detects `CHART_DATA::` in the final text and splits it into `{"text": ..., "chart_data": {...}}` for the frontend to render.

**`run_ollama(message)`** — async helper (httpx, non-blocking). Calls Ollama at `http://localhost:11434/api/chat` with `model=qwen3.5:4b`, `think=false`, `stream=false`, `num_ctx=4096`. Returns `{"text": ..., "chart_data": None}` — same internal shape as `run_agent`. Three distinct error paths: `ConnectError` → clean "start ollama serve" message; `TimeoutException` → loading hint; any other exception → shows `type(e).__name__` and message. Never raises — always returns a renderable dict.

**`run_gemini(message)`** — async helper (httpx, non-blocking). Calls Google AI Studio REST API (`gemini-3.1-flash-lite` model) using `GOOGLE_API_KEY`. Returns `{"text": ..., "chart_data": None}`. Three distinct error paths: `HTTPStatusError` → status code + response body; `TimeoutException` → retry hint; any other exception → shows `type(e).__name__` and message. Returns `"Gemini unavailable — set GOOGLE_API_KEY in .env."` if the key is missing. Never raises.

Conversation history is stored in `SessionStore` (module-level `session_store`). `/new` calls `session_store.reset(session_id)`.

**`/api/lyrics`** — Separate endpoint that connects only to the local MCP server, reads the `lyrics://standards` resource and `lyrics_brief` prompt, then calls Claude directly (no tool loop). **No longer used by the Artifacts tab** — the Artifacts tab routes lyrics through `/chat` via `sendMessage` so the selected model is respected. The endpoint still exists and is callable directly.

**`client.py`** — Standalone CLI agentic loop for local testing only; not used by the web app.

**`agents/finance_agent.py`** — Standalone CLI script for testing the Finance agent via `claude_agent_sdk`. Connects to `server.py` via stdio MCP and uses `mcp__stock__get_stock_price`, `mcp__stock__get_stock_news`, `mcp__stock__get_chart_data`. Not used by the web app — `agent_server.py` handles the web-facing Finance agent endpoint.

## Chart data flow

`get_chart_data` and `get_historical_chart` tools return a string prefixed with `Render this chart in the UI: CHART_DATA::` followed by a JSON object. The system prompt instructs Claude to copy this verbatim. `main.py` then extracts the JSON with brace-counting (not a simple split) to handle edge cases, and returns it as `chart_data` in the API response.

## Tool routing

`run_agent` builds a single `tool_routing: dict[str, ClientSession]` at startup — LiteLLM tools are inserted first, then local tools overwrite any collision (`LOCAL_PRIORITY = True` constant). Every `call_tool` goes through this map; a tool name not in the map returns `None` (empty result). The tool list sent to Claude is deduplicated by the same priority: iterate `local_tools + litellm_tools`, skip any name already seen. To change collision behaviour, flip `LOCAL_PRIORITY`.

## Model selection

The `ChatRequest.model` field is `Literal["claude-haiku", "qwen-3.5", "gemini"]` (default `"claude-haiku"`). Pydantic returns 422 for any other value — do not change to `str`.

**`frontend/src/models.js`** is the single source of truth for valid frontend model options:
```js
{ id: "claude-haiku", label: "Claude Haiku" }
{ id: "qwen-3.5",     label: "Qwen 3.5 (Local)", isLocal: true }
{ id: "gemini",       label: "Gemini 3.1 Flash Lite" }
```
`isLocal: true` marks models that run locally (no attachments, no session history). To add a new model: (1) add it to `models.js`, (2) add its id to the `Literal` in `ChatRequest`, (3) add a branch in `/chat`. Mark it `isLocal: true` only if it's a locally-running model.

**Chat Bot tab** — `ChatBox.selectedModel` state (default `"gemini"`) → `onSend(text, attachments, model)` → `App.handleSend` → `sendMessage(..., { model })` → POST `/chat`. The `⊕ Attach` button is disabled only for models with `isLocal: true` (currently only `qwen-3.5`). Switching to a local model clears pending attachments. `sendMessage` has no `model` default — callers must always pass it explicitly.

**Artifacts tab** — has its own `selectedModel` state (default `"gemini"`) independent of Chat Bot. Both Code and Lyrics generation pass `model: selectedModel` to `sendMessage`. Changing the model resets `artifactsSessionId` so Code mode starts a clean session. Lyrics uses `LYRICS_INSTRUCTION` prepended to the prompt — no MCP resource/prompt context (unlike the `/api/lyrics` endpoint). The Artifacts tab maintains two isolated sessions — `artifactsSessionId` (Code) and `lyricsSessionId` (Lyrics) — so neither contaminates the Chat Bot's module-level `sessionId`.

The Ollama and Gemini paths are **intentionally stateless** — no session history is stored or retrieved. Do NOT add memory to `run_ollama` or `run_gemini`. `think: False` is set on the Ollama request to suppress chain-of-thought output.

## Skills (`.claude/skills/`)

| Skill | Command | Purpose |
|---|---|---|
| `backend-run` | `/backend-run` | Start both FastAPI servers (ports 8000 + 8001) in background |
| `frontend-run` | `/frontend-run` | Start Vite dev server (port 5173) in background |
| `ollama-run` | `/ollama-run` | Start Ollama if not running, verify API at port 11434, check `qwen3.5:4b` is available |
| `mcp-dev` | `/mcp-dev` | Run `mcp dev server.py` for MCP Inspector testing |

## CI — AI Code Review

`.github/workflows/claude-review.yml` runs on every non-draft PR (open / push). It:
1. Diffs the branch against base with `git diff origin/$base...HEAD`
2. Pipes the diff to `gemini -p` (`@google/gemini-cli`, `--output-format json`, `--skip-trust`)
3. Parses `.response` for the review text; sums `.stats.models[].api.totalErrors` and fails if any errors
4. Uploads `result.json` as a downloadable artifact

Requires `GEMINI_API_KEY` in GitHub repo secrets. The env var `GEMINI_CLI_TRUST_WORKSPACE=true` is set on the CI runner — without it the Gemini CLI treats the fresh checkout as untrusted and exits with code 55. The review appears in the job logs under `===== GEMINI REVIEW =====`.

## Conventions & rules (always follow)

- Always `source venv/bin/activate` before running anything. Python 3.13 venv.
- User message content is always a **block list** (never a bare string) — the `/chat`
  endpoint builds it before appending to history. Do not revert to `content: req.message`.
- Attachments are validated against `ATTACH_LIMIT_BYTES` (15 MB decoded) before processing.
  Exceeding the limit must return a 413, not silently truncate.
- MCP tool results MUST be parsed into Anthropic's strict text/image schema
  before appending as `tool_result` — malformed schema breaks the agentic loop.
- Tool routing is local-first by design (`LOCAL_PRIORITY = True`).
  Deduplication is intentional — do not remove it. If both servers expose the
  same tool name, local wins in both the routing map and the deduplicated tool list.
- The `CHART_DATA::` payload must be passed through verbatim. Never reformat,
  re-indent, or "clean up" it.
- `get_stock_price` and `get_weather` are intentionally commented out.
  Do NOT re-enable without an explicit reason.
- `client.py` and `agents/finance_agent.py` are local-CLI only. Do NOT touch them for web-app changes. Web-facing Finance agent logic lives in `agent_server.py`.
- Do NOT add session memory to `run_ollama` or `run_gemini`. Both stateless paths are stateless by design.
- Do NOT change `ChatRequest.model` from `Literal` back to `str` — the type constraint is intentional.
- `httpx` is used (not `requests`) for both `run_ollama` and `run_gemini` — keep them async.
- `sendMessage` in `chat.js` has no `model` default — every caller must pass `model` explicitly. Do not add a default back; a missing model silently falls back to the backend Pydantic default.
- The `MODELS` array in `frontend/src/models.js` is the single source of truth. Do NOT redefine it in individual components — always import from `../models`.
- Before any commit: show a summary of what changed and why, and WAIT for
  explicit approval. Never commit and push in the same step. Push only after
  the commit is approved.

## Code style

- Python 3.13, FastAPI. Endpoints and MCP calls are async (`async def`).
  Do NOT introduce blocking calls inside the agentic loop.
- snake_case for functions and variables, matching existing code
  (`run_agent`, `local_tool_names`, `get_chart_data`, `litellm_session`).
- New MCP tools go in server.py using the `@mcp.tool()` decorator.
  Follow the existing tool signature + docstring pattern; don't invent a new one.
- Keep `CHART_DATA::` extraction as brace-counting, never a plain string split.
- Prefer small, single-purpose functions over large catch-all handlers.
