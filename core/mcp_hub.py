"""Optional MCP v2 stdio integration with explicit subprocess lifecycle."""
from __future__ import annotations

import asyncio
from concurrent.futures import TimeoutError as FutureTimeout
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from mcp import Client, StdioServerParameters
    _MCP_AVAILABLE = True
    _MCP_ERROR = None
except Exception as exc:  # noqa: BLE001
    Client = None
    StdioServerParameters = None
    _MCP_AVAILABLE = False
    _MCP_ERROR = exc

from utils.logger import get_logger

logger = get_logger("jarvis.mcp")

# Opt-in subprocess integrations should not inherit AI or email secrets by default.
_INHERITED_MCP_ENV = (
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "TEMP", "TMP", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
)


def _server_environment(configured: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    environment = {name: os.environ[name] for name in _INHERITED_MCP_ENV if name in os.environ}
    if configured:
        environment.update({str(name): str(value) for name, value in configured.items()})
    return environment


class NoopMCPHub:
    """Harmless fallback when the optional MCP SDK is not installed."""

    def __init__(self, reason: Optional[Exception] = None):
        self._reason = reason

    def start(self) -> bool:
        logger.warning("[MCP] Optional SDK unavailable: %s", self._reason)
        return False

    def stop(self) -> bool:
        return True

    def get_available_tools(self) -> Dict[str, Any]:
        return {}

    def call_tool(self, tool_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": False, "error": f"MCP unavailable: {self._reason}"}


class MCPHub:
    """Run v2 MCP clients on a dedicated asyncio loop, closing every client on stop."""

    def __init__(self, config_path: str = "config/mcp_servers.json"):
        self.config_path = config_path
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._sessions: Dict[str, Any] = {}
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_event_loop, name="jarvis-mcp-loop", daemon=True
        )
        self._initialized = False
        self._stopped = False

    def _run_event_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def start(self) -> bool:
        if not _MCP_AVAILABLE:
            logger.warning("[MCP] SDK unavailable: %s", _MCP_ERROR)
            return False
        if self._stopped:
            logger.warning("[MCP] Hub was stopped; construct a new hub to restart.")
            return False
        if self._initialized:
            return True
        if not self._thread.is_alive():
            self._thread.start()
        task = asyncio.run_coroutine_threadsafe(self._init_servers(), self._loop)
        try:
            return bool(task.result(timeout=45))
        except (Exception, FutureTimeout):
            task.cancel()
            logger.exception("[MCP] Hub initialization failed")
            return False

    async def _init_servers(self) -> bool:
        config_file = Path(self.config_path)
        if not config_file.is_file():
            logger.warning("[MCP] Configuration file not found: %s", config_file)
            return False
        with config_file.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        self._servers = data.get("mcpServers", {})
        for name, settings in self._servers.items():
            if not settings.get("enabled", True):
                continue
            try:
                await self._connect_to_server(name, settings)
            except Exception:
                logger.exception("[MCP] Failed connecting to server %s", name)
        self._initialized = True
        logger.info("[MCP] Connected to %d server(s)", len(self._sessions))
        return bool(self._sessions)

    async def _connect_to_server(self, name: str, settings: Dict[str, Any]) -> None:
        params = StdioServerParameters(
            command=settings["command"],
            args=settings.get("args", []),
            env=_server_environment(settings.get("env")),
        )
        logger.info("[MCP] Connecting to configured server '%s'", name)
        client = Client(params)
        await client.__aenter__()
        try:
            cursor = None
            discovered = {}
            while True:
                listing = await client.list_tools(cursor=cursor)
                for tool in listing.tools:
                    tool_id = f"mcp:{name}:{tool.name}"
                    discovered[tool_id] = {
                        "server": name,
                        "original_name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                cursor = listing.next_cursor
                if cursor is None:
                    break
        except BaseException:
            await client.__aexit__(None, None, None)
            raise
        self._sessions[name] = client
        self._tools.update(discovered)
        logger.info("[MCP] Server '%s' offers %d tools", name, len(discovered))

    def get_available_tools(self) -> Dict[str, Any]:
        return dict(self._tools)

    def call_tool(self, tool_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(tool_id)
        if tool is None:
            return {"success": False, "error": f"Unknown MCP tool: {tool_id}"}
        client = self._sessions.get(tool["server"])
        if client is None or self._stopped:
            return {"success": False, "error": "MCP server disconnected"}
        future = asyncio.run_coroutine_threadsafe(
            client.call_tool(tool["original_name"], arguments), self._loop
        )
        try:
            result = future.result(timeout=30)
            return {
                "success": not bool(getattr(result, "is_error", False)),
                "output": result.content,
            }
        except FutureTimeout:
            future.cancel()
            return {"success": False, "error": "MCP tool exceeded 30-second timeout"}
        except Exception as exc:
            logger.error("[MCP] Tool %s failed: %s", tool_id, exc)
            return {"success": False, "error": str(exc)}

    def stop(self) -> bool:
        if self._stopped:
            return True
        self._stopped = True
        if not self._thread.is_alive():
            self._loop.close()
            return True
        future = asyncio.run_coroutine_threadsafe(self._cleanup(), self._loop)
        try:
            future.result(timeout=20)
        except Exception:
            future.cancel()
            logger.exception("[MCP] Cleanup incomplete")
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)
            if not self._thread.is_alive():
                self._loop.close()
        return not self._thread.is_alive()

    async def _cleanup(self) -> None:
        for name, client in reversed(list(self._sessions.items())):
            try:
                await client.__aexit__(None, None, None)
            except Exception:
                logger.exception("[MCP] Failed closing client for server %s", name)
        self._sessions.clear()
        self._tools.clear()
        self._initialized = False


_hub: Optional[MCPHub] = None


def get_mcp_hub():
    global _hub
    if _hub is None or getattr(_hub, "_stopped", False):
        _hub = MCPHub() if _MCP_AVAILABLE else NoopMCPHub(_MCP_ERROR)
    return _hub
