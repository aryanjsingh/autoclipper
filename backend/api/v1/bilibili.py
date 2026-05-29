"""
Bilibili-related API routes
Handle Bilibili video parsing and download functionality
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from pydantic import BaseModel
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from ...utils.bilibili_downloader import BilibiliDownloader, get_bilibili_video_info
from ...core.config import get_data_directory
from pathlib import Path
import uuid
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Store download task status
download_tasks = {}

class BilibiliParseRequest(BaseModel):
    url: str
    browser: Optional[str] = None

class BilibiliDownloadRequest(BaseModel):
    url: str
    project_name: str
    video_category: Optional[str] = "default"
    browser: Optional[str] = None

class BilibiliVideoInfo(BaseModel):
    title: str
    description: str
    duration: int
    uploader: str
    upload_date: str
    view_count: int
    like_count: int
    thumbnail: str

class BilibiliDownloadTask(BaseModel):
    id: str
    url: str
    project_name: str
    video_category: str
    status: str  # pending, processing, completed, failed
    progress: float
    error_message: Optional[str] = None
    project_id: Optional[str] = None
    created_at: str
    updated_at: str

@router.post("/parse")
async def parse_bilibili_video(
    url: str = Form(...),
    browser: Optional[str] = Form(None)
):
    """Parse Bilibili video info"""
    try:
        logger.info(f"Starting Bilibili video parsing: {url}")
        
        # Validate URL format
        downloader = BilibiliDownloader(browser=browser)
        if not downloader.validate_bilibili_url(url):
            raise HTTPException(status_code=400, detail="Invalid Bilibili video link")
        
        # Get real video info
        video_info = await downloader.get_video_info(url)
        
        logger.info(f"Video info parsed successfully: {video_info.title}")
        
        return {
            "success": True,
            "video_info": {
                "title": video_info.title,
                "description": video_info.description,
                "duration": video_info.duration,
                "uploader": video_info.uploader,
                "upload_date": video_info.upload_date,
                "view_count": video_info.view_count,
                "like_count": 0,  # Bilibili API may not provide like count
                "thumbnail": video_info.thumbnail_url
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to parse Bilibili video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")

@router.post("/download")
async def create_bilibili_download_task(request: BilibiliDownloadRequest):
    """Create Bilibili video download task - create project immediately"""
    try:
        logger.info(f"Creating Bilibili download task: {request.url}")
        
        # First get video info to get thumbnail
        from ...utils.bilibili_downloader import BilibiliDownloader
        downloader = BilibiliDownloader(browser=request.browser)
        video_info = await downloader.get_video_info(request.url)
        
        # Create project record immediately
        from ...core.database import SessionLocal
        from ...services.project_service import ProjectService
        from ...schemas.project import ProjectCreate, ProjectType, ProjectStatus
        
        db = SessionLocal()
        try:
            project_service = ProjectService(db)
            
            # Process thumbnail - use parsed cover image directly
            thumbnail_data = None
            if video_info.thumbnail_url:
                try:
                    import requests
                    import base64
                    
                    # Download thumbnail
                    response = requests.get(video_info.thumbnail_url, timeout=10)
                    if response.status_code == 200:
                        # Convert to base64
                        thumbnail_base64 = base64.b64encode(response.content).decode('utf-8')
                        thumbnail_data = f"data:image/jpeg;base64,{thumbnail_base64}"
                        logger.info(f"Bilibili thumbnail retrieved: {video_info.title}")
                    else:
                        logger.warning(f"Failed to download Bilibili thumbnail: {response.status_code}")
                except Exception as e:
                    logger.error(f"Failed to process Bilibili thumbnail: {e}")
                    # Thumbnail processing failure does not affect main flow
            
            # Create project data
            project_data = ProjectCreate(
                name=request.project_name,
                description=f"Downloaded from Bilibili: {video_info.title}",
                project_type=ProjectType(request.video_category),
                status=ProjectStatus.PENDING,  # Initial status is pending
                source_url=request.url,
                source_file=None,  # Empty for now, updated after download
                settings={
                    "download_status": "downloading",
                    "download_progress": 0.0,
                    "bilibili_info": {
                        "url": request.url,
                        "browser": request.browser,
                        "title": video_info.title,
                        "uploader": video_info.uploader,
                        "duration": video_info.duration,
                        "view_count": video_info.view_count,
                        "thumbnail_url": video_info.thumbnail_url
                    }
                }
            )
            
            project = project_service.create_project(project_data)
            project_id = str(project.id)
            
            # Set thumbnail
            if thumbnail_data:
                project.thumbnail = thumbnail_data
                db.commit()
                logger.info(f"Project {project_id} thumbnail set")
            
            # Create project directory
            from ...core.path_utils import get_project_directory
            project_dir = get_project_directory(project_id)
            raw_dir = project_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Project created: {project_id}")
            
            # Generate download task ID
            task_id = str(uuid.uuid4())
            
            # Create task record
            task = BilibiliDownloadTask(
                id=task_id,
                url=request.url,
                project_name=request.project_name,
                video_category=request.video_category,
                status="pending",
                progress=0.0,
                project_id=project_id,  # Associate project ID
                created_at=str(uuid.uuid1().time),
                updated_at=str(uuid.uuid1().time)
            )
            
            # Store task
            download_tasks[task_id] = task
            
            # Async start download task - using safe task manager
            from .async_task_manager import task_manager
            await task_manager.create_safe_task(
                f"bilibili_download_{task_id}", 
                process_download_task, 
                task_id, 
                request, 
                project_id
            )
            
            # Return project info instead of task info
            return {
                "project_id": project_id,
                "task_id": task_id,
                "status": "created",
                "message": "Project created, downloading..."
            }
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Failed to create download task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.get("/tasks/{task_id}")
async def get_bilibili_task_status(task_id: str):
    """Get download task status"""
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return download_tasks[task_id]

@router.get("/tasks")
async def get_all_bilibili_tasks():
    """Get all download tasks"""
    return list(download_tasks.values())

async def update_project_download_progress(project_id: str, progress: float, message: str):
    """Update project download progress"""
    try:
        from ...core.database import SessionLocal
        from ...services.project_service import ProjectService
        
        db = SessionLocal()
        try:
            project_service = ProjectService(db)
            project = project_service.get(project_id)
            
            if project:
                # Update download progress in project settings
                if not project.processing_config:
                    project.processing_config = {}
                
                project.processing_config.update({
                    "download_progress": progress,
                    "download_message": message
                })
                
                # If progress reaches 100%, update status to pending
                if progress >= 100.0:
                    from ...schemas.project import ProjectStatus
                    project.status = ProjectStatus.PENDING
                
                db.commit()
                logger.info(f"Project {project_id} download progress updated: {progress}% - {message}")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to update project download progress: {e}")

async def process_download_task(task_id: str, request: BilibiliDownloadRequest, project_id: str):
    """Process download task"""
    try:
        # Update task status to processing
        download_tasks[task_id].status = "processing"
        download_tasks[task_id].progress = 10.0
        
        # Update project status and progress
        await update_project_download_progress(project_id, 10.0, "Getting video info...")
        
        # Get video info
        video_info = await get_bilibili_video_info(request.url, request.browser)
        download_tasks[task_id].progress = 30.0
        
        # Update project progress
        await update_project_download_progress(project_id, 30.0, "Downloading video...")
        
        # Download video
        data_dir = get_data_directory()
        download_dir = data_dir / "temp"
        download_dir.mkdir(exist_ok=True)
        
        from ...utils.bilibili_downloader import download_bilibili_video
        download_result = await download_bilibili_video(
            request.url, 
            download_dir, 
            request.browser
        )
        
        video_path = download_result.get('video_path', '')
        subtitle_path = download_result.get('subtitle_path', '')
        
        # Update project progress
        await update_project_download_progress(project_id, 60.0, "Video download completed, processing subtitles...")
        
        # If no subtitle file, prioritize using Whisper to generate subtitles
        if not subtitle_path and video_path:
            logger.info("Prioritizing Whisper for high-quality subtitle generation")
            # Update project progress
            await update_project_download_progress(project_id, 70.0, "Generating subtitles with Whisper...")
            
            try:
                from ...utils.speech_recognizer import generate_subtitle_for_video, SpeechRecognitionError
                from pathlib import Path
                video_file_path = Path(video_path)
                
                # Select appropriate model based on video info, but always use auto language detection
                model = "base"  # Default to balanced model
                language = "auto"  # Always use auto language detection
                
                # Can judge content type based on video title or description, select different model sizes
                if video_info.title and any(keyword in video_info.title.lower() for keyword in ['tutorial', 'lesson', 'knowledge', 'science']):
                    model = "small"  # Knowledge content uses more accurate model
                elif video_info.title and any(keyword in video_info.title.lower() for keyword in ['speech', 'lecture', 'sharing']):
                    model = "medium"  # Speech content uses high-accuracy model
                
                logger.info(f"Using Whisper to generate subtitles - language: {language}, model: {model}")
                
                generated_subtitle = generate_subtitle_for_video(
                    video_file_path,
                    language=language,
                    model=model
                )
                subtitle_path = str(generated_subtitle)
                logger.info(f"Whisper subtitle generation successful: {subtitle_path}")
                
                # Update project progress
                await update_project_download_progress(project_id, 90.0, "Subtitle generation completed, preparing for processing...")
                
            except SpeechRecognitionError as e:
                logger.error(f"Whisper subtitle generation failed: {e}")
                # When Whisper fails, mark project as failed
                logger.error("Subtitle file does not exist and Whisper generation failed, project will be marked as failed")
                subtitle_path = None  # Ensure subtitle path is empty, will mark project as failed later
            except Exception as e:
                logger.error(f"Unknown error during subtitle generation: {e}")
                subtitle_path = None  # Ensure subtitle path is empty, will mark project as failed later
        
        download_tasks[task_id].progress = 80.0
        
        # Update project info (project was already created at start)
        from ...services.project_service import ProjectService
        from ...core.database import SessionLocal
        
        db = SessionLocal()
        try:
            project_service = ProjectService(db)
            
            # Get created project
            project = project_service.get(project_id)
            if not project:
                raise Exception(f"Project {project_id} does not exist")
            
            # Update project info
            project.description = f"Downloaded from Bilibili: {video_info.title}"
            # Note: Do not set video_path here, wait until file move is complete
            
            # Update project settings
            if not project.processing_config:
                project.processing_config = {}
            
            project.processing_config.update({
                "bilibili_info": {
                    "title": video_info.title,
                    "uploader": video_info.uploader,
                    "duration": video_info.duration,
                    "view_count": video_info.view_count
                },
                "subtitle_path": subtitle_path if subtitle_path else None,
                "download_status": "completed",
                "download_progress": 100.0
            })
            
            # Move files to project directory
            from ...core.path_utils import get_project_directory
            project_dir = get_project_directory(project_id)
            raw_dir = project_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            
            # Move video file to project directory
            import shutil
            from pathlib import Path
            
            if video_path:
                video_file_path = Path(video_path)
                if video_file_path.exists():
                    # Rename video file to input.mp4
                    new_video_path = raw_dir / "input.mp4"
                    shutil.move(str(video_file_path), str(new_video_path))
                    logger.info(f"Video file moved to: {new_video_path}")
                    
                    # Update video path in project
                    project.video_path = str(new_video_path)
            
            # Move subtitle file to project directory
            if subtitle_path and subtitle_path.strip():
                subtitle_file_path = Path(subtitle_path)
                if subtitle_file_path.exists():
                    # Rename subtitle file to input.srt
                    new_subtitle_path = raw_dir / "input.srt"
                    shutil.move(str(subtitle_file_path), str(new_subtitle_path))
                    logger.info(f"Subtitle file moved to: {new_subtitle_path}")
                    
                    # Update subtitle path in project processing config
                    if not project.processing_config:
                        project.processing_config = {}
                    project.processing_config["subtitle_path"] = str(new_subtitle_path)
            
            # Save project updates
            db.commit()
            
            # Check if subtitle file exists, mark project as failed if not
            srt_file_path = raw_dir / "input.srt"
            if not srt_file_path.exists():
                logger.error(f"Subtitle file does not exist: {srt_file_path}, project will be marked as failed")
                from ...schemas.project import ProjectStatus
                project.status = ProjectStatus.FAILED
                if not project.processing_config:
                    project.processing_config = {}
                project.processing_config["error_message"] = "Subtitle file does not exist and Whisper generation failed"
                db.commit()
                
                # Update task status to failed
                download_tasks[task_id].status = "failed"
                download_tasks[task_id].error_message = "Subtitle file does not exist and Whisper generation failed"
                download_tasks[task_id].progress = 0.0
                download_tasks[task_id].project_id = str(project.id)
                download_tasks[task_id].updated_at = datetime.now().isoformat()
                
                # Update project download progress to failed
                await update_project_download_progress(project_id, 0.0, "Download failed: subtitle file does not exist")
                
                logger.info(f"Bilibili download task failed: {task_id}, project ID: {project.id}, reason: subtitle file does not exist")
                return
            
            # Update project download progress to completed
            await update_project_download_progress(project_id, 100.0, "Download completed, preparing to start processing")
            
            # Update task status
            download_tasks[task_id].status = "completed"
            download_tasks[task_id].progress = 100.0
            download_tasks[task_id].project_id = str(project.id)
            download_tasks[task_id].updated_at = datetime.now().isoformat()
            
            logger.info(f"Bilibili download task completed: {task_id}, project ID: {project.id}")
            
            # Auto-start processing pipeline
            try:
                # Update project status to pending
                from ...schemas.project import ProjectStatus
                project.status = ProjectStatus.PENDING  # Change to PENDING, let automation service start
                db.commit()
                
                logger.info(f"Bilibili project {project.id} download completed, waiting for automation pipeline to start")
                
                # Async start automation pipeline
                import asyncio
                from ...services.auto_pipeline_service import auto_pipeline_service
                
                # Use create_task to execute in already running event loop
                try:
                    loop = asyncio.get_running_loop()
                    # Create task in already running event loop
                    task = loop.create_task(
                        auto_pipeline_service.auto_start_pipeline(str(project.id))
                    )
                    # Wait for task completion
                    pipeline_result = await task
                except RuntimeError:
                    # If no running event loop, create new one
                    pipeline_result = await auto_pipeline_service.auto_start_pipeline(str(project.id))
                
                if pipeline_result['status'] == 'started':
                    logger.info(f"Bilibili project {project.id} automation pipeline started: {pipeline_result}")
                else:
                    logger.warning(f"Bilibili project {project.id} automation pipeline start result: {pipeline_result}")
                
            except Exception as e:
                logger.error(f"Failed to start Bilibili project {project.id} automation pipeline: {str(e)}")
                # Even if processing fails to start, return download success
                # User can restart processing via retry button
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to process download task: {str(e)}")
        download_tasks[task_id].status = "failed"
        download_tasks[task_id].error_message = str(e)
        download_tasks[task_id].progress = 0.0
