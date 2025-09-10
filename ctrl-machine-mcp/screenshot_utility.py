#!/usr/bin/env python3
"""Enhanced screenshot utility with improved file naming and segmentation support."""

import os
import time
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import mss
from PIL import Image
import pyautogui

class ScreenshotManager:
    """Manages screenshots with organized naming and segmentation."""
    
    def __init__(self, base_dir: str = "/app/screenshots"):
        """Initialize the screenshot manager."""
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self.sct = mss.mss()
        
    def _generate_filename(
        self, 
        purpose: str, 
        segment: Optional[str] = None,
        extension: str = "png"
    ) -> str:
        """
        Generate organized filename with timestamp and hash.
        Format: YYYYMMDD_HHMMSS_purpose_segment_hash.extension
        
        Args:
            purpose: Main purpose of screenshot (e.g., "danawa_search", "rtx_price")
            segment: Optional segment identifier (e.g., "top_left", "1of4")
            extension: File extension
        
        Returns:
            Generated filename
        """
        # Get timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Clean purpose string
        purpose_clean = purpose.lower().replace(" ", "_").replace("-", "_")
        
        # Build filename parts
        parts = [timestamp, purpose_clean]
        if segment:
            parts.append(segment)
        
        # Add short hash for uniqueness (first 6 chars of timestamp hash)
        hash_input = f"{timestamp}{purpose}{segment or ''}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        parts.append(short_hash)
        
        filename = "_".join(parts) + f".{extension}"
        return filename
    
    def capture_full_screen(self, purpose: str = "full_screen") -> Dict[str, Any]:
        """
        Capture the entire screen.
        
        Args:
            purpose: Description of the screenshot purpose
            
        Returns:
            Dictionary with capture info
        """
        monitor = self.sct.monitors[0]  # All monitors
        screenshot = self.sct.grab(monitor)
        
        # Convert to PIL Image
        img = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
        
        # Generate filename and save
        filename = self._generate_filename(purpose)
        filepath = os.path.join(self.base_dir, filename)
        img.save(filepath)
        
        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "size": (img.width, img.height),
            "timestamp": datetime.now().isoformat(),
            "purpose": purpose
        }
    
    def capture_region(
        self, 
        x: int, 
        y: int, 
        width: int, 
        height: int,
        purpose: str = "region",
        segment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture a specific region of the screen.
        
        Args:
            x, y: Top-left coordinates
            width, height: Region dimensions
            purpose: Description of the screenshot purpose
            segment: Optional segment identifier
            
        Returns:
            Dictionary with capture info
        """
        bbox = {"left": x, "top": y, "width": width, "height": height}
        screenshot = self.sct.grab(bbox)
        
        # Convert to PIL Image
        img = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
        
        # Generate filename and save
        filename = self._generate_filename(purpose, segment)
        filepath = os.path.join(self.base_dir, filename)
        img.save(filepath)
        
        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "size": (img.width, img.height),
            "region": {"x": x, "y": y, "width": width, "height": height},
            "timestamp": datetime.now().isoformat(),
            "purpose": purpose,
            "segment": segment
        }
    
    def capture_and_analyze(
        self, 
        purpose: str = "analysis",
        segments: int = 1
    ) -> Dict[str, Any]:
        """
        Capture full screen and optionally segment in memory for analysis.
        
        Args:
            purpose: Description of the screenshot purpose
            segments: Number of segments for memory analysis (1, 2, or 4)
            
        Returns:
            Dictionary with capture info and segmented images for analysis
        """
        # Capture full screen
        monitor = self.sct.monitors[0]
        screenshot = self.sct.grab(monitor)
        
        # Convert to PIL Image
        img = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
        
        # Generate filename and save full image
        filename = self._generate_filename(purpose)
        filepath = os.path.join(self.base_dir, filename)
        img.save(filepath)
        
        # Prepare segments in memory for analysis
        memory_segments = []
        
        if segments == 1:
            # Single full image
            memory_segments.append({
                "segment": "full",
                "image": img,
                "region": (0, 0, img.width, img.height)
            })
        elif segments == 2:
            # Split into top and bottom halves
            half_height = img.height // 2
            memory_segments = [
                {
                    "segment": "top",
                    "image": img.crop((0, 0, img.width, half_height)),
                    "region": (0, 0, img.width, half_height)
                },
                {
                    "segment": "bottom",
                    "image": img.crop((0, half_height, img.width, img.height)),
                    "region": (0, half_height, img.width, img.height - half_height)
                }
            ]
        elif segments == 4:
            # Split into 4 quadrants
            half_width = img.width // 2
            half_height = img.height // 2
            memory_segments = [
                {
                    "segment": "top_left",
                    "image": img.crop((0, 0, half_width, half_height)),
                    "region": (0, 0, half_width, half_height)
                },
                {
                    "segment": "top_right",
                    "image": img.crop((half_width, 0, img.width, half_height)),
                    "region": (half_width, 0, img.width - half_width, half_height)
                },
                {
                    "segment": "bottom_left",
                    "image": img.crop((0, half_height, half_width, img.height)),
                    "region": (0, half_height, half_width, img.height - half_height)
                },
                {
                    "segment": "bottom_right",
                    "image": img.crop((half_width, half_height, img.width, img.height)),
                    "region": (half_width, half_height, img.width - half_width, img.height - half_height)
                }
            ]
        
        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "size": (img.width, img.height),
            "timestamp": datetime.now().isoformat(),
            "purpose": purpose,
            "segments_count": segments,
            "memory_segments": memory_segments  # In-memory segments for analysis
        }
    
    def capture_with_context(
        self,
        purpose: str,
        click_position: Optional[Tuple[int, int]] = None,
        search_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture screenshot with additional context information.
        
        Args:
            purpose: Description of the screenshot purpose
            click_position: Optional (x, y) position where action occurred
            search_text: Optional search text used
            
        Returns:
            Dictionary with capture info and context
        """
        result = self.capture_full_screen(purpose)
        
        # Add context information
        result["context"] = {
            "click_position": click_position,
            "search_text": search_text,
            "mouse_position": pyautogui.position(),
            "screen_size": pyautogui.size()
        }
        
        return result
    
    def list_screenshots(self, recent: int = 10) -> List[Dict[str, Any]]:
        """
        List recent screenshots with metadata.
        
        Args:
            recent: Number of recent screenshots to list
            
        Returns:
            List of screenshot information
        """
        screenshots = []
        
        # Get all PNG files in directory
        files = [f for f in os.listdir(self.base_dir) if f.endswith('.png')]
        
        # Sort by timestamp (files start with YYYYMMDD_HHMMSS)
        files.sort(reverse=True)
        
        # Get info for recent files
        for filename in files[:recent]:
            filepath = os.path.join(self.base_dir, filename)
            
            # Parse filename
            parts = filename.replace('.png', '').split('_')
            
            # Get file stats
            stat = os.stat(filepath)
            
            # Try to get image dimensions
            try:
                with Image.open(filepath) as img:
                    width, height = img.size
            except:
                width, height = None, None
            
            screenshots.append({
                "filename": filename,
                "filepath": filepath,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "dimensions": (width, height) if width else None,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "parts": parts
            })
        
        return screenshots
    
    def cleanup_old_screenshots(self, keep_recent: int = 50) -> int:
        """
        Clean up old screenshots, keeping only recent ones.
        
        Args:
            keep_recent: Number of recent screenshots to keep
            
        Returns:
            Number of files deleted
        """
        files = [f for f in os.listdir(self.base_dir) if f.endswith('.png')]
        files.sort(reverse=True)
        
        deleted = 0
        for filename in files[keep_recent:]:
            filepath = os.path.join(self.base_dir, filename)
            try:
                os.remove(filepath)
                deleted += 1
            except:
                pass
        
        return deleted


# Example usage functions
def capture_danawa_search(manager: ScreenshotManager, search_term: str) -> Dict[str, Any]:
    """Capture Danawa search with proper naming."""
    purpose = f"danawa_search_{search_term.replace(' ', '_').lower()}"
    return manager.capture_full_screen(purpose)


def capture_price_detail(manager: ScreenshotManager, product: str) -> Dict[str, Any]:
    """Capture price details with in-memory segmentation for analysis."""
    purpose = f"price_detail_{product.replace(' ', '_').lower()}"
    return manager.capture_and_analyze(purpose, segments=4)


if __name__ == "__main__":
    # Test the screenshot manager
    manager = ScreenshotManager()
    
    # Example: Capture full screen
    result = manager.capture_full_screen("test_full_screen")
    print(f"Full screen captured: {result['filename']}")
    
    # Example: Capture with in-memory segmentation
    result = manager.capture_and_analyze("test_analysis", segments=4)
    print(f"Captured with {result['segments_count']} memory segments")
    print(f"Saved as: {result['filename']}")
    for seg in result['memory_segments']:
        print(f"  - {seg['segment']}: {seg['image'].size}")
    
    # List recent screenshots
    recent = manager.list_screenshots(5)
    print(f"\nRecent screenshots:")
    for shot in recent:
        print(f"  - {shot['filename']} ({shot['size_mb']} MB)")