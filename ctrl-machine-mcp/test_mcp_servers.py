"""Integration tests for HID Input and Screenshot MCP servers."""

import asyncio
import json
import pytest
import sys
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Mock the MCP imports for testing
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.server'] = MagicMock()
sys.modules['mcp.server.models'] = MagicMock()
sys.modules['mcp.server.stdio'] = MagicMock()
sys.modules['mcp.types'] = MagicMock()

# Import after mocking
from hid_input_mcp import HIDInputController, InputEvent, MouseButton
from screenshot_mcp import ScreenshotCapture, CaptureMode, CaptureRegion, Screenshot


class TestHIDInputController:
    """Test HID Input Controller functionality."""
    
    @pytest.fixture
    def controller(self):
        """Create a controller instance for testing."""
        with patch('hid_input_mcp.pynput'):
            with patch('hid_input_mcp.pyautogui'):
                controller = HIDInputController()
                yield controller
    
    @pytest.mark.asyncio
    async def test_move_mouse(self, controller):
        """Test mouse movement."""
        with patch.object(controller, 'mouse_controller') as mock_mouse:
            result = await controller.move_mouse(100, 200)
            
            assert result['success'] is True
            assert result['position'] == {'x': 100, 'y': 200}
            assert 'Mouse moved to' in result['message']
            mock_mouse.position = (100, 200)
    
    @pytest.mark.asyncio
    async def test_click_mouse(self, controller):
        """Test mouse clicking."""
        with patch.object(controller, 'mouse_controller') as mock_mouse:
            mock_mouse.position = (150, 250)
            
            result = await controller.click_mouse(150, 250, button='left', clicks=2)
            
            assert result['success'] is True
            assert result['button'] == 'left'
            assert result['clicks'] == 2
    
    @pytest.mark.asyncio
    async def test_type_text(self, controller):
        """Test text typing."""
        with patch.object(controller, 'keyboard_controller') as mock_keyboard:
            test_text = "Hello, World!"
            result = await controller.type_text(test_text)
            
            assert result['success'] is True
            assert result['text_length'] == len(test_text)
            assert f"Typed {len(test_text)} characters" in result['message']
    
    @pytest.mark.asyncio
    async def test_press_key(self, controller):
        """Test key pressing."""
        with patch.object(controller, 'keyboard_controller') as mock_keyboard:
            result = await controller.press_key('enter')
            
            assert result['success'] is True
            assert result['key'] == 'enter'
            assert 'Pressed key: enter' in result['message']
    
    @pytest.mark.asyncio
    async def test_press_key_with_modifiers(self, controller):
        """Test key pressing with modifiers."""
        with patch('hid_input_mcp.pyautogui.hotkey') as mock_hotkey:
            result = await controller.press_key('c', modifiers=['ctrl'])
            
            assert result['success'] is True
            assert result['key'] == 'c'
            assert result['modifiers'] == ['ctrl']
            mock_hotkey.assert_called_once_with('ctrl', 'c')
    
    @pytest.mark.asyncio
    async def test_drag_mouse(self, controller):
        """Test mouse dragging."""
        with patch('hid_input_mcp.pyautogui.dragTo') as mock_drag:
            result = await controller.drag_mouse(10, 20, 100, 200, duration=0.5)
            
            assert result['success'] is True
            assert result['start'] == {'x': 10, 'y': 20}
            assert result['end'] == {'x': 100, 'y': 200}
            mock_drag.assert_called_once_with(100, 200, duration=0.5, button='left')
    
    @pytest.mark.asyncio
    async def test_scroll_mouse(self, controller):
        """Test mouse scrolling."""
        with patch('hid_input_mcp.pyautogui.scroll') as mock_scroll:
            result = await controller.scroll_mouse(x=100, y=100, clicks=5, direction='up')
            
            assert result['success'] is True
            assert result['direction'] == 'up'
            assert result['amount'] == 5
            mock_scroll.assert_called_once_with(5)
    
    @pytest.mark.asyncio
    async def test_get_mouse_position(self, controller):
        """Test getting mouse position."""
        with patch.object(controller, 'mouse_controller') as mock_mouse:
            mock_mouse.position = (300, 400)
            
            result = await controller.get_mouse_position()
            
            assert result['success'] is True
            assert result['position'] == {'x': 300, 'y': 400}
    
    @pytest.mark.asyncio
    async def test_event_history(self, controller):
        """Test event history tracking."""
        # Simulate some events
        controller._log_event(InputEvent(
            event_type='test_event',
            timestamp=time.time(),
            details={'test': 'data'},
            success=True
        ))
        
        history = await controller.get_event_history(limit=5)
        
        assert len(history) >= 1
        assert history[-1]['type'] == 'test_event'
        assert history[-1]['success'] is True
    
    @pytest.mark.asyncio
    async def test_human_typing_simulation(self, controller):
        """Test human-like typing simulation."""
        with patch.object(controller, 'keyboard_controller') as mock_keyboard:
            with patch('asyncio.sleep') as mock_sleep:
                result = await controller.type_text("Hi", simulate_human=True)
                
                assert result['success'] is True
                assert mock_sleep.called
                # Should have delays between characters


