import subprocess
import json
import time

def test_raw_stdio():
    print("[RAW] Spawning mock server...")
    proc = subprocess.Popen(
        ["python", "test_mcp_mock_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Send initialize
    msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    print(f"[RAW] Sending: {json.dumps(msg)}")
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    
    # Read response
    line = proc.stdout.readline()
    print(f"[RAW] Received: {line.strip()}")
    
    # Send list_tools
    msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    print(f"[RAW] Sending: {json.dumps(msg)}")
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    
    line = proc.stdout.readline()
    print(f"[RAW] Received: {line.strip()}")
    
    proc.terminate()
    print("[RAW] Test complete.")

if __name__ == "__main__":
    test_raw_stdio()
