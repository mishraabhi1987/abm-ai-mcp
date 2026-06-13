import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command=sys.executable,
    args=["server.py"],
    env=None
)

async def main():
    # 1. Server process launch + connection खोलना
    async with stdio_client(server_params) as (read, write):
        # 2. उस connection पर session बनाना
        async with ClientSession(read, write) as session:
            # 3. Handshake
            await session.initialize()
            print("✅ Connected to server")

            # 4. Tools की list माँगना
            tools_response = await session.list_tools()
            print("\n🛠 Available tools:")
            for tool in tools_response.tools:
                print(f"  - {tool.name}: {tool.description}")

asyncio.run(main())