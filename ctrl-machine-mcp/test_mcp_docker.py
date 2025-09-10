#!/usr/bin/env python3
"""Test script for Docker MCP servers."""

import json
import requests
import time
import base64
from datetime import datetime

# Server URLs
SCREENSHOT_URL = "http://localhost:8080"
HID_URL = "http://localhost:8081"

def test_health():
    """Test health endpoints."""
    print("🏥 Testing health endpoints...")
    
    # Screenshot MCP
    response = requests.get(f"{SCREENSHOT_URL}/health")
    if response.status_code == 200:
        print(f"✅ Screenshot MCP: {response.json()}")
    else:
        print(f"❌ Screenshot MCP failed: {response.status_code}")
    
    # HID Input MCP
    response = requests.get(f"{HID_URL}/health")
    if response.status_code == 200:
        print(f"✅ HID Input MCP: {response.json()}")
    else:
        print(f"❌ HID Input MCP failed: {response.status_code}")
    
    print()

def test_tools_list():
    """Test tools listing."""
    print("🔧 Testing tools listing...")
    
    # Screenshot tools
    response = requests.get(f"{SCREENSHOT_URL}/tools")
    if response.status_code == 200:
        tools = response.json().get("tools", [])
        print(f"📷 Screenshot tools: {[t['name'] for t in tools]}")
    
    # HID tools
    response = requests.get(f"{HID_URL}/tools")
    if response.status_code == 200:
        tools = response.json().get("tools", [])
        print(f"🖱️ HID Input tools: {[t['name'] for t in tools]}")
    
    print()

def test_screenshot_capture():
    """Test screenshot capture."""
    print("📸 Testing screenshot capture...")
    
    # Full screen capture
    response = requests.post(f"{SCREENSHOT_URL}/capture", json={})
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ Full screenshot captured: {result.get('filename')}")
            print(f"   Dimensions: {result.get('dimensions')}")
        else:
            print(f"❌ Screenshot failed: {result.get('error')}")
    
    # Region capture
    response = requests.post(f"{SCREENSHOT_URL}/capture", json={
        "region": {"top": 100, "left": 100, "width": 500, "height": 400}
    })
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ Region screenshot captured: {result.get('filename')}")
    
    print()

def test_mouse_operations():
    """Test mouse operations."""
    print("🖱️ Testing mouse operations...")
    
    # Move mouse
    response = requests.post(f"{HID_URL}/move", json={
        "x": 960, "y": 540, "duration": 0.5
    })
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ Mouse moved to center: {result.get('position')}")
    
    time.sleep(0.5)
    
    # Click mouse
    response = requests.post(f"{HID_URL}/click", json={
        "x": 960, "y": 540, "button": "left", "clicks": 1
    })
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ Mouse clicked at center")
    
    print()

def test_keyboard_operations():
    """Test keyboard operations."""
    print("⌨️ Testing keyboard operations...")
    
    # Press key
    response = requests.post(f"{HID_URL}/press", json={
        "key": "escape", "presses": 1
    })
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ Pressed ESC key")
    
    # Type text (using proper JSON encoding)
    text_data = {"text": "Hello MCP Docker!", "interval": 0.05}
    response = requests.post(
        f"{HID_URL}/type",
        json=text_data,
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ Typed text successfully")
    else:
        print(f"❌ Type text failed: {response.text}")
    
    # Hotkey
    response = requests.post(f"{HID_URL}/hotkey", json={
        "keys": ["ctrl", "a"]
    })
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print(f"✅ Pressed Ctrl+A hotkey")
    
    print()

def test_mcp_protocol():
    """Test MCP protocol endpoints."""
    print("🔌 Testing MCP protocol...")
    
    # Test tools/list via MCP
    response = requests.post(f"{SCREENSHOT_URL}/mcp", json={
        "method": "tools/list",
        "params": {}
    })
    if response.status_code == 200:
        result = response.json()
        tools = result.get("tools", [])
        print(f"✅ Screenshot MCP tools/list: {len(tools)} tools")
    
    # Test tools/call for screenshot
    response = requests.post(f"{SCREENSHOT_URL}/mcp", json={
        "method": "tools/call",
        "params": {
            "name": "capture_screenshot",
            "arguments": {}
        }
    })
    if response.status_code == 200:
        result = response.json()
        content = result.get("content", [])
        if content and content[0].get("type") == "image":
            print(f"✅ Screenshot captured via MCP protocol")
    
    print()

def main():
    """Run all tests."""
    print("=" * 50)
    print("🚀 Docker MCP Server Test Suite")
    print("=" * 50)
    print()
    
    test_health()
    test_tools_list()
    test_screenshot_capture()
    test_mouse_operations()
    test_keyboard_operations()
    test_mcp_protocol()
    
    print("=" * 50)
    print("✨ Test suite completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()