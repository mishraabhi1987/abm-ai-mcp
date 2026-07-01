import os
import json
import logging
import requests
import numexpr
from urllib.parse import urlparse
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
from bs4 import BeautifulSoup
import yfinance as yf

load_dotenv()
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# MCP server banaya — naam diya "Demo"
mcp = FastMCP("ABM AI")

# ============================================================
# RESOURCES
# ============================================================


@mcp.resource("resource://abm/info")
def get_server_info() -> str:
    """Basic identity and description of ABM AI server."""
    return json.dumps(
        {
            "name": "ABM AI",
            "version": "1.0.0",
            "description": "AI-powered assistant with tools for weather, stocks, news, charts and web search.",
            "author": "Abhishek",
            "transport": "Streamable HTTP",
        },
        indent=2,
    )


@mcp.resource("resource://abm/tools")
def get_tools_list() -> str:
    """List of all available tools in ABM AI and what they do."""
    return json.dumps(
        {
            "tools": [
                {
                    "name": "calculate",
                    "description": "Solves mathematical expressions",
                    "example": "4 + 5 * 2",
                },
                {
                    "name": "fetch_url",
                    "description": "Fetches and explains content from any URL",
                    "example": "https://example.com",
                },
                {
                    "name": "web_search",
                    "description": "Searches the web using Tavily",
                    "example": "Latest AI news 2026",
                },
                {
                    "name": "get_stock_price",
                    "description": "Returns live price for NSE/US stocks",
                    "example": "RELIANCE.NS",
                },
                {
                    "name": "get_weather",
                    "description": "Returns current weather for any city",
                    "example": "Noida",
                },
                {
                    "name": "get_chart_data",
                    "description": "Generates bar, line, or pie chart data",
                    "example": "bar chart of stock prices",
                },
                {
                    "name": "get_historical_chart",
                    "description": "Returns historical price trend chart for a stock",
                    "example": "RELIANCE.NS 1mo",
                },
            ]
        },
        indent=2,
    )


@mcp.resource("resource://abm/status")
def get_server_status() -> str:
    """Current status and runtime info of ABM AI server."""
    from datetime import datetime

    return json.dumps(
        {
            "status": "online",
            "server": "ABM AI v1.0.0",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tools_count": 7,
            "resources_count": 3,
            "message": "All systems operational",
        },
        indent=2,
    )


# @mcp.tool() decorator is function ko ek "tool" bana deta hai
# jise client call kar sakta hai


# MCP tool for calculating mathematical expressions safely using numexpr
@mcp.tool()
def calculate(expression: str) -> str:
    """Solve a mathematical expression. Supports +, -, *, /, **, parentheses.
    Examples: '4 + 5 * 2', '(10 - 3) ** 2', '100 / 4', '2 ** 8'."""
    try:
        result = numexpr.evaluate(expression).item()
        return f"{expression} = {result}"
    except Exception:
        return (
            f"Could not calculate '{expression}'. Use numbers and + - * / ** ( ) only."
        )


