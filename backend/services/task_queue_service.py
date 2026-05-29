"""
Task queue management service
Manages Celery task submission, monitoring, and status queries
"""

import logging
from typing import Dict, Any, Optional, List
from celery.result import AsyncResult
from sqlalchemy.orm import Session

from ..core.celery_app import celery_app
from ..core.database import SessionLocal
from ..models.task import Task, TaskStatus, TaskType
from ..repositories.task_repository import TaskRepository
from ..tasks.processing import process_video_pipeline, process_single_step, retry_processing_step
from ..tasks.video import extract_video_clips, generate_video_collections, optimize_video_quality
from ..tasks.notification import send_processing_notification, send_error_notification, send_completion_notification
from ..tasks.maintenance import cleanup_expired_tasks, health_check, backup_project_data

logger = logging.getLogger(__name__)


class TaskQueueService:
    """Task queue management service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository(db)
    
    def submit_video_processing_task(self, project_id: str, srt_path: str) -> Dict[str, Any]:
        """
        Submit video processing task
        
        Args:
            project_id: Project ID
            srt_path: SRT file path
            
        Returns:
            Task submission result
        """
        logger.info(f"Submitting video processing task: {project_id}")
        
        try:
            # Create and save task record
            task = self.task_repo.create(
                project_id=project_id,
                name="Video pipeline processing",
                description=f"Processing video pipeline for project {project_id}",
                task_type=TaskType.VIDEO_PROCESSING,
                status=TaskStatus.PENDING,
                priority=1
            )
            
            # Submit Celery task
            celery_task = process_video_pipeline.delay(project_id, srt_path)
            
            # Update task record
            task.celery_task_id = celery_task.id
            self.db.commit()
            
            logger.info(f"Video processing task submitted: {task.id}, Celery task ID: {celery_task.id}")
            
            return {
                'success': True,
                'task_id': task.id,
                'celery_task_id': celery_task.id,
                'status': 'PENDING',
                'message': 'Video processing task submitted'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit video processing task: {project_id}, error: {e}")
            raise
    
    def submit_single_step_task(self, project_id: str, step_name: str, srt_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit single step processing task
        
        Args:
            project_id: Project ID
            step_name: Step name
            srt_path: SRT file path (only needed for Step1)
            
        Returns:
            Task submission result
        """
        logger.info(f"Submitting single step task: {project_id}, {step_name}")
        
        try:
            # Create and save task record
            task = self.task_repo.create(
                project_id=project_id,
                name=f"Step processing: {step_name}",
                description=f"Processing step {step_name} for project {project_id}",
                task_type=TaskType.VIDEO_PROCESSING,
                status=TaskStatus.PENDING,
                priority=2
            )
            
            # Submit Celery task
            celery_task = process_single_step.delay(project_id, step_name, srt_path)
            
            # Update task record
            task.celery_task_id = celery_task.id
            self.db.commit()
            
            logger.info(f"Single step task submitted: {task.id}, Celery task ID: {celery_task.id}")
            
            return {
                'success': True,
                'task_id': task.id,
                'celery_task_id': celery_task.id,
                'step': step_name,
                'status': 'PENDING',
                'message': f'Step {step_name} processing task submitted'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit single step task: {project_id}, {step_name}, error: {e}")
            raise
    
    def submit_retry_task(self, project_id: str, task_id: str, step_name: str, srt_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit retry task
        
        Args:
            project_id: Project ID
            task_id: Task ID
            step_name: Step name
            srt_path: SRT file path (only needed for Step1)
            
        Returns:
            Task submission result
        """
        logger.info(f"Submitting retry task: {project_id}, {task_id}, {step_name}")
        
        try:
            # Create and save task record
            task = self.task_repo.create(
                project_id=project_id,
                name=f"Retry step: {step_name}",
                description=f"Retrying step {step_name} for project {project_id}",
                task_type=TaskType.VIDEO_PROCESSING,
                status=TaskStatus.PENDING,
                priority=3
            )
            
            # Submit Celery task
            celery_task = retry_processing_step.delay(project_id, task_id, step_name, srt_path)
            
            # Update task record
            task.celery_task_id = celery_task.id
            self.db.commit()
            
            logger.info(f"Retry task submitted: {task.id}, Celery task ID: {celery_task.id}")
            
            return {
                'success': True,
                'task_id': task.id,
                'celery_task_id': celery_task.id,
                'original_task_id': task_id,
                'step': step_name,
                'status': 'PENDING',
                'message': f'Step {step_name} retry task submitted'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit retry task: {project_id}, {task_id}, {step_name}, error: {e}")
            raise
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status info
        """
        try:
            # Get database task record
            task = self.task_repo.get_by_id(task_id)
            if not task:
                return {'error': 'Task does not exist'}
            
            # Get Celery task status
            celery_status = {}
            if task.celery_task_id:
                celery_result = AsyncResult(task.celery_task_id, app=celery_app)
                celery_status = {
                    'celery_task_id': task.celery_task_id,
                    'celery_status': celery_result.status,
                    'celery_result': celery_result.result if celery_result.ready() else None,
                    'celery_info': celery_result.info if hasattr(celery_result, 'info') else None
                }
            
            return {
                'task_id': task.id,
                'project_id': task.project_id,
                'name': task.name,
                'status': task.status.value,
                'task_type': task.task_type.value,
                'progress': task.progress,
                'error_message': task.error_message,
                'result': task.result_data,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'celery_status': celery_status
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status: {task_id}, error: {e}")
            return {'error': f'Failed to get task status: {e}'}
    
    def get_project_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all tasks for a project
        
        Args:
            project_id: Project ID
            
        Returns:
            Task list
        """
        try:
            tasks = self.task_repo.get_by_project(project_id)
            return [
                {
                    'task_id': task.id,
                    'name': task.name,
                    'status': task.status.value,
                    'task_type': task.task_type.value,
                    'progress': task.progress,
                    'created_at': task.created_at.isoformat(),
                    'updated_at': task.updated_at.isoformat()
                }
                for task in tasks
            ]
            
        except Exception as e:
            logger.error(f"Failed to get project tasks: {project_id}, error: {e}")
            return []
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        Cancel task
        
        Args:
            task_id: Task ID
            
        Returns:
            Cancellation result
        """
        try:
            task = self.task_repo.get_by_id(task_id)
            if not task:
                return {'error': 'Task does not exist'}
            
            # Cancel Celery task
            if task.celery_task_id:
                celery_result = AsyncResult(task.celery_task_id, app=celery_app)
                celery_result.revoke(terminate=True)
            
            # Update task status
            task.status = TaskStatus.CANCELLED
            self.db.commit()
            
            logger.info(f"Task cancelled: {task_id}")
            return {
                'success': True,
                'task_id': task_id,
                'status': 'CANCELLED',
                'message': 'Task cancelled'
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel task: {task_id}, error: {e}")
            return {'error': f'Failed to cancel task: {e}'}
    
    def submit_video_clips_task(self, project_id: str, clip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Submit video clip extraction task
        
        Args:
            project_id: Project ID
            clip_data: Clip data
            
        Returns:
            Task submission result
        """
        logger.info(f"Submitting video clip extraction task: {project_id}")
        
        try:
            # Create and save task record
            task = self.task_repo.create(
                project_id=project_id,
                name="Video clip extraction",
                description=f"Extracting video clips for project {project_id}",
                task_type=TaskType.VIDEO_PROCESSING,
                status=TaskStatus.PENDING,
                priority=2
            )
            
            # Submit Celery task
            celery_task = extract_video_clips.delay(project_id, clip_data)
            
            # Update task record
            task.celery_task_id = celery_task.id
            self.db.commit()
            
            logger.info(f"Video clip extraction task submitted: {task.id}, Celery task ID: {celery_task.id}")
            
            return {
                'success': True,
                'task_id': task.id,
                'celery_task_id': celery_task.id,
                'clip_count': len(clip_data),
                'status': 'PENDING',
                'message': f'Video clip extraction task submitted, total {len(clip_data)} clips'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit video clip extraction task: {project_id}, error: {e}")
            raise
    
    def submit_collection_generation_task(self, project_id: str, collection_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Submit collection generation task
        
        Args:
            project_id: Project ID
            collection_data: Collection data
            
        Returns:
            Task submission result
        """
        logger.info(f"Submitting collection generation task: {project_id}")
        
        try:
            # Create and save task record
            task = self.task_repo.create(
                project_id=project_id,
                name="Video collection generation",
                description=f"Generating video collection for project {project_id}",
                task_type=TaskType.VIDEO_PROCESSING,
                status=TaskStatus.PENDING,
                priority=2
            )
            
            # Submit Celery task
            celery_task = generate_video_collections.delay(project_id, collection_data)
            
            # Update task record
            task.celery_task_id = celery_task.id
            self.db.commit()
            
            logger.info(f"Collection generation task submitted: {task.id}, Celery task ID: {celery_task.id}")
            
            return {
                'success': True,
                'task_id': task.id,
                'celery_task_id': celery_task.id,
                'collection_count': len(collection_data),
                'status': 'PENDING',
                'message': f'Video collection generation task submitted, total {len(collection_data)} collections'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit collection generation task: {project_id}, error: {e}")
            raise 
