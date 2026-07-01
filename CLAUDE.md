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

`LITELLM_API_KEY` is used to connect to the remote LiteLLM MCP gateway at `https://litellm.tfscreener.com/mcp/`. `GOOGLE_API_KEY` is used by `run_gemini_agent` to call Google AI Studio (not Vertex AI).

## Architecture

The system has three Python server files and one standalone CLI client:

**`server.py`** — Local MCP server (FastMCP). Runs as a subprocess via stdio. Provides tools: `calculate`, `fetch_url`, `web_search`, `get_stock_price`, `get_stock_news`, `get_weather`, `get_stock_price_data`, `get_stock_news_data`, `get_chart_data`, `get_historical_chart`. Also exposes MCP resources (`resource://abm/*`) and a prompt (`lyrics_brief`) used by the lyrics feature. `fetch_stock_price` and `fetch_stock_news` are plain Python functions (not MCP tools) used internally by the structured-data tools above.

**`agent_server.py`** — Separate FastAPI app on port 8001. Exposes `POST /api/agent/finance`. Opens a per-request MCP session (stdio_client + ClientSession) and uses `ToolRegistry` to call `get_stock_price_data` and `get_stock_news_data`, then sends the result to Claude (`claude-haiku-4-5`) for grounded analysis. No agentic loop — single Claude call per request. The Vite proxy routes `/api/agent` to this server.

**`main.py`** — FastAPI app and agentic loops. On each `/chat` POST it:

1. Validates attachment size (≤ 15 MB decoded; `ATTACH_LIMIT_BYTES` constant); raises 413 on violation.
2. Builds a content-block list for the user turn: text block for the message, `document` blocks for PDFs, `image` blocks for images, inline `text` blocks (truncated at 4 000 chars) for `.txt`/`.md`. User content is always a block list, never a bare string.
3. Opens a local stdio MCP session and wraps it in a `ToolRegistry`.
4. Branches on `req.model` (`Literal["claude-haiku", "qwen-3.5", "gemini"]`, default `"claude-haiku"`):
   - `"qwen-3.5"` → calls `run_qwen_agent(req.message, registry)`; **stateless** (no session history stored or read).
   - `"gemini"` → calls `run_gemini_agent(req.message, registry)`; **stateless** (no session history stored or read).
   - anything else → retrieves session history from `SessionStore`, appends the user turn, calls `run_haiku(history, registry, mode)`, saves history back.

**`run_haiku(messages, registry, mode)`** — Claude Haiku agentic loop (max `MAX_TURNS=6`). Optionally connects to LiteLLM MCP (5 s timeout; failures are non-fatal). Builds a `tool_routing: dict[str, ToolRegistry]` with `LOCAL_PRIORITY = True` so local tools win on name collision. Deduplicates the merged tool list before sending to Claude. Routes each `tool_use` block through the appropriate `ToolRegistry.execute()`; injects results as Anthropic `tool_result` blocks. Detects `CHART_DATA::` via `_extract_chart` (brace-counting, never a plain split). Returns `{"text": ..., "chart_data": ...}`.

**`run_gemini_agent(message, registry)`** — Gemini tool-calling loop (max `MAX_TURNS=6`). Calls `registry.get_tools("gemini")` for the `functionDeclarations` envelope. Detects `functionCall` parts in each response; re-injects results as `functionResponse` parts in a `"user"` turn. Returns `_extract_chart(text)` — never hardcodes `chart_data: None`.

**`run_qwen_agent(message, registry)`** — Qwen/Ollama tool-calling loop (max `MAX_TURNS=6`). Prepends `QWEN_SYSTEM` as a `role: "system"` message instructing Qwen to use `.NS` suffix for Indian stocks and reproduce `CHART_DATA::` verbatim. Calls `registry.get_tools("openai")` for the OpenAI-style tool schema. Detects `tool_calls` in the Ollama response; handles `arguments` as dict or JSON string (logger.warning on JSONDecodeError, never silent crash). Re-injects results as `{"role": "tool", ...}` messages. Returns `_extract_chart(text)` — never hardcodes `chart_data: None`.

All three runners return the fallback `"Reached reasoning limit — please rephrase or break the question into smaller parts."` if `MAX_TURNS` is exhausted without a final answer.

Conversation history is stored in `SessionStore` (module-level `session_store`). `/new` calls `session_store.reset(session_id)`.

**`/api/lyrics`** — Separate endpoint that connects only to the local MCP server, reads the `lyrics://standards` resource and `lyrics_brief` prompt, then calls Claude directly (no tool loop). **No longer used by the Artifacts tab** — the Artifacts tab routes lyrics through `/chat` via `sendMessage` so the selected model is respected. The endpoint still exists and is callable directly.

