import time
from core.mcp_hub import get_mcp_hub

def test_mcp():
    print("[TEST] Initializing MCP Hub...")
    hub = get_mcp_hub()
    hub.start()
    
    # Give it a moment to connect and discover tools
    print("[TEST] Waiting for tool discovery...")
    time.sleep(3)
    
    tools = hub.get_available_tools()
    print(f"[TEST] Discovered {len(tools)} tools: {list(tools.keys())}")
    
    if not tools:
        print("[FAIL] No tools discovered.")
        return

    # Call the mock tool
    tool_id = "mcp:mock-server:mock_hello"
    if tool_id not in tools:
        # Check if the name matches (mock-server is hardcoded in the mock script)
        tool_id = list(tools.keys())[0]

    print(f"[TEST] Calling tool '{tool_id}'...")
    result = hub.call_tool(tool_id, {"name": "Krish"})
    
    if result["success"]:
        print(f"[SUCCESS] Tool Result: {result['output']}")
    else:
        print(f"[FAIL] Tool execution failed: {result['error']}")

    hub.stop()
    print("[TEST] Hub stopped.")

if __name__ == "__main__":
    test_mcp()
