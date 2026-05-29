"""
Enhanced retry mechanism
Supports complete retry flow from download to processing
"""

import logging
import uuid
from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...core.database import get_db
from ...models.project import Project, ProjectStatus
from ...models.task import Task, TaskStatus, TaskType
from ...services.project_service import ProjectService
from ...services.processing_service import ProcessingService
from ...core.config import get_data_directory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retry", tags=["Enhanced Retry"])

class RetryStrategy(str, Enum):
    """Retry strategy enumeration"""
    DOWNLOAD_ONLY = "download_only"      # Only retry download
    PROCESSING_ONLY = "processing_only"  # Only retry processing
    FULL_RETRY = "full_retry"           # Full retry (download + processing)
    SMART_RETRY = "smart_retry"         # Smart retry (auto-determine)

class RetryRequest(BaseModel):
    """Retry request"""
    strategy: Optional[RetryStrategy] = RetryStrategy.SMART_RETRY
    force_redownload: bool = False  # Whether to force re-download
    browser: Optional[str] = None   # Browser setting (used for download)

class RetryResponse(BaseModel):
    """Retry response"""
    success: bool
    message: str
    strategy_used: RetryStrategy
    project_id: str
    task_id: Optional[str] = None
    download_task_id: Optional[str] = None

def determine_retry_strategy(project: Project, force_redownload: bool = False) -> RetryStrategy:
    """Intelligently determine retry strategy"""
    if force_redownload:
        return RetryStrategy.FULL_RETRY
    
    # Check if video file exists
    video_exists = project.video_path and Path(project.video_path).exists()
    
    if not video_exists:
        return RetryStrategy.FULL_RETRY  # No video file, full retry
    
    # Check project status
    if project.status == ProjectStatus.FAILED:
        return RetryStrategy.PROCESSING_ONLY  # Has video file but processing failed, only retry processing
    elif project.status == ProjectStatus.PENDING:
        return RetryStrategy.PROCESSING_ONLY  # Has video file but not processed, only retry processing
    else:
        return RetryStrategy.SMART_RETRY

