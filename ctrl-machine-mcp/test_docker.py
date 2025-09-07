#!/usr/bin/env python3
"""Test script to verify HID input functionality in Docker container."""

import pyautogui
import time
import sys

def test_hid_input():
    """Test HID input capabilities."""
    print("Starting HID Input Docker Test...")
    print("-" * 50)
    
    # Configure PyAutoGUI
    pyautogui.FAILSAFE = False  # Disable failsafe in container
    pyautogui.PAUSE = 0.5
    
    try:
        # Test 1: Screen detection
        print("1. Testing screen detection...")
        width, height = pyautogui.size()
        print(f"   ✓ Screen size: {width}x{height}")
        
        # Test 2: Mouse position
        print("\n2. Testing mouse position...")
        x, y = pyautogui.position()
        print(f"   ✓ Current mouse position: ({x}, {y})")
        
        # Test 3: Mouse movement
        print("\n3. Testing mouse movement...")
        center_x, center_y = width // 2, height // 2
        pyautogui.moveTo(center_x, center_y, duration=1)
        new_x, new_y = pyautogui.position()
        print(f"   ✓ Moved mouse to center: ({new_x}, {new_y})")
        
        # Test 4: Mouse click
        print("\n4. Testing mouse click...")
        pyautogui.click(center_x, center_y)
        print(f"   ✓ Clicked at ({center_x}, {center_y})")
        
        # Test 5: Keyboard typing
        print("\n5. Testing keyboard input...")
        test_text = "HID Input Test Success!"
        # Note: In container, this types into the virtual display
        pyautogui.typewrite(test_text, interval=0.05)
        print(f"   ✓ Typed text: '{test_text}'")
        
        # Test 6: Key combinations
        print("\n6. Testing key combinations...")
        pyautogui.hotkey('ctrl', 'a')
        print("   ✓ Pressed Ctrl+A")
        
        # Test 7: Screenshot capability
        print("\n7. Testing screenshot capability...")
        screenshot = pyautogui.screenshot()
        screenshot.save('/tmp/test_screenshot.png')
        print("   ✓ Screenshot saved to /tmp/test_screenshot.png")
        
        print("\n" + "=" * 50)
        print("✅ All HID input tests passed successfully!")
        print("=" * 50)
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_hid_input())