"""Video processing Celery tasks
Includes WebSocket real-time notifications and Pipeline adapter integration
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
from celery import current_task
from pathlib import Path

from backend.core.celery_app import celery_app
from backend.services.websocket_notification_service import notification_service
from backend.services.processing_service import ProcessingService
from backend.services.pipeline_adapter import create_pipeline_adapter
from backend.core.database import SessionLocal
from backend.models.project import Project, ProjectStatus
from backend.models.task import Task, TaskStatus, TaskType
from datetime import datetime

logger = logging.getLogger(__name__)

def run_async_notification(coro):
    """Helper function to run async notifications - fixes event loop conflicts"""
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If event loop is running, use thread pool execution
            import concurrent.futures
            import threading
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=10)  # 10 second timeout
        else:
            # If event loop is not running, run directly
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

@celery_app.task(bind=True, name='backend.tasks.processing.process_video_pipeline')
def process_video_pipeline(self, project_id: str, input_video_path: str, input_srt_path: str) -> Dict[str, Any]:
    """
    Video processing pipeline task - uses Pipeline adapter
    
    Args:
        project_id: Project ID
        input_video_path: Input video path
        input_srt_path: Input SRT path
        
    Returns:
        Processing result
    """
    task_id = self.request.id
    logger.info(f"Starting video pipeline processing: {project_id}, task ID: {task_id}")
    
    try:
        # Create database session
        db = SessionLocal()
        
        try:
            # Create task record
            task = Task(
                name=f"Video processing pipeline",
                description=f"Process complete video pipeline for project {project_id}",
                task_type=TaskType.VIDEO_PROCESSING,
                project_id=project_id,
                celery_task_id=task_id,
                status=TaskStatus.RUNNING,
                progress=0,
                current_step="Initializing",
                total_steps=6
            )
            db.add(task)
            db.commit()
            
            # Send start notification
            run_async_notification(
                notification_service.send_processing_start(project_id, task_id)
            )
            
            # Simplified progress system doesn't need complex callback functions
            # New progress system automatically sends progress events within the pipeline
            
            # Use simplified Pipeline adapter
            from backend.services.simple_pipeline_adapter import create_simple_pipeline_adapter
            pipeline_adapter = create_simple_pipeline_adapter(str(project_id), str(task.id))
            
            # Execute Pipeline processing - use async wrapper
            import asyncio
            result = asyncio.run(pipeline_adapter.process_project_sync(input_video_path, input_srt_path))
            
            # Check processing result
            if result.get("status") == "failed":
                # Processing failed
                error_msg = result.get("message", "Processing failed")
                task.status = TaskStatus.FAILED
                task.error_message = error_msg
                task.result_data = result
                
                # Update project status to failed
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.status = ProjectStatus.FAILED
                    project.updated_at = datetime.utcnow()
                    logger.info(f"Project status updated to failed: {project_id}")
                
                db.commit()
                
                # Failure status is automatically handled by simplified progress system
                
                # Send error notification (backward compatible) - WebSocket notifications disabled
                # run_async_notification(
                #     notification_service.send_processing_error(project_id, task_id, error_msg)
                # )
                
                return {
                    "success": False,
                    "project_id": project_id,
                    "task_id": task_id,
                    "error": error_msg,
                    "result": result
                }
            else:
                # Processing succeeded
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                task.current_step = "Processing complete"
                task.result_data = result
                
                # Update project status to completed
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.status = ProjectStatus.COMPLETED
                    project.completed_at = datetime.utcnow()
                    project.updated_at = datetime.utcnow()
                    logger.info(f"Project status updated to completed: {project_id}")
                
                db.commit()
                
                # Completion status is automatically handled by simplified progress system
                
                # Send completion notification (backward compatible) - WebSocket notifications disabled
                # run_async_notification(
                #     notification_service.send_processing_complete(project_id, task_id, result)
                # )
            
            logger.info(f"Video pipeline processing complete: {project_id}")
            return {
                "success": True,
                "project_id": project_id,
                "task_id": task_id,
                "result": result,
                "message": "Video processing pipeline complete"
            }
            
        finally:
            db.close()
            
    except Exception as e:
        error_msg = f"Video pipeline processing failed: {str(e)}"
        logger.error(error_msg)
        
        # Update task status to failed
        try:
            db = SessionLocal()
            task = db.query(Task).filter(Task.celery_task_id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = error_msg
                
                # Update project status to failed
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.status = ProjectStatus.FAILED
                    project.updated_at = datetime.utcnow()
                    logger.info(f"Project status updated to failed: {project_id}")
                
                db.commit()
            db.close()
        except Exception as db_error:
            logger.error(f"Failed to update task status: {str(db_error)}")
        
        # Send error notification
        run_async_notification(
            notification_service.send_processing_error(project_id, task_id, error_msg)
        )
        
        raise

@celery_app.task(bind=True, name='backend.tasks.processing.process_single_step')
def process_single_step(self, project_id: str, step: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process single step task
    
    Args:
        project_id: Project ID
        step: Step name
        config: Processing configuration
        
    Returns:
        Processing result
    """
    task_id = self.request.id
    logger.info(f"Starting single step processing: {project_id}, step: {step}, task ID: {task_id}")
    
    try:
        # Send start notification
        # Send processing start notification (backward compatible) - WebSocket notifications disabled
        # run_async_notification(
        #     notification_service.send_processing_start(project_id, task_id)
        # )
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Create processing service
            processing_service = ProcessingService(db)
            
            # Execute different processing based on step type
            if step == "outline":
                run_async_notification(
                    notification_service.send_processing_progress(project_id, task_id, 50, "Generating outline")
                )
                result = processing_service.generate_outline(project_id, config)
                
            elif step == "timeline":
                run_async_notification(
                    notification_service.send_processing_progress(project_id, task_id, 50, "Extracting timeline")
                )
                result = processing_service.extract_timeline(project_id, config)
                
            elif step == "titles":
                run_async_notification(
                    notification_service.send_processing_progress(project_id, task_id, 50, "Generating titles")
                )
                result = processing_service.generate_titles(project_id, config)
                
            elif step == "clips":
                run_async_notification(
                    notification_service.send_processing_progress(project_id, task_id, 50, "Video clipping")
                )
                result = processing_service.extract_clips(project_id, config)
                
            elif step == "collections":
                run_async_notification(
                    notification_service.send_processing_progress(project_id, task_id, 50, "Generating collections")
                )
                result = processing_service.generate_collections(project_id, config)
                
            else:
                raise Exception(f"Unknown step type: {step}")
            
            if not result.get("success"):
                raise Exception(f"Step {step} processing failed: {result.get('error')}")
            
            # Send completion notification
            run_async_notification(
                notification_service.send_processing_complete(project_id, task_id, result)
            )
            
            logger.info(f"Single step processing complete: {project_id}, step: {step}")
            return result
            
        finally:
            db.close()
            
    except Exception as e:
        error_msg = f"Single step processing failed: {str(e)}"
        logger.error(error_msg)
        
        # Send error notification
        run_async_notification(
            notification_service.send_processing_error(project_id, task_id, error_msg)
        )
        
        raise

