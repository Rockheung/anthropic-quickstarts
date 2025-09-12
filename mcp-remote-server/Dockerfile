# Single stage build for amd64 architecture  
FROM --platform=linux/amd64 python:3.12-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

# Install build and runtime dependencies
RUN apt-get update && apt-get install -y \
    # Build tools
    gcc \
    g++ \
    make \
    pkg-config \
    # X11 virtual display
    xvfb \
    x11vnc \
    fluxbox \
    # GUI automation tools
    scrot \
    xdotool \
    xclip \
    x11-utils \
    # System utilities
    wget \
    curl \
    gnupg \
    lsb-release \
    sudo \
    procps \
    # Graphics libraries
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxinerama1 \
    libxi6 \
    libxrandr2 \
    libxcursor1 \
    libxtst6 \
    libxkbfile1 \
    libgl1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxss1 \
    libasound2 \
    # Fonts
    fonts-liberation \
    fonts-noto \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    fonts-noto-extra \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for browser automation (amd64 only)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Pretendard fonts
RUN mkdir -p /usr/share/fonts/truetype/pretendard && \
    # Download Pretendard fonts
    wget -q https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip -O /tmp/pretendard.zip && \
    apt-get update && apt-get install -y unzip && \
    unzip -q /tmp/pretendard.zip -d /tmp/pretendard && \
    cp /tmp/pretendard/public/static/*.otf /usr/share/fonts/truetype/pretendard/ 2>/dev/null || \
    cp /tmp/pretendard/public/static/*.ttf /usr/share/fonts/truetype/pretendard/ 2>/dev/null || \
    cp /tmp/pretendard/web/static/*.ttf /usr/share/fonts/truetype/pretendard/ 2>/dev/null || \
    cp /tmp/pretendard/static/*.ttf /usr/share/fonts/truetype/pretendard/ 2>/dev/null || true && \
    # Clean up
    rm -rf /tmp/pretendard* && \
    apt-get remove -y unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Update font cache
    fc-cache -fv

# Create working directory
WORKDIR /app

# Copy requirements and install Python packages first
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY mcp_fastmcp_server.py /app/
COPY entrypoint.sh /app/

# Create optimized startup script
RUN echo '#!/bin/bash\n\
set -euo pipefail\n\
\n\
# Function to cleanup on exit\n\
cleanup() {\n\
    echo "Cleaning up processes..."\n\
    pkill -f Xvfb || true\n\
    pkill -f fluxbox || true\n\
    pkill -f x11vnc || true\n\
}\n\
\n\
# Set up signal handlers\n\
trap cleanup EXIT\n\
trap cleanup SIGTERM\n\
trap cleanup SIGINT\n\
\n\
# Start X virtual framebuffer with optimized settings\n\
echo "Starting Xvfb display server..."\n\
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -dpi 96 -ac &\n\
XVFB_PID=$!\n\
\n\
# Wait for X server to be ready\n\
for i in {1..30}; do\n\
    if xdpyinfo -display :99 >/dev/null 2>&1; then\n\
        echo "X server is ready"\n\
        break\n\
    fi\n\
    if [ $i -eq 30 ]; then\n\
        echo "X server failed to start"\n\
        exit 1\n\
    fi\n\
    sleep 0.1\n\
done\n\
\n\
# Start lightweight window manager\n\
echo "Starting window manager..."\n\
fluxbox &\n\
FLUXBOX_PID=$!\n\
sleep 1\n\
\n\
# Optional: Start VNC server for debugging\n\
if [ "${ENABLE_VNC:-false}" = "true" ] && [ ! -z "${VNC_PASSWORD:-}" ]; then\n\
    echo "Starting VNC server..."\n\
    mkdir -p ~/.vnc\n\
    x11vnc -storepasswd "$VNC_PASSWORD" ~/.vnc/passwd\n\
    x11vnc -forever -display :99 -rfbauth ~/.vnc/passwd -rfbport 5900 -shared -nowf &\n\
    echo "VNC server started on port 5900"\n\
fi\n\
\n\
# Verify system readiness\n\
echo "Verifying system readiness..."\n\
python3 -c "import mss; import pyautogui; print(f\"Found {len(mss.mss().monitors)} monitors\")"\n\
\n\
# Start the MCP server\n\
echo "Starting MCP server v2.0.0 on $MCP_HOST:$MCP_PORT"\n\
exec python3 /app/mcp_fastmcp_server.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Create improved health check script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Check if MCP server is responding\n\
if ! curl -f -s --max-time 5 http://localhost:${MCP_PORT}/health >/dev/null 2>&1; then\n\
    echo "Health check failed: MCP server not responding"\n\
    exit 1\n\
fi\n\
\n\
# Check if X server is running\n\
if ! pgrep -f "Xvfb :99" >/dev/null; then\n\
    echo "Health check failed: X server not running"\n\
    exit 1\n\
fi\n\
\n\
echo "Health check passed"\n\
exit 0\n\
' > /app/healthcheck.sh && chmod +x /app/healthcheck.sh

# Create non-root user for security and set up directories
RUN groupadd -r mcpuser && useradd -r -g mcpuser -u 1001 -m mcpuser \
    && mkdir -p /home/mcpuser/.fluxbox /home/mcpuser/.cache/fontconfig /tmp/.X11-unix \
    && chown -R mcpuser:mcpuser /app /home/mcpuser \
    && chmod +x /app/*.sh \
    && chmod 1777 /tmp/.X11-unix

# Switch to non-root user
USER mcpuser

# Expose ports
EXPOSE 8000 5900

# Health check with improved settings
HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD /app/healthcheck.sh

# Add labels for better container management
LABEL maintainer="MCP Remote Server" \
      version="2.0.0" \
      description="MCP server for remote computer control with GUI automation" \
      org.opencontainers.image.source="https://github.com/anthropics/anthropic-quickstarts"

# Entry point
ENTRYPOINT ["/app/start.sh"]