#!/bin/bash

# Set up VNC password if provided
if [ -n "$VNC_PASSWORD" ]; then
    echo "Setting VNC password..."
    mkdir -p /home/mcpuser/.vnc
    echo "$VNC_PASSWORD" | vncpasswd -f > /home/mcpuser/.vnc/passwd
    chmod 600 /home/mcpuser/.vnc/passwd
    chown -R mcpuser:mcpuser /home/mcpuser/.vnc
fi

# Start supervisor
echo "Starting MCP HTTP servers..."
exec /usr/local/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf