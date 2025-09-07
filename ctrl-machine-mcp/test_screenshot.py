#!/usr/bin/env python3
"""Test script for Screenshot MCP server functionality."""

import time
import mss
import pyautogui
from PIL import ImageGrab
import base64
from io import BytesIO


def test_mss_backend():
    """Test MSS screenshot backend."""
    print("\n1. Testing MSS backend...")
    with mss.mss() as sct:
        # Capture primary monitor
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        print(f"   ✓ MSS captured: {screenshot.width}x{screenshot.height}")
        
        # Test region capture
        region = {"top": 100, "left": 100, "width": 500, "height": 400}
        screenshot = sct.grab(region)
        print(f"   ✓ MSS region: {screenshot.width}x{screenshot.height}")
    return True


def test_pyautogui_backend():
    """Test PyAutoGUI screenshot backend."""
    print("\n2. Testing PyAutoGUI backend...")
    
    # Full screen
    screenshot = pyautogui.screenshot()
    print(f"   ✓ PyAutoGUI full: {screenshot.width}x{screenshot.height}")
    
    # Region capture
    region_shot = pyautogui.screenshot(region=(100, 100, 500, 400))
    print(f"   ✓ PyAutoGUI region: {region_shot.width}x{region_shot.height}")
    return True


def test_pil_backend():
    """Test PIL/Pillow screenshot backend."""
    print("\n3. Testing PIL backend...")
    
    # Full screen
    screenshot = ImageGrab.grab()
    print(f"   ✓ PIL full: {screenshot.width}x{screenshot.height}")
    
    # Region capture
    bbox = (100, 100, 600, 500)
    region_shot = ImageGrab.grab(bbox=bbox)
    print(f"   ✓ PIL region: {region_shot.width}x{region_shot.height}")
    return True


def test_base64_encoding():
    """Test image to base64 encoding."""
    print("\n4. Testing base64 encoding...")
    
    # Capture small screenshot
    screenshot = pyautogui.screenshot(region=(0, 0, 100, 100))
    
    # Convert to base64
    buffered = BytesIO()
    screenshot.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    print(f"   ✓ Base64 encoded: {len(img_base64)} chars")
    print(f"   ✓ Starts with: {img_base64[:50]}...")
    return True


def test_screen_info():
    """Test screen information gathering."""
    print("\n5. Testing screen info...")
    
    # PyAutoGUI screen size
    size = pyautogui.size()
    print(f"   ✓ Primary screen: {size.width}x{size.height}")
    
    # MSS monitors info
    with mss.mss() as sct:
        print(f"   ✓ Total monitors: {len(sct.monitors) - 1}")
        for i, monitor in enumerate(sct.monitors):
            if i == 0:  # Skip combined monitor
                continue
            print(f"     Monitor {i}: {monitor['width']}x{monitor['height']} at ({monitor['left']}, {monitor['top']})")
    
    return True


def test_performance():
    """Test screenshot capture performance."""
    print("\n6. Testing performance...")
    
    # MSS performance
    start = time.time()
    with mss.mss() as sct:
        for _ in range(5):
            sct.grab(sct.monitors[1])
    mss_time = time.time() - start
    print(f"   ✓ MSS: 5 captures in {mss_time:.2f}s ({5/mss_time:.1f} fps)")
    
    # PyAutoGUI performance
    start = time.time()
    for _ in range(5):
        pyautogui.screenshot()
    pyautogui_time = time.time() - start
    print(f"   ✓ PyAutoGUI: 5 captures in {pyautogui_time:.2f}s ({5/pyautogui_time:.1f} fps)")
    
    # PIL performance
    start = time.time()
    for _ in range(5):
        ImageGrab.grab()
    pil_time = time.time() - start
    print(f"   ✓ PIL: 5 captures in {pil_time:.2f}s ({5/pil_time:.1f} fps)")
    
    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("Screenshot MCP Test Suite")
    print("=" * 50)
    
    tests = [
        ("MSS Backend", test_mss_backend),
        ("PyAutoGUI Backend", test_pyautogui_backend),
        ("PIL Backend", test_pil_backend),
        ("Base64 Encoding", test_base64_encoding),
        ("Screen Info", test_screen_info),
        ("Performance", test_performance)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"   ✗ {name} failed")
        except Exception as e:
            failed += 1
            print(f"   ✗ {name} error: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())