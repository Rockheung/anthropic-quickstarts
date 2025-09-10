#!/usr/bin/env python3
"""
MCP HTTP Bridge Server
Provides HTTP/SSE transport for MCP servers
Implements MCP protocol 1.0.0 over HTTP
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from aiohttp import web
from aiohttp_sse import sse_response
import pyautogui
import mss
from PIL import Image
import base64
import io

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

class MCPHTTPBridge:
    def __init__(self, server_type: str, port: int):
        self.server_type = server_type  # "hid" or "screenshot"
        self.port = port
        self.server_info = {
            "name": f"{server_type}-mcp-server",
            "version": "1.0.0"
        }
        self.protocol_version = "1.0.0"
        
        # Initialize based on server type
        if server_type == "hid":
            self.screen_width, self.screen_height = pyautogui.size()
            logger.info(f"HID Server - Screen size: {self.screen_width}x{self.screen_height}")
        elif server_type == "screenshot":
            self.sct = mss.mss()
            self.monitor = self.sct.monitors[0]
            logger.info(f"Screenshot Server - Monitor: {self.monitor}")
        
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools based on server type"""
        if self.server_type == "hid":
            return [
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
                }
            ]
        elif self.server_type == "screenshot":
            return [
                {
                    "name": "take_screenshot",
                    "description": "Take a screenshot of the entire screen or a specific region",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "region": {
                                "type": "object",
                                "description": "Optional region to capture",
                                "properties": {
                                    "left": {"type": "integer"},
                                    "top": {"type": "integer"},
                                    "width": {"type": "integer"},
                                    "height": {"type": "integer"}
                                }
                            },
                            "return_base64": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to return base64 encoded image"
                            }
                        }
                    }
                },
                {
                    "name": "get_screen_info",
                    "description": "Get information about the screen dimensions",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        return []
    
    async def execute_hid_tool(self, tool_name: str, args: Dict[str, Any]) -> List[Dict[str, Any]]:
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
    
    async def execute_screenshot_tool(self, tool_name: str, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute screenshot tool"""
        try:
            if tool_name == "take_screenshot":
                region = args.get("region")
                return_base64 = args.get("return_base64", True)
                
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
                
                # Return base64 if requested
                if return_base64:
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    base64_image = base64.b64encode(buffer.getvalue()).decode()
                    
                    results.append({
                        "type": "image",
                        "data": base64_image,
                        "mimeType": "image/png"
                    })
                    
                    results.append({
                        "type": "text",
                        "text": f"Screenshot captured: {screenshot.size[0]}x{screenshot.size[1]}"
                    })
                
                return results
            
            elif tool_name == "get_screen_info":
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
                
                return [{
                    "type": "text",
                    "text": json.dumps(info, indent=2)
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
                        "protocolVersion": self.protocol_version,
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": self.server_info
                    }
                }
            
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": self.get_tools()
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                if self.server_type == "hid":
                    result = await self.execute_hid_tool(tool_name, tool_args)
                elif self.server_type == "screenshot":
                    result = await self.execute_screenshot_tool(tool_name, tool_args)
                else:
                    result = [{"type": "text", "text": "Unknown server type"}]
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": result
                    }
                }
            
            elif method == "notifications/initialized":
                # Client notification that initialization is complete
                response = None  # No response for notifications
            
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            if response:
                return web.json_response(response)
            else:
                return web.Response(status=204)  # No content for notifications
                
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
    
    async def handle_mcp_sse(self, request: web.Request):
        """Handle MCP Server-Sent Events endpoint"""
        async with sse_response(request) as resp:
            # Send initial connection message
            await resp.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "connection.init",
                "params": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {
                        "tools": True
                    },
                    "serverInfo": self.server_info
                }
            }))
            
            # Keep connection alive
            while True:
                await asyncio.sleep(30)
                await resp.send(json.dumps({"type": "ping"}))
    
    async def health_check(self, request: web.Request):
        """Health check endpoint"""
        try:
            status = {
                "status": "healthy",
                "server": self.server_info["name"],
                "version": self.server_info["version"],
                "protocol": self.protocol_version,
                "display": DISPLAY
            }
            
            if self.server_type == "hid":
                x, y = pyautogui.position()
                status["mouse_position"] = {"x": x, "y": y}
                status["screen_size"] = {
                    "width": self.screen_width,
                    "height": self.screen_height
                }
            elif self.server_type == "screenshot":
                status["monitor"] = {
                    "width": self.monitor["width"],
                    "height": self.monitor["height"]
                }
            
            return web.json_response(status)
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
    
    async def start(self):
        """Start the HTTP server"""
        app = self.create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        
        logger.info(f"Starting {self.server_type.upper()} MCP HTTP Bridge on port {self.port}")
        logger.info(f"MCP endpoint: http://0.0.0.0:{self.port}/mcp")
        logger.info(f"SSE endpoint: http://0.0.0.0:{self.port}/mcp/sse")
        logger.info(f"Using DISPLAY: {DISPLAY}")
        
        await site.start()
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            await runner.cleanup()

async def main():
    """Main entry point"""
    # Determine which server to run based on port or environment variable
    server_type = os.environ.get('MCP_SERVER_TYPE', 'hid')
    
    if server_type == 'hid':
        port = int(os.environ.get('HID_MCP_PORT', 8081))
    elif server_type == 'screenshot':
        port = int(os.environ.get('SCREENSHOT_MCP_PORT', 8080))
    else:
        logger.error(f"Unknown server type: {server_type}")
        sys.exit(1)
    
    server = MCPHTTPBridge(server_type=server_type, port=port)
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())