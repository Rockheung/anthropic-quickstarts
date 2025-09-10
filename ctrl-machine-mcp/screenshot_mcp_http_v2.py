#!/usr/bin/env python3
"""
Screenshot MCP HTTP Server for Docker Container
Captures screenshots from the virtual display inside the container
"""

import asyncio
import base64
import io
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

from aiohttp import web
from PIL import Image
import mss
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure we're using the container's display
DISPLAY = os.environ.get('DISPLAY', ':99')
os.environ['DISPLAY'] = DISPLAY
logger.info(f"Using DISPLAY: {DISPLAY}")

class ScreenshotServer:
    def __init__(self, port: int = 8080):
        self.port = port
        self.screenshots_dir = "/app/screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Initialize mss for the specific display
        self.sct = mss.mss(display=DISPLAY)
        
        # Get monitor info
        self.monitors = self.sct.monitors
        self.primary_monitor = self.monitors[1] if len(self.monitors) > 1 else self.monitors[0]
        logger.info(f"Primary monitor: {self.primary_monitor}")
        
    async def capture_screenshot(self, request: web.Request) -> web.Response:
        """Capture screenshot from container's virtual display"""
        try:
            data = await request.json() if request.body_exists else {}
            mode = data.get('mode', 'full_screen')
            
            logger.info(f"Capturing screenshot in mode: {mode}")
            
            # Capture from the virtual display
            with mss.mss(display=DISPLAY) as sct:
                # Get the primary monitor (virtual display)
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                
                # Capture the screen
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image
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
                logger.info(f"Screenshot saved to: {filepath}")
                
                # Convert to base64 for response
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                return web.json_response({
                    "success": True,
                    "mode": mode,
                    "filename": filename,
                    "filepath": filepath,
                    "width": img.width,
                    "height": img.height,
                    "display": DISPLAY,
                    "image_base64": img_base64,
                    "timestamp": timestamp
                })
                
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
                "display": DISPLAY
            }, status=500)
    
    async def get_display_info(self, request: web.Request) -> web.Response:
        """Get information about the virtual display"""
        try:
            with mss.mss(display=DISPLAY) as sct:
                monitors = sct.monitors
                
                return web.json_response({
                    "success": True,
                    "display": DISPLAY,
                    "monitors": monitors,
                    "primary_monitor": monitors[1] if len(monitors) > 1 else monitors[0]
                })
        except Exception as e:
            logger.error(f"Failed to get display info: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        try:
            # Test if we can access the display
            with mss.mss(display=DISPLAY) as sct:
                monitors = sct.monitors
                
            return web.json_response({
                "status": "healthy",
                "server": "screenshot-mcp-http-v2",
                "display": DISPLAY,
                "monitors_count": len(monitors)
            })
        except Exception as e:
            return web.json_response({
                "status": "unhealthy",
                "error": str(e)
            }, status=503)
    
    def create_app(self) -> web.Application:
        """Create the aiohttp application"""
        app = web.Application()
        
        # Add routes
        app.router.add_post('/screenshot', self.capture_screenshot)
        app.router.add_get('/display_info', self.get_display_info)
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
        
        logger.info(f"Starting Screenshot MCP HTTP Server on port {self.port}")
        logger.info(f"Using DISPLAY: {DISPLAY}")
        logger.info(f"Screenshots directory: {self.screenshots_dir}")
        
        await site.start()
        
        # Keep the server running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            await runner.cleanup()

async def main():
    """Main entry point"""
    port = int(os.environ.get('SCREENSHOT_MCP_PORT', 8080))
    server = ScreenshotServer(port=port)
    await server.start()

if __name__ == "__main__":
    # Verify X11 connection
    try:
        import subprocess
        result = subprocess.run(
            ['xdpyinfo', '-display', DISPLAY],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info(f"Successfully connected to X11 display {DISPLAY}")
        else:
            logger.warning(f"Could not verify X11 connection: {result.stderr}")
    except Exception as e:
        logger.warning(f"Could not run xdpyinfo: {e}")
    
    # Run the server
    asyncio.run(main())