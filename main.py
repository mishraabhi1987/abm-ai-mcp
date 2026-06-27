import sys
import os
import uuid
import json
import asyncio
import base64
import httpx
from contextlib import AsyncExitStack
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
from dotenv import load_dotenv
from anthropic import AsyncAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import stdio_client
from datetime import datetime
from zoneinfo import ZoneInfo


load_dotenv()
anthropic = AsyncAnthropic()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

server_params = StdioServerParameters(
    command=sys.executable,
    args=["server.py"],
    env=os.environ,
)

# LiteLLM MCP server config
LITELLM_URL = "https://litellm.tfscreener.com/mcp/"
LITELLM_HEADERS = {
    "Authorization": f"Bearer {os.getenv('LITELLM_API_KEY')}",
}
LOCAL_PRIORITY = True  # local tool wins on name collision with LiteLLM
ATTACH_LIMIT_BYTES = 15 * 1024 * 1024  # 15 MB decoded attachment ceiling

now = datetime.now(ZoneInfo("Asia/Kolkata"))

SYSTEM_PROMPT = (
"You are ABM AI, created by Abhishek (ABM Technologies). "
    f"The current date and time is {now.strftime('%A, %B %d, %Y, %I:%M %p')} IST. "
    "Use this as the single anchor for every date, weekday, age, duration, or 'current' "
    "calculation — compute from it, never from memory or assumption. "
    "Verify before you assert: for current events, prices, live data, who-holds-a-role, "
    "or any product/version/model status, use web_search first. Do not guess, and do not "
    "refuse when a quick search can confirm. "
    "Use a tool only when the request genuinely matches it; otherwise answer directly. "
    "Stay internally consistent: if your own analysis shows no problem, say so plainly — "
    "never label a non-issue as a 'bug', 'error', or 'inconsistency', and never contradict "
    "your own conclusion within the same answer. "
    "Report only findings you can defend; flag uncertainty explicitly instead of inflating it. "
    "Do not expose internal tool mechanics or say 'I don't have a function'."
    "When the user asks for a chart or graph, FIRST write a complete text summary "
    "with actual numbers, prices, and key insights as plain text. "
    "THEN on a new line add CHART_DATA:: followed by the chart tool output. "
    "Example format: 'TCS: ₹2161.40 (+1.15%) | Wipro: ₹180.14 (+1.57%) | TCS is 12x higher.\nCHART_DATA::...'"
    "When get_chart_data tool returns a result starting with 'Render this chart in the UI: CHART_DATA::', "
    "you MUST copy that entire line including CHART_DATA:: and everything after it verbatim into your response."
)

class SessionStore:
    """In-memory session store with per-session message cap.
    TODO: replace _store with an aiosqlite backend for persistence across restarts.
    Interface contract: callers use only get / set / reset.
    """
    MAX_MESSAGES = 200

    def __init__(self):
        self._store: dict[str, list] = {}

    def get(self, session_id: str) -> list:
        return list(self._store.get(session_id, []))

    def set(self, session_id: str, messages: list) -> None:
        self._store[session_id] = messages[-self.MAX_MESSAGES :]

    def reset(self, session_id: str) -> None:
        self._store.pop(session_id, None)


session_store = SessionStore()


class Attachment(BaseModel):
    filename: str
    media_type: str
    data_base64: str


class ChatRequest(BaseModel):
    message: str = ""
    mode: str = "auto"
    session_id: str | None = None
    attachments: list[Attachment] | None = None
    model: Literal["claude-haiku", "qwen-3.5", "gemini"] = "claude-haiku"