@celery_app.task(bind=True, name='backend.tasks.processing.retry_processing_step')
def retry_processing_step(self, project_id: str, step: str, config: Dict[str, Any], 
                         original_task_id: str) -> Dict[str, Any]:
    """
    Retry processing step task
    
    Args:
        project_id: Project ID
        step: Step name
        config: Processing configuration
        original_task_id: Original task ID
        
    Returns:
        Processing result
    """
    task_id = self.request.id
    logger.info(f"Starting retry processing step: {project_id}, step: {step}, task ID: {task_id}")
    
    try:
        # Send start notification
        # Send processing start notification (backward compatible) - WebSocket notifications disabled
        # run_async_notification(
        #     notification_service.send_processing_start(project_id, task_id)
        # )
        
        # Send retry notification
        run_async_notification(
            notification_service.send_system_notification(
                "retry_started",
                "Retry started",
                f"Retrying step: {step}",
                "warning"
            )
        )
        
        # Call single step processing
        result = process_single_step.apply_async(
            args=[project_id, step, config],
            task_id=task_id
        ).get()
        
        # Send retry success notification
        run_async_notification(
            notification_service.send_system_notification(
                "retry_success",
                "Retry succeeded",
                f"Step {step} retry succeeded",
                "success"
            )
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Retry processing step failed: {str(e)}"
        logger.error(error_msg)
        
        # Send retry failure notification
        run_async_notification(
            notification_service.send_error_notification(
                "retry_failed",
                f"Step {step} retry failed",
                {"project_id": project_id, "step": step, "error": str(e)}
            )
        )
        
        raise
