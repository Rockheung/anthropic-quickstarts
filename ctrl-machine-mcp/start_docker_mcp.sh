#!/bin/bash

echo "🚀 Starting Docker MCP Servers..."

# Check if container is running
if ! docker ps | grep -q mcp-unified; then
    echo "❌ Container 'mcp-unified' is not running"
    echo "Starting container..."
    docker start mcp-unified
    sleep 3
fi

# Install aiohttp if not already installed
echo "📦 Checking dependencies..."
docker exec mcp-unified pip3 list | grep -q aiohttp || docker exec mcp-unified pip3 install aiohttp

# Copy HTTP server files to container
echo "📂 Copying server files..."
docker cp screenshot_mcp_http.py mcp-unified:/app/
docker cp hid_input_mcp_http.py mcp-unified:/app/

# Kill any existing HTTP servers
echo "🔄 Restarting HTTP servers..."
docker exec mcp-unified pkill -f mcp_http || true
sleep 1

# Start HTTP servers
docker exec -d mcp-unified python3 /app/screenshot_mcp_http.py
docker exec -d mcp-unified python3 /app/hid_input_mcp_http.py

# Wait for servers to start
echo "⏳ Waiting for servers to start..."
sleep 3

# Check health
echo "🏥 Checking server health..."
if curl -s http://localhost:8080/health | grep -q healthy; then
    echo "✅ Screenshot MCP is healthy"
else
    echo "❌ Screenshot MCP failed to start"
fi

if curl -s http://localhost:8081/health | grep -q healthy; then
    echo "✅ HID Input MCP is healthy"
else
    echo "❌ HID Input MCP failed to start"
fi

echo ""
echo "📋 MCP Servers Status:"
echo "  Screenshot MCP: http://localhost:8080"
echo "  HID Input MCP:  http://localhost:8081"
echo "  VNC Access:     vnc://localhost:5900"
echo ""
echo "🎯 To use with Claude Code:"
echo "  claude --mcp-config $(pwd)/mcp_docker_config.json"