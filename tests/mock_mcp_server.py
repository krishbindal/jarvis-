"""Harmless MCP server for stdio lifecycle integration tests."""
from mcp.server.mcpserver import MCPServer

server = MCPServer("jarvis-test-echo")


@server.tool()
def echo(text: str) -> str:
    """Return the supplied text without modifying the system."""
    return text


if __name__ == "__main__":
    server.run(transport="stdio")
