#!/bin/bash

# Clean up any existing X server locks
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null

# Start X virtual framebuffer
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -ac &
XVFB_PID=$!
sleep 3

# Check if Xvfb started successfully
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "Failed to start Xvfb"
    exit 1
fi

# Export display variable
export DISPLAY=:99
echo "DISPLAY set to $DISPLAY"

# Test X connection
xdpyinfo -display :99 >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "X server not responding properly"
    exit 1
fi

# Start window manager
echo "Starting Fluxbox..."
fluxbox -display :99 &
sleep 2


# Optional: Start VNC server for debugging (password required)
if [ ! -z "$VNC_PASSWORD" ]; then
    echo "Setting up VNC server..."
    mkdir -p ~/.vnc
    x11vnc -storepasswd "$VNC_PASSWORD" ~/.vnc/passwd 2>/dev/null
    x11vnc -forever -display :99 -rfbauth ~/.vnc/passwd -rfbport 5900 -noxdamage -shared &
    echo "VNC server started on port 5900"
fi

# Wait for everything to stabilize
sleep 3

# Start the MCP FastMCP SSE server
echo "Starting MCP SSE server on $MCP_HOST:$MCP_PORT"
echo "SSE endpoint will be available at: http://$MCP_HOST:$MCP_PORT/sse"
exec python3 /app/mcp_fastmcp_server.py