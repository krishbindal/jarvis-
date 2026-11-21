"""Integration coverage for the optional MCP v2 subprocess."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.mcp_hub import MCPHub, _MCP_AVAILABLE, _server_environment


class McpEnvironmentTests(unittest.TestCase):
    def test_default_child_does_not_inherit_secrets(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "private", "EMAIL_PASS": "hidden"}):
            child = _server_environment()
            self.assertNotIn("GROQ_API_KEY", child)
            self.assertNotIn("EMAIL_PASS", child)

    def test_explicit_server_settings_are_passed(self):
        self.assertEqual(_server_environment({"MY_TEST_SETTING": "ok"})["MY_TEST_SETTING"], "ok")


@unittest.skipUnless(_MCP_AVAILABLE, "install requirements-mcp.txt first")
class McpLifecycleTests(unittest.TestCase):
    def test_stdio_tool_roundtrip_and_clean_shutdown(self):
        server = Path(__file__).with_name("mock_mcp_server.py")
        with tempfile.TemporaryDirectory() as folder:
            config_path = Path(folder) / "mcp_servers.json"
            config_path.write_text(
                json.dumps({
                    "mcpServers": {
                        "echo": {
                            "command": sys.executable,
                            "args": ["-u", str(server)],
                            "enabled": True,
                        }
                    }
                }),
                encoding="utf-8",
            )
            hub = MCPHub(config_path=str(config_path))
            try:
                self.assertTrue(hub.start(), "MCP v2 mock server did not connect")
                tool_id = "mcp:echo:echo"
                self.assertIn(tool_id, hub.get_available_tools())
                self.assertIsInstance(hub.get_available_tools()[tool_id]["input_schema"], dict)
                result = hub.call_tool(tool_id, {"text": "hello MCP"})
                self.assertTrue(result["success"], result)
                self.assertIn("hello MCP", str(result["output"]))
            finally:
                self.assertTrue(hub.stop(), "MCP loop thread did not stop")
                self.assertFalse(hub._thread.is_alive())


if __name__ == "__main__":
    unittest.main()
