#!/usr/bin/env python3
"""HTTP-based Screenshot MCP Server for Docker deployment."""

import asyncio
import base64
import io
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiohttp import web
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ImageContent, ServerCapabilities

import PIL.Image
import pyautogui
import mss
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("screenshot-mcp-http")

# Screenshot storage
SCREENSHOT_DIR = "/app/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def capture_screenshot(region: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Capture a screenshot and return base64 encoded image."""
    try:
        with mss.mss() as sct:
            if region:
                monitor = {
                    "top": region.get("top", 0),
                    "left": region.get("left", 0),
                    "width": region.get("width", 1920),
                    "height": region.get("height", 1080)
                }
            else:
                monitor = sct.monitors[0]  # Full screen
            
            screenshot = sct.grab(monitor)
            img = PIL.Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(SCREENSHOT_DIR, filename)
            img.save(filepath)
            
            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return {
                "success": True,
                "image": img_base64,
                "filename": filename,
                "dimensions": {"width": img.width, "height": img.height},
                "timestamp": timestamp
            }
    except Exception as e:
        logger.error(f"Screenshot capture failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# HTTP handlers
async def handle_capture(request):
    """Handle screenshot capture requests."""
    try:
        data = await request.json() if request.body_exists else {}
        region = data.get("region")
        result = await capture_screenshot(region)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_list_tools(request):
    """List available tools."""
    tools = [
        {
            "name": "capture_screenshot",
            "description": "Capture a screenshot of the screen",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "object",
                        "properties": {
                            "top": {"type": "integer"},
                            "left": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"}
                        },
                        "description": "Optional region to capture"
                    }
                }
            }
        }
    ]
    return web.json_response({"tools": tools})

async def handle_health(request):
    """Health check endpoint."""
    return web.json_response({"status": "healthy", "server": "screenshot-mcp-http"})

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
            if tool_name == "capture_screenshot":
                result = await capture_screenshot(params.get("arguments", {}).get("region"))
                return web.json_response({
                    "content": [{
                        "type": "image",
                        "data": result.get("image"),
                        "mimeType": "image/png"
                    }] if result.get("success") else [{
                        "type": "text",
                        "text": f"Error: {result.get('error')}"
                    }]
                })
        
        return web.json_response({"error": "Unknown method"}, status=400)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# Create web application
app = web.Application()
app.router.add_post('/capture', handle_capture)
app.router.add_get('/tools', handle_list_tools)
app.router.add_get('/health', handle_health)
app.router.add_post('/mcp', handle_mcp_request)

if __name__ == "__main__":
    port = int(os.environ.get("SCREENSHOT_MCP_PORT", "8080"))
    logger.info(f"Starting Screenshot MCP HTTP server on port {port}")
    web.run_app(app, host="0.0.0.0", port=port)