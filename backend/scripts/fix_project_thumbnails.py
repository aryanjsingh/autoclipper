#!/usr/bin/env python3
"""
Fix project thumbnails script
Handle thumbnail issues for link import and file import projects
"""

import sys
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.core.database import SessionLocal
from backend.models.project import Project
from backend.utils.thumbnail_generator import generate_project_thumbnail
import requests
import base64
import logging

logger = logging.getLogger(__name__)

def fix_project_thumbnail(project_id: str):
    """Fix thumbnail for specified project"""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            print(f"Project {project_id} does not exist")
            return False
        
        if project.thumbnail:
            print(f"Project {project_id} already has thumbnail, skipping")
            return True
        
        print(f"Fixing thumbnail for project {project_id}...")
        
        # Check project type and source
        source_url = project.project_metadata.get('source_url') if project.project_metadata else None
        is_bilibili_project = source_url and 'bilibili.com' in source_url
        has_video_file = project.video_path and Path(project.video_path).exists()
        
        if is_bilibili_project:
            # Link import project - try to get thumbnail from Bilibili
            print(f"Detected Bilibili project, attempting to get original video thumbnail...")
            success = fix_bilibili_thumbnail(project, db)
        elif has_video_file:
            # File import project - generate thumbnail from video file
            print(f"Detected file import project, generating thumbnail from video file...")
            success = fix_file_import_thumbnail(project, db)
        else:
            # No original video file, try to generate thumbnail from clips
            print(f"No original video file, attempting to generate thumbnail from clips...")
            success = fix_clip_thumbnail(project, db)
        
        if success:
            print(f"Project {project_id} thumbnail fixed successfully")
        else:
            print(f"Project {project_id} thumbnail fix failed")
        
        return success
        
    except Exception as e:
        print(f"Error fixing thumbnail for project {project_id}: {e}")
        return False
    finally:
        db.close()

def fix_bilibili_thumbnail(project, db):
    """Fix Bilibili project thumbnail"""
    try:
        # Get Bilibili info from project settings
        if not project.processing_config:
            return False
        
        bilibili_info = project.processing_config.get('bilibili_info', {})
        if not bilibili_info:
            return False
        
        # Try to get thumbnail from Bilibili API
        # Implementation depends on actual Bilibili API
        # Currently returns False, indicating manual handling needed
        print("Bilibili thumbnail retrieval requires API support, skipping for now")
        return False
        
    except Exception as e:
        logger.error(f"Failed to fix Bilibili thumbnail: {e}")
        return False

def fix_file_import_thumbnail(project, db):
    """Fix file import project thumbnail"""
    try:
        video_path = Path(project.video_path)
        if not video_path.exists():
            print(f"Video file does not exist: {video_path}")
            return False
        
        # Generate thumbnail
        thumbnail_data = generate_project_thumbnail(project.id, video_path)
        
        if thumbnail_data:
            # Save to database
            project.thumbnail = thumbnail_data
            db.commit()
            return True
        else:
            print("Thumbnail generation failed")
            return False
            
    except Exception as e:
        logger.error(f"Failed to fix file import thumbnail: {e}")
        return False

def fix_clip_thumbnail(project, db):
    """Generate thumbnail from clips"""
    try:
        # Find clip files in project directory
        project_dir = Path(f"/Users/zhoukk/autoclip/data/projects/{project.id}")
        clips_dir = project_dir / "output" / "clips"
        
        if not clips_dir.exists():
            print(f"Clips directory does not exist: {clips_dir}")
            return False
        
        # Get first clip file
        clip_files = list(clips_dir.glob("*.mp4"))
        if not clip_files:
            print(f"No clip files found")
            return False
        
        first_clip = clip_files[0]
        print(f"Using clip file to generate thumbnail: {first_clip.name}")
        
        # Generate thumbnail
        thumbnail_data = generate_project_thumbnail(project.id, first_clip)
        
        if thumbnail_data:
            # Save to database
            project.thumbnail = thumbnail_data
            db.commit()
            return True
        else:
            print("Failed to generate thumbnail from clips")
            return False
            
    except Exception as e:
        logger.error(f"Failed to generate thumbnail from clips: {e}")
        return False

def fix_all_project_thumbnails():
    """Fix thumbnails for all projects"""
    db = SessionLocal()
    try:
        # Find all projects without thumbnails
        projects = db.query(Project).filter(Project.thumbnail.is_(None)).all()
        
        if not projects:
            print("All projects already have thumbnails")
            return True
        
        print(f"Found {len(projects)} projects that need thumbnail fixes")
        
        success_count = 0
        for project in projects:
            if fix_project_thumbnail(project.id):
                success_count += 1
        
        print(f"Complete! Successfully fixed thumbnails for {success_count}/{len(projects)} projects")
        return True
        
    except Exception as e:
        print(f"Error fixing all project thumbnails: {e}")
        return False
    finally:
        db.close()

def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Fix specified project
        project_id = sys.argv[1]
        print(f"Starting thumbnail fix for project {project_id}...")
        if fix_project_thumbnail(project_id):
            print("Thumbnail fix complete!")
        else:
            print("Thumbnail fix failed")
            sys.exit(1)
    else:
        # Fix all projects
        print("Starting thumbnail fix for all projects...")
        if fix_all_project_thumbnails():
            print("All thumbnails fixed successfully!")
        else:
            print("Thumbnail fix failed")
            sys.exit(1)

if __name__ == "__main__":
    main()