class TestScreenshotCapture:
    """Test Screenshot Capture functionality."""
    
    @pytest.fixture
    def capture(self):
        """Create a capture instance for testing."""
        with patch('screenshot_mcp.mss.mss'):
            with patch('screenshot_mcp.pyautogui'):
                capture = ScreenshotCapture()
                yield capture
    
    def create_mock_image(self):
        """Create a mock PIL Image."""
        with patch('screenshot_mcp.PIL.Image') as mock_image_class:
            mock_image = MagicMock()
            mock_image.width = 1920
            mock_image.height = 1080
            mock_image_class.frombytes.return_value = mock_image
            return mock_image
    
    @pytest.mark.asyncio
    async def test_capture_full_screen(self, capture):
        """Test full screen capture."""
        with patch.object(capture.sct, 'grab') as mock_grab:
            with patch('screenshot_mcp.PIL.Image.frombytes') as mock_frombytes:
                mock_screenshot = MagicMock()
                mock_screenshot.width = 1920
                mock_screenshot.height = 1080
                mock_screenshot.rgb = b'mock_rgb_data'
                mock_grab.return_value = mock_screenshot
                
                mock_image = MagicMock()
                mock_image.width = 1920
                mock_image.height = 1080
                mock_frombytes.return_value = mock_image
                
                with patch.object(capture, '_image_to_base64', return_value='base64_data'):
                    result = await capture.capture_full_screen()
                    
                    assert isinstance(result, Screenshot)
                    assert result.mode == CaptureMode.FULL_SCREEN
                    assert result.base64_data == 'base64_data'
                    assert result.metadata['width'] == 1920
                    assert result.metadata['height'] == 1080
    
    @pytest.mark.asyncio
    async def test_capture_region(self, capture):
        """Test region capture."""
        region = CaptureRegion(x=100, y=100, width=800, height=600)
        
        with patch.object(capture.sct, 'grab') as mock_grab:
            with patch('screenshot_mcp.PIL.Image.frombytes') as mock_frombytes:
                mock_screenshot = MagicMock()
                mock_screenshot.width = 800
                mock_screenshot.height = 600
                mock_screenshot.rgb = b'mock_rgb_data'
                mock_grab.return_value = mock_screenshot
                
                mock_image = MagicMock()
                mock_image.width = 800
                mock_image.height = 600
                mock_frombytes.return_value = mock_image
                
                with patch.object(capture, '_image_to_base64', return_value='base64_data'):
                    result = await capture.capture_region(region)
                    
                    assert isinstance(result, Screenshot)
                    assert result.mode == CaptureMode.REGION
                    assert result.metadata['region']['x'] == 100
                    assert result.metadata['region']['y'] == 100
                    assert result.metadata['region']['width'] == 800
                    assert result.metadata['region']['height'] == 600
    
    @pytest.mark.asyncio
    async def test_start_periodic_capture(self, capture):
        """Test starting periodic capture."""
        result = await capture.start_periodic_capture(interval=2.0, mode=CaptureMode.FULL_SCREEN)
        
        assert result['success'] is True
        assert capture.capture_enabled is True
        assert capture.capture_interval == 2.0
        assert 'Started periodic capture' in result['message']
        
        # Stop the capture
        await capture.stop_periodic_capture()
    
    @pytest.mark.asyncio
    async def test_stop_periodic_capture(self, capture):
        """Test stopping periodic capture."""
        # Start capture first
        await capture.start_periodic_capture(interval=1.0)
        
        # Now stop it
        result = await capture.stop_periodic_capture()
        
        assert result['success'] is True
        assert capture.capture_enabled is False
        assert 'Stopped periodic capture' in result['message']
    
    @pytest.mark.asyncio
    async def test_get_capture_status(self, capture):
        """Test getting capture status."""
        capture.capture_enabled = True
        capture.capture_interval = 1.5
        
        status = await capture.get_capture_status()
        
        assert status['enabled'] is True
        assert status['interval'] == 1.5
        assert 'history_count' in status
        assert 'max_history' in status
    
    @pytest.mark.asyncio
    async def test_capture_history(self, capture):
        """Test screenshot history management."""
        # Create mock screenshots
        for i in range(3):
            mock_image = MagicMock()
            mock_image.width = 1920
            mock_image.height = 1080
            
            screenshot = Screenshot(
                image=mock_image,
                mode=CaptureMode.FULL_SCREEN,
                timestamp=time.time() + i,
                metadata={'index': i},
                base64_data=f'base64_{i}'
            )
            capture.capture_history.append(screenshot)
        
        # Get latest screenshot
        latest = await capture.get_latest_screenshot()
        assert latest is not None
        assert latest.metadata['index'] == 2
        
        # Clear history
        result = await capture.clear_history()
        assert result['success'] is True
        assert 'Cleared 3 screenshots' in result['message']
        assert len(capture.capture_history) == 0
    
    @pytest.mark.asyncio
    async def test_find_browser_windows(self, capture):
        """Test finding browser windows."""
        with patch('sys.platform', 'darwin'):
            with patch('screenshot_mcp.Quartz.CGWindowListCopyWindowInfo') as mock_window_list:
                mock_window_list.return_value = [
                    {
                        'kCGWindowOwnerName': 'Google Chrome',
                        'kCGWindowName': 'Test Page',
                        'kCGWindowBounds': {'X': 0, 'Y': 0, 'Width': 1024, 'Height': 768}
                    }
                ]
                
                windows = await capture.find_browser_windows()
                
                assert len(windows) > 0
                assert windows[0]['name'] == 'Google Chrome'
                assert windows[0]['title'] == 'Test Page'
    
    @pytest.mark.asyncio
    async def test_capture_monitor(self, capture):
        """Test monitor-specific capture."""
        capture.sct.monitors = [
            {},  # Combined monitor
            {'left': 0, 'top': 0, 'width': 1920, 'height': 1080},  # Monitor 1
            {'left': 1920, 'top': 0, 'width': 1920, 'height': 1080}  # Monitor 2
        ]
        
        with patch.object(capture.sct, 'grab') as mock_grab:
            with patch('screenshot_mcp.PIL.Image.frombytes') as mock_frombytes:
                mock_screenshot = MagicMock()
                mock_screenshot.width = 1920
                mock_screenshot.height = 1080
                mock_screenshot.rgb = b'mock_rgb_data'
                mock_grab.return_value = mock_screenshot
                
                mock_image = MagicMock()
                mock_image.width = 1920
                mock_image.height = 1080
                mock_frombytes.return_value = mock_image
                
                with patch.object(capture, '_image_to_base64', return_value='base64_data'):
                    result = await capture.capture_monitor(monitor_index=1)
                    
                    assert isinstance(result, Screenshot)
                    assert result.mode == CaptureMode.MONITOR
                    assert result.metadata['monitor_index'] == 1


