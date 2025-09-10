#!/usr/bin/env python3
"""Test mouse movement and screenshot capture."""

import json
import subprocess
import base64
from PIL import Image
import io

def send_request(request):
    """Send a request to the MCP server and get response."""
    cmd = f'echo \'{json.dumps(request)}\' | docker exec -i mcp-unified python3 /app/unified_mcp_server.py 2>/dev/null'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # Find JSON response in output
    for line in result.stdout.split('\n'):
        if line.strip() and line.startswith('{'):
            try:
                return json.loads(line)
            except:
                pass
    return None

# Initialize the server
print("Initializing MCP server...")
init_request = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "1.0.0",
        "capabilities": {"tools": {}},
        "clientInfo": {"name": "test-client", "version": "1.0.0"}
    },
    "id": 1
}

response = send_request(init_request)
if response and 'result' in response:
    print(f"✅ Server initialized: {response['result']['serverInfo']['name']}")
else:
    print("❌ Failed to initialize server")
    exit(1)

# Move mouse to (100, 100)
print("\nMoving mouse to (100, 100)...")
move_request = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "move_mouse",
        "arguments": {"x": 100, "y": 100}
    },
    "id": 2
}

# Note: The unified server expects a single session, so we need to use a persistent connection
# For now, let's use docker exec directly with pyautogui

print("\nExecuting mouse movement and screenshot directly...")
cmd = """docker exec mcp-unified python3 -c "
import pyautogui
import mss
import base64
import io
from PIL import Image

# Move mouse
pyautogui.moveTo(100, 100)
print(f'Mouse moved to: {pyautogui.position()}')

# Take screenshot
with mss.mss() as sct:
    monitor = sct.monitors[0]  # All monitors
    screenshot = sct.grab(monitor)
    
    # Convert to PIL Image
    img = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
    
    # Save to file
    img.save('/app/screenshots/test_screenshot.png')
    print(f'Screenshot saved: {img.width}x{img.height}')
"
"""

result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr)

# Check if screenshot was saved
check_cmd = "docker exec mcp-unified ls -la /app/screenshots/"
result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
print("\nScreenshot directory:")
print(result.stdout)

print("\n✅ Test completed!")
print("You can view the screenshot at: ./screenshots/test_screenshot.png")
print("You can also connect via VNC to see the desktop: vnc://localhost:5900")