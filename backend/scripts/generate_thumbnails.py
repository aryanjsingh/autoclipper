#!/usr/bin/env python3
"""
Script to generate thumbnails for existing projects
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
from sqlalchemy import text

def generate_thumbnails_for_projects():
    """Generate thumbnails for all projects without thumbnails"""
    db = SessionLocal()
    try:
        # Find all projects without thumbnails but with video files
        projects = db.query(Project).filter(
            Project.thumbnail.is_(None),
            Project.video_path.isnot(None)
        ).all()
        
        if not projects:
            print("All projects already have thumbnails")
            return True
        
        print(f"Found {len(projects)} projects that need thumbnails generated")
        
        success_count = 0
        for project in projects:
            try:
                print(f"Generating thumbnail for project '{project.name}' ({project.id})...")
                
                # Check if video file exists
                video_path = Path(project.video_path)
                if not video_path.exists():
                    print(f"Video file does not exist: {video_path}")
                    continue
                
                # Generate thumbnail
                thumbnail_data = generate_project_thumbnail(project.id, video_path)
                
                if thumbnail_data:
                    # Save to database
                    project.thumbnail = thumbnail_data
                    db.commit()
                    print(f"Project '{project.name}' thumbnail generated successfully")
                    success_count += 1
                else:
                    print(f"Project '{project.name}' thumbnail generation failed")
                    
            except Exception as e:
                print(f"Project '{project.name}' processing failed: {e}")
                db.rollback()
                continue
        
        print(f"Complete! Successfully generated thumbnails for {success_count}/{len(projects)} projects")
        return True
        
    except Exception as e:
        print(f"Error occurred during thumbnail generation: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def generate_thumbnail_for_project(project_id: str):
    """Generate thumbnail for specified project"""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            print(f"Project {project_id} does not exist")
            return False
        
        if not project.video_path:
            print(f"Project {project_id} has no video file")
            return False
        
        # Check if video file exists
        video_path = Path(project.video_path)
        if not video_path.exists():
            print(f"Video file does not exist: {video_path}")
            return False
        
        print(f"Generating thumbnail for project '{project.name}' ({project.id})...")
        
        # Generate thumbnail
        thumbnail_data = generate_project_thumbnail(project.id, video_path)
        
        if thumbnail_data:
            # Save to database
            project.thumbnail = thumbnail_data
            db.commit()
            print(f"Project '{project.name}' thumbnail generated successfully")
            return True
        else:
            print(f"Project '{project.name}' thumbnail generation failed")
            return False
            
    except Exception as e:
        print(f"Error processing project {project_id}: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Generate thumbnail for specified project
        project_id = sys.argv[1]
        print(f"Starting thumbnail generation for project {project_id}...")
        if generate_thumbnail_for_project(project_id):
            print("Thumbnail generation complete!")
        else:
            print("Thumbnail generation failed")
            sys.exit(1)
    else:
        # Generate thumbnails for all projects
        print("Starting thumbnail generation for all projects...")
        if generate_thumbnails_for_projects():
            print("All thumbnails generated successfully!")
        else:
            print("Thumbnail generation failed")
            sys.exit(1)

if __name__ == "__main__":
    main()