class TestMCPIntegration:
    """Test MCP server integration."""
    
    @pytest.mark.asyncio
    async def test_hid_mcp_tool_listing(self):
        """Test HID MCP tool listing."""
        from hid_input_mcp import list_tools
        
        with patch('hid_input_mcp.pynput'):
            with patch('hid_input_mcp.pyautogui'):
                tools = await list_tools()
                
                tool_names = [tool.name for tool in tools]
                assert 'move_mouse' in tool_names
                assert 'click_mouse' in tool_names
                assert 'type_text' in tool_names
                assert 'press_key' in tool_names
                assert 'drag_mouse' in tool_names
                assert 'scroll_mouse' in tool_names
                assert 'get_mouse_position' in tool_names
                assert 'get_event_history' in tool_names
    
    @pytest.mark.asyncio
    async def test_screenshot_mcp_tool_listing(self):
        """Test Screenshot MCP tool listing."""
        from screenshot_mcp import list_tools
        
        with patch('screenshot_mcp.mss.mss'):
            with patch('screenshot_mcp.pyautogui'):
                tools = await list_tools()
                
                tool_names = [tool.name for tool in tools]
                assert 'capture_screenshot' in tool_names
                assert 'start_periodic_capture' in tool_names
                assert 'stop_periodic_capture' in tool_names
                assert 'get_capture_status' in tool_names
                assert 'get_latest_screenshot' in tool_names
                assert 'find_browser_windows' in tool_names
                assert 'clear_history' in tool_names


