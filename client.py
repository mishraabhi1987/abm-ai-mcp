import asyncio
import sys
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
load_dotenv()

anthropic = Anthropic()   # API key environment से उठा लेगा

server_params = StdioServerParameters(
    command=sys.executable,
    args=["server.py"],
    env=None
)

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # MCP format → Anthropic format
            tools_response = await session.list_tools()
            available_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in tools_response.tools
            ]

            # User का सवाल
            messages = [
                {"role": "user", "content": "58 aur 7 ko jodo"}
            ]

            # ===== Agentic loop =====
            while True:
                response = anthropic.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )

                # Claude का पूरा response messages में add करो
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # अगर Claude ने tool नहीं माँगा → वो final जवाब दे चुका, loop तोड़ो
                if response.stop_reason != "tool_use":
                    # text block ढूँढकर print करो
                    for block in response.content:
                        if block.type == "text":
                            print(f"\n💬 Claude: {block.text}")
                    break

                # Claude ने tool माँगा → हर tool_use block process करो
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"\n🛠 Claude wants: {block.name}({block.input})")

                        # MCP server पर असली tool चलाओ
                        result = await session.call_tool(block.name, block.input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result.content
                        })

                # सारे results एक साथ user message की तरह वापस भेजो
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

asyncio.run(main())