# MCP tool to fetch and explain content of a URL (like news article, blog post, etc.)
@mcp.tool()
def fetch_url(url: str) -> str:
    """Fetch the content of a web page or URL so it can be explained or summarized.
    Use this when the user shares a link and wants to know what it is about."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        # remove script/style noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        # limit to avoid huge payloads (first ~3000 chars is enough to explain)
        text = text[:3000]

        title = soup.title.string if soup.title else "No title"
        return f"Title: {title}\n\nContent:\n{text}"
    except Exception as e:
        return f"Could not fetch '{url}'. Error: {str(e)}"


# MCP Tool for web search using Tavily
@mcp.tool()
def web_search(query: str) -> str:
    response = tavily_client.search(query, max_results=5)
    # Results ko clean text me convert karo (model ke liye)
    results = []
    for r in response.get("results", []):
        results.append(f"{r['title']}: {r['content']}")
    return "\n\n".join(results) if results else "No result found."


# ============================================================
# STRUCTURED HELPERS — used by agent_server.py directly.
# The MCP tools below wrap these and return the same strings
# they always did, so Chat Bot / Artifacts are unaffected.
# ============================================================


def _price_not_found(symbol: str) -> str:
    has_suffix = any(symbol.upper().endswith(s) for s in (".NS", ".BO", ".US"))
    if has_suffix:
        return f"Symbol '{symbol}' not found. Check the spelling — e.g. RELIANCE.NS, TCS.NS."
    return f"Symbol '{symbol}' not found. For NSE stocks add .NS (e.g. RELIANCE.NS)."


def fetch_stock_price(symbol: str) -> dict:
    """Return structured price data for a symbol, or {"error": "..."} on failure."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.last_price
        prev_close = info.previous_close
        if price is None:
            return {"error": _price_not_found(symbol)}
        change = price - (prev_close or 0)
        change_pct = (change / prev_close * 100) if prev_close else 0
        return {
            "symbol": symbol,
            "current": round(price, 2),
            "prev_close": round(prev_close, 2) if prev_close is not None else None,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "currency": info.currency or "",
        }
    except Exception as e:
        logging.warning("fetch_stock_price failed for '%s': %s", symbol, e)
        return {"error": _price_not_found(symbol)}


def fetch_stock_news(company: str, max_results: int = 5) -> list:
    """Return structured news list for a company, or [] on any failure."""
    try:
        res = tavily_client.search(
            query=f"{company} stock latest news",
            topic="news",
            days=7,
            max_results=max_results,
            include_domains=[
                "reuters.com",
                "livemint.com",
                "economictimes.indiatimes.com",
                "moneycontrol.com",
                "thehindu.com",
            ],
        )
    except Exception as e:
        logging.warning("fetch_stock_news failed for '%s': %s", company, e)
        return []
    items = []
    for r in res.get("results", []):
        url = r.get("url", "")
        try:
            source = urlparse(url).netloc.replace("www.", "")
        except Exception:
            source = ""
        items.append(
            {
                "title": r.get("title", ""),
                "url": url,
                "source": source,
                "date": r.get("published_date", "") or "",
                "summary": (r.get("content") or "")[:200],
            }
        )
    return items


# Structured data tools — return JSON strings for orchestrator / registry use.
# These are distinct from get_stock_price / get_stock_news which return
# human-readable strings for the Chat Bot. Callers must json.loads the result.


@mcp.tool()
def get_stock_price_data(symbol: str) -> str:
    """Return stock price as a JSON string for structured / orchestrator use.
    For Indian (NSE) stocks add .NS suffix (e.g. CDSL.NS, RELIANCE.NS, TCS.NS).
    For US stocks use the ticker directly (e.g. AAPL, TSLA).
    Shape on success: {"symbol","current","prev_close","change","change_pct","currency"}.
    Shape on failure: {"error": "<message>"}.
    For human-readable price output in chat, use get_stock_price instead."""
    return json.dumps(fetch_stock_price(symbol))


@mcp.tool()
def get_stock_news_data(company: str, max_results: int = 5) -> str:
    """Return stock news as a JSON array string for structured / orchestrator use.
    Each item: {"title","url","source","date","summary"}.
    For human-readable news output in chat, use get_stock_news instead."""
    return json.dumps(fetch_stock_news(company, max_results))


# Stock price MCP tool
@mcp.tool()
def get_stock_price(symbol: str) -> str:
    """Get the current price, change %, and basic info for a stock.
    For Indian (NSE) stocks, add .NS after the symbol (e.g. RELIANCE.NS, TCS.NS).
    For US stocks, use the symbol directly (e.g. AAPL, TSLA). Use this for live stock/share prices.
    """
    data = fetch_stock_price(symbol)
    if "error" in data:
        return data["error"]
    return (
        f"{data['symbol']}\n"
        f"Price: {data['current']:.2f} {data['currency']}\n"
        f"Previous Close: {data['prev_close']:.2f}\n"
        f"Change: {data['change']:+.2f} ({data['change_pct']:+.2f}%)"
    )


