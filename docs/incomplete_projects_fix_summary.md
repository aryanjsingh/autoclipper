# Incomplete Projects Retry Fix Summary

## Problem Description

Users reported two incomplete projects that could not be restarted after clicking retry:

1. **Project 1**: `19cdeea4-16fb-49ce-b114-54cdff7419cd` (iPhone 17/Pro/Air Impressions)
2. **Project 2**: `e11ab97b-6dd2-4d50-97c6-d934b835232c` (43 Days as a Creator: I Made a Film)

## Analysis

### Project 1
- ✅ Video file exists (42.5MB)
- ❌ 18 duplicate task records
- ❌ Project status: failed
- ❌ Multiple Celery task ID conflicts
- ❌ Variable scope issue in pipeline code

### Project 2
- ❌ No video file
- ❌ Project status: pending
- ❌ Needs Bilibili video re-download
- ⚠️ Source URL: `https://www.bilibili.com/video/BV1ihbYzGErq/`

## Fixes

### 1. Pipeline Variable Scope

**Issue**: `cannot access local variable 'timeline_data' where it is not associated with a value`

**Fix**: Fixed variable initialization in `backend/services/simple_pipeline_adapter.py`

```python
# Before: when no outline data, timeline_data was undefined
else:
    logger.warning("No outline data, skipping timeline extraction and content scoring")
    # Create empty files...

# After: initialize all required variables
else:
    logger.warning("No outline data, skipping timeline extraction and content scoring")
    # Create empty files...
    # Initialize empty variables
    timeline_data = []
    scored_clips = []
    titled_clips = []
    collections = []
```

### 2. Duplicate Task Cleanup

**Issue**: Project 1 had 18 duplicate task records causing conflicts

**Fix**: Added `scripts/fix_incomplete_projects.py`
- Remove duplicate task records
- Keep the latest task record
- Clear Celery task ID conflicts

### 3. Automatic Re-download

**Issue**: Project 2 had no video file and needed re-download

**Fix**: Updated retry API in `backend/api/v1/projects.py`
- Detect whether video file exists
- Read source URL from project metadata
- Choose download method by URL type (Bilibili/YouTube)
- Start download with safe task manager

```python
# If video file missing, try re-download
if not video_path.exists():
    logger.warning(f"Video file not found: {video_path}, attempting re-download")
    
    # Check source URL in project metadata
    if hasattr(project, 'project_metadata') and project.project_metadata:
        source_url = project.project_metadata.get('source_url')
        if source_url:
            # Choose download method by URL type
            if 'bilibili.com' in source_url:
                # Bilibili re-download
                # ...
            elif 'youtube.com' in source_url or 'youtu.be' in source_url:
                # YouTube re-download
                # ...
```

### 4. Improved Exception Handling

**Fix**: Use safe task manager in `backend/api/v1/async_task_manager.py`
- Prevent uncaught exceptions from restarting backend
- Task status tracking
- Task cancel and cleanup

## Results

### Project 1
- ✅ Duplicate tasks cleaned up
- ✅ Pipeline variable scope fixed
- ✅ Retry works correctly
- ✅ Processing can be restarted

### Project 2
- ✅ Automatic re-download implemented
- ✅ Source URL detected and re-download started
- ✅ Safe task manager in use
- ✅ Bilibili and YouTube re-download supported

## Testing

### Scripts added
1. `scripts/check_incomplete_projects.py` - Check incomplete projects
2. `scripts/fix_incomplete_projects.py` - Fix project issues
3. `scripts/test_retry_api.py` - Test retry API
4. `scripts/test_bilibili_redownload.py` - Test Bilibili re-download

### Test results
- ✅ Project 1 retry works
- ✅ Project 2 automatic re-download works
- ✅ Pipeline variable scope fixed
- ✅ Duplicate task cleanup works

## Impact

**Before:**
- Project retry failed
- Pipeline processing errors
- Duplicate task conflicts
- No automatic re-download

**After:**
- Project retry works
- Stable pipeline processing
- Clear task management
- Automatic re-download in place

## Technical Notes

1. **Variable scope**: Ensure all variables are initialized before use
2. **Task deduplication**: Remove duplicate tasks to avoid conflicts
3. **Automatic re-download**: Detect missing files and re-download intelligently
4. **Exception handling**: Safe task manager prevents uncaught exceptions
5. **API improvement**: Retry API now supports automatic re-download

## Follow-up

1. Monitor project processing to confirm fixes
2. Periodically clean duplicate tasks
3. Improve error logs for troubleshooting
4. Consider adding task queue management
