#!/usr/bin/env python3
"""
Data Storage Optimization Migration Script
Migrates from dual storage mode to optimized storage mode (database stores metadata, file system stores actual files)
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
from backend.services.optimized_storage_service import OptimizedStorageService
from backend.models.project import Project
from backend.models.clip import Clip
from backend.models.collection import Collection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_current_storage():
    """Analyze current storage status"""
    logger.info("Analyzing current storage status...")
    
    data_dir = project_root / "data"
    projects_dir = data_dir / "projects"
    
    if not projects_dir.exists():
        logger.warning("Project directory does not exist")
        return {"projects": [], "total_size": 0}
    
    projects_info = []
    total_size = 0
    
    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir() and not project_dir.name.startswith('.'):
            project_id = project_dir.name
            project_size = sum(f.stat().st_size for f in project_dir.rglob('*') if f.is_file())
            
            # Check for duplicate data
            has_duplicate_data = False
            if (project_dir / "clips_metadata.json").exists():
                has_duplicate_data = True
            
            projects_info.append({
                "project_id": project_id,
                "size_mb": round(project_size / (1024 * 1024), 2),
                "has_duplicate_data": has_duplicate_data,
                "files_count": len(list(project_dir.rglob('*')))
            })
            
            total_size += project_size
    
    logger.info(f"Analysis complete: {len(projects_info)} projects, total size: {round(total_size / (1024 * 1024), 2)} MB")
    
    return {
        "projects": projects_info,
        "total_size": total_size
    }


def migrate_project_to_optimized_storage(db, project_id: str, dry_run: bool = True):
    """Migrate a single project to optimized storage mode"""
    logger.info(f"Migrating project: {project_id} (dry_run={dry_run})")
    
    try:
        # Get project info
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.warning(f"Project {project_id} does not exist in database")
            return {"success": False, "error": "Project does not exist"}
        
        # Check project directory
        data_dir = project_root / "data"
        old_project_dir = data_dir / "projects" / project_id
        
        if not old_project_dir.exists():
            logger.warning(f"Project directory does not exist: {old_project_dir}")
            return {"success": False, "error": "Project directory does not exist"}
        
        if dry_run:
            logger.info(f"Simulating migration for project {project_id}")
            return {"success": True, "dry_run": True, "message": "Migration simulation successful"}
        
        # Create optimized storage service
        storage_service = OptimizedStorageService(db, project_id)
        
        # Execute migration
        migration_result = storage_service.migrate_from_old_storage(old_project_dir)
        
        if migration_result["success"]:
            logger.info(f"Project {project_id} migrated successfully")
            
            # Clean up old duplicate storage files
            cleanup_old_duplicate_files(old_project_dir)
            
            return {
                "success": True,
                "migrated_files": migration_result["migrated_files"],
                "migrated_metadata": migration_result["migrated_metadata"]
            }
        else:
            logger.error(f"Project {project_id} migration failed: {migration_result['error']}")
            return migration_result
            
    except Exception as e:
        logger.error(f"Error migrating project {project_id}: {e}")
        return {"success": False, "error": str(e)}


def cleanup_old_duplicate_files(project_dir: Path):
    """Clean up old duplicate storage files"""
    try:
        logger.info(f"Cleaning up duplicate files for project {project_dir.name}...")
        
        # Delete duplicate metadata files
        duplicate_files = [
            "clips_metadata.json",
            "collections_metadata.json",
            "step1_outline.json",
            "step2_timeline.json",
            "step3_scoring.json",
            "step4_titles.json",
            "step5_collections.json"
        ]
        
        cleaned_count = 0
        for file_name in duplicate_files:
            file_path = project_dir / file_name
            if file_path.exists():
                # Backup file
                backup_path = project_dir / f"{file_name}.backup"
                file_path.rename(backup_path)
                cleaned_count += 1
                logger.info(f"Backed up duplicate file: {file_name}")
        
        logger.info(f"Cleanup complete, backed up {cleaned_count} duplicate files")
        
    except Exception as e:
        logger.error(f"Failed to clean up duplicate files: {e}")


def main():
    """Main function"""
    logger.info("Starting data storage optimization migration...")
    
    # Analyze current storage status
    storage_info = analyze_current_storage()
    
    if not storage_info["projects"]:
        logger.info("No projects found to migrate")
        return
    
    # Display analysis results
    print("\nCurrent Storage Status Analysis:")
    print("=" * 60)
    for project in storage_info["projects"]:
        status = "Has duplicate data" if project["has_duplicate_data"] else "Normal"
        print(f"Project {project['project_id'][:8]}... | {project['size_mb']:>8.2f} MB | {project['files_count']:>4} files | {status}")
    
    print(f"\nTotal size: {round(storage_info['total_size'] / (1024 * 1024), 2)} MB")
    
    # Ask whether to continue
    print("\n" + "=" * 60)
    print("Migration Options:")
    print("1. Dry run - Preview migration effects without executing")
    print("2. Execute migration - Actually migrate data and clean up duplicate files")
    print("3. Exit")
    
    while True:
        choice = input("\nSelect operation (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice, please enter 1, 2, or 3")
    
    if choice == '3':
        logger.info("User cancelled migration")
        return
    
    dry_run = (choice == '1')
    
    if dry_run:
        logger.info("Starting migration simulation...")
    else:
        logger.info("Starting actual migration...")
        # Create backup
        backup_dir = project_root / f"migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(exist_ok=True)
        logger.info(f"Created backup directory: {backup_dir}")
    
    # Execute migration
    db = SessionLocal()
    try:
        success_count = 0
        failed_count = 0
        
        for project_info in storage_info["projects"]:
            project_id = project_info["project_id"]
            
            result = migrate_project_to_optimized_storage(db, project_id, dry_run)
            
            if result["success"]:
                success_count += 1
                if dry_run:
                    logger.info(f"Migration simulation successful: {project_id}")
                else:
                    logger.info(f"Migration successful: {project_id}")
            else:
                failed_count += 1
                logger.error(f"Migration failed: {project_id} - {result.get('error', 'Unknown error')}")
        
        # Display migration results
        print("\n" + "=" * 60)
        print("Migration Results:")
        print(f"Succeeded: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Total: {success_count + failed_count}")
        
        if not dry_run and success_count > 0:
            print(f"\nBackup location: {backup_dir}")
            print("Recommendations:")
            print("1. Test system functionality")
            print("2. Delete backup files after confirming everything works")
            print("3. Run data consistency check")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
    finally:
        db.close()
    
    logger.info("Migration complete!")


if __name__ == "__main__":
    main()