async def retry_download_only(
    project_id: str, 
    browser: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Only retry download"""
    try:
        # Get project info
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get original download info (extracted from project description)
        description = project.description or ""
        if "Downloaded from Bilibili:" in description:
            # Bilibili project
            url = description.replace("Downloaded from Bilibili:", "").strip()
            return await retry_bilibili_download(project_id, url, browser, db)
        elif "Downloaded from YouTube:" in description:
            # YouTube project
            url = description.replace("Downloaded from YouTube:", "").strip()
            return await retry_youtube_download(project_id, url, browser, db)
        else:
            raise HTTPException(status_code=400, detail="Unable to determine download source")
    
    except Exception as e:
        logger.error(f"Retry download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retry download failed: {str(e)}")

async def retry_bilibili_download(
    project_id: str, 
    url: str, 
    browser: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retry Bilibili download"""
    try:
        # Import Bilibili download related modules
        from .bilibili import process_download_task, BilibiliDownloadRequest
        from .async_task_manager import task_manager
        
        # Create download request
        request = BilibiliDownloadRequest(
            url=url,
            project_name=db.query(Project).filter(Project.id == project_id).first().name,
            video_category="default",
            browser=browser
        )
        
        # Generate new download task ID
        task_id = str(uuid.uuid4())
        
        # Start download task
        await task_manager.create_safe_task(
            f"bilibili_retry_{task_id}",
            process_download_task,
            task_id,
            request,
            project_id
        )
        
        return {
            "success": True,
            "message": "Bilibili download retry started",
            "task_id": task_id
        }
    
    except Exception as e:
        logger.error(f"Retry Bilibili download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retry Bilibili download failed: {str(e)}")

async def retry_youtube_download(
    project_id: str, 
    url: str, 
    browser: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retry YouTube download"""
    try:
        # Import YouTube download related modules
        from .youtube import process_youtube_download_task, YouTubeDownloadRequest
        from .async_task_manager import task_manager
        
        # Create download request
        request = YouTubeDownloadRequest(
            url=url,
            project_name=db.query(Project).filter(Project.id == project_id).first().name,
            video_category="default",
            browser=browser
        )
        
        # Generate new download task ID
        task_id = str(uuid.uuid4())
        
        # Start download task
        await task_manager.create_safe_task(
            f"youtube_retry_{task_id}",
            process_youtube_download_task,
            task_id,
            request,
            project_id
        )
        
        return {
            "success": True,
            "message": "YouTube download retry started",
            "task_id": task_id
        }
    
    except Exception as e:
        logger.error(f"Retry YouTube download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retry YouTube download failed: {str(e)}")

async def retry_processing_only(
    project_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Only retry processing"""
    try:
        # Use existing processing service
        processing_service = ProcessingService(db)
        
        # Get project info
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check video file
        if not project.video_path or not Path(project.video_path).exists():
            raise HTTPException(status_code=400, detail="Video file does not exist, please retry download first")
        
        # Reset project status
        project.status = ProjectStatus.PENDING
        db.commit()
        
        # Start processing task
        result = processing_service.start_processing(
            project_id=project_id,
            srt_path=Path(project.video_path).parent / "input.srt" if (project.video_path and Path(project.video_path).parent / "input.srt").exists() else None
        )
        
        return {
            "success": True,
            "message": "Processing retry started",
            "task_id": result.get("task_id")
        }
    
    except Exception as e:
        logger.error(f"Retry processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retry processing failed: {str(e)}")

@router.post("/projects/{project_id}/smart-retry", response_model=RetryResponse)
async def smart_retry_project(
    project_id: str,
    request: RetryRequest,
    db: Session = Depends(get_db)
):
    """Smart retry project"""
    try:
        # Get project info
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Determine retry strategy
        if request.strategy == RetryStrategy.SMART_RETRY:
            strategy = determine_retry_strategy(project, request.force_redownload)
        else:
            strategy = request.strategy
        
        logger.info(f"Project {project_id} using retry strategy: {strategy}")
        
        # Execute retry
        if strategy == RetryStrategy.FULL_RETRY:
            # Full retry: first retry download, auto-start processing after download
            download_result = await retry_download_only(project_id, request.browser, db)
            return RetryResponse(
                success=True,
                message="Full retry started (download + processing)",
                strategy_used=strategy,
                project_id=project_id,
                download_task_id=download_result.get("task_id")
            )
        
        elif strategy == RetryStrategy.DOWNLOAD_ONLY:
            # Only retry download
            download_result = await retry_download_only(project_id, request.browser, db)
            return RetryResponse(
                success=True,
                message="Download retry started",
                strategy_used=strategy,
                project_id=project_id,
                download_task_id=download_result.get("task_id")
            )
        
        elif strategy == RetryStrategy.PROCESSING_ONLY:
            # Only retry processing
            processing_result = await retry_processing_only(project_id, db)
            return RetryResponse(
                success=True,
                message="Processing retry started",
                strategy_used=strategy,
                project_id=project_id,
                task_id=processing_result.get("task_id")
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported retry strategy: {strategy}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Smart retry failed: {e}")
        raise HTTPException(status_code=500, detail=f"Smart retry failed: {str(e)}")

@router.get("/projects/{project_id}/retry-strategy")
async def get_retry_strategy(
    project_id: str,
    force_redownload: bool = False,
    db: Session = Depends(get_db)
):
    """Get suggested retry strategy"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        strategy = determine_retry_strategy(project, force_redownload)
        
        return {
            "project_id": project_id,
            "suggested_strategy": strategy,
            "reason": _get_strategy_reason(project, strategy),
            "video_exists": project.video_path and Path(project.video_path).exists(),
            "project_status": project.status
        }
    
    except Exception as e:
        logger.error(f"Failed to get retry strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get retry strategy: {str(e)}")

def _get_strategy_reason(project: Project, strategy: RetryStrategy) -> str:
    """Get strategy selection reason"""
    if strategy == RetryStrategy.FULL_RETRY:
        return "No video file or forced re-download"
    elif strategy == RetryStrategy.PROCESSING_ONLY:
        return "Video file exists but processing failed or not started"
    elif strategy == RetryStrategy.DOWNLOAD_ONLY:
        return "Only retry download stage"
    else:
        return "Intelligent determination"
