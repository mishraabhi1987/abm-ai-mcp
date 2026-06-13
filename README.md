# MCP Server — Learning Project

A first Model Context Protocol (MCP) server built with the FastMCP SDK. Exposes a simple `add` tool, tested via the MCP Inspector.

**Stack:** Python 3.13 (venv) · mcp SDK 1.27.2 · uv · macOS (M2)

---

## Setup

```bash
# 1. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. MCP SDK (with CLI + Inspector)
pip install "mcp[cli]"

# 3. uv (required by the Inspector's default launcher)
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify
uv --version
mcp version
```

---

## Run & test

```bash
mcp dev server.py
```

uvicorn main:app --reload

Opens the Inspector at a local URL (e.g. `http://localhost:6274`) and connects automatically.

Then: **Tools** tab → **List Tools** → select `add` → enter `a`, `b` → **Run Tool** → result.

Stop the server with `Ctrl + C`.

> Note: `mcp dev` runs the server via `uv`, isolated from the local venv. If the server uses extra libraries later, pass them explicitly, e.g. `mcp dev server.py --with requests`.

---

## Concept — MCP architecture

**Host → MCP Client → MCP Server**

- **Host** (e.g. Claude app): decides a tool is needed.
- **Client**: sends the `tools/call` message to the server.
- **Server** (`server.py`): executes the tool and returns the result.

The LLM decides _which_ tool to call; the server only _executes_. The LLM is involved twice — once to choose the tool + arguments, once to form the final answer from the result.

The Inspector's History panel shows the real protocol messages: `initialize` → `tools/list` → `tools/call`.

---

## Next steps

- [ ] Add a second tool (handle multiple tools)
- [ ] Write a custom Python client (call the server from code, no Inspector)
- [ ] Later: expose RAG retrieval as an MCP tool → capstone integration
