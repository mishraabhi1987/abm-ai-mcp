# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
source venv/bin/activate
uvicorn main:app --reload
```

The server starts at `http://localhost:8000`. The UI is served from `index.html` / `style.css` at the root route.

To test the MCP server directly via the Inspector:

```bash
mcp dev server.py
```

## Required environment variables (`.env`)

```
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...
LITELLM_API_KEY=...
```

`LITELLM_API_KEY` is used to connect to the remote LiteLLM MCP gateway at `https://litellm.tfscreener.com/mcp/`.

## Architecture

The system has two Python files and a legacy standalone client:

**`server.py`** — Local MCP server (FastMCP). Runs as a subprocess via stdio. Provides tools: `calculate`, `fetch_url`, `web_search`, `get_chart_data`, `get_historical_chart`. Also exposes MCP resources (`resource://abm/*`) and a prompt (`lyrics_brief`) used by the lyrics feature. Note: `get_stock_price` and `get_weather` are defined but commented out (`#@mcp.tool()`).

**`main.py`** — FastAPI app and agentic loop. On each `/chat` POST it:

1. Validates attachment size (≤ 15 MB decoded; `ATTACH_LIMIT_BYTES` constant); raises 413 on violation.
2. Builds a content-block list for the user turn: text block for the message, `document` blocks for PDFs, `image` blocks for images, inline `text` blocks (truncated at 4 000 chars) for `.txt`/`.md`. User content is always a block list, never a bare string.
3. Retrieves session history from `SessionStore` (200-message FIFO cap; SQLite TODO seam), appends the user turn, runs the agent, saves back.
4. Connects to the local stdio MCP server (mandatory) via `AsyncExitStack`.
5. Attempts to connect to the remote LiteLLM MCP server with a 5 s `asyncio.wait_for` timeout; any failure logs a warning and continues with local tools only — the request never 500s when LiteLLM is down.
6. Builds a `tool_routing` dict (`tool_name → session`) with `LOCAL_PRIORITY = True` so local tools win on name collision.
7. Deduplicates the merged tool list before sending to Claude — the Anthropic API never receives two tools with the same name.
8. Runs an agentic loop calling `claude-haiku-4-5` (via `AsyncAnthropic`) with the deduplicated tool set.
9. Routes each `tool_use` block through `tool_routing`; unknown tool names return an empty result.
10. Parses MCP result content into Anthropic's strict schema (text/image) before appending as `tool_result`.
11. Detects `CHART_DATA::` in the final text and splits it into `{"text": ..., "chart_data": {...}}` for the frontend to render.

Conversation history is stored in `SessionStore` (module-level `session_store`). `/new` calls `session_store.reset(session_id)`.

**`/api/lyrics`** — Separate endpoint that connects only to the local MCP server, reads the `lyrics://standards` resource and `lyrics_brief` prompt, then calls Claude directly (no tool loop).

**`client.py`** — Standalone CLI agentic loop for local testing only; not used by the web app.

## Chart data flow

`get_chart_data` and `get_historical_chart` tools return a string prefixed with `Render this chart in the UI: CHART_DATA::` followed by a JSON object. The system prompt instructs Claude to copy this verbatim. `main.py` then extracts the JSON with brace-counting (not a simple split) to handle edge cases, and returns it as `chart_data` in the API response.

## Tool routing

`run_agent` builds a single `tool_routing: dict[str, ClientSession]` at startup — LiteLLM tools are inserted first, then local tools overwrite any collision (`LOCAL_PRIORITY = True` constant). Every `call_tool` goes through this map; a tool name not in the map returns `None` (empty result). The tool list sent to Claude is deduplicated by the same priority: iterate `local_tools + litellm_tools`, skip any name already seen. To change collision behaviour, flip `LOCAL_PRIORITY`.

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
- `client.py` is local-CLI only. Do NOT touch it for web-app changes.
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