async def run_agent(messages: list, mode: str = "auto") -> dict:
    async with AsyncExitStack() as stack:
        # --- Local session (mandatory) ---
        local_read, local_write = await stack.enter_async_context(
            stdio_client(server_params)
        )
        local_session = await stack.enter_async_context(
            ClientSession(local_read, local_write)
        )
        await local_session.initialize()
        local_tools_resp = await local_session.list_tools()
        local_tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
            }
            for t in local_tools_resp.tools
        ]

        # --- LiteLLM session (optional, 5 s timeout) ---
        litellm_session = None
        litellm_tools = []

        async def _open_litellm(s: AsyncExitStack):
            r, w, _ = await s.enter_async_context(
                streamablehttp_client(LITELLM_URL, headers=LITELLM_HEADERS)
            )
            ls = await s.enter_async_context(ClientSession(r, w))
            await ls.initialize()
            resp = await ls.list_tools()
            return ls, [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                }
                for t in resp.tools
            ]

        _litellm_stack = AsyncExitStack()
        try:
            litellm_session, litellm_tools = await asyncio.wait_for(
                _open_litellm(_litellm_stack), timeout=5.0
            )
            await stack.enter_async_context(_litellm_stack)
        except Exception as e:
            await _litellm_stack.aclose()
            print(f"Warning: LiteLLM unavailable ({type(e).__name__}), using local tools only.")

        # --- Routing map: tool_name -> session (LOCAL_PRIORITY: local wins on collision) ---
        tool_routing: dict = {}
        for t in litellm_tools:
            tool_routing[t["name"]] = litellm_session
        if LOCAL_PRIORITY:
            for t in local_tools:
                tool_routing[t["name"]] = local_session

        # --- Deduplicate tools sent to Claude (local wins on collision) ---
        seen_names: set = set()
        all_tools = []
        for t in local_tools + litellm_tools:
            if t["name"] not in seen_names:
                seen_names.add(t["name"])
                all_tools.append(t)

        # --- mode / tool_choice setup ---
        if mode == "auto":
            active_tools = all_tools
            tool_choice = {"type": "auto"}
        else:
            active_tools = [t for t in all_tools if t["name"] == mode]
            if not active_tools:
                active_tools = all_tools
                tool_choice = {"type": "auto"}
            else:
                tool_choice = {"type": "tool", "name": mode}

        # --- Agentic loop ---
        while True:
            response = await anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=active_tools,
                tool_choice=tool_choice,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                final = ""
                for block in response.content:
                    if block.type == "text":
                        final += block.text

                if "CHART_DATA::" in final:
                    parts = final.split("CHART_DATA::")
                    text_part = parts[0].replace("Render this chart in the UI:", "").strip()
                    raw = parts[1].strip() if len(parts) > 1 else ""

                    # find the balanced {...} JSON block after the marker
                    brace_count = 0
                    json_end = 0
                    for i, ch in enumerate(raw):
                        if ch == "{":
                            brace_count += 1
                        elif ch == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break

                    # GUARD: only parse if we actually found a complete JSON block
                    chart_part = None
                    if json_end > 0:
                        try:
                            chart_part = json.loads(raw[:json_end])
                        except json.JSONDecodeError:
                            chart_part = None  # malformed/truncated -> show text only

                    if chart_part is not None:
                        if not text_part:
                            text_part = f"📊 {chart_part.get('title', 'Chart')}"
                        return {"text": text_part, "chart_data": chart_part}

                    # chart missing/broken -> graceful text, NEVER a 500
                    fallback = text_part or final.replace("CHART_DATA::", "").strip()
                    return {"text": fallback, "chart_data": None}

                return {"text": final, "chart_data": None}

            # --- TOOL EXECUTION with ROUTING ---
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    session = tool_routing.get(block.name)
                    result = await session.call_tool(block.name, block.input) if session else None

                    # --- Parse MCP content to match Anthropic strict schema ---
                    formatted_content = []
                    if result and hasattr(result, "content") and result.content:
                        for item in result.content:
                            if item.type == "text":
                                formatted_content.append({
                                    "type": "text",
                                    "text": item.text
                                })
                            elif item.type == "image":
                                # Anthropic expects 'source' wrapper and 'media_type' instead of 'mimeType'
                                formatted_content.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": getattr(item, "mimeType", "image/jpeg"),
                                        "data": item.data
                                    }
                                })
                            else:
                                # Fallback for any unknown types
                                formatted_content.append({
                                    "type": "text",
                                    "text": str(item)
                                })
                    else:
                        formatted_content = "Tool not found or returned empty result"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": formatted_content,
                    })
            if not tool_results: 
                salvage = ""
                for b in response.content:
                    if b.type == "text":
                        salvage += b.text
                return {"text": salvage or "Sorry, I couldn't generate a response. Please try again.", "chart_data": None}
            messages.append({"role": "user", "content": tool_results})
            tool_choice = {"type": "auto"}


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"


