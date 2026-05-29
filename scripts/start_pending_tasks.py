#!/usr/bin/env python3
"""
Start pending tasks
View and launch all pending tasks
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables
import os
os.environ['PYTHONPATH'] = str(project_root)

# Add backend directory to path
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from backend.core.database import SessionLocal
from backend.models.task import Task, TaskStatus, TaskType
from backend.models.project import Project, ProjectStatus
from backend.services.task_queue_service import TaskQueueService
from backend.services.processing_service import ProcessingService
from backend.core.celery_simple import celery_app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_pending_tasks():
    """List all pending tasks"""
    print("Checking pending tasks...")
    
    try:
        db = SessionLocal()
        
        try:
            # Query pending tasks
            pending_tasks = db.query(Task).filter(Task.status == TaskStatus.PENDING).all()
            
            if not pending_tasks:
                print("No pending tasks found")
                return []
            
            print(f"Found {len(pending_tasks)} pending tasks:")
            print("-" * 80)
            
            for i, task in enumerate(pending_tasks, 1):
                print(f"{i}. Task ID: {task.id}")
                print(f"   Name: {task.name}")
                print(f"   Type: {task.task_type}")
                print(f"   Project ID: {task.project_id}")
                print(f"   Created at: {task.created_at}")
                print(f"   Priority: {task.priority}")
                if task.description:
                    print(f"   Description: {task.description}")
                print("-" * 80)
            
            return pending_tasks
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Failed to query pending tasks: {e}")
        return []

def list_pending_projects():
    """List all pending projects"""
    print("\nChecking pending projects...")
    
    try:
        db = SessionLocal()
        
        try:
            # Query pending projects
            pending_projects = db.query(Project).filter(Project.status == ProjectStatus.PENDING).all()
            
            if not pending_projects:
                print("No pending projects found")
                return []
            
            print(f"Found {len(pending_projects)} pending projects:")
            print("-" * 80)
            
            for i, project in enumerate(pending_projects, 1):
                print(f"{i}. Project ID: {project.id}")
                print(f"   Name: {project.name}")
                print(f"   Type: {project.project_type}")
                print(f"   Created at: {project.created_at}")
                if project.description:
                    print(f"   Description: {project.description}")
                print("-" * 80)
            
            return pending_projects
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Failed to query pending projects: {e}")
        return []

def start_task(task_id: str):
    """Start a specific task"""
    print(f"Starting task: {task_id}")
    
    try:
        db = SessionLocal()
        task_service = TaskQueueService(db)
        
        try:
            # Get task info
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                print(f"Task not found: {task_id}")
                return False
            
            if task.status != TaskStatus.PENDING:
                print(f"Task status is not pending: {task.status}")
                return False
            
            print(f"Task info:")
            print(f"   Name: {task.name}")
            print(f"   Type: {task.task_type}")
            print(f"   Project ID: {task.project_id}")
            
            # Start different processing based on task type
            if task.task_type == TaskType.VIDEO_PROCESSING:
                return start_video_processing_task(task, db)
            else:
                print(f"Unsupported task type: {task.task_type}")
                return False
                
        finally:
            db.close()
            
    except Exception as e:
        print(f"Failed to start task: {e}")
        return False

def start_video_processing_task(task: Task, db):
    """Start video processing task"""
    print("Starting video processing task...")
    
    try:
        # Get project info
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            print(f"Project not found: {task.project_id}")
            return False
        
        # Get project file paths
        from backend.core.path_utils import get_project_raw_directory
        raw_dir = get_project_raw_directory(project.id)
        
        video_path = None
        srt_path = None
        
        # Get file paths from project config
        if project.video_path:
            video_path = project.video_path
        
        # Get SRT path from processing_config
        if project.processing_config and "subtitle_path" in project.processing_config:
            srt_path = project.processing_config["subtitle_path"]
        
        # If path doesn't exist, try to find from raw directory
        if not video_path or not Path(video_path).exists():
            video_files = list(raw_dir.glob("*.mp4"))
            if video_files:
                video_path = str(video_files[0])
        
        if not srt_path or not Path(srt_path).exists():
            srt_files = list(raw_dir.glob("*.srt"))
            if srt_files:
                srt_path = str(srt_files[0])
        
        print(f"File paths:")
        print(f"   Video: {video_path}")
        print(f"   Subtitles: {srt_path}")
        
        # Start Celery task
        from backend.tasks.processing import process_video_pipeline
        
        celery_task = process_video_pipeline.delay(
            project_id=str(project.id),
            input_video_path=video_path or "",
            input_srt_path=srt_path or ""
        )
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.celery_task_id = celery_task.id
        task.started_at = datetime.utcnow()
        db.commit()
        
        print(f"Task started, Celery task ID: {celery_task.id}")
        return True
        
    except Exception as e:
        print(f"Failed to start video processing task: {e}")
        return False

def start_project(project_id: str):
    """Start a specific project"""
    print(f"Starting project: {project_id}")
    
    try:
        db = SessionLocal()
        processing_service = ProcessingService(db)
        
        try:
            # Get project info
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                print(f"Project not found: {project_id}")
                return False
            
            if project.status != ProjectStatus.PENDING:
                print(f"Project status is not pending: {project.status}")
                return False
            
            print(f"Project info:")
            print(f"   Name: {project.name}")
            print(f"   Type: {project.project_type}")
            
            # Get project file paths
            from backend.core.path_utils import get_project_raw_directory
            raw_dir = get_project_raw_directory(project.id)
            
            video_path = None
            srt_path = None
            
            # Get file paths from project config
            if project.video_path:
                video_path = project.video_path
            
            # Get SRT path from processing_config
            if project.processing_config and "subtitle_path" in project.processing_config:
                srt_path = project.processing_config["subtitle_path"]
            
            # If path doesn't exist, try to find from raw directory
            if not video_path or not Path(video_path).exists():
                video_files = list(raw_dir.glob("*.mp4"))
                if video_files:
                    video_path = str(video_files[0])
            
            if not srt_path or not Path(srt_path).exists():
                srt_files = list(raw_dir.glob("*.srt"))
                if srt_files:
                    srt_path = str(srt_files[0])
            
            print(f"File paths:")
            print(f"   Video: {video_path}")
            print(f"   Subtitles: {srt_path}")
            
            # Start processing
            result = processing_service.start_processing(project_id, Path(srt_path) if srt_path else None)
            
            print(f"Project processing started")
            print(f"   Result: {result}")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Failed to start project: {e}")
        return False

def start_all_pending_tasks():
    """Start all pending tasks"""
    print("Starting all pending tasks...")
    
    # Get pending tasks
    pending_tasks = list_pending_tasks()
    
    if not pending_tasks:
        print("No pending tasks to start")
        return
    
    # Start each task
    success_count = 0
    for task in pending_tasks:
        if start_task(task.id):
            success_count += 1
    
    print(f"Successfully started {success_count}/{len(pending_tasks)} tasks")

def start_all_pending_projects():
    """Start all pending projects"""
    print("Starting all pending projects...")
    
    # Get pending projects
    pending_projects = list_pending_projects()
    
    if not pending_projects:
        print("No pending projects to start")
        return
    
    # Start each project
    success_count = 0
    for project in pending_projects:
        if start_project(project.id):
            success_count += 1
    
    print(f"Successfully started {success_count}/{len(pending_projects)} projects")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Start pending tasks")
    parser.add_argument("--list", action="store_true", help="List pending tasks")
    parser.add_argument("--list-projects", action="store_true", help="List pending projects")
    parser.add_argument("--start-task", type=str, help="Start a specific task by ID")
    parser.add_argument("--start-project", type=str, help="Start a specific project by ID")
    parser.add_argument("--start-all", action="store_true", help="Start all pending tasks")
    parser.add_argument("--start-all-projects", action="store_true", help="Start all pending projects")
    
    args = parser.parse_args()
    
    if args.list:
        list_pending_tasks()
    elif args.list_projects:
        list_pending_projects()
    elif args.start_task:
        start_task(args.start_task)
    elif args.start_project:
        start_project(args.start_project)
    elif args.start_all:
        start_all_pending_tasks()
    elif args.start_all_projects:
        start_all_pending_projects()
    else:
        # Default: show all pending tasks and projects
        list_pending_tasks()
        list_pending_projects()
        
        # Ask whether to start all tasks
        response = input("\nStart all pending tasks? (y/N): ")
        if response.lower() in ['y', 'yes']:
            start_all_pending_tasks()
            start_all_pending_projects()

if __name__ == "__main__":
    main()
