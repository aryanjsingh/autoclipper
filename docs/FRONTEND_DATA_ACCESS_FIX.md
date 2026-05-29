# Front-end Data Access Issue Repair Documentation

## Problem Description

The front end displays 0 clips and 0 collections, and video files cannot be previewed normally.

## Problem Cause Analysis

1. **Data storage logic is not called**: There is complete data storage logic in the Pipeline adapter, but it is not called in ProcessingOrchestrator
2. **Incomplete metadata fields**: `clip_metadata` and `collection_metadata` in the database are missing key fields
3. **Path configuration error**: The video file path configuration is incorrect
4. **Route registration missing**: The `files` route is not registered correctly

## Fix

### 1. Fix Data Storage Logic

**Problem**: ProcessingOrchestrator is only responsible for executing pipeline steps, but is not responsible for saving the results to the database

**Solution**:
- Add data storage logic at the end of the `execute_pipeline` method
- Add `_save_pipeline_results_to_database` method

```python
def execute_pipeline(self, srt_path: Path, steps_to_execute: Optional[List[ProcessingStep]] = None) -> Dict[str, Any]:
    # ... execute pipeline steps ...

    # Pipeline complete — save data to database
    self._save_pipeline_results_to_database(results)

    # Update task status to completed
    self._update_task_status(TaskStatus.COMPLETED, progress=100)
```

### 2. Fix Metadata Fields

**Problem**: `clip_metadata` in the database lacks `recommend_reason`, `outline`, `content`, and other fields

**Solution**:
- Modify the `_save_clips_to_database` method of the Pipeline adapter
- Add complete metadata fields to `clip_metadata`
- Create an update script to fix existing data

```python
clip_metadata = {
    'metadata_file': metadata_path,
    'clip_id': clip_id,
    'created_at': datetime.now().isoformat(),
    # Add complete metadata fields
    'recommend_reason': clip_data.get('recommend_reason', ''),
    'outline': clip_data.get('outline', ''),
    'content': clip_data.get('content', []),
    'chunk_index': clip_data.get('chunk_index', 0),
    'generated_title': clip_data.get('generated_title', ''),
    'id': clip_data.get('id', '')  # Add id field
}
```

### 3. Fix Path Configuration

**Issue**: `get_clips_directory()` returns wrong path

**Solution**:
- Modify the path configuration in `backend/core/path_utils.py`
- Make sure the path points to the actual file location

```python
def get_clips_directory() -> Path:
    """Get the clips directory."""
    return get_data_directory() / "output" / "clips"

def get_collections_directory() -> Path:
    """Get the collections directory."""
    return get_data_directory() / "output" / "collections"
```

### 4. Fix Video File Access

**Issue**: Clip video URL returns 405 error; collection video URL returns 404 error

**Solution**:
- Fix the `original_id` acquisition logic in the `get_project_clip` method
- Add `files` route registration to `main.py`
- Fix front-end collection video URL generation logic

```python
# Fix original_id acquisition logic
original_id = clip.clip_metadata.get('id') if clip.clip_metadata else None
if not original_id:
    # Read id from metadata file
    metadata_file = clip.clip_metadata.get('metadata_file')
    if metadata_file and Path(metadata_file).exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_data = json.load(f)
            original_id = metadata_data.get('id')
```

### 5. Fix Route Registration

**Issue**: The `files` route is not registered with the FastAPI application

**Solution**:
- Add the import and registration of the `files` router in `backend/main.py`

```python
from api.v1 import health, projects, clips, collections, tasks as task_routes, settings as settings_routes, bilibili, youtube, speech_recognition, files

app.include_router(files.router, prefix="/api/v1", tags=["files"])
```

## Repair Results

### ✅ Issues Fixed

1. **Data storage**: Successfully saved 6 clips and 1 collection to the database
2. **Metadata completeness**: `clip_metadata` contains complete fields
3. **Clip video access**: ✅ Successfully accessed clip video files
4. **API data return**: ✅ The front-end API returns the correct data format

### 📊 Test Results

**Clip data**:
- API returns: 6 clips ✅
- Data conversion: successful ✅
- Video access: successful ✅ (status code 200, file size 58MB)

**Collection data**:
- API returns: 1 collection ✅
- Data conversion: successful ✅
- Video access: partially successful ⚠️ (status code 404, further repair required)

### 🔧 Tool Scripts Created

1. **`scripts/fix_data_storage.py`** — Fix data storage issues
2. **`scripts/update_clip_metadata.py`** — Update metadata fields
3. **`scripts/test_frontend_data.py`** — Test front-end data reading
4. **`scripts/test_video_access.py`** — Test video file access

## Current Status

### ✅ Working Normally

- Front-end data reading ✅
- Clip video access ✅
- API data return ✅
- Metadata integrity ✅

### ⚠️ Needs Further Fixes

- Collection video access (404 error)
- Front-end collection video URL generation logic

## How to Use

### Repair Existing Project Data

```bash
python scripts/fix_data_storage.py --project-id <project ID>
```

### Update Metadata Fields

```bash
python scripts/update_clip_metadata.py --project-id <project ID>
```

### Test Data Access

```bash
python scripts/test_frontend_data.py
python scripts/test_video_access.py
```

## Next Steps

1. **Fix collection video access**: Solve the 404 error of collection video URL
2. **Optimize front-end experience**: Improve video preview and playback functions
3. **Add error handling**: Improve error handling and user prompts
4. **Performance optimization**: Optimize data loading and video streaming

## Related Documents

- `backend/services/processing_orchestrator.py` — Processing orchestrator
- `backend/services/pipeline_adapter.py` — Pipeline adapter
- `backend/core/path_utils.py` — Path configuration
- `backend/api/v1/projects.py` — Projects API
- `backend/api/v1/files.py` — Files API
- `frontend/src/services/api.ts` — Front-end API client
- `scripts/` — Various fix and test scripts
