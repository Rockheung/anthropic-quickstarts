"""Screenshot MCP Server for periodic screen capture and analysis.

This MCP server provides screen capture capabilities with configurable intervals,
supporting full screen, window-specific, and browser-specific captures.
"""

import asyncio
import base64
import io
import logging
import os
import sys
import time
from typing import Any, Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import PIL.Image
import pyautogui
import mss
import numpy as np


# Platform-specific imports for window management
if sys.platform == "darwin":  # macOS
    import Quartz
    import AppKit
elif sys.platform == "win32":  # Windows
    import win32gui
    import win32con
    import win32process
    import psutil
else:  # Linux
    import subprocess


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CaptureMode(Enum):
    """Screenshot capture modes."""
    FULL_SCREEN = "full_screen"
    ACTIVE_WINDOW = "active_window"
    REGION = "region"
    MONITOR = "monitor"
    BROWSER = "browser"


@dataclass
class Screenshot:
    """Represents a captured screenshot."""
    image: PIL.Image.Image
    mode: CaptureMode
    timestamp: float
    metadata: Dict[str, Any]
    base64_data: Optional[str] = None


@dataclass
class CaptureRegion:
    """Defines a screen region for capture."""
    x: int
    y: int
    width: int
    height: int


class ScreenshotCapture:
    """Handles screen capture operations."""
    
    def __init__(self):
        """Initialize the screenshot capture system."""
        self.sct = mss.mss()
        self.capture_history: List[Screenshot] = []
        self.max_history = 50
        self.periodic_capture_task: Optional[asyncio.Task] = None
        self.capture_interval: float = 1.0  # Default 1 second
        self.capture_enabled: bool = False
        
    def _save_to_history(self, screenshot: Screenshot) -> None:
        """Save screenshot to history."""
        self.capture_history.append(screenshot)
        if len(self.capture_history) > self.max_history:
            self.capture_history.pop(0)
        logger.info(f"Screenshot captured: {screenshot.mode.value} at {screenshot.timestamp}")
    
    def _image_to_base64(self, image: PIL.Image.Image, format: str = "PNG") -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    async def capture_full_screen(self) -> Screenshot:
        """Capture the entire screen."""
        try:
            # Use mss for better performance
            monitor = self.sct.monitors[0]  # All monitors combined
            screenshot = self.sct.grab(monitor)
            
            # Convert to PIL Image
            image = PIL.Image.frombytes(
                "RGB",
                (screenshot.width, screenshot.height),
                screenshot.rgb
            )
            
            # Create Screenshot object
            result = Screenshot(
                image=image,
                mode=CaptureMode.FULL_SCREEN,
                timestamp=time.time(),
                metadata={
                    "width": image.width,
                    "height": image.height,
                    "monitors": len(self.sct.monitors) - 1
                },
                base64_data=self._image_to_base64(image)
            )
            
            self._save_to_history(result)
            return result
            
        except Exception as e:
            logger.error(f"Failed to capture full screen: {str(e)}")
            raise
    
    async def capture_monitor(self, monitor_index: int = 1) -> Screenshot:
        """Capture a specific monitor."""
        try:
            if monitor_index >= len(self.sct.monitors):
                raise ValueError(f"Monitor {monitor_index} not found")
            
            monitor = self.sct.monitors[monitor_index]
            screenshot = self.sct.grab(monitor)
            
            # Convert to PIL Image
            image = PIL.Image.frombytes(
                "RGB",
                (screenshot.width, screenshot.height),
                screenshot.rgb
            )
            
            result = Screenshot(
                image=image,
                mode=CaptureMode.MONITOR,
                timestamp=time.time(),
                metadata={
                    "monitor_index": monitor_index,
                    "width": image.width,
                    "height": image.height,
                    "position": {"x": monitor["left"], "y": monitor["top"]}
                },
                base64_data=self._image_to_base64(image)
            )
            
            self._save_to_history(result)
            return result
            
        except Exception as e:
            logger.error(f"Failed to capture monitor {monitor_index}: {str(e)}")
            raise
    
    async def capture_region(self, region: CaptureRegion) -> Screenshot:
        """Capture a specific screen region."""
        try:
            bbox = {
                "left": region.x,
                "top": region.y,
                "width": region.width,
                "height": region.height
            }
            
            screenshot = self.sct.grab(bbox)
            
            # Convert to PIL Image
            image = PIL.Image.frombytes(
                "RGB",
                (screenshot.width, screenshot.height),
                screenshot.rgb
            )
            
            result = Screenshot(
                image=image,
                mode=CaptureMode.REGION,
                timestamp=time.time(),
                metadata={
                    "region": {
                        "x": region.x,
                        "y": region.y,
                        "width": region.width,
                        "height": region.height
                    }
                },
                base64_data=self._image_to_base64(image)
            )
            
            self._save_to_history(result)
            return result
            
        except Exception as e:
            logger.error(f"Failed to capture region: {str(e)}")
            raise
    
    async def capture_active_window(self) -> Screenshot:
        """Capture the currently active window."""
        try:
            if sys.platform == "darwin":
                # macOS implementation
                return await self._capture_active_window_macos()
            elif sys.platform == "win32":
                # Windows implementation
                return await self._capture_active_window_windows()
            else:
                # Linux implementation
                return await self._capture_active_window_linux()
                
        except Exception as e:
            logger.error(f"Failed to capture active window: {str(e)}")
            # Fallback to full screen
            return await self.capture_full_screen()
    
    async def _capture_active_window_macos(self) -> Screenshot:
        """Capture active window on macOS."""
        # Get active window bounds using Quartz
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        
        for window in window_list:
            if window.get('kCGWindowLayer', 0) == 0:
                bounds = window.get('kCGWindowBounds', {})
                x = int(bounds.get('X', 0))
                y = int(bounds.get('Y', 0))
                width = int(bounds.get('Width', 100))
                height = int(bounds.get('Height', 100))
                
                region = CaptureRegion(x, y, width, height)
                screenshot = await self.capture_region(region)
                screenshot.mode = CaptureMode.ACTIVE_WINDOW
                screenshot.metadata['window_name'] = window.get('kCGWindowOwnerName', 'Unknown')
                return screenshot
        
        # Fallback to full screen
        return await self.capture_full_screen()
    
    async def _capture_active_window_windows(self) -> Screenshot:
        """Capture active window on Windows."""
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            width = right - x
            height = bottom - y
            
            region = CaptureRegion(x, y, width, height)
            screenshot = await self.capture_region(region)
            screenshot.mode = CaptureMode.ACTIVE_WINDOW
            
            # Get window title
            window_title = win32gui.GetWindowText(hwnd)
            screenshot.metadata['window_name'] = window_title
            
            return screenshot
        
        # Fallback to full screen
        return await self.capture_full_screen()
    
    async def _capture_active_window_linux(self) -> Screenshot:
        """Capture active window on Linux using xdotool."""
        try:
            # Get active window ID
            result = subprocess.run(
                ['xdotool', 'getactivewindow'],
                capture_output=True,
                text=True
            )
            window_id = result.stdout.strip()
            
            # Get window geometry
            result = subprocess.run(
                ['xdotool', 'getwindowgeometry', window_id],
                capture_output=True,
                text=True
            )
            
            # Parse geometry
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Position:' in line:
                    pos = line.split(':')[1].strip().split(',')
                    x = int(pos[0])
                    y = int(pos[1].split()[0])
                elif 'Geometry:' in line:
                    size = line.split(':')[1].strip().split('x')
                    width = int(size[0])
                    height = int(size[1])
            
            region = CaptureRegion(x, y, width, height)
            screenshot = await self.capture_region(region)
            screenshot.mode = CaptureMode.ACTIVE_WINDOW
            
            # Get window name
            result = subprocess.run(
                ['xdotool', 'getwindowname', window_id],
                capture_output=True,
                text=True
            )
            screenshot.metadata['window_name'] = result.stdout.strip()
            
            return screenshot
            
        except Exception:
            # Fallback to full screen
            return await self.capture_full_screen()
    
    async def find_browser_windows(self) -> List[Dict[str, Any]]:
        """Find all browser windows."""
        browser_names = [
            'Chrome', 'Firefox', 'Safari', 'Edge', 'Opera', 'Brave',
            'chromium', 'firefox', 'safari', 'microsoft edge'
        ]
        
        windows = []
        
        if sys.platform == "darwin":
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly,
                Quartz.kCGNullWindowID
            )
            
            for window in window_list:
                owner_name = window.get('kCGWindowOwnerName', '').lower()
                if any(browser in owner_name for browser in browser_names):
                    bounds = window.get('kCGWindowBounds', {})
                    windows.append({
                        'name': window.get('kCGWindowOwnerName'),
                        'title': window.get('kCGWindowName', ''),
                        'bounds': {
                            'x': int(bounds.get('X', 0)),
                            'y': int(bounds.get('Y', 0)),
                            'width': int(bounds.get('Width', 0)),
                            'height': int(bounds.get('Height', 0))
                        }
                    })
        
        elif sys.platform == "win32":
            def enum_windows_callback(hwnd, windows_list):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        process = psutil.Process(pid)
                        process_name = process.name().lower()
                        if any(browser in process_name for browser in browser_names):
                            rect = win32gui.GetWindowRect(hwnd)
                            windows_list.append({
                                'name': process.name(),
                                'title': window_title,
                                'bounds': {
                                    'x': rect[0],
                                    'y': rect[1],
                                    'width': rect[2] - rect[0],
                                    'height': rect[3] - rect[1]
                                }
                            })
                    except:
                        pass
                return True
            
            win32gui.EnumWindows(enum_windows_callback, windows)
        
        return windows
    
    async def capture_browser(self, browser_index: int = 0) -> Screenshot:
        """Capture a specific browser window."""
        try:
            browsers = await self.find_browser_windows()
            
            if not browsers:
                logger.warning("No browser windows found")
                return await self.capture_full_screen()
            
            if browser_index >= len(browsers):
                browser_index = 0
            
            browser = browsers[browser_index]
            bounds = browser['bounds']
            
            region = CaptureRegion(
                bounds['x'],
                bounds['y'],
                bounds['width'],
                bounds['height']
            )
            
            screenshot = await self.capture_region(region)
            screenshot.mode = CaptureMode.BROWSER
            screenshot.metadata.update({
                'browser_name': browser['name'],
                'browser_title': browser['title'],
                'browser_index': browser_index
            })
            
            return screenshot
            
        except Exception as e:
            logger.error(f"Failed to capture browser: {str(e)}")
            return await self.capture_full_screen()
    
    async def start_periodic_capture(
        self,
        interval: float = 1.0,
        mode: CaptureMode = CaptureMode.FULL_SCREEN,
        **kwargs
    ) -> Dict[str, Any]:
        """Start periodic screenshot capture."""
        if self.capture_enabled:
            return {
                "success": False,
                "message": "Periodic capture already running"
            }
        
        self.capture_interval = interval
        self.capture_enabled = True
        
        async def capture_loop():
            """Periodic capture loop."""
            while self.capture_enabled:
                try:
                    if mode == CaptureMode.FULL_SCREEN:
                        await self.capture_full_screen()
                    elif mode == CaptureMode.MONITOR:
                        monitor_index = kwargs.get('monitor_index', 1)
                        await self.capture_monitor(monitor_index)
                    elif mode == CaptureMode.REGION:
                        region = kwargs.get('region')
                        if region:
                            await self.capture_region(region)
                    elif mode == CaptureMode.ACTIVE_WINDOW:
                        await self.capture_active_window()
                    elif mode == CaptureMode.BROWSER:
                        browser_index = kwargs.get('browser_index', 0)
                        await self.capture_browser(browser_index)
                    
                    await asyncio.sleep(self.capture_interval)
                    
                except Exception as e:
                    logger.error(f"Error in periodic capture: {str(e)}")
                    await asyncio.sleep(self.capture_interval)
        
        self.periodic_capture_task = asyncio.create_task(capture_loop())
        
        return {
            "success": True,
            "message": f"Started periodic capture with {interval}s interval",
            "mode": mode.value,
            "interval": interval
        }
    
    async def stop_periodic_capture(self) -> Dict[str, Any]:
        """Stop periodic screenshot capture."""
        if not self.capture_enabled:
            return {
                "success": False,
                "message": "Periodic capture not running"
            }
        
        self.capture_enabled = False
        
        if self.periodic_capture_task:
            self.periodic_capture_task.cancel()
            try:
                await self.periodic_capture_task
            except asyncio.CancelledError:
                pass
            self.periodic_capture_task = None
        
        return {
            "success": True,
            "message": "Stopped periodic capture"
        }
    
    async def get_capture_status(self) -> Dict[str, Any]:
        """Get periodic capture status."""
        return {
            "enabled": self.capture_enabled,
            "interval": self.capture_interval,
            "history_count": len(self.capture_history),
            "max_history": self.max_history
        }
    
    async def get_latest_screenshot(self) -> Optional[Screenshot]:
        """Get the most recent screenshot."""
        if self.capture_history:
            return self.capture_history[-1]
        return None
    
    async def clear_history(self) -> Dict[str, Any]:
        """Clear screenshot history."""
        count = len(self.capture_history)
        self.capture_history.clear()
        return {
            "success": True,
            "message": f"Cleared {count} screenshots from history"
        }


