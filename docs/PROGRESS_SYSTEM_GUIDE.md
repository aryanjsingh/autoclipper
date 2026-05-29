# Enhanced Progress System Usage Guide

## 📋 Overview

This project has implemented an enhanced progress system that provides unified progress tracking, status management, and error handling capabilities. The system integrates Redis cache, database persistence, and memory cache to ensure the reliability and real-time nature of progress information.

## 🏗️ System Architecture

### Progress Stages

```python
class ProgressStage(Enum):
    INGEST = "INGEST"          # Download/ready (10%)
    SUBTITLE = "SUBTITLE"      # Subtitles/alignment (15%)
    ANALYZE = "ANALYZE"        # Semantic analysis/outline (20%)
    HIGHLIGHT = "HIGHLIGHT"    # Clip localization/scoring (25%)
    EXPORT = "EXPORT"          # Export/packaging (20%)
    DONE = "DONE"              # Validation/archiving (10%)
    ERROR = "ERROR"            # Error state
```

### Progress Status

```python
class ProgressStatus(Enum):
    PENDING = "PENDING"        # Waiting
    RUNNING = "RUNNING"        # Running
    COMPLETED = "COMPLETED"    # Completed
    FAILED = "FAILED"          # Failed
    CANCELLED = "CANCELLED"    # Cancelled
```

### Storage Hierarchy

1. **Memory Cache**: Quick access, stores currently active progress information
2. **Redis Cache**: Distributed cache, supports multi-instance sharing
3. **Database Persistence**: Long-term storage, synchronized with project status

## 🚀 How to Use

### 1. Basic Progress Tracking

```python
from backend.services.enhanced_progress_service import (
    start_progress, update_progress, complete_progress, fail_progress,
    ProgressStage, ProgressStatus
)

# Start progress tracking
progress_info = start_progress(
    project_id="project_123",
    task_id="task_456",
    initial_message="Starting video processing"
)

# Update progress
progress_info = update_progress(
    project_id="project_123",
    stage=ProgressStage.SUBTITLE,
    message="Generating subtitles",
    sub_progress=50.0  # 50% complete in current stage
)

# Complete progress
progress_info = complete_progress(
    project_id="project_123",
    message="Video processing complete"
)

# Mark as failed
progress_info = fail_progress(
    project_id="project_123",
    error_message="Video file is corrupted"
)
```

### 2. Use in Services

```python
from backend.services.enhanced_progress_service import (
    progress_service, ProgressStage
)
from backend.core.error_middleware import handle_errors, ErrorCategory

class VideoProcessingService:
    
    @handle_errors(ErrorCategory.PROCESSING)
    async def process_video(self, project_id: str, video_path: str):
        try:
            # Start progress tracking
            progress_service.start_progress(
                project_id=project_id,
                initial_message="Starting video processing"
            )
            
            # Download stage
            progress_service.update_progress(
                project_id=project_id,
                stage=ProgressStage.INGEST,
                message="Downloading video file",
                sub_progress=100.0
            )
            
            # Subtitle generation stage
            progress_service.update_progress(
                project_id=project_id,
                stage=ProgressStage.SUBTITLE,
                message="Generating subtitles",
                sub_progress=0.0
            )
            
            # Simulate subtitle generation
            for i in range(10):
                await asyncio.sleep(1)  # Simulate processing time
                progress_service.update_progress(
                    project_id=project_id,
                    stage=ProgressStage.SUBTITLE,
                    message=f"Subtitle generation progress: {i*10}%",
                    sub_progress=i * 10.0
                )
            
            # Analysis stage
            progress_service.update_progress(
                project_id=project_id,
                stage=ProgressStage.ANALYZE,
                message="Analyzing video content",
                sub_progress=0.0
            )
            
            # Continue other stages...
            
            # Complete processing
            progress_service.complete_progress(
                project_id=project_id,
                message="Video processing complete"
            )
            
        except Exception as e:
            # Mark as failed
            progress_service.fail_progress(
                project_id=project_id,
                error_message=str(e)
            )
            raise
```

### 3. Use in API

