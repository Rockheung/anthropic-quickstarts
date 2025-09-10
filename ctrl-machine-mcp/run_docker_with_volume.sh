#!/bin/bash

# Run Docker container with volume mapping for screenshots

CONTAINER_NAME="mcp-unified"
IMAGE_NAME="mcp-unified:latest"
SCREENSHOTS_DIR="$(pwd)/screenshots"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting MCP Docker Container with Volume Mapping${NC}"

# Create screenshots directory if it doesn't exist
mkdir -p "$SCREENSHOTS_DIR"
echo -e "${GREEN}✅ Screenshots directory: $SCREENSHOTS_DIR${NC}"

# Check if container already exists
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo -e "${YELLOW}⚠️  Container $CONTAINER_NAME already exists${NC}"
    
    # Check if it's running
    if docker ps | grep -q "$CONTAINER_NAME"; then
        echo -e "${GREEN}✅ Container is already running${NC}"
    else
        echo "Starting existing container..."
        docker start "$CONTAINER_NAME"
    fi
    
    # Stop and remove old container
    echo "Do you want to recreate the container with volume mapping? (y/n)"
    read -r response
    
    if [[ "$response" == "y" ]]; then
        echo "Stopping and removing old container..."
        docker stop "$CONTAINER_NAME" 2>/dev/null
        docker rm "$CONTAINER_NAME" 2>/dev/null
        
        # Run new container with volume mapping
        echo -e "${GREEN}Creating new container with volume mapping...${NC}"
        docker run -d \
            --name "$CONTAINER_NAME" \
            --platform linux/amd64 \
            -e VNC_PASSWORD="${VNC_PASSWORD:-mcp123}" \
            -p 5900:5900 \
            -p 8080:8080 \
            -p 8081:8081 \
            -v "$SCREENSHOTS_DIR:/app/screenshots:rw" \
            "$IMAGE_NAME"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Container created successfully with volume mapping${NC}"
        else
            echo -e "${RED}❌ Failed to create container${NC}"
            exit 1
        fi
    fi
else
    # Run new container
    echo -e "${GREEN}Creating new container with volume mapping...${NC}"
    docker run -d \
        --name "$CONTAINER_NAME" \
        --platform linux/amd64 \
        -e VNC_PASSWORD="${VNC_PASSWORD:-mcp123}" \
        -p 5900:5900 \
        -p 8080:8080 \
        -p 8081:8081 \
        -v "$SCREENSHOTS_DIR:/app/screenshots:rw" \
        "$IMAGE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Container created successfully${NC}"
    else
        echo -e "${RED}❌ Failed to create container${NC}"
        exit 1
    fi
fi

# Wait for container to be ready
echo -e "${YELLOW}⏳ Waiting for container to be ready...${NC}"
sleep 5

# Install aiohttp and start HTTP servers
echo -e "${GREEN}📦 Setting up HTTP MCP servers...${NC}"
docker exec "$CONTAINER_NAME" pip3 install aiohttp 2>/dev/null

# Copy HTTP server files
docker cp screenshot_mcp_http.py "$CONTAINER_NAME:/app/"
docker cp hid_input_mcp_http.py "$CONTAINER_NAME:/app/"

# Start HTTP servers
docker exec -d "$CONTAINER_NAME" python3 /app/screenshot_mcp_http.py
docker exec -d "$CONTAINER_NAME" python3 /app/hid_input_mcp_http.py

# Wait for servers to start
sleep 3

# Check health
echo -e "${GREEN}🏥 Checking server health...${NC}"
if curl -s http://localhost:8080/health | grep -q healthy; then
    echo -e "${GREEN}✅ Screenshot MCP is healthy${NC}"
else
    echo -e "${RED}❌ Screenshot MCP failed to start${NC}"
fi

if curl -s http://localhost:8081/health | grep -q healthy; then
    echo -e "${GREEN}✅ HID Input MCP is healthy${NC}"
else
    echo -e "${RED}❌ HID Input MCP failed to start${NC}"
fi

echo ""
echo -e "${GREEN}📋 Container Status:${NC}"
echo "  Container Name: $CONTAINER_NAME"
echo "  Screenshots:    $SCREENSHOTS_DIR (host) <-> /app/screenshots (container)"
echo "  VNC Access:     vnc://localhost:5900 (password: ${VNC_PASSWORD:-mcp123})"
echo "  Screenshot MCP: http://localhost:8080"
echo "  HID Input MCP:  http://localhost:8081"
echo ""
echo -e "${GREEN}📸 Screenshots will be saved to: $SCREENSHOTS_DIR${NC}"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "  - Open screenshots folder: ./sync_screenshots.sh open"
echo "  - Sync screenshots manually: ./sync_screenshots.sh sync"
echo "  - Watch for new screenshots: ./sync_screenshots.sh watch"
echo "  - Use with Claude Code: claude --mcp-config $(pwd)/mcp_docker_config.json"