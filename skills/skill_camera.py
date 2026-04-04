"""
JARVIS-X Phase 31: Physical Vision (Camera Skill)
Local webcam capture powered by OpenCV.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from utils.logger import get_logger

logger = get_logger("SKILL_CAMERA")

def capture_photo(filename: str = None) -> dict:
    """Captures a photo from the primary webcam and saves it to memory."""
    try:
        import cv2
        
        # Initialize camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
             return {"success": False, "message": "Could not access the camera (0)"}
        
        # Allow settling time
        time.sleep(1)
        
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return {"success": False, "message": "Failed to capture image from camera."}
        
        # Save logic
        save_dir = Path("assets/memory/captures")
        save_dir.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            filename = f"capture_{int(time.time())}.jpg"
        
        save_path = save_dir / filename
        cv2.imwrite(str(save_path), frame)
        
        # Release resources
        cap.release()
        
        logger.info(f"[CAMERA] Photo captured and saved: {save_path.name}")
        return {
            "success": True, 
            "message": f"Photo saved to {save_path.name}",
            "path": str(save_path)
        }
        
    except Exception as e:
        logger.error(f"[CAMERA] Failure: {e}")
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    # Test
    print(capture_photo("test_capture.jpg"))
