"""
Unified Path Management Utilities
Solves inconsistent path construction issues in the project
"""

import os
from pathlib import Path
from typing import Optional

def get_project_root() -> Path:
    """
    Get project root directory
    Search upward from backend directory until finding the directory containing backend
    """
    current_path = Path(__file__).parent  # backend/core/

    # Search upward for project root directory
    while current_path.parent != current_path:  # Not yet at root
        if (current_path.parent / "backend").exists():
            return current_path.parent
        current_path = current_path.parent

    # If not found, use default path
    return Path(__file__).parent.parent.parent

def get_data_directory() -> Path:
    """Get data directory"""
    # Use data directory under project root consistently, matching config.py
    project_root = get_project_root()
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_projects_directory() -> Path:
    """Get projects directory"""
    projects_dir = get_data_directory() / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir

def get_output_directory() -> Path:
    """Get output directory"""
    output_dir = get_project_root() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def get_project_directory(project_id: str) -> Path:
    """Get project directory"""
    project_dir = get_projects_directory() / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir

def get_project_raw_directory(project_id: str) -> Path:
    """Get project raw files directory"""
    raw_dir = get_project_directory(project_id) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir

def get_project_output_directory(project_id: str) -> Path:
    """Get project output directory"""
    output_dir = get_project_directory(project_id) / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def get_clips_directory() -> Path:
    """Get clips directory"""
    clips_dir = get_output_directory() / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    return clips_dir

def get_collections_directory() -> Path:
    """Get collections directory"""
    collections_dir = get_output_directory() / "collections"
    collections_dir.mkdir(parents=True, exist_ok=True)
    return collections_dir

def get_metadata_directory() -> Path:
    """Get metadata directory"""
    metadata_dir = get_output_directory() / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return metadata_dir

def get_settings_file_path() -> Path:
    """Get settings file path"""
    return get_data_directory() / "settings.json"

def get_uploads_directory() -> Path:
    """Get uploads directory"""
    uploads_dir = get_data_directory() / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir

def get_temp_directory() -> Path:
    """Get temporary directory"""
    temp_dir = get_data_directory() / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def ensure_directory_exists(path: Path) -> Path:
    """Ensure directory exists"""
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_video_file_path(project_id: str, filename: str) -> Path:
    """Get project video file path"""
    return get_project_raw_directory(project_id) / filename

def get_srt_file_path(project_id: str, filename: str) -> Path:
    """Get project SRT file path"""
    return get_project_raw_directory(project_id) / filename

def get_clip_file_path(clip_id: str, title: str) -> Path:
    """Get clip file path"""
    # Sanitize filename, remove special characters
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')
    return get_clips_directory() / f"{clip_id}_{safe_title}.mp4"

def get_collection_file_path(collection_id: str, title: str) -> Path:
    """Get collection file path"""
    # Sanitize filename, remove special characters
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')
    return get_collections_directory() / f"{collection_id}_{safe_title}.mp4"

def get_metadata_file_path(project_id: str) -> Path:
    """Get project metadata file path"""
    return get_metadata_directory() / f"{project_id}_metadata.json"

def get_log_file_path() -> Path:
    """Get log file path"""
    return get_project_root() / "backend.log"

def get_cache_directory() -> Path:
    """Get cache directory"""
    cache_dir = get_data_directory() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def get_backup_directory() -> Path:
    """Get backup directory"""
    backup_dir = get_data_directory() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def cleanup_temp_files(max_age_hours: int = 24):
    """Clean up temporary files"""
    import time
    temp_dir = get_temp_directory()
    current_time = time.time()
    
    for file_path in temp_dir.iterdir():
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > (max_age_hours * 3600):
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Failed to clean up temporary file: {file_path}, error: {e}")

def validate_file_path(file_path: Path) -> bool:
    """Validate if file path is safe"""
    try:
        # Check if path is within allowed directories
        allowed_dirs = [
            get_data_directory(),
            get_output_directory(),
            get_project_root()
        ]
        
        file_path = file_path.resolve()
        return any(file_path.is_relative_to(allowed_dir) for allowed_dir in allowed_dirs)
    except Exception:
        return False
