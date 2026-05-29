"""
Progress message adapter
Converts rich messages to simple messages for backward compatibility
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ProgressMessageAdapter:
    """Progress message adapter"""
    
    @staticmethod
    def to_simple(msg: dict) -> dict:
        """
        Convert rich message to simple message
        
        Args:
            msg: Rich message dictionary
            
        Returns:
            Simple message dictionary
        """
        # Status mapping
        status_map = {
            "PROGRESS": "running", 
            "RUNNING": "running",
            "COMPLETED": "completed", 
            "FAILED": "failed", 
            "ERROR": "failed",
            "PENDING": "running",
            "CANCELLED": "failed"
        }
        
        # Extract project ID
        project_id = msg.get("project_id") or msg.get("projectId")
        
        # Extract progress value - supports new unified format
        progress = msg.get("progress", 0) or msg.get("percent", 0)
        if isinstance(progress, (int, float)):
            progress = int(round(float(progress)))
        else:
            progress = 0
        
        # Extract step name
        step_name = (
            msg.get("step_name") or 
            msg.get("phase") or 
            msg.get("current_step") or 
            msg.get("message") or
            "Processing"
        )
        
        # Extract status
        status = msg.get("status", "running")
        if isinstance(status, str):
            status = status_map.get(status.upper(), "running")
        
        # Build simple message
        simple_msg = {
            "type": "task_progress_update",
            "project_id": project_id,
            "progress": progress,
            "step_name": step_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Optional fields
        if "task_id" in msg:
            simple_msg["task_id"] = msg["task_id"]
        
        if "message" in msg:
            simple_msg["message"] = msg["message"]
        
        logger.debug(f"Message adapted: rich -> simple: {simple_msg}")
        return simple_msg
    
    @staticmethod
    def is_progress_message(msg: dict) -> bool:
        """
        Determine if this is a progress message
        
        Args:
            msg: Message dictionary
            
        Returns:
            Whether it is a progress message
        """
        progress_types = [
            "task_progress_update",
            "task_update", 
            "project_update",
            "progress_update",
            "project_progress"  # New unified format
        ]
        
        msg_type = msg.get("type", "")
        return msg_type in progress_types
    
    @staticmethod
    def extract_project_id(msg: dict) -> Optional[str]:
        """
        Extract project ID from message
        
        Args:
            msg: Message dictionary
            
        Returns:
            Project ID or None
        """
        return msg.get("project_id") or msg.get("projectId")
    
    @staticmethod
    def should_throttle(last_progress: int, current_progress: int, 
                       last_timestamp: float, current_timestamp: float,
                       min_interval: float = 0.2) -> bool:
        """
        Determine if sending should be throttled
        
        Args:
            last_progress: Last progress value
            current_progress: Current progress value
            last_timestamp: Last timestamp
            current_timestamp: Current timestamp
            min_interval: Minimum interval (seconds)
            
        Returns:
            Whether sending should be throttled
        """
        # Time interval check
        if current_timestamp - last_timestamp < min_interval:
            return True
        
        # Progress regression check - avoid UI flashing back
        if current_progress < last_progress:
            logger.debug(f"Progress regressed, using last progress: {current_progress} -> {last_progress}")
            return True
        
        return False

# Global adapter instance
progress_adapter = ProgressMessageAdapter()
