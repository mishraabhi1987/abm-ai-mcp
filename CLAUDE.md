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

1. Connects to both the local stdio MCP server and the remote LiteLLM MCP server simultaneously.
2. Merges their tool lists (`local_tools + litellm_tools`).
3. Runs an agentic loop calling `claude-haiku-4-5` with the merged tool set.
4. Routes each `tool_use` block back to whichever server owns that tool name (`local_tool_names` vs `litellm_tool_names`).
5. Parses MCP result content into Anthropic's strict schema (text/image) before appending as `tool_result`.
6. Detects `CHART_DATA::` in the final text and splits it into `{"text": ..., "chart_data": {...}}` for the frontend to render.

Conversation history is stored in memory per `session_id` in the `conversations` dict. `/new` clears a session.

**`/api/lyrics`** — Separate endpoint that connects only to the local MCP server, reads the `lyrics://standards` resource and `lyrics_brief` prompt, then calls Claude directly (no tool loop).

**`client.py`** — Standalone CLI agentic loop for local testing only; not used by the web app.

## Chart data flow

`get_chart_data` and `get_historical_chart` tools return a string prefixed with `Render this chart in the UI: CHART_DATA::` followed by a JSON object. The system prompt instructs Claude to copy this verbatim. `main.py` then extracts the JSON with brace-counting (not a simple split) to handle edge cases, and returns it as `chart_data` in the API response.

## Tool routing

Tool names are partitioned into `local_tool_names` and `litellm_tool_names` sets at the start of each `run_agent` call. Any tool not in either set returns `None` and becomes an empty-result `tool_result`. There is no deduplication if both servers expose a tool with the same name — the first match (local) wins since routing checks local first.

## Conventions & rules (always follow)

- Always `source venv/bin/activate` before running anything. Python 3.13 venv.
- MCP tool results MUST be parsed into Anthropic's strict text/image schema
  before appending as `tool_result` — malformed schema breaks the agentic loop.
- Tool routing is local-first by design. Do NOT add deduplication logic;
  if both servers expose the same tool name, local wins on purpose.
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
