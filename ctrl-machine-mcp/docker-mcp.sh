#!/bin/bash
# Docker MCP Server Management Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.combined.yml"
CONTAINER_NAME="mcp-combined"

# Functions
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

show_help() {
    cat << EOF
Docker MCP Server Management Script

Usage: $0 [command] [options]

Commands:
    build       Build the Docker image
    start       Start the MCP servers
    stop        Stop the MCP servers
    restart     Restart the MCP servers
    status      Show container status
    logs        Show container logs
    test        Run tests in container
    vnc         Open VNC connection (macOS)
    shell       Open shell in container
    clean       Stop and remove containers
    help        Show this help message

Options:
    --separate  Use separate containers for each MCP server
    --follow    Follow logs (with 'logs' command)

Examples:
    $0 build              # Build the combined image
    $0 start              # Start combined container
    $0 start --separate   # Start separate containers
    $0 logs --follow      # Follow container logs
    $0 test               # Run tests
    $0 vnc                # Connect to VNC display

Ports:
    5900 - VNC server (visual debugging)
    8080 - HID Input MCP server
    8081 - Screenshot MCP server

EOF
}

build_image() {
    print_status "Building Docker image..."
    docker-compose -f $COMPOSE_FILE build mcp-combined
    print_status "Build complete!"
}

start_containers() {
    if [[ "$1" == "--separate" ]]; then
        print_status "Starting separate MCP containers..."
        docker-compose -f $COMPOSE_FILE --profile separate up -d
    else
        print_status "Starting combined MCP container..."
        docker-compose -f $COMPOSE_FILE up -d mcp-combined
    fi
    
    print_status "Waiting for services to start..."
    sleep 5
    
    show_status
    print_status "MCP servers are running!"
    echo ""
    echo "Access points:"
    echo "  VNC:        vnc://localhost:5900"
    echo "  HID MCP:    http://localhost:8080"
    echo "  Screenshot: http://localhost:8081"
}

stop_containers() {
    print_status "Stopping MCP containers..."
    docker-compose -f $COMPOSE_FILE down
    print_status "Containers stopped."
}

restart_containers() {
    stop_containers
    sleep 2
    start_containers "$@"
}

show_status() {
    print_status "Container status:"
    docker-compose -f $COMPOSE_FILE ps
    
    echo ""
    print_status "Port bindings:"
    docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "(NAMES|mcp-)" || true
}

show_logs() {
    if [[ "$1" == "--follow" ]]; then
        print_status "Following container logs (Ctrl+C to exit)..."
        docker-compose -f $COMPOSE_FILE logs -f
    else
        print_status "Recent logs:"
        docker-compose -f $COMPOSE_FILE logs --tail=50
    fi
}

run_tests() {
    print_status "Running tests in container..."
    
    # Test health check
    print_status "1. Health check..."
    docker exec $CONTAINER_NAME python3 /app/healthcheck.py
    
    # Test screenshot functionality
    print_status "2. Screenshot test..."
    docker exec $CONTAINER_NAME python3 /app/test_screenshot.py
    
    # Test combined functionality
    print_status "3. Combined HID + Screenshot test..."
    docker exec $CONTAINER_NAME python3 /app/test_combined.py
    
    print_status "All tests passed!"
}

open_vnc() {
    print_status "Opening VNC connection..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open vnc://localhost:5900
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v vncviewer &> /dev/null; then
            vncviewer localhost:5900 &
        else
            print_error "vncviewer not found. Install it with: sudo apt-get install vncviewer"
            echo "Manual connection: vnc://localhost:5900"
        fi
    else
        print_warning "Please connect to vnc://localhost:5900 manually"
    fi
}

open_shell() {
    print_status "Opening shell in container..."
    docker exec -it $CONTAINER_NAME /bin/bash
}

clean_up() {
    print_warning "Cleaning up containers and volumes..."
    docker-compose -f $COMPOSE_FILE down -v
    print_status "Cleanup complete."
}

# Main script
case "$1" in
    build)
        build_image
        ;;
    start)
        start_containers "$2"
        ;;
    stop)
        stop_containers
        ;;
    restart)
        restart_containers "$2"
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    test)
        run_tests
        ;;
    vnc)
        open_vnc
        ;;
    shell)
        open_shell
        ;;
    clean)
        clean_up
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac