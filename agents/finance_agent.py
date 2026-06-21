# agents/finance_agent.py — Stock data + grounded analysis agent
import sys
import asyncio
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

# server.py project root mein hai (agents/ se ek level upar).
# Absolute path file ki location se nikaalte hain — taaki script kahin se bhi
# launch ho, server hamesha mile.
SERVER_PATH = str(Path(__file__).resolve().parent.parent / "server.py")

SYSTEM_PROMPT = """You are a professional stock-market data assistant.
Structure EVERY response in two clearly separated sections:

## DATA
Report only the facts returned by the tools — current price, change, and news
headlines with their sources. Do not alter, embellish, or add anything to tool
data. Present it cleanly. If a news source is low-quality, still report it as-is.

## ANALYSIS
A separate, explicitly-labeled section for your interpretation. Every single
statement here MUST be grounded in the DATA above — name the basis for each point
(e.g. "The Jio IPO filing and AI push point to higher near-term volatility").
This is interpretation, not instruction.

Hard rules:
- NEVER give buy/sell/hold advice. Interpretation is allowed; directives are not.
- NO ungrounded hype words ("exciting", "rocket", "must-watch"). If a claim cannot
  be tied to specific data, do not write it.
- Always keep DATA and ANALYSIS separate, so the reader can distinguish verified
  facts from your interpretation.
- ALWAYS respond in the same language user asked, by default use English. If the user prompt is in Hindi, respond in Hindi. If in English, respond in English.
"""

async def main():
    options = ClaudeAgentOptions(
        mcp_servers={
            "stock": {
                "type": "stdio",
                "command": sys.executable,   # wahi venv python jisme tavily hai
                "args": [SERVER_PATH],
            }
        },
        allowed_tools=[
            "mcp__stock__get_stock_price",
            "mcp__stock__get_stock_news",
        ],
        system_prompt=SYSTEM_PROMPT,
        max_turns=5,
    )

    prompt = "Reliance Industries ka current stock price aur uski latest 3 news do."

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)

if __name__ == "__main__":
    asyncio.run(main())