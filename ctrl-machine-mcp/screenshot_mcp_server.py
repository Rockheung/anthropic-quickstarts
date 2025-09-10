#!/usr/bin/env python3
"""
MCP-compliant HTTP Server for Screenshots
Implements proper MCP protocol over HTTP/SSE
"""

import asyncio
import base64
import io
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from aiohttp import web
from aiohttp_sse import sse_response
import mss
from PIL import Image
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ImageContent, ServerCapabilities, ToolsCapability

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure we're using the container's display
DISPLAY = os.environ.get('DISPLAY', ':99')
os.environ['DISPLAY'] = DISPLAY

# Initialize MCP server
mcp_server = Server("screenshot-mcp-server")

class ScreenshotMCPServer:
    def __init__(self, port: int = 8080):
        self.port = port
        self.screenshots_dir = "/app/screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
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
                        "name": "screenshot-mcp-server",
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
                            "name": "screenshot-mcp-server",
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
                                "name": "capture_screenshot",
                                "description": "Capture a screenshot from the virtual display",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "mode": {
                                            "type": "string",
                                            "enum": ["full_screen", "active_window"],
                                            "default": "full_screen"
                                        }
                                    }
                                }
                            },
                            {
                                "name": "get_display_info",
                                "description": "Get information about the virtual display",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {}
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                if tool_name == "capture_screenshot":
                    result = await self.capture_screenshot(tool_args)
                elif tool_name == "get_display_info":
                    result = await self.get_display_info()
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
                
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
    
    async def capture_screenshot(self, args: Dict[str, Any]) -> list:
        """Capture screenshot and return MCP-formatted response"""
        try:
            mode = args.get("mode", "full_screen")
            
            with mss.mss(display=DISPLAY) as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                screenshot = sct.grab(monitor)
                
                img = Image.frombytes(
                    'RGB',
                    (screenshot.width, screenshot.height),
                    screenshot.bgra,
                    'raw',
                    'BGRX'
                )
                
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"screenshot_{timestamp}.png"
                filepath = os.path.join(self.screenshots_dir, filename)
                img.save(filepath)
                
                # Convert to base64
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                return [
                    {
                        "type": "text",
                        "text": f"Screenshot captured: {mode}\nSize: {img.width}x{img.height}\nTimestamp: {timestamp}"
                    },
                    {
                        "type": "image",
                        "data": img_base64,
                        "mimeType": "image/png"
                    }
                ]
                
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return [{
                "type": "text",
                "text": f"Error capturing screenshot: {str(e)}"
            }]
    
    async def get_display_info(self) -> list:
        """Get display information"""
        try:
            with mss.mss(display=DISPLAY) as sct:
                monitors = sct.monitors
                
                return [{
                    "type": "text",
                    "text": json.dumps({
                        "display": DISPLAY,
                        "monitors": monitors,
                        "primary_monitor": monitors[1] if len(monitors) > 1 else monitors[0]
                    }, indent=2)
                }]
        except Exception as e:
            return [{
                "type": "text",
                "text": f"Error getting display info: {str(e)}"
            }]
    
    async def health_check(self, request: web.Request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "server": "screenshot-mcp-server",
            "display": DISPLAY,
            "mcp_protocol": "0.1.0"
        })
    
    def create_app(self) -> web.Application:
        """Create the aiohttp application"""
        app = web.Application()
        
        # MCP endpoints
        app.router.add_post('/mcp', self.handle_mcp_request)
        app.router.add_get('/mcp/sse', self.handle_mcp_sse)
        
        # Health check
        app.router.add_get('/health', self.health_check)
        
        # Legacy endpoints for backward compatibility
        app.router.add_post('/screenshot', self.legacy_screenshot)
        app.router.add_get('/display_info', self.legacy_display_info)
        
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
    
    async def legacy_screenshot(self, request: web.Request):
        """Legacy screenshot endpoint for compatibility"""
        try:
            data = await request.json() if request.body_exists else {}
            result = await self.capture_screenshot(data)
            
            # Extract base64 image from MCP response
            image_data = None
            for item in result:
                if item.get("type") == "image":
                    image_data = item.get("data")
                    break
            
            return web.json_response({
                "success": True,
                "image_base64": image_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def legacy_display_info(self, request: web.Request):
        """Legacy display info endpoint"""
        try:
            result = await self.get_display_info()
            text_content = result[0].get("text") if result else "{}"
            return web.json_response(json.loads(text_content))
        except Exception as e:
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def start(self):
        """Start the HTTP server"""
        app = self.create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        
        logger.info(f"Starting Screenshot MCP Server on port {self.port}")
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
    port = int(os.environ.get('SCREENSHOT_MCP_PORT', 8080))
    server = ScreenshotMCPServer(port=port)
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())