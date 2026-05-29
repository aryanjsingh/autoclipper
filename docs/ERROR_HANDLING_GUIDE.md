# Unified Error Handling Guidelines

## 📋 Overview

This project implements a unified error handling mechanism with consistent error response formats and automatic error handling.

## 🏗️ Error handling architecture

### Error categories

```python
class ErrorCategory(Enum):
    CONFIGURATION = "CONFIGURATION"  # Configuration error
    NETWORK = "NETWORK"              # Network error
    API = "API"                      # API error
    FILE_IO = "FILE_IO"              # File I/O error
    PROCESSING = "PROCESSING"        # Processing error
    VALIDATION = "VALIDATION"        # Validation error
    SYSTEM = "SYSTEM"                # System error
```

### Error levels

```python
class ErrorLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
```

## 🚀 How to use

### 1. Throw custom exceptions

```python
from backend.utils.error_handler import AutoClipsException, ErrorCategory

# Raise configuration error
raise AutoClipsException(
    message="API key is not configured",
    category=ErrorCategory.CONFIGURATION,
    details={"config_key": "DASHSCOPE_API_KEY"}
)

# Raise file error
raise AutoClipsException(
    message="File does not exist",
    category=ErrorCategory.FILE_IO,
    details={"file_path": "/path/to/file.mp4"}
)
```

### 2. Use error handling decorator

```python
from backend.core.error_middleware import handle_errors
from backend.utils.error_handler import ErrorCategory

@handle_errors(ErrorCategory.PROCESSING)
async def process_video(video_path: str):
    # Any exception in this function is converted to AutoClipsException
    if not os.path.exists(video_path):
        raise FileNotFoundError("Video file does not exist")
    
    # Processing logic...
    return result
```

### 3. Use error context manager

```python
from backend.core.error_middleware import error_context
from backend.utils.error_handler import ErrorCategory

def upload_file(file_path: str):
    with error_context(ErrorCategory.FILE_IO, {"file_path": file_path}):
        # Any exception in this context is converted to AutoClipsException
        with open(file_path, 'r') as f:
            content = f.read()
        return content
```

### 4. Use in API routes

```python
from fastapi import APIRouter, HTTPException
from backend.utils.error_handler import AutoClipsException, ErrorCategory

router = APIRouter()

@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    try:
        # Business logic
        project = await get_project_from_db(project_id)
        if not project:
            raise AutoClipsException(
                message=f"Project not found: {project_id}",
                category=ErrorCategory.VALIDATION,
                details={"project_id": project_id}
            )
        return project
    except AutoClipsException:
        # Re-raise for the global exception handler
        raise
    except Exception as e:
        # Other exceptions are converted to AutoClipsException
        raise AutoClipsException(
            message="Failed to get project",
            category=ErrorCategory.SYSTEM,
            original_exception=e
        )
```

## 📊 Error response format

All error responses follow a uniform format:

```json
{
  "error": {
    "code": "AUTOCLIPS_VALIDATION",
    "message": "Project not found: abc123",
    "details": {
      "project_id": "abc123"
    },
    "request_id": "req_123456",
    "timestamp": 1640995200.0
  }
}
```

### Field description

- `code`: Error code in the form `AUTOCLIPS_{CATEGORY}` or `HTTP_{STATUS_CODE}`
- `message`: User-friendly error message
- `details`: Error details, including debugging information
- `request_id`: Request ID for tracing
- `timestamp`: When the error occurred

## 🔧 HTTP status code mapping

| Error category | HTTP status code | Description |
|----------------|------------------|-------------|
| CONFIGURATION | 500 | Configuration error |
| NETWORK | 503 | Network error |
| API | 502 | API error |
| FILE_IO | 500 | File I/O error |
| PROCESSING | 500 | Processing error |
| VALIDATION | 400 | Validation error |
| SYSTEM | 500 | System error |

## 📝 Best practices

### 1. Writing error messages

```python
# ✅ Good error message
raise AutoClipsException(
    message="Unsupported video format; please use MP4",
    category=ErrorCategory.VALIDATION,
    details={"supported_formats": ["mp4", "avi", "mov"]}
)

# ❌ Poor error message
raise AutoClipsException(
    message="Error: Invalid file",
    category=ErrorCategory.VALIDATION
)
```

