#!/usr/bin/env python3
"""
Data Consistency Check and Cleanup Script
Checks and fixes inconsistencies between database and file system
"""

import sys
import os
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from backend.core.database import SessionLocal
from backend.models.project import Project
from backend.models.task import Task, TaskStatus
from backend.models.clip import Clip
from backend.models.collection import Collection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataConsistencyChecker:
    """Data consistency checker"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(project_root / "data" / "autoclip.db")
        self.data_dir = project_root / "data"
        self.projects_dir = self.data_dir / "projects"
        
    def check_consistency(self) -> Dict[str, Any]:
        """Check data consistency"""
        logger.info("Starting data consistency check...")
        
        issues = []
        warnings = []
        
        # 1. Check project data consistency
        project_issues = self._check_project_consistency()
        issues.extend(project_issues)
        
        # 2. Check task data consistency
        task_issues = self._check_task_consistency()
        issues.extend(task_issues)
        
        # 3. Check file system consistency
        file_issues = self._check_filesystem_consistency()
        issues.extend(file_issues)
        
        # 4. Check orphaned data
        orphaned_data = self._check_orphaned_data()
        warnings.extend(orphaned_data)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_issues": len(issues),
            "total_warnings": len(warnings),
            "issues": issues,
            "warnings": warnings,
            "status": "healthy" if len(issues) == 0 else "unhealthy"
        }
    
    def _check_project_consistency(self) -> List[Dict[str, Any]]:
        """Check project data consistency"""
        issues = []
        
        try:
            # Get projects from database
            db = SessionLocal()
            try:
                db_projects = db.query(Project).all()
                db_project_ids = {p.id for p in db_projects}
                
                # Get project directories from file system
                fs_project_ids = set()
                if self.projects_dir.exists():
                    for project_dir in self.projects_dir.iterdir():
                        if project_dir.is_dir() and not project_dir.name.startswith('.'):
                            fs_project_ids.add(project_dir.name)
                
                # Check orphaned files
                orphaned_files = fs_project_ids - db_project_ids
                if orphaned_files:
                    issues.append({
                        "type": "orphaned_files",
                        "severity": "warning",
                        "message": f"Found {len(orphaned_files)} orphaned project files",
                        "details": list(orphaned_files)
                    })
                
                # Check missing files
                missing_files = db_project_ids - fs_project_ids
                if missing_files:
                    issues.append({
                        "type": "missing_files",
                        "severity": "error",
                        "message": f"Found {len(missing_files)} projects with missing files",
                        "details": list(missing_files)
                    })
                
                # Check invalid project directories
                if (self.projects_dir / "None").exists():
                    issues.append({
                        "type": "invalid_directory",
                        "severity": "warning",
                        "message": "Found invalid project directory 'None'",
                        "details": ["None"]
                    })
                
            finally:
                db.close()
                
        except Exception as e:
            issues.append({
                "type": "check_error",
                "severity": "error",
                "message": f"Error checking project consistency: {str(e)}",
                "details": []
            })
        
        return issues
    
    def _check_task_consistency(self) -> List[Dict[str, Any]]:
        """Check task data consistency"""
        issues = []
        
        try:
            db = SessionLocal()
            try:
                # Check long-running abnormal tasks
                from datetime import timedelta
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                long_running_tasks = db.query(Task).filter(
                    Task.status == TaskStatus.RUNNING,
                    Task.created_at < cutoff_time
                ).all()
                
                if long_running_tasks:
                    issues.append({
                        "type": "long_running_tasks",
                        "severity": "warning",
                        "message": f"Found {len(long_running_tasks)} long-running tasks",
                        "details": [{"id": t.id, "name": t.name, "created_at": t.created_at.isoformat()} for t in long_running_tasks]
                    })
                
                # Check orphaned tasks
                all_tasks = db.query(Task).all()
                all_project_ids = {p.id for p in db.query(Project).all()}
                
                orphaned_tasks = []
                for task in all_tasks:
                    if task.project_id not in all_project_ids:
                        orphaned_tasks.append(task)
                
                if orphaned_tasks:
                    issues.append({
                        "type": "orphaned_tasks",
                        "severity": "error",
                        "message": f"Found {len(orphaned_tasks)} orphaned tasks",
                        "details": [{"id": t.id, "name": t.name, "project_id": t.project_id} for t in orphaned_tasks]
                    })
                
            finally:
                db.close()
                
        except Exception as e:
            issues.append({
                "type": "check_error",
                "severity": "error",
                "message": f"Error checking task consistency: {str(e)}",
                "details": []
            })
        
        return issues
    
    def _check_filesystem_consistency(self) -> List[Dict[str, Any]]:
        """Check file system consistency"""
        issues = []
        
        try:
            # Check project directory structure
            if self.projects_dir.exists():
                for project_dir in self.projects_dir.iterdir():
                    if project_dir.is_dir() and not project_dir.name.startswith('.'):
                        # Check required directory structure
                        required_dirs = ["raw", "processing", "output"]
                        missing_dirs = []
                        
                        for req_dir in required_dirs:
                            if not (project_dir / req_dir).exists():
                                missing_dirs.append(req_dir)
                        
                        if missing_dirs:
                            issues.append({
                                "type": "missing_directories",
                                "severity": "warning",
                                "message": f"Project {project_dir.name} is missing directories: {', '.join(missing_dirs)}",
                                "details": {"project_id": project_dir.name, "missing_dirs": missing_dirs}
                            })
                        
                        # Check duplicate metadata files
                        metadata_files = [
                            "clips_metadata.json",
                            "collections_metadata.json",
                            "step1_outline.json",
                            "step2_timeline.json",
                            "step3_scoring.json",
                            "step4_titles.json",
                            "step5_collections.json"
                        ]
                        
                        duplicate_files = []
                        for metadata_file in metadata_files:
                            if (project_dir / metadata_file).exists():
                                duplicate_files.append(metadata_file)
                        
                        if duplicate_files:
                            issues.append({
                                "type": "duplicate_metadata",
                                "severity": "info",
                                "message": f"Project {project_dir.name} has duplicate metadata files",
                                "details": {"project_id": project_dir.name, "duplicate_files": duplicate_files}
                            })
                
        except Exception as e:
            issues.append({
                "type": "check_error",
                "severity": "error",
                "message": f"Error checking file system consistency: {str(e)}",
                "details": []
            })
        
        return issues
    
    def _check_orphaned_data(self) -> List[Dict[str, Any]]:
        """Check orphaned data"""
        warnings = []
        
        try:
            db = SessionLocal()
            try:
                # Check orphaned clip data
                all_clips = db.query(Clip).all()
                all_project_ids = {p.id for p in db.query(Project).all()}
                
                orphaned_clips = [clip for clip in all_clips if clip.project_id not in all_project_ids]
                if orphaned_clips:
                    warnings.append({
                        "type": "orphaned_clips",
                        "message": f"Found {len(orphaned_clips)} orphaned clips",
                        "count": len(orphaned_clips)
                    })
                
                # Check orphaned collection data
                all_collections = db.query(Collection).all()
                orphaned_collections = [col for col in all_collections if col.project_id not in all_project_ids]
                if orphaned_collections:
                    warnings.append({
                        "type": "orphaned_collections",
                        "message": f"Found {len(orphaned_collections)} orphaned collections",
                        "count": len(orphaned_collections)
                    })
                
            finally:
                db.close()
                
        except Exception as e:
            warnings.append({
                "type": "check_error",
                "message": f"Error checking orphaned data: {str(e)}"
            })
        
        return warnings
    
    def fix_issues(self, issues: List[Dict[str, Any]], dry_run: bool = True) -> Dict[str, Any]:
        """Fix discovered issues"""
        logger.info(f"Starting to fix issues (dry_run={dry_run})")
        
        fixed_count = 0
        failed_count = 0
        fix_results = []
        
        for issue in issues:
            try:
                if issue["type"] == "orphaned_files":
                    result = self._fix_orphaned_files(issue["details"], dry_run)
                    fix_results.append(result)
                    if result["success"]:
                        fixed_count += 1
                    else:
                        failed_count += 1
                
                elif issue["type"] == "long_running_tasks":
                    result = self._fix_long_running_tasks(issue["details"], dry_run)
                    fix_results.append(result)
                    if result["success"]:
                        fixed_count += 1
                    else:
                        failed_count += 1
                
                elif issue["type"] == "invalid_directory":
                    result = self._fix_invalid_directory(issue["details"], dry_run)
                    fix_results.append(result)
                    if result["success"]:
                        fixed_count += 1
                    else:
                        failed_count += 1
                
                else:
                    logger.warning(f"Unknown issue type: {issue['type']}")
                    
            except Exception as e:
                logger.error(f"Failed to fix issue: {issue['type']}, error: {e}")
                failed_count += 1
        
        return {
            "fixed_count": fixed_count,
            "failed_count": failed_count,
            "fix_results": fix_results,
            "dry_run": dry_run
        }
    
    def _fix_orphaned_files(self, orphaned_files: List[str], dry_run: bool) -> Dict[str, Any]:
        """Fix orphaned files"""
        try:
            if dry_run:
                logger.info(f"Simulating cleanup of orphaned files: {orphaned_files}")
                return {"success": True, "action": "dry_run", "files": orphaned_files}
            
            cleaned_count = 0
            for project_id in orphaned_files:
                project_dir = self.projects_dir / project_id
                if project_dir.exists():
                    shutil.rmtree(project_dir)
                    cleaned_count += 1
                    logger.info(f"Cleaned up orphaned project directory: {project_id}")
            
            return {"success": True, "action": "cleanup", "cleaned_count": cleaned_count}
            
        except Exception as e:
            logger.error(f"Failed to clean up orphaned files: {e}")
            return {"success": False, "error": str(e)}
    
    def _fix_long_running_tasks(self, long_running_tasks: List[Dict], dry_run: bool) -> Dict[str, Any]:
        """Fix long-running tasks"""
        try:
            if dry_run:
                logger.info(f"Simulating fix for {len(long_running_tasks)} long-running tasks")
                return {"success": True, "action": "dry_run", "tasks": long_running_tasks}
            
            db = SessionLocal()
            try:
                fixed_count = 0
                for task_info in long_running_tasks:
                    task_id = task_info["id"]
                    task = db.query(Task).filter(Task.id == task_id).first()
                    if task:
                        task.status = TaskStatus.FAILED
                        task.error_message = "Task timed out, automatically marked as failed"
                        task.updated_at = datetime.utcnow()
                        fixed_count += 1
                        logger.info(f"Fixed long-running task: {task_id}")
                
                db.commit()
                return {"success": True, "action": "fix", "fixed_count": fixed_count}
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to fix long-running tasks: {e}")
            return {"success": False, "error": str(e)}
    
    def _fix_invalid_directory(self, invalid_dirs: List[str], dry_run: bool) -> Dict[str, Any]:
        """Fix invalid directories"""
        try:
            if dry_run:
                logger.info(f"Simulating cleanup of invalid directories: {invalid_dirs}")
                return {"success": True, "action": "dry_run", "dirs": invalid_dirs}
            
            cleaned_count = 0
            for dir_name in invalid_dirs:
                invalid_dir = self.projects_dir / dir_name
                if invalid_dir.exists():
                    shutil.rmtree(invalid_dir)
                    cleaned_count += 1
                    logger.info(f"Cleaned up invalid directory: {dir_name}")
            
            return {"success": True, "action": "cleanup", "cleaned_count": cleaned_count}
            
        except Exception as e:
            logger.error(f"Failed to clean up invalid directories: {e}")
            return {"success": False, "error": str(e)}


def main():
    """Main function"""
    logger.info("Starting data consistency check and repair...")
    
    checker = DataConsistencyChecker()
    
    # 1. Check data consistency
    result = checker.check_consistency()
    
    print("\n" + "=" * 80)
    print("Data Consistency Check Results")
    print("=" * 80)
    print(f"Check time: {result['timestamp']}")
    print(f"Total issues: {result['total_issues']}")
    print(f"Total warnings: {result['total_warnings']}")
    print(f"Status: {result['status']}")
    
    if result['issues']:
        print("\nIssues found:")
        for i, issue in enumerate(result['issues'], 1):
            print(f"{i}. [{issue['severity'].upper()}] {issue['message']}")
            if issue.get('details'):
                print(f"   Details: {issue['details']}")
    
    if result['warnings']:
        print("\nWarnings:")
        for i, warning in enumerate(result['warnings'], 1):
            print(f"{i}. {warning['message']}")
    
    # 2. If there are issues, ask whether to fix them
    if result['total_issues'] > 0:
        print("\n" + "=" * 60)
        print("Repair Options:")
        print("1. Dry run - Preview repair effects without executing")
        print("2. Execute repair - Actually fix discovered issues")
        print("3. Exit")
        
        while True:
            choice = input("\nSelect operation (1/2/3): ").strip()
            if choice in ['1', '2', '3']:
                break
            print("Invalid choice, please enter 1, 2, or 3")
        
        if choice == '3':
            logger.info("User cancelled repair")
            return
        
        dry_run = (choice == '1')
        
        # Execute repair
        fix_result = checker.fix_issues(result['issues'], dry_run)
        
        print("\n" + "=" * 60)
        if dry_run:
            print("Repair Simulation Results:")
        else:
            print("Repair complete:")
        
        print(f"Successfully repaired: {fix_result['fixed_count']}")
        print(f"Failed to repair: {fix_result['failed_count']}")
        
        if fix_result['fix_results']:
            print("\nRepair Details:")
            for i, fix_result_item in enumerate(fix_result['fix_results'], 1):
                status = "OK" if fix_result_item['success'] else "FAIL"
                print(f"{i}. {status} {fix_result_item.get('action', 'unknown')}")
                if not fix_result_item['success']:
                    print(f"   Error: {fix_result_item.get('error', 'unknown')}")
    
    else:
        print("\nData consistency check passed, no repairs needed!")
    
    logger.info("Data consistency check and repair complete!")


if __name__ == "__main__":
    main()
