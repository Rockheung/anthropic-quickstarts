# Use Python 3.12 slim image based on Debian (lighter than Ubuntu)
# Support both amd64 and arm64 architectures
FROM --platform=linux/amd64 python:3.12-slim

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
# Optional VNC password (can be overridden at runtime)
ENV VNC_PASSWORD=""

# Update system and install essential packages
RUN apt-get update && apt-get install -y \
    # X11 and display dependencies
    xvfb \
    x11vnc \
    fluxbox \
    xterm \
    # GUI automation dependencies
    scrot \
    xdotool \
    xclip \
    # System utilities
    wget \
    curl \
    gnupg \
    lsb-release \
    sudo \
    git \
    nano \
    # Libraries for PyAutoGUI
    python3-tk \
    python3-dev \
    python3-pil \
    python3-pil.imagetk \
    # Build dependencies for evdev
    gcc \
    libc6-dev \
    linux-libc-dev \
    # Additional X11 libraries
    libx11-dev \
    libxext-dev \
    libxrender-dev \
    libxinerama-dev \
    libxi-dev \
    libxrandr-dev \
    libxcursor-dev \
    libxtst-dev \
    libxkbfile-dev \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for browser automation (using new GPG key method)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Korean fonts (Nanum) - download directly from Ubuntu repository
RUN wget -P /tmp https://launchpad.net/ubuntu/+archive/primary/+files/fonts-nanum_20200506-1_all.deb \
    && wget -P /tmp https://launchpad.net/ubuntu/+archive/primary/+files/fonts-nanum-coding_2.5-1_all.deb \
    && dpkg -i /tmp/fonts-nanum*.deb || true \
    && apt-get update && apt-get install -f -y \
    && rm /tmp/fonts-nanum*.deb \
    && fc-cache -fv

# Create a non-root user for running the application
RUN useradd -m -s /bin/bash mcpuser && \
    echo 'mcpuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Set working directory
WORKDIR /app

# Copy both MCP servers
COPY hid_input_mcp.py /app/
COPY screenshot_mcp.py /app/
COPY requirements.txt /app/

# Create requirements file if it doesn't exist
RUN echo "pyautogui==0.9.54" > /app/requirements.txt && \
    echo "pynput==1.7.6" >> /app/requirements.txt && \
    echo "mcp>=0.1.0" >> /app/requirements.txt && \
    echo "pillow>=10.0.0" >> /app/requirements.txt && \
    echo "python-xlib>=0.33" >> /app/requirements.txt && \
    echo "pyscreeze>=0.1.30" >> /app/requirements.txt && \
    echo "mss>=9.0.1" >> /app/requirements.txt && \
    echo "numpy>=1.24.0" >> /app/requirements.txt

# Install Python packages including supervisor
RUN pip3 install --no-cache-dir -r /app/requirements.txt && \
    pip3 install --no-cache-dir supervisor

# Create supervisor configuration for running both MCP servers
RUN mkdir -p /etc/supervisor/conf.d && \
    echo '[supervisord]' > /etc/supervisor/supervisord.conf && \
    echo 'nodaemon=true' >> /etc/supervisor/supervisord.conf && \
    echo 'user=mcpuser' >> /etc/supervisor/supervisord.conf && \
    echo 'logfile=/tmp/supervisord.log' >> /etc/supervisor/supervisord.conf && \
    echo 'pidfile=/tmp/supervisord.pid' >> /etc/supervisor/supervisord.conf && \
    echo '' >> /etc/supervisor/supervisord.conf && \
    echo '[program:hid-mcp]' >> /etc/supervisor/supervisord.conf && \
    echo 'command=python3 /app/hid_input_mcp.py' >> /etc/supervisor/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisor/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/supervisord.conf && \
    echo 'stderr_logfile=/tmp/hid-mcp.err.log' >> /etc/supervisor/supervisord.conf && \
    echo 'stdout_logfile=/tmp/hid-mcp.out.log' >> /etc/supervisor/supervisord.conf && \
    echo 'environment=DISPLAY=":99",PYTHONUNBUFFERED="1"' >> /etc/supervisor/supervisord.conf && \
    echo '' >> /etc/supervisor/supervisord.conf && \
    echo '[program:screenshot-mcp]' >> /etc/supervisor/supervisord.conf && \
    echo 'command=python3 /app/screenshot_mcp.py' >> /etc/supervisor/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisor/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/supervisord.conf && \
    echo 'stderr_logfile=/tmp/screenshot-mcp.err.log' >> /etc/supervisor/supervisord.conf && \
    echo 'stdout_logfile=/tmp/screenshot-mcp.out.log' >> /etc/supervisor/supervisord.conf && \
    echo 'environment=DISPLAY=":99",PYTHONUNBUFFERED="1"' >> /etc/supervisor/supervisord.conf

# Create startup script
RUN echo '#!/bin/bash\n\
# Start X virtual framebuffer\n\
Xvfb :99 -screen 0 1920x1080x24 &\n\
sleep 2\n\
\n\
# Start window manager\n\
fluxbox &\n\
sleep 2\n\
\n\
# Start VNC server with optional password\n\
if [ -n "$VNC_PASSWORD" ]; then\n\
    # Create VNC password file\n\
    mkdir -p ~/.vnc\n\
    x11vnc -storepasswd "$VNC_PASSWORD" ~/.vnc/passwd\n\
    x11vnc -display :99 -rfbauth ~/.vnc/passwd -listen 0.0.0.0 -forever -shared &\n\
else\n\
    # No password\n\
    x11vnc -display :99 -nopw -listen 0.0.0.0 -forever -shared &\n\
fi\n\
\n\
# Start Chrome in kiosk mode (optional)\n\
if [ "$START_BROWSER" = "true" ]; then\n\
    google-chrome --no-sandbox --disable-dev-shm-usage --disable-gpu \\\n\
        --window-size=1920,1080 --window-position=0,0 \\\n\
        --no-first-run --no-default-browser-check \\\n\
        --disable-translate --disable-features=TranslateUI \\\n\
        --disable-background-timer-throttling \\\n\
        --disable-renderer-backgrounding \\\n\
        --disable-backgrounding-occluded-windows \\\n\
        ${CHROME_URL:-"https://www.google.com"} &\n\
fi\n\
\n\
# Run supervisor to manage both MCP servers or any command passed\n\
if [ "$1" = "supervisor" ]; then\n\
    exec /usr/local/bin/supervisord -c /etc/supervisor/supervisord.conf\n\
else\n\
    exec "$@"\n\
fi\n\
' > /app/start.sh && chmod +x /app/start.sh

# Create a healthcheck script
RUN echo '#!/bin/bash\n\
import pyautogui\n\
import sys\n\
try:\n\
    # Test if we can get screen size\n\
    width, height = pyautogui.size()\n\
    print(f"Screen size: {width}x{height}")\n\
    # Test if we can get mouse position\n\
    x, y = pyautogui.position()\n\
    print(f"Mouse position: {x},{y}")\n\
    sys.exit(0)\n\
except Exception as e:\n\
    print(f"Health check failed: {e}")\n\
    sys.exit(1)\n\
' > /app/healthcheck.py && chmod +x /app/healthcheck.py

# Switch to non-root user
USER mcpuser

# Expose ports
# 5900 for VNC
# 8080 for HID MCP server (if using HTTP transport)
# 8081 for Screenshot MCP server (if using HTTP transport)
EXPOSE 5900 8080 8081

# Set entrypoint
ENTRYPOINT ["/app/start.sh"]

# Default command - run supervisor to manage both MCP servers
CMD ["supervisor"]