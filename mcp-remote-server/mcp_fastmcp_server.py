#!/usr/bin/env python3
"""
MCP SSE Server using FastMCP from official SDK
Remote computer control via Server-Sent Events transport
"""

import asyncio
import base64
import io
import json
import logging
import os
import sys
from typing import Optional

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Set display before importing GUI libraries
os.environ['DISPLAY'] = ':99'

# Import MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
    from mcp import types
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.middleware.cors import CORSMiddleware
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
    pyautogui.PAUSE = 0.1
except ImportError as e:
    logger.error(f"Required libraries not installed: {e}")
    sys.exit(1)

# Initialize FastMCP server
mcp = FastMCP(
    name="remote-computer-control",
    version="1.0.0"
)

# Global screenshot instance
screenshotter = mss.mss()

# Tool implementations
@mcp.tool()
def screenshot(
    format: str = "base64",
    quality: int = 85,
    monitor: int = 0
) -> types.ImageContent:
    """
    Capture a screenshot of the screen.
    
    Args:
        format: Output format ("base64" or "url")
        quality: JPEG quality (1-100)
        monitor: Monitor index (0 for primary)
    
    Returns:
        Screenshot as base64-encoded image
    """
    try:
        monitors = screenshotter.monitors
        if monitor >= len(monitors):
            raise ValueError(f"Monitor {monitor} not found")
        
        mon = monitors[monitor]
        screenshot_data = screenshotter.grab(mon)
        
        # Convert to PIL Image
        img = PIL.Image.frombytes("RGB", screenshot_data.size, screenshot_data.bgra, "raw", "BGRX")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=quality)
        img_data = base64.b64encode(buffer.getvalue()).decode()
        
        logger.info(f"Screenshot captured: {img.width}x{img.height}")
        
        return types.ImageContent(
            type="image",
            data=img_data,
            mimeType="image/png"
        )
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        raise

@mcp.tool()
def move_mouse(x: int, y: int, duration: float = 0.5) -> str:
    """
    Move mouse to specific coordinates.
    
    Args:
        x: X coordinate
        y: Y coordinate
        duration: Movement duration in seconds
    
    Returns:
        Confirmation message
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        logger.info(f"Mouse moved to ({x}, {y})")
        return f"Moved mouse to ({x}, {y})"
    except Exception as e:
        logger.error(f"Mouse move error: {e}")
        raise

@mcp.tool()
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
        clicks: Number of clicks
        interval: Interval between clicks
    
    Returns:
        Confirmation message
    """
    try:
        if x is not None and y is not None:
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
            logger.info(f"Clicked {button} at ({x}, {y})")
            return f"Clicked {button} button at ({x}, {y})"
        else:
            pyautogui.click(clicks=clicks, interval=interval, button=button)
            pos = pyautogui.position()
            logger.info(f"Clicked {button} at current position ({pos.x}, {pos.y})")
            return f"Clicked {button} button at current position ({pos.x}, {pos.y})"
    except Exception as e:
        logger.error(f"Click error: {e}")
        raise

@mcp.tool()
def type_text(text: str, interval: float = 0.05) -> str:
    """
    Type text using keyboard.
    
    Args:
        text: Text to type
        interval: Interval between keystrokes
    
    Returns:
        Confirmation message
    """
    try:
        pyautogui.typewrite(text, interval=interval)
        logger.info(f"Typed text: {text[:50]}...")
        return f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}"
    except Exception as e:
        logger.error(f"Type error: {e}")
        raise

@mcp.tool()
def press_key(key: str, modifiers: list[str] = []) -> str:
    """
    Press a key or key combination.
    
    Args:
        key: Key to press (e.g., 'enter', 'tab', 'escape')
        modifiers: Modifier keys (e.g., ['ctrl', 'alt', 'shift'])
    
    Returns:
        Confirmation message
    """
    try:
        if modifiers:
            keys = modifiers + [key]
            pyautogui.hotkey(*keys)
            logger.info(f"Pressed {'+'.join(keys)}")
            return f"Pressed {'+'.join(keys)}"
        else:
            pyautogui.press(key)
            logger.info(f"Pressed {key}")
            return f"Pressed {key}"
    except Exception as e:
        logger.error(f"Key press error: {e}")
        raise

@mcp.tool()
def get_screen_size(monitor: int = 0) -> dict:
    """
    Get screen dimensions.
    
    Args:
        monitor: Monitor index (0 for primary)
    
    Returns:
        Screen dimensions as dict
    """
    try:
        monitors = screenshotter.monitors
        if monitor >= len(monitors):
            raise ValueError(f"Monitor {monitor} not found")
        
        mon = monitors[monitor]
        return {
            "width": mon["width"],
            "height": mon["height"],
            "left": mon["left"],
            "top": mon["top"]
        }
    except Exception as e:
        logger.error(f"Screen size error: {e}")
        raise

@mcp.tool()
def get_mouse_position() -> dict:
    """
    Get current mouse position.
    
    Returns:
        Mouse position as dict
    """
    try:
        pos = pyautogui.position()
        return {"x": pos.x, "y": pos.y}
    except Exception as e:
        logger.error(f"Mouse position error: {e}")
        raise

# Resource for server status
@mcp.resource("server://status")
def get_server_status() -> str:
    """
    Get server status information.
    
    Returns:
        Server status as JSON string
    """
    return json.dumps({
        "name": "remote-computer-control",
        "version": "1.0.0",
        "transport": "SSE",
        "display": os.environ.get("DISPLAY", "none"),
        "monitors": len(screenshotter.monitors)
    }, indent=2)

# Main entry point
if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    
    logger.info(f"Starting MCP SSE Server on {host}:{port}")
    logger.info("SSE endpoint will be available at /sse")
    
    # Create Starlette app with the SSE server mounted
    app = Starlette(
        routes=[
            Mount("/", app=mcp.sse_app()),
        ]
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )