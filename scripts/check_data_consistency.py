#!/usr/bin/env python3
"""
Data Consistency Check Script
Checks consistency between database and file system
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.database import SessionLocal
from backend.models.project import Project
from backend.models.clip import Clip
from backend.models.collection import Collection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_project_consistency(db, project_id: str):
    """Check data consistency for a single project"""
    logger.info(f"Checking project consistency: {project_id}")
    
    issues = []
    
    try:
        # Check project in database
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            issues.append("Project does not exist in database")
            return {"project_id": project_id, "issues": issues, "status": "error"}
        
        # Check project directory
        data_dir = project_root / "data"
        project_dir = data_dir / "projects" / project_id
        
        if not project_dir.exists():
            issues.append("Project directory does not exist")
            return {"project_id": project_id, "issues": issues, "status": "error"}
        
        # Check clip consistency
        clips_issues = check_clips_consistency(db, project_id, project_dir)
        issues.extend(clips_issues)
        
        # Check collection consistency
        collections_issues = check_collections_consistency(db, project_id, project_dir)
        issues.extend(collections_issues)
        
        # Check file paths
        file_path_issues = check_file_paths_consistency(db, project_id, project_dir)
        issues.extend(file_path_issues)
        
        status = "warning" if issues else "ok"
        return {
            "project_id": project_id,
            "issues": issues,
            "status": status,
            "clips_count": len(db.query(Clip).filter(Clip.project_id == project_id).all()),
            "collections_count": len(db.query(Collection).filter(Collection.project_id == project_id).all())
        }
        
    except Exception as e:
        logger.error(f"Error checking project {project_id}: {e}")
        return {
            "project_id": project_id,
            "issues": [f"Error during check: {str(e)}"],
            "status": "error"
        }


def check_clips_consistency(db, project_id: str, project_dir: Path):
    """Check clip data consistency"""
    issues = []
    
    try:
        # Get clips from database
        db_clips = db.query(Clip).filter(Clip.project_id == project_id).all()
        
        # Check clip files in file system
        clips_dir = project_dir / "output" / "clips"
        fs_clips = list(clips_dir.glob("*.mp4")) if clips_dir.exists() else []
        
        # Check if clip files in database exist
        for clip in db_clips:
            if clip.video_path:
                file_path = project_root / "data" / clip.video_path
                if not file_path.exists():
                    issues.append(f"Clip file does not exist: {clip.video_path}")
        
        # Check if clips in file system have database records
        for clip_file in fs_clips:
            clip_name = clip_file.name
            found_in_db = any(clip.video_path and clip.video_path.endswith(clip_name) for clip in db_clips)
            if not found_in_db:
                issues.append(f"Clip in file system not recorded in database: {clip_name}")
        
        # Check for duplicate data
        clips_metadata_file = project_dir / "clips_metadata.json"
        if clips_metadata_file.exists():
            issues.append("Duplicate clip metadata file exists (clips_metadata.json)")
        
    except Exception as e:
        issues.append(f"Error checking clip consistency: {str(e)}")
    
    return issues


def check_collections_consistency(db, project_id: str, project_dir: Path):
    """Check collection data consistency"""
    issues = []
    
    try:
        # Get collections from database
        db_collections = db.query(Collection).filter(Collection.project_id == project_id).all()
        
        # Check collection files in file system
        collections_dir = project_dir / "output" / "collections"
        fs_collections = list(collections_dir.glob("*.mp4")) if collections_dir.exists() else []
        
        # Check if collection files in database exist
        for collection in db_collections:
            if collection.video_path:
                file_path = project_root / "data" / collection.video_path
                if not file_path.exists():
                    issues.append(f"Collection file does not exist: {collection.video_path}")
        
        # Check if collections in file system have database records
        for collection_file in fs_collections:
            collection_name = collection_file.name
            found_in_db = any(collection.video_path and collection.video_path.endswith(collection_name) for collection in db_collections)
            if not found_in_db:
                issues.append(f"Collection in file system not recorded in database: {collection_name}")
        
        # Check for duplicate data
        collections_metadata_file = project_dir / "collections_metadata.json"
        if collections_metadata_file.exists():
            issues.append("Duplicate collection metadata file exists (collections_metadata.json)")
        
    except Exception as e:
        issues.append(f"Error checking collection consistency: {str(e)}")
    
    return issues


def check_file_paths_consistency(db, project_id: str, project_dir: Path):
    """Check file path consistency"""
    issues = []
    
    try:
        # Check project file paths
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.video_path:
            video_path = project_root / "data" / project.video_path
            if not video_path.exists():
                issues.append(f"Project video file does not exist: {project.video_path}")
        
        if project and project.subtitle_path:
            subtitle_path = project_root / "data" / project.subtitle_path
            if not subtitle_path.exists():
                issues.append(f"Project subtitle file does not exist: {project.subtitle_path}")
        
    except Exception as e:
        issues.append(f"Error checking file path consistency: {str(e)}")
    
    return issues


def generate_consistency_report(results):
    """Generate consistency check report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_projects": len(results),
        "ok_projects": len([r for r in results if r["status"] == "ok"]),
        "warning_projects": len([r for r in results if r["status"] == "warning"]),
        "error_projects": len([r for r in results if r["status"] == "error"]),
        "results": results
    }
    
    return report


def main():
    """Main function"""
    logger.info("Starting data consistency check...")
    
    db = SessionLocal()
    try:
        # Get all projects
        projects = db.query(Project).all()
        
        if not projects:
            logger.info("No projects found")
            return
        
        logger.info(f"Found {len(projects)} projects, starting check...")
        
        results = []
        for project in projects:
            result = check_project_consistency(db, project.id)
            results.append(result)
        
        # Generate report
        report = generate_consistency_report(results)
        
        # Display check results
        print("\n" + "=" * 80)
        print("Data Consistency Check Report")
        print("=" * 80)
        print(f"Check time: {report['timestamp']}")
        print(f"Total projects: {report['total_projects']}")
        print(f"OK: {report['ok_projects']}")
        print(f"Warnings: {report['warning_projects']}")
        print(f"Errors: {report['error_projects']}")
        
        print("\nDetailed Results:")
        print("-" * 80)
        
        for result in results:
            status_icon = {
                "ok": "OK",
                "warning": "WARN",
                "error": "ERR"
            }.get(result["status"], "UNK")
            
            print(f"[{status_icon}] Project {result['project_id'][:8]}... | "
                  f"Clips: {result.get('clips_count', 0)} | "
                  f"Collections: {result.get('collections_count', 0)}")
            
            if result["issues"]:
                for issue in result["issues"]:
                    print(f"    * {issue}")
        
        # Save report
        report_file = project_root / f"consistency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\nDetailed report saved: {report_file}")
        
        # Provide suggestions
        if report['warning_projects'] > 0 or report['error_projects'] > 0:
            print("\nRecommendations:")
            print("1. Run data migration script to fix issues")
            print("2. Check file permissions and path configuration")
            print("3. Clean up duplicate metadata files")
        
    except Exception as e:
        logger.error(f"Error during check: {e}")
    finally:
        db.close()
    
    logger.info("Consistency check complete!")


if __name__ == "__main__":
    main()
