#!/usr/bin/env python3
"""Unified MCP Server combining HID Input and Screenshot capabilities.

This server provides both hardware input control and screen capture functionality
through a single MCP interface, optimized for automation tasks.
"""

import asyncio
import base64
import io
import json
import logging
import os
import sys
import time
from typing import Any, Optional, Dict, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ImageContent, ServerCapabilities

# GUI automation imports
import PIL.Image
import pyautogui
import pynput
from pynput import keyboard, mouse
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

# Configure PyAutoGUI safety features
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Default pause between actions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# HID Input Components
# ============================================================================

class MouseButton(Enum):
    """Mouse button types."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"

class KeyModifier(Enum):
    """Keyboard modifier keys."""
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    CMD = "cmd"  # macOS Command key
    WIN = "win"  # Windows key

@dataclass
class InputEvent:
    """Represents an input event with metadata."""
    event_type: str
    timestamp: float
    details: Dict[str, Any]
    success: bool
    error: Optional[str] = None

# ============================================================================
# Screenshot Components
# ============================================================================

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

# ============================================================================
# Unified Controller
# ============================================================================

class UnifiedController:
    """Unified controller for HID input and screenshot operations."""
    
    def __init__(self):
        """Initialize the unified controller."""
        # HID components
        self.keyboard_controller = pynput.keyboard.Controller()
        self.mouse_controller = pynput.mouse.Controller()
        self.input_event_history: List[InputEvent] = []
        self.max_input_history = 100
        
        # Screenshot components
        self.sct = mss.mss()
        self.capture_history: List[Screenshot] = []
        self.max_capture_history = 50
        self.periodic_capture_task: Optional[asyncio.Task] = None
        self.capture_interval: float = 1.0
        self.capture_enabled: bool = False
    
    # ========================================================================
    # HID Input Methods
    # ========================================================================
    
    def _log_input_event(self, event: InputEvent) -> None:
        """Log an input event to history."""
        self.input_event_history.append(event)
        if len(self.input_event_history) > self.max_input_history:
            self.input_event_history.pop(0)
        
        if event.success:
            logger.info(f"Input Event: {event.event_type} - {event.details}")
        else:
            logger.error(f"Input Event failed: {event.event_type} - {event.error}")
    
    async def move_mouse(self, x: int, y: int, duration: float = 0.0) -> Dict[str, Any]:
        """Move mouse to absolute position."""
        try:
            start_time = time.time()
            
            if duration > 0:
                pyautogui.moveTo(x, y, duration=duration)
            else:
                self.mouse_controller.position = (x, y)
            
            event = InputEvent(
                event_type="mouse_move",
                timestamp=start_time,
                details={"x": x, "y": y, "duration": duration},
                success=True
            )
            self._log_input_event(event)
            
            return {
                "success": True,
                "position": {"x": x, "y": y},
                "message": f"Mouse moved to ({x}, {y})"
            }
        except Exception as e:
            event = InputEvent(
                event_type="mouse_move",
                timestamp=time.time(),
                details={"x": x, "y": y},
                success=False,
                error=str(e)
            )
            self._log_input_event(event)
            return {"success": False, "error": str(e)}
    
    async def click_mouse(
        self, 
        x: Optional[int] = None, 
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0
    ) -> Dict[str, Any]:
        """Click mouse button at position."""
        try:
            start_time = time.time()
            
            # Move to position if specified
            if x is not None and y is not None:
                await self.move_mouse(x, y)
            
            # Perform click
            if clicks > 1:
                pyautogui.click(button=button, clicks=clicks, interval=interval)
            else:
                button_obj = getattr(pynput.mouse.Button, button, pynput.mouse.Button.left)
                self.mouse_controller.click(button_obj, clicks)
            
            current_pos = self.mouse_controller.position
            event = InputEvent(
                event_type="mouse_click",
                timestamp=start_time,
                details={
                    "x": current_pos[0],
                    "y": current_pos[1],
                    "button": button,
                    "clicks": clicks
                },
                success=True
            )
            self._log_input_event(event)
            
            return {
                "success": True,
                "position": {"x": current_pos[0], "y": current_pos[1]},
                "button": button,
                "clicks": clicks,
                "message": f"Clicked {button} button {clicks} time(s)"
            }
        except Exception as e:
            event = InputEvent(
                event_type="mouse_click",
                timestamp=time.time(),
                details={"button": button, "clicks": clicks},
                success=False,
                error=str(e)
            )
            self._log_input_event(event)
            return {"success": False, "error": str(e)}
    
    async def type_text(
        self,
        text: str,
        interval: float = 0.0,
        simulate_human: bool = False
    ) -> Dict[str, Any]:
        """Type text using keyboard."""
        try:
            import random
            start_time = time.time()
            
            if simulate_human:
                # Add random delays between keystrokes for human-like typing
                for char in text:
                    self.keyboard_controller.type(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))
            else:
                if interval > 0:
                    pyautogui.typewrite(text, interval=interval)
                else:
                    self.keyboard_controller.type(text)
            
            event = InputEvent(
                event_type="keyboard_type",
                timestamp=start_time,
                details={
                    "text_length": len(text),
                    "interval": interval,
                    "simulate_human": simulate_human
                },
                success=True
            )
            self._log_input_event(event)
            
            return {
                "success": True,
                "text_length": len(text),
                "message": f"Typed {len(text)} characters"
            }
        except Exception as e:
            event = InputEvent(
                event_type="keyboard_type",
                timestamp=time.time(),
                details={"text_length": len(text)},
                success=False,
                error=str(e)
            )
            self._log_input_event(event)
            return {"success": False, "error": str(e)}
    
    async def press_key(
        self,
        key: str,
        modifiers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Press a single key or key combination."""
        try:
            start_time = time.time()
            
            if modifiers:
                # Use pyautogui for key combinations
                keys = modifiers + [key]
                pyautogui.hotkey(*keys)
            else:
                # Map special keys
                special_keys = {
                    "enter": pynput.keyboard.Key.enter,
                    "return": pynput.keyboard.Key.enter,
                    "tab": pynput.keyboard.Key.tab,
                    "space": pynput.keyboard.Key.space,
                    "backspace": pynput.keyboard.Key.backspace,
                    "delete": pynput.keyboard.Key.delete,
                    "escape": pynput.keyboard.Key.esc,
                    "esc": pynput.keyboard.Key.esc,
                    "up": pynput.keyboard.Key.up,
                    "down": pynput.keyboard.Key.down,
                    "left": pynput.keyboard.Key.left,
                    "right": pynput.keyboard.Key.right,
                    "home": pynput.keyboard.Key.home,
                    "end": pynput.keyboard.Key.end,
                    "pageup": pynput.keyboard.Key.page_up,
                    "pagedown": pynput.keyboard.Key.page_down,
                }
                
                # Add F-keys
                for i in range(1, 13):
                    special_keys[f"f{i}"] = getattr(pynput.keyboard.Key, f"f{i}")
                
                key_obj = special_keys.get(key.lower())
                if key_obj:
                    self.keyboard_controller.press(key_obj)
                    self.keyboard_controller.release(key_obj)
                else:
                    self.keyboard_controller.press(key)
                    self.keyboard_controller.release(key)
            
            event = InputEvent(
                event_type="keyboard_press",
                timestamp=start_time,
                details={
                    "key": key,
                    "modifiers": modifiers
                },
                success=True
            )
            self._log_input_event(event)
            
            return {
                "success": True,
                "key": key,
                "modifiers": modifiers,
                "message": f"Pressed key: {key}" + (f" with modifiers: {modifiers}" if modifiers else "")
            }
        except Exception as e:
            event = InputEvent(
                event_type="keyboard_press",
                timestamp=time.time(),
                details={"key": key, "modifiers": modifiers},
                success=False,
                error=str(e)
            )
            self._log_input_event(event)
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # Screenshot Methods
    # ========================================================================
    
    def _save_to_capture_history(self, screenshot: Screenshot) -> None:
        """Save screenshot to history."""
        self.capture_history.append(screenshot)
        if len(self.capture_history) > self.max_capture_history:
            self.capture_history.pop(0)
        logger.info(f"Screenshot captured: {screenshot.mode.value} at {screenshot.timestamp}")
    
    def _image_to_base64(self, image: PIL.Image.Image, format: str = "PNG") -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    async def capture_screenshot(
        self,
        mode: str = "full_screen",
        **kwargs
    ) -> Screenshot:
        """Capture a screenshot with specified mode."""
        try:
            capture_mode = CaptureMode(mode)
            
            if capture_mode == CaptureMode.FULL_SCREEN:
                # Capture entire screen
                monitor = self.sct.monitors[0]  # All monitors combined
                screenshot = self.sct.grab(monitor)
                
                image = PIL.Image.frombytes(
                    "RGB",
                    (screenshot.width, screenshot.height),
                    screenshot.rgb
                )
                
                result = Screenshot(
                    image=image,
                    mode=capture_mode,
                    timestamp=time.time(),
                    metadata={
                        "width": image.width,
                        "height": image.height,
                        "monitors": len(self.sct.monitors) - 1
                    },
                    base64_data=self._image_to_base64(image)
                )
            
            elif capture_mode == CaptureMode.MONITOR:
                # Capture specific monitor
                monitor_index = kwargs.get('monitor_index', 1)
                if monitor_index >= len(self.sct.monitors):
                    monitor_index = 1
                
                monitor = self.sct.monitors[monitor_index]
                screenshot = self.sct.grab(monitor)
                
                image = PIL.Image.frombytes(
                    "RGB",
                    (screenshot.width, screenshot.height),
                    screenshot.rgb
                )
                
                result = Screenshot(
                    image=image,
                    mode=capture_mode,
                    timestamp=time.time(),
                    metadata={
                        "monitor_index": monitor_index,
                        "width": image.width,
                        "height": image.height,
                        "position": {"x": monitor["left"], "y": monitor["top"]}
                    },
                    base64_data=self._image_to_base64(image)
                )
            
            elif capture_mode == CaptureMode.REGION:
                # Capture specific region
                region = kwargs.get('region', {})
                bbox = {
                    "left": region.get('x', 0),
                    "top": region.get('y', 0),
                    "width": region.get('width', 800),
                    "height": region.get('height', 600)
                }
                
                screenshot = self.sct.grab(bbox)
                
                image = PIL.Image.frombytes(
                    "RGB",
                    (screenshot.width, screenshot.height),
                    screenshot.rgb
                )
                
                result = Screenshot(
                    image=image,
                    mode=capture_mode,
                    timestamp=time.time(),
                    metadata={"region": region},
                    base64_data=self._image_to_base64(image)
                )
            
            else:
                # Default to full screen for other modes (simplified for Docker environment)
                monitor = self.sct.monitors[0]
                screenshot = self.sct.grab(monitor)
                
                image = PIL.Image.frombytes(
                    "RGB",
                    (screenshot.width, screenshot.height),
                    screenshot.rgb
                )
                
                result = Screenshot(
                    image=image,
                    mode=CaptureMode.FULL_SCREEN,
                    timestamp=time.time(),
                    metadata={
                        "width": image.width,
                        "height": image.height,
                        "fallback": True
                    },
                    base64_data=self._image_to_base64(image)
                )
            
            self._save_to_capture_history(result)
            return result
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {str(e)}")
            raise
    
    async def start_periodic_capture(
        self,
        interval: float = 1.0,
        mode: str = "full_screen",
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
                    await self.capture_screenshot(mode, **kwargs)
                    await asyncio.sleep(self.capture_interval)
                except Exception as e:
                    logger.error(f"Error in periodic capture: {str(e)}")
                    await asyncio.sleep(self.capture_interval)
        
        self.periodic_capture_task = asyncio.create_task(capture_loop())
        
        return {
            "success": True,
            "message": f"Started periodic capture with {interval}s interval",
            "mode": mode,
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
    
    # ========================================================================
    # Combined Methods
    # ========================================================================
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        current_mouse_pos = self.mouse_controller.position
        
        return {
            "mouse_position": {"x": current_mouse_pos[0], "y": current_mouse_pos[1]},
            "input_history_count": len(self.input_event_history),
            "capture_history_count": len(self.capture_history),
            "periodic_capture_enabled": self.capture_enabled,
            "capture_interval": self.capture_interval,
            "monitors": len(self.sct.monitors) - 1,
            "platform": sys.platform
        }
    
    async def clear_all_history(self) -> Dict[str, Any]:
        """Clear all event history."""
        input_count = len(self.input_event_history)
        capture_count = len(self.capture_history)
        
        self.input_event_history.clear()
        self.capture_history.clear()
        
        return {
            "success": True,
            "cleared": {
                "input_events": input_count,
                "screenshots": capture_count
            }
        }

# ============================================================================
# MCP Server Setup
# ============================================================================

# Initialize MCP server and controller
server = Server("unified-automation-mcp")
controller = UnifiedController()

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    return [
        # HID Input Tools
        Tool(
            name="move_mouse",
            description="Move mouse to absolute position",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "duration": {
                        "type": "number",
                        "default": 0.0,
                        "description": "Movement duration in seconds"
                    }
                },
                "required": ["x", "y"]
            }
        ),
        Tool(
            name="click_mouse",
            description="Click mouse button at current or specified position",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (optional)"},
                    "y": {"type": "integer", "description": "Y coordinate (optional)"},
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "default": "left",
                        "description": "Mouse button"
                    },
                    "clicks": {
                        "type": "integer",
                        "default": 1,
                        "description": "Number of clicks"
                    },
                    "interval": {
                        "type": "number",
                        "default": 0.0,
                        "description": "Interval between clicks"
                    }
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
                    "interval": {
                        "type": "number",
                        "default": 0.0,
                        "description": "Interval between keystrokes"
                    },
                    "simulate_human": {
                        "type": "boolean",
                        "default": False,
                        "description": "Simulate human typing with random delays"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="press_key",
            description="Press a single key or key combination",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to press"},
                    "modifiers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Modifier keys (ctrl, alt, shift, cmd, win)"
                    }
                },
                "required": ["key"]
            }
        ),
        # Screenshot Tools
        Tool(
            name="capture_screenshot",
            description="Capture a screenshot with specified mode",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["full_screen", "monitor", "region"],
                        "default": "full_screen",
                        "description": "Capture mode"
                    },
                    "monitor_index": {
                        "type": "integer",
                        "default": 1,
                        "description": "Monitor index for monitor mode"
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
                        "enum": ["full_screen", "monitor", "region"],
                        "default": "full_screen",
                        "description": "Capture mode"
                    },
                    "monitor_index": {
                        "type": "integer",
                        "default": 1,
                        "description": "Monitor index for monitor mode"
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
        # System Tools
        Tool(
            name="get_system_status",
            description="Get overall system status including mouse position and history counts",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="clear_all_history",
            description="Clear all event history (input and screenshots)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Union[TextContent, ImageContent]]:
    """Handle tool calls from MCP clients."""
    try:
        # HID Input Tools
        if name == "move_mouse":
            result = await controller.move_mouse(
                arguments["x"],
                arguments["y"],
                arguments.get("duration", 0.0)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "click_mouse":
            result = await controller.click_mouse(
                arguments.get("x"),
                arguments.get("y"),
                arguments.get("button", "left"),
                arguments.get("clicks", 1),
                arguments.get("interval", 0.0)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "type_text":
            result = await controller.type_text(
                arguments["text"],
                arguments.get("interval", 0.0),
                arguments.get("simulate_human", False)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "press_key":
            result = await controller.press_key(
                arguments["key"],
                arguments.get("modifiers")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # Screenshot Tools
        elif name == "capture_screenshot":
            screenshot = await controller.capture_screenshot(
                arguments.get("mode", "full_screen"),
                monitor_index=arguments.get("monitor_index", 1),
                region=arguments.get("region", {})
            )
            
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
            result = await controller.start_periodic_capture(
                arguments.get("interval", 1.0),
                arguments.get("mode", "full_screen"),
                monitor_index=arguments.get("monitor_index", 1),
                region=arguments.get("region", {})
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "stop_periodic_capture":
            result = await controller.stop_periodic_capture()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # System Tools
        elif name == "get_system_status":
            result = await controller.get_system_status()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "clear_all_history":
            result = await controller.clear_all_history()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Tool execution error: {str(e)}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Run the Unified MCP server."""
    logger.info("Starting Unified Automation MCP Server...")
    logger.info("Platform: %s", sys.platform)
    logger.info("Python version: %s", sys.version)
    
    # Verify display is available
    display = os.environ.get('DISPLAY', 'Not set')
    logger.info("DISPLAY: %s", display)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="unified-automation-mcp",
                server_version="1.0.0",
                capabilities=ServerCapabilities(tools={}),
                instructions="Unified MCP Server for HID input control and screen capture automation"
            )
        )

if __name__ == "__main__":
    asyncio.run(main())