@pytest.mark.asyncio
async def test_combined_workflow():
    """Test a combined workflow using both MCP servers."""
    with patch('hid_input_mcp.pynput'):
        with patch('hid_input_mcp.pyautogui'):
            with patch('screenshot_mcp.mss.mss'):
                with patch('screenshot_mcp.pyautogui'):
                    # Initialize controllers
                    hid_controller = HIDInputController()
                    screenshot_capture = ScreenshotCapture()
                    
                    # Simulate a workflow
                    # 1. Take initial screenshot
                    with patch.object(screenshot_capture, '_image_to_base64', return_value='base64_data'):
                        with patch.object(screenshot_capture.sct, 'grab') as mock_grab:
                            with patch('screenshot_mcp.PIL.Image.frombytes') as mock_frombytes:
                                mock_screenshot = MagicMock()
                                mock_screenshot.width = 1920
                                mock_screenshot.height = 1080
                                mock_screenshot.rgb = b'mock_rgb_data'
                                mock_grab.return_value = mock_screenshot
                                
                                mock_image = MagicMock()
                                mock_image.width = 1920
                                mock_image.height = 1080
                                mock_frombytes.return_value = mock_image
                                
                                screenshot1 = await screenshot_capture.capture_full_screen()
                                assert screenshot1 is not None
                    
                    # 2. Move mouse to position
                    with patch.object(hid_controller, 'mouse_controller'):
                        move_result = await hid_controller.move_mouse(500, 500)
                        assert move_result['success'] is True
                    
                    # 3. Click at position
                    with patch.object(hid_controller, 'mouse_controller'):
                        click_result = await hid_controller.click_mouse(500, 500)
                        assert click_result['success'] is True
                    
                    # 4. Type some text
                    with patch.object(hid_controller, 'keyboard_controller'):
                        type_result = await hid_controller.type_text("Test automation")
                        assert type_result['success'] is True
                    
                    # 5. Take final screenshot
                    with patch.object(screenshot_capture, '_image_to_base64', return_value='base64_data'):
                        with patch.object(screenshot_capture.sct, 'grab') as mock_grab:
                            with patch('screenshot_mcp.PIL.Image.frombytes') as mock_frombytes:
                                mock_screenshot = MagicMock()
                                mock_screenshot.width = 1920
                                mock_screenshot.height = 1080
                                mock_screenshot.rgb = b'mock_rgb_data'
                                mock_grab.return_value = mock_screenshot
                                
                                mock_image = MagicMock()
                                mock_image.width = 1920
                                mock_image.height = 1080
                                mock_frombytes.return_value = mock_image
                                
                                screenshot2 = await screenshot_capture.capture_full_screen()
                                assert screenshot2 is not None
                    
                    # Verify we have history
                    assert len(screenshot_capture.capture_history) == 2
                    assert len(hid_controller.event_history) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])