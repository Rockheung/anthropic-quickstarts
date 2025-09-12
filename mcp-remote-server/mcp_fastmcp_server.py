#!/usr/bin/env python3
"""
MCP SSE Server using FastMCP from official SDK
Remote computer control via Server-Sent Events transport
"""

import asyncio
import atexit
import base64
import io
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Custom exception classes
class MCPError(Exception):
    """Base exception for MCP server errors"""
    pass

class ToolError(MCPError):
    """Exception for tool execution errors"""
    pass

class ValidationError(MCPError):
    """Exception for input validation errors"""
    pass

class DisplayError(MCPError):
    """Exception for display-related errors"""
    pass

# Configuration dataclass
@dataclass
class ServerConfig:
    host: str
    port: int
    log_level: str
    display: str
    max_screenshot_size: int
    rate_limit_requests: int
    rate_limit_window: int
    enable_vnc: bool
    vnc_password: Optional[str]
    
    @classmethod
    def from_env(cls) -> 'ServerConfig':
        return cls(
            host=os.getenv('MCP_HOST', '0.0.0.0'),
            port=int(os.getenv('MCP_PORT', '8000')),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            display=os.getenv('DISPLAY', ':99'),
            max_screenshot_size=int(os.getenv('MAX_SCREENSHOT_SIZE', '5242880')),  # 5MB
            rate_limit_requests=int(os.getenv('RATE_LIMIT_REQUESTS', '100')),
            rate_limit_window=int(os.getenv('RATE_LIMIT_WINDOW', '60')),
            enable_vnc=os.getenv('ENABLE_VNC', 'false').lower() == 'true',
            vnc_password=os.getenv('VNC_PASSWORD')
        )

# Load configuration
config = ServerConfig.from_env()

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Set display before importing GUI libraries
os.environ['DISPLAY'] = config.display

# Import MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
    from mcp import types
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    from starlette.middleware.cors import CORSMiddleware
    from starlette.responses import JSONResponse
    import uvicorn
except ImportError as e:
    logger.error(f"Required packages not installed: {e}")
    logger.error("Run: pip install mcp starlette uvicorn")
    sys.exit(1)

# Import GUI libraries
try:
    import mss
    import pyautogui
    import PIL.Image
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05  # Reduced pause for better performance
except ImportError as e:
    logger.error(f"Required libraries not installed: {e}")
    sys.exit(1)

# Rate limiting storage
class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
        
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
            
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.window_seconds
        ]
        
        if len(self.requests[client_id]) >= self.max_requests:
            return False
            
        self.requests[client_id].append(now)
        return True

# Initialize rate limiter
rate_limiter = RateLimiter(config.rate_limit_requests, config.rate_limit_window)

# Security middleware
class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Get client IP
            client_ip = None
            for header_name, header_value in scope.get("headers", []):
                if header_name == b"x-forwarded-for":
                    client_ip = header_value.decode().split(",")[0].strip()
                    break
                elif header_name == b"x-real-ip":
                    client_ip = header_value.decode()
                    break
            
            if not client_ip:
                client_ip = scope.get("client", ["unknown"])[0]
            
            # Rate limiting check
            if not rate_limiter.is_allowed(client_ip):
                response = JSONResponse(
                    {"error": "Rate limit exceeded", "retry_after": config.rate_limit_window},
                    status_code=429
                )
                await response(scope, receive, send)
                return
            
            # Security headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers.update({
                        b"x-content-type-options": b"nosniff",
                        b"x-frame-options": b"DENY",
                        b"x-xss-protection": b"1; mode=block",
                        b"strict-transport-security": b"max-age=31536000; includeSubDomains",
                        b"content-security-policy": b"default-src 'self'",
                        b"server": b"MCP-Remote-Control/2.0.0"
                    })
                    message["headers"] = list(headers.items())
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)

# Initialize FastMCP server
mcp = FastMCP("remote-computer-control")

# Global screenshot instance and cleanup tracking
screenshotter = mss.mss()
cleanup_functions = []

# Input validation helpers
def validate_coordinates(x: int, y: int) -> None:
    """Validate mouse coordinates"""
    if not isinstance(x, int) or not isinstance(y, int):
        raise ValidationError("Coordinates must be integers")
    if x < 0 or y < 0:
        raise ValidationError("Coordinates must be non-negative")
    if x > 10000 or y > 10000:  # Reasonable upper limit
        raise ValidationError("Coordinates too large")

def validate_text_input(text: str) -> None:
    """Validate text input"""
    if not isinstance(text, str):
        raise ValidationError("Text must be a string")
    if len(text) > 10000:  # Prevent excessively long text
        raise ValidationError("Text too long (max 10000 characters)")

