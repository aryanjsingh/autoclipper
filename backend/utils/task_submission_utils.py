"""
Task submission utility
Standalone utility functions to avoid circular import issues
"""

import logging
from typing import Dict, Any, Optional
from ..core.celery_app import celery_app

logger = logging.getLogger(__name__)

def submit_video_pipeline_task(project_id: str, input_video_path: str, input_srt_path: str) -> Dict[str, Any]:
    """
    Submit video pipeline task
    
    Args:
        project_id: Project ID
        input_video_path: Input video path
        input_srt_path: Input SRT path
        
    Returns:
        Task submission result
    """
    try:
        logger.info(f"Submitting video pipeline task: {project_id}")
        
        # Submit task directly using celery_app
        logger.info(f"Preparing to submit task to queue...")
        logger.info(f"Task name: backend.tasks.processing.process_video_pipeline")
        logger.info(f"Task parameters: {[project_id, input_video_path, input_srt_path]}")
        
        try:
            celery_task = celery_app.send_task(
                'backend.tasks.processing.process_video_pipeline',
                args=[project_id, input_video_path, input_srt_path]
            )
            
            logger.info(f"Video pipeline task submitted: {celery_task.id}")
            logger.info(f"Task status: {celery_task.state}")
            
            # Check if task was really submitted to queue
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            queue_length = r.llen('processing')
            logger.info(f"Redis queue length: {queue_length}")
            
        except Exception as e:
            logger.error(f"Exception during task submission: {e}")
            raise
        
        return {
            'success': True,
            'task_id': celery_task.id,
            'status': 'PENDING',
            'message': 'Video pipeline task submitted'
        }
        
    except Exception as e:
        logger.error(f"Failed to submit video pipeline task: {project_id}, error: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Task submission failed'
        }

def submit_single_step_task(project_id: str, step: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit single step task
    
    Args:
        project_id: Project ID
        step: Step name
        config: Processing configuration
        
    Returns:
        Task submission result
    """
    try:
        logger.info(f"Submitting single step task: {project_id}, {step}")
        
        # Submit task directly using celery_app
        celery_task = celery_app.send_task(
            'tasks.processing.process_single_step',
            args=[project_id, step, config]
        )
        
        logger.info(f"Single step task submitted: {celery_task.id}")
        
        return {
            'success': True,
            'task_id': celery_task.id,
            'step': step,
            'status': 'PENDING',
            'message': f'Step {step} task submitted'
        }
        
    except Exception as e:
        logger.error(f"Failed to submit single step task: {project_id}, {step}, error: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Task submission failed'
        }
