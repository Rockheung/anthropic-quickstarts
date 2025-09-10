#!/usr/bin/env python3
"""
HID Input MCP HTTP Server for Docker Container
Controls mouse and keyboard inside the container's virtual display
"""

import asyncio
import json
import logging
import os
import sys
import subprocess
from typing import Optional, Dict, Any, List

from aiohttp import web
import pyautogui

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

# Configure PyAutoGUI for container environment
pyautogui.FAILSAFE = True  # Moving mouse to corner will abort
pyautogui.PAUSE = 0.1  # Pause between actions

class HIDInputServer:
    def __init__(self, port: int = 8081):
        self.port = port
        
        # Verify display connection
        self._verify_display()
        
        # Get screen size from the virtual display
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"Screen size: {self.screen_width}x{self.screen_height}")
        
    def _verify_display(self):
        """Verify we can connect to the X11 display"""
        try:
            # Test X11 connection
            result = subprocess.run(
                ['xdpyinfo', '-display', DISPLAY],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Successfully connected to X11 display {DISPLAY}")
                # Parse screen dimensions from xdpyinfo
                for line in result.stdout.split('\n'):
                    if 'dimensions:' in line:
                        logger.info(f"Display info: {line.strip()}")
            else:
                logger.error(f"Failed to connect to display {DISPLAY}: {result.stderr}")
                raise RuntimeError(f"Cannot connect to display {DISPLAY}")
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout connecting to display {DISPLAY}")
            raise RuntimeError(f"Timeout connecting to display {DISPLAY}")
        except Exception as e:
            logger.error(f"Error verifying display: {e}")
            # Continue anyway, PyAutoGUI might still work
    
    async def move_mouse(self, request: web.Request) -> web.Response:
        """Move mouse to specified coordinates"""
        try:
            data = await request.json()
            x = data.get('x', 0)
            y = data.get('y', 0)
            duration = data.get('duration', 0.5)
            
            # Ensure coordinates are within screen bounds
            x = max(0, min(x, self.screen_width - 1))
            y = max(0, min(y, self.screen_height - 1))
            
            logger.info(f"Moving mouse to ({x}, {y}) with duration {duration}s on display {DISPLAY}")
            
            # Move mouse using PyAutoGUI (which uses the DISPLAY env var)
            pyautogui.moveTo(x, y, duration=duration)
            
            # Get current position to verify
            current_x, current_y = pyautogui.position()
            
            return web.json_response({
                "success": True,
                "action": "move",
                "target": {"x": x, "y": y},
                "actual": {"x": current_x, "y": current_y},
                "display": DISPLAY,
                "duration": duration
            })
            
        except Exception as e:
            logger.error(f"Mouse move failed: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
                "display": DISPLAY
            }, status=500)
    
    async def click_mouse(self, request: web.Request) -> web.Response:
        """Click mouse at specified coordinates"""
        try:
            data = await request.json()
            x = data.get('x', None)
            y = data.get('y', None)
            button = data.get('button', 'left')
            clicks = data.get('clicks', 1)
            
            if x is not None and y is not None:
                # Ensure coordinates are within screen bounds
                x = max(0, min(x, self.screen_width - 1))
                y = max(0, min(y, self.screen_height - 1))
                logger.info(f"Clicking at ({x}, {y}) with {button} button, {clicks} clicks")
                pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            else:
                # Click at current position
                logger.info(f"Clicking at current position with {button} button, {clicks} clicks")
                pyautogui.click(button=button, clicks=clicks)
            
            current_x, current_y = pyautogui.position()
            
            return web.json_response({
                "success": True,
                "action": "click",
                "position": {"x": current_x, "y": current_y},
                "button": button,
                "clicks": clicks,
                "display": DISPLAY
            })
            
        except Exception as e:
            logger.error(f"Mouse click failed: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
                "display": DISPLAY
            }, status=500)
    
    async def type_text(self, request: web.Request) -> web.Response:
        """Type text using keyboard"""
        try:
            data = await request.json()
            text = data.get('text', '')
            interval = data.get('interval', 0.05)
            
            logger.info(f"Typing text: '{text[:20]}...' with interval {interval}s")
            
            pyautogui.typewrite(text, interval=interval)
            
            return web.json_response({
                "success": True,
                "action": "type",
                "text_length": len(text),
                "interval": interval,
                "display": DISPLAY
            })
            
        except Exception as e:
            logger.error(f"Type text failed: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
                "display": DISPLAY
            }, status=500)
    
    async def press_key(self, request: web.Request) -> web.Response:
        """Press a specific key or key combination"""
        try:
            data = await request.json()
            key = data.get('key', '')
            
            logger.info(f"Pressing key: {key}")
            
            # Handle key combinations (e.g., "ctrl+a")
            if '+' in key:
                keys = key.split('+')
                pyautogui.hotkey(*keys)
            else:
                pyautogui.press(key)
            
            return web.json_response({
                "success": True,
                "action": "press",
                "key": key,
                "display": DISPLAY
            })
            
        except Exception as e:
            logger.error(f"Press key failed: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
                "display": DISPLAY
            }, status=500)
    
    async def get_mouse_position(self, request: web.Request) -> web.Response:
        """Get current mouse position"""
        try:
            x, y = pyautogui.position()
            
            return web.json_response({
                "success": True,
                "position": {"x": x, "y": y},
                "screen_size": {
                    "width": self.screen_width,
                    "height": self.screen_height
                },
                "display": DISPLAY
            })
            
        except Exception as e:
            logger.error(f"Get mouse position failed: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
                "display": DISPLAY
            }, status=500)
    
    async def drag_mouse(self, request: web.Request) -> web.Response:
        """Drag mouse from one position to another"""
        try:
            data = await request.json()
            start_x = data.get('start_x', 0)
            start_y = data.get('start_y', 0)
            end_x = data.get('end_x', 0)
            end_y = data.get('end_y', 0)
            duration = data.get('duration', 1.0)
            button = data.get('button', 'left')
            
            logger.info(f"Dragging from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            
            # Move to start position
            pyautogui.moveTo(start_x, start_y, duration=0.5)
            
            # Perform drag
            pyautogui.dragTo(end_x, end_y, duration=duration, button=button)
            
            current_x, current_y = pyautogui.position()
            
            return web.json_response({
                "success": True,
                "action": "drag",
                "start": {"x": start_x, "y": start_y},
                "end": {"x": end_x, "y": end_y},
                "actual": {"x": current_x, "y": current_y},
                "duration": duration,
                "button": button,
                "display": DISPLAY
            })
            
        except Exception as e:
            logger.error(f"Mouse drag failed: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
                "display": DISPLAY
            }, status=500)
    
    async def scroll(self, request: web.Request) -> web.Response:
        """Scroll the mouse wheel"""
        try:
            data = await request.json()
            clicks = data.get('clicks', 3)
            x = data.get('x', None)
            y = data.get('y', None)
            
            if x is not None and y is not None:
                logger.info(f"Scrolling {clicks} clicks at ({x}, {y})")
                pyautogui.scroll(clicks, x=x, y=y)
            else:
                logger.info(f"Scrolling {clicks} clicks at current position")
                pyautogui.scroll(clicks)
            
            return web.json_response({
                "success": True,
                "action": "scroll",
                "clicks": clicks,
                "display": DISPLAY
            })
            
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
                "display": DISPLAY
            }, status=500)
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        try:
            # Test if we can get mouse position
            x, y = pyautogui.position()
            
            return web.json_response({
                "status": "healthy",
                "server": "hid-input-mcp-http-v2",
                "display": DISPLAY,
                "mouse_position": {"x": x, "y": y},
                "screen_size": {
                    "width": self.screen_width,
                    "height": self.screen_height
                }
            })
        except Exception as e:
            return web.json_response({
                "status": "unhealthy",
                "error": str(e),
                "display": DISPLAY
            }, status=503)
    
    def create_app(self) -> web.Application:
        """Create the aiohttp application"""
        app = web.Application()
        
        # Add routes
        app.router.add_post('/move', self.move_mouse)
        app.router.add_post('/click', self.click_mouse)
        app.router.add_post('/type', self.type_text)
        app.router.add_post('/press', self.press_key)
        app.router.add_post('/drag', self.drag_mouse)
        app.router.add_post('/scroll', self.scroll)
        app.router.add_get('/position', self.get_mouse_position)
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
        
        logger.info(f"Starting HID Input MCP HTTP Server on port {self.port}")
        logger.info(f"Using DISPLAY: {DISPLAY}")
        logger.info(f"Screen size: {self.screen_width}x{self.screen_height}")
        
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
    port = int(os.environ.get('HID_MCP_PORT', 8081))
    server = HIDInputServer(port=port)
    await server.start()

if __name__ == "__main__":
    # Force PyAutoGUI to use the X11 backend (not the host display)
    os.environ['DISPLAY'] = DISPLAY
    
    # Disable PyAutoGUI's screenshot functionality to avoid conflicts
    pyautogui.screenshot = None
    
    # Run the server
    asyncio.run(main())