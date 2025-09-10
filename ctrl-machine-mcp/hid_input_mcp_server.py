#!/usr/bin/env python3
"""
MCP-compliant HTTP Server for HID Input
Implements proper MCP protocol over HTTP/SSE
"""

import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Dict, Optional

from aiohttp import web
from aiohttp_sse import sse_response
import pyautogui
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities, ToolsCapability

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

# Initialize MCP server
mcp_server = Server("hid-input-mcp-server")

class HIDInputMCPServer:
    def __init__(self, port: int = 8081):
        self.port = port
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen size: {self.screen_width}x{self.screen_height}")
        
    async def handle_mcp_sse(self, request: web.Request):
        """Handle MCP Server-Sent Events endpoint"""
        async with sse_response(request) as resp:
            # Send initial connection message
            await resp.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "connection.init",
                "params": {
                    "protocolVersion": "1.0.0",
                    "capabilities": {
                        "tools": True
                    },
                    "serverInfo": {
                        "name": "hid-input-mcp-server",
                        "version": "1.0.0"
                    }
                }
            }))
            
            # Keep connection alive
            while True:
                await asyncio.sleep(30)
                await resp.send(json.dumps({"type": "ping"}))
    
    async def handle_mcp_request(self, request: web.Request):
        """Handle MCP JSON-RPC requests"""
        try:
            data = await request.json()
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")
            
            logger.info(f"MCP request: {method}")
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "1.0.0",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "hid-input-mcp-server",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "move_mouse",
                                "description": "Move mouse to specified coordinates",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "integer", "description": "X coordinate"},
                                        "y": {"type": "integer", "description": "Y coordinate"},
                                        "duration": {"type": "number", "default": 0.5, "description": "Movement duration in seconds"}
                                    },
                                    "required": ["x", "y"]
                                }
                            },
                            {
                                "name": "click_mouse",
                                "description": "Click mouse at specified coordinates or current position",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "integer", "description": "X coordinate (optional)"},
                                        "y": {"type": "integer", "description": "Y coordinate (optional)"},
                                        "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                                        "clicks": {"type": "integer", "default": 1, "description": "Number of clicks"}
                                    }
                                }
                            },
                            {
                                "name": "type_text",
                                "description": "Type text using keyboard",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string", "description": "Text to type"},
                                        "interval": {"type": "number", "default": 0.05, "description": "Interval between keystrokes"}
                                    },
                                    "required": ["text"]
                                }
                            },
                            {
                                "name": "press_key",
                                "description": "Press a specific key or key combination",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "key": {"type": "string", "description": "Key to press (e.g., 'enter', 'tab', 'ctrl+a')"}
                                    },
                                    "required": ["key"]
                                }
                            },
                            {
                                "name": "get_mouse_position",
                                "description": "Get current mouse position",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {}
                                }
                            },
                            {
                                "name": "drag_mouse",
                                "description": "Drag mouse from one position to another",
                                "inputSchema": {
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
                            },
                            {
                                "name": "scroll",
                                "description": "Scroll the mouse wheel",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "clicks": {"type": "integer", "default": 3, "description": "Number of scroll clicks (positive=up, negative=down)"},
                                        "x": {"type": "integer", "description": "X coordinate (optional)"},
                                        "y": {"type": "integer", "description": "Y coordinate (optional)"}
                                    }
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                result = await self.execute_tool(tool_name, tool_args)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": result
                    }
                }
            
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return web.json_response(response)
            
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "id": data.get("id") if 'data' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            })
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> list:
        """Execute HID input tool"""
        try:
            if tool_name == "move_mouse":
                x = args.get("x", 0)
                y = args.get("y", 0)
                duration = args.get("duration", 0.5)
                
                x = max(0, min(x, self.screen_width - 1))
                y = max(0, min(y, self.screen_height - 1))
                
                pyautogui.moveTo(x, y, duration=duration)
                current_x, current_y = pyautogui.position()
                
                return [{
                    "type": "text",
                    "text": f"Mouse moved to ({current_x}, {current_y})"
                }]
            
            elif tool_name == "click_mouse":
                x = args.get("x")
                y = args.get("y")
                button = args.get("button", "left")
                clicks = args.get("clicks", 1)
                
                if x is not None and y is not None:
                    pyautogui.click(x=x, y=y, button=button, clicks=clicks)
                else:
                    pyautogui.click(button=button, clicks=clicks)
                
                current_x, current_y = pyautogui.position()
                return [{
                    "type": "text",
                    "text": f"Clicked {button} button {clicks} time(s) at ({current_x}, {current_y})"
                }]
            
            elif tool_name == "type_text":
                text = args.get("text", "")
                interval = args.get("interval", 0.05)
                
                pyautogui.typewrite(text, interval=interval)
                
                return [{
                    "type": "text",
                    "text": f"Typed {len(text)} characters"
                }]
            
            elif tool_name == "press_key":
                key = args.get("key", "")
                
                if '+' in key:
                    keys = key.split('+')
                    pyautogui.hotkey(*keys)
                else:
                    pyautogui.press(key)
                
                return [{
                    "type": "text",
                    "text": f"Pressed key: {key}"
                }]
            
            elif tool_name == "get_mouse_position":
                x, y = pyautogui.position()
                
                return [{
                    "type": "text",
                    "text": json.dumps({
                        "x": x,
                        "y": y,
                        "screen_width": self.screen_width,
                        "screen_height": self.screen_height
                    }, indent=2)
                }]
            
            elif tool_name == "drag_mouse":
                start_x = args.get("start_x", 0)
                start_y = args.get("start_y", 0)
                end_x = args.get("end_x", 0)
                end_y = args.get("end_y", 0)
                duration = args.get("duration", 1.0)
                button = args.get("button", "left")
                
                pyautogui.moveTo(start_x, start_y, duration=0.5)
                pyautogui.dragTo(end_x, end_y, duration=duration, button=button)
                
                return [{
                    "type": "text",
                    "text": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"
                }]
            
            elif tool_name == "scroll":
                clicks = args.get("clicks", 3)
                x = args.get("x")
                y = args.get("y")
                
                if x is not None and y is not None:
                    pyautogui.scroll(clicks, x=x, y=y)
                else:
                    pyautogui.scroll(clicks)
                
                return [{
                    "type": "text",
                    "text": f"Scrolled {clicks} clicks"
                }]
            
            else:
                return [{
                    "type": "text",
                    "text": f"Unknown tool: {tool_name}"
                }]
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return [{
                "type": "text",
                "text": f"Error: {str(e)}"
            }]
    
    async def health_check(self, request: web.Request):
        """Health check endpoint"""
        try:
            x, y = pyautogui.position()
            return web.json_response({
                "status": "healthy",
                "server": "hid-input-mcp-server",
                "display": DISPLAY,
                "mcp_protocol": "0.1.0",
                "mouse_position": {"x": x, "y": y},
                "screen_size": {
                    "width": self.screen_width,
                    "height": self.screen_height
                }
            })
        except Exception as e:
            return web.json_response({
                "status": "unhealthy",
                "error": str(e)
            }, status=503)
    
    def create_app(self) -> web.Application:
        """Create the aiohttp application"""
        app = web.Application()
        
        # MCP endpoints
        app.router.add_post('/mcp', self.handle_mcp_request)
        app.router.add_get('/mcp/sse', self.handle_mcp_sse)
        
        # Health check
        app.router.add_get('/health', self.health_check)
        
        # Legacy endpoints for backward compatibility
        app.router.add_post('/move', self.legacy_move)
        app.router.add_post('/click', self.legacy_click)
        app.router.add_post('/type', self.legacy_type)
        app.router.add_post('/press', self.legacy_press)
        app.router.add_get('/position', self.legacy_position)
        
        # Add CORS middleware
        async def cors_middleware(app, handler):
            async def middleware_handler(request):
                if request.method == 'OPTIONS':
                    response = web.Response()
                else:
                    response = await handler(request)
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                return response
            return middleware_handler
        
        app.middlewares.append(cors_middleware)
        
        return app
    
    async def legacy_move(self, request: web.Request):
        """Legacy move endpoint"""
        try:
            data = await request.json()
            result = await self.execute_tool("move_mouse", data)
            return web.json_response({"success": True, "message": result[0]["text"]})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)
    
    async def legacy_click(self, request: web.Request):
        """Legacy click endpoint"""
        try:
            data = await request.json()
            result = await self.execute_tool("click_mouse", data)
            return web.json_response({"success": True, "message": result[0]["text"]})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)
    
    async def legacy_type(self, request: web.Request):
        """Legacy type endpoint"""
        try:
            data = await request.json()
            result = await self.execute_tool("type_text", data)
            return web.json_response({"success": True, "message": result[0]["text"]})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)
    
    async def legacy_press(self, request: web.Request):
        """Legacy press endpoint"""
        try:
            data = await request.json()
            result = await self.execute_tool("press_key", data)
            return web.json_response({"success": True, "message": result[0]["text"]})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)
    
    async def legacy_position(self, request: web.Request):
        """Legacy position endpoint"""
        try:
            result = await self.execute_tool("get_mouse_position", {})
            return web.json_response(json.loads(result[0]["text"]))
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def start(self):
        """Start the HTTP server"""
        app = self.create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        
        logger.info(f"Starting HID Input MCP Server on port {self.port}")
        logger.info(f"MCP endpoint: http://0.0.0.0:{self.port}/mcp")
        logger.info(f"SSE endpoint: http://0.0.0.0:{self.port}/mcp/sse")
        logger.info(f"Using DISPLAY: {DISPLAY}")
        logger.info(f"Screen size: {self.screen_width}x{self.screen_height}")
        
        await site.start()
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            await runner.cleanup()

async def main():
    """Main entry point"""
    port = int(os.environ.get('HID_MCP_PORT', 8081))
    server = HIDInputMCPServer(port=port)
    await server.start()

if __name__ == "__main__":
    # Force PyAutoGUI to use the X11 backend
    os.environ['DISPLAY'] = DISPLAY
    pyautogui.screenshot = None  # Disable screenshot functionality
    
    asyncio.run(main())