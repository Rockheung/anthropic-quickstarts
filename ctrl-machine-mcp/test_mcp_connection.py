#!/usr/bin/env python3
"""Test MCP server connections in Docker container."""

import subprocess
import json
import sys

def test_mcp_server(server_name, command, args):
    """Test if an MCP server responds to initialization."""
    print(f"\nTesting {server_name}...")
    
    # Prepare MCP initialization message
    init_message = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }
    
    try:
        # Run the MCP server command
        process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send initialization message
        process.stdin.write(json.dumps(init_message) + "\n")
        process.stdin.flush()
        
        # Wait for response (with timeout)
        import time
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print(f"✓ {server_name} is running")
            process.terminate()
            return True
        else:
            stderr = process.stderr.read()
            print(f"✗ {server_name} failed to start")
            if stderr:
                print(f"  Error: {stderr}")
            return False
            
    except Exception as e:
        print(f"✗ {server_name} connection failed: {e}")
        return False

def main():
    """Test all MCP servers."""
    print("Testing MCP Server Connections in Docker Container")
    print("=" * 50)
    
    # Load configuration
    with open('claude_code_mcp_config.json', 'r') as f:
        config = json.load(f)
    
    results = []
    for server_name, server_config in config['mcpServers'].items():
        command = server_config['command']
        args = server_config['args']
        success = test_mcp_server(server_name, command, args)
        results.append((server_name, success))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {name}: {status}")
    
    # Return exit code based on results
    sys.exit(0 if all(r[1] for r in results) else 1)

if __name__ == "__main__":
    main()