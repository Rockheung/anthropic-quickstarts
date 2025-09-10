#!/usr/bin/env python3
"""Test the Unified MCP server functionality."""

import json
import subprocess
import sys
import time

def test_unified_server():
    """Test unified MCP server with initialization request."""
    # JSON-RPC initialization request
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0.0",
            "capabilities": {"tools": {}}
        },
        "id": 1
    }
    
    # Test tools list request
    tools_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    
    # Run the unified MCP server with the requests
    cmd = f'echo \'{json.dumps(init_request)}\' | docker exec -i mcp-unified python3 /app/unified_mcp_server.py'
    
    try:
        print("Testing Unified MCP Server...")
        print("=" * 50)
        
        # Test initialization
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print("Initialization Test:")
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and line.startswith('{'):
                    try:
                        response = json.loads(line)
                        if 'result' in response:
                            print("✅ Server initialized successfully")
                            print(f"   Server: {response['result'].get('serverInfo', {}).get('name')}")
                            print(f"   Version: {response['result'].get('serverInfo', {}).get('version')}")
                            break
                    except json.JSONDecodeError:
                        pass
        
        if result.stderr:
            print("Stderr:", result.stderr[:200])
        
        print()
        
        # Test tools list
        cmd = f'echo \'{json.dumps(tools_request)}\' | docker exec -i mcp-unified python3 /app/unified_mcp_server.py'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print("Tools List Test:")
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and line.startswith('{'):
                    try:
                        response = json.loads(line)
                        if 'result' in response and 'tools' in response['result']:
                            tools = response['result']['tools']
                            print(f"✅ Found {len(tools)} tools:")
                            
                            # Group tools by category
                            hid_tools = []
                            screenshot_tools = []
                            system_tools = []
                            
                            for tool in tools:
                                name = tool.get('name', '')
                                if name in ['move_mouse', 'click_mouse', 'type_text', 'press_key']:
                                    hid_tools.append(name)
                                elif 'capture' in name or 'screenshot' in name:
                                    screenshot_tools.append(name)
                                else:
                                    system_tools.append(name)
                            
                            if hid_tools:
                                print(f"   HID Input: {', '.join(hid_tools)}")
                            if screenshot_tools:
                                print(f"   Screenshot: {', '.join(screenshot_tools)}")
                            if system_tools:
                                print(f"   System: {', '.join(system_tools)}")
                            
                            return True
                    except json.JSONDecodeError:
                        pass
        
        print("❌ Could not get tools list")
        return False
        
    except subprocess.TimeoutExpired:
        print("❌ Server timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

if __name__ == "__main__":
    # Wait a bit for container to be ready
    print("Waiting for container to be ready...")
    time.sleep(2)
    
    # Check if container is running
    check_cmd = "docker ps | grep mcp-unified"
    result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
    
    if "mcp-unified" not in result.stdout:
        print("❌ Container is not running. Please start it first with:")
        print("   docker-compose up -d")
        sys.exit(1)
    
    # Test the server
    if test_unified_server():
        print("\n✅ Unified MCP Server is working correctly!")
        print("\nYou can now:")
        print("1. Restart Claude Code to load the MCP settings")
        print("2. Type '/mcp' in Claude Code to see 'unified-automation'")
    else:
        print("\n⚠️ Server needs debugging")
        print("Check logs with: docker-compose logs")
        sys.exit(1)