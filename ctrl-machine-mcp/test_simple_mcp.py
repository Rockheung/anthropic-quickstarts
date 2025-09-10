#!/usr/bin/env python3
"""Minimal MCP server for testing."""

import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ServerCapabilities

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server
server = Server("test-mcp")

@server.list_tools()
async def list_tools():
    """List available tools."""
    return [
        Tool(
            name="test_tool",
            description="A simple test tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    if name == "test_tool":
        message = arguments.get("message", "No message provided")
        return [TextContent(type="text", text=f"Test response: {message}")]
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Run the server."""
    logger.info("Starting test MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="test-mcp",
                server_version="1.0.0",
                capabilities=ServerCapabilities(tools={}),
            )
        )

if __name__ == "__main__":
    asyncio.run(main())