"""
Clips API routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ...core.database import get_db
from ...services.clip_service import ClipService
from ...schemas.clip import ClipCreate, ClipUpdate, ClipResponse, ClipListResponse, ClipStatus, ClipFilter
from ...schemas.base import PaginationParams
from ...models.clip import Clip
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_clip_service(db: Session = Depends(get_db)) -> ClipService:
    """Dependency to get clip service."""
    return ClipService(db)


@router.patch("/{clip_id}/title", response_model=ClipResponse)
async def update_clip_title(
    clip_id: str,
    title_data: dict,
    clip_service: ClipService = Depends(get_clip_service)
):
    """Update clip title."""
    try:
        new_title = title_data.get("title", "").strip()
        if not new_title:
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        
        if len(new_title) > 200:
            raise HTTPException(status_code=400, detail="Title length cannot exceed 200 characters")
        
        # Update clip title
        clip = clip_service.update_clip(clip_id, ClipUpdate(title=new_title))
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        # Return updated clip info
        return ClipResponse(
            id=str(clip.id),
            project_id=str(clip.project_id),
            title=str(clip.title),
            description=str(clip.description) if clip.description else None,
            start_time=getattr(clip, 'start_time', 0),
            end_time=getattr(clip, 'end_time', 0),
            duration=int(getattr(clip, 'duration', 0)),
            score=getattr(clip, 'score', None),
            status=getattr(clip, 'status', 'pending'),
            video_path=getattr(clip, 'video_path', None),
            tags=getattr(clip, 'tags', []) or [],
            clip_metadata=getattr(clip, 'clip_metadata', {}) or {},
            created_at=getattr(clip, 'created_at', None),
            updated_at=getattr(clip, 'updated_at', None),
            collection_ids=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update clip title: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update clip title: {str(e)}")


@router.post("/{clip_id}/generate-title", response_model=dict)
async def generate_clip_title(
    clip_id: str,
    clip_service: ClipService = Depends(get_clip_service)
):
    """Generate a new title for a clip using LLM."""
    try:
        # Get clip info
        clip = clip_service.get(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        # Get content directly from clip_metadata
        clip_metadata = getattr(clip, 'clip_metadata', {}) or {}
        
        if not clip_metadata:
            raise HTTPException(status_code=404, detail="Clip metadata not found")
        
        # Prepare LLM input data
        llm_input = [{
            "id": clip_id,
            "title": clip_metadata.get('outline', '') or getattr(clip, 'title', ''),
            "content": clip_metadata.get('content', []),
            "recommend_reason": clip_metadata.get('recommend_reason', '')
        }]
        
        # Call LLM to generate title
        from ...utils.llm_client import LLMClient
        from ...core.shared_config import PROMPT_FILES
        
        llm_client = LLMClient()
        
        # Load title generation prompt
        with open(PROMPT_FILES['title'], 'r', encoding='utf-8') as f:
            title_prompt = f.read()
        
        # Call LLM
        raw_response = llm_client.call_with_retry(title_prompt, llm_input)
        
        if not raw_response:
            raise HTTPException(status_code=500, detail="LLM call failed")
        
        # Parse LLM response
        titles_map = llm_client.parse_json_response(raw_response)
        
        if not isinstance(titles_map, dict) or clip_id not in titles_map:
            raise HTTPException(status_code=500, detail="LLM returned invalid format")
        
        generated_title = titles_map[clip_id]
        
        return {
            "clip_id": clip_id,
            "generated_title": generated_title,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate clip title: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate clip title: {str(e)}")


@router.post("/", response_model=ClipResponse)
async def create_clip(
    clip_data: ClipCreate,
    clip_service: ClipService = Depends(get_clip_service)
):
    """Create a new clip."""
    try:
        clip = clip_service.create_clip(clip_data)
        # Convert to response schema
        status_obj = getattr(clip, 'status', None)
        status_value = status_obj.value if hasattr(status_obj, 'value') else 'pending'
        
        return ClipResponse(
            id=str(getattr(clip, 'id', '')),
            project_id=str(getattr(clip, 'project_id', '')),
            title=str(getattr(clip, 'title', '')),
            description=str(getattr(clip, 'description', '')) if getattr(clip, 'description', None) else None,
            start_time=getattr(clip, 'start_time', 0),
            end_time=getattr(clip, 'end_time', 0),
            duration=getattr(clip, 'duration', 0),
            score=getattr(clip, 'score', None),
            status=status_value,
            video_path=getattr(clip, 'video_path', None),
            tags=getattr(clip, 'tags', []) or [],
            clip_metadata=getattr(clip, 'clip_metadata', {}) or {},
            created_at=getattr(clip, 'created_at', None) if isinstance(getattr(clip, 'created_at', None), (type(None), __import__('datetime').datetime)) else None,
            updated_at=getattr(clip, 'updated_at', None) if isinstance(getattr(clip, 'updated_at', None), (type(None), __import__('datetime').datetime)) else None,
            collection_ids=[]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=ClipListResponse)
async def get_clips(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[ClipStatus] = Query(None, description="Filter by status"),
    clip_service: ClipService = Depends(get_clip_service)
):
    """Get paginated clips with optional filtering."""
    try:
        pagination = PaginationParams(page=page, size=size)
        
        filters = None
        if project_id or status:
            filters = ClipFilter(
                project_id=project_id,
                status=status
            )
        
        return clip_service.get_clips_paginated(pagination, filters)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{clip_id}", response_model=ClipResponse)
async def get_clip(
    clip_id: str,
    clip_service: ClipService = Depends(get_clip_service)
):
    """Get a clip by ID."""
    try:
        clip = clip_service.get(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        return clip
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{clip_id}", response_model=ClipResponse)
async def update_clip(
    clip_id: str,
    clip_data: ClipUpdate,
    clip_service: ClipService = Depends(get_clip_service)
):
    """Update a clip."""
    try:
        clip = clip_service.update_clip(clip_id, clip_data)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        return clip
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{clip_id}")
async def delete_clip(
    clip_id: str,
    clip_service: ClipService = Depends(get_clip_service)
):
    """Delete a clip."""
    try:
        success = clip_service.delete(clip_id)
        if not success:
            raise HTTPException(status_code=404, detail="Clip not found")
        return {"message": "Clip deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup-duplicates")
async def cleanup_duplicate_clips(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Clean up duplicate clip data in a project"""
    try:
        from ...models.project import Project
        import json
        from pathlib import Path
        from ...core.config import get_data_directory
        
        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all clips from database
        db_clips = db.query(Clip).filter(Clip.project_id == project_id).all()
        logger.info(f"Database has {len(db_clips)} clips")
        
        # Read original data from file system
        data_dir = get_data_directory()
        project_dir = data_dir / "projects" / project_id
        clips_metadata_file = project_dir / "clips_metadata.json"
        
        if not clips_metadata_file.exists():
            raise HTTPException(status_code=404, detail="Clip metadata file not found")
        
        with open(clips_metadata_file, 'r', encoding='utf-8') as f:
            original_clips = json.load(f)
        
        logger.info(f"File system has {len(original_clips)} clips")
        
        # Create ID mapping for original clips
        original_clip_ids = {clip['id']: clip for clip in original_clips}
        
        # Clean up duplicates
        deleted_count = 0
        kept_count = 0
        
        for db_clip in db_clips:
            metadata = db_clip.clip_metadata or {}
            original_id = metadata.get('id')
            
            if original_id and original_id in original_clip_ids:
                # This clip is valid, keep it
                kept_count += 1
                logger.info(f"Keeping clip: {db_clip.title} (ID: {original_id})")
            else:
                # This clip is duplicate or invalid, delete it
                logger.info(f"Deleting duplicate clip: {db_clip.title} (DB ID: {db_clip.id})")
                db.delete(db_clip)
                deleted_count += 1
        
        db.commit()
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "original_count": len(original_clips),
            "db_before_count": len(db_clips),
            "kept_count": kept_count,
            "deleted_count": deleted_count,
            "message": f"Cleanup completed: kept {kept_count}, deleted {deleted_count} duplicate clips"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clean up duplicate clips: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.post("/resync-project")
async def resync_project_clips(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Re-sync project clip data"""
    try:
        from ...models.project import Project
        from ...services.data_sync_service import DataSyncService
        from pathlib import Path
        from ...core.config import get_data_directory
        
        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Delete existing clip data
        existing_clips = db.query(Clip).filter(Clip.project_id == project_id).all()
        deleted_count = len(existing_clips)
        for clip in existing_clips:
            db.delete(clip)
        db.commit()
        logger.info(f"Deleted {deleted_count} existing clips")
        
        # Re-sync data
        data_dir = get_data_directory()
        project_dir = data_dir / "projects" / project_id
        
        sync_service = DataSyncService(db)
        synced_count = sync_service._sync_clips_from_filesystem(project_id, project_dir)
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "deleted_count": deleted_count,
            "synced_count": synced_count,
            "message": f"Re-sync completed: deleted {deleted_count}, synced {synced_count} clips"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to re-sync clips: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Re-sync failed: {str(e)}")