# Initialize MCP server
server = Server("screenshot-mcp")
capture = ScreenshotCapture()


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available screenshot tools."""
    return [
        Tool(
            name="capture_screenshot",
            description="Capture a screenshot with specified mode",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["full_screen", "active_window", "region", "monitor", "browser"],
                        "default": "full_screen",
                        "description": "Capture mode"
                    },
                    "monitor_index": {
                        "type": "integer",
                        "default": 1,
                        "description": "Monitor index for monitor mode"
                    },
                    "browser_index": {
                        "type": "integer",
                        "default": 0,
                        "description": "Browser window index for browser mode"
                    },
                    "region": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"}
                        },
                        "description": "Region coordinates for region mode"
                    }
                }
            }
        ),
        Tool(
            name="start_periodic_capture",
            description="Start periodic screenshot capture",
            inputSchema={
                "type": "object",
                "properties": {
                    "interval": {
                        "type": "number",
                        "default": 1.0,
                        "description": "Capture interval in seconds"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["full_screen", "active_window", "region", "monitor", "browser"],
                        "default": "full_screen",
                        "description": "Capture mode"
                    },
                    "monitor_index": {
                        "type": "integer",
                        "default": 1,
                        "description": "Monitor index for monitor mode"
                    },
                    "browser_index": {
                        "type": "integer",
                        "default": 0,
                        "description": "Browser window index for browser mode"
                    },
                    "region": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"}
                        },
                        "description": "Region coordinates for region mode"
                    }
                }
            }
        ),
        Tool(
            name="stop_periodic_capture",
            description="Stop periodic screenshot capture",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_capture_status",
            description="Get periodic capture status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_latest_screenshot",
            description="Get the most recent screenshot",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="find_browser_windows",
            description="Find all browser windows",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="clear_history",
            description="Clear screenshot history",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent | ImageContent]:
    """Handle tool calls from MCP clients."""
    try:
        if name == "capture_screenshot":
            mode_str = arguments.get("mode", "full_screen")
            mode = CaptureMode(mode_str)
            
            if mode == CaptureMode.FULL_SCREEN:
                screenshot = await capture.capture_full_screen()
            elif mode == CaptureMode.MONITOR:
                monitor_index = arguments.get("monitor_index", 1)
                screenshot = await capture.capture_monitor(monitor_index)
            elif mode == CaptureMode.REGION:
                region_data = arguments.get("region")
                if region_data:
                    region = CaptureRegion(**region_data)
                    screenshot = await capture.capture_region(region)
                else:
                    screenshot = await capture.capture_full_screen()
            elif mode == CaptureMode.ACTIVE_WINDOW:
                screenshot = await capture.capture_active_window()
            elif mode == CaptureMode.BROWSER:
                browser_index = arguments.get("browser_index", 0)
                screenshot = await capture.capture_browser(browser_index)
            else:
                screenshot = await capture.capture_full_screen()
            
            return [
                ImageContent(
                    type="image",
                    data=screenshot.base64_data,
                    mimeType="image/png"
                ),
                TextContent(
                    type="text",
                    text=f"Screenshot captured: {screenshot.mode.value}\n"
                         f"Size: {screenshot.metadata.get('width', 'N/A')}x{screenshot.metadata.get('height', 'N/A')}\n"
                         f"Timestamp: {datetime.fromtimestamp(screenshot.timestamp).isoformat()}"
                )
            ]
        
        elif name == "start_periodic_capture":
            interval = arguments.get("interval", 1.0)
            mode_str = arguments.get("mode", "full_screen")
            mode = CaptureMode(mode_str)
            
            kwargs = {}
            if mode == CaptureMode.MONITOR:
                kwargs['monitor_index'] = arguments.get("monitor_index", 1)
            elif mode == CaptureMode.REGION:
                region_data = arguments.get("region")
                if region_data:
                    kwargs['region'] = CaptureRegion(**region_data)
            elif mode == CaptureMode.BROWSER:
                kwargs['browser_index'] = arguments.get("browser_index", 0)
            
            result = await capture.start_periodic_capture(interval, mode, **kwargs)
            
            import json
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "stop_periodic_capture":
            result = await capture.stop_periodic_capture()
            import json
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_capture_status":
            result = await capture.get_capture_status()
            import json
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_latest_screenshot":
            screenshot = await capture.get_latest_screenshot()
            if screenshot:
                return [
                    ImageContent(
                        type="image",
                        data=screenshot.base64_data,
                        mimeType="image/png"
                    ),
                    TextContent(
                        type="text",
                        text=f"Latest screenshot: {screenshot.mode.value}\n"
                             f"Timestamp: {datetime.fromtimestamp(screenshot.timestamp).isoformat()}"
                    )
                ]
            else:
                return [TextContent(type="text", text="No screenshots in history")]
        
        elif name == "find_browser_windows":
            windows = await capture.find_browser_windows()
            import json
            return [TextContent(type="text", text=json.dumps(windows, indent=2))]
        
        elif name == "clear_history":
            result = await capture.clear_history()
            import json
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Tool execution error: {str(e)}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the Screenshot MCP server."""
    logger.info("Starting Screenshot MCP Server...")
    
    async with stdio_server(server):
        # The server will run until the connection is closed
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())