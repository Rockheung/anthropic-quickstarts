#!/usr/bin/env python3
"""
Test MCP Server - A simple MCP server for testing
Implements the MCP protocol with basic test tools
"""

import sys
import json
import logging
from typing import Any, Dict, Optional
import asyncio
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, filename='/tmp/test_mcp_server.log')
logger = logging.getLogger(__name__)

class TestMCPServer:
    def __init__(self):
        self.server_info = {
            "name": "test-mcp-server",
            "version": "1.0.0",
            "capabilities": {
                "tools": True,
                "resources": False,
                "prompts": False
            }
        }
        
        self.tools = {
            "echo": {
                "description": "Echo back the input message",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to echo back"
                        }
                    },
                    "required": ["message"]
                }
            },
            "get_time": {
                "description": "Get the current time",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "description": "Time format (iso, unix, human)",
                            "enum": ["iso", "unix", "human"],
                            "default": "iso"
                        }
                    }
                }
            },
            "calculate": {
                "description": "Perform a simple calculation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            },
            "test_error": {
                "description": "Test error handling by throwing an error",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "error_message": {
                            "type": "string",
                            "description": "Custom error message",
                            "default": "Test error occurred"
                        }
                    }
                }
            }
        }

    def send_response(self, id: Optional[str], result: Any = None, error: Any = None):
        response = {"jsonrpc": "2.0"}
        if id is not None:
            response["id"] = id
        if error is not None:
            response["error"] = error
        else:
            response["result"] = result
        
        output = json.dumps(response) + "\n"
        sys.stdout.write(output)
        sys.stdout.flush()
        logger.debug(f"Sent response: {output.strip()}")

    def handle_initialize(self, id: str, params: Dict[str, Any]):
        result = {
            "protocolVersion": "2025-06-18",
            "serverInfo": self.server_info
        }
        self.send_response(id, result)

    def handle_tools_list(self, id: str):
        tools_list = []
        for name, tool_info in self.tools.items():
            tools_list.append({
                "name": name,
                "description": tool_info["description"],
                "inputSchema": tool_info["inputSchema"]
            })
        
        self.send_response(id, {"tools": tools_list})

    def handle_tools_call(self, id: str, params: Dict[str, Any]):
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            self.send_response(id, error={
                "code": -32602,
                "message": f"Unknown tool: {tool_name}"
            })
            return
        
        try:
            if tool_name == "echo":
                result = {
                    "content": [{
                        "type": "text",
                        "text": f"Echo: {arguments.get('message', '')}"
                    }]
                }
            
            elif tool_name == "get_time":
                format_type = arguments.get("format", "iso")
                now = datetime.now()
                
                if format_type == "iso":
                    time_str = now.isoformat()
                elif format_type == "unix":
                    time_str = str(int(now.timestamp()))
                else:  # human
                    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
                
                result = {
                    "content": [{
                        "type": "text",
                        "text": f"Current time ({format_type}): {time_str}"
                    }]
                }
            
            elif tool_name == "calculate":
                expression = arguments.get("expression", "")
                try:
                    # Safe evaluation of simple math expressions
                    import ast
                    import operator as op
                    
                    ops = {
                        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                        ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg
                    }
                    
                    def eval_expr(node):
                        if isinstance(node, ast.Num):
                            return node.n
                        elif isinstance(node, ast.BinOp):
                            return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
                        elif isinstance(node, ast.UnaryOp):
                            return ops[type(node.op)](eval_expr(node.operand))
                        else:
                            raise ValueError("Unsupported expression")
                    
                    tree = ast.parse(expression, mode='eval')
                    result_value = eval_expr(tree.body)
                    
                    result = {
                        "content": [{
                            "type": "text",
                            "text": f"{expression} = {result_value}"
                        }]
                    }
                except Exception as e:
                    result = {
                        "content": [{
                            "type": "text",
                            "text": f"Error evaluating expression: {str(e)}"
                        }]
                    }
            
            elif tool_name == "test_error":
                error_msg = arguments.get("error_message", "Test error occurred")
                raise Exception(error_msg)
            
            self.send_response(id, result)
            
        except Exception as e:
            self.send_response(id, error={
                "code": -32603,
                "message": f"Tool execution error: {str(e)}"
            })

    def handle_request(self, request: Dict[str, Any]):
        method = request.get("method")
        id = request.get("id")
        params = request.get("params", {})
        
        logger.debug(f"Handling request: {method}")
        
        if method == "initialize":
            self.handle_initialize(id, params)
        elif method == "tools/list":
            self.handle_tools_list(id)
        elif method == "tools/call":
            self.handle_tools_call(id, params)
        else:
            self.send_response(id, error={
                "code": -32601,
                "message": f"Method not found: {method}"
            })

    async def run(self):
        logger.info("Test MCP Server starting...")
        
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                logger.debug(f"Received: {line}")
                
                try:
                    request = json.loads(line)
                    self.handle_request(request)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    self.send_response(None, error={
                        "code": -32700,
                        "message": "Parse error"
                    })
                    
            except Exception as e:
                logger.error(f"Server error: {e}")
                break
        
        logger.info("Test MCP Server shutting down...")

def main():
    server = TestMCPServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()