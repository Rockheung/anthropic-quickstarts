# Use Python 3.12 slim image based on Debian (lighter than Ubuntu)
FROM python:3.12-slim

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

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
    software-properties-common \
    sudo \
    git \
    nano \
    # Libraries for PyAutoGUI
    python3-tk \
    python3-dev \
    python3-pil \
    python3-pil.imagetk \
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

# Install Chrome for browser automation
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for running the application
RUN useradd -m -s /bin/bash mcpuser && \
    echo 'mcpuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Set working directory
WORKDIR /app

# Copy the HID input MCP server
COPY hid_input_mcp.py /app/
COPY requirements.txt /app/

# Create requirements file if it doesn't exist
RUN echo "pyautogui==0.9.54" > /app/requirements.txt && \
    echo "pynput==1.8.1" >> /app/requirements.txt && \
    echo "mcp==1.13.1" >> /app/requirements.txt && \
    echo "pillow>=10.0.0" >> /app/requirements.txt && \
    echo "python-xlib>=0.33" >> /app/requirements.txt && \
    echo "pyscreeze>=0.1.30" >> /app/requirements.txt

# Install Python packages
RUN pip3 install --no-cache-dir -r /app/requirements.txt

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
# Start VNC server (optional, for debugging)\n\
x11vnc -display :99 -nopw -listen 0.0.0.0 -forever -shared &\n\
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
# Run the MCP server or any command passed\n\
exec "$@"\n\
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
# 8080 for MCP server (if using HTTP transport)
EXPOSE 5900 8080

# Set entrypoint
ENTRYPOINT ["/app/start.sh"]

# Default command - run the HID input MCP server
CMD ["python3", "/app/hid_input_mcp.py"]