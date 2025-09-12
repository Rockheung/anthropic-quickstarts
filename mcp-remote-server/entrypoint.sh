#!/bin/bash
set -euo pipefail

# Enhanced entrypoint script for MCP Remote Server v2.0.0

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up processes..."
    pkill -f Xvfb || true
    pkill -f fluxbox || true
    pkill -f x11vnc || true
}

# Set up signal handlers
trap cleanup EXIT
trap cleanup SIGTERM
trap cleanup SIGINT

echo "=== MCP Remote Server v2.0.0 Starting ==="
echo "Configuration:"
echo "  MCP_HOST: ${MCP_HOST:-0.0.0.0}"
echo "  MCP_PORT: ${MCP_PORT:-8000}"
echo "  LOG_LEVEL: ${LOG_LEVEL:-INFO}"
echo "  ENABLE_VNC: ${ENABLE_VNC:-false}"

# Clean up any existing X server locks
echo "Cleaning up existing X server locks..."
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

# Start X virtual framebuffer with optimized settings
echo "Starting Xvfb display server..."
Xvfb :99 -screen 0 ${DISPLAY_WIDTH:-1920}x${DISPLAY_HEIGHT:-1080}x24 \
    -nolisten tcp -dpi 96 -ac +extension RANDR &
XVFB_PID=$!

# Wait for X server to be ready with timeout
echo "Waiting for X server to be ready..."
for i in {1..30}; do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "X server is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: X server failed to start within 30 seconds"
        cleanup
        exit 1
    fi
    sleep 0.1
done

# Verify X server is still running
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "ERROR: Xvfb process died unexpectedly"
    exit 1
fi

# Export display variable
export DISPLAY=:99
echo "DISPLAY set to $DISPLAY"

# Start lightweight window manager
echo "Starting Fluxbox window manager..."
fluxbox -display :99 &
FLUXBOX_PID=$!
sleep 1

# Optional: Start VNC server for debugging
if [ "${ENABLE_VNC:-false}" = "true" ] && [ ! -z "${VNC_PASSWORD:-}" ]; then
    echo "Starting VNC server for debugging..."
    mkdir -p ~/.vnc
    x11vnc -storepasswd "$VNC_PASSWORD" ~/.vnc/passwd
    x11vnc -forever -display :99 -rfbauth ~/.vnc/passwd -rfbport 5900 \
        -noxdamage -shared -nowf -bg
    echo "VNC server started on port 5900"
elif [ "${ENABLE_VNC:-false}" = "true" ]; then
    echo "WARNING: VNC enabled but no password set. Skipping VNC server."
fi

# Verify system readiness
echo "Verifying system readiness..."
python3 -c "
import sys
try:
    import mss
    import pyautogui
    screenshotter = mss.mss()
    monitor_count = len(screenshotter.monitors)
    print(f'System check passed: Found {monitor_count} monitors')
    if monitor_count == 0:
        print('WARNING: No monitors detected')
        sys.exit(1)
except Exception as e:
    print(f'System check failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "ERROR: System readiness check failed"
    cleanup
    exit 1
fi

# Final startup message
echo "=== System Ready ==="
echo "Starting MCP Server v2.0.0 on ${MCP_HOST:-0.0.0.0}:${MCP_PORT:-8000}"
echo "Health check: http://${MCP_HOST:-0.0.0.0}:${MCP_PORT:-8000}/health"
echo "Metrics: http://${MCP_HOST:-0.0.0.0}:${MCP_PORT:-8000}/metrics"
echo "SSE endpoint: http://${MCP_HOST:-0.0.0.0}:${MCP_PORT:-8000}/sse"

# Start the MCP server
exec python3 /app/mcp_fastmcp_server.py