@mcp.tool()
def get_stock_news(company: str, max_results: int = 5) -> str:
    """Kisi company/stock ki latest news laata hai (Tavily news search).

    Args:
        company: Company ya stock ka naam (jaise 'Reliance Industries', 'CDSL')
        max_results: Kitni news items chahiye (default 5)
    """
    items = fetch_stock_news(company, max_results)
    if not items:
        return f"'{company}' ke liye koi recent news nahi mili."
    lines = []
    for i, r in enumerate(items, 1):
        lines.append(f"{i}. {r['title']}\n   {r['url']}\n   {r['summary']}")
    return "\n\n".join(lines)


# MCP tool for getting current weather of a city using Open-Meteo API
@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city (temperature, wind, conditions).
    Works for any city worldwide, e.g. 'Noida', 'London', 'Tokyo'.
    Use this for live/current weather queries."""

    # Step 1: convert city name to coordinates (geocoding)
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_resp = requests.get(geo_url, params={"name": city, "count": 1}).json()

    if not geo_resp.get("results"):
        return f"Could not find location '{city}'. Check the spelling."

    loc = geo_resp["results"][0]
    lat, lon = loc["latitude"], loc["longitude"]
    name = loc.get("name", city)
    country = loc.get("country", "")

    # Step 2: get current weather for those coordinates
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_resp = requests.get(
        weather_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        },
    ).json()

    cur = weather_resp.get("current", {})
    temp = cur.get("temperature_2m")
    humidity = cur.get("relative_humidity_2m")
    wind = cur.get("wind_speed_10m")

    if temp is None:
        return f"Could not get weather data for {name}."

    return (
        f"Weather in {name}, {country}:\n"
        f"Temperature: {temp}°C\n"
        f"Humidity: {humidity}%\n"
        f"Wind Speed: {wind} km/h"
    )


# MCP tool to generate chart data for visualization
@mcp.tool()
def get_chart_data(
    chart_type: str, labels: list[str], values: list[float], title: str = ""
) -> str:
    """Generate chart data for visual graphs and charts.
    Use this when user wants to see a bar chart, line chart, or pie chart.
    chart_type: 'bar', 'line', or 'pie'
    labels: list of category names (e.g. ['RELIANCE', 'TCS', 'INFY'])
    values: list of numbers matching each label (e.g. [1450.5, 3200.0, 1800.75])
    title: optional chart heading"""
    import json

    chart = {"type": chart_type, "labels": labels, "values": values, "title": title}
    return f"Render this chart in the UI: CHART_DATA::{json.dumps(chart)}"


# Yeh function MCP response ko parse karega aur agar CHART_DATA mile to usko alag kareg
@mcp.tool()
def get_historical_chart(symbol: str, period: str = "1wk") -> str:
    """Get historical price chart data for a stock.
    symbol: NSE stock add .NS (e.g. RELIANCE.NS), US stocks direct (e.g. AAPL)
    period: '1wk', '1mo', '3mo', '1y'
    Use this when user asks for historical chart, past performance, or price trend."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)

    if hist.empty:
        return f"No historical data found for '{symbol}'."

    labels = [str(d.date()) for d in hist.index]
    values = [round(float(p), 2) for p in hist["Close"]]

    chart = {
        "type": "line",
        "labels": labels,
        "values": values,
        "title": f"{symbol} - {period} Price Trend",
    }
    return f"Render this chart in the UI: CHART_DATA::{json.dumps(chart)}"


# ============================================================
#  LYRICS GENERATION — Feature 1 (generic, not brand-specific)
#  Add this to server.py. NO tool — just these 2 primitives:
#    1. Resource: lyrics://standards  (App-controlled, songwriting craft)
#    2. Prompt:   lyrics_brief         (User-controlled, steers each song)
#  Writing the lyrics is the model's job — not a tool's.
# ============================================================


