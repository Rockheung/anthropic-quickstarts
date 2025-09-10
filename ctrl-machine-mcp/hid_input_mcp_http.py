#!/usr/bin/env python3
"""HTTP-based HID Input MCP Server for Docker deployment."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

from aiohttp import web
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities

import pyautogui

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure PyAutoGUI safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# Initialize MCP server
server = Server("hid-input-mcp-http")

async def click_mouse(x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
    """Perform mouse click at specified coordinates."""
    try:
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        return {
            "success": True,
            "action": "click",
            "position": {"x": x, "y": y},
            "button": button,
            "clicks": clicks
        }
    except Exception as e:
        logger.error(f"Mouse click failed: {e}")
        return {"success": False, "error": str(e)}

async def move_mouse(x: int, y: int, duration: float = 0.5) -> Dict[str, Any]:
    """Move mouse to specified coordinates."""
    try:
        pyautogui.moveTo(x=x, y=y, duration=duration)
        return {
            "success": True,
            "action": "move",
            "position": {"x": x, "y": y},
            "duration": duration
        }
    except Exception as e:
        logger.error(f"Mouse move failed: {e}")
        return {"success": False, "error": str(e)}

async def type_text(text: str, interval: float = 0.05) -> Dict[str, Any]:
    """Type text with specified interval between keystrokes."""
    try:
        pyautogui.typewrite(text, interval=interval)
        return {
            "success": True,
            "action": "type",
            "text": text,
            "interval": interval
        }
    except Exception as e:
        logger.error(f"Text typing failed: {e}")
        return {"success": False, "error": str(e)}

async def press_key(key: str, presses: int = 1) -> Dict[str, Any]:
    """Press a specific key."""
    try:
        pyautogui.press(key, presses=presses)
        return {
            "success": True,
            "action": "press",
            "key": key,
            "presses": presses
        }
    except Exception as e:
        logger.error(f"Key press failed: {e}")
        return {"success": False, "error": str(e)}

async def hotkey(*keys: str) -> Dict[str, Any]:
    """Press a hotkey combination."""
    try:
        pyautogui.hotkey(*keys)
        return {
            "success": True,
            "action": "hotkey",
            "keys": list(keys)
        }
    except Exception as e:
        logger.error(f"Hotkey failed: {e}")
        return {"success": False, "error": str(e)}

# HTTP handlers
async def handle_click(request):
    """Handle mouse click requests."""
    try:
        data = await request.json()
        result = await click_mouse(
            x=data.get("x", 0),
            y=data.get("y", 0),
            button=data.get("button", "left"),
            clicks=data.get("clicks", 1)
        )
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_move(request):
    """Handle mouse move requests."""
    try:
        data = await request.json()
        result = await move_mouse(
            x=data.get("x", 0),
            y=data.get("y", 0),
            duration=data.get("duration", 0.5)
        )
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_type(request):
    """Handle text typing requests."""
    try:
        data = await request.json()
        result = await type_text(
            text=data.get("text", ""),
            interval=data.get("interval", 0.05)
        )
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_press(request):
    """Handle key press requests."""
    try:
        data = await request.json()
        result = await press_key(
            key=data.get("key", ""),
            presses=data.get("presses", 1)
        )
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_hotkey(request):
    """Handle hotkey requests."""
    try:
        data = await request.json()
        keys = data.get("keys", [])
        result = await hotkey(*keys)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_list_tools(request):
    """List available tools."""
    tools = [
        {
            "name": "click_mouse",
            "description": "Click mouse at specified coordinates",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"]},
                    "clicks": {"type": "integer"}
                },
                "required": ["x", "y"]
            }
        },
        {
            "name": "move_mouse",
            "description": "Move mouse to specified coordinates",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "duration": {"type": "number"}
                },
                "required": ["x", "y"]
            }
        },
        {
            "name": "type_text",
            "description": "Type text with keyboard",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "interval": {"type": "number"}
                },
                "required": ["text"]
            }
        },
        {
            "name": "press_key",
            "description": "Press a specific key",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "presses": {"type": "integer"}
                },
                "required": ["key"]
            }
        },
        {
            "name": "hotkey",
            "description": "Press a hotkey combination",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["keys"]
            }
        }
    ]
    return web.json_response({"tools": tools})

async def handle_health(request):
    """Health check endpoint."""
    return web.json_response({"status": "healthy", "server": "hid-input-mcp-http"})

async def handle_mcp_request(request):
    """Handle MCP protocol requests."""
    try:
        data = await request.json()
        method = data.get("method")
        params = data.get("params", {})
        
        if method == "tools/list":
            return await handle_list_tools(request)
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            
            result = None
            if tool_name == "click_mouse":
                result = await click_mouse(args.get("x"), args.get("y"), 
                                         args.get("button", "left"), args.get("clicks", 1))
            elif tool_name == "move_mouse":
                result = await move_mouse(args.get("x"), args.get("y"), 
                                        args.get("duration", 0.5))
            elif tool_name == "type_text":
                result = await type_text(args.get("text"), args.get("interval", 0.05))
            elif tool_name == "press_key":
                result = await press_key(args.get("key"), args.get("presses", 1))
            elif tool_name == "hotkey":
                result = await hotkey(*args.get("keys", []))
            
            if result:
                return web.json_response({
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                })
        
        return web.json_response({"error": "Unknown method"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# Create web application
app = web.Application()
app.router.add_post('/click', handle_click)
app.router.add_post('/move', handle_move)
app.router.add_post('/type', handle_type)
app.router.add_post('/press', handle_press)
app.router.add_post('/hotkey', handle_hotkey)
app.router.add_get('/tools', handle_list_tools)
app.router.add_get('/health', handle_health)
app.router.add_post('/mcp', handle_mcp_request)

if __name__ == "__main__":
    port = int(os.environ.get("HID_MCP_PORT", "8081"))
    logger.info(f"Starting HID Input MCP HTTP server on port {port}")
    web.run_app(app, host="0.0.0.0", port=port)