```python
from fastapi import APIRouter, HTTPException
from backend.services.enhanced_progress_service import get_progress

router = APIRouter()

@router.get("/projects/{project_id}/progress")
async def get_project_progress(project_id: str):
    """Get project progress"""
    try:
        progress_info = get_progress(project_id)
        if not progress_info:
            raise HTTPException(status_code=404, detail="Project progress not found")
        
        return {
            "project_id": project_id,
            "progress": progress_info.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 4. Add Progress Callback

```python
from backend.services.enhanced_progress_service import progress_service

def progress_callback(progress_info):
    """Progress callback function"""
    print(f"Project {progress_info.project_id} progress update: {progress_info.progress}%")
    
    # You can add other logic here, such as:
    # - Send notifications
    # - Update frontend state
    # - Log events
    # - Trigger other services

# Register callback
progress_service.add_progress_callback(progress_callback)
```

## 📊 Progress Information Structure

```python
@dataclass
class ProgressInfo:
    project_id: str                    # Project ID
    task_id: Optional[str]             # Task ID
    stage: ProgressStage               # Current stage
    status: ProgressStatus             # Status
    progress: int                      # Total progress (0-100)
    message: str                       # Current message
    error_message: Optional[str]       # Error message
    start_time: Optional[datetime]     # Start time
    end_time: Optional[datetime]       # End time
    estimated_remaining: Optional[int] # Estimated remaining time (seconds)
    metadata: Optional[Dict[str, Any]] # Metadata
```

### Progress Calculation Rules

- **INGEST stage**: 0-10%
- **SUBTITLE stage**: 10-25%
- **ANALYZE stage**: 25-45%
- **HIGHLIGHT stage**: 45-70%
- **EXPORT stage**: 70-90%
- **DONE stage**: 100%

Progress within each stage can be subdivided using the `sub_progress` parameter (0-100).

## 🔧 Configuration and Optimization

### 1. Redis Configuration

```python
# Configure in backend/core/unified_config.py
redis:
  url: "redis://localhost:6379/0"
  max_connections: 10
  socket_timeout: 5
```

### 2. Cleanup Configuration

```python
# Periodically clean up old progress information
progress_service.cleanup_old_progress(max_age_hours=24)
```

### 3. Error Handling

```python
from backend.utils.error_handler import AutoClipsException, ErrorCategory

try:
    progress_service.update_progress(project_id, stage, message)
except AutoClipsException as e:
    if e.category == ErrorCategory.SYSTEM:
        # System error: log but do not interrupt processing
        logger.error(f"Progress update failed: {e}")
    else:
        # Other errors: re-raise
        raise
```

## 📝 Best Practices

### 1. Writing Progress Messages

```python
# ✅ Good progress message
progress_service.update_progress(
    project_id=project_id,
    stage=ProgressStage.SUBTITLE,
    message="Generating subtitles, about 2 minutes remaining",
    sub_progress=60.0
)

# ❌ Poor progress message
progress_service.update_progress(
    project_id=project_id,
    stage=ProgressStage.SUBTITLE,
    message="Processing...",
    sub_progress=60.0
)
```

### 2. Error Handling

```python
# ✅ Complete error handling
try:
    # Processing logic
    result = await process_video(video_path)
    progress_service.complete_progress(project_id, "Processing complete")
except Exception as e:
    # Record detailed error information
    error_message = f"Processing failed: {str(e)}"
    progress_service.fail_progress(project_id, error_message)
    raise
```

### 3. Metadata Usage

```python
# ✅ Use metadata to pass extra information
progress_service.update_progress(
    project_id=project_id,
    stage=ProgressStage.ANALYZE,
    message="Analyzing video content",
    metadata={
        "video_duration": 1200,  # Video duration (seconds)
        "analysis_method": "ai",  # Analysis method
        "estimated_clips": 5      # Estimated clip count
    }
)
```

### 4. Performance Optimization

```python
# ✅ Batch progress updates
for i, item in enumerate(items):
    if i % 10 == 0:  # Update progress every 10 items
        progress_service.update_progress(
            project_id=project_id,
            stage=ProgressStage.PROCESSING,
            message=f"Processing progress: {i}/{len(items)}",
            sub_progress=i / len(items) * 100
        )
