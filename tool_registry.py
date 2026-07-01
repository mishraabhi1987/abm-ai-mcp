import logging

from mcp import ClientSession

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Thin wrapper around an MCP ClientSession.

    Session lifecycle is owned by the caller (AsyncExitStack).
    Instantiate once per request after the session is initialized.
    """

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def get_tools(self, format: str) -> list:
        """Return the tool list shaped for the target provider.

        format: "anthropic" | "gemini" | "openai"
        Raises ValueError for unknown formats.
        """
        resp = await self._session.list_tools()
        tools = resp.tools
        if format == "anthropic":
            return self._to_anthropic(tools)
        if format == "gemini":
            return self._to_gemini(tools)
        if format == "openai":
            return self._to_openai(tools)
        raise ValueError(f"Unknown tool format: {format!r}")

    async def execute(self, name: str, arguments: dict) -> str:
        """Call a tool via MCP and return a normalized text result.

        Raises RuntimeError if the tool signals isError=True so callers
        can handle failures explicitly instead of receiving corrupt output.
        """
        result = await self._session.call_tool(name, arguments)
        if getattr(result, "isError", False):
            error_text = self._normalize(result)
            raise RuntimeError(f"Tool '{name}' returned an error: {error_text}")
        return self._normalize(result)

    # ── Format adapters ───────────────────────────────────────────────────────
    # Each adapter translates MCP tool definitions to the provider's schema.
    # Adding a new provider = add one adapter method + one branch in get_tools.

    def _to_anthropic(self, tools) -> list:
        # raw anthropic package (AsyncAnthropic) — NOT claude_agent_sdk
        return [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema or {},
            }
            for t in tools
        ]

    def _to_gemini(self, tools) -> list:
        if not tools:
            return []
        # All declarations go inside a single functionDeclarations envelope.
        return [
            {
                "functionDeclarations": [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema or {},
                    }
                    for t in tools
                ]
            }
        ]

    def _to_openai(self, tools) -> list:
        # OpenAI-compatible format used by Ollama / Qwen.
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema or {},
                },
            }
            for t in tools
        ]

    # ── Result normalization ──────────────────────────────────────────────────

    def _normalize(self, result) -> str:
        """Concatenate all TextContent items from a CallToolResult.

        Non-text blocks are logged and skipped — never repr'd, because str(item)
        produces Python object syntax that silently corrupts any json.loads caller.
        """
        if not result or not getattr(result, "content", None):
            return ""
        parts = []
        for item in result.content:
            if getattr(item, "type", None) == "text":
                parts.append(item.text)
            else:
                logger.warning(
                    "ToolRegistry._normalize: skipping non-text content block "
                    "(type=%r) — only TextContent is handled",
                    getattr(item, "type", "unknown"),
                )
        return "\n".join(parts)