### 2. Include error details

```python
# ✅ Include useful debugging information
raise AutoClipsException(
    message="Failed to process video",
    category=ErrorCategory.PROCESSING,
    details={
        "project_id": project_id,
        "step": "video_cutting",
        "error_code": "FFMPEG_ERROR",
        "file_size": file_size
    }
)
```

### 3. Choosing error categories

```python
# ✅ Choose the category that matches the failure
if not api_key:
    raise AutoClipsException(
        message="API key is not configured",
        category=ErrorCategory.CONFIGURATION  # Configuration issue
    )

if response.status_code == 429:
    raise AutoClipsException(
        message="API rate limit exceeded",
        category=ErrorCategory.API  # API issue
    )

if not os.path.exists(file_path):
    raise AutoClipsException(
        message="File does not exist",
        category=ErrorCategory.FILE_IO  # File issue
    )
```

### 4. Preserve exception chains

```python
# ✅ Keep the original exception
try:
    result = some_risky_operation()
except Exception as e:
    raise AutoClipsException(
        message="Operation failed",
        category=ErrorCategory.SYSTEM,
        original_exception=e  # Preserve original exception
    )
```

## 🧪 Testing error handling

### 1. Test custom exceptions

```python
import pytest
from backend.utils.error_handler import AutoClipsException, ErrorCategory

def test_custom_exception():
    with pytest.raises(AutoClipsException) as exc_info:
        raise AutoClipsException(
            message="Test error",
            category=ErrorCategory.VALIDATION
        )
    
    assert exc_info.value.category == ErrorCategory.VALIDATION
    assert exc_info.value.message == "Test error"
```

### 2. Test API error responses

```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_api_error_response():
    response = client.get("/api/v1/projects/nonexistent")
    
    assert response.status_code == 400
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "AUTOCLIPS_VALIDATION"
```

## 🔍 Error monitoring and logging

### 1. Error log format

All errors are logged automatically in the following format:

```
2024-01-01 12:00:00 - ERROR - Unhandled exception: AutoClipsException: Project not found: abc123
request_id: req_123456
path: /api/v1/projects/abc123
method: GET
traceback: [full stack trace]
```

### 2. Error statistics

Use log analysis to aggregate errors:

```bash
# Count errors by type
grep "AUTOCLIPS_" backend.log | cut -d' ' -f4 | sort | uniq -c

# Count error frequency
grep "ERROR" backend.log | wc -l
```

## 🚨 Common error handling scenarios

### 1. File operation errors

```python
@handle_errors(ErrorCategory.FILE_IO)
async def save_file(file_path: str, content: bytes):
    try:
        with open(file_path, 'wb') as f:
            f.write(content)
    except PermissionError:
        raise AutoClipsException(
            message="No permission to write file",
            category=ErrorCategory.FILE_IO,
            details={"file_path": file_path}
        )
    except OSError as e:
        raise AutoClipsException(
            message="Filesystem error",
            category=ErrorCategory.FILE_IO,
            details={"file_path": file_path, "os_error": str(e)}
        )
```

### 2. API call errors

```python
@handle_errors(ErrorCategory.API)
async def call_external_api(url: str, data: dict):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 429:
                    raise AutoClipsException(
                        message="API rate limit exceeded",
                        category=ErrorCategory.API,
                        details={"url": url, "status": 429}
                    )
                return await response.json()
    except aiohttp.ClientError as e:
        raise AutoClipsException(
            message="Network request failed",
            category=ErrorCategory.NETWORK,
            details={"url": url, "error": str(e)}
        )
```

### 3. Data processing errors

```python
@handle_errors(ErrorCategory.PROCESSING)
async def process_video_data(video_path: str):
    try:
        # Processing logic
        result = await video_processor.process(video_path)
        return result
    except VideoProcessingError as e:
        raise AutoClipsException(
            message="Video processing failed",
            category=ErrorCategory.PROCESSING,
            details={
                "video_path": video_path,
                "error_code": e.code,
                "step": e.step
            },
            original_exception=e
        )
```

## 📚 Related documents

- [API Documentation](./API_DOCUMENTATION.md)
- [Configuration Management Guide](./CONFIGURATION_GUIDE.md)
- [Log Management Guide](./LOGGING_GUIDE.md)
