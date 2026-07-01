# Run with: uvicorn agent_server:app --reload --port 8001
import os
import re
import sys
import json
import logging
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import AsyncAnthropic  # raw anthropic package — not claude_agent_sdk
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tool_registry import ToolRegistry

load_dotenv()

_anthropic = AsyncAnthropic(timeout=30.0)

server_params = StdioServerParameters(
    command=sys.executable,
    args=["server.py"],
    env=os.environ,
)

ANALYSIS_SYSTEM = (
    "You are a professional stock-market analyst. "
    "You receive verified price data and recent news for a stock. "
    "Your job is to interpret only — do NOT restate raw numbers or headlines. "
    "Every statement must be grounded in the provided data; name the specific point it rests on. "
    "Hard rules: never give buy/sell/hold advice; no ungrounded hype words "
    '("exciting", "rocket", "must-watch"); respond in plain markdown; '
    "respond in the same language the user wrote their query in."
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve(query: str):
    """Return (price_symbol, news_company) from a free-form query.

    Heuristic: if the query already has an exchange suffix (.NS/.BO/.US) it is
    used as-is; everything else gets the first word uppercased + .NS appended.
    Note: multi-word names use only the first word for the symbol
    (e.g. "Tata Consultancy" → TATA.NS); prefer the known ticker (TCS.NS).
    """
    q = query.strip()
    if re.search(r'\.(NS|BO|US)$', q, re.IGNORECASE):
        symbol = q.upper()
        company = re.sub(r'\.(NS|BO|US)$', '', symbol, flags=re.IGNORECASE)
    else:
        symbol = q.split()[0].upper() + '.NS'
        company = q
    return symbol, company


async def _analyse(price: dict, news: list, query: str) -> str:
    user_msg = (
        f"User query: {query}\n\n"
        f"Price data:\n{json.dumps(price, indent=2)}\n\n"
        f"News ({len(news)} items):\n{json.dumps(news, indent=2)}\n\n"
        "Provide grounded analysis. Do not restate price figures or headlines — only interpret."
    )
    msg = await _anthropic.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=ANALYSIS_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    return msg.content[0].text


class FinanceRequest(BaseModel):
    query: str


@app.post("/api/agent/finance")
async def finance_agent(req: FinanceRequest):
    symbol, company = _resolve(req.query)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            registry = ToolRegistry(session)

            # Fetch price via MCP — result is a JSON string.
            try:
                price_raw = await registry.execute("get_stock_price_data", {"symbol": symbol})
                price = json.loads(price_raw)
            except (RuntimeError, json.JSONDecodeError) as e:
                logging.warning("get_stock_price_data failed for '%s': %s", symbol, e)
                return {"price": {"error": str(e)}, "news": [], "analysis": "", "query": req.query}

            if "error" in price:
                return {"price": price, "news": [], "analysis": "", "query": req.query}

            # Fetch news via MCP — result is a JSON array string.
            try:
                news_raw = await registry.execute("get_stock_news_data", {"company": company, "max_results": 5})
                news = json.loads(news_raw)
            except (RuntimeError, json.JSONDecodeError) as e:
                logging.warning("get_stock_news_data failed for '%s': %s", company, e)
                news = []

    try:
        analysis = await asyncio.wait_for(_analyse(price, news, req.query), timeout=30.0)
    except asyncio.TimeoutError:
        logging.warning("Analysis call timed out for query: %s", req.query)
        analysis = ""
    return {"price": price, "news": news, "analysis": analysis, "query": req.query}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
