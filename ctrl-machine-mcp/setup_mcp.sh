#!/bin/bash

# Setup script for MCP servers with Claude Code

echo "🚀 Setting up MCP servers for Claude Code..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if container is running
if ! docker ps | grep -q mcp-unified; then
    echo "📦 Starting MCP unified container..."
    docker-compose up -d
    sleep 3
fi

# Create Claude Code config directory if not exists
mkdir -p ~/.claude

# Copy configuration to Claude Code config location
CONFIG_FILE=~/.claude/claude_code_config.json

if [ -f "$CONFIG_FILE" ]; then
    echo "⚠️  Config file already exists. Creating backup..."
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
fi

echo "📝 Installing MCP configuration..."
cat > "$CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "hid-input-mcp": {
      "command": "docker",
      "args": [
        "exec", "-i", "mcp-unified",
        "python3", "/app/hid_input_mcp.py"
      ],
      "env": {
        "DISPLAY": ":99",
        "PYTHONUNBUFFERED": "1"
      }
    },
    "screenshot-mcp": {
      "command": "docker",
      "args": [
        "exec", "-i", "mcp-unified",
        "python3", "/app/screenshot_mcp.py"
      ],
      "env": {
        "DISPLAY": ":99",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
EOF

echo "✅ MCP servers configured successfully!"
echo ""
echo "📋 Available MCP servers:"
echo "  • hid-input-mcp - Hardware input control (keyboard/mouse)"
echo "  • screenshot-mcp - Screen capture and analysis"
echo ""
echo "🔧 To use in Claude Code:"
echo "  1. Restart Claude Code"
echo "  2. Use /mcp command to list available servers"
echo "  3. Call MCP tools directly in your conversation"
echo ""
echo "🖥️  VNC access available at: vnc://localhost:5900"
echo "  Password: Check your .env file"
echo ""
echo "✨ Setup complete!"