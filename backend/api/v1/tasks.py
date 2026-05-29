"""
Task management API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.task import Task
from backend.schemas.task import TaskResponse, TaskCreate, TaskUpdate
from backend.services.task_service import TaskService
from backend.services.task_queue_service import TaskQueueService

router = APIRouter()

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get task list"""
    try:
        task_service = TaskService(db)
        tasks = task_service.get_tasks(
            skip=skip,
            limit=limit,
            status=status,
            project_id=project_id
        )
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task list: {str(e)}")

@router.get("/project/{project_id}", response_model=List[TaskResponse])
async def get_project_tasks(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Get task list for a specific project"""
    try:
        task_service = TaskService(db)
        tasks = task_service.get_tasks_by_project_id(project_id)
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project tasks: {str(e)}")

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get single task details"""
    try:
        task_service = TaskService(db)
        task = task_service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task does not exist")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task details: {str(e)}")

@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    """Create a new task"""
    try:
        task_service = TaskService(db)
        task = task_service.create_task(task_data)
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    db: Session = Depends(get_db)
):
    """Update a task"""
    try:
        task_service = TaskService(db)
        task = task_service.update_task(task_id, task_data)
        if not task:
            raise HTTPException(status_code=404, detail="Task does not exist")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Delete a task"""
    try:
        task_service = TaskService(db)
        success = task_service.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task does not exist")
        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")

@router.post("/{task_id}/submit")
async def submit_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Submit task to queue"""
    try:
        task_service = TaskService(db)
        task = task_service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task does not exist")
        
        # Submit to task queue
        queue_service = TaskQueueService()
        result = queue_service.submit_task(task)
        
        return {"message": "Task submitted to queue", "task_id": task_id, "celery_task_id": result.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")

@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Retry failed task"""
    try:
        task_service = TaskService(db)
        task = task_service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task does not exist")
        
        # Reset task status and resubmit
        task_service.update_task(task_id, TaskUpdate(status="pending", progress=0))
        
        # Submit to task queue
        queue_service = TaskQueueService()
        result = queue_service.submit_task(task)
        
        return {"message": "Task resubmitted", "task_id": task_id, "celery_task_id": result.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry task: {str(e)}")

@router.get("/{task_id}/status")
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get task status"""
    try:
        task_service = TaskService(db)
        task = task_service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task does not exist")
        
        return {
            "task_id": task_id,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "error": task.error,
            "updated_at": task.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")
