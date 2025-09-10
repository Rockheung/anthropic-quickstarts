#!/bin/bash

# Sync screenshots from Docker container to host machine

CONTAINER_NAME="mcp-unified"
HOST_DIR="/Users/heungjun/rockheung/anthropic-quickstarts/ctrl-machine-mcp/screenshots"
CONTAINER_DIR="/app/screenshots"

# Create host directory if it doesn't exist
mkdir -p "$HOST_DIR"

# Function to sync screenshots
sync_screenshots() {
    echo "📸 Syncing screenshots from Docker container to host..."
    
    # Copy all screenshots from container to host
    docker cp "$CONTAINER_NAME:$CONTAINER_DIR/." "$HOST_DIR/" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Screenshots synced successfully"
        
        # List synced files
        echo "📁 Files in $HOST_DIR:"
        ls -lh "$HOST_DIR" | tail -n +2
    else
        echo "❌ Failed to sync screenshots. Is the container running?"
    fi
}

# Function to watch and sync continuously
watch_sync() {
    echo "👀 Watching for new screenshots (Ctrl+C to stop)..."
    
    while true; do
        # Get current file count in container
        CONTAINER_COUNT=$(docker exec "$CONTAINER_NAME" ls "$CONTAINER_DIR" 2>/dev/null | wc -l)
        
        # Get current file count on host
        HOST_COUNT=$(ls "$HOST_DIR" 2>/dev/null | wc -l)
        
        # If counts differ, sync
        if [ "$CONTAINER_COUNT" != "$HOST_COUNT" ]; then
            echo "🔄 New screenshots detected!"
            sync_screenshots
        fi
        
        # Wait 5 seconds before next check
        sleep 5
    done
}

# Main script
case "${1:-sync}" in
    sync)
        sync_screenshots
        ;;
    watch)
        watch_sync
        ;;
    clean)
        echo "🗑️ Cleaning local screenshots..."
        rm -f "$HOST_DIR"/*.png
        echo "✅ Local screenshots cleaned"
        ;;
    open)
        echo "📂 Opening screenshots folder..."
        open "$HOST_DIR"
        ;;
    *)
        echo "Usage: $0 [sync|watch|clean|open]"
        echo "  sync  - Sync screenshots once (default)"
        echo "  watch - Watch and sync continuously"
        echo "  clean - Remove all local screenshots"
        echo "  open  - Open screenshots folder in Finder"
        exit 1
        ;;
esac