```

## 🧪 Testing the Progress System

### 1. Unit Testing

```python
import pytest
from backend.services.enhanced_progress_service import (
    start_progress, update_progress, complete_progress,
    ProgressStage, ProgressStatus
)

def test_progress_tracking():
    project_id = "test_project"
    
    # Start progress
    progress = start_progress(project_id, initial_message="Starting test")
    assert progress.project_id == project_id
    assert progress.status == ProgressStatus.RUNNING
    assert progress.progress == 0
    
    # Update progress
    progress = update_progress(
        project_id=project_id,
        stage=ProgressStage.SUBTITLE,
        message="Testing subtitle generation",
        sub_progress=50.0
    )
    assert progress.stage == ProgressStage.SUBTITLE
    assert progress.progress > 0
    
    # Complete progress
    progress = complete_progress(project_id, "Test complete")
    assert progress.status == ProgressStatus.COMPLETED
    assert progress.progress == 100
```

### 2. Integration Testing

```python
async def test_progress_integration():
    project_id = "integration_test"
    
    # Simulate full processing flow
    start_progress(project_id, "Starting integration test")
    
    for stage in [ProgressStage.INGEST, ProgressStage.SUBTITLE, 
                  ProgressStage.ANALYZE, ProgressStage.HIGHLIGHT, 
                  ProgressStage.EXPORT]:
        update_progress(project_id, stage, f"Testing {stage.value} stage")
        await asyncio.sleep(0.1)  # Simulate processing time
    
    complete_progress(project_id, "Integration test complete")
    
    # Verify final state
    final_progress = get_progress(project_id)
    assert final_progress.status == ProgressStatus.COMPLETED
    assert final_progress.progress == 100
```

## 🔍 Monitoring and Debugging

### 1. Progress Monitoring

```python
# Get all active progress
active_progress = progress_service.get_all_active_progress()
for progress in active_progress:
    print(f"Project {progress.project_id}: {progress.progress}% - {progress.message}")
```

### 2. Debug Information

```python
# Get detailed progress information
progress_info = get_progress(project_id)
if progress_info:
    print(f"Project ID: {progress_info.project_id}")
    print(f"Current stage: {progress_info.stage.value}")
    print(f"Total progress: {progress_info.progress}%")
    print(f"Status: {progress_info.status.value}")
    print(f"Message: {progress_info.message}")
    print(f"Start time: {progress_info.start_time}")
    print(f"Estimated remaining: {progress_info.estimated_remaining} seconds")
    if progress_info.metadata:
        print(f"Metadata: {progress_info.metadata}")
```

### 3. Logging

```python
import logging

# Configure progress logging
progress_logger = logging.getLogger('progress')
progress_logger.setLevel(logging.INFO)

def progress_log_callback(progress_info):
    progress_logger.info(
        f"Project {progress_info.project_id} progress update: "
        f"{progress_info.progress}% - {progress_info.message}"
    )

progress_service.add_progress_callback(progress_log_callback)
```

## 🚨 FAQ

### 1. Redis Connection Failed

```python
# The system automatically falls back to memory cache
# Check Redis configuration and connection
if not progress_service.redis_client:
    logger.warning("Redis unavailable, using memory cache")
```

### 2. Progress Information Lost

```python
# Periodic cleanup may cause progress information to be lost
# Set a reasonable cleanup interval
progress_service.cleanup_old_progress(max_age_hours=48)  # 48 hours
```

### 3. Progress Updates Too Frequent

```python
# The system has built-in throttling to avoid frequent updates
# Control update frequency in loops
for i, item in enumerate(items):
    if i % 10 == 0:  # Update every 10 iterations
        update_progress(project_id, stage, message, i/len(items)*100)
```

## 📚 Related Documents

- [Error Handling Guide](./ERROR_HANDLING_GUIDE.md)
- [Configuration Management Guide](./CONFIGURATION_GUIDE.md)
- [API Documentation](./API_DOCUMENTATION.md)
