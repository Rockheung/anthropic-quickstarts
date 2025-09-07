#!/usr/bin/env python3
"""Combined test for HID Input and Screenshot MCP servers."""

import pyautogui
import mss
from PIL import ImageGrab
import time
import base64
from io import BytesIO


def test_combined_automation():
    """Test combined HID input and screenshot capabilities."""
    print("=" * 60)
    print("Combined HID Input + Screenshot Test")
    print("=" * 60)
    
    # Configure PyAutoGUI safety
    pyautogui.FAILSAFE = False  # Disable in container
    pyautogui.PAUSE = 0.1
    
    # 1. Capture initial screenshot
    print("\n1. Capturing initial screen state...")
    with mss.mss() as sct:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        initial_shot = sct.grab(monitor)
        print(f"   ✓ Initial screenshot: {initial_shot.width}x{initial_shot.height}")
    
    # 2. Get current mouse position
    print("\n2. Getting mouse position...")
    initial_pos = pyautogui.position()
    print(f"   ✓ Initial mouse position: ({initial_pos[0]}, {initial_pos[1]})")
    
    # 3. Move mouse to center
    print("\n3. Moving mouse to center...")
    screen_width, screen_height = pyautogui.size()
    center_x = screen_width // 2
    center_y = screen_height // 2
    pyautogui.moveTo(center_x, center_y, duration=0.5)
    print(f"   ✓ Moved to center: ({center_x}, {center_y})")
    
    # 4. Capture screenshot after movement
    print("\n4. Capturing after mouse movement...")
    after_move = pyautogui.screenshot()
    print(f"   ✓ Screenshot after move: {after_move.width}x{after_move.height}")
    
    # 5. Simulate click
    print("\n5. Simulating mouse click...")
    pyautogui.click()
    print(f"   ✓ Clicked at ({center_x}, {center_y})")
    
    # 6. Type test text
    print("\n6. Simulating keyboard input...")
    test_text = "HID_Screenshot_Test"
    pyautogui.typewrite(test_text, interval=0.05)
    print(f"   ✓ Typed: '{test_text}'")
    
    # 7. Capture final screenshot
    print("\n7. Capturing final state...")
    final_shot = ImageGrab.grab()
    print(f"   ✓ Final screenshot: {final_shot.width}x{final_shot.height}")
    
    # 8. Encode screenshot to base64 (like MCP would)
    print("\n8. Testing base64 encoding...")
    buffered = BytesIO()
    # Create a small thumbnail for encoding test
    thumbnail = final_shot.resize((200, 150))
    thumbnail.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    print(f"   ✓ Encoded thumbnail: {len(img_base64)} chars")
    
    # 9. Test screen info gathering
    print("\n9. Gathering screen information...")
    with mss.mss() as sct:
        print(f"   ✓ Monitors: {len(sct.monitors) - 1}")
        print(f"   ✓ Primary size: {screen_width}x{screen_height}")
    
    # 10. Performance test
    print("\n10. Testing capture performance...")
    start = time.time()
    for i in range(10):
        pyautogui.screenshot()
    elapsed = time.time() - start
    fps = 10 / elapsed
    print(f"   ✓ Captured 10 frames in {elapsed:.2f}s ({fps:.1f} fps)")
    
    print("\n" + "=" * 60)
    print("✅ Combined test completed successfully!")
    print("=" * 60)
    
    return 0


def test_docker_environment():
    """Test if running in Docker with virtual display."""
    import os
    
    print("\nEnvironment Check:")
    display = os.environ.get('DISPLAY', 'Not set')
    print(f"   DISPLAY: {display}")
    
    if display == ':99':
        print("   ✓ Running in Docker with virtual display")
    else:
        print("   ✓ Running on host system")
    
    # Check if Xvfb is running (Docker)
    try:
        import subprocess
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'Xvfb' in result.stdout:
            print("   ✓ Xvfb virtual framebuffer detected")
        else:
            print("   ✓ Using system display")
    except:
        pass


def main():
    """Run combined tests."""
    try:
        test_docker_environment()
        return test_combined_automation()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())