import os
import json
import requests
import numexpr
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
from bs4 import BeautifulSoup
import yfinance as yf


load_dotenv()
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# MCP server banaya — naam diya "Demo"
mcp = FastMCP("Demo")


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
        return f"Could not calculate '{expression}'. Use numbers and + - * / ** ( ) only."

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

# Stock price MCP tool
@mcp.tool()
def get_stock_price(symbol: str) -> str:
    """Get the current price, change %, and basic info for a stock.
    For Indian (NSE) stocks, add .NS after the symbol (e.g. RELIANCE.NS, TCS.NS).
    For US stocks, use the symbol directly (e.g. AAPL, TSLA). Use this for live stock/share prices."""
    ticker = yf.Ticker(symbol)
    info = ticker.fast_info  # fast_info is faster and less rate-limited than .info

    price = info.get("lastPrice")
    prev_close = info.get("previousClose")

    if price is None:
        return f"No data found for '{symbol}'. Check the symbol (add .NS for NSE stocks)."

    change = price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0

    currency = info.get("currency", "")
    return (
        f"{symbol}\n"
        f"Price: {price:.2f} {currency}\n"
        f"Previous Close: {prev_close:.2f}\n"
        f"Change: {change:+.2f} ({change_pct:+.2f}%)"
    )


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
    weather_resp = requests.get(weather_url, params={
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
    }).json()

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
    chart_type: str,
    labels: list[str],
    values: list[float],
    title: str = ""
) -> str:
    """Generate chart data for visual graphs and charts.
    Use this when user wants to see a bar chart, line chart, or pie chart.
    chart_type: 'bar', 'line', or 'pie'
    labels: list of category names (e.g. ['RELIANCE', 'TCS', 'INFY'])
    values: list of numbers matching each label (e.g. [1450.5, 3200.0, 1800.75])
    title: optional chart heading"""
    import json
    chart = {
        "type": chart_type,
        "labels": labels,
        "values": values,
        "title": title
    }
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
        "type": "bar",
        "labels": labels,
        "values": values,
        "title": f"{symbol} - {period} Price Trend"
    }
    return f"Render this chart in the UI: CHART_DATA::{json.dumps(chart)}"

# Server ko run karo
if __name__ == "__main__":
    mcp.run()