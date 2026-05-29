# 🏗️ Backend architecture design document

## 📋 Overview

The backend of the automatic clipping tool uses a modular design, supports parallel processing of multiple projects, and includes complete error handling, configuration management, and security mechanisms.

## 🏛️ Architecture layers

### 1. Configuration layer

```
src/config.py
├── ConfigManager          # Unified configuration manager
├── Settings               # Application settings class
├── APIConfig              # API configuration
├── ProcessingConfig       # Processing parameter configuration
└── PathConfig             # Path configuration
```

**Features:**
- Environment variable support
- Configuration validation
- Backwards compatibility
- Multi-project configuration

### 2. Error handling layer

```
src/utils/error_handler.py
├── AutoClipsException     # Base exception class
├── Specific exceptions    # APIError, NetworkError, etc.
├── ErrorHandler           # Error handler
├── CircuitBreaker         # Circuit breaker
└── RetryConfig            # Retry configuration
```

**Features:**
- Layered error handling
- Automatic retry mechanism
- Circuit breaker pattern
- Error context management

### 3. Security layer

```
src/utils/api_key_manager.py
├── APIKeyManager          # API key manager
├── Encrypted storage      # Fernet encryption
├── Key rotation           # Key updates
└── Usage statistics       # Usage monitoring
```

**Features:**
- Encrypted storage of API keys
- Key format validation
- Automatic expiration management
- Usage statistics tracking

### 4. Processing pipeline layer

```
src/pipeline/
├── step1_outline.py       # Outline extraction
├── step2_timeline.py      # Timeline localization
├── step3_scoring.py       # Content scoring
├── step4_title.py         # Title generation
├── step5_clustering.py    # Topic clustering
└── step6_cutting.py       # Video cutting
```

**Features:**
- Modular design
- Independent processing steps
- Intermediate result caching
- Error recovery mechanism

### 5. Utilities layer

```
src/utils/
├── llm_client.py          # LLM client
├── text_processor.py      # Text processing
├── video_processor.py     # Video processing
└── file_manager.py        # File management
```

**Features:**
- Unified LLM calling interface
- Text chunking and merging
- Video processing wrapper
- File operation abstraction

## 🔄 Data flow

### Processing flow

```
Input file → Config validation → Chunking → LLM call → Result parse → File write → Output
     ↓            ↓                 ↓           ↓            ↓            ↓          ↓
 Validator    Config mgr        Text proc    API mgr     Error handler  File mgr   Metadata
```

### Error handling flow

```
Exception → Classification → Handling → Retry/circuit break → Logging → User feedback
    ↓            ↓              ↓              ↓                 ↓            ↓
 Capturer    Classifier      Handler        Recovery          Logger       Feedback
```

## 🛡️ Security design

### 1. API key management

- **Encrypted storage**: Fernet symmetric encryption
- **Key rotation**: Supports key update and rotation
- **Access control**: Role-based key access
- **Usage monitoring**: Key usage statistics and auditing

### 2. Input validation

- **File type validation**: Restrict uploaded file types
- **Size limits**: Prevent large-file attacks
- **Content verification**: Verify file content integrity
- **Path security**: Prevent path traversal attacks

### 3. Error message handling

- **Sensitive information filtering**: Do not expose internal error details
- **Error classification**: Distinguish user errors from system errors
- **Log desensitization**: Do not record sensitive information in logs

## 📊 Performance optimization

### 1. Concurrent processing

- **Asynchronous processing**: Use asyncio for concurrency
- **Task queue**: Background task processing
- **Resource pools**: Connection pool and thread pool management

### 2. Caching

- **Result cache**: Cache LLM call results
- **Configuration cache**: Cache configuration data
- **File cache**: Cache intermediate processing results

### 3. Resource management

- **Memory optimization**: Stream large files
- **Disk optimization**: Clean up temporary files
- **Network optimization**: Connection reuse and timeout control

## 🔧 Configuration management

### Environment variables

```bash
# Required
DASHSCOPE_API_KEY=your_api_key_here
AUTO_CLIPS_MASTER_PASSWORD=your_master_password

# Optional
MODEL_NAME=qwen-plus
CHUNK_SIZE=5000
MIN_SCORE_THRESHOLD=0.7
MAX_CLIPS_PER_COLLECTION=5
LOG_LEVEL=INFO
```

### Configuration file

```json
{
  "api_config": {
    "model_name": "qwen-plus",
    "max_tokens": 4096,
    "timeout": 30
  },
  "processing_config": {
    "chunk_size": 5000,
    "min_score_threshold": 0.7,
    "max_retries": 3
  },
  "paths": {
    "project_root": "/path/to/project",
    "uploads_dir": "/path/to/uploads",
    "temp_dir": "/path/to/temp"
  }
}
```

## 🧪 Testing strategy

### 1. Unit testing

- **Configuration tests**: Loading and validation
- **Error handling tests**: Exceptions and retries
- **API tests**: LLM client
- **Utility tests**: Helper functions

### 2. Integration testing

- **Pipeline tests**: End-to-end processing flow
- **File processing tests**: Upload and download
- **API integration tests**: External API integration

### 3. Performance testing

- **Load tests**: Concurrent processing
- **Memory tests**: Memory usage
- **Network tests**: Request performance

## 📈 Monitoring and logging

### 1. Logging system

```python
# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_clips.log'),
        logging.StreamHandler()
    ]
)
```

### 2. Performance monitoring

- **Processing time**: Per-step duration
- **Resource usage**: CPU, memory, disk
- **Error rate**: Error frequency
- **Success rate**: Processing success rate

### 3. Health checks

- **Service status**: Whether each service is healthy
- **Dependency checks**: External dependencies available
- **Resource checks**: Sufficient system resources

## 🚀 Deployment architecture

### Development environment

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   React Dev     │    │   FastAPI Dev   │
│   (prototype)   │    │   (dev frontend)│    │   (dev backend) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Production environment

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   React Build   │    │   FastAPI       │
│   (reverse proxy)│   │   (prod frontend)│   │   (prod backend)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Redis Cache   │
                    │   (cache layer) │
                    └─────────────────┘
```

## 🔄 Version control

### Semantic versioning

- **Major**: Incompatible API changes
- **Minor**: Backwards-compatible feature additions
- **Patch**: Backwards-compatible bug fixes

### Migration strategy

- **Backwards compatibility**: New versions remain compatible with older versions
- **Progressive migration**: Gradual feature migration
- **Rollback mechanism**: Quick rollback to older versions

## 📚 Best practices

### 1. Code standards

- **PEP 8**: Follow Python coding standards
- **Type annotations**: Use type hints
- **Docstrings**: Complete function and class documentation
- **Error handling**: Unified error handling approach

### 2. Security practices

- **Least privilege**: Use minimum necessary permissions
- **Input validation**: Strictly validate all input
- **Encrypted transport**: Encrypt sensitive data in transit
- **Regular updates**: Keep dependency packages up to date

### 3. Performance practices

- **Asynchronous processing**: Improve performance with async I/O
- **Caching strategy**: Use cache wisely
- **Resource cleanup**: Clean up temporary resources promptly
- **Monitoring and alerts**: Set up performance monitoring and alerts

---

**Note**: This document is updated as the project evolves; refer to the latest version.
