import sys
import os
import uuid
import json
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import stdio_client
from datetime import datetime
from zoneinfo import ZoneInfo


load_dotenv()
anthropic = Anthropic()
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

# --- Session-based conversation store (in-memory) ---
# Structure: { session_id: [list of messages] }
# Each session keeps its own separate history.
conversations = {}


class ChatRequest(BaseModel):
    message: str = ""
    mode: str = "auto"
    session_id: str | None = None   # frontend sends this to keep history


async def run_agent(messages: list, mode: str = "auto") -> dict:
    # Dono servers ek saath connect — nested context managers
    async with stdio_client(server_params) as (local_read, local_write):
        async with ClientSession(local_read, local_write) as local_session:
            async with streamablehttp_client(
                LITELLM_URL, headers=LITELLM_HEADERS
            ) as (litellm_read, litellm_write, _):
                async with ClientSession(litellm_read, litellm_write) as litellm_session:

                    # Dono sessions initialize
                    await local_session.initialize()
                    await litellm_session.initialize()

                    # --- LOCAL tools ---
                    local_tools_resp = await local_session.list_tools()
                    local_tool_names = {t.name for t in local_tools_resp.tools}
                    local_tools = [
                        {
                            "name": t.name,
                            "description": t.description,
                            "input_schema": t.inputSchema,
                        }
                        for t in local_tools_resp.tools
                    ]

                    # --- LITELLM tools ---
                    litellm_tools_resp = await litellm_session.list_tools()
                    litellm_tool_names = {t.name for t in litellm_tools_resp.tools}
                    litellm_tools = [
                        {
                            "name": t.name,
                            "description": t.description,
                            "input_schema": t.inputSchema,
                        }
                        for t in litellm_tools_resp.tools
                    ]

                    # --- MERGE dono ---
                    all_tools = local_tools + litellm_tools

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
                        response = anthropic.messages.create(
                            model="claude-haiku-4-5",
                            max_tokens=1000,
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
                                raw = parts[1].strip()
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
                                chart_part = json.loads(raw[:json_end])
                                if not text_part:
                                    text_part = f"📊 {chart_part.get('title', 'Chart')}"
                                return {"text": text_part, "chart_data": chart_part}

                            return {"text": final, "chart_data": None}

                        # --- TOOL EXECUTION with ROUTING ---
                        tool_results = []
                        for block in response.content:
                            if block.type == "tool_use":
                                # ROUTING: kaunse server ka tool hai?
                                if block.name in local_tool_names:
                                    result = await local_session.call_tool(block.name, block.input)
                                elif block.name in litellm_tool_names:
                                    result = await litellm_session.call_tool(block.name, block.input)
                                else:
                                    result = None

                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result.content if result else "Tool not found",
                                })
                        messages.append({"role": "user", "content": tool_results})

                        tool_choice = {"type": "auto"}


@app.get("/")
async def index():
    return FileResponse("index.html")


@app.get("/style.css")
async def styles():
    return FileResponse("style.css")


@app.post("/chat")
async def chat(req: ChatRequest):
    # 1. get or create a session id
    session_id = req.session_id or str(uuid.uuid4())

    # 2. get this session's history (or start empty)
    history = conversations.get(session_id, [])

    # 3. add the new user message
    history.append({"role": "user", "content": req.message})

    # 4. run the agent with the FULL history (so it remembers context)
    result = await run_agent(history, req.mode)

    # 5. save updated history back to this session
    conversations[session_id] = history

    # 6. return answer + chart_data + session_id
    return {
        "answer": result["text"],
        "chart_data": result["chart_data"],
        "session_id": session_id
    }


@app.post("/new")
async def new_chat(req: ChatRequest):
    # clear a session's history (New Chat button)
    if req.session_id and req.session_id in conversations:
        del conversations[req.session_id]
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
            response = anthropic.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1500,
                system=standards,
                messages=[{"role": "user", "content": brief}],
            )
            return "".join(b.text for b in response.content if b.type == "text")


@app.post("/api/lyrics")
async def lyrics(req: LyricsRequest):
    text = await run_lyrics(req.mood, req.theme, req.anchor)
    return {"lyrics": text}