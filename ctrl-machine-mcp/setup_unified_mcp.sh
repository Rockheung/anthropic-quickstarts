#!/bin/bash

# Setup script for Unified MCP Server with Claude Code

echo "=================================="
echo "Unified MCP Server Setup for Claude Code"
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build and start the container
echo "📦 Building Docker image..."
docker-compose build

echo "🚀 Starting Docker container..."
docker-compose up -d

# Wait for container to be ready
echo "⏳ Waiting for container to be ready..."
sleep 5

# Check container status
if docker-compose ps | grep -q "mcp-unified.*Up"; then
    echo "✅ Container is running"
else
    echo "❌ Container failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Create Claude Code MCP settings directory
echo "📁 Creating Claude Code settings directory..."
mkdir -p ~/.claude

# Create MCP settings for Claude Code
echo "⚙️ Configuring MCP settings for Claude Code..."
cat > ~/.claude/mcp_settings.json << 'EOF'
{
  "mcpServers": {
    "unified-automation": {
      "command": "docker",
      "args": ["exec", "-i", "mcp-unified", "python3", "/app/unified_mcp_server.py"],
      "env": {
        "DISPLAY": ":99",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
EOF

echo "✅ MCP settings configured at ~/.claude/mcp_settings.json"
echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "🎯 Next Steps:"
echo "1. Restart Claude Code to load the new MCP settings"
echo "2. In Claude Code, type '/mcp' to verify the server is connected"
echo "3. You should see 'unified-automation' in the list"
echo ""
echo "📝 Available Tools:"
echo "  HID Input:"
echo "    - move_mouse: Move mouse to position"
echo "    - click_mouse: Click at position"
echo "    - type_text: Type text"
echo "    - press_key: Press key combinations"
echo ""
echo "  Screenshot:"
echo "    - capture_screenshot: Take a screenshot"
echo "    - start_periodic_capture: Start periodic capture"
echo "    - stop_periodic_capture: Stop periodic capture"
echo ""
echo "  System:"
echo "    - get_system_status: Get system status"
echo "    - clear_all_history: Clear event history"
echo ""
echo "🖥️ VNC Access (for debugging):"
echo "  URL: vnc://localhost:5900"
if [ -n "$VNC_PASSWORD" ]; then
    echo "  Password: (set in .env file)"
else
    echo "  Password: (no password)"
fi
echo ""
echo "📊 Container Logs:"
echo "  docker-compose logs -f"
echo ""