# ---- RESOURCE: songwriting craft standards (App-controlled) ----
# The heavy, reusable craft rules live here once. The client loads this into context.
@mcp.resource("lyrics://standards")
def lyrics_standards() -> str:
    """Generic craft standards for writing great, original, singable lyrics."""
    return (
        "SONGWRITING STANDARDS (IntelliFrame Media Premium)\n"
        "\n"
        "CORE PRINCIPLE:\n"
        "Great lyrics take a universal feeling and tell it through ONE specific, fresh lens.\n"
        "Be concrete and surprising, not generic. Pick images that carry the emotion, not images that are just exact.\n"
        "\n"
        "LENGTH & OUTPUT (ONE-SHOT FINAL):\n"
        "- 4-5 minutes of singable lyrics (a full song, not a fragment).\n"
        "- ONE final, proofread block — ready to copy-paste.\n"
        "- Deliver lyrics 100% correct in the first draft. No alternate versions. Avoid altering or correcting after generation unless explicitly requested. Preserve the workflow flow.\n"
        "\n"
        "STRUCTURE (Hybrid Fast Chorus Entry Format v2.6 - DEFAULT):\n"
        "- Fast Entry is mandatory. Hit the Pre-Chorus and Chorus quickly to hook the listener.\n"
        "- Sections: Intro / Verse 1 / Pre-Chorus / Chorus (Hook) / Verse 2 / Bridge / Hook Callback / Outro.\n"
        "- Pre-Chorus: Flexible length (5–8 sec for Party/Swag; 10–15 sec for Romantic).\n"
        "- Bridge: Optional for Party songs; MANDATORY for Romantic songs.\n"
        "- Hook Callback: A 5–8 sec repetition of the core hook immediately after the Bridge.\n"
        "- Outro: Shorter and precise (8–12 sec maximum, fade/cut based on genre).\n"
        "\n"
        "HOOK CRAFT (Viral Potential):\n"
        "- Build ONE short, highly repeatable signature phrase or refrain, easy to chant and remember.\n"
        "- Repetition is intentional but vary it slightly (build-up, answer-back, drop) so it never feels flat.\n"
        "\n"
        "WRITING CRAFT & BENCHMARKS:\n"
        "- Romantic/Ghazal benchmark: 'Tuu Meri Dhun' style. Must be 'chumeswari'—soulful, simple, relatable, repeatable hooks, and deeply heart-touching.\n"
        "- SHOW, don't tell. Convey emotion through scene, action, and detail.\n"
        "- Keep a consistent point of view (who is singing, to whom). Make 'I' and 'you' real.\n"
        "- Match the language register to the genre. Avoid unnatural English loanwords in Hindi romantic songs unless the genre specifically demands an urban bilingual flow.\n"
        "\n"
        "SOUND & PROSODY:\n"
        "- Keep meter consistent between parallel lines.\n"
        "- Match stress to the beat — stressed syllables land on strong beats.\n"
        "- Meaning leads; rhyme serves it. NEVER force meaning to fit a rhyme.\n"
        "\n"
        "CONTENT (STRICT QUALITY GATE):\n"
        "- Strictly ZERO vulgar, cheap, or adult words. Content must remain 100% clean, high-quality, and highly appropriate.\n"
        "- Must signal IntelliFrame Media trust and premium quality at first glance.\n"
        "\n"
        "STYLE Tag:\n"
        "- Provide the exact style tag of these lyrics along with the final output.\n"
    )


# ---- PROMPT: lyrics brief (User-controlled) ----
# Stays small but steerable. The heavy craft comes from the resource.
# Optional args sharpen specificity — 'anchor' is the strongest uniqueness lever.
@mcp.prompt(title="Lyrics Brief")
def lyrics_brief(
    mood: str, theme: str = "", language: str = "", anchor: str = ""
) -> str:
    """Build an instruction to generate lyrics for a given mood/genre."""
    lines = [f"Write original song lyrics. Mood / genre: {mood}."]
    if theme:
        lines.append(f"Theme / situation: {theme}.")
    if language:
        lines.append(f"Primary language: {language}.")
    if anchor:
        lines.append(
            f"Build the whole song around this concrete image/detail: {anchor}."
        )
    lines.append(
        "Follow the songwriting standards provided in context "
        "(structure, hook craft, writing craft, prosody, and the quality gate)."
    )
    lines.append("Deliver ONE final, polished block — ready to copy-paste.")
    return "\n".join(lines)


# Server ko run karo
if __name__ == "__main__":
    mcp.run()
