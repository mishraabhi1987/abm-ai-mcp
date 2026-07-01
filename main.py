import sys
import os
import uuid
import json
import logging
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
from tool_registry import ToolRegistry

load_dotenv()
logger = logging.getLogger(__name__)
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

LITELLM_URL = "https://litellm.tfscreener.com/mcp/"
LITELLM_HEADERS = {
    "Authorization": f"Bearer {os.getenv('LITELLM_API_KEY')}",
}
LOCAL_PRIORITY = True
ATTACH_LIMIT_BYTES = 15 * 1024 * 1024
MAX_TURNS = 6  # hard cap on tool-call iterations per request

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


def _extract_chart(text: str) -> dict:
    """Split CHART_DATA:: marker from text and brace-count-parse the JSON payload."""
    if "CHART_DATA::" not in text:
        return {"text": text, "chart_data": None}
    parts = text.split("CHART_DATA::")
    text_part = parts[0].replace("Render this chart in the UI:", "").strip()
    raw = parts[1].strip() if len(parts) > 1 else ""
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
    if json_end > 0:
        try:
            chart_part = json.loads(raw[:json_end])
            if not text_part:
                text_part = f"📊 {chart_part.get('title', 'Chart')}"
            return {"text": text_part, "chart_data": chart_part}
        except json.JSONDecodeError:
            pass
    return {
        "text": text_part or text.replace("CHART_DATA::", "").strip(),
        "chart_data": None,
    }


async def run_haiku(messages: list, registry: ToolRegistry, mode: str = "auto") -> dict:
    """Claude Haiku agentic loop with local + optional LiteLLM tools via ToolRegistry."""
    async with AsyncExitStack() as stack:
        litellm_registry: ToolRegistry | None = None
        litellm_tools_raw: list = []

        async def _open_litellm(s: AsyncExitStack) -> ToolRegistry:
            r, w, _ = await s.enter_async_context(
                streamablehttp_client(LITELLM_URL, headers=LITELLM_HEADERS)
            )
            ls = await s.enter_async_context(ClientSession(r, w))
            await ls.initialize()
            return ToolRegistry(ls)

        _litellm_stack = AsyncExitStack()
        try:
            lr = await asyncio.wait_for(_open_litellm(_litellm_stack), timeout=5.0)
            await stack.enter_async_context(_litellm_stack)
            litellm_registry = lr
            litellm_tools_raw = await litellm_registry.get_tools("anthropic")
        except Exception as e:
            await _litellm_stack.aclose()
            print(
                f"Warning: LiteLLM unavailable ({type(e).__name__}), using local tools only."
            )

        local_tools_raw = await registry.get_tools("anthropic")

        # tool_name → ToolRegistry (local wins on name collision)
        tool_routing: dict[str, ToolRegistry] = {}
        for t in litellm_tools_raw:
            tool_routing[t["name"]] = litellm_registry  # type: ignore[assignment]
        if LOCAL_PRIORITY:
            for t in local_tools_raw:
                tool_routing[t["name"]] = registry

        # Deduplicate tool list sent to Claude (local wins)
        seen: set[str] = set()
        all_tools: list = []
        for t in local_tools_raw + litellm_tools_raw:
            if t["name"] not in seen:
                seen.add(t["name"])
                all_tools.append(t)

        if mode == "auto":
            active_tools = all_tools
            tool_choice: dict = {"type": "auto"}
        else:
            active_tools = [t for t in all_tools if t["name"] == mode]
            if not active_tools:
                active_tools = all_tools
                tool_choice = {"type": "auto"}
            else:
                tool_choice = {"type": "tool", "name": mode}

        for _turn in range(MAX_TURNS):
            response = await anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=5000,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=active_tools,
                tool_choice=tool_choice,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                final = "".join(b.text for b in response.content if b.type == "text")
                return _extract_chart(final)

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    r = tool_routing.get(block.name, registry)
                    try:
                        result_text = await r.execute(block.name, block.input)
                    except RuntimeError as e:
                        result_text = str(e)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": [{"type": "text", "text": result_text}],
                        }
                    )

            if not tool_results:
                salvage = "".join(b.text for b in response.content if b.type == "text")
                return {"text": salvage or "No response generated.", "chart_data": None}

            messages.append({"role": "user", "content": tool_results})
            tool_choice = {"type": "auto"}

    return {
        "text": "Reached reasoning limit — please rephrase or break the question into smaller parts.",
        "chart_data": None,
    }


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"