def validate_monitor_index(monitor: int) -> None:
    """Validate monitor index"""
    if not isinstance(monitor, int):
        raise ValidationError("Monitor index must be an integer")
    if monitor < 0:
        raise ValidationError("Monitor index must be non-negative")
    if monitor >= len(screenshotter.monitors):
        raise ValidationError(f"Monitor {monitor} not found (available: 0-{len(screenshotter.monitors)-1})")

def validate_image_quality(quality: int) -> None:
    """Validate image quality parameter"""
    if not isinstance(quality, int):
        raise ValidationError("Quality must be an integer")
    if quality < 1 or quality > 100:
        raise ValidationError("Quality must be between 1 and 100")

def validate_key_input(key: str) -> None:
    """Validate key input"""
    if not isinstance(key, str):
        raise ValidationError("Key must be a string")
    if len(key) > 50:  # Reasonable key name limit
        raise ValidationError("Key name too long")
        
# Error handling decorator
def handle_tool_errors(func):
    """Decorator to handle tool errors consistently"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            raise ToolError(f"Validation error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise ToolError(f"Tool execution failed: {e}")
    return wrapper

# Tool implementations
@mcp.tool()
@handle_tool_errors
def screenshot(
    format: str = "base64",
    quality: int = 85,
    monitor: int = 0,
    compress: bool = True
) -> types.ImageContent:
    """
    Capture a screenshot of the screen.
    
    Args:
        format: Output format ("base64" or "url")
        quality: Image quality (1-100) for JPEG, ignored for PNG
        monitor: Monitor index (0 for primary)
        compress: Whether to use JPEG compression for smaller size
    
    Returns:
        Screenshot as base64-encoded image
    """
    validate_image_quality(quality)
    validate_monitor_index(monitor)
    
    if format not in ["base64", "url"]:
        raise ValidationError("Format must be 'base64' or 'url'")
    
    monitors = screenshotter.monitors
    mon = monitors[monitor]
    screenshot_data = screenshotter.grab(mon)
    
    # Convert to PIL Image
    img = PIL.Image.frombytes("RGB", screenshot_data.size, screenshot_data.bgra, "raw", "BGRX")
    
    # Optimize image size if too large
    max_dimension = 1920
    if img.width > max_dimension or img.height > max_dimension:
        ratio = min(max_dimension / img.width, max_dimension / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, PIL.Image.Resampling.LANCZOS)
        logger.info(f"Resized screenshot from {screenshot_data.size} to {new_size}")
    
    # Convert to base64
    buffer = io.BytesIO()
    if compress:
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        mime_type = "image/jpeg"
    else:
        img.save(buffer, format="PNG", optimize=True)
        mime_type = "image/png"
        
    img_data = base64.b64encode(buffer.getvalue()).decode()
    
    # Check size limit
    if len(img_data) > config.max_screenshot_size:
        raise ToolError(f"Screenshot too large: {len(img_data)} bytes (max: {config.max_screenshot_size})")
    
    logger.info(f"Screenshot captured: {img.width}x{img.height}, size: {len(img_data)} bytes")
    
    return types.ImageContent(
        type="image",
        data=img_data,
        mimeType=mime_type
    )

@mcp.tool()
@handle_tool_errors
def move_mouse(x: int, y: int, duration: float = 0.5) -> str:
    """
    Move mouse to specific coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        duration: Movement duration in seconds (0.1-5.0)
    
    Returns:
        Confirmation message
    """
    validate_coordinates(x, y)
    
    if not isinstance(duration, (int, float)):
        raise ValidationError("Duration must be a number")
    if duration < 0.1 or duration > 5.0:
        raise ValidationError("Duration must be between 0.1 and 5.0 seconds")
    
    pyautogui.moveTo(x, y, duration=duration)
    logger.info(f"Mouse moved to ({x}, {y}) in {duration}s")
    return f"Moved mouse to ({x}, {y}) in {duration}s"

@mcp.tool()
@handle_tool_errors
def click_mouse(
    button: str = "left",
    x: Optional[int] = None,
    y: Optional[int] = None,
    clicks: int = 1,
    interval: float = 0.0
) -> str:
    """
    Click mouse button at current or specified position.
    
    Args:
        button: Mouse button ("left", "right", "middle")
        x: X coordinate (optional)
        y: Y coordinate (optional)
        clicks: Number of clicks (1-10)
        interval: Interval between clicks in seconds (0.0-2.0)
    
    Returns:
        Confirmation message
    """
    valid_buttons = ["left", "right", "middle"]
    if button not in valid_buttons:
        raise ValidationError(f"Button must be one of: {valid_buttons}")
    
    if x is not None and y is not None:
        validate_coordinates(x, y)
    
    if not isinstance(clicks, int) or clicks < 1 or clicks > 10:
        raise ValidationError("Clicks must be an integer between 1 and 10")
    
    if not isinstance(interval, (int, float)) or interval < 0.0 or interval > 2.0:
        raise ValidationError("Interval must be between 0.0 and 2.0 seconds")
    
    if x is not None and y is not None:
        pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
        logger.info(f"Clicked {button} {clicks} times at ({x}, {y})")
        return f"Clicked {button} button {clicks} times at ({x}, {y})"
    else:
        pyautogui.click(clicks=clicks, interval=interval, button=button)
        pos = pyautogui.position()
        logger.info(f"Clicked {button} {clicks} times at current position ({pos.x}, {pos.y})")
        return f"Clicked {button} button {clicks} times at current position ({pos.x}, {pos.y})"

@mcp.tool()
@handle_tool_errors
def type_text(text: str, interval: float = 0.02) -> str:
    """
    Type text using keyboard.
    
    Args:
        text: Text to type
        interval: Interval between keystrokes in seconds (0.01-0.5)
    
    Returns:
        Confirmation message
    """
    validate_text_input(text)
    
    if not isinstance(interval, (int, float)) or interval < 0.01 or interval > 0.5:
        raise ValidationError("Interval must be between 0.01 and 0.5 seconds")
    
    pyautogui.typewrite(text, interval=interval)
    logger.info(f"Typed {len(text)} characters: {text[:50]}{'...' if len(text) > 50 else ''}")
    return f"Typed {len(text)} characters: {text[:50]}{'...' if len(text) > 50 else ''}"

@mcp.tool()
@handle_tool_errors
def press_key(key: str, modifiers: List[str] = []) -> str:
    """
    Press a key or key combination.
    
    Args:
        key: Key to press (e.g., 'enter', 'tab', 'escape', 'a', 'f1')
        modifiers: Modifier keys (e.g., ['ctrl', 'alt', 'shift'])
    
    Returns:
        Confirmation message
    """
    validate_key_input(key)
    
    valid_modifiers = ['ctrl', 'alt', 'shift', 'cmd', 'win']
    for modifier in modifiers:
        if not isinstance(modifier, str):
            raise ValidationError("Modifiers must be strings")
        if modifier not in valid_modifiers:
            raise ValidationError(f"Invalid modifier '{modifier}'. Valid modifiers: {valid_modifiers}")
    
    if len(modifiers) > 3:
        raise ValidationError("Too many modifiers (max 3)")
    
    if modifiers:
        keys = modifiers + [key]
        pyautogui.hotkey(*keys)
        key_combo = '+'.join(keys)
        logger.info(f"Pressed key combination: {key_combo}")
        return f"Pressed key combination: {key_combo}"
    else:
        pyautogui.press(key)
        logger.info(f"Pressed key: {key}")
        return f"Pressed key: {key}"

@mcp.tool()
@handle_tool_errors
def get_screen_size(monitor: int = 0) -> Dict[str, Any]:
    """
    Get screen dimensions and monitor information.
    
    Args:
        monitor: Monitor index (0 for primary)
    
    Returns:
        Screen dimensions and monitor info as dict
    """
    validate_monitor_index(monitor)
    
    monitors = screenshotter.monitors
    mon = monitors[monitor]
    
    result = {
        "width": mon["width"],
        "height": mon["height"],
        "left": mon["left"],
        "top": mon["top"],
        "monitor_index": monitor,
        "total_monitors": len(monitors)
    }
    
    logger.info(f"Screen size for monitor {monitor}: {result['width']}x{result['height']}")
    return result

@mcp.tool()
@handle_tool_errors
def get_mouse_position() -> Dict[str, int]:
    """
    Get current mouse position and screen bounds.
    
    Returns:
        Mouse position and screen info as dict
    """
    pos = pyautogui.position()
    screen_size = pyautogui.size()
    
    result = {
        "x": pos.x,
        "y": pos.y,
        "screen_width": screen_size.width,
        "screen_height": screen_size.height
    }
    
    logger.info(f"Mouse position: ({pos.x}, {pos.y})")
    return result

# Additional tools for system information
@mcp.tool()
@handle_tool_errors
def get_system_info() -> Dict[str, Any]:
    """
    Get comprehensive system information.
    
    Returns:
        System information as dict
    """
    import platform
    import psutil
    
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
    except (ImportError, OSError, AttributeError) as e:
        logger.warning(f"Failed to get system metrics: {e}")
        cpu_percent = 0
        memory = None
        disk = None
    
    info = {
        "system": {
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python_version": platform.python_version()
        },
        "display": {
            "current_display": os.environ.get("DISPLAY", "none"),
            "monitors": len(screenshotter.monitors),
            "monitor_info": [{
                "index": i,
                "width": mon["width"],
                "height": mon["height"]
            } for i, mon in enumerate(screenshotter.monitors)]
        },
        "performance": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent if memory else None,
            "disk_percent": (disk.used / disk.total * 100) if disk else None
        },
        "server": {
            "name": "remote-computer-control",
            "version": "2.0.0",
            "transport": "SSE",
            "config": {
                "host": config.host,
                "port": config.port,
                "log_level": config.log_level,
                "rate_limit": f"{config.rate_limit_requests}/{config.rate_limit_window}s"
            }
        }
    }
    
    logger.info("System info requested")
    return info

# Resource for server status
@mcp.resource("server://status")
def get_server_status() -> str:
    """
    Get server status information.
    
    Returns:
        Server status as JSON string
    """
    status = {
        "name": "remote-computer-control",
        "version": "2.0.0",
        "transport": "SSE",
        "status": "healthy",
        "uptime": time.time() - start_time,
        "display": os.environ.get("DISPLAY", "none"),
        "monitors": len(screenshotter.monitors),
        "config": {
            "host": config.host,
            "port": config.port,
            "log_level": config.log_level
        }
    }
    return json.dumps(status, indent=2)

# Health check endpoints
def health_check(request):
    """Health check endpoint"""
    try:
        # Basic health checks
        monitors_available = len(screenshotter.monitors) > 0
        display_set = os.environ.get("DISPLAY") is not None
        
        status = {
            "status": "healthy" if monitors_available and display_set else "degraded",
            "timestamp": time.time(),
            "checks": {
                "monitors_available": monitors_available,
                "display_set": display_set,
                "mcp_server": True
            },
            "server": {
                "name": "remote-computer-control",
                "version": "2.0.0",
                "uptime": time.time() - start_time
            }
        }
        
        return JSONResponse(status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            {"status": "unhealthy", "error": str(e)},
            status_code=503
        )

def metrics_endpoint(request):
    """Metrics endpoint for monitoring"""
    try:
        import psutil
        
        metrics = {
            "timestamp": time.time(),
            "uptime": time.time() - start_time,
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent if psutil.disk_usage('/') else 0
            },
            "display": {
                "monitors": len(screenshotter.monitors),
                "current_display": os.environ.get("DISPLAY", "none")
            },
            "rate_limiting": {
                "active_clients": len(rate_limiter.requests),
                "max_requests_per_window": config.rate_limit_requests,
                "window_seconds": config.rate_limit_window
            }
        }
        
        return JSONResponse(metrics)
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return JSONResponse({"error": "Metrics unavailable"}, status_code=500)

# Cleanup functions
def cleanup_resources():
    """Clean up resources on shutdown"""
    logger.info("Cleaning up resources...")
    try:
        if screenshotter:
            screenshotter.close()
        for cleanup_func in cleanup_functions:
            try:
                cleanup_func()
            except Exception as e:
                logger.warning(f"Cleanup function failed: {e}")
    except Exception as e:
        logger.error(f"Resource cleanup failed: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    cleanup_resources()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
atexit.register(cleanup_resources)

# Track server start time
start_time = time.time()

# Main entry point
if __name__ == "__main__":
    logger.info(f"Starting MCP SSE Server v2.0.0 on {config.host}:{config.port}")
    logger.info(f"Configuration: {config}")
    logger.info("SSE endpoint will be available at /sse")
    logger.info("Health check available at /health")
    logger.info("Metrics available at /metrics")
    
    # Verify display is available
    if not os.environ.get("DISPLAY"):
        logger.warning("DISPLAY environment variable not set")
    
    try:
        # Test screenshot capability
        monitors = screenshotter.monitors
        logger.info(f"Found {len(monitors)} monitors")
        for i, mon in enumerate(monitors):
            logger.info(f"Monitor {i}: {mon['width']}x{mon['height']} at ({mon['left']}, {mon['top']})")
    except Exception as e:
        logger.error(f"Failed to initialize screenshot capability: {e}")
    
    # Create Starlette app with the SSE server mounted
    app = Starlette(
        routes=[
            Route("/health", health_check, methods=["GET"]),
            Route("/metrics", metrics_endpoint, methods=["GET"]),
            Mount("/", app=mcp.sse_app()),
        ]
    )
    
    # Add security middleware
    app.add_middleware(SecurityMiddleware)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Run the server
    try:
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level=config.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)
    finally:
        cleanup_resources()