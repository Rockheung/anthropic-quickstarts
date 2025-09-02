"""MCP server for computer control functionality."""

import asyncio
import base64
import io
import os
from typing import Any, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_handler
from mcp.types import Tool, TextContent, ImageContent
from PIL import Image

from computer_use_demo.tools import (
    ComputerTool,
    ScreenshotTool,
    EditTool,
    BashTool,
    ToolResult,
    ToolError,
)


server = Server("computer-control-mcp")


class ComputerControlServer:
    """MCP server for computer control operations."""
    
    def __init__(self):
        self.computer = ComputerTool()
        self.screenshot = ScreenshotTool()
        self.edit = EditTool()
        self.bash = BashTool()
        
    async def take_screenshot(self) -> dict[str, Any]:
        """Take a screenshot and return it as base64."""
        try:
            result = await self.screenshot.run()
            if isinstance(result, ToolResult):
                if result.base64_image:
                    return {
                        "type": "image",
                        "data": result.base64_image,
                        "format": "png"
                    }
            return {"type": "error", "message": "Failed to capture screenshot"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    async def click(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        """Click at specified coordinates."""
        try:
            action = f"click_{button}" if button in ["left", "right", "middle"] else "click"
            result = await self.computer.run(action=action, coordinate=[x, y])
            if isinstance(result, ToolResult):
                return {"type": "success", "message": f"Clicked at ({x}, {y})"}
            return {"type": "error", "message": "Click failed"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    async def type_text(self, text: str) -> dict[str, Any]:
        """Type text at current cursor position."""
        try:
            result = await self.computer.run(action="type", text=text)
            if isinstance(result, ToolResult):
                return {"type": "success", "message": f"Typed: {text}"}
            return {"type": "error", "message": "Typing failed"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    async def key(self, key: str) -> dict[str, Any]:
        """Press a specific key."""
        try:
            result = await self.computer.run(action="key", key=key)
            if isinstance(result, ToolResult):
                return {"type": "success", "message": f"Pressed key: {key}"}
            return {"type": "error", "message": "Key press failed"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    async def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> dict[str, Any]:
        """Drag from start to end coordinates."""
        try:
            result = await self.computer.run(
                action="drag",
                coordinate=[start_x, start_y],
                coordinate2=[end_x, end_y]
            )
            if isinstance(result, ToolResult):
                return {"type": "success", "message": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"}
            return {"type": "error", "message": "Drag failed"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    async def scroll(self, x: int, y: int, direction: str, amount: int = 3) -> dict[str, Any]:
        """Scroll at specified coordinates."""
        try:
            result = await self.computer.run(
                action="scroll",
                coordinate=[x, y],
                direction=direction,
                amount=amount
            )
            if isinstance(result, ToolResult):
                return {"type": "success", "message": f"Scrolled {direction} by {amount}"}
            return {"type": "error", "message": "Scroll failed"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    async def execute_bash(self, command: str) -> dict[str, Any]:
        """Execute a bash command."""
        try:
            result = await self.bash.run(command=command)
            if isinstance(result, ToolResult):
                return {
                    "type": "success",
                    "output": result.output or "",
                    "error": result.error or ""
                }
            return {"type": "error", "message": "Command execution failed"}
        except Exception as e:
            return {"type": "error", "message": str(e)}
    
    async def edit_file(self, path: str, content: str, view_range: Optional[tuple[int, int]] = None) -> dict[str, Any]:
        """Edit a file with specified content."""
        try:
            kwargs = {"path": path, "content": content}
            if view_range:
                kwargs["view_range"] = view_range
            result = await self.edit.run(**kwargs)
            if isinstance(result, ToolResult):
                return {"type": "success", "message": f"File edited: {path}"}
            return {"type": "error", "message": "File edit failed"}
        except Exception as e:
            return {"type": "error", "message": str(e)}


computer_server = ComputerControlServer()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available computer control tools."""
    return [
        Tool(
            name="screenshot",
            description="Take a screenshot of the current screen",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="click",
            description="Click at specified coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "default": "left",
                        "description": "Mouse button to click"
                    }
                },
                "required": ["x", "y"]
            }
        ),
        Tool(
            name="type",
            description="Type text at current cursor position",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"}
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="key",
            description="Press a specific key",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to press (e.g., 'Return', 'Tab', 'Escape')"}
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="drag",
            description="Drag from start to end coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer", "description": "Starting X coordinate"},
                    "start_y": {"type": "integer", "description": "Starting Y coordinate"},
                    "end_x": {"type": "integer", "description": "Ending X coordinate"},
                    "end_y": {"type": "integer", "description": "Ending Y coordinate"}
                },
                "required": ["start_x", "start_y", "end_x", "end_y"]
            }
        ),
        Tool(
            name="scroll",
            description="Scroll at specified coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right"],
                        "description": "Scroll direction"
                    },
                    "amount": {
                        "type": "integer",
                        "default": 3,
                        "description": "Amount to scroll"
                    }
                },
                "required": ["x", "y", "direction"]
            }
        ),
        Tool(
            name="bash",
            description="Execute a bash command",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Bash command to execute"}
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="edit_file",
            description="Edit a file with specified content",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "New file content"},
                    "view_range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                        "description": "Optional line range to view [start, end]"
                    }
                },
                "required": ["path", "content"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
    """Handle tool calls from MCP clients."""
    try:
        if name == "screenshot":
            result = await computer_server.take_screenshot()
            if result["type"] == "image":
                return [ImageContent(
                    type="image",
                    data=result["data"],
                    mimeType="image/png"
                )]
            else:
                return [TextContent(type="text", text=result["message"])]
        
        elif name == "click":
            result = await computer_server.click(
                arguments["x"],
                arguments["y"],
                arguments.get("button", "left")
            )
            return [TextContent(type="text", text=result["message"])]
        
        elif name == "type":
            result = await computer_server.type_text(arguments["text"])
            return [TextContent(type="text", text=result["message"])]
        
        elif name == "key":
            result = await computer_server.key(arguments["key"])
            return [TextContent(type="text", text=result["message"])]
        
        elif name == "drag":
            result = await computer_server.drag(
                arguments["start_x"],
                arguments["start_y"],
                arguments["end_x"],
                arguments["end_y"]
            )
            return [TextContent(type="text", text=result["message"])]
        
        elif name == "scroll":
            result = await computer_server.scroll(
                arguments["x"],
                arguments["y"],
                arguments["direction"],
                arguments.get("amount", 3)
            )
            return [TextContent(type="text", text=result["message"])]
        
        elif name == "bash":
            result = await computer_server.execute_bash(arguments["command"])
            if result["type"] == "success":
                output = result.get("output", "")
                error = result.get("error", "")
                text = f"Output: {output}" if output else ""
                if error:
                    text += f"\nError: {error}" if text else f"Error: {error}"
                return [TextContent(type="text", text=text or "Command executed successfully")]
            else:
                return [TextContent(type="text", text=result["message"])]
        
        elif name == "edit_file":
            result = await computer_server.edit_file(
                arguments["path"],
                arguments["content"],
                arguments.get("view_range")
            )
            return [TextContent(type="text", text=result["message"])]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with stdio_handler(server):
        await server.run(
            InitializationOptions(
                server_name="computer-control-mcp",
                server_version="1.0.0"
            )
        )


if __name__ == "__main__":
    asyncio.run(main())