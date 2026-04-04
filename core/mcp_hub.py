import asyncio
import json
import logging
import threading
from typing import Dict, List, Any, Optional
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from utils.logger import get_logger

logger = get_logger("jarvis.mcp")

class MCPHub:
    """
    Central manager for Model Context Protocol (MCP) servers.
    Bridges external specialized tools into JARVIS's command system.
    """
    def __init__(self, config_path: str = "config/mcp_servers.json"):
        self.config_path = config_path
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._sessions: Dict[str, ClientSession] = {}
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._tools = {}
        self._initialized = False

    def _run_event_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def start(self):
        """Initialize the hub and start the background event loop."""
        if not self._thread.is_alive():
            self._thread.start()
        
        if not self._initialized:
            logger.info("[MCP] Starting Hub initialization...")
            future = asyncio.run_coroutine_threadsafe(self._init_servers(), self._loop)
            return future.result()
        return True

    async def _init_servers(self):
        """Load configuration and connect to all enabled MCP servers."""
        if not Path(self.config_path).exists():
            logger.warning(f"[MCP] Config not found: {self.config_path}")
            return

        with open(self.config_path, "r") as f:
            config = json.load(f)
            self._servers = config.get("mcpServers", {})

        for name, cfg in self._servers.items():
            if cfg.get("enabled", True):
                try:
                    await self._connect_to_server(name, cfg)
                except Exception as e:
                    logger.error(f"[MCP] Failed to connect to server '{name}': {e}")
        
        self._initialized = True
        logger.info(f"[MCP] Hub initialized with {len(self._sessions)} active servers.")

    async def _connect_to_server(self, name: str, cfg: Dict):
        """Establish a stdio connection to an MCP server."""
        params = StdioServerParameters(
            command=cfg["command"],
            args=cfg.get("args", []),
            env=cfg.get("env", None)
        )
        
        logger.info(f"[MCP] Connecting to server '{name}' via: {cfg['command']} {' '.join(cfg.get('args', []))}")
        transport_ctx = stdio_client(params)
        read, write = await transport_ctx.__aenter__()
        
        session = ClientSession(read, write)
        await session.initialize()
        
        # Phase 21.2: Send initialized notification
        await session.send_notification("notifications/initialized")
        logger.info(f"[MCP] Session for '{name}' initialized.")
        
        # Store session and tools
        self._sessions[name] = session
        tools_list = await session.list_tools()
        
        for tool in tools_list.tools:
            tool_id = f"mcp:{name}:{tool.name}"
            self._tools[tool_id] = {
                "server": name,
                "original_name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            }
            logger.info(f"[MCP] Discovered tool: {tool_id}")

    def get_available_tools(self) -> Dict[str, Any]:
        """Return a mapping of discovered tools with their metadata."""
        return self._tools

    def call_tool(self, tool_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronously call an MCP tool via the background loop."""
        if tool_id not in self._tools:
            return {"success": False, "error": f"Tool '{tool_id}' not found."}
        
        tool_data = self._tools[tool_id]
        server_name = tool_data["server"]
        session = self._sessions.get(server_name)
        
        if not session:
            return {"success": False, "error": f"Server '{server_name}' is not connected."}

        future = asyncio.run_coroutine_threadsafe(
            session.call_tool(tool_data["original_name"], arguments), 
            self._loop
        )
        
        try:
            result = future.result(timeout=30)
            return {"success": True, "output": result.content}
        except Exception as e:
            logger.error(f"[MCP] Tool execution failed ({tool_id}): {e}")
            return {"success": False, "error": str(e)}

    def stop(self):
        """Gracefully shut down all MCP sessions."""
        future = asyncio.run_coroutine_threadsafe(self._cleanup(), self._loop)
        future.result()
        self._loop.call_soon_threadsafe(self._loop.stop)

    async def _cleanup(self):
        for name, session in self._sessions.items():
            try:
                # In a real implementation, we'd exit the transport context here
                pass 
            except:
                pass
        self._sessions.clear()

# Global singleton
_hub: Optional[MCPHub] = None

def get_mcp_hub() -> MCPHub:
    global _hub
    if _hub is None:
        _hub = MCPHub()
    return _hub
