"""HID Input MCP Server for hardware input signal management.

This MCP server provides low-level hardware input control through HID drivers,
enabling physical keyboard and mouse input generation for automation tasks.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import pyautogui
import pynput
from pynput import keyboard, mouse


# Configure PyAutoGUI safety features
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Default pause between actions


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


class HIDInputController:
    """Controls hardware input devices through HID drivers."""
    
    def __init__(self):
        """Initialize the HID input controller."""
        self.keyboard_controller = pynput.keyboard.Controller()
        self.mouse_controller = pynput.mouse.Controller()
        self.event_history: List[InputEvent] = []
        self.max_history = 100
        
    def _log_event(self, event: InputEvent) -> None:
        """Log an input event to history."""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        if event.success:
            logger.info(f"Event: {event.event_type} - {event.details}")
        else:
            logger.error(f"Event failed: {event.event_type} - {event.error}")
    
    async def move_mouse(self, x: int, y: int, duration: float = 0.0) -> Dict[str, Any]:
        """Move mouse to absolute position."""
        try:
            import time
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
            self._log_event(event)
            
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
            self._log_event(event)
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
            import time
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
            self._log_event(event)
            
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
            self._log_event(event)
            return {"success": False, "error": str(e)}
    
    async def drag_mouse(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: str = "left"
    ) -> Dict[str, Any]:
        """Drag mouse from start to end position."""
        try:
            import time
            start_time = time.time()
            
            pyautogui.dragTo(end_x, end_y, duration=duration, button=button)
            
            event = InputEvent(
                event_type="mouse_drag",
                timestamp=start_time,
                details={
                    "start": {"x": start_x, "y": start_y},
                    "end": {"x": end_x, "y": end_y},
                    "duration": duration,
                    "button": button
                },
                success=True
            )
            self._log_event(event)
            
            return {
                "success": True,
                "start": {"x": start_x, "y": start_y},
                "end": {"x": end_x, "y": end_y},
                "message": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"
            }
        except Exception as e:
            event = InputEvent(
                event_type="mouse_drag",
                timestamp=time.time(),
                details={
                    "start": {"x": start_x, "y": start_y},
                    "end": {"x": end_x, "y": end_y}
                },
                success=False,
                error=str(e)
            )
            self._log_event(event)
            return {"success": False, "error": str(e)}
    
    async def scroll_mouse(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        clicks: int = 3,
        direction: str = "down"
    ) -> Dict[str, Any]:
        """Scroll mouse wheel."""
        try:
            import time
            start_time = time.time()
            
            # Move to position if specified
            if x is not None and y is not None:
                await self.move_mouse(x, y)
            
            # Determine scroll amount
            scroll_amount = clicks if direction == "up" else -clicks
            pyautogui.scroll(scroll_amount)
            
            event = InputEvent(
                event_type="mouse_scroll",
                timestamp=start_time,
                details={
                    "direction": direction,
                    "clicks": clicks,
                    "position": {"x": x, "y": y} if x and y else None
                },
                success=True
            )
            self._log_event(event)
            
            return {
                "success": True,
                "direction": direction,
                "amount": clicks,
                "message": f"Scrolled {direction} by {clicks} clicks"
            }
        except Exception as e:
            event = InputEvent(
                event_type="mouse_scroll",
                timestamp=time.time(),
                details={"direction": direction, "clicks": clicks},
                success=False,
                error=str(e)
            )
            self._log_event(event)
            return {"success": False, "error": str(e)}
    
    async def type_text(
        self,
        text: str,
        interval: float = 0.0,
        simulate_human: bool = False
    ) -> Dict[str, Any]:
        """Type text using keyboard."""
        try:
            import time
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
            self._log_event(event)
            
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
            self._log_event(event)
            return {"success": False, "error": str(e)}
    
    async def press_key(
        self,
        key: str,
        modifiers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Press a single key or key combination."""
        try:
            import time
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
                    "f1": pynput.keyboard.Key.f1,
                    "f2": pynput.keyboard.Key.f2,
                    "f3": pynput.keyboard.Key.f3,
                    "f4": pynput.keyboard.Key.f4,
                    "f5": pynput.keyboard.Key.f5,
                    "f6": pynput.keyboard.Key.f6,
                    "f7": pynput.keyboard.Key.f7,
                    "f8": pynput.keyboard.Key.f8,
                    "f9": pynput.keyboard.Key.f9,
                    "f10": pynput.keyboard.Key.f10,
                    "f11": pynput.keyboard.Key.f11,
                    "f12": pynput.keyboard.Key.f12,
                }
                
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
            self._log_event(event)
            
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
            self._log_event(event)
            return {"success": False, "error": str(e)}
    
    async def get_mouse_position(self) -> Dict[str, Any]:
        """Get current mouse position."""
        try:
            pos = self.mouse_controller.position
            return {
                "success": True,
                "position": {"x": pos[0], "y": pos[1]}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_event_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent event history."""
        history = self.event_history[-limit:]
        return [
            {
                "type": event.event_type,
                "timestamp": event.timestamp,
                "details": event.details,
                "success": event.success,
                "error": event.error
            }
            for event in history
        ]


# Initialize MCP server
server = Server("hid-input-mcp")
controller = HIDInputController()


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available HID input tools."""
    return [
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
            name="drag_mouse",
            description="Drag mouse from start to end position",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer", "description": "Starting X coordinate"},
                    "start_y": {"type": "integer", "description": "Starting Y coordinate"},
                    "end_x": {"type": "integer", "description": "Ending X coordinate"},
                    "end_y": {"type": "integer", "description": "Ending Y coordinate"},
                    "duration": {
                        "type": "number",
                        "default": 0.5,
                        "description": "Drag duration in seconds"
                    },
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "default": "left",
                        "description": "Mouse button"
                    }
                },
                "required": ["start_x", "start_y", "end_x", "end_y"]
            }
        ),
        Tool(
            name="scroll_mouse",
            description="Scroll mouse wheel",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (optional)"},
                    "y": {"type": "integer", "description": "Y coordinate (optional)"},
                    "clicks": {
                        "type": "integer",
                        "default": 3,
                        "description": "Number of scroll clicks"
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down"],
                        "default": "down",
                        "description": "Scroll direction"
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
        Tool(
            name="get_mouse_position",
            description="Get current mouse position",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_event_history",
            description="Get recent input event history",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of events to retrieve"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls from MCP clients."""
    try:
        result = None
        
        if name == "move_mouse":
            result = await controller.move_mouse(
                arguments["x"],
                arguments["y"],
                arguments.get("duration", 0.0)
            )
        
        elif name == "click_mouse":
            result = await controller.click_mouse(
                arguments.get("x"),
                arguments.get("y"),
                arguments.get("button", "left"),
                arguments.get("clicks", 1),
                arguments.get("interval", 0.0)
            )
        
        elif name == "drag_mouse":
            result = await controller.drag_mouse(
                arguments["start_x"],
                arguments["start_y"],
                arguments["end_x"],
                arguments["end_y"],
                arguments.get("duration", 0.5),
                arguments.get("button", "left")
            )
        
        elif name == "scroll_mouse":
            result = await controller.scroll_mouse(
                arguments.get("x"),
                arguments.get("y"),
                arguments.get("clicks", 3),
                arguments.get("direction", "down")
            )
        
        elif name == "type_text":
            result = await controller.type_text(
                arguments["text"],
                arguments.get("interval", 0.0),
                arguments.get("simulate_human", False)
            )
        
        elif name == "press_key":
            result = await controller.press_key(
                arguments["key"],
                arguments.get("modifiers")
            )
        
        elif name == "get_mouse_position":
            result = await controller.get_mouse_position()
        
        elif name == "get_event_history":
            history = await controller.get_event_history(
                arguments.get("limit", 10)
            )
            result = {"success": True, "history": history}
        
        else:
            result = {"success": False, "error": f"Unknown tool: {name}"}
        
        # Format response
        if result:
            import json
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        else:
            return [TextContent(type="text", text="No result")]
    
    except Exception as e:
        logger.error(f"Tool execution error: {str(e)}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the HID Input MCP server."""
    logger.info("Starting HID Input MCP Server...")
    
    async with stdio_server(server):
        # The server will run until the connection is closed
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())