async def run_gemini_agent(message: str, registry: ToolRegistry) -> dict:
    """Gemini tool-calling loop using ToolRegistry for tool dispatch."""
    if not GOOGLE_API_KEY:
        return {
            "text": "Gemini unavailable — set GOOGLE_API_KEY in .env.",
            "chart_data": None,
        }
    tools = await registry.get_tools("gemini")
    messages = [{"role": "user", "parts": [{"text": message}]}]
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for _turn in range(MAX_TURNS):
                payload: dict = {"contents": messages}
                if tools:
                    payload["tools"] = tools
                resp = await client.post(
                    GEMINI_URL,
                    params={"key": GOOGLE_API_KEY},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                candidate = data.get("candidates", [{}])[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [{}])
                # Append model turn before executing tools (correct loop ordering)
                messages.append({"role": "model", "parts": parts})
                function_calls = [p for p in parts if "functionCall" in p]
                if not function_calls:
                    text = next((p.get("text") for p in parts if "text" in p), None)
                    return _extract_chart(text or "Gemini returned an empty response.")
                tool_results = []
                for fc_part in function_calls:
                    fc = fc_part["functionCall"]
                    name = fc["name"]
                    args = fc.get("args", {})
                    try:
                        result = await registry.execute(name, args)
                    except RuntimeError as e:
                        result = str(e)
                    tool_results.append(
                        {
                            "functionResponse": {
                                "name": name,
                                "response": {"output": result},
                            }
                        }
                    )
                messages.append({"role": "user", "parts": tool_results})
    except httpx.HTTPStatusError as e:
        return {
            "text": f"Gemini API error ({e.response.status_code}): {e.response.text}",
            "chart_data": None,
        }
    except httpx.TimeoutException:
        return {"text": "Gemini request timed out — try again.", "chart_data": None}
    except Exception as e:
        return {"text": f"Gemini error ({type(e).__name__}): {e}", "chart_data": None}
    return {
        "text": "Reached reasoning limit — please rephrase or break the question into smaller parts.",
        "chart_data": None,
    }


QWEN_SYSTEM = (
    "For Indian (NSE) stocks always use the .NS suffix: CDSL.NS, TCS.NS, RELIANCE.NS, INFY.NS, etc. "
    "When any tool returns a result containing 'CHART_DATA::', copy that entire string "
    "verbatim into your response — do not rephrase or replace it with your own data. "
    "If a chart tool call fails, report the error; never fabricate chart values."
)


async def run_qwen_agent(message: str, registry: ToolRegistry) -> dict:
    """Qwen/Ollama tool-calling loop using ToolRegistry for tool dispatch."""
    tools = await registry.get_tools("openai")
    messages: list = [
        {"role": "system", "content": QWEN_SYSTEM},
        {"role": "user", "content": message},
    ]
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            for _turn in range(MAX_TURNS):
                payload: dict = {
                    "model": "qwen3.5:4b",
                    "messages": messages,
                    "think": False,
                    "stream": False,
                    "options": {"num_ctx": 4096},
                }
                if tools:
                    payload["tools"] = tools
                resp = await client.post(
                    "http://localhost:11434/api/chat", json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                msg = data.get("message", {})
                tool_calls = msg.get("tool_calls") or []
                # Append assistant turn before executing tools (correct loop ordering)
                assistant_msg: dict = {
                    "role": "assistant",
                    "content": msg.get("content") or "",
                }
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                messages.append(assistant_msg)
                if not tool_calls:
                    return _extract_chart(
                        msg.get("content") or "Ollama returned an empty response."
                    )
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            logger.warning(
                                "run_qwen_agent: failed to parse tool arguments as JSON "
                                "(tool=%r, raw=%r) — falling back to empty dict",
                                name,
                                args,
                            )
                            args = {}
                    try:
                        result = await registry.execute(name, args)
                    except RuntimeError as e:
                        result = str(e)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.get("id", name),
                            "content": result,
                        }
                    )
    except httpx.ConnectError:
        return {
            "text": "Local model offline — start `ollama serve`.",
            "chart_data": None,
        }
    except httpx.TimeoutException:
        return {
            "text": "Ollama request timed out — the model may still be loading, try again.",
            "chart_data": None,
        }
    except Exception as e:
        return {"text": f"Ollama error ({type(e).__name__}): {e}", "chart_data": None}
    return {
        "text": "Reached reasoning limit — please rephrase or break the question into smaller parts.",
        "chart_data": None,
    }


@app.get("/")
async def index():
    return FileResponse("index.html")


@app.get("/style.css")
async def styles():
    return FileResponse("style.css")


@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    if req.attachments:
        total = sum(len(a.data_base64) * 3 // 4 for a in req.attachments)
        if total > ATTACH_LIMIT_BYTES:
            raise HTTPException(
                status_code=413, detail="Attachments exceed 15 MB limit"
            )

    content: list = []
    if req.message:
        content.append({"type": "text", "text": req.message})
    for a in req.attachments or []:
        if a.media_type == "application/pdf":
            content.append(
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": a.data_base64,
                    },
                }
            )
        elif a.media_type.startswith("image/"):
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": a.media_type,
                        "data": a.data_base64,
                    },
                }
            )
        elif a.media_type in ("text/plain", "text/markdown"):
            text = base64.b64decode(a.data_base64).decode("utf-8", errors="replace")[
                :4000
            ]
            content.append({"type": "text", "text": f"[{a.filename}]\n{text}"})
    if not content:
        content = [{"type": "text", "text": ""}]

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            registry = ToolRegistry(session)

            if req.model == "qwen-3.5":
                result = await run_qwen_agent(req.message, registry)
            elif req.model == "gemini":
                result = await run_gemini_agent(req.message, registry)
            else:
                history = session_store.get(session_id)
                history.append({"role": "user", "content": content})
                result = await run_haiku(history, registry, req.mode)
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


class LyricsRequest(BaseModel):
    mood: str
    theme: str = ""
    anchor: str = ""


async def run_lyrics(mood: str, theme: str = "", anchor: str = "") -> str:
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            res = await session.read_resource("lyrics://standards")
            standards = res.contents[0].text

            args = {"mood": mood}
            if theme:
                args["theme"] = theme
            if anchor:
                args["anchor"] = anchor
            pr = await session.get_prompt("lyrics_brief", arguments=args)
            brief = pr.messages[0].content.text

            response = await anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=5000,
                system=standards,
                messages=[{"role": "user", "content": brief}],
            )
            return "".join(b.text for b in response.content if b.type == "text")


@app.post("/api/lyrics")
async def lyrics(req: LyricsRequest):
    text = await run_lyrics(req.mood, req.theme, req.anchor)
    return {"lyrics": text}
