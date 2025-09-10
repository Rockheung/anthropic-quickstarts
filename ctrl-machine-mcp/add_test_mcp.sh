#!/bin/bash

# Script to add a test MCP server to Claude Code configuration

MCP_CONFIG_FILE="$HOME/.claude/mcp_settings.json"
PROJECT_MCP_CONFIG=".claude/mcp_settings.json"

# Create backup of existing config if it exists
if [ -f "$MCP_CONFIG_FILE" ]; then
    cp "$MCP_CONFIG_FILE" "$MCP_CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backed up existing config to $MCP_CONFIG_FILE.backup.*"
fi

# Function to add test MCP server to config
add_test_mcp() {
    local config_file="$1"
    local server_name="$2"
    
    # Create directory if it doesn't exist
    mkdir -p "$(dirname "$config_file")"
    
    # Check if file exists and has content
    if [ -f "$config_file" ] && [ -s "$config_file" ]; then
        # Use Python to safely merge JSON
        python3 -c "
import json
import sys

config_file = '$config_file'
server_name = '$server_name'

try:
    with open(config_file, 'r') as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = {}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Add test MCP server
config['mcpServers'][server_name] = {
    'command': 'python3',
    'args': ['/Users/rock/Documents/rockheung/anthropic-quickstarts/ctrl-machine-mcp/test_mcp_server.py'],
    'env': {
        'PYTHONUNBUFFERED': '1',
        'MCP_TEST_MODE': 'true'
    }
}

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print(f'Added {server_name} to {config_file}')
"
    else
        # Create new config file
        cat > "$config_file" <<EOF
{
  "mcpServers": {
    "$server_name": {
      "command": "python3",
      "args": ["/Users/rock/Documents/rockheung/anthropic-quickstarts/ctrl-machine-mcp/test_mcp_server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "MCP_TEST_MODE": "true"
      }
    }
  }
}
EOF
        echo "Created new config at $config_file with $server_name"
    fi
}

# Parse command line arguments
SERVER_NAME="${1:-test-mcp}"
CONFIG_LEVEL="${2:-user}"  # 'user' or 'project'

echo "Adding test MCP server: $SERVER_NAME"
echo "Configuration level: $CONFIG_LEVEL"

if [ "$CONFIG_LEVEL" = "project" ]; then
    add_test_mcp "$PROJECT_MCP_CONFIG" "$SERVER_NAME"
else
    add_test_mcp "$MCP_CONFIG_FILE" "$SERVER_NAME"
fi

echo ""
echo "Test MCP server '$SERVER_NAME' has been added!"
echo ""
echo "Next steps:"
echo "1. Create the test MCP server at: /Users/rock/Documents/rockheung/anthropic-quickstarts/ctrl-machine-mcp/test_mcp_server.py"
echo "2. Restart Claude Code to load the new MCP server"
echo "3. Run '/mcp' in Claude Code to verify the server is loaded"
echo ""
echo "Usage examples:"
echo "  ./add_test_mcp.sh                    # Add 'test-mcp' to user config"
echo "  ./add_test_mcp.sh my-test-server     # Add custom named server to user config"
echo "  ./add_test_mcp.sh test-mcp project   # Add to project-level config"