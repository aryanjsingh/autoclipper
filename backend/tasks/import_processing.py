"""
Local import processing tasks
Handles asynchronous tasks after video file upload: subtitle generation, thumbnail generation, processing pipeline initiation
"""

import logging
from pathlib import Path
from typing import Optional
from celery import Celery
from backend.core.database import get_db
from backend.services.project_service import ProjectService
from backend.utils.thumbnail_generator import generate_project_thumbnail
from backend.utils.task_submission_utils import submit_video_pipeline_task

logger = logging.getLogger(__name__)

# Get Celery application instance
from backend.core.celery_app import celery_app

@celery_app.task(bind=True)
def process_import_task(self, project_id: str, video_path: str, srt_file_path: Optional[str] = None):
    """
    Process local import asynchronous task
    
    Args:
        project_id: Project ID
        video_path: Video file path
        srt_file_path: Subtitle file path (optional)
    """
    try:
        logger.info(f"Starting import task processing: {project_id}")
        
        # Get database session
        db = next(get_db())
        project_service = ProjectService(db)
        
        # Update task progress
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Starting processing...'})
        
        # 1. Check and generate thumbnail (if not already present)
        logger.info(f"Checking thumbnail for project {project_id}...")
        self.update_state(state='PROGRESS', meta={'progress': 20, 'message': 'Checking thumbnail...'})
        
        project = project_service.get(project_id)
        if project and not project.thumbnail:
            logger.info(f"Project {project_id} has no thumbnail, starting generation...")
            self.update_state(state='PROGRESS', meta={'progress': 25, 'message': 'Generating thumbnail...'})
            
            try:
                thumbnail_data = generate_project_thumbnail(project_id, Path(video_path))
                if thumbnail_data:
                    project.thumbnail = thumbnail_data
                    db.commit()
                    logger.info(f"Project {project_id} thumbnail generated and saved successfully")
                else:
                    logger.warning(f"Project {project_id} thumbnail generation failed")
            except Exception as e:
                logger.error(f"Error generating project thumbnail: {e}")
                # Thumbnail generation failure doesn't affect subsequent process
        else:
            logger.info(f"Project {project_id} already has thumbnail, skipping generation")
        
        # 2. Generate subtitles (if not provided)
        srt_path = srt_file_path
        if not srt_path:
            logger.info(f"Starting subtitle generation for project {project_id}...")
            self.update_state(state='PROGRESS', meta={'progress': 40, 'message': 'Generating subtitles...'})
            
            try:
                from backend.utils.speech_recognizer import generate_subtitle_for_video
                
                # Select model based on video category
                project = project_service.get(project_id)
                video_category = "knowledge"  # Default category
                if project and project.processing_config:
                    video_category = project.processing_config.get("video_category", "knowledge")
                
                model = "base"  # Default use balanced model
                if video_category in ["business", "knowledge"]:
                    model = "small"  # Knowledge content uses more accurate model
                elif video_category == "speech":
                    model = "medium"  # Speech content uses high-precision model
                
                logger.info(f"Using Whisper to generate subtitles - language: auto, model: {model}")
                
                generated_subtitle = generate_subtitle_for_video(
                    Path(video_path),
                    language="auto",
                    model=model
                )
                srt_path = str(generated_subtitle)
                logger.info(f"Whisper subtitle generation successful: {srt_path}")
                
            except Exception as e:
                logger.error(f"Whisper subtitle generation failed: {str(e)}")
                # Subtitle generation failed, use empty subtitle file
                srt_path = None
        
        # 3. Update project status to processing
        logger.info(f"Updating project {project_id} status to processing...")
        self.update_state(state='PROGRESS', meta={'progress': 80, 'message': 'Starting processing pipeline...'})
        
        project_service.update_project_status(project_id, "processing")
        
        # 4. Start processing pipeline
        if srt_path and Path(srt_path).exists():
            try:
                task_result = submit_video_pipeline_task(
                    project_id=project_id,
                    input_video_path=video_path,
                    input_srt_path=srt_path
                )
                
                if task_result['success']:
                    logger.info(f"Project {project_id} processing task started, Celery task ID: {task_result['task_id']}")
                    self.update_state(state='PROGRESS', meta={'progress': 100, 'message': 'Processing pipeline started'})
                else:
                    logger.error(f"Celery task submission failed: {task_result['error']}")
                    project_service.update_project_status(project_id, "failed")
                    self.update_state(state='FAILURE', meta={'error': task_result['error']})
                    return
                    
            except Exception as e:
                logger.error(f"Failed to start project {project_id} processing: {str(e)}")
                project_service.update_project_status(project_id, "failed")
                self.update_state(state='FAILURE', meta={'error': str(e)})
                return
        else:
            logger.error(f"Subtitle file does not exist: {srt_path}")
            project_service.update_project_status(project_id, "failed")
            self.update_state(state='FAILURE', meta={'error': 'Subtitle file does not exist'})
            return
        
        logger.info(f"Import task complete: {project_id}")
        return {
            'status': 'completed',
            'project_id': project_id,
            'message': 'Import processing complete'
        }
        
    except Exception as e:
        logger.error(f"Import task failed: {project_id}, error: {e}")
        
        # Update project status to failed
        try:
            db = next(get_db())
            project_service = ProjectService(db)
            project_service.update_project_status(project_id, "failed")
        except:
            pass
        
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
    finally:
        try:
            db.close()
        except:
            pass
