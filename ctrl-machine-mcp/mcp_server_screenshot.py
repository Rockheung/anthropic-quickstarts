#!/usr/bin/env python3
"""
MCP Server for Screenshot Capture
Implements Model Context Protocol 1.0.0 specification
"""

import asyncio
import base64
import io
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import mss
from PIL import Image
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure we're using the container's display
DISPLAY = os.environ.get('DISPLAY', ':99')
os.environ['DISPLAY'] = DISPLAY

class ScreenshotMCPServer:
    def __init__(self):
        self.server = Server("screenshot-mcp")
        self.screenshots_dir = Path("/app/screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize mss for screenshot capture
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[0]  # Full screen
        logger.info(f"Primary monitor: {self.monitor}")
        
        # Register handlers
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup MCP protocol handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Return list of available tools"""
            return [
                Tool(
                    name="take_screenshot",
                    description="Take a screenshot of the entire screen or a specific region",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "region": {
                                "type": "object",
                                "description": "Optional region to capture",
                                "properties": {
                                    "left": {"type": "integer", "description": "Left coordinate"},
                                    "top": {"type": "integer", "description": "Top coordinate"},
                                    "width": {"type": "integer", "description": "Width of region"},
                                    "height": {"type": "integer", "description": "Height of region"}
                                }
                            },
                            "save_to_file": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to save screenshot to file"
                            },
                            "return_base64": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to return base64 encoded image"
                            }
                        }
                    }
                ),
                Tool(
                    name="capture_window",
                    description="Capture a screenshot of a specific window by title",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "window_title": {
                                "type": "string",
                                "description": "Title or partial title of the window to capture"
                            },
                            "save_to_file": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to save screenshot to file"
                            },
                            "return_base64": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to return base64 encoded image"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_screen_info",
                    description="Get information about the screen dimensions",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="list_windows",
                    description="List all visible windows",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="capture_element",
                    description="Capture a screenshot of a specific element at coordinates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "X coordinate of element"},
                            "y": {"type": "integer", "description": "Y coordinate of element"},
                            "width": {"type": "integer", "description": "Width of element"},
                            "height": {"type": "integer", "description": "Height of element"},
                            "padding": {
                                "type": "integer",
                                "default": 0,
                                "description": "Additional padding around element"
                            }
                        },
                        "required": ["x", "y", "width", "height"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[Any]:
            """Execute tool and return results"""
            try:
                if name == "take_screenshot":
                    region = arguments.get("region")
                    save_to_file = arguments.get("save_to_file", True)
                    return_base64 = arguments.get("return_base64", True)
                    
                    # Determine capture area
                    if region:
                        capture_area = {
                            "left": region.get("left", 0),
                            "top": region.get("top", 0),
                            "width": region.get("width", self.monitor["width"]),
                            "height": region.get("height", self.monitor["height"])
                        }
                    else:
                        capture_area = self.monitor
                    
                    # Capture screenshot
                    screenshot = self.sct.grab(capture_area)
                    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                    
                    results = []
                    
                    # Save to file if requested
                    if save_to_file:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = self.screenshots_dir / f"screenshot_{timestamp}.png"
                        img.save(filename)
                        results.append(TextContent(
                            type="text",
                            text=f"Screenshot saved to: {filename}"
                        ))
                    
                    # Return base64 if requested
                    if return_base64:
                        buffer = io.BytesIO()
                        img.save(buffer, format="PNG")
                        base64_image = base64.b64encode(buffer.getvalue()).decode()
                        results.append(ImageContent(
                            type="image",
                            data=base64_image,
                            mimeType="image/png"
                        ))
                    
                    return results
                
                elif name == "get_screen_info":
                    info = {
                        "display": DISPLAY,
                        "monitors": []
                    }
                    
                    for i, monitor in enumerate(self.sct.monitors):
                        info["monitors"].append({
                            "index": i,
                            "left": monitor["left"],
                            "top": monitor["top"],
                            "width": monitor["width"],
                            "height": monitor["height"]
                        })
                    
                    return [TextContent(
                        type="text",
                        text=json.dumps(info, indent=2)
                    )]
                
                elif name == "capture_element":
                    x = arguments.get("x", 0)
                    y = arguments.get("y", 0)
                    width = arguments.get("width", 100)
                    height = arguments.get("height", 100)
                    padding = arguments.get("padding", 0)
                    
                    # Add padding
                    capture_area = {
                        "left": max(0, x - padding),
                        "top": max(0, y - padding),
                        "width": min(self.monitor["width"], width + 2 * padding),
                        "height": min(self.monitor["height"], height + 2 * padding)
                    }
                    
                    # Capture screenshot
                    screenshot = self.sct.grab(capture_area)
                    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                    
                    # Save and return
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = self.screenshots_dir / f"element_{timestamp}.png"
                    img.save(filename)
                    
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    base64_image = base64.b64encode(buffer.getvalue()).decode()
                    
                    return [
                        TextContent(
                            type="text",
                            text=f"Element captured: {width}x{height} at ({x}, {y})"
                        ),
                        ImageContent(
                            type="image",
                            data=base64_image,
                            mimeType="image/png"
                        )
                    ]
                
                elif name == "list_windows":
                    # This would require wmctrl or similar tool
                    # For now, return a simple message
                    return [TextContent(
                        type="text",
                        text="Window listing requires additional tools (wmctrl) to be installed"
                    )]
                
                elif name == "capture_window":
                    # This would require window manager integration
                    # For now, capture full screen
                    screenshot = self.sct.grab(self.monitor)
                    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = self.screenshots_dir / f"window_{timestamp}.png"
                    img.save(filename)
                    
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    base64_image = base64.b64encode(buffer.getvalue()).decode()
                    
                    return [
                        TextContent(
                            type="text",
                            text=f"Screenshot saved (full screen as window capture needs wmctrl): {filename}"
                        ),
                        ImageContent(
                            type="image",
                            data=base64_image,
                            mimeType="image/png"
                        )
                    ]
                
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
                    
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    async def run(self):
        """Run the MCP server"""
        # Use stdio transport for MCP
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="screenshot-mcp",
                    server_version="1.0.0"
                )
            )

async def main():
    """Main entry point"""
    server = ScreenshotMCPServer()
    await server.run()

if __name__ == "__main__":
    import mcp.server.stdio
    asyncio.run(main())