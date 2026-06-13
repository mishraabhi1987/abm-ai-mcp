import sys
import uuid
import json
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
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
    env=None,
)

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


async def run_agent(messages: list, mode: str = "auto") -> str:
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            all_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in tools_response.tools
            ]

            # --- mode / tool_choice setup ---
            if mode == "auto":
                active_tools = all_tools
                tool_choice = {"type": "auto"}
            else:
                # only the selected tool
                active_tools = [t for t in all_tools if t["name"] == mode]
                if not active_tools:
                    # invalid mode -> safe fallback
                    active_tools = all_tools
                    tool_choice = {"type": "auto"}
                else:
                    tool_choice = {"type": "tool", "name": mode}

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
                       # "Render this chart in the UI:" text hata do
                        text_part = parts[0].replace("Render this chart in the UI:", "").strip()
                        # JSON sirf pehli line tak hai, baad ka text ignore karo
                        raw = parts[1].strip()
                        # pehla valid JSON object extract karo
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
                        # text empty hai to chart title fallback
                        if not text_part:
                            text_part = f"📊 {chart_part.get('title', 'Chart')}"
                        
                        return {"text": text_part, "chart_data": chart_part}

                    return {"text": final, "chart_data": None}

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await session.call_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result.content,
                        })
                messages.append({"role": "user", "content": tool_results})

                # IMPORTANT: after the first forced call, switch to AUTO
                # otherwise the model keeps calling the same tool in a loop
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