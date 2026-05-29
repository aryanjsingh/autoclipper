"""
Auto pipeline launch service
Automatically starts video processing pipeline when new project is created
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from backend.core.database import SessionLocal
from backend.models.project import Project, ProjectStatus
from backend.models.task import Task, TaskStatus
from backend.services.progress_update_service import progress_update_service
# from backend.services.pipeline_adapter import PipelineAdapter  # Temporarily commented out, file does not exist
from backend.utils.task_submission_utils import submit_video_pipeline_task

logger = logging.getLogger(__name__)

class AutoPipelineService:
    """Auto pipeline launch service"""
    
    def __init__(self):
        self.processing_projects = set()
    
    async def auto_start_pipeline(self, project_id: str) -> Dict[str, Any]:
        """
        Automatically start project pipeline processing
        
        Args:
            project_id: Project ID
            
        Returns:
            Launch result
        """
        try:
            logger.info(f"Auto-starting project pipeline: {project_id}")
            
            # Check if the project is already being processed
            if project_id in self.processing_projects:
                logger.warning(f"Project {project_id} is already being processed, skipping")
                return {"status": "skipped", "message": "Project is already being processed"}
            
            # Mark project as being processed
            self.processing_projects.add(project_id)
            
            # Get project info
            db = SessionLocal()
            try:
                project = db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    raise ValueError(f"Project {project_id} does not exist")
                
                # Check project status
                if project.status != ProjectStatus.PENDING:
                    logger.info(f"Project {project_id} status is {project.status}, skipping auto-start")
                    return {"status": "skipped", "message": f"Project status is {project.status}"}
                
                # Check project files
                if not project.video_path:
                    raise ValueError(f"Project {project_id} has no video file")
                
                # Find subtitle file
                srt_file = self._find_srt_file(project_id)
                if not srt_file:
                    logger.warning(f"Project {project_id} has no subtitle file, will attempt auto-generation")
                
                # Check if there's already a running task
                existing_task = db.query(Task).filter(
                    Task.project_id == project_id,
                    Task.name == "Auto Video Processing Pipeline",
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
                ).first()
                
                if existing_task:
                    # Use existing task
                    task = existing_task
                    logger.info(f"Using existing task: {task.id}")
                else:
                    # Create new task record
                    task = self._create_processing_task(db, project_id)
                    if not task:
                        raise ValueError("Failed to create task record")
                
                # Update project status
                project.status = ProjectStatus.PROCESSING
                project.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Project {project_id} status updated to processing")
                
                # Start progress monitoring
                await progress_update_service.start_progress_monitoring(task.id)
                
                # Submit Celery task
                logger.info(f"Preparing to submit Celery task: {project_id}")
                
                # Find project file paths
                from ..core.config import get_data_directory
                data_dir = get_data_directory()
                project_dir = Path(data_dir) / "projects" / project_id
                input_video_path = str(project_dir / "raw" / "input.mp4")
                input_srt_path = str(project_dir / "raw" / "input.srt")
                
                # Check if files exist
                if not Path(input_video_path).exists():
                    raise ValueError(f"Video file does not exist: {input_video_path}")
                
                logger.info(f"Video file: {input_video_path}")
                logger.info(f"Subtitle file: {input_srt_path if Path(input_srt_path).exists() else 'Does not exist'}")
                
                # Submit Celery task
                task_result = submit_video_pipeline_task(project_id, input_video_path, input_srt_path)
                logger.info(f"Celery task submission result: {task_result}")
                
                if task_result.get('success'):
                    celery_task_id = task_result['task_id']
                    logger.info(f"Celery task submitted: {celery_task_id}")
                    
                    # Update task record
                    task.celery_task_id = celery_task_id
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.utcnow()
                    db.commit()
                    
                    result = {
                        "status": "started",
                        "message": "Pipeline processing has started",
                        "project_id": project_id,
                        "task_id": task.id,
                        "celery_task_id": celery_task_id
                    }
                else:
                    error_msg = task_result.get('error', 'Unknown error')
                    raise ValueError(f"Failed to submit Celery task: {error_msg}")
                
                return result
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to auto-start pipeline: {e}")
            # Remove processing marker
            self.processing_projects.discard(project_id)
            
            # Update project status to failed
            await self._mark_project_failed(project_id, str(e))
            
            return {"status": "failed", "message": f"Launch failed: {str(e)}"}
    
    def _find_srt_file(self, project_id: str) -> Optional[str]:
        """Find project subtitle file"""
        try:
            from ..core.path_utils import get_project_directory
            project_dir = get_project_directory(project_id)
            
            # Find possible subtitle files
            srt_files = list(project_dir.glob("**/*.srt"))
            if srt_files:
                return str(srt_files[0])
            
            # Check raw directory
            raw_dir = project_dir / "raw"
            if raw_dir.exists():
                srt_files = list(raw_dir.glob("*.srt"))
                if srt_files:
                    return str(srt_files[0])
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to find subtitle file: {e}")
            return None
    
    def _create_processing_task(self, db: Session, project_id: str) -> Optional[Task]:
        """Create processing task record"""
        try:
            task = Task(
                project_id=project_id,
                name="Auto Video Processing Pipeline",
                task_type="video_processing",
                status=TaskStatus.PENDING,
                progress=0.0,
                current_step="Initializing",
                priority=0,
                metadata={
                    "auto_started": True,
                    "started_at": datetime.utcnow().isoformat()
                }
            )
            
            db.add(task)
            db.commit()
            db.refresh(task)
            
            logger.info(f"Created processing task: {task.id}")
            return task
            
        except Exception as e:
            logger.error(f"Failed to create task record: {e}")
            db.rollback()
            return None
    
    async def _mark_project_failed(self, project_id: str, error_message: str):
        """Mark project as failed status"""
        try:
            db = SessionLocal()
            try:
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.status = ProjectStatus.FAILED
                    project.updated_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"Project {project_id} marked as failed")
                    
                    # Remove from processing projects set
                    self.processing_projects.discard(project_id)
                    logger.info(f"Project {project_id} removed from processing set")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error marking project as failed: {e}")
    
    async def check_and_restart_failed_pipelines(self):
        """Check and restart failed pipelines"""
        try:
            db = SessionLocal()
            try:
                # Find failed projects
                failed_projects = db.query(Project).filter(
                    Project.status == ProjectStatus.FAILED
                ).all()
                
                for project in failed_projects:
                    logger.info(f"Checking failed project: {project.id}")
                    
                    # Check for incomplete tasks
                    incomplete_tasks = db.query(Task).filter(
                        Task.project_id == project.id,
                        Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
                    ).all()
                    
                    if not incomplete_tasks:
                        logger.info(f"Project {project.id} has no incomplete tasks, attempting restart")
                        await self.auto_start_pipeline(project.id)
                    else:
                        logger.info(f"Project {project.id} still has incomplete tasks, skipping restart")
                        
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error checking failed pipelines: {e}")
    
    async def auto_start_all_pending_pipelines(self):
        """Auto-start all pending pipelines"""
        try:
            db = SessionLocal()
            try:
                # Find all pending projects
                pending_projects = db.query(Project).filter(
                    Project.status == ProjectStatus.PENDING
                ).all()
                
                logger.info(f"Found {len(pending_projects)} pending projects")
                
                for project in pending_projects:
                    try:
                        logger.info(f"Auto-starting project pipeline: {project.id}")
                        result = await self.auto_start_pipeline(project.id)
                        logger.info(f"Project {project.id} launch result: {result}")
                        
                        # Avoid starting too many projects simultaneously
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Failed to auto-start project {project.id}: {e}")
                        continue
                        
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error auto-starting all pending pipelines: {e}")
    
    def get_processing_status(self) -> Dict[str, Any]:
        """Get processing status"""
        return {
            "processing_projects": list(self.processing_projects),
            "total_processing": len(self.processing_projects)
        }

# Global instance
auto_pipeline_service = AutoPipelineService()
