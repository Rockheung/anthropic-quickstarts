# Multi-stage build for amd64 architecture
FROM --platform=linux/amd64 python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage - amd64 architecture
FROM --platform=linux/amd64 python:3.12-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
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

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create working directory
WORKDIR /app

# Copy application files
COPY mcp_fastmcp_server.py /app/
COPY requirements.txt /app/
COPY entrypoint.sh /app/

# Create startup script
RUN echo '#!/bin/bash\n\
# Start X virtual framebuffer\n\
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &\n\
sleep 2\n\
\n\
# Start window manager\n\
fluxbox &\n\
sleep 1\n\
\n\
# Optional: Start VNC server for debugging (password required)\n\
if [ ! -z "$VNC_PASSWORD" ]; then\n\
    mkdir -p ~/.vnc\n\
    x11vnc -storepasswd "$VNC_PASSWORD" ~/.vnc/passwd\n\
    x11vnc -forever -display :99 -rfbauth ~/.vnc/passwd -rfbport 5900 &\n\
    echo "VNC server started on port 5900"\n\
fi\n\
\n\
# Start the MCP server\n\
echo "Starting MCP server on $MCP_HOST:$MCP_PORT"\n\
exec python3 /app/mcp_server.py\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Create health check script
RUN echo '#!/bin/bash\n\
curl -f http://localhost:${MCP_PORT}/health || exit 1\n\
' > /app/healthcheck.sh && chmod +x /app/healthcheck.sh

# Expose ports
EXPOSE 8000 5900

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# Entry point
ENTRYPOINT ["/app/entrypoint.sh"]