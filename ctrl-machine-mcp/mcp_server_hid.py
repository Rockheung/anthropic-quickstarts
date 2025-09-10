#!/usr/bin/env python3
"""
MCP Server for HID Input Control
Implements Model Context Protocol 1.0.0 specification
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import pyautogui
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

# Configure PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

class HIDInputMCPServer:
    def __init__(self):
        self.server = Server("hid-input-mcp")
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen size: {self.screen_width}x{self.screen_height}")
        
        # Register handlers
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup MCP protocol handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Return list of available tools"""
            return [
                Tool(
                    name="move_mouse",
                    description="Move mouse to specified coordinates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "X coordinate"},
                            "y": {"type": "integer", "description": "Y coordinate"},
                            "duration": {"type": "number", "default": 0.5, "description": "Movement duration in seconds"}
                        },
                        "required": ["x", "y"]
                    }
                ),
                Tool(
                    name="click_mouse",
                    description="Click mouse at specified coordinates or current position",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "X coordinate (optional)"},
                            "y": {"type": "integer", "description": "Y coordinate (optional)"},
                            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                            "clicks": {"type": "integer", "default": 1, "description": "Number of clicks"}
                        }
                    }
                ),
                Tool(
                    name="type_text",
                    description="Type text using keyboard",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to type"},
                            "interval": {"type": "number", "default": 0.05, "description": "Interval between keystrokes"}
                        },
                        "required": ["text"]
                    }
                ),
                Tool(
                    name="press_key",
                    description="Press a specific key or key combination",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "description": "Key to press (e.g., 'enter', 'tab', 'ctrl+a')"}
                        },
                        "required": ["key"]
                    }
                ),
                Tool(
                    name="get_mouse_position",
                    description="Get current mouse position",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="drag_mouse",
                    description="Drag mouse from one position to another",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_x": {"type": "integer", "description": "Start X coordinate"},
                            "start_y": {"type": "integer", "description": "Start Y coordinate"},
                            "end_x": {"type": "integer", "description": "End X coordinate"},
                            "end_y": {"type": "integer", "description": "End Y coordinate"},
                            "duration": {"type": "number", "default": 1.0, "description": "Drag duration"},
                            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
                        },
                        "required": ["start_x", "start_y", "end_x", "end_y"]
                    }
                ),
                Tool(
                    name="scroll",
                    description="Scroll the mouse wheel",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "clicks": {"type": "integer", "default": 3, "description": "Number of scroll clicks (positive=up, negative=down)"},
                            "x": {"type": "integer", "description": "X coordinate (optional)"},
                            "y": {"type": "integer", "description": "Y coordinate (optional)"}
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute tool and return results"""
            try:
                if name == "move_mouse":
                    x = arguments.get("x", 0)
                    y = arguments.get("y", 0)
                    duration = arguments.get("duration", 0.5)
                    
                    x = max(0, min(x, self.screen_width - 1))
                    y = max(0, min(y, self.screen_height - 1))
                    
                    pyautogui.moveTo(x, y, duration=duration)
                    current_x, current_y = pyautogui.position()
                    
                    return [TextContent(
                        type="text",
                        text=f"Mouse moved to ({current_x}, {current_y})"
                    )]
                
                elif name == "click_mouse":
                    x = arguments.get("x")
                    y = arguments.get("y")
                    button = arguments.get("button", "left")
                    clicks = arguments.get("clicks", 1)
                    
                    if x is not None and y is not None:
                        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
                    else:
                        pyautogui.click(button=button, clicks=clicks)
                    
                    current_x, current_y = pyautogui.position()
                    return [TextContent(
                        type="text",
                        text=f"Clicked {button} button {clicks} time(s) at ({current_x}, {current_y})"
                    )]
                
                elif name == "type_text":
                    text = arguments.get("text", "")
                    interval = arguments.get("interval", 0.05)
                    
                    pyautogui.typewrite(text, interval=interval)
                    
                    return [TextContent(
                        type="text",
                        text=f"Typed {len(text)} characters"
                    )]
                
                elif name == "press_key":
                    key = arguments.get("key", "")
                    
                    if '+' in key:
                        keys = key.split('+')
                        pyautogui.hotkey(*keys)
                    else:
                        pyautogui.press(key)
                    
                    return [TextContent(
                        type="text",
                        text=f"Pressed key: {key}"
                    )]
                
                elif name == "get_mouse_position":
                    x, y = pyautogui.position()
                    
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "x": x,
                            "y": y,
                            "screen_width": self.screen_width,
                            "screen_height": self.screen_height
                        }, indent=2)
                    )]
                
                elif name == "drag_mouse":
                    start_x = arguments.get("start_x", 0)
                    start_y = arguments.get("start_y", 0)
                    end_x = arguments.get("end_x", 0)
                    end_y = arguments.get("end_y", 0)
                    duration = arguments.get("duration", 1.0)
                    button = arguments.get("button", "left")
                    
                    pyautogui.moveTo(start_x, start_y, duration=0.5)
                    pyautogui.dragTo(end_x, end_y, duration=duration, button=button)
                    
                    return [TextContent(
                        type="text",
                        text=f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"
                    )]
                
                elif name == "scroll":
                    clicks = arguments.get("clicks", 3)
                    x = arguments.get("x")
                    y = arguments.get("y")
                    
                    if x is not None and y is not None:
                        pyautogui.scroll(clicks, x=x, y=y)
                    else:
                        pyautogui.scroll(clicks)
                    
                    return [TextContent(
                        type="text",
                        text=f"Scrolled {clicks} clicks"
                    )]
                
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
                    server_name="hid-input-mcp",
                    server_version="1.0.0"
                )
            )

async def main():
    """Main entry point"""
    server = HIDInputMCPServer()
    await server.run()

if __name__ == "__main__":
    import mcp.server.stdio
    asyncio.run(main())