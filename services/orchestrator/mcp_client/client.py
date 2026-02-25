"""MCP client for consuming OneStream MCP server tools."""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class MCPToolCall:
    server: str
    tool: str
    arguments: dict
    result: dict | None = None
    error: str | None = None


@dataclass
class MCPServerConfig:
    name: str
    transport: str = "stdio"  # "stdio" or "http+sse"
    command: str = ""  # For stdio transport
    url: str = ""  # For HTTP+SSE transport
    env: dict[str, str] = field(default_factory=dict)


class MCPClient:
    """Client for invoking tools on MCP servers.

    Supports both stdio (for CLI tools like Claude Code) and HTTP+SSE
    (for the web IDE) transports.
    """

    def __init__(self) -> None:
        self.servers: dict[str, MCPServerConfig] = {}
        self.call_history: list[MCPToolCall] = []

    def register_server(self, config: MCPServerConfig) -> None:
        """Register an MCP server configuration."""
        self.servers[config.name] = config
        logger.info("mcp_client.server_registered", server=config.name, transport=config.transport)

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict,
    ) -> dict:
        """Call a tool on a registered MCP server.

        In production, this would:
        - For stdio: spawn subprocess with MCP SDK, send JSON-RPC request
        - For HTTP+SSE: POST to server endpoint, stream response via SSE
        """
        server = self.servers.get(server_name)
        if not server:
            error = f"MCP server '{server_name}' not registered"
            logger.error("mcp_client.server_not_found", server=server_name)
            call = MCPToolCall(
                server=server_name,
                tool=tool_name,
                arguments=arguments,
                error=error,
            )
            self.call_history.append(call)
            return {"error": error}

        logger.info(
            "mcp_client.call_tool",
            server=server_name,
            tool=tool_name,
        )

        # Placeholder — in production this dispatches via MCP SDK
        result = {
            "status": "not_connected",
            "server": server_name,
            "tool": tool_name,
            "message": "MCP server call would be dispatched here via SDK",
        }

        call = MCPToolCall(
            server=server_name,
            tool=tool_name,
            arguments=arguments,
            result=result,
        )
        self.call_history.append(call)

        return result

    async def list_tools(self, server_name: str) -> list[dict]:
        """List available tools on a registered MCP server."""
        server = self.servers.get(server_name)
        if not server:
            return []

        # In production, this would send tools/list JSON-RPC request
        return [{"status": "not_connected", "server": server_name}]

    def get_call_history(self, server_name: str | None = None) -> list[MCPToolCall]:
        """Return call history, optionally filtered by server."""
        if server_name:
            return [c for c in self.call_history if c.server == server_name]
        return list(self.call_history)
