"""
Unified progress channel naming convention
Avoids message loss caused by inconsistent channel names
"""

def project_progress_channel(project_id: str) -> str:
    """
    Generate project progress channel name
    
    Args:
        project_id: Project ID
        
    Returns:
        Unified channel name: progress:project:<project_id>
    """
    # Use colons consistently, remove duplicate "project_"
    return f"progress:project:{project_id}"

def task_progress_channel(task_id: str) -> str:
    """
    Generate task progress channel name
    
    Args:
        task_id: Task ID
        
    Returns:
        Unified channel name: progress:task:<task_id>
    """
    return f"progress:task:{task_id}"

def normalize_channel(raw: str) -> str:
    """
    Normalize channel name to unified format
    
    Args:
        raw: Original channel name
        
    Returns:
        Normalized channel name
    """
    if not raw:
        return ""
    
    s = raw.strip()
    
    # If it's project ID format, convert to project progress channel
    if s.startswith("progress:project:"):
        return s
    elif s.startswith("project_"):
        # Remove project_ prefix, extract pure ID
        project_id = s[8:]  # Remove "project_" prefix
        return project_progress_channel(project_id)
    elif s.startswith("progress:project_"):
        # Handle progress:project_<id> format
        project_id = s[17:]  # Remove "progress:project_" prefix
        return project_progress_channel(project_id)
    else:
        # Assume it's a pure project ID
        return project_progress_channel(s)