**`client.py`** — Standalone CLI agentic loop for local testing only; not used by the web app.

## ToolRegistry

**`tool_registry.py`** — Thin adapter between an MCP `ClientSession` and the three model providers. Session lifecycle is owned by the caller's `AsyncExitStack`; the registry just holds a reference.

- `get_tools(format)` → `"anthropic"` | `"gemini"` | `"openai"` — fetches `list_tools()` and reshapes the schema for the target provider. `_to_gemini` returns `[]` on an empty tool list (guards against sending an empty `functionDeclarations` envelope).
- `execute(name, arguments)` → `str` — calls `call_tool`, raises `RuntimeError` if `isError=True`, otherwise concatenates `TextContent` blocks. Non-text blocks are `logger.warning`-skipped (never `str()`'d, to prevent Python repr corrupting downstream `json.loads` callers).

## Chart data flow

`get_chart_data` and `get_historical_chart` tools return a string prefixed with `Render this chart in the UI: CHART_DATA::` followed by a JSON object. All three runners (`run_haiku`, `run_gemini_agent`, `run_qwen_agent`) call `_extract_chart(text)` on their final text response — never hardcode `chart_data: None`. `_extract_chart` in `main.py` splits on the marker and extracts the JSON with brace-counting (not a simple split) to handle edge cases, returning `{"text": ..., "chart_data": ...}`.

## Tool routing

`run_haiku` builds `tool_routing: dict[str, ToolRegistry]` — LiteLLM tools map to the LiteLLM `ToolRegistry`, local tools map to the local `ToolRegistry`. Local wins on name collision (`LOCAL_PRIORITY = True`). The tool list sent to Claude is deduplicated by the same priority. `run_gemini_agent` and `run_qwen_agent` use only the local registry (no LiteLLM). To change collision behaviour, flip `LOCAL_PRIORITY`.

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

**Agents tab** — renders `<Agents />` (Finance Agent UI). Calls `POST /api/agent/finance` (proxied to `agent_server.py` on port 8001) via `frontend/src/api/agents.js:runFinanceAgent`. Stateless — no session ID. Returns structured `{ price, news, analysis, query }` which the component renders as a price hero card, news cards, and a markdown analysis block. Adding new agent modes: add to the `MODES` array in `Agents.jsx` and branch in `handleRun`.

The Qwen and Gemini paths are **intentionally stateless** — no session history is stored or retrieved. Do NOT add memory to `run_qwen_agent` or `run_gemini_agent`. `think: False` is set on the Ollama request to suppress chain-of-thought output.

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
- MCP tool results from `ToolRegistry.execute()` are already normalized to plain strings.
  Do not re-parse or re-wrap them before appending as `tool_result` content.
- Tool routing is local-first by design (`LOCAL_PRIORITY = True`).
  Deduplication is intentional — do not remove it. If both servers expose the
  same tool name, local wins in both the routing map and the deduplicated tool list.
- The `CHART_DATA::` payload must be passed through verbatim. Never reformat,
  re-indent, or "clean up" it.
- `client.py` is local-CLI only. Do NOT touch it for web-app changes.
- Do NOT add session memory to `run_qwen_agent` or `run_gemini_agent`. Both stateless paths are stateless by design.
- Do NOT change `ChatRequest.model` from `Literal` back to `str` — the type constraint is intentional.
- `httpx` is used (not `requests`) for both `run_qwen_agent` and `run_gemini_agent` — keep them async.
- `sendMessage` in `chat.js` has no `model` default — every caller must pass `model` explicitly. Do not add a default back; a missing model silently falls back to the backend Pydantic default.
- The `MODELS` array in `frontend/src/models.js` is the single source of truth. Do NOT redefine it in individual components — always import from `../models`.
- Before any commit: show a summary of what changed and why, and WAIT for
  explicit approval. Never commit and push in the same step. Push only after
  the commit is approved.

## Code style

- Python 3.13, FastAPI. Endpoints and MCP calls are async (`async def`).
  Do NOT introduce blocking calls inside the agentic loop.
- snake_case for functions and variables, matching existing code
  (`run_haiku`, `run_gemini_agent`, `run_qwen_agent`, `get_chart_data`).
- New MCP tools go in server.py using the `@mcp.tool()` decorator.
  Follow the existing tool signature + docstring pattern; don't invent a new one.
- Keep `CHART_DATA::` extraction as brace-counting, never a plain string split.
- Prefer small, single-purpose functions over large catch-all handlers.
