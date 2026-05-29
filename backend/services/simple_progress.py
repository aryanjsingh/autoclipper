"""
Simplified Progress Service - Fixed Stages + Fixed Weights
Based on the "keep it simple and stable" approach
"""

import time
import json
import logging
import os
from typing import List, Tuple, Optional, Dict, Any
import redis

logger = logging.getLogger(__name__)

# Fixed stage definitions - adjust based on your project's actual needs
STAGES: List[Tuple[str, int]] = [
    ("INGEST", 10),        # Download/Ready
    ("SUBTITLE", 15),      # Subtitles/Alignment
    ("ANALYZE", 20),       # Semantic Analysis/Outline
    ("HIGHLIGHT", 25),     # Clip Location/Scoring
    ("EXPORT", 20),        # Export/Packaging
    ("DONE", 10),          # Verification/Archiving
]

# Stage weight mapping
WEIGHTS = {name: w for name, w in STAGES}
# Stage order
ORDER = [name for name, _ in STAGES]

# Redis connection - uses the project's existing Redis configuration
try:
    # Get Redis URL from environment variable, default to local address
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    r = redis.Redis.from_url(redis_url, decode_responses=True)
    # Test connection
    r.ping()
    logger.info("Redis connection successful")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    r = None


def compute_percent(stage: str, subpercent: Optional[float] = None) -> int:
    """
    Calculate the percentage corresponding to a stage
    
    Args:
        stage: Current stage name
        subpercent: Sub-progress percentage (0-100), optional
        
    Returns:
        Total progress percentage (0-100)
    """
    # Accumulate weights of previous stages
    done = 0
    for s in ORDER:
        if s == stage:
            break
        done += WEIGHTS[s]
    
    # Current stage
    cur = WEIGHTS.get(stage, 0)
    
    if subpercent is None:
        # When switching stages, show up to the start of the current stage
        return min(100, done + cur) if stage == "DONE" else min(99, done)
    else:
        # With sub-progress, linearly convert by weight
        subpercent = max(0, min(100, subpercent))
        return min(99, done + int(cur * subpercent / 100))


def emit_progress(project_id: str, stage: str, message: str = "", subpercent: Optional[float] = None):
    """
    Send progress event
    
    Args:
        project_id: Project ID
        stage: Current stage
        message: Progress message
        subpercent: Sub-progress percentage, optional
    """
    if not r:
        logger.warning("Redis not connected, skipping progress emission")
        return
        
    percent = compute_percent(stage, subpercent)
    payload = {
        "project_id": project_id,
        "stage": stage,
        "percent": percent,
        "message": message,
        "ts": int(time.time())
    }
    
    try:
        # 1) Persist latest snapshot (for polling/refresh)
        r.hset(f"progress:project:{project_id}", mapping={
            "stage": stage, 
            "percent": str(percent), 
            "message": message, 
            "ts": str(payload["ts"])
        })
        
        # 2) Real-time broadcast (optional, for WebSocket)
        r.publish(f"progress:project:{project_id}", json.dumps(payload))
        
        logger.info(f"Progress event sent: {project_id} - {stage} ({percent}%) - {message}")
        
    except Exception as e:
        logger.error(f"Failed to send progress event: {e}")


def get_progress_snapshot(project_id: str) -> Optional[Dict[str, Any]]:
    """
    Get project progress snapshot
    
    Args:
        project_id: Project ID
        
    Returns:
        Progress snapshot data, or None if not found
    """
    if not r:
        return None
        
    try:
        h = r.hgetall(f"progress:project:{project_id}")
        if not h:
            return None
            
        return {
            "project_id": project_id,
            "stage": h.get("stage", ""),
            "percent": int(h.get("percent", 0)),
            "message": h.get("message", ""),
            "ts": int(h.get("ts", 0))
        }
    except Exception as e:
        logger.error(f"Failed to get progress snapshot: {e}")
        return None


def get_multiple_progress_snapshots(project_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Batch get progress snapshots for multiple projects
    
    Args:
        project_ids: List of project IDs
        
    Returns:
        List of progress snapshots
    """
    if not r:
        return []
        
    results = []
    for project_id in project_ids:
        snapshot = get_progress_snapshot(project_id)
        if snapshot:
            results.append(snapshot)
    
    return results


def clear_progress(project_id: str):
    """
    Clear project progress data
    
    Args:
        project_id: Project ID
    """
    if not r:
        return
        
    try:
        r.delete(f"progress:project:{project_id}")
        logger.info(f"Cleared project progress data: {project_id}")
    except Exception as e:
        logger.error(f"Failed to clear progress data: {e}")


STAGE_NAMES_ZH = {
    "INGEST": "Preparing source",
    "SUBTITLE": "Subtitles",
    "ANALYZE": "Content analysis",
    "HIGHLIGHT": "Highlight clips",
    "EXPORT": "Exporting video",
    "DONE": "Complete",
}

STAGE_NAMES_EN = {
    "INGEST": "Preparing source",
    "SUBTITLE": "Subtitles",
    "ANALYZE": "Content analysis",
    "HIGHLIGHT": "Highlight clips",
    "EXPORT": "Exporting video",
    "DONE": "Complete",
}


def get_stage_display_name(stage: str) -> str:
    """Return a human-readable stage label for the active output language."""
    from backend.core.output_language import is_english

    names = STAGE_NAMES_EN if is_english() else STAGE_NAMES_ZH
    return names.get(stage, stage)
