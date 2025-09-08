#!/usr/bin/env python3
"""Test MCP server functionality."""

import json
import subprocess
import sys

def test_mcp_server(server_script):
    """Test MCP server with initialization request."""
    # JSON-RPC initialization request
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {"tools": {}}
        },
        "id": 1
    }
    
    # Run the MCP server with the request
    cmd = f'echo \'{json.dumps(init_request)}\' | docker exec -i mcp-unified python3 /app/{server_script}'
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=3
        )
        
        print(f"Testing {server_script}:")
        print("STDOUT:", result.stdout[:500] if result.stdout else "No output")
        print("STDERR:", result.stderr[:500] if result.stderr else "No errors")
        print("-" * 50)
        
        # Check if we got a valid JSON response
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip() and line.startswith('{'):
                    try:
                        response = json.loads(line)
                        if 'jsonrpc' in response:
                            print(f"✅ Valid JSON-RPC response received")
                            return True
                    except json.JSONDecodeError:
                        pass
        
        return False
        
    except subprocess.TimeoutExpired:
        print(f"❌ {server_script} timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing {server_script}: {e}")
        return False

if __name__ == "__main__":
    # Test both MCP servers
    hid_ok = test_mcp_server("hid_input_mcp.py")
    screenshot_ok = test_mcp_server("screenshot_mcp.py")
    
    if hid_ok and screenshot_ok:
        print("\n✅ Both MCP servers are responding correctly!")
    else:
        print("\n⚠️ MCP servers need debugging")
        sys.exit(1)