async def run_gemini(message: str) -> dict:
    if not GOOGLE_API_KEY:
        return {"text": "Gemini unavailable — set GOOGLE_API_KEY in .env.", "chart_data": None}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                GEMINI_URL,
                params={"key": GOOGLE_API_KEY},
                json={"contents": [{"parts": [{"text": message}]}]},
            )
            resp.raise_for_status()
            data = resp.json()
            text = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text")
                or "Gemini returned an empty response."
            )
            return {"text": text, "chart_data": None}
    except httpx.HTTPStatusError as e:
        return {"text": f"Gemini API error ({e.response.status_code}): {e.response.text}", "chart_data": None}
    except httpx.TimeoutException:
        return {"text": "Gemini request timed out — try again.", "chart_data": None}
    except Exception as e:
        return {"text": f"Gemini error ({type(e).__name__}): {e}", "chart_data": None}


async def run_ollama(message: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "qwen3.5:4b",
                    "messages": [{"role": "user", "content": message}],
                    "think": False,
                    "stream": False,
                    "options": {"num_ctx": 4096},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("message", {}).get("content") or "Ollama returned an empty response."
            return {"text": text, "chart_data": None}
    except httpx.ConnectError:
        return {"text": "Local model offline — start `ollama serve`.", "chart_data": None}
    except httpx.TimeoutException:
        return {"text": "Ollama request timed out — the model may still be loading, try again.", "chart_data": None}
    except Exception as e:
        return {"text": f"Ollama error ({type(e).__name__}): {e}", "chart_data": None}


@app.get("/")
async def index():
    return FileResponse("index.html")


@app.get("/style.css")
async def styles():
    return FileResponse("style.css")


@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    # Validate total attachment size
    if req.attachments:
        total = sum(len(a.data_base64) * 3 // 4 for a in req.attachments)
        if total > ATTACH_LIMIT_BYTES:
            raise HTTPException(status_code=413, detail="Attachments exceed 15 MB limit")

    # Build content blocks for the user turn
    content: list = []
    if req.message:
        content.append({"type": "text", "text": req.message})
    for a in (req.attachments or []):
        if a.media_type == "application/pdf":
            content.append({
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": a.data_base64},
            })
        elif a.media_type.startswith("image/"):
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": a.media_type, "data": a.data_base64},
            })
        elif a.media_type in ("text/plain", "text/markdown"):
            text = base64.b64decode(a.data_base64).decode("utf-8", errors="replace")[:4000]
            content.append({"type": "text", "text": f"[{a.filename}]\n{text}"})
    if not content:
        content = [{"type": "text", "text": ""}]

    if req.model == "qwen-3.5":
        result = await run_ollama(req.message)
    elif req.model == "gemini":
        result = await run_gemini(req.message)
    else:
        history = session_store.get(session_id)
        history.append({"role": "user", "content": content})
        result = await run_agent(history, req.mode)
        session_store.set(session_id, history)

    return {
        "answer": result["text"],
        "chart_data": result["chart_data"],
        "session_id": session_id,
    }


@app.post("/new")
async def new_chat(req: ChatRequest):
    if req.session_id:
        session_store.reset(req.session_id)
    return {"ok": True}

# ============================================================
#  ADD THIS to main.py  (Lyrics endpoint for Artifacts -> Lyrics mode)
#  Uses the LOCAL MCP server's prompt + resource that you added to server.py:
#    resource: lyrics://standards
#    prompt:   lyrics_brief
#  NOTE: read_resource / get_prompt return-shapes vary slightly by SDK version.
#  On first run, print(res) and print(pr) once and adjust .contents / .messages
#  if the fields differ — do not assume in the dark.
# ============================================================


class LyricsRequest(BaseModel):
    mood: str
    theme: str = ""
    anchor: str = ""


async def run_lyrics(mood: str, theme: str = "", anchor: str = "") -> str:
    # Only the LOCAL stdio server is needed (it holds the lyrics primitives).
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. RESOURCE  (App-controlled standards)
            res = await session.read_resource("lyrics://standards")
            standards = res.contents[0].text

            # 2. PROMPT  (User-controlled brief)
            args = {"mood": mood}
            if theme:
                args["theme"] = theme
            if anchor:
                args["anchor"] = anchor
            pr = await session.get_prompt("lyrics_brief", arguments=args)
            brief = pr.messages[0].content.text

            # 3. Standards as system, brief as the user turn -> Claude writes the lyrics.
            response = await anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=8000,
                system=standards,
                messages=[{"role": "user", "content": brief}],
            )
            return "".join(b.text for b in response.content if b.type == "text")


@app.post("/api/lyrics")
async def lyrics(req: LyricsRequest):
    text = await run_lyrics(req.mood, req.theme, req.anchor)
    return {"lyrics": text}