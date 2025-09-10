# Model Context Protocol (MCP) - Latest 2025 Specification Guide

## Overview

The Model Context Protocol (MCP) is an open protocol that enables seamless integration between LLM applications and external data sources/tools. It provides a standardized way to connect AI models with the context they need, built on JSON-RPC 2.0.

**Current Version**: June 18, 2025 Update  
**Official Specification**: https://modelcontextprotocol.io/specification/2025-06-18

## Transport Mechanisms

MCP supports three primary transport mechanisms:

### 1. Standard Input/Output (stdio)
- Direct process communication via stdin/stdout
- Ideal for local server processes
- Example configuration:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 2. HTTP with Server-Sent Events (SSE)
- HTTP endpoints for request/response
- SSE for server-initiated events
- Supports remote servers
- Example configuration:
```json
{
  "mcpServers": {
    "remote-server": {
      "type": "sse",
      "url": "https://api.example.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer token"
      }
    }
  }
}
```

### 3. Streamable HTTP (New in 2025)
- Replaces HTTP+SSE for better performance
- Supports streaming responses
- JSON-RPC batching support
- Example configuration:
```json
{
  "mcpServers": {
    "stream-server": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer token"
      }
    }
  }
}
```

## June 2025 Security Updates

### OAuth 2.1 Integration
MCP servers are now classified as **OAuth Resource Servers**, requiring:
- OAuth 2.1 framework for authentication
- Resource Indicators (RFC 8707) for token scoping
- Protected resource metadata in server discovery

### Resource Indicators
Mandatory implementation to prevent token misuse:
```json
{
  "resource": "https://mcp-server.example.com",
  "scope": "read:screenshots write:inputs",
  "grant_type": "authorization_code"
}
```

### Security Best Practices
1. **Token Scoping**: Use tightly scoped tokens specific to each MCP server
2. **Transport Security**: Always use TLS for HTTP connections
3. **Input Validation**: Validate all inputs from MCP clients
4. **Rate Limiting**: Implement rate limits for API endpoints

## Core Protocol Structure

### Request Format (JSON-RPC 2.0)
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "screenshot",
    "arguments": {
      "format": "base64"
    }
  },
  "id": "request-123"
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "image",
        "data": "base64_encoded_image_data"
      }
    ]
  },
  "id": "request-123"
}
```

## MCP Server Implementation

### Basic Server Structure (Python)
```python
import json
import sys
from typing import Any, Dict

class MCPServer:
    def __init__(self):
        self.protocol_version = "1.0.0"
        self.server_info = {
            "name": "my-mcp-server",
            "version": "1.0.0"
        }
    
    async def handle_request(self, request: Dict[str, Any]):
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "initialize":
            return self.initialize(params)
        elif method == "tools/list":
            return self.list_tools()
        elif method == "tools/call":
            return self.call_tool(params)
        
    def initialize(self, params):
        return {
            "protocolVersion": self.protocol_version,
            "serverInfo": self.server_info,
            "capabilities": {
                "tools": True,
                "resources": True
            }
        }
```

## Claude Code Integration

### Configuration in Claude Code

1. **Project-level Configuration** (`.claude/mcp_settings.json`):
```json
{
  "mcpServers": {
    "screenshot-mcp": {
      "command": "python",
      "args": ["./mcp_server_screenshot.py"],
      "env": {
        "DISPLAY": ":99"
      }
    },
    "hid-input-mcp": {
      "command": "python", 
      "args": ["./mcp_server_hid.py"],
      "env": {
        "DISPLAY": ":99"
      }
    }
  }
}
```

2. **User-level Configuration** (`~/.claude/mcp_settings.json`):
- Global MCP servers available across all projects
- Same format as project-level configuration

### Common Issues and Solutions

#### Issue: "Package not found" errors
**Solution**: MCP servers should use standard executables (python, node) not npm packages that don't exist

#### Issue: Connection failures
**Solution**: 
- Ensure server is running and accessible
- Check firewall/port settings
- Verify authentication tokens

#### Issue: Protocol version mismatch
**Solution**: Update to latest MCP specification (1.0.0)

## Docker Integration for MCP Servers

### Docker Compose Configuration
```yaml
services:
  mcp-bridge:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    ports:
      - "8080:8080"  # Screenshot MCP
      - "8081:8081"  # HID Input MCP
    environment:
      - DISPLAY=:99
    volumes:
      - ./screenshots:/app/screenshots
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
```

### Dockerfile Example
```dockerfile
FROM python:3.12-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    fluxbox \
    python3-tk \
    python3-dev

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy MCP servers
COPY mcp_server_*.py /app/

# Start services
CMD ["python", "/app/mcp_http_bridge.py"]
```

## Testing MCP Connections

### Health Check Endpoint
```python
@app.route('/health')
def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

### Test Script
```python
import requests
import json

def test_mcp_connection(url):
    # Test initialize
    response = requests.post(f"{url}/mcp", json={
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"protocolVersion": "1.0.0"},
        "id": 1
    })
    
    if response.status_code == 200:
        print(f"✓ MCP server at {url} is responding")
        print(f"Response: {response.json()}")
    else:
        print(f"✗ Failed to connect to {url}")

# Test both servers
test_mcp_connection("http://localhost:8080")
test_mcp_connection("http://localhost:8081")
```

## Industry Adoption (2025)

- **Google DeepMind**: Gemini models with native MCP support
- **Microsoft**: Native MCP in Copilot Studio, GitHub integration
- **Anthropic**: Claude Code with built-in MCP support
- **Open Source**: Growing ecosystem of MCP servers and tools

## Resources

- **Official Documentation**: https://modelcontextprotocol.io
- **GitHub Repository**: https://github.com/modelcontextprotocol
- **TypeScript SDK**: `npm install @modelcontextprotocol/sdk`
- **Python SDK**: `pip install mcp`
- **Community Servers**: https://github.com/topics/mcp-server

## Version History

- **June 18, 2025**: OAuth 2.1 updates, Resource Indicators
- **March 26, 2025**: Streamable HTTP, JSON-RPC batching
- **January 2025**: Initial 1.0.0 release

---

*Last Updated: January 2025*
*Based on official MCP Specification v1.0.0*